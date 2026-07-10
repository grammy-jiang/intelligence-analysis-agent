# Phase 4 — OSINT collection + deception reviewer: design (security-gated)

> The external-collection layer. Realizes blueprint Layer 4 + design-spec §57–70. **Two gates precede ANY
> live connector:** (1) deployment context — RESOLVED below; (2) a mandatory, blocking security-review of
> this design. No connector code is written until the security panel reaches must-fix=0.

## Review response (v2) — the mandatory security gate returned must-fix; all folded in
The blocking panel (mcp-security + application-security) blocked v1. Resolutions:
- **Finding B — collect-then-grade hole in *shipped* ach-engine — FIXED IN CODE.** `score_matrix` now refuses
  any cell whose evidence lacks an effective `analyst_confirmed` grade, via a shared `grade_signals`
  cross-server signal (same narrow, write-scoped pattern as staleness) + a regression test. An ingested/ungraded
  artifact can no longer reach scored output.
- Design-level (folded into the tools + controls below): argument-level exfiltration (A), sole-egress
  *enforcement mechanism* (C), egress audit log (D), `extract_exif` RCE hardening (E), `artifact_ref` opaque
  token (F), SSRF completeness — per-hop full check + IANA blocklist + canonicalization + connection pinning +
  one shared guard (G), untrusted `note` (H). Both reviewers judged the architecture sound; these are spec
  additions, not a redesign.

## Gate 1 — deployment context: RESOLVED = unclassified / OSINT-only
Public open-source data only; **egress-allowed** to allowlisted OSINT sources; **no classified/compartmented
handling** and no classified data at rest. The no-egress / confidential class stays deferred (consistent with
the tech-stack decision). This resolves blueprint open decision #1 and is what makes live collection
permissible at all. Everything below assumes this context; a classified deployment would require a separate
design.

## Components (blueprint Layer 4)
- **`osint-toolkit` MCP** — collection primitives; the **sole** external-egress surface.
- **`osint-investigation` skill** — the *method* (when/why/how to search + verify); no toolkit mechanics in prose.
- **`deception-detection-reviewer` subagent** — read-only D&D critic over the evidence chain (Masterman/Jervis);
  buildable now that evidence-ledger exists. Its distillation is a factory task (map Masterman + Jervis D&D
  principles), out of scope for this doc except as a consumer of raw case state.

## `osint-toolkit` MCP — primitives only (FastMCP, same stack as Phase 3)
The toolkit **fetches/stores raw and proposes**; it never grades, never asserts a fact, never writes a trusted
record. Every result is a **candidate** for analyst confirmation (decision #10).

```python
mcp = FastMCP("osint-toolkit")

@mcp.tool
def search(query: str, connector: Connector, max_results: int = 20) -> SearchResult:
    """ONE search tool with a `connector` param (NOT one tool per source). `connector` is an allowlisted enum.
    Returns CANDIDATE results tagged source_channel='ingested' — inert data, never instruction."""

@mcp.tool
def fetch(url: str) -> FetchedArtifact:
    """Fetch a URL through the shared egress guard (control #3). `url` must EXACTLY MATCH (byte-for-byte,
    against a server-held per-session set) a URL returned by a prior in-session `search`/`reverse_image_search`
    call; a near-miss (same host, different path/query/trailing slash) counts as freeform and requires explicit
    analyst confirmation (control #7a). Stores raw bytes + a content hash; returns metadata + a server-issued
    opaque `artifact_ref`. No interpretation; the pre-egress gate (control #7) screens the URL before it leaves.
    Redirect hops are re-checked against the SSRF rules (scheme+IP), not against the provenance set."""

@mcp.tool
def extract_exif(artifact_ref: str) -> ExifData:
    """Parse EXIF from a fetched artifact (LOCAL, no egress). DMS→decimal conversion + any resizing happen
    INSIDE this contract; every geo/image field carries explicit semantic-role / modality /
    coordinate-reference-frame; a runtime validator lets the caller halt on misaligned data. CANDIDATE only."""

@mcp.tool
def compute_hash(artifact_ref: str) -> HashResult:
    """Content hash of a stored artifact (LOCAL, no egress) — for archival integrity + dedup."""

@mcp.tool
def reverse_image_search(artifact_ref: str, connector: Connector) -> CandidateMatches:
    """CANDIDATE image matches (egress via the guard). Proposals for human confirmation, not identifications."""

@mcp.tool
def get_map_tile(lat: float, lon: float, zoom: int, connector: Connector) -> MapTile:
    """CANDIDATE map tile for geolocation work (egress via the guard). Not a verified location."""

@mcp.tool
def propose_to_ledger(case_id: str, artifact_ref: str, note: str) -> ProposalRef:
    """Write the fetched artifact's PROVENANCE into evidence-ledger as an UNTRUSTED PROPOSAL:
    source_channel='ingested', NOT graded — the analyst must confirm + grade it via source-evaluation before
    ach-engine will score it (finding B closed). A proposal, never a trusted internal RPC. `artifact_ref` is a
    server-issued opaque token (control #12). **`note` is itself untrusted content** (it may paraphrase injected
    instructions from the fetched page): it is never scored, is length-capped, and is surfaced to the analyst as
    an unverified system-generated annotation (control #7/H)."""
```
Read-back (`get_artifact`, `list_artifacts`) + `verify_chain` per the Phase-3 conventions. `Connector` is a
`Literal[...]` allowlist. Geolocation *verification* is a workflow (the skill), never a tool output.

## SECURITY CONTROLS (the load-bearing section — all ship together, design-spec §65)
1. **Sole egress — with a named enforcement mechanism (C).** osint-toolkit is the ONLY server with network
   access. The three data servers run in an **OS-level network sandbox with no route to the network** (a
   network namespace / `--network=none` / a seccomp profile denying `socket(AF_INET/AF_INET6)`), AND a **CI
   check fails the build** if any network-capable symbol (`socket`, `requests`, `httpx`, `urllib`, …) appears
   anywhere in those three servers' import graph, including transitive deps. Both layers: the sandbox catches
   what static analysis misses, the check catches sandbox misconfig. **Inter-server / orchestrator transport is
   stdio or a local unix-domain socket — never a TCP socket** (so "no AF_INET" is unambiguous).
2. **Outbound allowlist, deny-by-default.** Each `connector` maps to a fixed set of allowed hostnames; any
   destination not on the list is refused. No arbitrary user-supplied hostnames reach the network except
   through `fetch`, which is itself guarded (below).
3. **SSRF defenses — one shared guard, complete (G).** ALL outbound calls route through a single guarded-client
   wrapper (the only thing permitted to open a socket); ad-hoc HTTP clients are banned by lint/review.
   - **Scheme allowlist HTTPS-only** (reject `file://`, `gopher://`, `data://`, …), re-checked on every hop.
   - **Blocklist from a maintained source** (IANA special-purpose registries / a vetted SSRF-guard lib), not
     hand-rolled — covers 127/8, 10/8, 172.16/12, 192.168/16, 169.254/16 (incl. 169.254.169.254), **0.0.0.0/8,
     100.64/10, 224.0.0.0/4, 240.0.0.0/4**, ::1, fc00::/7, fe80::/10, IPv4-mapped-IPv6.
   - **Canonicalize before checking**: strict IP parse; **reject non-canonical literal forms** (decimal/octal/
     hex, `::ffff:`-mapped, userinfo/host-confusable URLs) rather than normalizing them.
   - **Connection pinning (the real anti-rebinding backstop)**: resolve DNS **once**, open a raw socket to that
     **literal validated IP**, then layer TLS/HTTP over the already-open socket (SNI/Host = original hostname)
     — never let the HTTP client resolve-and-connect by hostname a second time.
   - **The guard drives redirect-following**; each hop re-applies the FULL check set (scheme + IP-block +
     connector-hostname); cap hops.
   - Wire-size + **decompressed-size** caps (defeat decompression bombs), content-type + timeout caps.
4. **Every return is inert data, never instruction.** Fetched text, page content, and image metadata are
   stored/returned as data; the toolkit performs no `sampling`/LLM step on them. The `source_channel='ingested'`
   tag (already in evidence-ledger) forces consuming skills to apply an untrusted-content fence.
5. **Ledger writes are untrusted proposals (B fixed in code).** `propose_to_ledger` writes
   `source_channel='ingested'`, leaves the item **ungraded**, and its `note` is treated as untrusted content
   (H — see the tool). ach-engine now **refuses to score any evidence lacking an effective `analyst_confirmed`
   grade** (finding B, via the `grade_signals` cross-server signal) — so an OSINT proposal can never become
   trusted, scored case state without a human grade *and* a confirmed rating.
6. **Candidate-only outputs.** Geolocation, reverse-image matches, and map tiles are proposals for human
   confirmation, never asserted facts (decision #10). The schemas name them `Candidate*`.
7. **Pre-egress gate on ALL egress paths (A).** A content check runs **before anything leaves the process** on
   *every* egress path (`search`, `fetch`, `reverse_image_search`, `get_map_tile`) — not just `fetch`:
   (a) it screens the outgoing `query`/`url` for embedded case/source identifiers (the exfiltration channel) and
   size-caps it; (b) a **deterministic** permission/hook blocks collection targeting a **named private
   individual**, fed by analyst-set target metadata (not free-text inference — an ML/NER signal is secondary,
   non-authoritative), **failing closed on ambiguity**; (c) `reverse_image_search` (which may upload a subject's
   likeness) requires its own explicit analyst confirmation. Honest label: where the flag is analyst-asserted it
   is *asserted, not verified* (like `judgment_source`). The substantive privacy/legal line is a policy owner's
   call, not this design's.
8. **Resource quotas + circuit-breakers** on metered/connector calls (per-connector rate limit, per-session
   budget, breaker on repeated errors) — cost + abuse containment.
9. **No secrets in tool defs / case state.** Connector API keys come from the server's trusted local
   environment (OS keychain / vault-backed), never a tool argument or a stored record; any URL/query-string
   that could carry an embedded key is **redacted before logging/returning/surfacing**; keys are per-connector,
   narrowly scoped, and independently revocable, with a rotation trigger on suspected compromise.
10. **Egress audit log (D).** Every egress-capable call emits a structured, **append-only hash-chained** record
   containing a per-tool **allowlist** of loggable fields (fail-closed — a field not on the list is never
   logged, so a future secret-bearing field can't leak by omission), the resolved IP after the SSRF check, the
   connector, size/timing, and outcome, with its own `verify_chain` — so "sole egress, allowlisted" is
   verifiable after the fact and a bypass leaves a trace. A breaker trip (control #8) is logged here too,
   fail-closed.
11. **`extract_exif` parser hardening (E).** It parses adversary-supplied bytes on the sole egress host: use a
   **memory-safe / pure-library** reader (not a shell-out to a CLI); **disable XML external entities** for any
   XMP/XML; verify the artifact's real **magic bytes** (never trust the remote `Content-Type`); run the parse
   **resource-limited + sandboxed** (bounded memory/time, no network) so a parser exploit is contained.
12. **`artifact_ref` is a server-issued opaque token (F).** Resolved only through an internal ID→path index;
   any value not in the index is rejected; stored filenames are never derived from remote-supplied names/headers
   (defeats path traversal toward the connector-key store).
13. **argv-array invocation, pinned hostnames (F/injection).** Any connector/extractor wrapping an external
   binary passes arguments as an **array, never a shell string** (closes command injection). Each connector pins
   fully-qualified hostnames (no wildcard domains); its client library is CVE-scanned in CI.

## Grounding vs plumbing (the rule)
- **Grounded:** the collect-then-grade separation (decision #8, FM/Masterman — the subject controls the
  footprint, so a self-grading collector launders injected directives); candidate-only verification (decision
  #10); egress-isolation of the trifecta (decision #9); D&D interrogation (Masterman C002/C044, Jervis).
- **Plumbing (engineering-inference):** FastMCP form, the SSRF/allowlist mechanics, artifact_ref/hashes,
  circuit-breaker/quota bookkeeping, the deterministic high-risk hook's implementation.

## Test plan (design-spec §72–75) — a regression test per must-fix
- osint-toolkit connectors evaluate against **REAL services**, not mocks — behind a `--live` opt-in; CI runs the
  non-egress parts deterministically.
- **SSRF matrix (G):** each blocked class (private/loopback/link-local/metadata, 0.0.0.0/8, 100.64/10,
  multicast/reserved); **IP-canonicalization bypasses** (decimal/octal/hex, `::ffff:`-mapped); a **DNS-rebinding**
  case (TTL flip between resolve and connect — the pinned-IP socket defeats it); **redirect-to-blocked-IP** and
  **redirect-to-`file://`**; a decompression bomb — all refused.
- **Collect-then-grade (B):** `score_matrix` refuses ungraded / model_draft-graded evidence — *shipped + tested*.
- **Argument exfiltration (A):** a `query`/`url` carrying a case/source identifier is screened before egress; a
  `fetch` url not originating from a prior result requires confirmation.
- **Egress audit (D):** every egress call yields a verifiable audit record; `verify_chain` passes; a simulated
  missing record fails the completeness test.
- **`extract_exif` (E):** a malformed/mislabeled image is parsed resource-limited with no shell-out; a magic-byte
  mismatch is rejected; an XXE payload is inert.
- **`artifact_ref` (F):** a `../` / absolute-path value is rejected (only index-issued tokens resolve).
- **Untrusted content (H):** a fetched page — and a `note` paraphrasing it — reaches the ledger as inert
  `ingested` data, is never scored, and never alters agent behavior.
- **Sole-egress (C):** the CI network-import check fails if a data server gains a network-capable dependency.
- Whole-agent eval at the phase gate.

## Open questions for the SECURITY REVIEW panel
1. Is process-level egress isolation (only osint-toolkit has a network namespace/sockets) the right enforcement
   for control #1, or is that over/under-scoped for a repo-local MVP?
2. Is the SSRF re-validation (post-DNS + per-redirect, pinned IP) sufficient against rebinding, or is a
   dedicated egress proxy warranted even at MVP?
3. Is the deterministic high-risk-tasking gate (named private individual) the right line, and where exactly is
   it drawn for unclassified OSINT?
4. Does `propose_to_ledger` fully honor collect-then-grade (decision #8), or can an `ingested` proposal leak
   into trusted state anywhere?
5. Any egress path on the other three servers we've missed (they must stay zero-egress)?
