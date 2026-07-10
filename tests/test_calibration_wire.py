"""Wire-level MCP smoke test — tools register, schemas resolve, error channel works.

Uses FastMCP's in-memory client (no subprocess). :memory: DB set before the server module imports.
"""

from __future__ import annotations

import asyncio
import os

os.environ["CALIBRATION_DB"] = ":memory:"

from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.calibration_tracker.server import mcp  # noqa: E402

EXPECTED_TOOLS = {
    "log_forecast", "resolve_forecast", "void_forecast", "get_forecast",
    "list_forecasts", "get_calibration_report", "verify_chain",
}


async def _run() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert EXPECTED_TOOLS <= names, f"missing tools: {EXPECTED_TOOLS - names}"
        # every tool exposes an input schema (FastMCP derives it from the typed signature)
        for t in tools:
            assert t.inputSchema and t.inputSchema.get("type") == "object"

        # happy path
        res = await client.call_tool(
            "log_forecast",
            {
                "case_id": "w", "question": "q", "probability": 0.5,
                "resolution_criteria": "resolves yes/no", "horizon": "3mo",
                "judgment_source": "analyst_confirmed",
            },
        )
        fid = res.data.forecast_id
        assert fid

        # error channel: model_draft is rejected as a ToolError, not a silent bad result
        try:
            await client.call_tool(
                "log_forecast",
                {
                    "case_id": "w", "question": "q2", "probability": 0.5,
                    "resolution_criteria": "def", "horizon": "3mo",
                    "judgment_source": "model_draft",
                },
            )
            raise AssertionError("expected ToolError for model_draft log_forecast")
        except ToolError as e:
            assert "analyst_confirmed" in str(e)

        # resolve + report round-trips through the wire
        await client.call_tool(
            "resolve_forecast", {"forecast_id": fid, "outcome": True, "resolved_at": "2026-01-01"}
        )
        rep = await client.call_tool("get_calibration_report", {"case_id": "w"})
        assert rep.data.n == 1


def test_wire_smoke():
    asyncio.run(_run())
