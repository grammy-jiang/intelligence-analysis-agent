"""FastMCP server for osint-toolkit (design v3, Layer 4) — the SOLE external-egress surface.

Security path (guard → pre-egress gate → audit) runs on every call. Live network is gated behind OSINT_LIVE
(off by default): with it off, the security path still runs and the call then fails closed with a clear
ToolError, so the guard/gate/audit are exercised deterministically without real services. Connectors against
real services are a follow-on. Every result is a CANDIDATE; writes to evidence-ledger are ungraded proposals.
"""

from __future__ import annotations

import http.client
import os
import ssl
import sys
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..common import ChainStatus
from .artifacts import ArtifactError, ArtifactStore
from .audit import EgressAudit
from .egress import EgressError, validate_url
from .models import (
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
# S4: bound the two highest-risk egress free-text inputs at the JSON schema (every other free-text field is
# already capped) so an oversized payload is rejected before _screen / urlsplit scan it in full.
_MAX_QUERY = 1024
_MAX_URL = 2048
# Mirrors evidence-ledger's own _MAX_ID; the ledger (the single writer) ultimately enforces it, but we bound
# the proposal fields here too so oversized input is rejected at this tool's JSON schema (review M2/S17).
_MAX_ID = 512
# control #7a: outgoing text is screened for these case/source identifiers before egress (exfil channel).
CASE_IDENTIFIERS = {s for s in os.environ.get("OSINT_CASE_IDENTIFIERS", "").split(",") if s.strip()}

_AUDIT_DB = os.environ.get("OSINT_AUDIT_DB", os.path.join(_DATA, "audit.db"))
_ARTIFACTS_DIR = os.environ.get("OSINT_ARTIFACTS_DIR", os.path.join(_DATA, "artifacts"))
os.makedirs(os.path.dirname(os.path.abspath(_AUDIT_DB)), exist_ok=True)

# M1: osint-toolkit is NOT a ledger writer. evidence-ledger takes an exclusive, lifetime single-writer lock on
# evidence.db (a tested integrity invariant), and .mcp.json runs evidence-ledger and osint-toolkit as SEPARATE
# processes on the same default data/evidence.db — so opening a second in-process EvidenceStore here fails
# closed at import and breaks the MCP initialize handshake. Instead, propose_to_ledger routes the ingested
# proposal to the single evidence-ledger writer over the MCP boundary (EVIDENCE_LEDGER_URL). This keeps
# evidence.db single-writer and its append-only hash chain un-forkable.
EVIDENCE_LEDGER_URL = os.environ.get("EVIDENCE_LEDGER_URL")

audit = EgressAudit(_AUDIT_DB)
artifacts = ArtifactStore(_ARTIFACTS_DIR)
# URLs a prior in-session fetch has already passed the guard for (fetch provenance set). NOTE: the stub
# search/reverse_image_search connectors do NOT populate this yet — when live connectors ship they MUST add
# their returned candidate URLs here, or the "url must come from a prior search result" gate in fetch() stays
# satisfiable only via confirmed=True (review S5).
_session_urls: set[str] = set()

# M3: mask_error_details=True — this is the highest-risk server (sole external egress, parses untrusted fetched
# bytes). Any non-ToolError (sqlite/disk/internal bug) must not leak raw str(e) — DB paths, SQL — to the client.
mcp = FastMCP("osint-toolkit", mask_error_details=True)


def _ledger_client():
    """A fastmcp Client connected to the SINGLE evidence-ledger writer, or None if unconfigured. Tests inject
    an in-memory client by monkeypatching this function."""
    if not EVIDENCE_LEDGER_URL:
        return None
    from fastmcp import Client

    return Client(EVIDENCE_LEDGER_URL)


def _norm_screen(s: str) -> str:
    """Casefold and strip common separators so `CASE-1234` / `CASE 1234` / `case.1234` all collapse to one form.
    S7: this is coarse defense-in-depth (it still misses base64/encoding), NOT the primary control."""
    return "".join(ch for ch in s.casefold() if ch.isalnum())


def _screen(text: str) -> None:
    """Pre-egress exfiltration screen (control #7a): refuse if outgoing text carries a case/source identifier.
    S7: compares on a separator-stripped casefold form so trivial spacing/case/punctuation edits don't bypass."""
    normalized = _norm_screen(text)
    for ident in CASE_IDENTIFIERS:
        needle = _norm_screen(ident)
        if needle and needle in normalized:
            raise ToolError("pre-egress gate: outgoing text carries a case/source identifier; blocked")


def _screen_or_audit(tool: str, text: str, fields: dict) -> None:
    """MF1: run the pre-egress exfil screen, but if it BLOCKS, record an audit row BEFORE re-raising. A blocked
    exfiltration attempt is the single event most worth logging, yet `_screen` raising before the first
    `audit.record` left it with no trace — breaking control #10 (every egress attempt is audited) on exactly the
    path that matters most. The screen text (query/url) is never logged — only the allowlisted fields."""
    try:
        _screen(text)
    except ToolError:
        audit.record(tool, fields, "-", "blocked (screen)")
        raise


def _require_confirmed_or_audit(tool: str, confirmed: bool, fields: dict, message: str) -> None:
    """control #10 + #7c: a consent/provenance REFUSAL is itself an egress-relevant event. Record an audit
    row BEFORE raising so a blocked attempt still leaves a trace (mirrors _screen_or_audit) — these three
    gates previously raised before any audit.record, so a refused upload/disclosure/fetch left NO trace,
    breaking control #10 (every egress attempt audited). `confirmed` is the already-evaluated gate predicate
    (True = allowed to proceed); only the allowlisted `fields` are logged, never the URL/coords."""
    if not confirmed:
        audit.record(tool, fields, "-", "blocked (confirmation required)")
        raise ToolError(message)


@mcp.tool
def search(
    query: Annotated[str, Field(max_length=_MAX_QUERY)],
    connector: Connector,
    max_results: Annotated[int, Field(gt=0, le=100)] = 20,
) -> SearchResult:
    """ONE search tool with an allowlisted `connector`. Returns CANDIDATE results (source_channel='ingested',
    inert data). The pre-egress gate screens `query` before egress. NOTE: no live connector is configured in
    this deployment — the call runs the guard/gate/audit then fails closed with a ToolError (review S19)."""
    _screen_or_audit("search", query, {"connector": connector, "max_results": max_results})
    audit.record("search", {"connector": connector, "max_results": max_results}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1 + configure keys). Guard/gate/audit ran.")
    raise ToolError("no live connector configured for this deployment")  # follow-on: real service


@mcp.tool
def fetch(
    url: Annotated[str, Field(max_length=_MAX_URL)],
    confirmed: Annotated[
        bool,
        Field(
            description="Analyst override allowing a URL that did NOT come from a prior in-session search "
            "result. ASSERTED, not verified — the host MUST bind this to real human approval (control #7c)."
        ),
    ] = False,
) -> FetchedArtifact:
    """Fetch a URL through the egress guard. `url` must EXACTLY MATCH a URL from a prior in-session search
    result, else `confirmed=True` is required (control #7a). SSRF-guarded + audited before anything leaves.

    S3: no live connector populates the provenance set in this deployment (the stub `search` always raises),
    so today `confirmed=True` is required for every first fetch — it is not populated by any prior search."""
    # control #7a/#10: a URL without prior-search provenance (and no analyst override) is refused — and the
    # refusal is AUDITED before raising, so a blocked freeform-fetch attempt leaves a trace like every other
    # egress attempt. The predicate passes when the URL has provenance OR the analyst confirmed the override.
    _require_confirmed_or_audit(
        "fetch", url in _session_urls or confirmed, {"host": "?"},
        "url did not originate from a prior in-session search result; pass confirmed=True",
    )
    _screen_or_audit("fetch", url, {"host": "?"})  # MF1: a blocked exfil URL still leaves an audit row
    try:
        host, ip = validate_url(url)  # fetch = SSRF blocklist (no per-connector allowlist)
    except EgressError as e:
        # MF1: the EgressError text can carry the resolved internal IP (a network-recon oracle). Keep both the
        # audit `outcome` column AND the client-visible ToolError host/IP-free; host/IP live in the audit DB only.
        audit.record("fetch", {"host": "?"}, "-", "blocked (pre-fetch guard)")
        print(f"[osint-toolkit] pre-fetch guard block: {e!r}", file=sys.stderr)
        raise ToolError("egress guard blocked the URL (host/IP recorded in the audit log only)") from e
    if not OSINT_LIVE:
        audit.record("fetch", {"host": host}, ip, "attempt (live off)")
        # S8: do not echo the resolved IP back to the client (a resolution oracle reachable with live off via
        # confirmed=True). The pinned IP is recorded in the audit log only.
        raise ToolError("live fetch disabled (set OSINT_LIVE=1). Guard/gate/audit ran; IP pinned in the audit log.")
    from .egress import fetch_pinned

    # MF2: audit the live egress ATTEMPT before the socket opens — a real fetch that dies at the socket/TLS
    # layer must still leave a log row (control #10: every outbound call audited).
    audit.record("fetch", {"host": host}, ip, "attempt (live)")
    try:
        final_url, body, ctype = fetch_pinned(url)  # re-validates every redirect hop; pinned TLS
    except EgressError as e:
        audit.record("fetch", {"host": host}, ip, "blocked (fetch guard)")  # fixed reason code
        print(f"[osint-toolkit] fetch guard block: {e!r}", file=sys.stderr)
        raise ToolError("egress guard blocked during fetch (host/IP recorded in the audit log only)") from e
    except (OSError, ssl.SSLError, http.client.HTTPException) as e:
        # MF2: fetch_pinned raises plain socket/TLS/HTTP errors (TimeoutError, ConnectionRefusedError,
        # ssl.SSLError, http.client.HTTPException) that are NOT EgressError. Without this they escape uncaught
        # (masked to an opaque error) and the attempt would be unaudited. Record the failure, surface a
        # detail-free ToolError, never leak the raw exception.
        audit.record("fetch", {"host": host}, ip, "error (network/TLS)")
        print(f"[osint-toolkit] fetch network/TLS error: {e!r}", file=sys.stderr)
        raise ToolError("fetch failed at the network/TLS layer (details in the server log only)") from e
    tok = artifacts.put(body)
    audit.record("fetch", {"host": host}, ip, "ok")
    _session_urls.add(final_url)
    return FetchedArtifact(
        artifact_ref=tok, host=host, content_type=ctype, sha256=artifacts.compute_hash(tok), size=len(body)
    )


@mcp.tool
def compute_hash(artifact_ref: Annotated[str, Field(max_length=_MAX_ID)]) -> HashResult:
    """SHA-256 of a stored artifact (LOCAL, no egress)."""
    try:
        return HashResult(artifact_ref=artifact_ref, sha256=artifacts.compute_hash(artifact_ref))
    except ArtifactError as e:
        raise ToolError(str(e)) from e


@mcp.tool
def extract_exif(artifact_ref: Annotated[str, Field(max_length=_MAX_ID)]) -> ExifData:
    """Parse EXIF from a stored artifact (LOCAL, no egress). Verifies real magic bytes (never a remote
    Content-Type); CANDIDATE only. (Full EXIF field parsing via a memory-safe library is a follow-on; the
    hardening — magic-byte check, size cap, no shell-out — is enforced here.)"""
    try:
        detected = artifacts.detect_type(artifact_ref)
        data = artifacts.read(artifact_ref)
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    if detected is None or not detected.startswith("image/"):
        return ExifData(
            artifact_ref=artifact_ref, detected_type=detected, fields={},
            note=f"artifact is not a recognized image ({detected}); EXIF not extracted",
        )
    from .exif import parse_exif

    fields = parse_exif(data)  # memory-safe, resource-limited; empty on any parser error
    note = "candidate; verify the location/fields before use — a planted artifact can carry false EXIF"
    return ExifData(artifact_ref=artifact_ref, detected_type=detected, fields=fields, note=note)


@mcp.tool
def reverse_image_search(
    artifact_ref: Annotated[str, Field(max_length=_MAX_ID)],
    connector: Connector,
    confirmed: Annotated[
        bool,
        Field(
            description="Analyst consent to UPLOAD this image (a subject's likeness) to a third party. "
            "ASSERTED, not verified — the host MUST bind this to real human approval (control #7c)."
        ),
    ] = False,
) -> CandidateMatches:
    """CANDIDATE image matches. Uploads the image to an external connector — may transmit a subject's likeness
    — so it REQUIRES `confirmed=True` (control #7c). NOTE: no live connector is configured in this deployment
    — the call runs the guard/audit then fails closed with a ToolError (review S19)."""
    # control #7c/#10: refusing the upload is an egress-relevant event — audit it before raising.
    _require_confirmed_or_audit(
        "reverse_image_search", confirmed, {"connector": connector},
        "reverse_image_search uploads an image to a third party; pass confirmed=True",
    )
    try:
        artifacts.read(artifact_ref)  # validates the token
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    audit.record("reverse_image_search", {"connector": connector}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1). Guard/gate/audit ran.")
    raise ToolError("no live connector configured for this deployment")


@mcp.tool
def get_map_tile(
    lat: Annotated[float, Field(ge=-90, le=90)],
    lon: Annotated[float, Field(ge=-180, le=180)],
    zoom: Annotated[int, Field(ge=0, le=22)],
    connector: Connector,
    confirmed: Annotated[
        bool,
        Field(
            description="Analyst consent to disclose these coordinates (a subject's location of interest) to a "
            "third-party tile provider. ASSERTED, not verified — the host MUST bind this to real human approval."
        ),
    ] = False,
) -> MapTile:
    """CANDIDATE map tile for geolocation work. Not a verified location. Discloses lat/lon to a third-party
    tile provider, so it REQUIRES `confirmed=True` (control #7c — same third-party-disclosure gate as `fetch`
    and `reverse_image_search`). S5: lat/lon/zoom bounds are enforced at the JSON schema so clients self-validate.
    NOTE: no live connector is configured in this deployment — the call fails closed with a ToolError (S19)."""
    # control #7c/#10: refusing the coordinate disclosure is an egress-relevant event — audit it before raising.
    _require_confirmed_or_audit(
        "get_map_tile", confirmed, {"connector": connector, "zoom": zoom},
        "get_map_tile discloses coordinates to a third-party tile provider; pass confirmed=True",
    )
    audit.record("get_map_tile", {"connector": connector, "zoom": zoom}, "-", "attempt")
    if not OSINT_LIVE:
        raise ToolError("live connector disabled (set OSINT_LIVE=1). Guard/audit ran.")
    raise ToolError("no live connector configured for this deployment")


@mcp.tool
async def propose_to_ledger(
    case_id: Annotated[str, Field(max_length=_MAX_ID)],
    artifact_ref: Annotated[str, Field(max_length=_MAX_ID)],
    source_id: Annotated[str, Field(max_length=_MAX_ID)],
    note: Annotated[str, Field(max_length=NOTE_CAP)],
    pii: Annotated[
        bool,
        Field(
            description="True if `note`/artifact identifies a human source. Passed through to evidence-ledger, "
            "which redacts PII items on read (source identity is life-safety). ASSERTED by the caller."
        ),
    ] = False,
) -> ProposalRef:
    """Write a fetched artifact's provenance into evidence-ledger as an UNTRUSTED, UNGRADED proposal
    (source_channel='ingested'). The analyst must confirm + grade it before ach-engine will score it (finding B).
    `note` is untrusted content: length-capped and never scored — a system annotation, not a judgment.

    osint-toolkit is NOT itself a ledger writer (evidence.db is single-writer, owned by evidence-ledger); this
    routes the proposal to evidence-ledger over the MCP boundary. Requires EVIDENCE_LEDGER_URL to be configured
    (else it fails closed rather than forking the append-only ledger)."""
    try:
        sha = artifacts.compute_hash(artifact_ref)  # validates the token (LOCAL, no egress)
    except ArtifactError as e:
        raise ToolError(str(e)) from e
    client = _ledger_client()
    if client is None:
        raise ToolError(
            "propose_to_ledger requires a configured evidence-ledger connection (set EVIDENCE_LEDGER_URL); "
            "osint-toolkit is not itself a ledger writer (evidence.db is single-writer)."
        )
    item = f"[OSINT ingested] artifact={artifact_ref} sha256={sha} | note(unverified): {note}"
    try:
        async with client as c:
            res = await c.call_tool(
                "add_evidence",
                {
                    "case_id": case_id, "item": item, "source_id": source_id,
                    "evidence_type": "report", "pii": pii, "source_channel": "ingested",
                },
            )
    except ToolError:
        raise  # a business-rule rejection from evidence-ledger (e.g. size cap) — surface it verbatim
    except Exception as e:  # noqa: BLE001 - surfaced as a clear tool error, never a raw internal leak
        # S1: do not re-embed raw str(e) (transport/URL/host detail) into a client-visible ToolError — that
        # bypasses the mask_error_details invariant. Log the detail to stderr; return a fixed reason code.
        print(f"[osint-toolkit] evidence-ledger proposal transport error: {e!r}", file=sys.stderr)
        raise ToolError("evidence-ledger proposal failed (transport error; details in the server log only)") from e
    # S2/MF2: the ledger response may lack structured content, or `res.data` may be a plain dict (when this
    # client holds no pydantic model for the callee's output schema) or a shape-drifted object. A bare
    # `res.data.evidence_id` deref would raise AttributeError, masked to an opaque error that makes every
    # ledger write look broken. Normalize dict-or-model and fail with a clear ToolError if the id is absent.
    data = res.data
    if data is None:
        raise ToolError("evidence-ledger returned an unexpected response shape (no structured content)")
    evidence_id = data.get("evidence_id") if isinstance(data, dict) else getattr(data, "evidence_id", None)
    if not evidence_id:
        raise ToolError("evidence-ledger returned an unexpected response shape (missing evidence_id)")
    return ProposalRef(evidence_id=evidence_id, case_id=case_id)


@mcp.tool
def verify_chain() -> ChainStatus:
    """Verify the egress audit log's hash chain (control #10)."""
    return audit.verify_chain()


def _ledger_url_is_local(url: str) -> bool:
    """S8: True if EVIDENCE_LEDGER_URL points at loopback / this box. propose_to_ledger routes case/source ids +
    note to this URL WITHOUT the _screen / validate_url / audit egress controls, so a misconfigured or hostile
    env var would silently exfiltrate off-box. A non-literal DNS host cannot be classified safely here → treat
    it as remote (fail closed) unless the operator opts in via OSINT_LEDGER_ALLOW_REMOTE=1."""
    import ipaddress
    from urllib.parse import urlsplit

    host = urlsplit(url).hostname or ""
    if host in ("localhost", "localhost.localdomain", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False  # a DNS name — cannot verify it stays on-box


def main() -> None:
    st = audit.verify_chain()
    if not st.ok:
        print(f"[osint-toolkit] REFUSING TO SERVE — egress audit chain failed: {st.mismatch}", file=sys.stderr)
        raise SystemExit(1)
    # S8: propose_to_ledger's route to EVIDENCE_LEDGER_URL is UNSCREENED + UNAUDITED. Fail closed if it is not
    # a loopback target, unless the operator explicitly opts in to a remote ledger.
    if EVIDENCE_LEDGER_URL and not _ledger_url_is_local(EVIDENCE_LEDGER_URL):
        if os.environ.get("OSINT_LEDGER_ALLOW_REMOTE") != "1":
            print(
                "[osint-toolkit] REFUSING TO SERVE — EVIDENCE_LEDGER_URL is not a loopback target; "
                "propose_to_ledger would route case/source ids off-box unscreened and unaudited. "
                "Set OSINT_LEDGER_ALLOW_REMOTE=1 to intentionally allow a remote ledger.",
                file=sys.stderr,
            )
            raise SystemExit(1)
    # S11: control #7a (the pre-egress exfil screen) is inert when no identifiers are configured. Fail closed
    # rather than serve LIVE egress while the operator believes the screen is active.
    if OSINT_LIVE and not CASE_IDENTIFIERS:
        print(
            "[osint-toolkit] REFUSING TO SERVE — OSINT_LIVE=1 but OSINT_CASE_IDENTIFIERS is empty; the "
            "pre-egress exfiltration screen (control #7a) would block nothing.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not CASE_IDENTIFIERS:
        print(
            "[osint-toolkit] WARNING: OSINT_CASE_IDENTIFIERS is empty — the pre-egress exfiltration screen "
            "(control #7a) will not block any identifier.",
            file=sys.stderr,
        )
    live = "LIVE egress ON" if OSINT_LIVE else "live egress OFF (guard/gate/audit only)"
    print(f"[osint-toolkit] audit chain OK ({st.rows_verified} rows); {live}; serving on stdio", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
