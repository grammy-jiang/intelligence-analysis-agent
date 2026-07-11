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


def test_grade_existence_check_runs_inside_write_lock(ev, tracked_lock):  # M1 (TOCTOU: check-then-act atomic)
    # The first-grade / has-prior-grade check must execute INSIDE the write-lock critical section, not
    # before it (old code checked in the public method, before the lock — two concurrent first grades
    # could both observe "no grade" and both insert). We prove atomicity by recording the lock depth at
    # the moment the existence check (_effective_grade) runs during an insert: it must be > 0.
    ev._write_lock = tracked_lock(ev._write_lock)  # TrackedLock helper lives in conftest.py (DRY)
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


def test_unredact_gate_rejects_falsey_env_values(monkeypatch):  # MF-2 (truthiness, not env-var presence)
    from mcp_servers.evidence_ledger import server

    # A NON-EMPTY but falsey value (an operator setting =0 / =false to DISABLE unredaction) must still deny —
    # the old `os.environ.get(...)` presence check granted it because any non-empty string is truthy.
    for val in ("0", "false", "no", "off", " "):
        monkeypatch.setenv("EVIDENCE_ALLOW_UNREDACT", val)
        with pytest.raises(server.ToolError, match="unredaction refused"):
            server._require_unredact_permitted(redact_pii=False)
    # only an explicit truthy token opts in (case-insensitive)
    for val in ("1", "true", "YES", "On"):
        monkeypatch.setenv("EVIDENCE_ALLOW_UNREDACT", val)
        server._require_unredact_permitted(redact_pii=False)


def test_store_rejects_out_of_domain_judgment_source(ev):  # MF-1(a): store-layer domain guard
    # The judgment_source domain is enforced at the store layer (defense-in-depth, mirrors ach-engine SF7) —
    # a direct store caller cannot smuggle a third value into the hash-chained grade payload. (The core
    # judgment-input boundary — a caller self-asserting analyst_confirmed — is by-design skill-enforced, not
    # server-verifiable; this only closes the "any value at all" gap.)
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    with pytest.raises(EvidenceError, match="judgment_source"):
        ev.grade_evidence(ref.evidence_id, "B", "2", "d", "totally_trusted")


def test_add_evidence_store_length_caps(ev):  # review item #6: store-layer DoS closure (append-only, no reclamation)
    # The tool boundary only capped the ENTRY COUNT of expected_observables (256) — a single entry with a giant
    # VALUE (e.g. {"h": "A"*50_000_000}) slipped straight through to the append-only row. The store now caps each
    # observable value AND key, plus the other free-text fields — a direct store caller cannot inflate the chain.
    with pytest.raises(EvidenceError, match="expected_observables value exceeds max length"):
        ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed", {"h": "A" * 2001})
    with pytest.raises(EvidenceError, match="expected_observables key exceeds max length"):
        ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed", {"k" * 513: "ok"})
    with pytest.raises(EvidenceError, match="item exceeds max length"):
        ev.add_evidence("c1", "z" * 100_001, "src1", "report", False, "analyst_typed")
    with pytest.raises(EvidenceError, match="case_id exceeds max length"):
        ev.add_evidence("c" * 513, "x", "src1", "report", False, "analyst_typed")


def test_insert_grade_store_length_caps(ev):  # review item #6: store-layer caps on the free-text grade strings
    ref = ev.add_evidence("c1", "x", "src1", "report", False, "analyst_typed")
    with pytest.raises(EvidenceError, match="diagnosticity exceeds max length"):
        ev.grade_evidence(ref.evidence_id, "B", "2", "d" * 10_001, "analyst_confirmed")
    with pytest.raises(EvidenceError, match="rationale exceeds max length"):
        ev.grade_evidence(ref.evidence_id, "B", "2", "d", "analyst_confirmed", "r" * 10_001)


def test_failed_insert_rolls_back_no_dangling_transaction(ev):  # review item #5 (atomic `with self._conn:`)
    # A failed INSERT must roll back cleanly, NOT leave a dangling OPEN transaction that a later commit could
    # smuggle into the append-only ledger. Force a UNIQUE(evidence_id) violation and assert the connection
    # holds no open transaction afterward — the old execute()+commit() idiom left in_transaction=True here.
    from unittest import mock

    from mcp_servers.evidence_ledger import store as store_mod

    with mock.patch.object(store_mod.uuid, "uuid4") as u:
        u.return_value.hex = "FIXEDDUPLICATEID"  # both adds mint the same evidence_id -> 2nd hits UNIQUE
        ev.add_evidence("c1", "a", "s", "report", False, "analyst_typed")
        with pytest.raises(sqlite3.IntegrityError):
            ev.add_evidence("c1", "b", "s", "report", False, "analyst_typed")
    assert ev._conn.in_transaction is False  # the failed insert rolled back; no dangling transaction
    # the ledger stays usable + consistent after the rolled-back failure
    ev.add_evidence("c1", "c", "s", "report", False, "analyst_typed")
    assert ev.verify_chain().ok is True
