"""Shared cross-server EVIDENCE-SIGNAL store (the narrow coupling between evidence-ledger and ach-engine).

Two append-only, hash-chained signals evidence-ledger WRITES and ach-engine READS:
- `stale_events` — a grade changed; dependent ACH cells must be re-rated before scoring.
- `grade_signals` — a grade was recorded with a given judgment_source; ach-engine refuses to SCORE a cell whose
  evidence has no effective `analyst_confirmed` grade (closes the collect-then-grade hole — an ingested,
  ungraded artifact can never reach scored output; design v3 decision #3/#8).

Deliberate, scoped, out-of-protocol side channel (design "DB file topology"): evidence-ledger may write only
these signals here — never ach-engine's core tables.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from collections.abc import Callable

from .common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash

_TABLES = ("stale_events", "grade_signals")


class StalenessStore:
    def __init__(self, db_path: str, clock: Callable[[], float] = time.time):
        self.db_path = db_path
        self._clock = clock
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        # SF-lock: serialize every head-read -> INSERT -> commit -> manifest-append so two threads cannot
        # read the same head and fork the append-only chain (mirrors ACHStore/EvidenceStore). Today the sole
        # writer path (evidence-ledger._insert_grade) already holds its own lock, but this store must be
        # correct independent of external discipline. RLock is reentrant, so verify_chain taking it around its
        # whole body cannot deadlock a caller that already holds it. NOTE: no OS-level *process* lock here (a
        # deliberate difference from EvidenceStore) — ach-engine opens this same file read-only cross-process,
        # so an exclusive file lock would break the intended single-writer(evidence-ledger)/reader(ach) split.
        self._write_lock = threading.RLock()
        # S2: check_same_thread=False to match EvidenceStore. grade_evidence -> _mark_staleness_signals
        # writes here on the same dispatch thread; if FastMCP ever runs a tool body on a worker thread,
        # the default (True) would raise ProgrammingError — the exact scenario EvidenceStore guards
        # against. Writes are serialized by EvidenceStore._write_lock (the only writer of these signals).
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS stale_events(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL, changed_field TEXT NOT NULL,
                marked_at TEXT NOT NULL, marked_ts REAL NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS grade_signals(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL, judgment_source TEXT NOT NULL,
                marked_at TEXT NOT NULL, marked_ts REAL NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            """
        )
        self._conn.commit()
        # MF5/N8: keep this shared signal DB (+ WAL sidecars) private — its grade_signals chain is the
        # collect-then-grade authority; the unkeyed chain's tamper-evidence rests on OS file isolation.
        if db_path != ":memory:":
            for path in (db_path, db_path + "-wal", db_path + "-shm"):
                if os.path.exists(path):
                    try:
                        os.chmod(path, 0o600)
                    except OSError:
                        pass
        # M-manifest (the MUST fix): tail of the self-chained external manifest, read once at open so appends
        # after a restart continue the chain. WITHOUT this anchor, trailing-row truncation of grade_signals —
        # deleting a `model_draft` downgrade so latest_grade_source() reverts to the earlier `analyst_confirmed`
        # — left a self-consistent but shorter chain that verify_chain() PASSED, silently forging the
        # collect-then-grade gate ach-engine.score_matrix trusts. The head+count manifest anchor detects it.
        self._manifest_head = self._read_manifest_head()

    def close(self) -> None:
        self._conn.close()

    def _head(self, table: str) -> str:
        # MF3: explicit guard (not assert — assertions are stripped under python -O / PYTHONOPTIMIZE,
        # which would re-open f-string SQL-identifier interpolation below). Mirrors ACHStore._head.
        if table not in _TABLES:
            raise ValueError(f"unknown table: {table}")
        r = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - internal literal
        ).fetchone()
        return r["row_hash"] if r else GENESIS

    # ---- external manifest (anchor against tail-truncation / whole-chain reset) --------------------
    def _read_manifest_head(self) -> str:
        """Last manifest_hash on disk (GENESIS if no manifest yet) — the tail of the self-chain."""
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return GENESIS
        last = GENESIS
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = json.loads(line).get("manifest_hash", GENESIS)
        return last

    def _append_manifest(self, table: str, head: str) -> None:
        if not self.manifest_path:
            return
        # SELF-CHAIN each line to the previous line's hash (mirrors ach-engine / evidence-ledger) so a MIDDLE
        # manifest line cannot be edited or dropped undetected — the per-table head+count reconciliation alone
        # misses an edit to a non-terminal line. MF5/N8: create the manifest private (0o600) — it anchors the
        # tamper-evidence reconciliation, so a co-resident writer must not read/rewrite it. Residual (SF4): the
        # manifest shares the DB's trust domain, so an actor with filesystem write can recompute the whole
        # self-chain in lockstep — durable tamper-evidence needs these heads shipped to an off-host WORM log.
        payload = {"table": table, "head": head, "at": now_iso()}
        mh = row_hash(self._manifest_head, payload)
        entry = {**payload, "prev_manifest_hash": self._manifest_head, "manifest_hash": mh}
        fd = os.open(self.manifest_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        self._manifest_head = mh

    def seed_manifest_baseline(self) -> int:
        """One-time migration: attest the current per-table heads for a DB that predates the manifest.
        Trust-on-first-use — only meaningful when no manifest exists yet. Returns entries written."""
        if not self.manifest_path or os.path.exists(self.manifest_path):
            return 0
        written = 0
        with self._write_lock:
            for table in _TABLES:
                head = self._head(table)
                if head != GENESIS:
                    self._append_manifest(table, head)
                    written += 1
        return written

    def _check_manifest(
        self, heads: dict[str, str], counts: dict[str, int]
    ) -> tuple[bool, ChainMismatch | None]:
        """Reconcile the live tables against the manifest AND verify the manifest's own self-chain.

        Trailing-row truncation leaves a self-consistent but shorter chain; the per-table head + append-count
        anchor catches it. The self-chain walk additionally catches an edit to a non-terminal manifest line.
        A non-empty table with no manifest file at all fails closed (not a vacuous pass).
        """
        if not self.manifest_path:  # in-memory stores have no manifest by design
            return True, None
        non_genesis = {t for t in _TABLES if heads.get(t, GENESIS) != GENESIS}
        if not os.path.exists(self.manifest_path):
            if non_genesis:
                table = sorted(non_genesis)[0]
                return False, ChainMismatch(
                    table=table, row_id="<manifest-missing>",
                    expected_hash=heads.get(table, GENESIS), got_hash=GENESIS,
                )
            return True, None
        last: dict[str, str] = {}
        last_count: dict[str, int] = {}
        prev = GENESIS
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                payload = {"table": e["table"], "head": e["head"], "at": e["at"]}
                expected = row_hash(prev, payload)
                if e.get("prev_manifest_hash") != prev or e.get("manifest_hash") != expected:
                    return False, ChainMismatch(
                        table=e.get("table", "?"), row_id="<manifest-chain>",
                        expected_hash=expected, got_hash=str(e.get("manifest_hash", "")),
                    )
                prev = expected
                last[e["table"]] = e["head"]
                last_count[e["table"]] = last_count.get(e["table"], 0) + 1
        for table in _TABLES:
            m_head, m_count = last.get(table, GENESIS), last_count.get(table, 0)
            if m_head != heads[table] or m_count != counts[table]:
                return False, ChainMismatch(
                    table=table, row_id="<manifest>",
                    expected_hash=f"{m_head} (manifest: {m_count} rows)",
                    got_hash=f"{heads[table]} (tables: {counts[table]} rows)",
                )
        return True, None

    # ---- staleness signal --------------------------------------------------
    def mark_stale(self, evidence_id: str, changed_field: str) -> None:
        ts = self._clock()
        payload = {"evidence_id": evidence_id, "changed_field": changed_field, "marked_at": now_iso()}
        with self._write_lock:
            prev = self._head("stale_events")
            rh = row_hash(prev, payload)
            with self._conn:  # atomic commit-or-rollback; manifest appended only AFTER the commit succeeds
                self._conn.execute(
                    "INSERT INTO stale_events(evidence_id, changed_field, marked_at, marked_ts, prev_hash, row_hash) "
                    "VALUES(?,?,?,?,?,?)",
                    (evidence_id, changed_field, payload["marked_at"], ts, prev, rh),
                )
            self._append_manifest("stale_events", rh)

    def latest_stale_ts(self, evidence_id: str) -> float | None:
        r = self._conn.execute(
            "SELECT MAX(marked_ts) m FROM stale_events WHERE evidence_id=?", (evidence_id,)
        ).fetchone()
        return r["m"] if r and r["m"] is not None else None

    def changed_field(self, evidence_id: str) -> str | None:
        r = self._conn.execute(
            "SELECT changed_field FROM stale_events WHERE evidence_id=? ORDER BY seq DESC LIMIT 1",
            (evidence_id,),
        ).fetchone()
        return r["changed_field"] if r else None

    # ---- grade-confirmation signal ----------------------------------------
    def mark_graded(self, evidence_id: str, judgment_source: str) -> None:
        ts = self._clock()
        payload = {"evidence_id": evidence_id, "judgment_source": judgment_source, "marked_at": now_iso()}
        with self._write_lock:
            prev = self._head("grade_signals")
            rh = row_hash(prev, payload)
            with self._conn:  # atomic commit-or-rollback; manifest appended only AFTER the commit succeeds
                self._conn.execute(
                    "INSERT INTO grade_signals(evidence_id, judgment_source, marked_at, marked_ts, prev_hash, row_hash) "
                    "VALUES(?,?,?,?,?,?)",
                    (evidence_id, judgment_source, payload["marked_at"], ts, prev, rh),
                )
            self._append_manifest("grade_signals", rh)

    def latest_grade_source(self, evidence_id: str) -> str | None:
        """The judgment_source of the most recent grade for an evidence item, or None if never graded.
        ach-engine requires this to be 'analyst_confirmed' before an evidence item's cells may be scored."""
        r = self._conn.execute(
            "SELECT judgment_source FROM grade_signals WHERE evidence_id=? ORDER BY seq DESC LIMIT 1",
            (evidence_id,),
        ).fetchone()
        return r["judgment_source"] if r else None

    # ---- integrity ---------------------------------------------------------
    def _payload_for(self, table: str, r) -> dict:
        if table == "stale_events":
            return {"evidence_id": r["evidence_id"], "changed_field": r["changed_field"], "marked_at": r["marked_at"]}
        return {"evidence_id": r["evidence_id"], "judgment_source": r["judgment_source"], "marked_at": r["marked_at"]}

    def verify_chain(self) -> ChainStatus:
        """Verify BOTH signal chains AND anchor each to the external manifest. score_matrix trusts
        grade_signals for collect-then-grade, so this must be checked at startup by every server that opens
        this file (evidence-ledger AND ach-engine). The manifest head+count anchor catches trailing-row
        truncation that the forward-only row walk alone would PASS (a deleted downgrade -> stale confirmation)."""
        with self._write_lock:
            heads: dict[str, str] = {}
            counts: dict[str, int] = {}
            verified = 0
            for table in _TABLES:
                prev = GENESIS
                count = 0
                rows = self._conn.execute(
                    f"SELECT * FROM {table} ORDER BY seq ASC"  # noqa: S608 - internal literal
                ).fetchall()
                for r in rows:
                    expected = row_hash(prev, self._payload_for(table, r))
                    if expected != r["row_hash"] or r["prev_hash"] != prev:
                        return ChainStatus(
                            server="evidence-signals", scope="all", ok=False, head_hash=heads, rows_verified=verified,
                            mismatch=ChainMismatch(
                                table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                            ),
                        )
                    prev = r["row_hash"]
                    count += 1
                    verified += 1
                heads[table] = prev
                counts[table] = count
            # M-manifest: reconcile live tables against the manifest (head+count) AND verify the manifest's own
            # self-chain — catches trailing-row truncation and a non-terminal manifest-line edit.
            manifest_ok, mismatch = self._check_manifest(heads, counts)
            if not manifest_ok:
                return ChainStatus(
                    server="evidence-signals", scope="all", ok=False, head_hash=heads,
                    rows_verified=verified, mismatch=mismatch,
                )
            return ChainStatus(
                server="evidence-signals", scope="all", ok=True, head_hash=heads, rows_verified=verified
            )
