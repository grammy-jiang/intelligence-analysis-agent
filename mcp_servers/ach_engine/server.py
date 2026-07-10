"""FastMCP server for ach-engine (design v3, Server 3)."""

from __future__ import annotations

import os
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..common import ChainStatus
from ..staleness import StalenessStore
from .models import CellRecord, Consistency, JudgmentSource, Matrix, MatrixList, MatrixRef, Ranking, Strength
from .store import ACHError, ACHStore

_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.environ.get("ACH_DB", os.path.join(_DATA, "ach.db"))
STALENESS_DB = os.environ.get("STALENESS_DB", os.path.join(_DATA, "staleness.db"))
for p in (DB_PATH, STALENESS_DB):
    if p != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)

staleness = StalenessStore(STALENESS_DB)
store = ACHStore(DB_PATH, staleness)
mcp = FastMCP("ach-engine")


@mcp.tool
def create_matrix(case_id: str, hypotheses: list[str]) -> MatrixRef:
    """Create the ACH matrix; MINT a stable synthetic hypothesis_id per hypothesis (independent of wording).
    Mutual-exclusivity is the ANALYST's responsibility — the tool only checks non-empty."""
    try:
        return store.create_matrix(case_id, hypotheses)
    except ACHError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def add_hypothesis(matrix_id: str, hypothesis: str) -> MatrixRef:
    """Append a new hypothesis column mid-analysis (append-only; prior cells intact)."""
    try:
        return store.add_hypothesis(matrix_id, hypothesis)
    except ACHError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def rate_cell(
    matrix_id: str,
    evidence_id: str,
    hypothesis_id: str,
    consistency: Consistency,
    strength: Strength,
    judgment_source: JudgmentSource,
    reason: str = "",
) -> CellRecord:
    """Append a consistency RATING for one (evidence × hypothesis) cell (required input). Supersede to change
    (non-empty `reason` required on a correction). Errors on unknown matrix_id/hypothesis_id."""
    try:
        return store.rate_cell(matrix_id, evidence_id, hypothesis_id, consistency, strength, judgment_source, reason)
    except ACHError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def score_matrix(matrix_id: str) -> Ranking:
    """COMPUTE the ranking by LEAST-TOTAL-INCONSISTENCY (fewest strong inconsistencies leads; ties → fewer
    weak; N/A excluded), flag non-diagnostic evidence. REFUSES if any effective cell is stale or model_draft,
    enumerating the blocking cells in the error."""
    try:
        return store.score_matrix(matrix_id)
    except ACHError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_matrix(matrix_id: str) -> Matrix:
    """Read the matrix + effective cells. `stale` is best-effort and MAY lag — score_matrix is the sole
    source of truth for scoring-readiness."""
    try:
        return store.get_matrix(matrix_id)
    except ACHError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def list_matrices(case_id: str, limit: int = 100, cursor: str | None = None) -> MatrixList:
    """Read-back for a case with pagination."""
    return store.list_matrices(case_id, limit, cursor)


@mcp.tool
def verify_chain(case_id: str | None = None) -> ChainStatus:
    """Verify the append-only hash chains (tamper evidence)."""
    return store.verify_chain(case_id)


def main() -> None:
    for label, st in (("ach-engine", store.verify_chain()), ("evidence-signals", staleness.verify_chain())):
        if not st.ok:
            print(f"[ach-engine] REFUSING TO SERVE — {label} chain failed: {st.mismatch}", file=sys.stderr)
            raise SystemExit(1)
    print("[ach-engine] chains OK; serving on stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
