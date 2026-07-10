"""SQLite append-only + hash-chained store for evidence-ledger (design v3, Server 2)."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid

from ..common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash
from ..staleness import StalenessStore
from .models import (
    RELIABILITY_ORDER,
    EvidenceList,
    EvidenceRecord,
    EvidenceRef,
    Grade,
    SourceHistory,
)

_TABLES = ("evidence", "grades")


class EvidenceError(Exception):
    """Business-rule violation; the server wraps this as a FastMCP ToolError."""


class EvidenceStore:
    def __init__(self, db_path: str, staleness: StalenessStore, analyst_id: str | None = None):
        self.db_path = db_path
        self.staleness = staleness
        self.analyst_id = analyst_id or os.environ.get("EVIDENCE_ANALYST_ID", "local-analyst")
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL, item TEXT NOT NULL,
                source_id TEXT NOT NULL, evidence_type TEXT NOT NULL, source_channel TEXT NOT NULL,
                expected_observables TEXT NOT NULL DEFAULT '{}', pii INTEGER NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS grades(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL, reliability TEXT NOT NULL, credibility TEXT NOT NULL,
                diagnosticity TEXT NOT NULL, analyst_id TEXT NOT NULL, judgment_source TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '', graded_at TEXT NOT NULL,
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

    def _append_manifest(self, table: str, head: str) -> None:
        if not self.manifest_path:
            return
        with open(self.manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"table": table, "head": head, "at": now_iso()}) + "\n")

    # ---- evidence ----------------------------------------------------------
    def add_evidence(
        self,
        case_id: str,
        item: str,
        source_id: str,
        evidence_type: str,
        pii: bool,
        source_channel: str,
        expected_observables: dict[str, str] | None = None,
    ) -> EvidenceRef:
        expected_observables = expected_observables or {}
        evidence_id = uuid.uuid4().hex
        payload = {
            "evidence_id": evidence_id, "case_id": case_id, "item": item, "source_id": source_id,
            "evidence_type": evidence_type, "source_channel": source_channel,
            "expected_observables": expected_observables, "pii": bool(pii),
        }
        prev = self._head("evidence")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO evidence(evidence_id, case_id, item, source_id, evidence_type, source_channel, "
            "expected_observables, pii, prev_hash, row_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                evidence_id, case_id, item, source_id, evidence_type, source_channel,
                json.dumps(expected_observables, sort_keys=True), int(bool(pii)), prev, rh,
            ),
        )
        self._conn.commit()
        self._append_manifest("evidence", rh)
        return EvidenceRef(evidence_id=evidence_id, case_id=case_id, pii=bool(pii))

    def _evidence_row(self, evidence_id: str) -> sqlite3.Row:
        r = self._conn.execute("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
        if not r:
            raise EvidenceError(f"unknown evidence_id: {evidence_id}")
        return r

    def _effective_grade(self, evidence_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM grades WHERE evidence_id=? ORDER BY seq DESC LIMIT 1", (evidence_id,)
        ).fetchone()

    def _insert_grade(
        self, evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, reason
    ) -> None:
        graded_at = now_iso()
        payload = {
            "evidence_id": evidence_id, "reliability": reliability, "credibility": credibility,
            "diagnosticity": diagnosticity, "analyst_id": self.analyst_id, "judgment_source": judgment_source,
            "rationale": rationale, "reason": reason, "graded_at": graded_at,
        }
        prev = self._head("grades")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO grades(evidence_id, reliability, credibility, diagnosticity, analyst_id, "
            "judgment_source, rationale, reason, graded_at, prev_hash, row_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                evidence_id, reliability, credibility, diagnosticity, self.analyst_id, judgment_source,
                rationale, reason, graded_at, prev, rh,
            ),
        )
        self._conn.commit()
        self._append_manifest("grades", rh)
        # cross-server: a (re)grade marks dependent ACH cells stale.
        self.staleness.mark_stale(evidence_id, "grade")

    def grade_evidence(
        self, evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale=""
    ) -> EvidenceRecord:
        self._evidence_row(evidence_id)
        if self._effective_grade(evidence_id) is not None:
            raise EvidenceError("a grade already exists for this evidence — use update_grade to supersede.")
        self._insert_grade(evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, "")
        return self.get_evidence(evidence_id, redact_pii=True)

    def update_grade(
        self, evidence_id, reliability, credibility, diagnosticity, reason, judgment_source, rationale=""
    ) -> EvidenceRecord:
        self._evidence_row(evidence_id)
        if self._effective_grade(evidence_id) is None:
            raise EvidenceError("no prior grade exists for this evidence — use grade_evidence first.")
        if not reason.strip():
            raise EvidenceError("update_grade requires a non-empty reason (a superseding correction).")
        self._insert_grade(
            evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, reason
        )
        return self.get_evidence(evidence_id, redact_pii=True)

    def get_evidence(self, evidence_id: str, redact_pii: bool = True) -> EvidenceRecord:
        r = self._evidence_row(evidence_id)
        grade_rows = self._conn.execute(
            "SELECT * FROM grades WHERE evidence_id=? ORDER BY seq ASC", (evidence_id,)
        ).fetchall()
        grades: list[Grade] = []
        n = len(grade_rows)
        for i, g in enumerate(grade_rows):
            grades.append(
                Grade(
                    reliability=g["reliability"], credibility=g["credibility"], diagnosticity=g["diagnosticity"],
                    judgment_source=g["judgment_source"], rationale=g["rationale"], reason=g["reason"],
                    graded_at=g["graded_at"], superseded=(i < n - 1),
                )
            )
        item = "REDACTED" if (r["pii"] and redact_pii) else r["item"]
        return EvidenceRecord(
            evidence_id=r["evidence_id"], case_id=r["case_id"], item=item, source_id=r["source_id"],
            evidence_type=r["evidence_type"], source_channel=r["source_channel"],
            expected_observables=json.loads(r["expected_observables"]), grades=grades,
            pii=bool(r["pii"]), row_hash=r["row_hash"],
        )

    def list_evidence(
        self, case_id: str, redact_pii: bool = True, limit: int = 100, cursor: str | None = None
    ) -> EvidenceList:
        limit = max(1, min(limit, 1000))
        after = int(cursor) if cursor else 0
        rows = self._conn.execute(
            "SELECT evidence_id, seq FROM evidence WHERE case_id=? AND seq>? ORDER BY seq ASC LIMIT ?",
            (case_id, after, limit + 1),
        ).fetchall()
        items = [self.get_evidence(r["evidence_id"], redact_pii) for r in rows[:limit]]
        next_cursor = str(rows[limit - 1]["seq"]) if len(rows) > limit else None
        return EvidenceList(items=items, next_cursor=next_cursor)

    def get_source_history(self, source_id: str, redact_pii: bool = True) -> SourceHistory:
        ev_rows = self._conn.execute(
            "SELECT evidence_id, case_id, seq FROM evidence WHERE source_id=? ORDER BY seq ASC", (source_id,)
        ).fetchall()
        seq_items: list[tuple[int, str, str]] = []  # (grade_seq, reliability, case_id)
        n_draft = 0
        cases: list[str] = []
        for ev in ev_rows:
            eff = self._effective_grade(ev["evidence_id"])
            if eff is None:
                continue
            if ev["case_id"] not in cases:
                cases.append(ev["case_id"])
            if eff["judgment_source"] == "analyst_confirmed":
                seq_items.append((eff["seq"], eff["reliability"], ev["case_id"]))
            else:
                n_draft += 1
        seq_items.sort(key=lambda t: t[0])
        grade_sequence = [r for _, r, _ in seq_items]
        direction = "n/a"
        if len(grade_sequence) >= 2:
            a, b = RELIABILITY_ORDER[grade_sequence[-2]], RELIABILITY_ORDER[grade_sequence[-1]]
            direction = "improved" if b < a else ("worsened" if b > a else "same")
        return SourceHistory(
            source_id=source_id, cases=cases, grade_sequence=grade_sequence, last_change_direction=direction,
            n=len(grade_sequence), n_model_draft_excluded=n_draft,
        )

    # ---- integrity ---------------------------------------------------------
    def verify_chain(self, case_id: str | None = None) -> ChainStatus:
        heads: dict[str, str] = {}
        verified = 0
        for table in _TABLES:
            prev = GENESIS
            rows = self._conn.execute(
                f"SELECT * FROM {table} ORDER BY seq ASC"  # noqa: S608 - internal literal
            ).fetchall()
            for r in rows:
                payload = self._payload_for(table, r)
                expected = row_hash(prev, payload)
                if expected != r["row_hash"] or r["prev_hash"] != prev:
                    return ChainStatus(
                        server="evidence-ledger", scope=case_id or "all", ok=False, head_hash=heads,
                        rows_verified=verified,
                        mismatch=ChainMismatch(
                            table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                        ),
                    )
                prev = r["row_hash"]
                verified += 1
            heads[table] = prev
        return ChainStatus(
            server="evidence-ledger", scope=case_id or "all", ok=True, head_hash=heads, rows_verified=verified
        )

    def _payload_for(self, table: str, r: sqlite3.Row) -> dict:
        if table == "evidence":
            return {
                "evidence_id": r["evidence_id"], "case_id": r["case_id"], "item": r["item"],
                "source_id": r["source_id"], "evidence_type": r["evidence_type"],
                "source_channel": r["source_channel"],
                "expected_observables": json.loads(r["expected_observables"]), "pii": bool(r["pii"]),
            }
        return {
            "evidence_id": r["evidence_id"], "reliability": r["reliability"], "credibility": r["credibility"],
            "diagnosticity": r["diagnosticity"], "analyst_id": r["analyst_id"],
            "judgment_source": r["judgment_source"], "rationale": r["rationale"], "reason": r["reason"],
            "graded_at": r["graded_at"],
        }
