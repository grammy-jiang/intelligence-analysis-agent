"""Cross-server integration: a grade change in evidence-ledger marks dependent ach-engine cells stale, and
score_matrix refuses until they are re-rated. Uses one shared, deterministic clock across both servers."""

from __future__ import annotations

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
        ach.rate_cell(ref.matrix_id, e.evidence_id, h1, "I", "strong", "analyst_confirmed")  # clk->2
        ach.rate_cell(ref.matrix_id, e.evidence_id, h2, "C", "weak", "analyst_confirmed")  # clk->3
        assert ach.score_matrix(ref.matrix_id).leading is not None  # rated after the grade -> fresh

        # grade changes -> stale mark (clk->4) is now AFTER the cells' rated_ts (2,3)
        ev.update_grade(e.evidence_id, "D", "4", "d", "downgraded", "analyst_confirmed")
        with pytest.raises(ACHError, match="stale"):
            ach.score_matrix(ref.matrix_id)
        assert any(c.stale for c in ach.get_matrix(ref.matrix_id).cells)  # best-effort read reflects it

        # re-rate (clk->5,6 > 4) clears staleness; scoring resumes
        ach.rate_cell(ref.matrix_id, e.evidence_id, h1, "I", "strong", "analyst_confirmed", reason="re-rate")
        ach.rate_cell(ref.matrix_id, e.evidence_id, h2, "C", "weak", "analyst_confirmed", reason="re-rate")
        assert ach.score_matrix(ref.matrix_id).leading is not None
    finally:
        ach.close()
        ev.close()
        st.close()


def test_score_refuses_ungraded_evidence(tmp_path):
    """collect-then-grade (finding B): evidence rated in ach but never analyst_confirmed-graded in
    evidence-ledger cannot be scored — an ingested/ungraded artifact never reaches scored output."""
    clk = Clock()
    st = StalenessStore(str(tmp_path / "stale.db"), clock=clk)
    ach = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t", clock=clk)
    try:
        ref = ach.create_matrix("c", ["H1", "H2"])
        h1 = ref.hypotheses[0].hypothesis_id
        ach.rate_cell(ref.matrix_id, "E_ungraded", h1, "I", "strong", "analyst_confirmed")
        with pytest.raises(ACHError, match="not analyst_confirmed-graded"):
            ach.score_matrix(ref.matrix_id)
        st.mark_graded("E_ungraded", "analyst_confirmed")  # now graded
        assert ach.score_matrix(ref.matrix_id).leading is not None
        st.mark_graded("E_ungraded", "model_draft")  # downgraded (latest signal wins)
        with pytest.raises(ACHError, match="not analyst_confirmed-graded"):
            ach.score_matrix(ref.matrix_id)
    finally:
        ach.close()
        st.close()
