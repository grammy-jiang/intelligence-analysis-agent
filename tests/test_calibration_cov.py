"""Targeted coverage for calibration-tracker server.py + store.py error/edge branches.

Two styles, mirroring the existing suite:
- store.py branches are driven directly against CalibrationStore (like test_calibration_tracker.py).
- server.py @mcp.tool bodies are driven by calling the tool functions directly (they are plain
  functions in this FastMCP version) after setting CALIBRATION_DB=":memory:" before the import
  (the test_calibration_wire.py pattern). Error paths assert the ForecastError -> ToolError wrap.
"""

from __future__ import annotations

import importlib
import os
import sqlite3

import pytest
from fastmcp.exceptions import ToolError

from mcp_servers.calibration_tracker import store as store_mod
from mcp_servers.calibration_tracker.store import CalibrationStore, ForecastError

os.environ["CALIBRATION_DB"] = ":memory:"

from mcp_servers.calibration_tracker import server as srv


@pytest.fixture()
def fstore(tmp_path):
    """A fresh file-backed store per test (a real DB is needed for WAL / raw-tamper paths)."""
    s = CalibrationStore(str(tmp_path / "cov.db"), analyst_id="cov-analyst")
    yield s
    s.close()


class _ConnProxy:
    """Wraps a real sqlite3 connection but raises on any statement containing `needle` — used to force
    the INSERT to fail so the store's rollback-then-reraise guard (S1) executes."""

    def __init__(self, real, needle: str):
        self._real = real
        self._needle = needle

    def execute(self, sql, *a, **k):
        if self._needle in sql:
            raise sqlite3.OperationalError("forced insert failure")
        return self._real.execute(sql, *a, **k)

    def commit(self):
        return self._real.commit()

    def rollback(self):
        return self._real.rollback()

    def __getattr__(self, name):
        return getattr(self._real, name)


# ---------------------------------------------------------------------------
# server.py — @mcp.tool bodies (success + ForecastError -> ToolError branches)
# ---------------------------------------------------------------------------


def test_server_log_forecast_error_wraps_toolerror():
    # server.py 88-89: ForecastError from the store is re-raised as a ToolError.
    with pytest.raises(ToolError, match="analyst_confirmed"):
        srv.log_forecast("w", "q", 0.5, "def", "3mo", judgment_source="model_draft")


def test_server_resolve_forecast_error_wraps_toolerror():
    # server.py 130-131: unknown forecast_id -> ForecastError -> ToolError. resolved_at is a valid PAST date
    # (M1 rejects future dates before the lookup), so the not-found path is what surfaces.
    with pytest.raises(ToolError, match="unknown forecast_id"):
        srv.resolve_forecast("nope", True, "2020-01-01")


def test_server_void_forecast_success_and_error():
    # server.py 148-149 (success) and 150-151 (error wrap).
    rec = srv.log_forecast("w", "void-me", 0.5, "def", "3mo")
    voided = srv.void_forecast(rec.forecast_id, "mis-logged")
    assert voided.voided is True
    with pytest.raises(ToolError, match="unknown forecast_id"):
        srv.void_forecast("nope", "reason")


def test_server_get_forecast_success_and_error():
    # server.py 161-162 (success) and 163-164 (error wrap).
    rec = srv.log_forecast("w", "get-me", 0.5, "def", "3mo")
    got = srv.get_forecast(rec.forecast_id)
    assert got.forecast_id == rec.forecast_id
    with pytest.raises(ToolError, match="unknown forecast_id"):
        srv.get_forecast("nope")


def test_server_list_forecasts_success_and_error():
    # server.py 188-189 (success) and 190-191 (error wrap; bad cursor -> ForecastError).
    srv.log_forecast("w", "list-me", 0.5, "def", "3mo")
    lst = srv.list_forecasts()
    assert len(lst.items) >= 1
    with pytest.raises(ToolError, match="cursor"):
        srv.list_forecasts(cursor="not-an-int")


def test_server_calibration_report_error_wraps_toolerror(monkeypatch):
    # server.py 213-214: the report tool never validates inputs into a ForecastError itself, so force the
    # store method to raise and confirm the tool re-wraps it as a ToolError.
    def _boom(*a, **k):
        raise ForecastError("forced report failure")

    monkeypatch.setattr(srv.store, "get_calibration_report", _boom)
    with pytest.raises(ToolError, match="forced report failure"):
        srv.get_calibration_report()


def test_server_verify_chain_success_and_error(monkeypatch):
    # server.py 221-222 (success path over the live :memory: store).
    assert srv.verify_chain().ok is True

    # server.py 223-224: force a ForecastError so the except/ToolError wrap runs.
    def _boom(*a, **k):
        raise ForecastError("forced verify failure")

    monkeypatch.setattr(srv.store, "verify_chain", _boom)
    with pytest.raises(ToolError, match="forced verify failure"):
        srv.verify_chain()


def test_server_main_serves_when_chain_ok(monkeypatch):
    # server.py 228, 229, 235-241: chain verifies -> print "serving" and call mcp.run (stubbed no-op).
    ran: dict[str, object] = {}

    class _OkStatus:
        ok = True
        rows_verified = 3
        mismatch = None

    class _FakeStore:
        def verify_chain(self):
            return _OkStatus()

    class _FakeMcp:
        def run(self, **kwargs):
            ran["kwargs"] = kwargs

    monkeypatch.setattr(srv, "store", _FakeStore())
    monkeypatch.setattr(srv, "mcp", _FakeMcp())
    srv.main()
    assert ran["kwargs"] == {"transport": "stdio", "show_banner": False}


def test_server_main_refuses_when_chain_broken(monkeypatch):
    # server.py 228, 229, 230-234: chain fails -> print refusal and SystemExit(1) (never reaches mcp.run).
    class _BadStatus:
        ok = False
        rows_verified = 0
        mismatch = "tampered"

    class _FakeStore:
        def verify_chain(self):
            return _BadStatus()

    monkeypatch.setattr(srv, "store", _FakeStore())
    with pytest.raises(SystemExit) as exc:
        srv.main()
    assert exc.value.code == 1


def test_server_import_makes_data_dir(tmp_path, monkeypatch):
    # server.py 27-28: the non-:memory: import branch os.makedirs the DB's parent dir. Re-import the module
    # with a file DB whose parent does not exist yet, then restore the :memory: globals for other tests.
    orig_store, orig_mcp, orig_db = srv.store, srv.mcp, srv.DB_PATH
    dbfile = tmp_path / "nested" / "calibration.db"  # 'nested' does not exist yet
    monkeypatch.setenv("CALIBRATION_DB", str(dbfile))
    try:
        importlib.reload(srv)
        assert str(dbfile) == srv.DB_PATH
        assert dbfile.parent.is_dir()  # created by line 28
        assert srv.verify_chain().ok is True  # the freshly built file-backed store is usable
    finally:
        if srv.store is not orig_store:
            srv.store.close()
        srv.store, srv.mcp, srv.DB_PATH = orig_store, orig_mcp, orig_db


# ---------------------------------------------------------------------------
# store.py — construction / validation / append-failure / report edge branches
# ---------------------------------------------------------------------------


def test_wal_journal_mode_required(tmp_path, monkeypatch):
    # store.py 104: a file DB that cannot enter WAL journal mode must refuse to run. Fake a connection whose
    # journal_mode PRAGMA reports a non-WAL mode.
    class _FakeCur:
        def fetchone(self):
            return ["delete"]

    class _FakeConn:
        def execute(self, *a, **k):
            return _FakeCur()

    monkeypatch.setattr(store_mod.sqlite3, "connect", lambda *a, **k: _FakeConn())
    with pytest.raises(ForecastError, match="WAL journal mode"):
        CalibrationStore(str(tmp_path / "nowal.db"))


def test_head_rejects_unknown_table(fstore):
    # store.py 160: the internal _head guard survives `python -O` (assert stripped) for a bad table literal.
    with pytest.raises(ValueError, match="unknown table"):
        fstore._head("bogus")


def test_seed_manifest_baseline_runs(fstore):
    # store.py 169-177: the one-time manifest baseline migration computes per-table (head, count). It is a
    # no-op when a manifest already exists, but the method body still executes.
    fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    written = fstore.seed_manifest_baseline()
    assert isinstance(written, int)


def test_rationale_length_cap(fstore):
    # store.py 209: an over-long rationale is rejected.
    with pytest.raises(ForecastError, match="rationale exceeds max length"):
        fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed", "r" * 4001)


def test_log_forecast_insert_failure_rolls_back(fstore):
    # store.py 278-280: a failed forecasts INSERT rolls back and re-raises (no dangling transaction).
    real = fstore._conn
    fstore._conn = _ConnProxy(real, "INSERT INTO forecasts")
    try:
        with pytest.raises(sqlite3.OperationalError):
            fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    finally:
        fstore._conn = real


def test_resolve_reason_length_cap(fstore):
    # store.py 317: an over-long correction reason is rejected up front.
    ref = fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    with pytest.raises(ForecastError, match="reason exceeds max length"):
        fstore.resolve_forecast(ref.forecast_id, True, "2030-01-01", reason="x" * 4001)


def test_resolve_forecast_insert_failure_rolls_back(fstore):
    # store.py 385-387: a failed resolutions INSERT rolls back and re-raises.
    ref = fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    real = fstore._conn
    fstore._conn = _ConnProxy(real, "INSERT INTO resolutions")
    try:
        with pytest.raises(sqlite3.OperationalError):
            fstore.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    finally:
        fstore._conn = real


def test_void_reason_validation(fstore):
    # store.py 393 (empty reason), 395 (over-long reason), 407 (already voided).
    ref = fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    with pytest.raises(ForecastError, match="non-empty reason"):
        fstore.void_forecast(ref.forecast_id, "   ")
    with pytest.raises(ForecastError, match="reason exceeds max length"):
        fstore.void_forecast(ref.forecast_id, "x" * 4001)
    fstore.void_forecast(ref.forecast_id, "mis-logged")
    with pytest.raises(ForecastError, match="already voided"):
        fstore.void_forecast(ref.forecast_id, "again")


def test_void_forecast_insert_failure_rolls_back(fstore):
    # store.py 417-419: a failed voids INSERT rolls back and re-raises.
    ref = fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    real = fstore._conn
    fstore._conn = _ConnProxy(real, "INSERT INTO voids")
    try:
        with pytest.raises(sqlite3.OperationalError):
            fstore.void_forecast(ref.forecast_id, "mis-logged")
    finally:
        fstore._conn = real


def test_list_forecasts_negative_cursor_rejected(fstore):
    # store.py 465: a negative (parseable) cursor is a business error, not a raw slice.
    fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    with pytest.raises(ForecastError, match="invalid cursor"):
        fstore.list_forecasts(cursor="-5")


def test_list_forecasts_case_and_resolved_filters(fstore):
    # store.py 470-471 (case_id filter clause) and 478-483 (per-row build; the resolved filter's `continue`
    # for an unresolved row and the append for a resolved one).
    a = fstore.log_forecast("LC", "qa", 0.5, "def", "3mo", "analyst_confirmed")
    fstore.log_forecast("LC", "qb", 0.5, "def", "3mo", "analyst_confirmed")  # stays unresolved
    fstore.log_forecast("OTHER", "qx", 0.5, "def", "3mo", "analyst_confirmed")  # different case
    fstore.resolve_forecast(a.forecast_id, True, a.locked_at)
    res = fstore.list_forecasts(case_id="LC", resolved=True)
    assert [i.question for i in res.items] == ["qa"]  # qb filtered (continue), qx out of case scope


def test_report_counts_corrected_forecast(fstore):
    # store.py 519: a scored forecast whose outcome was later corrected increments n_corrected.
    ref = fstore.log_forecast("RC", "q", 0.5, "def", "2999-12-31", "analyst_confirmed")
    fstore.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    fstore.resolve_forecast(ref.forecast_id, False, ref.locked_at, is_correction=True, reason="fix")
    rep = fstore.get_calibration_report(case_id="RC")
    assert rep.n == 1 and rep.n_corrected == 1


def test_report_tolerates_unparseable_locked_at(fstore):
    # store.py 544-545: the latency advisory swallows a parse error on a corrupt locked_at rather than
    # crashing the report. Corrupt the server-authored locked_at directly (bypassing the append-only API).
    ref = fstore.log_forecast("LK", "q", 0.5, "def", "2999-12-31", "analyst_confirmed")
    fstore.resolve_forecast(ref.forecast_id, True, ref.locked_at)
    fstore._conn.execute(
        "UPDATE forecasts SET locked_at='garbage' WHERE forecast_id=?", (ref.forecast_id,)
    )
    fstore._conn.commit()
    rep = fstore.get_calibration_report(case_id="LK")
    assert rep.n == 1  # still scored; only the advisory latency signal is disabled for this row


def test_verify_chain_walks_void_rows(fstore):
    # store.py 693: verify_chain rebuilds the voids-table payload while walking the chain.
    ref = fstore.log_forecast("c", "q", 0.5, "def", "3mo", "analyst_confirmed")
    fstore.void_forecast(ref.forecast_id, "mis-logged")
    st = fstore.verify_chain()
    assert st.ok is True and st.head_hash["voids"] != store_mod.GENESIS
