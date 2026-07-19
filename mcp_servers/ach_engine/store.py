"""SQLite append-only + hash-chained store for ach-engine (design v3, Server 3).

Ranking is computed strictly by least-total-inconsistency (decision #6). Cell staleness lives in the shared
staleness.db (never a mutable column on `cells`), computed by read-time comparison; score_matrix REFUSES on
any stale or model_draft cell, enumerating the blockers.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable
from typing import cast

from ..common import GENESIS, ChainMismatch, ChainStatus, Manifest, now_iso, row_hash
from ..staleness import StalenessStore
from .models import (
    Cell,
    CellRecord,
    Consistency,
    HypothesisItem,
    JudgmentSource,
    Matrix,
    MatrixList,
    MatrixRef,
    RankItem,
    Ranking,
    Strength,
)

_TABLES = ("matrices", "hypotheses", "cells")

# SF7: the store enforces these domains itself — not only the tool-boundary pydantic Literal — so a
# direct store caller (tests, scripts, another transport) cannot write out-of-domain values into the
# hash-chained payload.
_CONSISTENCY = ("C", "I", "N/A")
_STRENGTH = ("strong", "weak")
_JUDGMENT_SOURCE = ("analyst_confirmed", "model_draft")

# S5: store-layer length caps (defense-in-depth; mirrors calibration_tracker's store-layer caps and the
# tool-boundary caps in server.py). The tables are append-only with NO reclamation, so a single direct-store
# call (test/script/other transport that bypasses the pydantic Field caps) must not be able to inflate the
# hash-chained store without limit — a cheap DoS on DB size + verify_chain's full-table scan.
_MAX_ID = 512
_MAX_TEXT = 10_000


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
        # M6: check_same_thread=False mirrors StalenessStore/EvidenceStore — FastMCP may dispatch a
        # tool body on a worker thread; the sqlite3 default (True) would raise ProgrammingError. All
        # writes are serialized through self._write_lock to preserve single-writer discipline.
        # RLock (not Lock) mirrors the sibling stores and is reentrant, so verify_chain taking the lock
        # around its whole body cannot deadlock a future caller that already holds it (nest-safe).
        self._write_lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
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
        self._restrict_perms()
        # M-manifest: the shared external tamper-evidence anchor (per-table head + monotonic append count),
        # read once at open so appends after a restart continue the self-chain.
        self._manifest = Manifest(self.manifest_path, _TABLES)

    def _restrict_perms(self) -> None:
        # MF5/N8: the unkeyed SHA-256 chain's tamper-evidence rests on OS file isolation — keep the
        # DB (and its WAL sidecars + manifest) private to the owning user so no other local principal
        # can rewrite-and-rehash the chain. Best-effort: a managed FS may forbid chmod.
        if self.db_path == ":memory:":
            return
        for path in (self.db_path, self.db_path + "-wal", self.db_path + "-shm", self.manifest_path):
            if path and os.path.exists(path):
                try:
                    os.chmod(path, 0o600)
                except OSError:
                    pass

    def close(self) -> None:
        self._conn.close()

    def _head(self, table: str) -> str:
        # S2: explicit guard (not assert — assertions are stripped under python -O, which would
        # re-open f-string identifier interpolation below).
        if table not in _TABLES:
            raise ValueError(f"unknown table: {table}")
        r = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - internal literal
        ).fetchone()
        return r["row_hash"] if r else GENESIS

    def seed_manifest_baseline(self) -> int:
        """One-time migration for a DB predating the manifest — attest current per-table (head, count).
        Trust-on-first-use; no-op if a manifest already exists. Returns entries written."""
        with self._write_lock:
            heads = {t: self._head(t) for t in _TABLES}
            counts = {
                t: self._conn.execute(
                    f"SELECT COUNT(*) c FROM {t}"  # noqa: S608 - internal literal from _TABLES
                ).fetchone()["c"]
                for t in _TABLES
            }
            return self._manifest.seed(heads, counts)

    # ---- matrix / hypotheses ----------------------------------------------
    def create_matrix(self, case_id: str, hypotheses: list[str]) -> MatrixRef:
        if not case_id or not case_id.strip():  # SF9: a blank case_id groups matrices outside any real case
            raise ACHError("create_matrix requires a non-empty case_id.")
        if len(case_id) > _MAX_ID:  # S5: store-layer length cap (defense-in-depth), mirrors rate_cell's evidence_id
            raise ACHError(f"case_id exceeds max length {_MAX_ID}.")
        if not hypotheses:
            raise ACHError("create_matrix requires a non-empty hypothesis set.")
        matrix_id = uuid.uuid4().hex
        payload = {"matrix_id": matrix_id, "case_id": case_id}
        # M1 (TOCTOU): read the chain head + compute row_hash INSIDE the write lock, immediately before the
        # INSERT (mirrors _insert_hypothesis). If the head is read outside the lock, two concurrent writers can
        # hash against the same stale head and fork the append-only chain — verify_chain then reports a false
        # tamper on ordinary non-adversarial concurrency.
        with self._write_lock:
            prev = self._head("matrices")
            rh = row_hash(prev, payload)
            # M3: single transaction (commit or rollback atomically); manifest is written only AFTER the
            # commit succeeds, so it can never record a row that was not durably committed.
            appends: list[tuple[str, str]] = [("matrices", rh)]
            with self._conn:
                self._conn.execute(
                    "INSERT INTO matrices(matrix_id, case_id, prev_hash, row_hash) VALUES(?,?,?,?)",
                    (matrix_id, case_id, prev, rh),
                )
                for text in hypotheses:
                    _, h_rh = self._insert_hypothesis(matrix_id, text)
                    appends.append(("hypotheses", h_rh))
            for table, head in appends:
                self._manifest.append(table, head)
        return self.get_matrix_ref(matrix_id)

    def _insert_hypothesis(self, matrix_id: str, text: str) -> tuple[str, str]:
        """Insert one hypothesis row (no commit / no manifest — the caller owns the transaction)."""
        if not text or not text.strip():  # S3: reject empty/whitespace hypothesis text
            raise ACHError("hypothesis text must be non-empty.")
        if len(text) > _MAX_TEXT:  # S5: bound every string that lands in the append-only chain (DoS)
            raise ACHError(f"hypothesis text exceeds max length {_MAX_TEXT}.")
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
        return hid, rh

    def add_hypothesis(self, matrix_id: str, hypothesis: str) -> MatrixRef:
        self._matrix_row(matrix_id)
        with self._write_lock:
            with self._conn:
                _, rh = self._insert_hypothesis(matrix_id, hypothesis)
            self._manifest.append("hypotheses", rh)  # M3: after commit
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
        self,
        matrix_id: str,
        evidence_id: str,
        hypothesis_id: str,
        consistency: str,
        strength: str,
        judgment_source: str,
        reason: str = "",
    ) -> CellRecord:
        if not evidence_id or not evidence_id.strip():  # S3: reject blank evidence_id
            raise ACHError("evidence_id must be non-empty.")
        # S5: store-layer length caps on the caller-controlled strings that persist into the append-only,
        # no-reclamation cells row (evidence_id + reason) — independent of the tool-boundary pydantic caps.
        if len(evidence_id) > _MAX_ID:
            raise ACHError(f"evidence_id exceeds max length {_MAX_ID}.")
        if len(reason) > _MAX_TEXT:
            raise ACHError(f"reason exceeds max length {_MAX_TEXT}.")
        # SF7: enforce the value domains in the store, independent of the tool-boundary pydantic Literal.
        if consistency not in _CONSISTENCY:
            raise ACHError(f"consistency must be one of {_CONSISTENCY}, got {consistency!r}.")
        if strength not in _STRENGTH:
            raise ACHError(f"strength must be one of {_STRENGTH}, got {strength!r}.")
        if judgment_source not in _JUDGMENT_SOURCE:
            raise ACHError(f"judgment_source must be one of {_JUDGMENT_SOURCE}, got {judgment_source!r}.")
        self._matrix_row(matrix_id)
        hyp = self._conn.execute(
            "SELECT 1 FROM hypotheses WHERE hypothesis_id=? AND matrix_id=?", (hypothesis_id, matrix_id)
        ).fetchone()
        if not hyp:
            raise ACHError(f"unknown hypothesis_id for this matrix: {hypothesis_id}")
        # M4: `analyst_confirmed` is not a claim the caller can self-attest from thin air. A cell may
        # only carry it when the evidence it rates already holds an out-of-band `analyst_confirmed`
        # grade signal (written by evidence-ledger, a separate actor) — the "grade_signals-style
        # cross-store signal" that ties confirmation to a human action rather than the calling agent.
        # An agent's own draft must be recorded as `model_draft` (and is blocked by score_matrix until
        # re-rated). Residual A (reviewed → owner decision): the per-evidence signal does not bind a *specific*
        # rating — a confirm-then-re-rate, or a new cell reusing the same confirmed evidence, is accepted. This
        # is EVIDENCE-anchored, not per-rating, confirmation; it is disclosed as such in the rate_cell /
        # score_matrix tool docs, and the HUMAN GATE (review get_matrix before score_matrix) is the control. A
        # per-cell confirm token was considered and DEFERRED: over stdio it stays caller-asserted, so it would
        # add auditability, not true verification (same honest limit as judgment_source / the calibration horizon).
        if (
            judgment_source == "analyst_confirmed"
            and self.staleness.latest_grade_source(evidence_id) != "analyst_confirmed"
        ):
            raise ACHError(
                "cannot record an analyst_confirmed cell rating for evidence that is not itself "
                "analyst_confirmed-graded in evidence-ledger (out-of-band confirmation required): "
                "grade the evidence first, or record this rating as model_draft."
            )
        rated_at = now_iso()
        rated_ts = self._clock()
        # M1: rated_ts is in the hashed payload — it drives _cell_stale and the score_matrix staleness
        # blocker, so a raw UPDATE of it must break verify_chain, not sail through with ok=True.
        payload = {
            "matrix_id": matrix_id, "evidence_id": evidence_id, "hypothesis_id": hypothesis_id,
            "consistency": consistency, "strength": strength, "analyst_id": self.analyst_id,
            "judgment_source": judgment_source, "reason": reason, "rated_at": rated_at,
            "rated_ts": rated_ts,
        }
        with self._write_lock:
            # M1 (TOCTOU): the supersede decision (does a prior EFFECTIVE cell exist?), the
            # reason-required-when-superseding check, and the head-read + row_hash + INSERT MUST all be one
            # atomic critical section — mirrors evidence-ledger _insert_grade. Reading _effective_cell OUTSIDE
            # the lock is a TOCTOU: two concurrent rate_cell calls could both observe "no prior", both skip the
            # reason requirement, and the returned superseded flag could disagree with the committed order.
            prior = self._effective_cell(matrix_id, evidence_id, hypothesis_id)
            if prior is not None and not reason.strip():
                raise ACHError("reason is required when superseding an existing cell rating.")
            # M5: compute the correction flag in-lock from the same read that gated the reason requirement.
            superseded = prior is not None
            prev = self._head("cells")
            rh = row_hash(prev, payload)
            with self._conn:  # M3: atomic commit-or-rollback
                self._conn.execute(
                    "INSERT INTO cells(matrix_id, evidence_id, hypothesis_id, consistency, strength, analyst_id, "
                    "judgment_source, reason, rated_at, rated_ts, prev_hash, row_hash) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        matrix_id, evidence_id, hypothesis_id, consistency, strength, self.analyst_id,
                        judgment_source, reason, rated_at, rated_ts, prev, rh,
                    ),
                )
            self._manifest.append("cells", rh)  # after commit
        return CellRecord(
            matrix_id=matrix_id, evidence_id=evidence_id, hypothesis_id=hypothesis_id,
            # domains are enforced above (raise on out-of-domain), so these casts are sound, not blind.
            consistency=cast(Consistency, consistency), strength=cast(Strength, strength),
            judgment_source=cast(JudgmentSource, judgment_source), reason=reason, rated_at=rated_at,
            # M5: report the truth — a rating that supersedes a prior effective cell is a correction.
            superseded=superseded, row_hash=rh,
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
        hyps = self._hypotheses(matrix_id)
        blockers: list[str] = []

        # MF1: a hypothesis with an absent cell must never be ranked. An unrated (evidence × hypothesis)
        # pair — e.g. a hypothesis just added via add_hypothesis before existing evidence was re-rated
        # against it — would otherwise score 0/0 and win the least-inconsistency sort over every
        # genuinely-evaluated hypothesis (the exact ACH failure this server exists to prevent). Require
        # full coverage: every evidence item in the matrix must be rated against every hypothesis.
        evidence_ids = sorted({c["evidence_id"] for c in eff})
        if not evidence_ids:
            raise ACHError("cannot score — no cells have been rated yet.")
        rated_pairs = {(c["evidence_id"], c["hypothesis_id"]) for c in eff}
        for h in hyps:
            for ev in evidence_ids:
                if (ev, h.hypothesis_id) not in rated_pairs:
                    blockers.append(
                        f"({ev}, {h.hypothesis_id}) not rated: every evidence item must be rated against "
                        "every hypothesis before scoring (coverage gap)"
                    )

        for c in eff:
            # collect-then-grade (decision #8): the EVIDENCE must carry an effective analyst_confirmed grade
            # in evidence-ledger before any of its cells may be scored — an ingested/ungraded artifact can never
            # reach scored output regardless of the cell rating's own judgment_source.
            grade_src = self.staleness.latest_grade_source(c["evidence_id"])
            if grade_src != "analyst_confirmed":
                # S4: distinguish "never registered (likely a typo)" from "registered but not
                # analyst_confirmed" so the remediation is correct for each case.
                detail = (
                    "no grade signal at all — check the evidence_id for a typo and register/grade it "
                    "in evidence-ledger"
                    if grade_src is None
                    else f"currently graded '{grade_src}' — analyst_confirm it in evidence-ledger"
                )
                blockers.append(
                    f"({c['evidence_id']}, {c['hypothesis_id']}) evidence not analyst_confirmed-graded: {detail}"
                )
            elif self._cell_stale(c):
                blockers.append(f"({c['evidence_id']}, {c['hypothesis_id']}) stale: re-rate after grade change")
            elif c["judgment_source"] == "model_draft":
                blockers.append(f"({c['evidence_id']}, {c['hypothesis_id']}) model_draft: confirm before scoring")
        if blockers:
            raise ACHError("cannot score — resolve these cells first: " + "; ".join(blockers))

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
        try:  # S1: a malformed cursor is a caller error (ACHError), not an uncaught ValueError
            after = int(cursor) if cursor else 0
        except (TypeError, ValueError) as e:
            raise ACHError(f"invalid cursor: {cursor!r}") from e
        rows = self._conn.execute(
            "SELECT matrix_id, seq FROM matrices WHERE case_id=? AND seq>? ORDER BY seq ASC LIMIT ?",
            (case_id, after, limit + 1),
        ).fetchall()
        items = [self.get_matrix_ref(r["matrix_id"]) for r in rows[:limit]]
        next_cursor = str(rows[limit - 1]["seq"]) if len(rows) > limit else None
        return MatrixList(items=items, next_cursor=next_cursor)

    # ---- integrity ---------------------------------------------------------
    def verify_chain(self) -> ChainStatus:
        # MF4: integrity is table-wide and ALWAYS GLOBAL — there is no per-case scope. The prior
        # `case_id` param was echoed into `scope` but never filtered any row (the whole DB was always
        # walked), advertising a filter that did nothing; siblings dropped it for the same reason.
        # M2/lock: hold the write lock for the whole read+manifest walk (mirrors evidence-ledger). Every
        # writer holds _write_lock across its commit -> manifest-append; without it here a verify interleaved
        # with an in-flight write could read a row committed-but-not-yet-manifest-attested and report a
        # spurious tamper on a healthy store. RLock is reentrant, so a caller already holding it won't deadlock.
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
                    payload = self._payload_for(table, r)
                    expected = row_hash(prev, payload)
                    if expected != r["row_hash"] or r["prev_hash"] != prev:
                        return ChainStatus(
                            server="ach-engine", scope="all", ok=False, head_hash=heads,
                            rows_verified=verified,
                            mismatch=ChainMismatch(
                                table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                            ),
                        )
                    prev = r["row_hash"]
                    count += 1
                    verified += 1
                heads[table] = prev
                counts[table] = count

            # M2/M-manifest: delegate head+count reconciliation + the manifest self-chain walk to the shared
            # helper (catches trailing-row truncation and a non-terminal manifest-line edit).
            ok, mm = self._manifest.check(heads, counts)
            if not ok and mm is not None:
                return ChainStatus(
                    server="ach-engine", scope="all", ok=False, head_hash=heads, rows_verified=verified,
                    mismatch=ChainMismatch(
                        table=mm.table, row_id=mm.row_id, expected_hash=mm.expected_hash, got_hash=mm.got_hash
                    ),
                )
            return ChainStatus(
                server="ach-engine", scope="all", ok=True, head_hash=heads, rows_verified=verified
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
            "rated_ts": r["rated_ts"],  # M1: rated_ts feeds staleness logic, so it must be in the hash
        }
