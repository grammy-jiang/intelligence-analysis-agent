"""Pydantic I/O models for the calibration-tracker MCP server (design v3, Server 1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JudgmentSource = Literal["analyst_confirmed", "model_draft"]


class ForecastRef(BaseModel):
    """Returned by log_forecast — non-content acknowledgment."""

    forecast_id: str
    case_id: str
    locked_at: str


class ForecastRecord(BaseModel):
    forecast_id: str
    case_id: str
    question: str
    probability: float = Field(
        description="Analyst's judgment: P(question resolves YES, i.e. the resolution outcome is True), in [0,1]."
    )
    resolution_criteria: str
    horizon: str
    analyst_id: str
    judgment_source: JudgmentSource
    rationale: str = ""
    locked_at: str
    outcome: bool | None = Field(
        default=None, description="Effective resolved outcome (latest resolution); True=YES. None if unresolved."
    )
    resolved_at: str | None = None
    voided: bool = False
    was_corrected: bool = Field(
        default=False, description="True if the outcome was superseded by at least one correction."
    )
    correction_count: int = Field(
        default=0, description="Number of correction resolutions appended after the first resolution."
    )
    row_hash: str = Field(
        description="Internal chain-integrity hash of the forecast row — NOT a judgment or score."
    )


class ForecastList(BaseModel):
    items: list[ForecastRecord]
    next_cursor: str | None = None


class Bucket(BaseModel):
    p_range: str
    n: int
    observed_freq: float | None


class CalibrationReport(BaseModel):
    n: int
    n_voided: int
    n_corrected: int = Field(
        default=0, description="Count of scored forecasts whose outcome was later corrected (audit signal)."
    )
    brier: float | None
    buckets: list[Bucket]
    resolution_component: float | None = Field(
        default=None,
        description="Murphy resolution component; higher = better discrimination.",
    )
    reliability_component: float | None = Field(
        default=None,
        description="Murphy reliability component; lower = better calibrated.",
    )
    note: str


class ChainMismatch(BaseModel):
    table: str
    row_id: str
    expected_hash: str
    got_hash: str


class ChainStatus(BaseModel):
    server: str
    scope: str
    ok: bool
    head_hash: dict[str, str]
    rows_verified: int
    mismatch: ChainMismatch | None = None
