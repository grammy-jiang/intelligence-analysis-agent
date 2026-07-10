"""SQLite append-only + hash-chained store for ach-engine (design v3, Server 3).

Ranking is computed strictly by least-total-inconsistency (decision #6). Cell staleness lives in the shared
staleness.db (never a mutable column on `cells`), computed by read-time comparison; score_matrix REFUSES on
any stale or model_draft cell, enumerating the blockers.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from collections.abc import Callable

from ..common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash
from ..staleness import StalenessStore
from .models import (
    Cell,
    CellRecord,
    HypothesisItem,
    Matrix,
    MatrixList,
    MatrixRef,
    RankItem,
    Ranking,
)

_TABLES = ("matrices", "hypotheses", "cells")


class ACHError(Exception):
    """Business-rule violation; the server wraps this as a FastMCP ToolError."""


class ACHStore:
    def __init__(
        self,
        db_path: str,
        staleness: StalenessStore,
        analyst_id: str | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.db_path = db_path
        self.staleness = staleness
        self._clock = clock
        self.analyst_id = analyst_id or os.environ.get("ACH_ANALYST_ID", "local-analyst")
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS matrices(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                matrix_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL, prev_hash TEXT NOT NULL,
                row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS hypotheses(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis_id TEXT UNIQUE NOT NULL, matrix_id TEXT NOT NULL, text TEXT NOT NULL,
                added_at TEXT NOT NULL, prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cells(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                matrix_id TEXT NOT NULL, evidence_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL,
                consistency TEXT NOT NULL, strength TEXT NOT NULL, analyst_id TEXT NOT NULL,
                judgment_source TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', rated_at TEXT NOT NULL,
                rated_ts REAL NOT NULL, prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
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

    # ---- matrix / hypotheses ----------------------------------------------
    def create_matrix(self, case_id: str, hypotheses: list[str]) -> MatrixRef:
        if not hypotheses:
            raise ACHError("create_matrix requires a non-empty hypothesis set.")
        matrix_id = uuid.uuid4().hex
        payload = {"matrix_id": matrix_id, "case_id": case_id}
        prev = self._head("matrices")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO matrices(matrix_id, case_id, prev_hash, row_hash) VALUES(?,?,?,?)",
            (matrix_id, case_id, prev, rh),
        )
        self._append_manifest("matrices", rh)
        for text in hypotheses:
            self._insert_hypothesis(matrix_id, text)
        self._conn.commit()
        return self.get_matrix_ref(matrix_id)

    def _insert_hypothesis(self, matrix_id: str, text: str) -> str:
        hid = "h_" + uuid.uuid4().hex[:12]
        added_at = now_iso()
        payload = {"hypothesis_id": hid, "matrix_id": matrix_id, "text": text, "added_at": added_at}
        prev = self._head("hypotheses")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO hypotheses(hypothesis_id, matrix_id, text, added_at, prev_hash, row_hash) "
            "VALUES(?,?,?,?,?,?)",
            (hid, matrix_id, text, added_at, prev, rh),
        )
        self._append_manifest("hypotheses", rh)
        return hid

    def add_hypothesis(self, matrix_id: str, hypothesis: str) -> MatrixRef:
        self._matrix_row(matrix_id)
        self._insert_hypothesis(matrix_id, hypothesis)
        self._conn.commit()
        return self.get_matrix_ref(matrix_id)

    def _matrix_row(self, matrix_id: str) -> sqlite3.Row:
        r = self._conn.execute("SELECT * FROM matrices WHERE matrix_id=?", (matrix_id,)).fetchone()
        if not r:
            raise ACHError(f"unknown matrix_id: {matrix_id}")
        return r

    def _hypotheses(self, matrix_id: str) -> list[HypothesisItem]:
        rows = self._conn.execute(
            "SELECT hypothesis_id, text FROM hypotheses WHERE matrix_id=? ORDER BY seq ASC", (matrix_id,)
        ).fetchall()
        return [HypothesisItem(hypothesis_id=r["hypothesis_id"], text=r["text"]) for r in rows]

    def get_matrix_ref(self, matrix_id: str) -> MatrixRef:
        r = self._matrix_row(matrix_id)
        return MatrixRef(matrix_id=matrix_id, case_id=r["case_id"], hypotheses=self._hypotheses(matrix_id))

    # ---- cells -------------------------------------------------------------
    def _effective_cell(self, matrix_id: str, evidence_id: str, hypothesis_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM cells WHERE matrix_id=? AND evidence_id=? AND hypothesis_id=? ORDER BY seq DESC "
            "LIMIT 1",
            (matrix_id, evidence_id, hypothesis_id),
        ).fetchone()

    def rate_cell(
        self, matrix_id, evidence_id, hypothesis_id, consistency, strength, judgment_source, reason=""
    ) -> CellRecord:
        self._matrix_row(matrix_id)
        hyp = self._conn.execute(
            "SELECT 1 FROM hypotheses WHERE hypothesis_id=? AND matrix_id=?", (hypothesis_id, matrix_id)
        ).fetchone()
        if not hyp:
            raise ACHError(f"unknown hypothesis_id for this matrix: {hypothesis_id}")
        prior = self._effective_cell(matrix_id, evidence_id, hypothesis_id)
        if prior is not None and not reason.strip():
            raise ACHError("reason is required when superseding an existing cell rating.")
        rated_at = now_iso()
        rated_ts = self._clock()
        payload = {
            "matrix_id": matrix_id, "evidence_id": evidence_id, "hypothesis_id": hypothesis_id,
            "consistency": consistency, "strength": strength, "analyst_id": self.analyst_id,
            "judgment_source": judgment_source, "reason": reason, "rated_at": rated_at,
        }
        prev = self._head("cells")
        rh = row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO cells(matrix_id, evidence_id, hypothesis_id, consistency, strength, analyst_id, "
            "judgment_source, reason, rated_at, rated_ts, prev_hash, row_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                matrix_id, evidence_id, hypothesis_id, consistency, strength, self.analyst_id,
                judgment_source, reason, rated_at, rated_ts, prev, rh,
            ),
        )
        self._conn.commit()
        self._append_manifest("cells", rh)
        return CellRecord(
            matrix_id=matrix_id, evidence_id=evidence_id, hypothesis_id=hypothesis_id, consistency=consistency,
            strength=strength, judgment_source=judgment_source, reason=reason, rated_at=rated_at,
            superseded=False, row_hash=rh,
        )

    def _effective_cells(self, matrix_id: str) -> list[sqlite3.Row]:
        rows = self._conn.execute(
            "SELECT * FROM cells WHERE matrix_id=? ORDER BY seq ASC", (matrix_id,)
        ).fetchall()
        eff: dict[tuple[str, str], sqlite3.Row] = {}
        for r in rows:
            eff[(r["evidence_id"], r["hypothesis_id"])] = r  # later seq wins
        return list(eff.values())

    def _cell_stale(self, cell: sqlite3.Row) -> bool:
        ts = self.staleness.latest_stale_ts(cell["evidence_id"])
        return ts is not None and ts > cell["rated_ts"]

    def get_matrix(self, matrix_id: str) -> Matrix:
        r = self._matrix_row(matrix_id)
        cells: list[Cell] = []
        for c in self._effective_cells(matrix_id):
            stale = self._cell_stale(c)  # best-effort; score_matrix is authoritative
            cells.append(
                Cell(
                    evidence_id=c["evidence_id"], hypothesis_id=c["hypothesis_id"], consistency=c["consistency"],
                    strength=c["strength"], judgment_source=c["judgment_source"], stale=stale,
                    stale_reason=(self.staleness.changed_field(c["evidence_id"]) if stale else None),
                    rated_at=c["rated_at"],
                )
            )
        return Matrix(matrix_id=matrix_id, case_id=r["case_id"], hypotheses=self._hypotheses(matrix_id), cells=cells)

    def score_matrix(self, matrix_id: str) -> Ranking:
        self._matrix_row(matrix_id)
        eff = self._effective_cells(matrix_id)
        blockers: list[str] = []
        for c in eff:
            if self._cell_stale(c):
                blockers.append(f"({c['evidence_id']}, {c['hypothesis_id']}) stale: re-rate after grade change")
            elif c["judgment_source"] == "model_draft":
                blockers.append(f"({c['evidence_id']}, {c['hypothesis_id']}) model_draft: confirm before scoring")
        if blockers:
            raise ACHError("cannot score — resolve these cells first: " + "; ".join(blockers))

        hyps = self._hypotheses(matrix_id)
        strong = {h.hypothesis_id: 0 for h in hyps}
        weak = {h.hypothesis_id: 0 for h in hyps}
        by_evidence: dict[str, list[str]] = {}
        for c in eff:
            by_evidence.setdefault(c["evidence_id"], []).append(c["consistency"])
            if c["consistency"] == "I":
                if c["strength"] == "strong":
                    strong[c["hypothesis_id"]] = strong.get(c["hypothesis_id"], 0) + 1
                else:
                    weak[c["hypothesis_id"]] = weak.get(c["hypothesis_id"], 0) + 1
        # non-diagnostic: evidence with no 'I' against any hypothesis (consistent/NA with all → no discrimination)
        non_diagnostic = [ev for ev, cs in by_evidence.items() if "I" not in cs]
        ordered = sorted(
            (RankItem(hypothesis_id=h.hypothesis_id, strong_inconsistencies=strong[h.hypothesis_id],
                      weak_inconsistencies=weak[h.hypothesis_id]) for h in hyps),
            key=lambda ri: (ri.strong_inconsistencies, ri.weak_inconsistencies),
        )
        leading = ordered[0].hypothesis_id if ordered else None
        return Ranking(ordered=ordered, non_diagnostic=non_diagnostic, leading=leading)

    def list_matrices(self, case_id: str, limit: int = 100, cursor: str | None = None) -> MatrixList:
        limit = max(1, min(limit, 1000))
        after = int(cursor) if cursor else 0
        rows = self._conn.execute(
            "SELECT matrix_id, seq FROM matrices WHERE case_id=? AND seq>? ORDER BY seq ASC LIMIT ?",
            (case_id, after, limit + 1),
        ).fetchall()
        items = [self.get_matrix_ref(r["matrix_id"]) for r in rows[:limit]]
        next_cursor = str(rows[limit - 1]["seq"]) if len(rows) > limit else None
        return MatrixList(items=items, next_cursor=next_cursor)

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
                        server="ach-engine", scope=case_id or "all", ok=False, head_hash=heads,
                        rows_verified=verified,
                        mismatch=ChainMismatch(
                            table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                        ),
                    )
                prev = r["row_hash"]
                verified += 1
            heads[table] = prev
        return ChainStatus(
            server="ach-engine", scope=case_id or "all", ok=True, head_hash=heads, rows_verified=verified
        )

    def _payload_for(self, table: str, r: sqlite3.Row) -> dict:
        if table == "matrices":
            return {"matrix_id": r["matrix_id"], "case_id": r["case_id"]}
        if table == "hypotheses":
            return {
                "hypothesis_id": r["hypothesis_id"], "matrix_id": r["matrix_id"], "text": r["text"],
                "added_at": r["added_at"],
            }
        return {
            "matrix_id": r["matrix_id"], "evidence_id": r["evidence_id"], "hypothesis_id": r["hypothesis_id"],
            "consistency": r["consistency"], "strength": r["strength"], "analyst_id": r["analyst_id"],
            "judgment_source": r["judgment_source"], "reason": r["reason"], "rated_at": r["rated_at"],
        }
