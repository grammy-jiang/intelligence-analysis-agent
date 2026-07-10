"""FastMCP server for evidence-ledger (design v3, Server 2)."""

from __future__ import annotations

import os
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..common import ChainStatus
from ..staleness import StalenessStore
from .models import (
    Credibility,
    EvidenceList,
    EvidenceRecord,
    EvidenceRef,
    EvidenceType,
    JudgmentSource,
    Reliability,
    SourceChannel,
    SourceHistory,
)
from .store import EvidenceError, EvidenceStore

_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.environ.get("EVIDENCE_DB", os.path.join(_DATA, "evidence.db"))
STALENESS_DB = os.environ.get("STALENESS_DB", os.path.join(_DATA, "staleness.db"))
for p in (DB_PATH, STALENESS_DB):
    if p != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)

staleness = StalenessStore(STALENESS_DB)
store = EvidenceStore(DB_PATH, staleness)
mcp = FastMCP("evidence-ledger")


@mcp.tool
def add_evidence(
    case_id: str,
    item: str,
    source_id: str,
    evidence_type: EvidenceType,
    pii: bool,
    source_channel: SourceChannel,
    expected_observables: dict[str, str] | None = None,
) -> EvidenceRef:
    """Store a RAW evidence item (no grade yet). `pii` is REQUIRED (no default — source identity is
    life-safety). `expected_observables` maps hypothesis_id → 'should see / not see'. Returns a reference
    with NO content fields."""
    try:
        return store.add_evidence(
            case_id, item, source_id, evidence_type, pii, source_channel, expected_observables
        )
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def grade_evidence(
    evidence_id: str,
    reliability: Reliability,
    credibility: Credibility,
    diagnosticity: str,
    judgment_source: JudgmentSource,
    rationale: str = "",
) -> EvidenceRecord:
    """Append the FIRST grade (accepts model_draft or analyst_confirmed; only analyst_confirmed enters the
    cross-case source-trust record). reliability A–F + credibility 1–6 are two INDEPENDENT required inputs.
    `diagnosticity` is a NARRATIVE annotation only — it does NOT feed score_matrix. Errors if a grade already
    exists (use update_grade). Marks dependent ACH cells stale."""
    try:
        return store.grade_evidence(evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale)
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def update_grade(
    evidence_id: str,
    reliability: Reliability,
    credibility: Credibility,
    diagnosticity: str,
    reason: str,
    judgment_source: JudgmentSource,
    rationale: str = "",
) -> EvidenceRecord:
    """Append a SUPERSEDING grade (required `reason`; never edits). Errors if no prior grade exists. Re-marks
    dependent ACH cells stale."""
    try:
        return store.update_grade(
            evidence_id, reliability, credibility, diagnosticity, reason, judgment_source, rationale
        )
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_evidence(evidence_id: str, redact_pii: bool = True) -> EvidenceRecord:
    """Read one evidence item + its grade history. `pii` items return item='REDACTED' unless redact_pii=False
    (which the host's confirmation policy should gate — source identity is life-safety)."""
    try:
        return store.get_evidence(evidence_id, redact_pii)
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def list_evidence(
    case_id: str, redact_pii: bool = True, limit: int = 100, cursor: str | None = None
) -> EvidenceList:
    """Read-back for a case with pagination."""
    return store.list_evidence(case_id, redact_pii, limit, cursor)


@mcp.tool
def get_source_history(source_id: str, redact_pii: bool = True) -> SourceHistory:
    """CROSS-CASE view (folded source-trust-registry): the ordered sequence of this source's
    `analyst_confirmed` grades + the direction of the most recent change. A transparent RECORD, not a
    synthesized trust score; model_draft grades are excluded (and counted)."""
    return store.get_source_history(source_id, redact_pii)


@mcp.tool
def verify_chain(case_id: str | None = None) -> ChainStatus:
    """Verify the append-only hash chains (tamper evidence)."""
    return store.verify_chain(case_id)


@mcp.tool
def verify_signals_chain() -> ChainStatus:
    """Verify the shared cross-server signal store (stale_events + grade_signals) that ach-engine's
    collect-then-grade gate depends on."""
    return staleness.verify_chain()


def main() -> None:
    for label, st in (("evidence-ledger", store.verify_chain()), ("evidence-signals", staleness.verify_chain())):
        if not st.ok:
            print(f"[evidence-ledger] REFUSING TO SERVE — {label} chain failed: {st.mismatch}", file=sys.stderr)
            raise SystemExit(1)
    print("[evidence-ledger] chains OK; serving on stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
