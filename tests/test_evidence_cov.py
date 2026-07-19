"""Coverage-focused tests for evidence-ledger server.py tool bodies.

Exercises every @mcp.tool (add_evidence / grade_evidence / update_grade / get_evidence / list_evidence /
get_source_history / verify_chain / verify_signals_chain) plus the main() entrypoint over an in-memory
fastmcp Client, hitting each tool's success AND its error/ToolError branch. Mirrors the env-before-import
in-memory Client pattern of test_evidence_ach_wire.py / test_osint_wire.py.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from types import SimpleNamespace

# Real (non-:memory:) DB paths, set BEFORE importing the server, so the import-time makedirs branch runs
# and the store exercises its on-disk manifest path. Mirrors the wire tests setting EVIDENCE_DB up front.
_TMP = tempfile.mkdtemp()
os.environ["EVIDENCE_DB"] = os.path.join(_TMP, "evidence.db")
os.environ["STALENESS_DB"] = os.path.join(_TMP, "staleness.db")
os.environ.setdefault("EVIDENCE_ANALYST_ID", "cov-analyst")

import pytest  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

from mcp_servers.evidence_ledger import server  # noqa: E402
from mcp_servers.evidence_ledger.server import mcp as ev_mcp  # noqa: E402
from mcp_servers.evidence_ledger.store import EvidenceError  # noqa: E402


def _args(**over) -> dict:
    """A valid add_evidence payload; override any field via kwargs."""
    a = {
        "case_id": "cov",
        "item": "an item",
        "source_id": "src",
        "evidence_type": "report",
        "pii": False,
        "source_channel": "analyst_typed",
    }
    a.update(over)
    return a


async def _err(c, tool, payload) -> str:
    try:
        await c.call_tool(tool, payload)
        raise AssertionError(f"expected ToolError from {tool}")
    except ToolError as e:
        return str(e)


async def _add_ok(c, **over) -> str:
    r = await c.call_tool("add_evidence", _args(**over))
    return r.data.evidence_id


def test_add_evidence_observable_caps_are_tool_errors():
    """add_evidence tool-boundary validation of expected_observables (count / key / value caps)."""

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            # too many entries -> the count guard
            too_many = {f"h{i}": "x" for i in range(server._MAX_OBSERVABLES + 1)}
            assert "too many entries" in await _err(
                c, "add_evidence", _args(expected_observables=too_many)
            )
            # an oversized KEY -> the per-entry key guard (loop body, first branch)
            assert "key exceeds max length" in await _err(
                c, "add_evidence", _args(expected_observables={"k" * (server._MAX_ID + 1): "ok"})
            )
            # an oversized VALUE -> the per-entry value guard (loop body, second branch)
            assert "value exceeds max length" in await _err(
                c,
                "add_evidence",
                _args(expected_observables={"h": "v" * (server._MAX_OBSERVABLE_VAL + 1)}),
            )
            # a valid observables dict flows straight through to the store (loop runs, no raise)
            eid = await _add_ok(c, expected_observables={"h1": "should see X"})
            rec = await c.call_tool("get_evidence", {"evidence_id": eid})
            assert rec.data.expected_observables == {"h1": "should see X"}

    asyncio.run(_go())


def test_add_evidence_store_error_becomes_tool_error(monkeypatch):
    """A store-layer EvidenceError raised inside add_evidence is wrapped as a ToolError."""

    def boom(*a, **k):
        raise EvidenceError("store add boom")

    monkeypatch.setattr(server.store, "add_evidence", boom)

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            assert "store add boom" in await _err(c, "add_evidence", _args())

    asyncio.run(_go())


def test_update_grade_success_and_missing_prior():
    """update_grade success path (supersede) and its no-prior-grade EvidenceError -> ToolError."""

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            eid = await _add_ok(c)
            await c.call_tool(
                "grade_evidence",
                {
                    "evidence_id": eid,
                    "reliability": "B",
                    "credibility": "2",
                    "diagnosticity": "d",
                    "judgment_source": "analyst_confirmed",
                },
            )
            rec = await c.call_tool(
                "update_grade",
                {
                    "evidence_id": eid,
                    "reliability": "A",
                    "credibility": "1",
                    "diagnosticity": "d",
                    "reason": "new corroboration",
                    "judgment_source": "analyst_confirmed",
                },
            )
            assert rec.data.grades[-1].reliability == "A"
            assert rec.data.grades[-1].superseded is False

            # a second item with NO prior grade -> update_grade must error
            eid2 = await _add_ok(c)
            assert "no prior grade" in await _err(
                c,
                "update_grade",
                {
                    "evidence_id": eid2,
                    "reliability": "A",
                    "credibility": "1",
                    "diagnosticity": "d",
                    "reason": "r",
                    "judgment_source": "analyst_confirmed",
                },
            )

    asyncio.run(_go())


def test_get_evidence_success_and_unknown():
    """get_evidence returns a record for a known id and wraps the store's unknown-id EvidenceError."""

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            eid = await _add_ok(c)
            rec = await c.call_tool("get_evidence", {"evidence_id": eid})
            assert rec.data.evidence_id == eid
            assert "unknown evidence_id" in await _err(
                c, "get_evidence", {"evidence_id": "nonesuch"}
            )

    asyncio.run(_go())


def test_list_evidence_success_and_bad_limit():
    """list_evidence returns items for a case and wraps the store's bad-limit EvidenceError."""

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            await _add_ok(c, case_id="listcase")
            lst = await c.call_tool("list_evidence", {"case_id": "listcase"})
            assert len(lst.data.items) >= 1
            assert "limit must be in" in await _err(
                c, "list_evidence", {"case_id": "listcase", "limit": 0}
            )

    asyncio.run(_go())


def test_get_source_history_success_and_store_error(monkeypatch):
    """get_source_history success path, then a store-raised EvidenceError wrapped as ToolError."""

    async def _ok() -> None:
        async with Client(ev_mcp) as c:
            await _add_ok(c, source_id="srcHist")
            h = await c.call_tool("get_source_history", {"source_id": "srcHist"})
            assert h.data.source_id == "srcHist"

    asyncio.run(_ok())

    def boom(*a, **k):
        raise EvidenceError("history boom")

    monkeypatch.setattr(server.store, "get_source_history", boom)

    async def _err_path() -> None:
        async with Client(ev_mcp) as c:
            assert "history boom" in await _err(c, "get_source_history", {"source_id": "srcHist"})

    asyncio.run(_err_path())


def test_verify_chain_and_signals_chain():
    """Both verify tools return a passing ChainStatus over the healthy in-memory session."""

    async def _go() -> None:
        async with Client(ev_mcp) as c:
            assert (await c.call_tool("verify_chain", {})).data.ok is True
            assert (await c.call_tool("verify_signals_chain", {})).data.ok is True

    asyncio.run(_go())


def test_main_serves_when_chains_ok(monkeypatch):
    """main() verifies both chains and, on success, prints OK and hands off to mcp.run (stubbed)."""
    calls: list[dict] = []
    monkeypatch.setattr(server.mcp, "run", lambda **kw: calls.append(kw))
    server.main()
    assert calls and calls[0]["transport"] == "stdio"


def test_main_refuses_when_chain_bad(monkeypatch):
    """main() fails closed (SystemExit) when a chain does not verify — it must not reach mcp.run."""
    monkeypatch.setattr(
        server.mcp, "run", lambda **kw: pytest.fail("must not serve on a bad chain")
    )
    monkeypatch.setattr(
        server.store, "verify_chain", lambda: SimpleNamespace(ok=False, mismatch=None)
    )
    with pytest.raises(SystemExit):
        server.main()
