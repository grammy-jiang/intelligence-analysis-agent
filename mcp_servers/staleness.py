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

import sqlite3
import time
from collections.abc import Callable

from .common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash

_TABLES = ("stale_events", "grade_signals")


class StalenessStore:
    def __init__(self, db_path: str, clock: Callable[[], float] = time.time):
        self.db_path = db_path
        self._clock = clock
        self._conn = sqlite3.connect(db_path)
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

    def close(self) -> None:
        self._conn.close()

    def _head(self, table: str) -> str:
        assert table in _TABLES
        r = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - internal literal
        ).fetchone()
        return r["row_hash"] if r else GENESIS

    # ---- staleness signal --------------------------------------------------
    def mark_stale(self, evidence_id: str, changed_field: str) -> None:
        ts = self._clock()
        payload = {"evidence_id": evidence_id, "changed_field": changed_field, "marked_at": now_iso()}
        prev = self._head("stale_events")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO stale_events(evidence_id, changed_field, marked_at, marked_ts, prev_hash, row_hash) "
            "VALUES(?,?,?,?,?,?)",
            (evidence_id, changed_field, payload["marked_at"], ts, prev, rh),
        )
        self._conn.commit()

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
        prev = self._head("grade_signals")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO grade_signals(evidence_id, judgment_source, marked_at, marked_ts, prev_hash, row_hash) "
            "VALUES(?,?,?,?,?,?)",
            (evidence_id, judgment_source, payload["marked_at"], ts, prev, rh),
        )
        self._conn.commit()

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
        """Verify BOTH signal chains. score_matrix trusts grade_signals for collect-then-grade, so this must be
        checked at startup by every server that opens this file (evidence-ledger AND ach-engine)."""
        heads: dict[str, str] = {}
        verified = 0
        for table in _TABLES:
            prev = GENESIS
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
                verified += 1
            heads[table] = prev
        return ChainStatus(
            server="evidence-signals", scope="all", ok=True, head_hash=heads, rows_verified=verified
        )
