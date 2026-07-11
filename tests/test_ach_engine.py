"""Deterministic fixtures for ach-engine (Server 3), incl. the Iraqi-retaliation golden."""

from __future__ import annotations

import json
import sqlite3

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
    # evidence must carry an effective analyst_confirmed grade before its cells can be scored
    ach.staleness.mark_graded(ev, "analyst_confirmed")
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


def test_rated_ts_tamper_breaks_chain(ach):
    # M1: rated_ts drives staleness logic, so tampering it must break verify_chain (not sail through).
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", hid, "C")
    assert ach.verify_chain().ok is True
    raw = sqlite3.connect(ach.db_path)
    raw.execute("UPDATE cells SET rated_ts = rated_ts + 9999 WHERE evidence_id='E1'")
    raw.commit()
    raw.close()
    s = ach.verify_chain()
    assert s.ok is False and s.mismatch.table == "cells"


def test_trailing_truncation_detected(ach):
    # M2: deleting the last row leaves a self-consistent shorter chain — the manifest reconciliation
    # must catch it.
    ref = ach.create_matrix("c", ["H1", "H2"])
    h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", h1, "C")
    _rate(ach, ref.matrix_id, "E2", h2, "I")
    assert ach.verify_chain().ok is True
    raw = sqlite3.connect(ach.db_path)
    raw.execute("DELETE FROM cells WHERE seq = (SELECT MAX(seq) FROM cells)")
    raw.commit()
    raw.close()
    s = ach.verify_chain()
    assert s.ok is False and s.mismatch.table == "cells"


def test_rate_confirmed_requires_out_of_band_grade(ach):
    # M4: analyst_confirmed is not self-attestable — an agent can only draft (model_draft) unless the
    # evidence already carries an out-of-band analyst_confirmed grade signal.
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    with pytest.raises(ACHError, match="out-of-band confirmation required"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "analyst_confirmed")
    ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "model_draft")  # drafting is always allowed
    ach.staleness.mark_graded("E1", "analyst_confirmed")  # human confirms out of band
    rec = ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "analyst_confirmed", reason="confirm")
    assert rec.judgment_source == "analyst_confirmed"


def test_superseded_flag_reflects_correction(ach):
    # M5: the engine-computed superseded flag must tell a correction from a fresh rating.
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    first = _rate(ach, ref.matrix_id, "E1", hid, "C")
    assert first.superseded is False
    second = ach.rate_cell(ref.matrix_id, "E1", hid, "I", "strong", "analyst_confirmed", reason="re-read")
    assert second.superseded is True


def test_list_matrices_rejects_bad_cursor(ach):
    # S1: a malformed cursor is a caller error surfaced as ACHError, not an uncaught ValueError.
    ach.create_matrix("c", ["H1"])
    with pytest.raises(ACHError, match="invalid cursor"):
        ach.list_matrices("c", cursor="not-an-int")


def test_score_blocks_uncovered_hypothesis(ach):
    # MF1: a hypothesis lacking a rating against every evidence item must NOT be silently ranked
    # first at 0/0 — score_matrix refuses on the coverage gap instead of letting the untested
    # hypothesis win the least-inconsistency sort.
    ref = ach.create_matrix("c", ["H1", "H2"])
    h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", h1, "I", "strong")  # only H1 rated; H2 has no cell
    with pytest.raises(ACHError, match="coverage gap"):
        ach.score_matrix(ref.matrix_id)
    # full coverage -> scores, and H2 (no inconsistency) legitimately leads over H1 (1 strong I)
    _rate(ach, ref.matrix_id, "E1", h2, "C", "weak")
    r = ach.score_matrix(ref.matrix_id)
    assert r.leading == h2


def test_added_hypothesis_blocks_scoring_until_rated(ach):
    # MF1: add_hypothesis mid-analysis introduces ABSENT cells; a fully-scored matrix must go back to
    # refusing until the new column is rated against existing evidence, not let it win at 0/0.
    ref = ach.create_matrix("c", ["H1", "H2"])
    h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", h1, "I", "strong")
    _rate(ach, ref.matrix_id, "E1", h2, "C", "weak")
    assert ach.score_matrix(ref.matrix_id).leading == h2  # scores fine at full coverage
    ref2 = ach.add_hypothesis(ref.matrix_id, "H3")
    h3 = next(h.hypothesis_id for h in ref2.hypotheses if h.text == "H3")
    with pytest.raises(ACHError, match="coverage gap"):
        ach.score_matrix(ref.matrix_id)
    _rate(ach, ref.matrix_id, "E1", h3, "C", "weak")  # rate the new column -> scores again
    assert ach.score_matrix(ref.matrix_id).leading is not None
    assert h3  # column exists and is now covered


def test_score_refuses_empty_matrix(ach):
    # MF1: a matrix with no rated cells has nothing to rank — refuse rather than emit a degenerate 0/0.
    ref = ach.create_matrix("c", ["H1", "H2"])
    with pytest.raises(ACHError, match="no cells have been rated"):
        ach.score_matrix(ref.matrix_id)


def test_store_rejects_out_of_domain_values(ach):
    # SF7: the store enforces the consistency/strength/judgment_source domains itself, not only the
    # tool-boundary pydantic Literal — a direct store caller cannot write junk into the hash chain.
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    ach.staleness.mark_graded("E1", "analyst_confirmed")
    with pytest.raises(ACHError, match="consistency"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "MAYBE", "strong", "analyst_confirmed")
    with pytest.raises(ACHError, match="strength"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "C", "sorta", "analyst_confirmed")
    with pytest.raises(ACHError, match="judgment_source"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "C", "weak", "guessing")


def test_create_matrix_rejects_blank_case_id(ach):
    # SF9: a blank/whitespace case_id groups matrices outside any real case — reject it up front.
    with pytest.raises(ACHError, match="case_id"):
        ach.create_matrix("  ", ["H1"])


def test_create_matrix_rejects_oversized_case_id(ach):
    # S5: store-layer length cap (defense-in-depth) — a direct store caller bypassing the tool-schema Field
    # must not persist an unbounded case_id into the append-only matrices table.
    with pytest.raises(ACHError, match="max length"):
        ach.create_matrix("x" * 1000, ["H1"])


def test_verify_chain_scope_is_always_all(ach):
    # MF4: integrity is table-wide, never case-scoped; the dead case_id filter was removed.
    ach.create_matrix("c", ["H1"])
    assert ach.verify_chain().scope == "all"


def test_head_read_runs_inside_write_lock(ach, tracked_lock):
    # M1 (TOCTOU): create_matrix / rate_cell previously read the chain head + computed row_hash BEFORE
    # acquiring the write lock — two concurrent writers could hash against the same stale head and fork the
    # append-only chain (verify_chain then reports a false tamper on ordinary concurrency). Prove every _head
    # read during a write now happens while the lock is held (mirrors _insert_hypothesis).
    ach._write_lock = tracked_lock(ach._write_lock)  # TrackedLock helper lives in conftest.py (DRY)
    depths: list[int] = []
    orig = ach._head

    def probe(table):
        depths.append(ach._write_lock.depth)
        return orig(table)

    ach._head = probe
    ref = ach.create_matrix("c", ["H1", "H2"])  # _head("matrices") + _head("hypotheses") x2
    hid = ref.hypotheses[0].hypothesis_id
    ach.staleness.mark_graded("E1", "analyst_confirmed")
    ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "analyst_confirmed")  # _head("cells")
    assert depths and all(d > 0 for d in depths)  # every head read happened under the write lock


def test_effective_cell_read_runs_inside_write_lock(ach, tracked_lock):
    # M1 (TOCTOU, review item #1): rate_cell previously read _effective_cell (the supersede decision AND the
    # reason-required gate) BEFORE acquiring the write lock — two concurrent rate_cell calls could both observe
    # "no prior" and both insert a first rating / skip the reason requirement. Prove the effective-cell read
    # now runs under the lock (mirrors test_head_read_runs_inside_write_lock / evidence-ledger's TOCTOU test).
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    ach._write_lock = tracked_lock(ach._write_lock)
    depths: list[int] = []
    orig = ach._effective_cell

    def probe(matrix_id, evidence_id, hypothesis_id):
        depths.append(ach._write_lock.depth)
        return orig(matrix_id, evidence_id, hypothesis_id)

    ach._effective_cell = probe
    ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "model_draft")
    assert depths and depths[0] > 0  # the supersede decision read ran while the write lock was held


def test_verify_chain_holds_write_lock(ach, tracked_lock):
    # review item #2: verify_chain must hold the write lock for its whole read + manifest walk, so a verify
    # interleaved with an in-flight write cannot read a committed-but-not-yet-manifest-attested row and report
    # a spurious tamper. Prove _payload_for (called for every row INSIDE verify_chain) runs under the lock.
    ach.create_matrix("c", ["H1"])  # >=1 row so _payload_for is exercised
    ach._write_lock = tracked_lock(ach._write_lock)
    depths: list[int] = []
    orig = ach._payload_for

    def probe(table, r):
        depths.append(ach._write_lock.depth)
        return orig(table, r)

    ach._payload_for = probe
    assert ach.verify_chain().ok is True
    assert depths and all(d > 0 for d in depths)  # every payload build happened under the write lock


def test_store_length_caps(ach):
    # review item #6: the cells/hypotheses tables are append-only with NO reclamation, so the store itself
    # (not only the tool-boundary pydantic caps) must bound the caller-controlled strings — a direct store
    # caller cannot inflate the hash-chained payload without limit.
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    with pytest.raises(ACHError, match="evidence_id exceeds max length"):
        ach.rate_cell(ref.matrix_id, "E" * 513, hid, "C", "strong", "model_draft")
    with pytest.raises(ACHError, match="reason exceeds max length"):
        ach.rate_cell(ref.matrix_id, "E1", hid, "C", "strong", "model_draft", reason="r" * 10_001)
    with pytest.raises(ACHError, match="hypothesis text exceeds max length"):
        ach.add_hypothesis(ref.matrix_id, "H" * 10_001)


def test_manifest_middle_line_edit_detected(ach):
    # review item #7: the manifest is SELF-CHAINED (prev_manifest_hash / manifest_hash) so editing a
    # NON-TERMINAL line is detected. The per-table head+count reconciliation alone only checks the LAST head
    # per table, so an edit to an earlier line for a multi-entry table would slip through without the chain.
    # create_matrix writes [matrices, hypotheses(H1), hypotheses(H2)] — edit the first hypotheses line (middle).
    ach.create_matrix("c", ["H1", "H2"])
    assert ach.verify_chain().ok is True
    mp = ach.db_path + ".manifest.jsonl"
    with open(mp, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    assert len(lines) >= 3  # a genuine middle line exists
    e = json.loads(lines[1])  # first hypotheses entry — NOT the last per-table head, so only the self-chain catches it
    e["head"] = "0" * 64  # rewrite its attested head; the recomputed manifest_hash no longer matches
    lines[1] = json.dumps(e)
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    assert ach.verify_chain().ok is False
