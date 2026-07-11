"""Deterministic fixtures for calibration-tracker (gate before any LLM/wire use)."""

from __future__ import annotations

import json
import os
import sqlite3

import pytest

from mcp_servers.calibration_tracker.store import (
    GENESIS,
    CalibrationStore,
    ForecastError,
    _row_hash,
)


@pytest.fixture()
def store(tmp_path):
    s = CalibrationStore(str(tmp_path / "cal.db"), analyst_id="test-analyst")
    yield s
    s.close()


def _log(s, q="Q", p=0.5, case="c1"):
    return s.log_forecast(case, q, p, "clairvoyance-style def", "3mo", "analyst_confirmed")


# --- the real Brier gate ---------------------------------------------------
# The 8 resolved items from docs/validation/compute_brier.py (assisted forecasts).
BRIER_ITEMS = [
    ("Y2K", 0.12, 0), ("Olympics", 0.06, 0), ("Grexit", 0.25, 0), ("Recession", 0.40, 0),
    ("SpaceX", 0.45, 1), ("Higgs", 0.82, 1), ("Favorite", 0.75, 1), ("Ceasefire", 0.30, 0),
]


def test_brier_gate_matches_reference(store):
    for q, p, outcome in BRIER_ITEMS:
        ref = store.log_forecast("brier", q, p, "resolves to a yes/no", "1y", "analyst_confirmed")
        # resolved_at must be >= the forecast's locked_at (S4); use the lock time itself.
        store.resolve_forecast(ref.forecast_id, bool(outcome), ref.locked_at)
    report = store.get_calibration_report(case_id="brier")
    reference_brier = sum((p - o) ** 2 for _, p, o in BRIER_ITEMS) / len(BRIER_ITEMS)
    assert report.n == 8
    # store rounds Brier to 6dp for a clean report; it matches the reference formula to that precision
    assert report.brier == pytest.approx(reference_brier, abs=1e-6)
    assert report.brier == pytest.approx(0.090988, abs=1e-6)
    # Murphy decomposition sanity: reliability >= 0, resolution >= 0.
    assert report.reliability_component >= 0
    assert report.resolution_component >= 0


def test_report_empty(store):
    r = store.get_calibration_report()
    assert r.n == 0 and r.brier is None and "no resolved" in r.note


# --- forecast lock ---------------------------------------------------------
def test_probability_locked_no_update_path(store):
    ref = _log(store, p=0.3)
    rec = store.get_forecast(ref.forecast_id)
    assert rec.probability == 0.3
    # there is no update_probability tool/method — lock is enforced by absence + append-only chain
    assert not hasattr(store, "update_forecast")


def test_model_draft_rejected(store):
    with pytest.raises(ForecastError, match="analyst_confirmed"):
        store.log_forecast("c", "q", 0.5, "def", "3mo", "model_draft")


def test_probability_range_and_empty_criteria(store):
    with pytest.raises(ForecastError, match="probability"):
        store.log_forecast("c", "q", 1.5, "def", "3mo", "analyst_confirmed")
    with pytest.raises(ForecastError, match="resolution_criteria"):
        store.log_forecast("c", "q", 0.5, "   ", "3mo", "analyst_confirmed")


# --- resolution + correction ----------------------------------------------
def test_resolve_then_correct(store):
    ref = _log(store)
    store.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    assert store.get_forecast(ref.forecast_id).outcome is True
    # second resolve without correction is rejected
    with pytest.raises(ForecastError, match="already resolved"):
        store.resolve_forecast(ref.forecast_id, False, ref.locked_at)
    # correction requires a reason
    with pytest.raises(ForecastError, match="reason"):
        store.resolve_forecast(ref.forecast_id, False, ref.locked_at, is_correction=True)
    # valid correction supersedes (latest wins), original row still present in the chain
    rec = store.resolve_forecast(ref.forecast_id, False, ref.locked_at, is_correction=True, reason="miscoded")
    assert store.get_forecast(ref.forecast_id).outcome is False
    # correction is now visible on the record without a full chain audit (S12)
    assert rec.was_corrected is True and rec.correction_count == 1


def test_correction_requires_prior_resolution(store):
    ref = _log(store)
    with pytest.raises(ForecastError, match="no prior resolution"):
        store.resolve_forecast(ref.forecast_id, True, "2026-01-01", is_correction=True, reason="x")


def test_unknown_forecast(store):
    with pytest.raises(ForecastError, match="unknown forecast_id"):
        store.resolve_forecast("nope", True, "2026-01-01")


# --- void (pre-resolution only) -------------------------------------------
def test_void_excludes_and_counts(store):
    good = store.log_forecast("v", "keep", 0.9, "def", "1y", "analyst_confirmed")
    bad = store.log_forecast("v", "typo", 0.1, "def", "1y", "analyst_confirmed")
    store.void_forecast(bad.forecast_id, "typo in probability")
    store.resolve_forecast(good.forecast_id, True, good.locked_at)
    r = store.get_calibration_report(case_id="v")
    assert r.n == 1  # only the non-voided resolved forecast
    assert r.n_voided == 1


def test_cannot_void_resolved(store):
    ref = _log(store)
    store.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    with pytest.raises(ForecastError, match="pre-resolution only"):
        store.void_forecast(ref.forecast_id, "too late")


def test_cannot_resolve_voided(store):
    ref = _log(store)
    store.void_forecast(ref.forecast_id, "mislogged")
    with pytest.raises(ForecastError, match="voided"):
        store.resolve_forecast(ref.forecast_id, True, "2026-01-01")


# --- hash chain integrity --------------------------------------------------
def test_chain_verifies_clean(store):
    for i in range(3):
        ref = _log(store, q=f"q{i}", p=0.1 * i)
        store.resolve_forecast(ref.forecast_id, i % 2 == 0, ref.locked_at)
    st = store.verify_chain()
    assert st.ok is True and st.mismatch is None and st.rows_verified == 6


def test_chain_detects_tamper(store, tmp_path):
    ref = _log(store, p=0.4)
    # tamper: mutate the stored probability directly, bypassing the append-only API
    raw = sqlite3.connect(str(tmp_path / "cal.db"))
    raw.execute("UPDATE forecasts SET probability=0.99 WHERE forecast_id=?", (ref.forecast_id,))
    raw.commit()
    raw.close()
    st = store.verify_chain()
    assert st.ok is False
    assert st.mismatch is not None and st.mismatch.table == "forecasts"


# --- M1: external manifest is tamper-evident (whole-chain / manifest deletion) ---
def test_manifest_deletion_is_detected(store, tmp_path):
    _log(store, p=0.4)
    assert store.verify_chain().ok is True
    # deleting the manifest while DB rows survive must NOT pass vacuously (fail-closed)
    os.remove(str(tmp_path / "cal.db.manifest.jsonl"))
    st = store.verify_chain()
    assert st.ok is False and st.mismatch is not None and "manifest" in st.mismatch.row_id


def test_manifest_line_tamper_is_detected(store, tmp_path):
    _log(store, p=0.4)
    mp = tmp_path / "cal.db.manifest.jsonl"
    lines = [ln for ln in mp.read_text().splitlines() if ln.strip()]
    e = json.loads(lines[0])
    e["head"] = "0" * 64  # rewrite the attested head; the self-chain hash no longer matches
    mp.write_text(json.dumps(e) + "\n")
    assert store.verify_chain().ok is False


def test_verify_chain_scope_is_always_all(store):
    _log(store)
    assert store.verify_chain().scope == "all"  # integrity is table-wide, never case-scoped (S8)


# --- S4: resolved_at is validated (ISO + not backdated before the lock) ---
def test_resolved_at_cannot_predate_lock(store):
    ref = _log(store)
    with pytest.raises(ForecastError, match="earlier than"):
        store.resolve_forecast(ref.forecast_id, True, "2000-01-01")


def test_resolved_at_must_be_iso(store):
    ref = _log(store)
    with pytest.raises(ForecastError, match="ISO-8601"):
        store.resolve_forecast(ref.forecast_id, True, "not-a-date")


# --- S2: malformed pagination cursor is a business error, not a raw ValueError leak ---
def test_bad_cursor_rejected(store):
    _log(store)
    with pytest.raises(ForecastError, match="cursor"):
        store.list_forecasts(cursor="not-int")


# --- S6/S5: required strings must be non-empty and bounded ---
def test_empty_question_rejected(store):
    with pytest.raises(ForecastError, match="question"):
        store.log_forecast("c", "   ", 0.5, "def", "3mo", "analyst_confirmed")


def test_oversized_field_rejected(store):
    with pytest.raises(ForecastError, match="max length"):
        store.log_forecast("c", "x" * 5000, 0.5, "def", "3mo", "analyst_confirmed")


# --- S11: idempotency must not silently drop content that differs from a recent forecast ---
def test_idempotency_does_not_drop_differing_content(store):
    a = store.log_forecast("c", "q", 0.5, "criteria A", "3mo", "analyst_confirmed")
    b = store.log_forecast("c", "q", 0.5, "criteria B", "3mo", "analyst_confirmed")
    assert a.forecast_id != b.forecast_id  # differing criteria => a new forecast, not a silent dedup
    c = store.log_forecast("c", "q", 0.5, "criteria A", "3mo", "analyst_confirmed")
    assert c.forecast_id == a.forecast_id  # a truly identical retry within the window IS deduped


# --- S5: log_forecast echoes the full locked record so the caller can confirm the immutable write ---
def test_log_forecast_returns_full_record(store):
    rec = store.log_forecast("c", "will it rain?", 0.7, "criteria", "3mo", "analyst_confirmed", "because")
    assert rec.probability == 0.7
    assert rec.question == "will it rain?"
    assert rec.resolution_criteria == "criteria"
    assert rec.horizon == "3mo"
    assert rec.rationale == "because"
    assert rec.outcome is None  # unresolved
    assert rec.row_hash  # chain hash present


# --- S2: created_ts is now covered by the row hash, so tampering with it is detected ---
def test_created_ts_tamper_detected(store, tmp_path):
    ref = _log(store)
    assert store.verify_chain().ok
    raw = sqlite3.connect(str(tmp_path / "cal.db"))
    raw.execute("UPDATE forecasts SET created_ts = created_ts + 1000 WHERE forecast_id=?", (ref.forecast_id,))
    raw.commit()
    raw.close()
    status = store.verify_chain()
    assert status.ok is False and status.mismatch.table == "forecasts"


# --- S3: a shared DB file must not leak or expose another analyst's forecasts ---
def test_cross_analyst_access_denied(tmp_path):
    db = str(tmp_path / "shared.db")
    a = CalibrationStore(db, analyst_id="alice")
    try:
        ref = a.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    finally:
        a.close()  # release the single-writer lock before bob opens
    b = CalibrationStore(db, analyst_id="bob")
    try:
        with pytest.raises(ForecastError, match="unknown forecast_id"):
            b.get_forecast(ref.forecast_id)
        assert b.list_forecasts().items == []
        assert b.get_calibration_report().n == 0
    finally:
        b.close()


# --- S3: only one process may hold a file-backed DB open (single-writer local design) ---
def test_second_writer_refused(tmp_path):
    db = str(tmp_path / "locked.db")
    a = CalibrationStore(db, analyst_id="alice")
    try:
        with pytest.raises(ForecastError, match="already open"):
            CalibrationStore(db, analyst_id="bob")
    finally:
        a.close()
    c = CalibrationStore(db, analyst_id="carol")  # lock released -> a new writer can open
    c.close()


# --- M1: the single-resolution decision runs INSIDE the write lock (TOCTOU: check-then-act atomic) ---
def test_resolution_check_runs_inside_write_lock(store, tracked_lock):
    # The prior code read _latest_resolution (the "already resolved?" decision) BEFORE acquiring the lock —
    # two concurrent resolve_forecast(is_correction=False) calls could both observe "unresolved" and both
    # append a first resolution, defeating the no-double-resolve invariant. Prove the decision read now
    # happens while the write lock is held (mirrors evidence-ledger's grade-existence TOCTOU test).
    store._write_lock = tracked_lock(store._write_lock)  # TrackedLock helper lives in conftest.py (DRY)
    depths: list[int] = []
    orig = store._latest_resolution

    def probe(forecast_id):
        depths.append(store._write_lock.depth)
        return orig(forecast_id)

    store._latest_resolution = probe
    ref = _log(store)
    store.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    # the FIRST _latest_resolution call is the single-resolution decision; it must run under the lock.
    assert depths and depths[0] > 0


def test_void_check_runs_inside_write_lock(store):
    # Same TOCTOU class for void: the pre-resolution-only / not-already-voided decision must be atomic with
    # the append (the read was previously before the lock). RLock._is_owned() is True only while this thread
    # holds the write lock.
    held: list[bool] = []
    orig = store._latest_resolution

    def probe(forecast_id):
        held.append(store._write_lock._is_owned())
        return orig(forecast_id)

    store._latest_resolution = probe
    ref = _log(store)
    store.void_forecast(ref.forecast_id, "mislogged")
    assert held and held[0] is True  # the pre-resolution decision ran while the lock was held


# --- M2: trailing-row truncation is caught by the manifest anchor (head + per-table row count) ---
def test_manifest_detects_tail_truncation(store, tmp_path):
    _log(store, q="q1")
    _log(store, q="q2")
    assert store.verify_chain().ok is True
    # delete the last forecast row directly: the surviving chain stays internally self-consistent but shorter;
    # only the external manifest anchor (attested head + row count) reveals the missing tail.
    raw = sqlite3.connect(str(tmp_path / "cal.db"))
    raw.execute("DELETE FROM forecasts WHERE seq=(SELECT MAX(seq) FROM forecasts)")
    raw.commit()
    raw.close()
    st = store.verify_chain()
    assert st.ok is False and st.mismatch is not None and st.mismatch.table == "forecasts"


# --- N5: a corrupt stored locked_at fails the resolve loud, not silently skipping anti-backdating ---
def test_corrupt_locked_at_blocks_resolve(store, tmp_path):
    ref = _log(store)
    raw = sqlite3.connect(str(tmp_path / "cal.db"))
    raw.execute("UPDATE forecasts SET locked_at='garbage' WHERE forecast_id=?", (ref.forecast_id,))
    raw.commit()
    raw.close()
    with pytest.raises(ForecastError, match="corrupt lock timestamp"):
        store.resolve_forecast(ref.forecast_id, True, "2030-01-01")


# --- item #10: case_id (the shared cross-server correlation key) is capped at 512, aligned with siblings ---
def test_case_id_cap_aligned_to_512(store):
    # A 512-char case_id — valid in ach-engine / evidence-ledger (both 512) — must now be accepted here too
    # (it was rejected at the old 200 cap); 513 is the first rejected length. Pins the aligned value at the
    # store layer (a revert to MAX_ID=200 makes the 512-char log_forecast raise, failing the first line).
    store.log_forecast("c" * 512, "q", 0.5, "def", "3mo", "analyst_confirmed")
    with pytest.raises(ForecastError, match="case_id exceeds max length 512"):
        store.log_forecast("c" * 513, "q2", 0.5, "def", "3mo", "analyst_confirmed")


# --- item #8: a PRE-count manifest must not cause a false tamper after the count anchor is added ---
def test_manifest_count_migration_from_precount(tmp_path):
    # _read_manifest_state falls back to the live table's COUNT(*) when a table has manifest entries but none
    # carry "count" — so the NEXT write attests the correct running count (not 1 from a zero seed), and
    # verify_chain stays green on upgrade instead of reporting a spurious trailing-truncation tamper.
    db = str(tmp_path / "cal.db")
    a = CalibrationStore(db, analyst_id="m")
    try:
        _log(a, q="q1")
        _log(a, q="q2")
        assert a.verify_chain().ok is True
    finally:
        a.close()
    # Rewrite the manifest into the PRE-count format (strip "count"), recomputing the self-chain over the
    # count-less payload so it stays internally valid — exactly what an old-format manifest looks like on disk.
    mp = tmp_path / "cal.db.manifest.jsonl"
    prev = GENESIS
    out: list[str] = []
    for ln in mp.read_text().splitlines():
        if not ln.strip():
            continue
        e = json.loads(ln)
        payload = {"table": e["table"], "head": e["head"], "at": e["at"]}  # NO "count"
        mh = _row_hash(prev, payload)
        out.append(json.dumps({**payload, "prev_manifest_hash": prev, "manifest_hash": mh}))
        prev = mh
    mp.write_text("\n".join(out) + "\n")
    b = CalibrationStore(db, analyst_id="m")
    try:
        assert b.verify_chain().ok is True  # the pre-count manifest verifies (no false tamper on read)
        _log(b, q="q3")  # migration seeded the count from the live table -> this attests count=3, not 1
        assert b.verify_chain().ok is True  # WITHOUT the fallback: a FALSE tamper (manifest 1 vs table 3 rows)
    finally:
        b.close()
