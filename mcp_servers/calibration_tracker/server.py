"""FastMCP server for calibration-tracker (design v3, Server 1).

Tools wrap CalibrationStore; ForecastError → ToolError. Nothing writes to stdout (the stdio JSON-RPC
channel); logs go to stderr. `analyst_id` is a trusted local binding inside the store, never a tool arg.
"""

from __future__ import annotations

import os
import sys
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .models import (
    CalibrationReport,
    ChainStatus,
    ForecastList,
    ForecastRecord,
)
from .store import CalibrationStore, ForecastError

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "..", "data", "calibration.db")
DB_PATH = os.environ.get("CALIBRATION_DB", _DEFAULT_DB)
if DB_PATH != ":memory:":
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

store = CalibrationStore(DB_PATH)
# mask_error_details=True (N1): only explicit ToolError messages reach the client; an unexpected
# exception is masked so DB paths / SQL fragments never leak over the wire.
mcp = FastMCP("calibration-tracker", mask_error_details=True)


@mcp.tool
def log_forecast(
    case_id: Annotated[str, Field(max_length=200, description="Analytic case this forecast belongs to.")],
    question: Annotated[
        str,
        Field(
            max_length=4000,
            description="The yes/no question. `probability` is P(this resolves YES).",
        ),
    ],
    probability: Annotated[
        float,
        Field(ge=0.0, le=1.0, description="P(question resolves YES, i.e. outcome=True), in [0,1]."),
    ],
    resolution_criteria: Annotated[
        str, Field(max_length=4000, description="Clairvoyance-style definition of what counts as YES.")
    ],
    horizon: Annotated[
        str,
        Field(
            max_length=500,
            description="When it resolves — an ISO date (2026-12-31) or ISO-8601 duration (P30D). Locked forever.",
        ),
    ],
    judgment_source: Annotated[
        Literal["analyst_confirmed"],
        Field(
            description="Must be 'analyst_confirmed'. The caller ATTESTS the judgment is human-confirmed; "
            "this tool does not independently verify it (see judgment_source in the return value)."
        ),
    ] = "analyst_confirmed",
    rationale: Annotated[str, Field(max_length=4000, description="Optional reasoning for the judgment.")] = "",
) -> ForecastRecord:
    """Log a NEW forecast and LOCK its question + probability (only outcomes/voids are appended later).
    `probability` is the analyst's judgment = P(question resolves YES). `judgment_source` is a caller
    attestation ('analyst_confirmed'), not an independently verified control.

    Idempotency: a byte-identical retry (every field equal) within a 5-second window returns the ORIGINAL
    forecast_id instead of appending a duplicate row; any differing field is a new forecast.

    Returns the full locked ForecastRecord so the caller can confirm the immutable fields
    (probability, question, resolution_criteria, horizon) from this call's own response.
    """
    try:
        return store.log_forecast(
            case_id, question, probability, resolution_criteria, horizon, judgment_source, rationale
        )
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def resolve_forecast(
    forecast_id: Annotated[
        str, Field(max_length=200, description="The forecast_id returned by log_forecast.")
    ],
    outcome: Annotated[bool, Field(description="True = the question resolved YES.")],
    resolved_at: Annotated[
        str, Field(description="ISO-8601 date/datetime the outcome was known; must be >= the forecast's locked_at.")
    ],
    is_correction: Annotated[
        bool,
        Field(description="False = first resolution. True = append a SUPERSEDING correction (needs a reason)."),
    ] = False,
    reason: Annotated[str, Field(max_length=4000, description="Required (non-empty) when is_correction=True.")] = "",
) -> ForecastRecord:
    """Append the OUTCOME to a locked forecast. First resolution: is_correction=False. To fix a wrong
    outcome: is_correction=True + non-empty reason (appends a superseding resolution; never edits)."""
    try:
        return store.resolve_forecast(forecast_id, outcome, resolved_at, is_correction, reason)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def void_forecast(
    forecast_id: Annotated[
        str, Field(max_length=200, description="The forecast_id returned by log_forecast.")
    ],
    reason: Annotated[
        str, Field(max_length=4000, description="Why it is mis-logged; non-empty and recorded in the ledger.")
    ],
) -> ForecastRecord:
    """Flag a MIS-LOGGED forecast as excluded from Brier scoring. PRE-RESOLUTION ONLY (errors if resolved)."""
    try:
        return store.void_forecast(forecast_id, reason)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_forecast(
    forecast_id: Annotated[
        str, Field(max_length=200, description="The forecast_id returned by log_forecast.")
    ],
) -> ForecastRecord:
    """Read one forecast (with its effective outcome / voided status)."""
    try:
        return store.get_forecast(forecast_id)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def list_forecasts(
    case_id: Annotated[
        str | None, Field(default=None, max_length=200, description="Filter to one analytic case; omit for all.")
    ] = None,
    resolved: Annotated[
        bool | None,
        Field(description="Filter: None=all, True=only resolved, False=only unresolved."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=1000, description="Max items per page (1..1000).")] = 100,
    cursor: Annotated[
        str | None, Field(description="Opaque pagination token from a prior next_cursor; omit for the first page.")
    ] = None,
) -> ForecastList:
    """Read-back with filters + pagination. Pass the returned `next_cursor` back as `cursor` for the next page."""
    try:
        return store.list_forecasts(case_id, resolved, limit, cursor)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_calibration_report(
    case_id: Annotated[
        str | None, Field(default=None, max_length=200, description="Scope the report to one case; omit for all.")
    ] = None,
) -> CalibrationReport:
    """COMPUTE Brier + a calibration table + Murphy resolution/reliability over analyst_confirmed, non-voided,
    resolved forecasts. Read-only; no judgment invented."""
    try:
        return store.get_calibration_report(case_id)
    except ForecastError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def verify_chain() -> ChainStatus:
    """Verify the append-only hash chains + the external manifest (tamper / whole-chain-deletion evidence).
    Integrity is table-wide by construction; it cannot be scoped to a single case (scope is always 'all')."""
    try:
        return store.verify_chain()
    except ForecastError as e:
        raise ToolError(str(e)) from e


def main() -> None:
    status = store.verify_chain()
    if not status.ok:
        print(f"[calibration-tracker] REFUSING TO SERVE — chain verify failed: {status.mismatch}", file=sys.stderr)
        raise SystemExit(1)
    print(f"[calibration-tracker] chain OK ({status.rows_verified} rows); serving on stdio", file=sys.stderr)
    # show_banner=False (N2): the default banner does a "newer version" HTTP check — suppressed to
    # honour this repo's no-egress discipline (only the osint server is permitted network egress).
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
