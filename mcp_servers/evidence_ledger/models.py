"""Pydantic I/O models for the evidence-ledger MCP server (design v3, Server 2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Reliability = Literal["A", "B", "C", "D", "E", "F"]
Credibility = Literal["1", "2", "3", "4", "5", "6"]
EvidenceType = Literal["report", "assumption", "deduction", "absence"]
SourceChannel = Literal["analyst_typed", "ingested"]
JudgmentSource = Literal["analyst_confirmed", "model_draft"]

RELIABILITY_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}


class EvidenceRef(BaseModel):
    """Returned by add_evidence — NEVER carries `item` (redaction gate applies to all item reads)."""

    evidence_id: str
    case_id: str
    pii: bool


class Grade(BaseModel):
    reliability: Reliability
    credibility: Credibility
    diagnosticity: str  # narrative only — does NOT feed score_matrix
    judgment_source: JudgmentSource
    rationale: str = ""
    reason: str = ""
    graded_at: str
    superseded: bool


class EvidenceRecord(BaseModel):
    evidence_id: str
    case_id: str
    item: str  # "REDACTED" when pii and redact_pii
    source_id: str
    evidence_type: EvidenceType
    source_channel: SourceChannel
    expected_observables: dict[str, str]
    grades: list[Grade]
    pii: bool
    row_hash: str


class EvidenceList(BaseModel):
    items: list[EvidenceRecord]
    next_cursor: str | None = None


class SourceHistory(BaseModel):
    source_id: str
    cases: list[str]
    grade_sequence: list[str]  # reliability letters of analyst_confirmed grades, in order
    last_change_direction: str  # improved | worsened | same | n/a
    n: int
    n_model_draft_excluded: int
