"""FastMCP server for evidence-ledger (design v3, Server 2)."""

from __future__ import annotations

import os
import sys
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..common import ChainStatus, verify_stable
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

_INSTRUCTIONS = """evidence-ledger (design v3, Server 2): an append-only, hash-chained record of evidence
and its A–F / 1–6 grades. Lifecycle: add_evidence (raw item, no grade) -> grade_evidence (first grade)
-> update_grade (superseding correction; never edits) -> get_evidence / list_evidence to read back.

Trust model (the analyst supplies judgment; this server only records it faithfully):
- `judgment_source` is caller-asserted provenance, and the analyst's identity is a trusted LOCAL binding
  (EVIDENCE_ANALYST_ID), never a tool argument. The load-bearing human gate lives in the calling
  workflow/skill, not inside this server — a grade marked `analyst_confirmed` asserts a human confirmed it.
- ach-engine REFUSES to SCORE any ACH cell whose evidence's latest grade is not `analyst_confirmed`
  (collect-then-grade). If you graded `model_draft`, re-grade via update_grade(..., analyst_confirmed).
- PII items redact by default; unredaction is host-gated (set EVIDENCE_ALLOW_UNREDACT) — source identity
  is life-safety.
- `item` is IMMUTABLE once stored: there is no edit tool. Correct a mis-entry with a NEW add_evidence.
No network egress."""

# mask_error_details=True: this is the trio's life-safety server. Any non-ToolError exception
# (sqlite3.OperationalError, disk-full, an internal bug) must NOT surface raw text — it could leak
# DB_PATH, SQL/schema fragments, or internals to the caller. Business-rule errors are raised as
# ToolError (with a deliberate message) and are unaffected by this mask.
mcp = FastMCP("evidence-ledger", instructions=_INSTRUCTIONS, mask_error_details=True)

# S7: input size caps (append-only, no delete/edit → an ingested pipeline could otherwise persist
# arbitrarily large payloads with no reclamation, degrading verify_chain full-table scans and DB size).
_MAX_ITEM = 100_000
_MAX_ID = 512
_MAX_TEXT = 10_000
_MAX_OBSERVABLES = 256
# DoS: cap each observable KEY and VALUE, not only the entry count — one entry with a giant value
# ({"h": "A"*50_000_000}) would otherwise pass the count check and persist into the append-only row.
_MAX_OBSERVABLE_VAL = 2000
# MF2: the host-gate opt-in is an explicit ALLOW-LIST of truthy tokens, not env-var presence. os.environ.get
# returns a non-empty string for EVIDENCE_ALLOW_UNREDACT=0 / =false (an operator's intent to DISABLE), which is
# truthy in Python — so a presence check would grant life-safety unredaction on a value meant to deny it.
_UNREDACT_TRUTHY = {"1", "true", "yes", "on"}


def _require_unredact_permitted(redact_pii: bool) -> None:
    """MF2: unredaction (redact_pii=False) exposes source-identifying PII — life-safety. A same-call
    boolean from the caller is not enough; the HOST must opt in out-of-band by setting EVIDENCE_ALLOW_UNREDACT
    to an explicit truthy value (1/true/yes/on). Any other value — including '0'/'false'/'' — denies."""
    allowed = os.environ.get("EVIDENCE_ALLOW_UNREDACT", "").strip().lower() in _UNREDACT_TRUTHY
    if not redact_pii and not allowed:
        raise ToolError(
            "unredaction refused: reading PII items unredacted requires host approval "
            "(EVIDENCE_ALLOW_UNREDACT is not set). Source identity is life-safety."
        )


@mcp.tool
def add_evidence(
    case_id: Annotated[str, Field(max_length=_MAX_ID)],
    item: Annotated[str, Field(max_length=_MAX_ITEM)],
    source_id: Annotated[str, Field(max_length=_MAX_ID)],
    evidence_type: EvidenceType,
    pii: bool,
    source_channel: SourceChannel,
    expected_observables: dict[str, str] | None = None,
) -> EvidenceRef:
    """Store a RAW evidence item (no grade yet). Returns a reference with NO content fields.

    - `case_id`: the ACH case / investigation this item belongs to.
    - `item`: the raw evidence text (the report, observation, or artifact content). IMMUTABLE once
      stored — there is NO edit tool; correct a mistake with a new add_evidence.
    - `source_id`: stable identifier of the originating source (feeds the cross-case source-trust record).
    - `evidence_type`: one of report | assumption | deduction | absence
      (`absence` = an absence-of-expected-evidence signal, itself diagnostic).
    - `pii`: REQUIRED, no default — True if `item` identifies a human source (source identity is
      life-safety; PII items redact by default on read).
    - `source_channel`: analyst_typed (human-entered) or ingested (from an untrusted external pipeline).
      An `ingested` item is UNTRUSTED pipeline output; the human gate that turns a grade into
      `analyst_confirmed` lives in the calling workflow, not this server (see the trust model above).
    - `expected_observables`: maps hypothesis_id -> 'should see' / 'should not see' under that hypothesis
      (at most 256 entries).
    """
    if expected_observables is not None:
        if len(expected_observables) > _MAX_OBSERVABLES:
            raise ToolError(f"expected_observables has too many entries (max {_MAX_OBSERVABLES}).")
        for k, v in expected_observables.items():
            if len(k) > _MAX_ID:
                raise ToolError(f"an expected_observables key exceeds max length {_MAX_ID}.")
            if len(v) > _MAX_OBSERVABLE_VAL:
                raise ToolError(
                    f"an expected_observables value exceeds max length {_MAX_OBSERVABLE_VAL}."
                )
    try:
        return store.add_evidence(
            case_id, item, source_id, evidence_type, pii, source_channel, expected_observables
        )
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def grade_evidence(
    evidence_id: Annotated[str, Field(max_length=_MAX_ID)],
    reliability: Reliability,
    credibility: Credibility,
    diagnosticity: Annotated[str, Field(max_length=_MAX_TEXT)],
    judgment_source: JudgmentSource,
    rationale: Annotated[str, Field(max_length=_MAX_TEXT)] = "",
) -> EvidenceRecord:
    """Append the FIRST grade (accepts model_draft or analyst_confirmed; only analyst_confirmed enters the
    cross-case source-trust record). reliability A–F + credibility 1–6 are two INDEPENDENT required inputs.
    `diagnosticity` is a NARRATIVE annotation only — it does NOT feed score_matrix. `rationale` records WHY
    this grade was chosen. Errors if a grade already exists (use update_grade). Marks dependent ACH cells stale.

    NEVER set `judgment_source='analyst_confirmed'` unless a human literally confirmed THIS grade in THIS
    call — that value asserts human review and makes the evidence scoreable. Default to `model_draft`; an
    ingested/untrusted item in particular must pass through `model_draft` first.

    GATE: ach-engine REFUSES to score any ACH cell whose evidence's latest grade is not `analyst_confirmed`.
    A `model_draft` grade will therefore block scoring — re-grade via update_grade(..., analyst_confirmed)
    once a human has confirmed it."""
    try:
        return store.grade_evidence(
            evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale
        )
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def update_grade(
    evidence_id: Annotated[str, Field(max_length=_MAX_ID)],
    reliability: Reliability,
    credibility: Credibility,
    diagnosticity: Annotated[str, Field(max_length=_MAX_TEXT)],
    reason: Annotated[str, Field(max_length=_MAX_TEXT)],
    judgment_source: JudgmentSource,
    rationale: Annotated[str, Field(max_length=_MAX_TEXT)] = "",
) -> EvidenceRecord:
    """Append a SUPERSEDING grade (never edits). Errors if no prior grade exists. Re-marks dependent ACH
    cells stale. `reason` (required) records WHY this grade SUPERSEDES the prior one; `rationale` records WHY
    this new grade was chosen — they are distinct.

    NEVER set `judgment_source='analyst_confirmed'` unless a human literally confirmed THIS grade in THIS
    call — that value asserts human review and makes the evidence scoreable. Default to `model_draft`.

    GATE: this is the remedy path for the ach-engine collect-then-grade gate — call it with
    judgment_source='analyst_confirmed' once a human has confirmed a previously `model_draft` grade, so the
    evidence's cells become scoreable."""
    try:
        return store.update_grade(
            evidence_id, reliability, credibility, diagnosticity, reason, judgment_source, rationale
        )
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_evidence(
    evidence_id: Annotated[str, Field(max_length=_MAX_ID)], redact_pii: bool = True
) -> EvidenceRecord:  # SF1: read-path IDs carry the same _MAX_ID cap as the write tools
    """Read one evidence item + its grade history. `pii` items return item='REDACTED' unless redact_pii=False,
    which is host-gated (requires EVIDENCE_ALLOW_UNREDACT — source identity is life-safety)."""
    _require_unredact_permitted(redact_pii)
    try:
        return store.get_evidence(evidence_id, redact_pii)
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def list_evidence(
    case_id: Annotated[str, Field(max_length=_MAX_ID)],  # SF1: same _MAX_ID cap as the write tools
    redact_pii: bool = True,
    limit: int = 100,
    cursor: str | None = None,
) -> EvidenceList:
    """Read-back for a case with pagination. Unredacted reads (redact_pii=False) are host-gated
    (EVIDENCE_ALLOW_UNREDACT)."""
    _require_unredact_permitted(redact_pii)
    try:
        return store.list_evidence(case_id, redact_pii, limit, cursor)
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def get_source_history(
    source_id: Annotated[str, Field(max_length=_MAX_ID)], redact_pii: bool = True
) -> SourceHistory:  # SF1: read-path IDs carry the same _MAX_ID cap as the write tools
    """CROSS-CASE view (folded source-trust-registry): the ordered sequence of this source's
    `analyst_confirmed` grades + the direction of the most recent change. A transparent RECORD, not a
    synthesized trust score; model_draft grades are excluded (and counted). Unredacted reads
    (redact_pii=False) are host-gated (EVIDENCE_ALLOW_UNREDACT)."""
    _require_unredact_permitted(redact_pii)
    try:
        return store.get_source_history(source_id, redact_pii)
    except EvidenceError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def verify_chain() -> ChainStatus:
    """Verify the append-only evidence + grade hash chains AND anchor each to the external manifest (tamper
    evidence, incl. tail-truncation / whole-chain reset). Verification is ALWAYS GLOBAL — the whole ledger,
    not a single case. See verify_signals_chain for the SEPARATE cross-server signal store.

    NOTE: this is an UNKEYED SHA-256 hash chain — tamper-evidence rests entirely on OS file-permission
    isolation of the DB + manifest (kept 0600) from any other local writer, INCLUDING a co-resident agent
    with a filesystem/bash tool; it is NOT protection against an actor who can rewrite the files and
    recompute the chain forward."""
    return store.verify_chain()


@mcp.tool
def verify_signals_chain() -> ChainStatus:
    """Verify the SHARED cross-server signal store (stale_events + grade_signals) that ach-engine's
    collect-then-grade gate depends on. This is a DIFFERENT store from verify_chain — run BOTH to fully
    check integrity.

    NOTE: this is the same UNKEYED SHA-256 mechanism as verify_chain — tamper-evidence rests entirely on OS
    file-permission isolation of the staleness DB + manifest (kept 0600) from any other local writer, INCLUDING
    a co-resident agent with a filesystem/bash tool; it is NOT protection against an actor who rewrites the
    files and recomputes the chain forward."""
    return staleness.verify_chain()


def main() -> None:
    # verify_stable tolerates the benign cross-process commit -> manifest-append window on the SHARED
    # staleness store (retry) while still failing closed on genuine tampering.
    for label, fn in (
        ("evidence-ledger", store.verify_chain),
        ("evidence-signals", staleness.verify_chain),
    ):
        st = verify_stable(fn)
        if not st.ok:
            print(
                f"[evidence-ledger] REFUSING TO SERVE — {label} chain failed: {st.mismatch}",
                file=sys.stderr,
            )
            raise SystemExit(1)
    print("[evidence-ledger] chains OK; serving on stdio", file=sys.stderr)
    # show_banner=False: the default FastMCP banner performs a "newer version" HTTP check — suppressed to
    # honour this repo's no-egress discipline (only the osint server is permitted network egress).
    mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
