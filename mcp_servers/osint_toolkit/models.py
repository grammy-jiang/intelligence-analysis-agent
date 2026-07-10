"""Pydantic I/O for osint-toolkit (design v3, Layer 4). Every result is a CANDIDATE — inert data, never a fact."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Connector = Literal["web", "image", "map"]
SourceChannel = Literal["ingested"]

# per-connector fully-qualified hostname allowlist (no wildcards). Placeholder hosts until live keys/config.
CONNECTOR_HOSTS: dict[str, set[str]] = {
    "web": {"api.example-search.invalid"},
    "image": {"api.example-image.invalid"},
    "map": {"tile.example-map.invalid"},
}


class Candidate(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""


class SearchResult(BaseModel):
    connector: Connector
    source_channel: SourceChannel = "ingested"
    candidates: list[Candidate]


class FetchedArtifact(BaseModel):
    artifact_ref: str
    host: str
    content_type: str | None
    sha256: str
    size: int
    source_channel: SourceChannel = "ingested"


class ExifData(BaseModel):
    artifact_ref: str
    candidate: bool = True  # a proposal for human confirmation, never a verified location
    detected_type: str | None
    fields: dict[str, str]
    note: str


class HashResult(BaseModel):
    artifact_ref: str
    sha256: str


class CandidateMatches(BaseModel):
    connector: Connector
    source_channel: SourceChannel = "ingested"
    candidates: list[Candidate]


class MapTile(BaseModel):
    artifact_ref: str | None
    lat: float
    lon: float
    zoom: int
    candidate: bool = True


class ProposalRef(BaseModel):
    evidence_id: str
    case_id: str
    source_channel: SourceChannel = "ingested"
