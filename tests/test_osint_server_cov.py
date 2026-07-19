"""Branch-coverage tests for osint-toolkit's server security/gate/error paths (design v3, Layer 4).

Complements test_osint_wire.py without editing it: this file drives the fail-closed and error branches that the
sole-egress surface runs after guard/gate/audit — the live-connector stubs (OSINT_LIVE on), fetch's live-off
IP-pin / per-hop guard-block / success paths, extract_exif's three type branches, the ArtifactError and
consent/provenance refusals, propose_to_ledger's success + ledger-transport error handling, _ledger_url_is_local,
the _ledger_client factory, and main()'s startup fail-closed + serve gate. Live egress is off by default.

Import pattern mirrors test_osint_wire.py: the server reads env at import time, so env is set BEFORE the import.
Module globals (OSINT_LIVE / CASE_IDENTIFIERS / EVIDENCE_LEDGER_URL / _session_urls / audit) are always adjusted
with monkeypatch so nothing leaks into the other osint test modules in a combined run.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import types

_TMP = tempfile.mkdtemp()
os.environ["OSINT_AUDIT_DB"] = os.path.join(_TMP, "audit.db")
os.environ["OSINT_ARTIFACTS_DIR"] = os.path.join(_TMP, "art")
os.environ.setdefault("EVIDENCE_DB", ":memory:")
os.environ.setdefault("STALENESS_DB", ":memory:")
os.environ["OSINT_CASE_IDENTIFIERS"] = "SECRET-CASE-42"
os.environ.pop("OSINT_LIVE", None)
os.environ.pop("EVIDENCE_LEDGER_URL", None)

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.osint_toolkit import egress as eg  # noqa: E402
from mcp_servers.osint_toolkit import server as srv  # noqa: E402
from mcp_servers.osint_toolkit.server import mcp  # noqa: E402

_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 64


async def _data(tool: str, args: dict):
    """Call a tool through an in-memory fastmcp Client and return its structured `.data`."""
    async with Client(mcp) as c:
        return (await c.call_tool(tool, args)).data


async def _err(tool: str, args: dict) -> str:
    """Call a tool expecting a ToolError; return its message (fail if the call unexpectedly succeeds)."""
    try:
        await _data(tool, args)
    except ToolError as e:
        return str(e)
    raise AssertionError(f"expected ToolError from {tool}")


def test_security_path_fail_closed_live_off(monkeypatch):
    """With live egress off the security path runs then fails closed: the screen blocks an identifier-bearing
    query, a clean query and the disclosure tools audit then refuse, the provenance + consent gates refuse, the
    SSRF guard blocks a private-IP fetch, local no-egress tools work, and the audit chain verifies."""
    monkeypatch.setattr(srv, "OSINT_LIVE", False)
    monkeypatch.setattr(srv, "CASE_IDENTIFIERS", {"SECRET-CASE-42"})

    async def _go():
        # pre-egress screen blocks a query carrying a case identifier
        assert "case/source identifier" in await _err(
            "search", {"query": "exfil SECRET-CASE-42", "connector": "web"}
        )
        # a clean query passes the screen + audit, then fails closed (live off)
        assert "live connector disabled" in await _err(
            "search", {"query": "public tide tables", "connector": "web"}
        )
        # provenance gate: a URL from no prior search result and no override is refused (audited before raising)
        assert "did not originate" in await _err(
            "fetch", {"url": "https://unseen.example.invalid/x"}
        )
        # SSRF guard blocks a private-IP fetch even with the analyst override; the resolved IP is not echoed
        blocked = await _err("fetch", {"url": "https://10.0.0.1/x", "confirmed": True})
        assert "egress guard blocked" in blocked and "10.0.0.1" not in blocked
        # consent gates on the two third-party-disclosure tools
        tok = srv.artifacts.put(_JPEG)
        assert "confirmed=True" in await _err(
            "reverse_image_search", {"artifact_ref": tok, "connector": "image"}
        )
        assert "confirmed=True" in await _err(
            "get_map_tile", {"lat": 1.0, "lon": 2.0, "zoom": 5, "connector": "map"}
        )
        # local no-egress tool + audit chain
        h = await _data("compute_hash", {"artifact_ref": tok})
        assert len(h.sha256) == 64
        assert (await _data("verify_chain", {})).ok is True

    asyncio.run(_go())


def test_search_live_connector_stub(monkeypatch):
    """search: with OSINT_LIVE on, a clean query passes the screen + audit then fails closed because no live
    connector is wired in this deployment (server line 140)."""
    monkeypatch.setattr(srv, "OSINT_LIVE", True)

    async def _go():
        assert "no live connector configured" in await _err(
            "search", {"query": "public weather data", "connector": "web"}
        )

    asyncio.run(_go())


def test_fetch_live_off_pins_and_fails_closed(monkeypatch):
    """fetch: a public IP literal passes validate_url with confirmed=True (provenance override); with live off
    the pinned-IP attempt is audited and the call fails closed without echoing the IP (server lines 182-185)."""
    monkeypatch.setattr(srv, "OSINT_LIVE", False)

    async def _go():
        msg = await _err("fetch", {"url": "https://93.184.216.34/x", "confirmed": True})
        assert "live fetch disabled" in msg
        assert "93.184.216.34" not in msg  # the pinned IP stays in the audit log only

    asyncio.run(_go())


def test_fetch_live_on_guard_block_during_fetch(monkeypatch):
    """fetch: on the live path a redirect hop that fails the egress guard (EgressError from fetch_pinned) is
    audited as a fetch-guard block and surfaced without the raw guard detail (server lines 196-198)."""
    monkeypatch.setattr(srv, "OSINT_LIVE", True)

    def blocked(url):
        raise eg.EgressError("redirect hop resolves to a blocked internal IP")

    monkeypatch.setattr(eg, "fetch_pinned", blocked)

    async def _go():
        msg = await _err("fetch", {"url": "https://93.184.216.34/x", "confirmed": True})
        assert "egress guard blocked during fetch" in msg
        assert "redirect hop" not in msg  # raw EgressError detail masked

    asyncio.run(_go())


def test_fetch_live_on_success(monkeypatch):
    """fetch: the live success path stores the body as an opaque artifact, audits 'ok', records the final URL as
    provenance, and returns a FetchedArtifact with the real hash/size (server lines 211-214)."""
    monkeypatch.setattr(srv, "OSINT_LIVE", True)
    monkeypatch.setattr(srv, "_session_urls", set())
    body = b"<html>candidate page body</html>"

    def ok(url):
        return "https://93.184.216.34/final", body, "text/html"

    monkeypatch.setattr(eg, "fetch_pinned", ok)

    async def _go():
        d = await _data("fetch", {"url": "https://93.184.216.34/x", "confirmed": True})
        assert d.host == "93.184.216.34"
        assert d.content_type == "text/html"
        assert d.size == len(body)
        assert len(d.sha256) == 64
        assert "https://93.184.216.34/final" in srv._session_urls  # provenance recorded

    asyncio.run(_go())


def test_fetch_live_on_network_error_is_masked(monkeypatch):
    """fetch: a plain socket/TLS/HTTP failure (not an EgressError) from fetch_pinned is caught, audited as a
    network/TLS error, and surfaced as a detail-free ToolError that never leaks the raw cause (server 201-208)."""
    monkeypatch.setattr(srv, "OSINT_LIVE", True)

    def boom(url):
        raise ConnectionRefusedError("connection refused to 93.184.216.34:443")

    monkeypatch.setattr(eg, "fetch_pinned", boom)

    async def _go():
        msg = await _err("fetch", {"url": "https://93.184.216.34/x", "confirmed": True})
        assert "network/TLS" in msg
        assert "connection refused" not in msg.lower()  # raw socket detail masked

    asyncio.run(_go())


def test_compute_hash_unknown_ref():
    """compute_hash: a well-formed but unknown token surfaces the ArtifactError as a ToolError (server 228-229)."""

    async def _go():
        assert "unknown artifact_ref" in await _err(
            "compute_hash", {"artifact_ref": "art_" + "0" * 32}
        )

    asyncio.run(_go())


def test_extract_exif_type_branches():
    """extract_exif (server lines 237-255): an unknown token -> ArtifactError -> ToolError (240-241); non-image
    bytes -> a 'not a recognized image' candidate with empty fields (242-248); a real JPEG -> the parse_exif
    candidate path (249-255)."""

    async def _go():
        # (a) unknown token
        assert "unknown artifact_ref" in await _err(
            "extract_exif", {"artifact_ref": "art_" + "0" * 32}
        )
        # (b) non-image artifact
        txt = srv.artifacts.put(b"plain text, definitely not an image")
        d = await _data("extract_exif", {"artifact_ref": txt})
        assert d.detected_type is None
        assert d.fields == {}
        assert "not a recognized image" in d.note
        # (c) a real JPEG (magic bytes) -> parse path, candidate note
        img = srv.artifacts.put(_JPEG)
        d2 = await _data("extract_exif", {"artifact_ref": img})
        assert d2.detected_type == "image/jpeg"
        assert "candidate" in d2.note

    asyncio.run(_go())


def test_reverse_image_search_confirmed_branches(monkeypatch):
    """reverse_image_search with consent (server lines 280-287): live off -> audited attempt then fail-closed
    (280-281, 284-286); an unknown token -> ArtifactError -> ToolError (282-283); live on -> the
    no-live-connector stub (287)."""

    async def _go():
        tok = srv.artifacts.put(_JPEG)
        monkeypatch.setattr(srv, "OSINT_LIVE", False)
        assert "live connector disabled" in await _err(
            "reverse_image_search", {"artifact_ref": tok, "connector": "image", "confirmed": True}
        )
        assert "unknown artifact_ref" in await _err(
            "reverse_image_search",
            {"artifact_ref": "art_" + "0" * 32, "connector": "image", "confirmed": True},
        )
        monkeypatch.setattr(srv, "OSINT_LIVE", True)
        assert "no live connector configured" in await _err(
            "reverse_image_search", {"artifact_ref": tok, "connector": "image", "confirmed": True}
        )

    asyncio.run(_go())


def test_get_map_tile_confirmed_paths(monkeypatch):
    """get_map_tile with consent: the disclosure gate + audit pass, then live off fails closed (316-317) and
    live on hits the no-live-connector stub (318)."""

    async def _go():
        args = {"lat": 51.5, "lon": -0.12, "zoom": 12, "connector": "map", "confirmed": True}
        monkeypatch.setattr(srv, "OSINT_LIVE", False)
        assert "live connector disabled" in await _err("get_map_tile", args)
        monkeypatch.setattr(srv, "OSINT_LIVE", True)
        assert "no live connector configured" in await _err("get_map_tile", args)

    asyncio.run(_go())


def test_propose_bad_artifact_ref():
    """propose_to_ledger: an unknown artifact token fails at the local hash (which validates the token) before
    any ledger call, surfacing the ArtifactError as a ToolError (server lines 344-345)."""

    async def _go():
        assert "unknown artifact_ref" in await _err(
            "propose_to_ledger",
            {"case_id": "c1", "artifact_ref": "art_" + "0" * 32, "source_id": "s", "note": "n"},
        )

    asyncio.run(_go())


def test_propose_success_dict_response(monkeypatch):
    """propose_to_ledger success path: a valid artifact is hashed locally, the ingested (ungraded) proposal is
    routed to the injected evidence-ledger client, and evidence_id is read from the dict-shaped structured
    content into a ProposalRef (server lines ~346-365, 381-393)."""

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def call_tool(self, name, args):
            assert name == "add_evidence"
            assert args["source_channel"] == "ingested"  # routed as an ungraded ingested proposal
            return types.SimpleNamespace(data={"evidence_id": "ev-123", "case_id": args["case_id"]})

    monkeypatch.setattr(srv, "_ledger_client", lambda: _FakeClient())

    async def _go():
        tok = srv.artifacts.put(_JPEG)
        d = await _data(
            "propose_to_ledger",
            {
                "case_id": "c9",
                "artifact_ref": tok,
                "source_id": "osint:web",
                "note": "ingested page",
            },
        )
        assert d.evidence_id == "ev-123"
        assert d.case_id == "c9"

    asyncio.run(_go())


def test_propose_ledger_error_branches(monkeypatch):
    """propose_to_ledger transport/shape handling: a ToolError from evidence-ledger is surfaced verbatim
    (366-367); any other exception becomes a fixed, detail-free transport error, never leaking the raw cause
    (368-374); a response with no structured content is a clear shape error (383)."""

    class _FakeClient:
        def __init__(self, *, exc=None, data="__unset__"):
            self._exc = exc
            self._data = data

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def call_tool(self, name, args):
            if self._exc is not None:
                raise self._exc
            return types.SimpleNamespace(data=self._data)

    async def _go():
        tok = srv.artifacts.put(_JPEG)
        base = {"case_id": "c1", "artifact_ref": tok, "source_id": "s", "note": "n"}
        # (a) no ledger connection configured -> fail closed, never open a second single-writer (server 348)
        monkeypatch.setattr(srv, "_ledger_client", lambda: None)
        assert "requires a configured evidence-ledger connection" in await _err(
            "propose_to_ledger", base
        )
        # (b) a business-rule ToolError from the ledger -> surfaced verbatim
        monkeypatch.setattr(
            srv,
            "_ledger_client",
            lambda: _FakeClient(exc=ToolError("ledger rejected: item too large")),
        )
        assert "ledger rejected: item too large" in await _err("propose_to_ledger", base)
        # (c) a raw transport exception -> masked, fixed reason code (the raw detail never leaks)
        monkeypatch.setattr(
            srv,
            "_ledger_client",
            lambda: _FakeClient(exc=RuntimeError("dial tcp 10.1.2.3:9000 refused")),
        )
        masked = await _err("propose_to_ledger", base)
        assert "transport error" in masked and "10.1.2.3" not in masked
        # (d) a structured-content-less response -> a clear shape error (server 383)
        monkeypatch.setattr(srv, "_ledger_client", lambda: _FakeClient(data=None))
        assert "no structured content" in await _err("propose_to_ledger", base)
        # (e) a dict-shaped response missing evidence_id -> a clear shape error (server 390)
        monkeypatch.setattr(
            srv, "_ledger_client", lambda: _FakeClient(data={"unexpected": "shape"})
        )
        assert "missing evidence_id" in await _err("propose_to_ledger", base)

    asyncio.run(_go())


def test_ledger_client_factory(monkeypatch):
    """_ledger_client factory (server lines 77-81): None when EVIDENCE_LEDGER_URL is unset, a constructed
    fastmcp Client when it is set. test_osint_wire.py replaces srv._ledger_client at import with an in-memory
    factory, so only assert the fail-closed None branch when the real factory is in place (combined-run safe)."""
    real_factory = getattr(srv._ledger_client, "__name__", "") == "_ledger_client"
    monkeypatch.setattr(srv, "EVIDENCE_LEDGER_URL", None)
    unset = srv._ledger_client()
    monkeypatch.setattr(srv, "EVIDENCE_LEDGER_URL", "http://localhost:9765/mcp")
    configured = srv._ledger_client()
    assert configured is not None  # a Client is constructed for a configured URL
    if real_factory:
        assert unset is None  # real factory fails closed (returns None) when unconfigured


def test_ledger_url_is_local_classification():
    """_ledger_url_is_local (server lines 407-416): loopback names/IPs and an empty host are on-box; a public IP
    and an unverifiable DNS name are treated as remote (fail closed)."""
    assert srv._ledger_url_is_local("http://localhost:8000/mcp") is True
    assert srv._ledger_url_is_local("http://127.0.0.1:8000/mcp") is True
    assert srv._ledger_url_is_local("file:///no/host") is True  # empty host
    assert srv._ledger_url_is_local("http://8.8.8.8:8000/mcp") is False  # public IP, not loopback
    assert (
        srv._ledger_url_is_local("http://ledger.example.com/mcp") is False
    )  # DNS name -> unverifiable


def test_main_startup_scenarios(monkeypatch):
    """main() startup gate (server lines 420-458): (1) a failed audit chain refuses to serve; (2) a non-loopback
    EVIDENCE_LEDGER_URL without the remote opt-in refuses to serve; (3) OSINT_LIVE with no case identifiers
    refuses to serve; (4) the clean path warns on empty identifiers and calls mcp.run()."""
    ok_status = types.SimpleNamespace(ok=True, rows_verified=3, mismatch=None)

    # (1) audit chain failure -> refuse to serve before anything else (420-426)
    monkeypatch.setattr(
        srv.audit,
        "verify_chain",
        lambda: types.SimpleNamespace(ok=False, mismatch="tampered", rows_verified=0),
    )
    try:
        srv.main()
        raise AssertionError("expected SystemExit on a failed audit chain")
    except SystemExit as e:
        assert e.code == 1

    # (2) a non-loopback ledger URL with no remote opt-in -> refuse (429-437)
    monkeypatch.setattr(srv.audit, "verify_chain", lambda: ok_status)
    monkeypatch.setattr(srv, "EVIDENCE_LEDGER_URL", "http://ledger.example.com/mcp")
    monkeypatch.delenv("OSINT_LEDGER_ALLOW_REMOTE", raising=False)
    try:
        srv.main()
        raise AssertionError("expected SystemExit on a non-loopback ledger URL")
    except SystemExit as e:
        assert e.code == 1

    # (3) live egress on with no configured identifiers -> the screen is inert -> refuse (440-446)
    monkeypatch.setattr(srv, "EVIDENCE_LEDGER_URL", None)
    monkeypatch.setattr(srv, "OSINT_LIVE", True)
    monkeypatch.setattr(srv, "CASE_IDENTIFIERS", set())
    try:
        srv.main()
        raise AssertionError("expected SystemExit when OSINT_LIVE is on with no identifiers")
    except SystemExit as e:
        assert e.code == 1

    # (4) clean path: live off, empty identifiers -> warning, then serve with mcp.run stubbed (447-458)
    ran: list[bool] = []
    monkeypatch.setattr(srv, "OSINT_LIVE", False)
    monkeypatch.setattr(srv, "CASE_IDENTIFIERS", set())
    monkeypatch.setattr(srv.mcp, "run", lambda *a, **k: ran.append(True))
    srv.main()
    assert ran == [True]  # reached the serve path
