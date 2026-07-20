"""Shared hash-chain helpers + chain-status models for the MCP state layer (design v3)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import NamedTuple

from pydantic import BaseModel

GENESIS = "0" * 64


def canon(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def row_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + canon(payload)).encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ChainMismatch(BaseModel):
    table: str
    row_id: str
    expected_hash: str
    got_hash: str


class ChainStatus(BaseModel):
    server: str
    scope: str
    ok: bool
    head_hash: dict[str, str]
    rows_verified: int
    mismatch: ChainMismatch | None = None


# verify_stable retry budget (env-tunable so a slow-disk/throttled-IOPS deployment whose fsync stalls past
# the default window can widen it rather than fail spuriously). A real tamper reproduces regardless of budget.
_VERIFY_ATTEMPTS = max(1, int(os.environ.get("MCP_VERIFY_ATTEMPTS", "3")))
_VERIFY_DELAY_S = max(0.0, float(os.environ.get("MCP_VERIFY_DELAY_S", "0.05")))


def verify_stable(
    verify_fn: Callable[[], ChainStatus],
    attempts: int | None = None,
    delay: float | None = None,
    label: str = "verify_chain",
) -> ChainStatus:
    """Call a store's verify_chain(), tolerating the benign cross-process commit -> manifest-append window.

    A writer commits a row, then appends the manifest attestation as a SEPARATE fsync'd step (they cannot
    share one transaction — different files). A verify from ANOTHER process that lands between the two sees a
    table head/count one ahead of the manifest and reports a spurious mismatch. Such a race self-resolves
    within one append, so retry a few times before trusting a mismatch.

    Fail-closed scope: a PASSIVE or persistent tamper (the DB and manifest stay inconsistent) reproduces on
    every attempt and is still refused. It does NOT defend against an ACTIVE co-resident attacker who can
    forge a self-consistent chain and revert it inside the retry window — that is the already-disclosed
    "rewrite the files and recompute the chain forward" residual (see Manifest), not closed here. So that a
    forge-and-revert cannot pass invisibly, ANY retry (>1 attempt) is logged to stderr — an operator can read
    a lone retry as benign cross-process jitter but a pattern as a possible active tamper. attempts/delay
    default from MCP_VERIFY_ATTEMPTS / MCP_VERIFY_DELAY_S. Returns the final ChainStatus."""
    n = _VERIFY_ATTEMPTS if attempts is None else attempts
    d = _VERIFY_DELAY_S if delay is None else delay
    status = verify_fn()
    used = 1
    for _ in range(max(0, n - 1)):
        if status.ok:
            break
        time.sleep(d)
        status = verify_fn()
        used += 1
    if used > 1:
        print(
            f"[verify_stable] {label}: chain reconciled after {used} attempts (ok={status.ok}) — "
            "a benign cross-process append window, or investigate a possible active tamper.",
            file=sys.stderr,
        )
    return status


class ManifestMismatch(NamedTuple):
    """A manifest reconciliation failure. Each store wraps it into its own ChainMismatch model (common's or
    a per-package duplicate), so the Manifest helper stays decoupled from any specific pydantic model."""

    table: str
    row_id: str
    expected_hash: str
    got_hash: str


class Manifest:
    """Self-chained, fsync'd, 0600 external attestation of per-table chain heads + append counts.

    The tamper-evidence anchor that catches (a) trailing-row TRUNCATION — a self-consistent but SHORTER
    chain the forward per-row walk would PASS — via the attested per-table head + monotonic append count, and
    (b) whole-table / whole-file DELETION via a fail-closed presence check. Extracted so every store shares
    ONE implementation: a new store inherits the protection instead of re-deriving (and possibly OMITTING)
    it — which is exactly how the shared staleness store once came to lack a manifest.

    Wire format, one JSON line per append: {table, head, at, count, prev_manifest_hash, manifest_hash}.
    Each line's manifest_hash chains to the previous line's, so a NON-TERMINAL line cannot be edited or
    dropped undetected; `count` (the monotonic per-table append count) is inside the hashed payload.

    Residual (documented): the manifest shares the DB's trust domain. A trailing-row TRUNCATION needs NO
    recomputation — dropping a chain's tail leaves every earlier line self-consistent — so an actor with
    filesystem write to BOTH the DB and this file can truncate them in lockstep undetected (a mid-chain edit,
    by contrast, must recompute every following line). Durable tamper-evidence needs these heads shipped to an
    off-host append-only/WORM log. The OWNING STORE keeps its own write-lock around commit -> append and
    around its verify walk, so this class is not independently thread-safe by design.
    """

    def __init__(self, path: str | None, tables: tuple[str, ...]):
        self.path = path
        self._tables = tables
        self._head, self._counts = self._read_state()

    def _read_state(self) -> tuple[str, dict[str, int]]:
        """Tail manifest_hash + last attested per-table count (GENESIS + {} if no manifest yet)."""
        counts: dict[str, int] = {}
        if not self.path or not os.path.exists(self.path):
            return GENESIS, counts
        last = GENESIS
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                last = e.get("manifest_hash", GENESIS)
                counts[e["table"]] = e.get("count", counts.get(e["table"], 0) + 1)
        return last, counts

    def append(self, table: str, head: str, count: int | None = None) -> None:
        """Attest a per-table head AFTER its row durably commits. Normal appends auto-increment the count;
        seed() passes the true live count. Created 0600 (private) + fsync'd."""
        if not self.path:
            return
        if count is None:
            count = self._counts.get(table, 0) + 1
        payload = {"table": table, "head": head, "at": now_iso(), "count": count}
        mh = row_hash(self._head, payload)
        entry = {**payload, "prev_manifest_hash": self._head, "manifest_hash": mh}
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._head = mh
        self._counts[table] = count

    def check(
        self, heads: dict[str, str], counts: dict[str, int]
    ) -> tuple[bool, ManifestMismatch | None]:
        """Reconcile live per-table (head, count) against the manifest AND verify the manifest's own
        self-chain. A non-empty table with no manifest file at all fails closed (not a vacuous pass)."""
        if not self.path:  # in-memory store: nothing to attest
            return True, None
        non_genesis = {t for t in self._tables if heads.get(t, GENESIS) != GENESIS}
        if not os.path.exists(self.path):
            if non_genesis:
                t = sorted(non_genesis)[0]
                return False, ManifestMismatch(
                    t, "<manifest-missing>", heads.get(t, GENESIS), GENESIS
                )
            return True, None
        last: dict[str, str] = {}
        last_count: dict[str, int] = {}
        line_count: dict[str, int] = {}
        prev = GENESIS
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                # `count` is part of the hashed payload only when ATTESTED — a pre-count manifest (an older
                # on-disk format) hashed a {table, head, at} payload, so honour whichever form each line used.
                payload = {"table": e["table"], "head": e["head"], "at": e["at"]}
                if "count" in e:
                    payload["count"] = e["count"]
                expected = row_hash(prev, payload)
                if e.get("prev_manifest_hash") != prev or e.get("manifest_hash") != expected:
                    return False, ManifestMismatch(
                        e.get("table", "?"),
                        "<manifest-chain>",
                        expected,
                        str(e.get("manifest_hash", "")),
                    )
                prev = expected
                last[e["table"]] = e["head"]
                line_count[e["table"]] = line_count.get(e["table"], 0) + 1
                if "count" in e:
                    last_count[e["table"]] = e["count"]
        for table in self._tables:
            m_head = last.get(table, GENESIS)
            # attested count: the last payload count if any entry carried one, else the manifest LINE count
            # (equal to the row count for a pre-count manifest, where each row wrote one count-less line).
            m_count = last_count.get(table, line_count.get(table, 0))
            if m_head != heads.get(table, GENESIS) or m_count != counts.get(table, 0):
                return False, ManifestMismatch(
                    table,
                    "<manifest>",
                    f"{m_head} (manifest: {m_count} rows)",
                    f"{heads.get(table, GENESIS)} (tables: {counts.get(table, 0)} rows)",
                )
        return True, None

    def seed(self, heads: dict[str, str], counts: dict[str, int]) -> int:
        """One-time migration: attest current per-table (head, count) for a DB predating the manifest.
        Trust-on-first-use — a no-op if a manifest already exists. Returns entries written."""
        if not self.path or os.path.exists(self.path):
            return 0
        written = 0
        for table in self._tables:
            if heads.get(table, GENESIS) != GENESIS:
                self.append(table, heads[table], counts.get(table, 0))
                written += 1
        return written
