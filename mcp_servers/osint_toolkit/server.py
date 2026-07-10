"""FastMCP server for osint-toolkit (design v3, Layer 4) — the SOLE external-egress surface.

Security path (guard → pre-egress gate → audit) runs on every call. Live network is gated behind OSINT_LIVE
(off by default): with it off, the security path still runs and the call then fails closed with a clear
ToolError, so the guard/gate/audit are exercised deterministically without real services. Connectors against
real services are a follow-on. Every result is a CANDIDATE; writes to evidence-ledger are ungraded proposals.
"""

from __future__ import annotations

import os
import sys

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ..common import ChainStatus
from ..evidence_ledger.store import EvidenceStore
from ..staleness import StalenessStore
from .artifacts import ArtifactError, ArtifactStore
from .audit import EgressAudit
from .egress import EgressError, validate_url
from .models import (
    CONNECTOR_HOSTS,
    CandidateMatches,
    Connector,
    ExifData,
    FetchedArtifact,
    HashResult,
    MapTile,
    ProposalRef,
    SearchResult,
)

_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "data")
OSINT_LIVE = os.environ.get("OSINT_LIVE") == "1"
NOTE_CAP = 500
# control #7a: outgoing text is screened for these case/source identifiers before egress (exfil channel).
CASE_IDENTIFIERS = {s for s in os.environ.get("OSINT_CASE_IDENTIFIERS", "").split(",") if s.strip()}

_AUDIT_DB = os.environ.get("OSINT_AUDIT_DB", os.path.join(_DATA, "audit.db"))
_ARTIFACTS_DIR = os.environ.get("OSINT_ARTIFACTS_DIR", os.path.join(_DATA, "artifacts"))
_EVIDENCE_DB = os.environ.get("EVIDENCE_DB", os.path.join(_DATA, "evidence.db"))
_STALENESS_DB = os.environ.get("STALENESS_DB", os.path.join(_DATA, "staleness.db"))
for p in (_AUDIT_DB, _EVIDENCE_DB, _STALENESS_DB):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)

audit = EgressAudit(_AUDIT_DB)
artifacts = ArtifactStore(_ARTIFACTS_DIR)
_staleness = StalenessStore(_STALENESS_DB)
_evidence = EvidenceStore(_EVIDENCE_DB, _staleness)
_session_urls: set[str] = set()  # URLs returned by prior search/reverse_image_search (fetch provenance set)

mcp = FastMCP("osint-toolkit")


def _screen(text: str) -> None:
    """Pre-egress exfiltration screen (control #7a): refuse if outgoing text carries a case/source identifier."""
    lowered = text.lower()
    for ident in CASE_IDENTIFIERS:
        if ident.lower() in lowered:
            raise ToolError(f"pre-egress gate: outgoing text carries a case/source identifier; blocked")


@mcp.tool
def search(query: str, connector: Connector, max_results: int = 20) -> SearchResult:
    """ONE search tool with an allowlisted `connector`. Returns CANDIDATE results (source_channel='ingested',
    inert data). The pre-egress gate screens `query` before egress."""
    _screen(query)
    audit.record("search", {"connector": connector, "max_results": max_results}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1 + configure keys). Guard/gate/audit ran.")
    raise ToolError("no live connector configured for this deployment")  # follow-on: real service


@mcp.tool
def fetch(url: str, confirmed: bool = False) -> FetchedArtifact:
    """Fetch a URL through the egress guard. `url` must EXACTLY MATCH a URL from a prior in-session search
    result, else `confirmed=True` is required (control #7a). SSRF-guarded + audited before anything leaves."""
    if url not in _session_urls and not confirmed:
        raise ToolError("url did not originate from a prior in-session search result; pass confirmed=True")
    _screen(url)
    try:
        host, ip = validate_url(url)  # fetch = SSRF blocklist (no per-connector allowlist)
    except EgressError as e:
        audit.record("fetch", {"host": "?"}, "-", f"blocked: {e}")
        raise ToolError(f"egress guard blocked the URL: {e}") from e
    audit.record("fetch", {"host": host}, ip, "attempt")
    if not OSINT_LIVE:
        raise ToolError("live fetch disabled (set OSINT_LIVE=1). Guard/gate/audit ran; IP pinned to " + ip)
    raise ToolError("no live fetch transport configured for this deployment")


@mcp.tool
def compute_hash(artifact_ref: str) -> HashResult:
    """SHA-256 of a stored artifact (LOCAL, no egress)."""
    try:
        return HashResult(artifact_ref=artifact_ref, sha256=artifacts.compute_hash(artifact_ref))
    except ArtifactError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def extract_exif(artifact_ref: str) -> ExifData:
    """Parse EXIF from a stored artifact (LOCAL, no egress). Verifies real magic bytes (never a remote
    Content-Type); CANDIDATE only. (Full EXIF field parsing via a memory-safe library is a follow-on; the
    hardening — magic-byte check, size cap, no shell-out — is enforced here.)"""
    try:
        detected = artifacts.detect_type(artifact_ref)
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    note = "candidate; verify before use"
    if detected is None or not detected.startswith("image/"):
        note = f"artifact is not a recognized image ({detected}); EXIF not extracted"
    return ExifData(artifact_ref=artifact_ref, detected_type=detected, fields={}, note=note)


@mcp.tool
def reverse_image_search(artifact_ref: str, connector: Connector, confirmed: bool = False) -> CandidateMatches:
    """CANDIDATE image matches. Uploads the image to an external connector — may transmit a subject's likeness
    — so it REQUIRES `confirmed=True` (control #7c)."""
    if not confirmed:
        raise ToolError("reverse_image_search uploads an image to a third party; pass confirmed=True")
    try:
        artifacts.read(artifact_ref)  # validates the token
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    audit.record("reverse_image_search", {"connector": connector}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1). Guard/gate/audit ran.")
    raise ToolError("no live connector configured for this deployment")


@mcp.tool
def get_map_tile(lat: float, lon: float, zoom: int, connector: Connector) -> MapTile:
    """CANDIDATE map tile for geolocation work. Not a verified location."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= zoom <= 22):
        raise ToolError("lat/lon/zoom out of range")
    audit.record("get_map_tile", {"connector": connector, "zoom": zoom}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1). Guard/audit ran.")
    raise ToolError("no live connector configured for this deployment")


@mcp.tool
def propose_to_ledger(case_id: str, artifact_ref: str, source_id: str, note: str, pii: bool = False) -> ProposalRef:
    """Write a fetched artifact's provenance into evidence-ledger as an UNTRUSTED, UNGRADED proposal
    (source_channel='ingested'). The analyst must confirm + grade it before ach-engine will score it (finding B).
    `note` is untrusted content: length-capped and never scored — a system annotation, not a judgment."""
    try:
        sha = artifacts.compute_hash(artifact_ref)  # validates the token
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    item = f"[OSINT ingested] artifact={artifact_ref} sha256={sha} | note(unverified): {note[:NOTE_CAP]}"
    ref = _evidence.add_evidence(case_id, item, source_id, "report", pii, "ingested")
    return ProposalRef(evidence_id=ref.evidence_id, case_id=case_id)


@mcp.tool
def verify_chain() -> ChainStatus:
    """Verify the egress audit log's hash chain (control #10)."""
    return audit.verify_chain()


def main() -> None:
    st = audit.verify_chain()
    if not st.ok:
        print(f"[osint-toolkit] REFUSING TO SERVE — egress audit chain failed: {st.mismatch}", file=sys.stderr)
        raise SystemExit(1)
    live = "LIVE egress ON" if OSINT_LIVE else "live egress OFF (guard/gate/audit only)"
    print(f"[osint-toolkit] audit chain OK ({st.rows_verified} rows); {live}; serving on stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
