"""Deterministic fixtures for evidence-ledger (Server 2)."""

from __future__ import annotations

import sqlite3

import pytest

from mcp_servers.evidence_ledger.models import EvidenceRef
from mcp_servers.evidence_ledger.store import EvidenceError, EvidenceStore
from mcp_servers.staleness import StalenessStore


@pytest.fixture()
def ev(tmp_path):
    st = StalenessStore(str(tmp_path / "stale.db"))
    s = EvidenceStore(str(tmp_path / "ev.db"), st, analyst_id="t")
    yield s
    s.close()
    st.close()


def test_add_grade_get(ev):
    ref = ev.add_evidence("c1", "a report", "src1", "report", False, "analyst_typed", {"h1": "should see X"})
    rec = ev.grade_evidence(ref.evidence_id, "B", "2", "diagnostic vs h1", "analyst_confirmed")
    assert rec.grades[-1].reliability == "B" and rec.grades[-1].credibility == "2"
    assert rec.expected_observables == {"h1": "should see X"}


def test_evidence_ref_carries_no_item():
    assert "item" not in EvidenceRef.model_fields
    assert set(EvidenceRef.model_fields) == {"evidence_id", "case_id", "pii"}


def test_pii_redacted_by_default(ev):
    ref = ev.add_evidence("c1", "SENSITIVE source name", "src1", "report", True, "analyst_typed")
    assert ev.get_evidence(ref.evidence_id).item == "REDACTED"
    assert ev.get_evidence(ref.evidence_id, redact_pii=False).item == "SENSITIVE source name"


def test_grade_then_update_supersedes(ev):
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    ev.grade_evidence(ref.evidence_id, "C", "3", "d", "analyst_confirmed")
    with pytest.raises(EvidenceError, match="already exists"):
        ev.grade_evidence(ref.evidence_id, "A", "1", "d", "analyst_confirmed")
    with pytest.raises(EvidenceError, match="reason"):
        ev.update_grade(ref.evidence_id, "A", "1", "d", "", "analyst_confirmed")
    rec = ev.update_grade(ref.evidence_id, "A", "1", "d", "new corroboration", "analyst_confirmed")
    assert rec.grades[-1].reliability == "A" and rec.grades[-1].superseded is False
    assert rec.grades[0].superseded is True


def test_update_without_prior_grade(ev):
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    with pytest.raises(EvidenceError, match="no prior grade"):
        ev.update_grade(ref.evidence_id, "A", "1", "d", "r", "analyst_confirmed")


def test_grade_marks_stale(ev):
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    assert ev.staleness.latest_stale_ts(ref.evidence_id) is None
    ev.grade_evidence(ref.evidence_id, "B", "2", "d", "analyst_confirmed")
    assert ev.staleness.latest_stale_ts(ref.evidence_id) is not None


def test_source_history_confirmed_only(ev):
    a = ev.add_evidence("c1", "x", "srcX", "report", False, "analyst_typed")
    b = ev.add_evidence("c2", "y", "srcX", "report", False, "analyst_typed")
    d = ev.add_evidence("c3", "z", "srcX", "report", False, "analyst_typed")
    ev.grade_evidence(a.evidence_id, "C", "3", "d", "analyst_confirmed")
    ev.grade_evidence(b.evidence_id, "A", "1", "d", "analyst_confirmed")  # improved (C -> A)
    ev.grade_evidence(d.evidence_id, "F", "5", "d", "model_draft")  # excluded
    hist = ev.get_source_history("srcX")
    assert hist.grade_sequence == ["C", "A"]
    assert hist.last_change_direction == "improved"
    assert hist.n == 2 and hist.n_model_draft_excluded == 1
    assert set(hist.cases) == {"c1", "c2", "c3"}


def test_unknown_evidence(ev):
    with pytest.raises(EvidenceError, match="unknown evidence_id"):
        ev.grade_evidence("nope", "A", "1", "d", "analyst_confirmed")


def test_chain_tamper_detected(ev, tmp_path):
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    raw = sqlite3.connect(str(tmp_path / "ev.db"))
    raw.execute("UPDATE evidence SET item='TAMPERED' WHERE evidence_id=?", (ref.evidence_id,))
    raw.commit()
    raw.close()
    st = ev.verify_chain()
    assert st.ok is False and st.mismatch.table == "evidence"
