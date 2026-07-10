"""FastMCP server for calibration-tracker (design v3, Server 1).

Tools wrap CalibrationStore; ForecastError → ToolError. Nothing writes to stdout (the stdio JSON-RPC
channel); logs go to stderr. `analyst_id` is a trusted local binding inside the store, never a tool arg.
"""

from __future__ import annotations

import os
import sys
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .models import (
    CalibrationReport,
    ChainStatus,
    ForecastList,
    ForecastRecord,
    ForecastRef,
    JudgmentSource,
)
from .store import CalibrationStore, ForecastError

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "calibration.db")
DB_PATH = os.environ.get("CALIBRATION_DB", _DEFAULT_DB)
if DB_PATH != ":memory:":
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

store = CalibrationStore(DB_PATH)
mcp = FastMCP("calibration-tracker")


@mcp.tool
def log_forecast(
    case_id: str,
    question: str,
    probability: Annotated[float, Field(ge=0.0, le=1.0)],
    resolution_criteria: str,
    horizon: str,
    judgment_source: JudgmentSource,
    rationale: str = "",
) -> ForecastRef:
    """Log a NEW forecast and LOCK its question + probability (only outcomes/voids are appended later).
    `probability` is the analyst's judgment (required input). Requires judgment_source='analyst_confirmed'.
    """
    try:
        return store.log_forecast(
            case_id, question, probability, resolution_criteria, horizon, judgment_source, rationale
        )
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def resolve_forecast(
    forecast_id: str, outcome: bool, resolved_at: str, is_correction: bool = False, reason: str = ""
) -> ForecastRecord:
    """Append the OUTCOME to a locked forecast. First resolution: is_correction=False. To fix a wrong
    outcome: is_correction=True + non-empty reason (appends a superseding resolution; never edits)."""
    try:
        return store.resolve_forecast(forecast_id, outcome, resolved_at, is_correction, reason)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def void_forecast(forecast_id: str, reason: str) -> ForecastRecord:
    """Flag a MIS-LOGGED forecast as excluded from Brier scoring. PRE-RESOLUTION ONLY (errors if resolved)."""
    try:
        return store.void_forecast(forecast_id, reason)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_forecast(forecast_id: str) -> ForecastRecord:
    """Read one forecast (with its effective outcome / voided status)."""
    try:
        return store.get_forecast(forecast_id)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def list_forecasts(
    case_id: str | None = None, resolved: bool | None = None, limit: int = 100, cursor: str | None = None
) -> ForecastList:
    """Read-back with filters + pagination (opaque cursor)."""
    return store.list_forecasts(case_id, resolved, limit, cursor)


@mcp.tool
def get_calibration_report(case_id: str | None = None) -> CalibrationReport:
    """COMPUTE Brier + a calibration table + Murphy resolution/reliability over analyst_confirmed, non-voided,
    resolved forecasts. Read-only; no judgment invented."""
    return store.get_calibration_report(case_id)


@mcp.tool
def verify_chain(case_id: str | None = None) -> ChainStatus:
    """Verify the append-only hash chains + the external manifest (tamper / whole-chain-deletion evidence)."""
    return store.verify_chain(case_id)


def main() -> None:
    status = store.verify_chain()
    if not status.ok:
        print(f"[calibration-tracker] REFUSING TO SERVE — chain verify failed: {status.mismatch}", file=sys.stderr)
        raise SystemExit(1)
    print(f"[calibration-tracker] chain OK ({status.rows_verified} rows); serving on stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
