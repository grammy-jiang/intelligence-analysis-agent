"""Wire-level MCP smoke for evidence-ledger + ach-engine (tools register, schemas resolve, errors surface)."""

from __future__ import annotations

import asyncio
import os

os.environ["EVIDENCE_DB"] = ":memory:"
os.environ["ACH_DB"] = ":memory:"
os.environ["STALENESS_DB"] = ":memory:"

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.ach_engine.server import mcp as ach_mcp  # noqa: E402
from mcp_servers.evidence_ledger.server import mcp as ev_mcp  # noqa: E402


async def _ev() -> None:
    async with Client(ev_mcp) as c:
        names = {t.name for t in await c.list_tools()}
        assert {
            "add_evidence", "grade_evidence", "update_grade", "get_evidence",
            "list_evidence", "get_source_history", "verify_chain",
        } <= names
        r = await c.call_tool(
            "add_evidence",
            {"case_id": "w", "item": "x", "source_id": "s", "evidence_type": "report",
             "pii": False, "source_channel": "analyst_typed"},
        )
        eid = r.data.evidence_id
        await c.call_tool(
            "grade_evidence",
            {"evidence_id": eid, "reliability": "B", "credibility": "2",
             "diagnosticity": "d", "judgment_source": "analyst_confirmed"},
        )
        try:
            await c.call_tool(
                "grade_evidence",
                {"evidence_id": eid, "reliability": "A", "credibility": "1",
                 "diagnosticity": "d", "judgment_source": "analyst_confirmed"},
            )
            raise AssertionError("expected ToolError re-grading")
        except ToolError as e:
            assert "already exists" in str(e)


async def _ach() -> None:
    async with Client(ach_mcp) as c:
        names = {t.name for t in await c.list_tools()}
        assert {
            "create_matrix", "add_hypothesis", "rate_cell", "score_matrix",
            "get_matrix", "list_matrices", "verify_chain",
        } <= names
        r = await c.call_tool("create_matrix", {"case_id": "w", "hypotheses": ["H1", "H2"]})
        assert len(r.data.hypotheses) == 2


def test_evidence_wire():
    asyncio.run(_ev())


def test_ach_wire():
    asyncio.run(_ach())
