"""Deterministic fixtures for evidence-ledger (Server 2)."""

from __future__ import annotations

import os
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


def test_grade_carries_analyst_id(ev):  # MF6
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    rec = ev.grade_evidence(ref.evidence_id, "B", "2", "d", "analyst_confirmed")
    assert rec.grades[-1].analyst_id == "t"


def test_verify_chain_is_global(ev):  # MF5
    ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    st = ev.verify_chain()
    assert st.ok is True and st.scope == "all"


def test_bad_cursor_is_business_error(ev):  # SF1
    ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    with pytest.raises(EvidenceError, match="invalid cursor"):
        ev.list_evidence("c1", cursor="not-an-int")


def test_manifest_detects_tail_truncation(ev, tmp_path):  # MF3
    # Two rows internally self-consistent even after the last is deleted; only the manifest anchor catches it.
    ev.add_evidence("c1", "first", "src1", "report", False, "analyst_typed")
    ev.add_evidence("c1", "second", "src1", "report", False, "analyst_typed")
    assert ev.verify_chain().ok is True
    raw = sqlite3.connect(str(tmp_path / "ev.db"))
    raw.execute("DELETE FROM evidence WHERE seq=(SELECT MAX(seq) FROM evidence)")
    raw.commit()
    raw.close()
    st = ev.verify_chain()
    assert st.ok is False and st.mismatch.table == "evidence"


def test_manifest_missing_fails_closed(ev, tmp_path):  # MF3
    ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    os.remove(str(tmp_path / "ev.db.manifest.jsonl"))
    ev._manifest_head = ev._read_manifest_head()  # simulate a fresh open after the manifest was deleted
    st = ev.verify_chain()
    assert st.ok is False and st.mismatch.row_id == "<manifest-missing>"


def test_staleness_write_failure_is_loud(ev, monkeypatch):  # MF4
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")

    def boom(*a, **k):
        raise RuntimeError("staleness.db locked")

    monkeypatch.setattr(ev.staleness, "mark_stale", boom)
    with pytest.raises(EvidenceError, match="reconcile"):
        ev.grade_evidence(ref.evidence_id, "B", "2", "d", "analyst_confirmed")


def test_second_writer_refused(tmp_path):  # SF3
    st = StalenessStore(str(tmp_path / "stale.db"))
    a = EvidenceStore(str(tmp_path / "ev.db"), st, analyst_id="t")
    try:
        with pytest.raises(EvidenceError, match="already open by another process"):
            EvidenceStore(str(tmp_path / "ev.db"), st, analyst_id="t")
    finally:
        a.close()
        st.close()


def test_grade_existence_check_runs_inside_write_lock(ev):  # M1 (TOCTOU: check-then-act atomic)
    # The first-grade / has-prior-grade check must execute INSIDE the write-lock critical section, not
    # before it (old code checked in the public method, before the lock — two concurrent first grades
    # could both observe "no grade" and both insert). We prove atomicity by recording the lock depth at
    # the moment the existence check (_effective_grade) runs during an insert: it must be > 0.
    class _TrackedLock:
        def __init__(self, inner):
            self._inner = inner
            self.depth = 0

        def acquire(self, *a, **k):
            r = self._inner.acquire(*a, **k)
            self.depth += 1
            return r

        def release(self):
            self.depth -= 1
            self._inner.release()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, *a):
            self.release()

    ev._write_lock = _TrackedLock(ev._write_lock)
    depths: list[int] = []
    orig = ev._effective_grade

    def probe(evidence_id):
        depths.append(ev._write_lock.depth)
        return orig(evidence_id)

    ev._effective_grade = probe
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    ev.grade_evidence(ref.evidence_id, "B", "2", "d", "analyst_confirmed")  # first grade
    ev.update_grade(ref.evidence_id, "A", "1", "d", "corroboration", "analyst_confirmed")  # superseding
    assert depths  # the check ran
    assert all(d > 0 for d in depths)  # every existence check happened while the write lock was held


def test_list_evidence_bad_limit_is_loud(ev):  # S4 (fail loud, not silent clamp)
    ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    for bad in (0, -1, 1001):
        with pytest.raises(EvidenceError, match="limit must be in"):
            ev.list_evidence("c1", limit=bad)
    assert len(ev.list_evidence("c1", limit=1000).items) == 1  # boundary still accepted


def test_mask_error_details_enabled():  # M3 (raw internal errors not surfaced to the client)
    from mcp_servers.evidence_ledger import server

    assert server.mcp._tool_manager.mask_error_details is True


def test_unredact_gate_denied_by_default(monkeypatch):  # MF2 (tool-layer host gate)
    from mcp_servers.evidence_ledger import server

    monkeypatch.delenv("EVIDENCE_ALLOW_UNREDACT", raising=False)
    with pytest.raises(server.ToolError, match="unredaction refused"):
        server._require_unredact_permitted(redact_pii=False)
    server._require_unredact_permitted(redact_pii=True)  # redacted read always allowed
    monkeypatch.setenv("EVIDENCE_ALLOW_UNREDACT", "1")
    server._require_unredact_permitted(redact_pii=False)  # host opt-in permits it
