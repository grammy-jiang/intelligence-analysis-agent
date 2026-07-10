"""Shared hash-chain helpers + chain-status models for the MCP state layer (design v3)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel

GENESIS = "0" * 64


def canon(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def row_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + canon(payload)).encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
