"""Shared cross-server staleness store (the narrow coupling between evidence-ledger and ach-engine).

evidence-ledger WRITES stale events when a grade changes; ach-engine READS them at score time. This is a
deliberate, scoped, out-of-protocol side channel (design v3 "DB file topology"): evidence-ledger may write
only the staleness signal here — never ach-engine's core tables. Append-only + hash-chained.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable

from .common import GENESIS, now_iso, row_hash


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
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _head(self) -> str:
        r = self._conn.execute("SELECT row_hash FROM stale_events ORDER BY seq DESC LIMIT 1").fetchone()
        return r["row_hash"] if r else GENESIS

    def mark_stale(self, evidence_id: str, changed_field: str) -> None:
        ts = self._clock()
        payload = {"evidence_id": evidence_id, "changed_field": changed_field, "marked_at": now_iso()}
        prev = self._head()
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO stale_events(evidence_id, changed_field, marked_at, marked_ts, prev_hash, row_hash) "
            "VALUES(?,?,?,?,?,?)",
            (evidence_id, changed_field, payload["marked_at"], ts, prev, rh),
        )
        self._conn.commit()

    def latest_stale_ts(self, evidence_id: str) -> float | None:
        """Fresh read (WAL) of the most recent stale mark for an evidence item, or None."""
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
