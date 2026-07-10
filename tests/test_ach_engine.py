"""Deterministic fixtures for ach-engine (Server 3), incl. the Iraqi-retaliation golden."""

from __future__ import annotations

import pytest

from mcp_servers.ach_engine.store import ACHError, ACHStore
from mcp_servers.staleness import StalenessStore


@pytest.fixture()
def ach(tmp_path):
    st = StalenessStore(str(tmp_path / "stale.db"))
    s = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t")
    yield s
    s.close()
    st.close()


def _rate(ach, mid, ev, hid, cons, strength="strong", js="analyst_confirmed"):
    return ach.rate_cell(mid, ev, hid, cons, strength, js)


def test_iraqi_golden_h2_leads_by_least_inconsistency(ach):
    ref = ach.create_matrix("iraq", ["H1", "H2", "H3", "H4", "H5"])
    hid = {h.text: h.hypothesis_id for h in ref.hypotheses}
    # consistency matrix from docs/validation/case-workspace.md (all I treated as strong)
    rows = {
        "E1": {"H1": "I", "H2": "C", "H3": "C", "H4": "C", "H5": "C"},
        "E2": {"H1": "C", "H2": "N/A", "H3": "I", "H4": "I", "H5": "C"},
        "E3": {"H1": "I", "H2": "C", "H3": "C", "H4": "C", "H5": "I"},
        "E4": {"H1": "N/A", "H2": "C", "H3": "I", "H4": "C", "H5": "N/A"},
        "E5": {"H1": "I", "H2": "C", "H3": "C", "H4": "C", "H5": "I"},
        "E6": {"H1": "I", "H2": "C", "H3": "C", "H4": "C", "H5": "I"},
    }
    for ev, cols in rows.items():
        for h, cons in cols.items():
            _rate(ach, ref.matrix_id, ev, hid[h], cons)
    r = ach.score_matrix(ref.matrix_id)
    # leading = H2 with zero strong inconsistencies (Heuer: least-inconsistency, not most-confirmation)
    assert r.leading == hid["H2"]
    lead = next(x for x in r.ordered if x.hypothesis_id == hid["H2"])
    assert lead.strong_inconsistencies == 0
    # H1 is the most disconfirmed (4 strong I), demoted despite E2 pulling toward it
    h1 = next(x for x in r.ordered if x.hypothesis_id == hid["H1"])
    assert h1.strong_inconsistencies == 4
    # ordered ascending by strong inconsistencies
    assert [x.strong_inconsistencies for x in r.ordered] == sorted(x.strong_inconsistencies for x in r.ordered)


def test_supersede_requires_reason(ach):
    ref = ach.create_matrix("c", ["H1", "H2"])
    hid = ref.hypotheses[0].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", hid, "C")
    with pytest.raises(ACHError, match="reason is required"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "I", "strong", "analyst_confirmed")
    # with reason it supersedes
    ach.rate_cell(ref.matrix_id, "E1", hid, "I", "strong", "analyst_confirmed", reason="re-read")
    m = ach.get_matrix(ref.matrix_id)
    cell = next(c for c in m.cells if c.evidence_id == "E1" and c.hypothesis_id == hid)
    assert cell.consistency == "I"


def test_score_refuses_model_draft(ach):
    ref = ach.create_matrix("c", ["H1", "H2"])
    hid = ref.hypotheses[0].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", hid, "I", "strong", js="model_draft")
    with pytest.raises(ACHError, match="model_draft"):
        ach.score_matrix(ref.matrix_id)


def test_unknown_matrix_and_hypothesis(ach):
    with pytest.raises(ACHError, match="unknown matrix_id"):
        ach.score_matrix("nope")
    ref = ach.create_matrix("c", ["H1"])
    with pytest.raises(ACHError, match="unknown hypothesis_id"):
        ach.rate_cell(ref.matrix_id, "E1", "h_bogus", "C", "weak", "analyst_confirmed")


def test_add_hypothesis(ach):
    ref = ach.create_matrix("c", ["H1"])
    ref2 = ach.add_hypothesis(ref.matrix_id, "H2")
    assert len(ref2.hypotheses) == 2


def test_empty_hypotheses_rejected(ach):
    with pytest.raises(ACHError, match="non-empty"):
        ach.create_matrix("c", [])


def test_chain_verifies(ach):
    ref = ach.create_matrix("c", ["H1", "H2"])
    _rate(ach, ref.matrix_id, "E1", ref.hypotheses[0].hypothesis_id, "C")
    assert ach.verify_chain().ok is True
