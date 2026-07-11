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


async def _ach_hypothesis_length_cap() -> None:
    async with Client(ach_mcp) as c:
        # M2: each hypothesis STRING is capped at _MAX_TEXT (not only the list length) — an oversized
        # hypothesis is rejected at the tool schema before it can persist into the append-only store.
        try:
            await c.call_tool("create_matrix", {"case_id": "c", "hypotheses": ["ok", "x" * 10_001]})
            raise AssertionError("expected ToolError for an oversized hypothesis")
        except ToolError:
            pass
        # min_length=1: an empty hypothesis list is rejected at the schema too.
        try:
            await c.call_tool("create_matrix", {"case_id": "c", "hypotheses": []})
            raise AssertionError("expected ToolError for an empty hypothesis list")
        except ToolError:
            pass


async def _ev_read_path_id_cap() -> None:
    async with Client(ev_mcp) as c:
        # SF1: read-path IDs carry the same _MAX_ID (512) cap as the write tools — an oversized id is
        # rejected at the schema, never reaching SQLite.
        for tool, args in (
            ("get_evidence", {"evidence_id": "x" * 600}),
            ("list_evidence", {"case_id": "x" * 600}),
            ("get_source_history", {"source_id": "x" * 600}),
        ):
            try:
                await c.call_tool(tool, args)
                raise AssertionError(f"expected ToolError from {tool} on an oversized id")
            except ToolError:
                pass


def test_evidence_wire():
    asyncio.run(_ev())


def test_ach_wire():
    asyncio.run(_ach())


def test_ach_hypothesis_length_cap():
    asyncio.run(_ach_hypothesis_length_cap())


def test_evidence_read_path_id_cap():
    asyncio.run(_ev_read_path_id_cap())
