"""Deterministic fixtures for calibration-tracker (gate before any LLM/wire use)."""

from __future__ import annotations

import sqlite3

import pytest

from mcp_servers.calibration_tracker.store import CalibrationStore, ForecastError


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
        store.resolve_forecast(ref.forecast_id, bool(outcome), "2026-01-01")
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
    store.resolve_forecast(ref.forecast_id, True, "2026-01-01")
    assert store.get_forecast(ref.forecast_id).outcome is True
    # second resolve without correction is rejected
    with pytest.raises(ForecastError, match="already resolved"):
        store.resolve_forecast(ref.forecast_id, False, "2026-02-01")
    # correction requires a reason
    with pytest.raises(ForecastError, match="reason"):
        store.resolve_forecast(ref.forecast_id, False, "2026-02-01", is_correction=True)
    # valid correction supersedes (latest wins), original row still present in the chain
    store.resolve_forecast(ref.forecast_id, False, "2026-02-01", is_correction=True, reason="miscoded")
    assert store.get_forecast(ref.forecast_id).outcome is False


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
    store.resolve_forecast(good.forecast_id, True, "2026-01-01")
    r = store.get_calibration_report(case_id="v")
    assert r.n == 1  # only the non-voided resolved forecast
    assert r.n_voided == 1


def test_cannot_void_resolved(store):
    ref = _log(store)
    store.resolve_forecast(ref.forecast_id, True, "2026-01-01")
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
        store.resolve_forecast(ref.forecast_id, i % 2 == 0, "2026-01-01")
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
