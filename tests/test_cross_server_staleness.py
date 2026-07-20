"""Cross-server integration: a grade change in evidence-ledger marks dependent ach-engine cells stale, and
score_matrix refuses until they are re-rated. Uses one shared, deterministic clock across both servers."""

from __future__ import annotations

import sqlite3

import pytest

from mcp_servers.ach_engine.store import ACHError, ACHStore
from mcp_servers.evidence_ledger.store import EvidenceStore
from mcp_servers.staleness import StalenessStore


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        self.t += 1.0
        return self.t


def test_grade_change_blocks_scoring_until_rerated(tmp_path):
    clk = Clock()
    st = StalenessStore(str(tmp_path / "stale.db"), clock=clk)
    ev = EvidenceStore(str(tmp_path / "ev.db"), st, analyst_id="t")
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        e = ev.add_evidence("c", "x", "src", "report", False, "analyst_typed")
        ev.grade_evidence(e.evidence_id, "B", "2", "d", "analyst_confirmed")  # clk->1 (stale ts=1)

        ref = ach.create_matrix("c", ["H1", "H2"])
        h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
        ach.rate_cell(
            ref.matrix_id, e.evidence_id, h1, "I", "strong", "analyst_confirmed"
        )  # clk->2
        ach.rate_cell(ref.matrix_id, e.evidence_id, h2, "C", "weak", "analyst_confirmed")  # clk->3
        assert ach.score_matrix(ref.matrix_id).leading is not None  # rated after the grade -> fresh

        # grade changes -> stale mark (clk->4) is now AFTER the cells' rated_ts (2,3)
        ev.update_grade(e.evidence_id, "D", "4", "d", "downgraded", "analyst_confirmed")
        with pytest.raises(ACHError, match="stale"):
            ach.score_matrix(ref.matrix_id)
        assert any(
            c.stale for c in ach.get_matrix(ref.matrix_id).cells
        )  # best-effort read reflects it

        # re-rate (clk->5,6 > 4) clears staleness; scoring resumes
        ach.rate_cell(
            ref.matrix_id, e.evidence_id, h1, "I", "strong", "analyst_confirmed", reason="re-rate"
        )
        ach.rate_cell(
            ref.matrix_id, e.evidence_id, h2, "C", "weak", "analyst_confirmed", reason="re-rate"
        )
        assert ach.score_matrix(ref.matrix_id).leading is not None
    finally:
        ach.close()
        ev.close()
        st.close()


def test_score_refuses_ungraded_evidence(tmp_path):
    """collect-then-grade (finding B): evidence whose out-of-band grade is not analyst_confirmed cannot
    be scored — an ingested/ungraded artifact never reaches scored output. The score-time gate is
    exercised via a later downgrade; M4 additionally blocks the analyst_confirmed rating up front (see
    test_rate_confirmed_requires_out_of_band_grade)."""
    clk = Clock()
    st = StalenessStore(str(tmp_path / "stale.db"), clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1", "H2"])
        h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
        st.mark_graded("E1", "analyst_confirmed")  # out-of-band confirmation (M4 precondition)
        # MF1: rate E1 against BOTH hypotheses — a full-coverage matrix is required before scoring, so
        # the score-time grade gate below is exercised on its own merit, not on a coverage gap.
        ach.rate_cell(ref.matrix_id, "E1", h1, "I", "strong", "analyst_confirmed")
        ach.rate_cell(ref.matrix_id, "E1", h2, "C", "weak", "analyst_confirmed")
        assert ach.score_matrix(ref.matrix_id).leading is not None
        st.mark_graded(
            "E1", "model_draft"
        )  # downgraded (latest signal wins) -> score-time gate fires
        with pytest.raises(ACHError, match="not analyst_confirmed-graded"):
            ach.score_matrix(ref.matrix_id)
    finally:
        ach.close()
        st.close()


def test_signals_chain_detects_tamper(tmp_path):
    """grade_signals is the authority score_matrix trusts for collect-then-grade — its chain must be
    integrity-verifiable, or a forged 'analyst_confirmed' defeats finding B silently."""
    st = StalenessStore(str(tmp_path / "stale.db"))
    try:
        st.mark_graded("E1", "analyst_confirmed")
        st.mark_stale("E1", "grade")
        assert st.verify_chain().ok is True
        raw = sqlite3.connect(str(tmp_path / "stale.db"))
        raw.execute("UPDATE grade_signals SET judgment_source='model_draft' WHERE evidence_id='E1'")
        raw.commit()
        raw.close()
        s = st.verify_chain()
        assert s.ok is False and s.mismatch.table == "grade_signals"
    finally:
        st.close()


def test_signals_chain_detects_tail_truncation(tmp_path):
    """MUST-fix: deleting the TRAILING grade_signals row — e.g. erasing a model_draft downgrade so
    latest_grade_source() reverts to the earlier analyst_confirmed — leaves a self-consistent but shorter
    chain. The forward-only row walk alone PASSES it (silently forging the collect-then-grade gate
    score_matrix trusts); the manifest head+count anchor must FAIL it."""
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db)
    try:
        st.mark_graded("E1", "analyst_confirmed")
        st.mark_graded("E1", "model_draft")  # the downgrade an attacker wants to erase
        assert st.latest_grade_source("E1") == "model_draft"
        assert st.verify_chain().ok is True

        raw = sqlite3.connect(db)
        raw.execute("DELETE FROM grade_signals WHERE seq=(SELECT MAX(seq) FROM grade_signals)")
        raw.commit()
        raw.close()

        # the attack succeeds on the DATA — the downgrade is now hidden...
        assert st.latest_grade_source("E1") == "analyst_confirmed"
        # ...but integrity must catch it: the manifest still attests 2 rows / the later head.
        s = st.verify_chain()
        assert s.ok is False and s.mismatch.table == "grade_signals"
    finally:
        st.close()


def test_signals_chain_missing_manifest_fails_closed(tmp_path):
    """A non-empty signal chain with NO manifest file at all (e.g. the file was deleted to erase the
    truncation evidence) must fail closed — a missing manifest is treated as tampering, not a vacuous pass."""
    import os

    db = str(tmp_path / "stale.db")
    st = StalenessStore(db)
    try:
        st.mark_graded("E1", "analyst_confirmed")
        assert st.verify_chain().ok is True
        os.remove(db + ".manifest.jsonl")
        s = st.verify_chain()
        assert s.ok is False and s.mismatch.row_id == "<manifest-missing>"
    finally:
        st.close()


def _tamper_delete_last_grade_signal(db_path: str) -> None:
    raw = sqlite3.connect(db_path)
    raw.execute("DELETE FROM grade_signals WHERE seq=(SELECT MAX(seq) FROM grade_signals)")
    raw.commit()
    raw.close()


def test_score_matrix_rejects_tampered_signal_store(tmp_path):
    """S2: score_matrix reads latest_grade_source straight from the shared staleness store, which is otherwise
    only integrity-checked at process startup. A mid-session tamper of grade_signals must make score_matrix
    REFUSE (it re-verifies the chain on the hot path), not silently trust a forged collect-then-grade gate."""
    clk = Clock()
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db, clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1", "H2"])
        h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
        st.mark_graded("E1", "analyst_confirmed")
        ach.rate_cell(ref.matrix_id, "E1", h1, "I", "strong", "analyst_confirmed")
        ach.rate_cell(ref.matrix_id, "E1", h2, "C", "weak", "analyst_confirmed")
        assert ach.score_matrix(ref.matrix_id).leading is not None  # healthy signal store -> scores

        _tamper_delete_last_grade_signal(db)  # forge the gate by erasing the grade signal
        with pytest.raises(ACHError, match="integrity check"):
            ach.score_matrix(ref.matrix_id)
    finally:
        ach.close()
        st.close()


def test_rate_cell_confirmed_rejects_tampered_signal_store(tmp_path):
    """S2: rate_cell(analyst_confirmed) also leans on the shared grade signal; a tampered signal store must
    make it refuse up front rather than record a rating backed by a possibly-forged grade."""
    clk = Clock()
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db, clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1"])
        h1 = ref.hypotheses[0].hypothesis_id
        st.mark_graded("E1", "analyst_confirmed")
        _tamper_delete_last_grade_signal(db)
        with pytest.raises(ACHError, match="integrity check"):
            ach.rate_cell(ref.matrix_id, "E1", h1, "I", "strong", "analyst_confirmed")
    finally:
        ach.close()
        st.close()


def test_get_matrix_surfaces_supersede_history(tmp_path):
    """M5: get_matrix is the human gate before score_matrix, so it must reveal a confirm-then-re-rate — the
    effective cell's `superseded` flag + its `reason` — not only the final effective values."""
    clk = Clock()
    st = StalenessStore(str(tmp_path / "stale.db"), clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1"])
        h1 = ref.hypotheses[0].hypothesis_id
        st.mark_graded("E1", "analyst_confirmed")
        ach.rate_cell(ref.matrix_id, "E1", h1, "C", "weak", "analyst_confirmed")
        first = {(c.evidence_id, c.hypothesis_id): c for c in ach.get_matrix(ref.matrix_id).cells}[
            ("E1", h1)
        ]
        assert first.superseded is False and first.reason == ""  # a single rating, not re-rated

        # re-rate the SAME cell (a confirm-then-re-rate) with a reason
        ach.rate_cell(
            ref.matrix_id, "E1", h1, "I", "strong", "analyst_confirmed", reason="new read"
        )
        eff = {(c.evidence_id, c.hypothesis_id): c for c in ach.get_matrix(ref.matrix_id).cells}[
            ("E1", h1)
        ]
        assert eff.superseded is True and eff.reason == "new read"  # the re-rate is now visible
        assert eff.consistency == "I"  # and the effective value is the latest rating
    finally:
        ach.close()
        st.close()


def test_get_matrix_reports_signal_store_health(tmp_path):
    """S4: get_matrix is the human gate, and its `stale` display reads the shared staleness store. A tampered
    store must surface signals_ok=False so a reviewing analyst does not trust a possibly-forged `stale` flag."""
    clk = Clock()
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db, clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1"])
        h1 = ref.hypotheses[0].hypothesis_id
        st.mark_graded("E1", "analyst_confirmed")
        ach.rate_cell(ref.matrix_id, "E1", h1, "C", "weak", "analyst_confirmed")
        assert ach.get_matrix(ref.matrix_id).signals_ok is True  # healthy store

        _tamper_delete_last_grade_signal(db)
        assert (
            ach.get_matrix(ref.matrix_id).signals_ok is False
        )  # tamper surfaced, not silently trusted
    finally:
        ach.close()
        st.close()
