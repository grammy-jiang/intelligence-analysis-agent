"""FastMCP server for ach-engine (design v3, Server 3)."""

from __future__ import annotations

import functools
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..common import ChainStatus
from ..staleness import StalenessStore
from .models import CellRecord, Consistency, JudgmentSource, Matrix, MatrixList, MatrixRef, Ranking, Strength
from .store import ACHError, ACHStore

_DATA = Path(__file__).resolve().parent.parent.parent / "data"


def _resolve_db(env: str, default_name: str) -> str:
    """Resolve a DB path from env (or default) and make its directory private.

    SF16: one resolved path is reused for makedirs + connect (no unnormalized `..`, robust to
    os.chdir). MF5/N8: the tamper-evidence guarantee rests on OS file-permission isolation of the
    DB/manifest from any other local writer, so the containing directory is created 0700 (the store
    sets 0600 on the DB + manifest files themselves)."""
    raw = os.environ.get(env, str(_DATA / default_name))
    if raw == ":memory:":
        return raw
    p = Path(raw).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:  # best-effort; a shared/managed dir may forbid chmod
        pass
    return str(p)


DB_PATH = _resolve_db("ACH_DB", "ach.db")
STALENESS_DB = _resolve_db("STALENESS_DB", "staleness.db")

staleness = StalenessStore(STALENESS_DB)
store = ACHStore(DB_PATH, staleness)

# SF1: self-description — the lifecycle, the analyst-supplies-judgment trust model, the hard
# evidence-ledger scoring dependency, and (MF5) the residual unkeyed-chain risk, surfaced up front.
_INSTRUCTIONS = """ach-engine (design v3, Server 3): an append-only, hash-chained ACH (Analysis of
Competing Hypotheses) matrix. The analyst supplies every judgment; this server only records ratings
faithfully and computes the ranking by LEAST-TOTAL-INCONSISTENCY (Heuer) — it never decides.

Lifecycle: create_matrix (mint a stable hypothesis_id per hypothesis) -> rate_cell (one
evidence x hypothesis consistency rating at a time) -> score_matrix (rank once every cell is
rateable) -> get_matrix / list_matrices to read back. add_hypothesis grows the matrix mid-analysis.

Scoring gate (collect-then-grade; the cross-server dependency): score_matrix REFUSES to rank until
every evidence item is rated against every hypothesis (no coverage gaps), AND every rated evidence
item carries an out-of-band `analyst_confirmed` grade in evidence-ledger, AND no cell is stale or
`model_draft`. It enumerates the blocking cells in the error. `analyst_confirmed` is NOT
self-attestable on a rating — record an agent's own read as `model_draft` and confirm the evidence
in evidence-ledger.

Integrity: verify_chain checks the append-only chains reconciled against a manifest (tail-truncation
evidence); it is ALWAYS GLOBAL. NOTE: this is an UNKEYED SHA-256 hash chain — its tamper-evidence
rests entirely on OS file-permission isolation of the DB + manifest (kept 0600) from any other local
writer, INCLUDING a co-resident agent that also holds a filesystem/bash tool. It is NOT protection
against an actor who can rewrite the files and recompute the chain forward.

No network egress."""

# mask_error_details=True (MF2): only explicit ToolError messages reach the client; any other
# exception (sqlite3.OperationalError, disk-full, an internal bug) is masked so DB paths / SQL or
# schema fragments never leak over the wire. Business-rule errors are raised as ToolError below.
mcp = FastMCP("ach-engine", instructions=_INSTRUCTIONS, mask_error_details=True)

# SF3: input-size caps. The tables are append-only with no reclamation, so one oversized call would
# persist forever and drag verify_chain's full-table scan (and enable a cheap DoS).
_MAX_ID = 512
_MAX_TEXT = 10_000
_MAX_HYPOTHESES = 64


def _translate_ach_errors(fn: Callable) -> Callable:
    """SF13: every tool maps a business-rule ACHError to a FastMCP ToolError identically.

    functools.wraps preserves the wrapped signature/annotations so FastMCP still derives the input
    and output schemas (incl. the Annotated Field descriptions) from the real parameters."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return fn(*args, **kwargs)
        except ACHError as e:
            raise ToolError(str(e)) from e

    return wrapper


@mcp.tool
@_translate_ach_errors
def create_matrix(
    case_id: Annotated[str, Field(max_length=_MAX_ID, description="The ACH case / investigation this matrix belongs to.")],
    hypotheses: Annotated[
        list[str],
        Field(
            max_length=_MAX_HYPOTHESES,
            description="The initial competing hypotheses. Mutual-exclusivity is the ANALYST's "
            "responsibility; the tool only checks each is non-empty. Each is minted a stable "
            "synthetic hypothesis_id independent of its wording.",
        ),
    ],
) -> MatrixRef:
    """Create the ACH matrix; MINT a stable synthetic hypothesis_id per hypothesis (independent of wording).
    Mutual-exclusivity is the ANALYST's responsibility — the tool only checks each hypothesis is non-empty."""
    return store.create_matrix(case_id, hypotheses)


@mcp.tool
@_translate_ach_errors
def add_hypothesis(
    matrix_id: Annotated[str, Field(max_length=_MAX_ID, description="The matrix to append the hypothesis column to.")],
    hypothesis: Annotated[str, Field(max_length=_MAX_TEXT, description="The new hypothesis text.")],
) -> MatrixRef:
    """Append a new hypothesis column mid-analysis (append-only; prior cells intact). The new column
    starts with ABSENT cells against all existing evidence — score_matrix REFUSES to rank the matrix
    until every evidence item has been rated against it (an unrated cell is a coverage-gap blocker)."""
    return store.add_hypothesis(matrix_id, hypothesis)


@mcp.tool
@_translate_ach_errors
def rate_cell(
    matrix_id: Annotated[str, Field(max_length=_MAX_ID, description="The matrix this cell belongs to.")],
    evidence_id: Annotated[
        str, Field(max_length=_MAX_ID, description="The evidence item (as registered in evidence-ledger) being rated.")
    ],
    hypothesis_id: Annotated[
        str, Field(max_length=_MAX_ID, description="The synthetic hypothesis_id from create_matrix / add_hypothesis.")
    ],
    consistency: Annotated[
        Consistency,
        Field(
            description="How the evidence bears on the hypothesis — 'C' consistent, 'I' inconsistent, "
            "'N/A' not applicable (excluded from scoring)."
        ),
    ],
    strength: Annotated[
        Strength,
        Field(
            description="Weight of an inconsistency — 'strong' or 'weak' (strong dominates the ranking). "
            "Only read when consistency=='I'; supply 'weak' as a placeholder for 'C'/'N/A' cells."
        ),
    ],
    judgment_source: Annotated[
        JudgmentSource,
        Field(
            description="'model_draft' for an agent's own draft (score_matrix REFUSES to score it until "
            "re-rated), or 'analyst_confirmed'. `analyst_confirmed` is NOT self-attestable: it is accepted "
            "only when the evidence already carries an out-of-band analyst_confirmed grade in "
            "evidence-ledger; otherwise record the rating as model_draft."
        ),
    ],
    reason: Annotated[
        str, Field(max_length=_MAX_TEXT, description="Required (non-empty) when superseding an existing rating (a correction).")
    ] = "",
) -> CellRecord:
    """Append a consistency RATING for one (evidence × hypothesis) cell (required input).

    Errors on unknown matrix_id/hypothesis_id, blank evidence_id, an out-of-domain rating value, or an
    unbacked analyst_confirmed."""
    return store.rate_cell(matrix_id, evidence_id, hypothesis_id, consistency, strength, judgment_source, reason)


@mcp.tool
@_translate_ach_errors
def score_matrix(matrix_id: Annotated[str, Field(max_length=_MAX_ID, description="The matrix to rank.")]) -> Ranking:
    """COMPUTE the ranking by LEAST-TOTAL-INCONSISTENCY (fewest strong inconsistencies leads; ties → fewer
    weak; N/A excluded), flag non-diagnostic evidence. REFUSES if any hypothesis has an unrated cell
    (coverage gap), or any effective cell is stale, model_draft, or evidence not analyst_confirmed-graded
    — enumerating the blocking cells in the error."""
    return store.score_matrix(matrix_id)


@mcp.tool
@_translate_ach_errors
def get_matrix(matrix_id: Annotated[str, Field(max_length=_MAX_ID, description="The matrix to read.")]) -> Matrix:
    """Read the matrix + effective cells. `stale` is best-effort and MAY lag — score_matrix is the sole
    source of truth for scoring-readiness."""
    return store.get_matrix(matrix_id)


@mcp.tool
@_translate_ach_errors
def list_matrices(
    case_id: Annotated[str, Field(max_length=_MAX_ID, description="The case whose matrices to list.")],
    limit: Annotated[int, Field(ge=1, le=1000, description="Max matrices to return (1–1000).")] = 100,
    cursor: Annotated[
        str | None, Field(max_length=_MAX_ID, description="Opaque token from a prior next_cursor.")
    ] = None,
) -> MatrixList:
    """Read-back for a case with pagination. `cursor` is an opaque token from a prior next_cursor."""
    return store.list_matrices(case_id, limit, cursor)


@mcp.tool
@_translate_ach_errors
def verify_chain() -> ChainStatus:
    """Verify the append-only hash chains (tamper evidence), reconciled against the manifest so
    trailing-row truncation is detected. Verification is ALWAYS GLOBAL (the whole store, never a single
    case). STOP and escalate if the result has ok=False."""
    return store.verify_chain()


def main() -> None:
    for label, st in (("ach-engine", store.verify_chain()), ("evidence-signals", staleness.verify_chain())):
        if not st.ok:
            print(f"[ach-engine] REFUSING TO SERVE — {label} chain failed: {st.mismatch}", file=sys.stderr)
            raise SystemExit(1)
    print("[ach-engine] chains OK; serving on stdio", file=sys.stderr)
    # SF15: transport="stdio", show_banner=False — the default FastMCP banner performs a "newer
    # version" HTTP check; suppressed to honour this repo's no-egress discipline (only osint egresses).
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
