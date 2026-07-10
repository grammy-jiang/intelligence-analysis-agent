"""Wire-level smoke for osint-toolkit: tools register, the security path (gate/guard/audit/provenance) runs,
propose_to_ledger writes an ingested UNGRADED item. Live egress off (OSINT_LIVE unset)."""

from __future__ import annotations

import asyncio
import os
import tempfile

_TMP = tempfile.mkdtemp()
os.environ["OSINT_AUDIT_DB"] = os.path.join(_TMP, "audit.db")
os.environ["OSINT_ARTIFACTS_DIR"] = os.path.join(_TMP, "art")
os.environ["EVIDENCE_DB"] = os.path.join(_TMP, "evidence.db")
os.environ["STALENESS_DB"] = os.path.join(_TMP, "staleness.db")
os.environ["OSINT_CASE_IDENTIFIERS"] = "SECRET-CASE-42"
os.environ.pop("OSINT_LIVE", None)

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.osint_toolkit import server as srv  # noqa: E402
from mcp_servers.osint_toolkit.server import mcp  # noqa: E402


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
        # propose_to_ledger writes an INGESTED, UNGRADED item (ach-engine will refuse to score it)
        p = await c.call_tool(
            "propose_to_ledger",
            {"case_id": "c1", "artifact_ref": tok, "source_id": "osint:web", "note": "an ingested page"},
        )
        rec = srv._evidence.get_evidence(p.data.evidence_id)
        assert rec.source_channel == "ingested" and rec.grades == []
        # egress audit chain verifies
        v = await c.call_tool("verify_chain", {})
        assert v.data.ok is True


def test_osint_wire():
    asyncio.run(_run())
