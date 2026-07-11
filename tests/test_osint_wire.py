"""Wire-level smoke for osint-toolkit: tools register, the security path (gate/guard/audit/provenance) runs,
propose_to_ledger routes an ingested UNGRADED proposal to evidence-ledger over the MCP boundary (osint is NOT
itself a ledger writer — M1). Live egress off (OSINT_LIVE unset)."""

from __future__ import annotations

import asyncio
import os
import tempfile

_TMP = tempfile.mkdtemp()
os.environ["OSINT_AUDIT_DB"] = os.path.join(_TMP, "audit.db")
os.environ["OSINT_ARTIFACTS_DIR"] = os.path.join(_TMP, "art")
os.environ.setdefault("EVIDENCE_DB", ":memory:")
os.environ.setdefault("STALENESS_DB", ":memory:")
os.environ["OSINT_CASE_IDENTIFIERS"] = "SECRET-CASE-42"
os.environ.pop("OSINT_LIVE", None)

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.evidence_ledger.server import mcp as ev_mcp  # noqa: E402
from mcp_servers.osint_toolkit import server as srv  # noqa: E402
from mcp_servers.osint_toolkit.server import mcp  # noqa: E402

# M1: inject an in-memory client to the single evidence-ledger writer (production uses EVIDENCE_LEDGER_URL).
srv._ledger_client = lambda: Client(ev_mcp)


async def _run() -> None:
    async with Client(mcp) as c:
        names = {t.name for t in await c.list_tools()}
        assert {
            "search", "fetch", "compute_hash", "extract_exif", "reverse_image_search",
            "get_map_tile", "propose_to_ledger", "verify_chain",
        } <= names

        async def expect(tool, args, needle):
            try:
                await c.call_tool(tool, args)
                raise AssertionError(f"expected ToolError from {tool}")
            except ToolError as e:
                assert needle in str(e), f"{tool}: {e}"

        # pre-egress gate blocks a query carrying a case identifier
        await expect("search", {"query": "dig up SECRET-CASE-42", "connector": "web"}, "case/source identifier")
        # a clean query passes the gate, then fails closed (live off) — audit ran
        await expect("search", {"query": "public weather data", "connector": "web"}, "live connector disabled")
        # fetch provenance: a URL not from a prior result is refused
        await expect("fetch", {"url": "https://api.example-search.invalid/x"}, "did not originate")
        # exact-match provenance passes that check (then fails later at the guard/DNS, not "did not originate")
        srv._session_urls.add("https://api.example-search.invalid/exact")
        await expect("fetch", {"url": "https://api.example-search.invalid/DIFFERENT"}, "did not originate")
        await expect("fetch", {"url": "https://api.example-search.invalid/exact"}, "egress guard blocked")
        # SSRF guard blocks a metadata-IP fetch even when confirmed
        await expect(
            "fetch", {"url": "https://169.254.169.254/latest/meta-data", "confirmed": True}, "egress guard blocked"
        )
        # reverse_image_search requires confirmation (may upload a likeness)
        tok = srv.artifacts.put(b"\xff\xd8\xff\xe0 image bytes")
        await expect("reverse_image_search", {"artifact_ref": tok, "connector": "image"}, "confirmed=True")

        # local, no-egress tools work
        r = await c.call_tool("compute_hash", {"artifact_ref": tok})
        assert len(r.data.sha256) == 64
        # propose_to_ledger routes an INGESTED, UNGRADED item into evidence-ledger (ach-engine refuses to score it)
        p = await c.call_tool(
            "propose_to_ledger",
            {"case_id": "c1", "artifact_ref": tok, "source_id": "osint:web", "note": "an ingested page"},
        )
        eid = p.data.evidence_id
        async with Client(ev_mcp) as ec:
            rec = await ec.call_tool("get_evidence", {"evidence_id": eid})
        assert rec.data.source_channel == "ingested" and rec.data.grades == []
        # M2/S17: an oversized identifier is rejected at this tool's schema (before touching the append-only ledger)
        await expect(
            "propose_to_ledger",
            {"case_id": "x" * 600, "artifact_ref": tok, "source_id": "s", "note": "n"},
            "",  # any ToolError; Pydantic max_length rejection
        )
        # egress audit chain verifies
        v = await c.call_tool("verify_chain", {})
        assert v.data.ok is True


def test_osint_wire():
    asyncio.run(_run())


def test_fetch_guard_block_does_not_leak_resolved_ip():
    """MF1: a blocked-IP fetch must not disclose the resolved internal IP back to the caller (recon oracle);
    the host/IP stay in the audit log only."""

    async def _go() -> None:
        async with Client(mcp) as c:
            try:
                await c.call_tool("fetch", {"url": "https://10.0.0.1/x", "confirmed": True})
                raise AssertionError("expected ToolError")
            except ToolError as e:
                assert "10.0.0.1" not in str(e)  # internal IP must not leak
                assert "audit log only" in str(e)

    asyncio.run(_go())


def test_live_fetch_network_error_is_audited_and_masked(monkeypatch):
    """MF2: a socket/TLS failure on the live path must be caught (not escape as an opaque masked error) AND
    the attempt must be audited (control #10)."""
    from mcp_servers.osint_toolkit import egress as eg

    monkeypatch.setattr(srv, "OSINT_LIVE", True)

    def boom(url):
        raise ConnectionRefusedError("connection refused")

    monkeypatch.setattr(eg, "fetch_pinned", boom)

    def count(outcome):
        row = srv.audit._conn.execute(
            "SELECT COUNT(*) c FROM egress_log WHERE outcome=?", (outcome,)
        ).fetchone()
        return row["c"]

    before_attempt, before_err = count("attempt (live)"), count("error (network/TLS)")

    async def _go() -> None:
        async with Client(mcp) as c:
            try:
                # public IP literal → validate_url passes with no DNS; confirmed=True satisfies provenance
                await c.call_tool("fetch", {"url": "https://93.184.216.34/x", "confirmed": True})
                raise AssertionError("expected ToolError")
            except ToolError as e:
                assert "network/TLS" in str(e)
                assert "connection refused" not in str(e).lower()  # raw exception detail masked

    asyncio.run(_go())
    assert count("attempt (live)") == before_attempt + 1  # attempt logged before the socket opened
    assert count("error (network/TLS)") == before_err + 1  # failure logged
    assert srv.audit.verify_chain().ok is True


def test_get_map_tile_requires_confirmation():
    """S6: get_map_tile discloses coordinates to a third party → same confirmed gate as fetch."""

    async def _go() -> None:
        async with Client(mcp) as c:
            try:
                await c.call_tool("get_map_tile", {"lat": 51.5, "lon": -0.12, "zoom": 12, "connector": "map"})
                raise AssertionError("expected ToolError")
            except ToolError as e:
                assert "confirmed=True" in str(e)
            # with consent it passes the gate then fails closed (live off)
            try:
                await c.call_tool(
                    "get_map_tile",
                    {"lat": 51.5, "lon": -0.12, "zoom": 12, "connector": "map", "confirmed": True},
                )
                raise AssertionError("expected ToolError")
            except ToolError as e:
                assert "live connector disabled" in str(e)

    asyncio.run(_go())


def test_screen_normalizes_separators():
    """S7: a separator/case-obfuscated identifier no longer bypasses the pre-egress screen."""

    async def _go() -> None:
        async with Client(mcp) as c:
            for q in ["dig up secret case 42", "SECRET.CASE.42", "Secret-Case_42"]:
                try:
                    await c.call_tool("search", {"query": q, "connector": "web"})
                    raise AssertionError(f"expected ToolError for {q!r}")
                except ToolError as e:
                    assert "case/source identifier" in str(e)

    asyncio.run(_go())


def test_blocked_screen_leaves_audit_row():
    """MF1: a pre-egress screen block (an exfiltration attempt — the highest-signal event) must STILL write an
    audit row. Previously _screen raised before the first audit.record, so a blocked exfil left no trace,
    breaking control #10 (every egress attempt audited) on exactly the path that matters most."""

    def blocked_count():
        return srv.audit._conn.execute(
            "SELECT COUNT(*) c FROM egress_log WHERE outcome=?", ("blocked (screen)",)
        ).fetchone()["c"]

    async def _go() -> None:
        async with Client(mcp) as c:
            before = blocked_count()
            for tool, args in (
                ("search", {"query": "leak SECRET-CASE-42 now", "connector": "web"}),
                ("fetch", {"url": "https://x.invalid/SECRET-CASE-42", "confirmed": True}),
            ):
                try:
                    await c.call_tool(tool, args)
                    raise AssertionError(f"expected ToolError from {tool}")
                except ToolError as e:
                    assert "case/source identifier" in str(e)
            assert blocked_count() == before + 2  # both blocked attempts left an audit trail
            assert srv.audit.verify_chain().ok is True  # and the audit chain + manifest stay consistent

    asyncio.run(_go())


def test_propose_handles_dict_shaped_ledger_response(monkeypatch):
    """MF2: evidence-ledger's structured result may arrive as a plain dict (this client holds no pydantic model
    for the callee's output schema). propose_to_ledger must read evidence_id from a dict-or-model, never crash
    on a bare `.evidence_id` deref (which would mask every ledger write as an opaque error)."""

    class _Res:
        def __init__(self, data):
            self.data = data

    def fake_client(data):
        class _FakeClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def call_tool(self, name, args):
                return _Res(data)

        return lambda: _FakeClient()

    async def _go() -> None:
        async with Client(mcp) as c:
            tok = srv.artifacts.put(b"\xff\xd8\xff\xe0 img")
            # a well-formed DICT result -> evidence_id read from the dict, no AttributeError crash
            monkeypatch.setattr(srv, "_ledger_client", fake_client({"evidence_id": "ev-dict", "case_id": "c1"}))
            p = await c.call_tool(
                "propose_to_ledger", {"case_id": "c1", "artifact_ref": tok, "source_id": "s", "note": "n"}
            )
            assert p.data.evidence_id == "ev-dict"
            # a shape-drifted dict (no evidence_id) -> a clear ToolError, not an opaque masked error
            monkeypatch.setattr(srv, "_ledger_client", fake_client({"unexpected": "shape"}))
            try:
                await c.call_tool(
                    "propose_to_ledger", {"case_id": "c1", "artifact_ref": tok, "source_id": "s", "note": "n"}
                )
                raise AssertionError("expected ToolError for a dict missing evidence_id")
            except ToolError as e:
                assert "unexpected response shape" in str(e)

    asyncio.run(_go())


def test_propose_requires_configured_ledger(monkeypatch):
    """M1: with no evidence-ledger connection configured, propose fails closed (does NOT open a second
    in-process writer to the single-writer evidence.db)."""
    monkeypatch.setattr(srv, "_ledger_client", lambda: None)

    async def _go() -> None:
        async with Client(mcp) as c:
            tok = srv.artifacts.put(b"\xff\xd8\xff\xe0 img")
            try:
                await c.call_tool(
                    "propose_to_ledger",
                    {"case_id": "c1", "artifact_ref": tok, "source_id": "s", "note": "n"},
                )
                raise AssertionError("expected ToolError when ledger unconfigured")
            except ToolError as e:
                assert "not itself a ledger writer" in str(e)

    asyncio.run(_go())
