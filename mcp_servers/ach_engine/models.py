"""Pydantic I/O models for the ach-engine MCP server (design v3, Server 3)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Consistency = Literal["C", "I", "N/A"]
Strength = Literal["strong", "weak"]
JudgmentSource = Literal["analyst_confirmed", "model_draft"]


class HypothesisItem(BaseModel):
    hypothesis_id: str
    text: str


class MatrixRef(BaseModel):
    matrix_id: str
    case_id: str
    hypotheses: list[HypothesisItem]


class Cell(BaseModel):
    evidence_id: str
    hypothesis_id: str
    consistency: Consistency
    strength: Strength
    judgment_source: JudgmentSource
    # M5 (human-gate visibility): reason of the effective rating + whether this (evidence × hypothesis) cell
    # was re-rated at least once. get_matrix is the human gate before score_matrix, so it must surface a
    # confirm-then-re-rate, not only the final effective values.
    reason: str = ""
    superseded: bool = False
    stale: bool
    stale_reason: str | None = None
    rated_at: str


class Matrix(BaseModel):
    matrix_id: str
    case_id: str
    hypotheses: list[HypothesisItem]
    cells: list[Cell]


class CellRecord(BaseModel):
    matrix_id: str
    evidence_id: str
    hypothesis_id: str
    consistency: Consistency
    strength: Strength
    judgment_source: JudgmentSource
    reason: str = ""
    rated_at: str
    superseded: bool
    row_hash: str


class RankItem(BaseModel):
    hypothesis_id: str
    strong_inconsistencies: int
    weak_inconsistencies: int


class Ranking(BaseModel):
    ordered: list[RankItem]
    non_diagnostic: list[str]
    leading: str | None


class MatrixList(BaseModel):
    items: list[MatrixRef]
    next_cursor: str | None = None
