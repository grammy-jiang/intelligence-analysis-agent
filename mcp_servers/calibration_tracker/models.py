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
        default=None,
        description="Effective resolved outcome (latest resolution); True=YES. None if unresolved.",
    )
    resolved_at: str | None = None
    voided: bool = False
    was_corrected: bool = Field(
        default=False, description="True if the outcome was superseded by at least one correction."
    )
    correction_count: int = Field(
        default=0,
        description="Number of correction resolutions appended after the first resolution.",
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
        default=0,
        description="Count of scored forecasts whose outcome was later corrected (audit signal).",
    )
    resolved_before_horizon: int = Field(
        default=0,
        description=(
            "ADVISORY audit signal (NOT a correctness failure): count of resolved forecasts whose "
            "resolved_at fell strictly BEFORE a stated, ISO-8601-parseable horizon — surfaced for human "
            "review of possible premature/hindsight resolution. Early resolution is legitimate (an outcome "
            "can be known before the stated deadline). A non-date horizon — free-form ('end of Q2') OR an "
            "ISO-8601 DURATION ('P30D') — is skipped (see n_horizon_checked/n_horizon_skipped for coverage; "
            "resolved_within_min_latency is the locked_at-anchored companion signal — harder to game, not "
            "ungameable)."
        ),
    )
    n_horizon_checked: int = Field(
        default=0,
        description=(
            "Coverage denominator for resolved_before_horizon: resolutions whose horizon parsed as an "
            "ISO-8601 date and was actually compared. resolved_before_horizon=0 WITH n_horizon_checked=0 "
            "means NO coverage (every horizon was free-form/duration), not 'no premature resolutions'."
        ),
    )
    n_horizon_skipped: int = Field(
        default=0,
        description=(
            "Resolutions whose horizon did not parse as an ISO-8601 date — free-form ('end of Q2') OR an "
            "ISO-8601 DURATION ('P30D') — and so contributed no horizon signal."
        ),
    )
    resolved_within_min_latency: int = Field(
        default=0,
        description=(
            "ADVISORY audit signal keyed to the SERVER-authored locked_at (not the analyst-authored horizon): "
            "count of forecasts resolved within 24h of lock WHERE the horizon could not certify the timing — an "
            "unparseable horizon, a resolution before its horizon, OR a horizon set less than an hour past the "
            "lock (too near to vouch, so a self-chosen near-instant horizon cannot launder a fast self-grade). "
            "Flags the log-then-self-grade pattern the horizon signal misses, without flagging a genuine "
            "short-fuse forecast. resolved_at is bounded to real time, so the gap is real; residual: an analyst "
            "can still wait out the 24h window (or a genuine horizon) before self-grading. Advisory, not a gate; "
            "early resolution is legitimate."
        ),
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
