"""Hash-chained egress audit log (design v3 control #10). Per-tool ALLOWLIST of loggable fields (fail-closed:
a field not listed is never logged, so a future secret-bearing field can't leak by omission — not a denylist)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading

from ..common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash

# Loggable arg fields per tool. Note: `query` (search) and the full `url` (fetch) are DELIBERATELY absent —
# they may carry case/source identifiers; only the validated host + connector are recorded.
LOGGABLE_FIELDS = {
    "search": ("connector", "max_results"),
    "fetch": ("host",),
    "reverse_image_search": ("connector",),
    "get_map_tile": ("connector", "zoom"),
}


class EgressAudit:
    def __init__(self, db_path: str):
        # S14: check_same_thread=False to match every sibling store — FastMCP may dispatch a tool body on a
        # worker thread. All writes are serialized by self._lock (S15), so this cannot race.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        # S15: serialize the head-read -> hash -> INSERT -> commit sequence so two concurrent egress calls
        # cannot read the same prev_hash and fork the append-only chain (mirrors EvidenceStore._write_lock).
        self._lock = threading.Lock()
        # MF3: an external append-only manifest anchoring the chain head + row count, so trailing-row
        # truncation (deleting an attempt->ok egress pair to erase an event) is detectable — a forward-only
        # re-derivation cannot catch it. Mirrors ach-engine's manifest reconciliation.
        self._manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS egress_log("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, tool TEXT NOT NULL, fields TEXT NOT NULL, "
            "resolved_ip TEXT NOT NULL, outcome TEXT NOT NULL, at TEXT NOT NULL, "
            "prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL)"
        )
        self._conn.commit()
        # M-manifest: tail of the self-chained manifest, read once at open so appends after a restart
        # continue the chain (each line binds to the previous line's hash — a mid-file edit is detectable).
        self._manifest_head = self._read_manifest_head()

    def close(self) -> None:
        self._conn.close()

    def _head(self) -> str:
        r = self._conn.execute("SELECT row_hash FROM egress_log ORDER BY seq DESC LIMIT 1").fetchone()
        return r["row_hash"] if r else GENESIS

    def _read_manifest_head(self) -> str:
        """Last manifest_hash on disk (GENESIS if no manifest yet) — the tail of the self-chain."""
        if not self._manifest_path or not os.path.exists(self._manifest_path):
            return GENESIS
        last = GENESIS
        with open(self._manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = json.loads(line).get("manifest_hash", GENESIS)
        return last

    def _append_manifest(self, head: str) -> None:
        # MF3: one manifest line per audit row (the chain head after that append), created 0600 — the
        # unkeyed chain's tamper-evidence rests on OS file isolation of both the DB and this anchor.
        # M-manifest: SELF-CHAIN each line to the previous line's hash (backport of the calibration/
        # evidence-ledger manifest self-chaining) so a MIDDLE manifest line cannot be edited or dropped
        # undetected — the head+count anchor alone misses an edit to a non-terminal line.
        if not self._manifest_path:
            return
        payload = {"head": head, "at": now_iso()}
        mh = row_hash(self._manifest_head, payload)
        entry = {**payload, "prev_manifest_hash": self._manifest_head, "manifest_hash": mh}
        fd = os.open(self._manifest_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        self._manifest_head = mh

    def _check_manifest(self, db_head: str, db_count: int) -> tuple[bool, ChainMismatch | None]:
        """Reconcile the live egress_log against the manifest AND verify the manifest's own self-chain.

        MF3: trailing-row truncation (erasing an attempt->ok pair to hide an event) leaves a self-consistent
        shorter chain; the attested head + row count catches it. The self-chain walk additionally catches an
        edit to any non-terminal manifest line. A non-empty chain with no manifest file fails closed.
        (Residual: an actor with filesystem write can recompute both the DB chain AND the manifest self-chain
        in lockstep — durable tamper-evidence needs these heads shipped to an off-host WORM log.)
        """
        if not self._manifest_path:  # in-memory store: nothing to attest
            return True, None
        if not os.path.exists(self._manifest_path):
            if db_head != GENESIS:  # rows survive but the manifest was deleted -> fail closed, not vacuous pass
                return False, ChainMismatch(
                    table="egress_log", row_id="<manifest-missing>", expected_hash=db_head, got_hash=GENESIS
                )
            return True, None
        last_head, count, prev = GENESIS, 0, GENESIS
        with open(self._manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                expected = row_hash(prev, {"head": e["head"], "at": e["at"]})
                if e.get("prev_manifest_hash") != prev or e.get("manifest_hash") != expected:
                    return False, ChainMismatch(
                        table="egress_log", row_id="<manifest-chain>",
                        expected_hash=expected, got_hash=str(e.get("manifest_hash", "")),
                    )
                prev = expected
                last_head = e["head"]
                count += 1
        if last_head != db_head or count != db_count:
            return False, ChainMismatch(
                table="egress_log", row_id="manifest",
                expected_hash=f"{last_head} ({count} rows)", got_hash=f"{db_head} ({db_count} rows)",
            )
        return True, None

    def record(self, tool: str, fields: dict, resolved_ip: str, outcome: str) -> None:
        allow = LOGGABLE_FIELDS.get(tool, ())
        logged = {k: fields[k] for k in allow if k in fields}  # fail-closed allowlist
        with self._lock:  # S15: whole head-read -> INSERT -> commit is atomic vs other writers
            payload = {"tool": tool, "fields": logged, "resolved_ip": resolved_ip, "outcome": outcome,
                       "at": now_iso()}
            prev = self._head()
            rh = row_hash(prev, payload)
            self._conn.execute(
                "INSERT INTO egress_log(tool, fields, resolved_ip, outcome, at, prev_hash, row_hash) "
                "VALUES(?,?,?,?,?,?,?)",
                (tool, json.dumps(logged, sort_keys=True), resolved_ip, outcome, payload["at"], prev, rh),
            )
            self._conn.commit()
            self._append_manifest(rh)  # MF3: attest the new head AFTER the row durably commits

    def verify_chain(self) -> ChainStatus:
        # lock: hold self._lock for the whole read + manifest walk. Every writer (record) holds self._lock
        # across its commit -> manifest-append; without the lock here a verify interleaved with an in-flight
        # record could read a row committed-but-not-yet-manifest-attested and report a spurious tamper on a
        # healthy log. self._lock is a plain Lock and verify_chain re-acquires nothing, so it cannot deadlock.
        with self._lock:
            prev = GENESIS
            verified = 0
            for r in self._conn.execute("SELECT * FROM egress_log ORDER BY seq ASC").fetchall():
                payload = {"tool": r["tool"], "fields": json.loads(r["fields"]), "resolved_ip": r["resolved_ip"],
                           "outcome": r["outcome"], "at": r["at"]}
                expected = row_hash(prev, payload)
                if expected != r["row_hash"] or r["prev_hash"] != prev:
                    return ChainStatus(
                        server="osint-egress-audit", scope="all", ok=False, head_hash={"egress_log": prev},
                        rows_verified=verified,
                        mismatch=ChainMismatch(table="egress_log", row_id=str(r["seq"]), expected_hash=expected,
                                               got_hash=r["row_hash"]),
                    )
                prev = r["row_hash"]
                verified += 1
            # MF3/M-manifest: reconcile the live table against the manifest AND verify the manifest self-chain.
            # Truncating trailing rows leaves a self-consistent shorter chain; the head + count anchor catches
            # it, and the self-chain walk catches a non-terminal manifest-line edit (the residual both-truncated
            # attack — dropping the matching manifest tail too — still needs an off-host WORM anchor).
            manifest_ok, mismatch = self._check_manifest(prev, verified)
            if not manifest_ok:
                return ChainStatus(
                    server="osint-egress-audit", scope="all", ok=False, head_hash={"egress_log": prev},
                    rows_verified=verified, mismatch=mismatch,
                )
            return ChainStatus(server="osint-egress-audit", scope="all", ok=True, head_hash={"egress_log": prev},
                               rows_verified=verified)

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) c FROM egress_log").fetchone()["c"]
