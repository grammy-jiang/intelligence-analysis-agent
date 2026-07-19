"""Coverage tests for ach-engine server.py + store.py (added file; no product edits).

Mirrors the two existing styles:
  * tests/test_ach_engine.py — direct ACHStore unit tests (file-based store).
  * tests/test_evidence_ach_wire.py — in-memory fastmcp Client with the DB env vars set to
    ":memory:" BEFORE importing the server module.

Targets the server tool bodies + their ACHError->ToolError translation, `_resolve_db`, `main()`,
and the store edge cases (chmod best-effort, the `_head` table guard, `seed_manifest_baseline`,
blank hypothesis text / blank evidence_id refusals, the weak-inconsistency tally, and
`list_matrices` pagination).
"""

from __future__ import annotations

import asyncio
import os

os.environ["ACH_DB"] = ":memory:"
os.environ["STALENESS_DB"] = ":memory:"

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_servers.ach_engine import server as ach_server
from mcp_servers.ach_engine.store import ACHError, ACHStore
from mcp_servers.common import ChainMismatch, ChainStatus
from mcp_servers.staleness import StalenessStore


@pytest.fixture()
def ach(tmp_path):
    """A fresh file-based ACHStore (needed so chmod / manifest paths exist — unlike the module's
    in-memory store) with its own staleness signal DB. Mirrors tests/test_ach_engine.py::ach."""
    st = StalenessStore(str(tmp_path / "stale.db"))
    s = ACHStore(str(tmp_path / "ach.db"), st, analyst_id="t")
    yield s
    s.close()
    st.close()


def _rate(store, mid, ev, hid, cons, strength="strong", js="analyst_confirmed"):
    # evidence must carry an effective analyst_confirmed grade before its cells can be scored
    store.staleness.mark_graded(ev, "analyst_confirmed")
    return store.rate_cell(mid, ev, hid, cons, strength, js)


# --------------------------------------------------------------------------- store: edge cases


def test_head_rejects_unknown_table(ach):
    # store.py 126: S2 explicit guard (not assert) before the f-string SQL-identifier interpolation.
    with pytest.raises(ValueError, match="unknown table"):
        ach._head("not_a_real_table")


def test_restrict_perms_chmod_is_best_effort(ach, monkeypatch):
    # store.py 116-117: _restrict_perms swallows a chmod OSError (a managed FS may forbid chmod).
    def boom(*args, **kwargs):
        raise OSError("chmod not permitted here")

    monkeypatch.setattr(os, "chmod", boom)
    # the DB file exists (file-based store), so chmod is attempted and the except: pass must fire.
    ach._restrict_perms()  # must not raise


def test_seed_manifest_baseline_reattests(ach):
    # store.py 135-143: one-time migration attesting current per-table (head, count). Remove the
    # manifest first so seed() actually re-attests (matrices + hypotheses heads; cells still genesis).
    ach.create_matrix("c", ["H1"])
    mp = ach.manifest_path
    assert mp and os.path.exists(mp)
    os.remove(mp)
    assert ach.seed_manifest_baseline() == 2


def test_insert_hypothesis_rejects_blank_text(ach):
    # store.py 184: S3 reject empty/whitespace hypothesis text (add_hypothesis -> _insert_hypothesis).
    ref = ach.create_matrix("c", ["H1"])
    with pytest.raises(ACHError, match="hypothesis text must be non-empty"):
        ach.add_hypothesis(ref.matrix_id, "   ")


def test_rate_cell_rejects_blank_evidence_id(ach):
    # store.py 249: S3 reject a blank/whitespace evidence_id.
    ref = ach.create_matrix("c", ["H1"])
    hid = ref.hypotheses[0].hypothesis_id
    with pytest.raises(ACHError, match="evidence_id must be non-empty"):
        ach.rate_cell(ref.matrix_id, "   ", hid, "C", "weak", "model_draft")


def test_score_counts_weak_inconsistency(ach):
    # store.py 456: the weak (non-strong) inconsistency tally branch. An 'I'/'weak' cell that passes
    # every gate must land in `weak`, not `strong`.
    ref = ach.create_matrix("c", ["H1", "H2"])
    h1, h2 = ref.hypotheses[0].hypothesis_id, ref.hypotheses[1].hypothesis_id
    _rate(ach, ref.matrix_id, "E1", h1, "I", strength="weak")
    _rate(ach, ref.matrix_id, "E1", h2, "C", strength="weak")
    r = ach.score_matrix(ref.matrix_id)
    lead = next(x for x in r.ordered if x.hypothesis_id == h1)
    assert lead.weak_inconsistencies == 1 and lead.strong_inconsistencies == 0
    assert r.leading == h2  # H2 (no inconsistency) beats H1 (one weak I)


def test_list_matrices_pagination(ach):
    # store.py 481-487: the read-back body + the next_cursor pagination path (len(rows) > limit) and
    # its exhausted else (next_cursor None).
    for _ in range(3):
        ach.create_matrix("pg", ["H1"])
    page1 = ach.list_matrices("pg", limit=2)
    assert len(page1.items) == 2 and page1.next_cursor is not None
    page2 = ach.list_matrices("pg", limit=2, cursor=page1.next_cursor)
    assert len(page2.items) == 1 and page2.next_cursor is None


# --------------------------------------------------------------------------- server: _resolve_db


def test_resolve_db_creates_private_dir(tmp_path, monkeypatch):
    # server.py 43-46, 49: a non-":memory:" path is resolved, its parent created, and made 0700.
    target = tmp_path / "nested" / "ach.db"
    monkeypatch.setenv("ACH_COV_DB", str(target))
    result = ach_server._resolve_db("ACH_COV_DB", "unused.db")
    assert result == str(target.resolve())
    assert target.parent.is_dir()
    assert (target.parent.stat().st_mode & 0o777) == 0o700


def test_resolve_db_chmod_failure_is_best_effort(tmp_path, monkeypatch):
    # server.py 47-48: the chmod on the containing dir is best-effort; an OSError is swallowed and the
    # resolved path still returned.
    target = tmp_path / "nested2" / "ach.db"
    monkeypatch.setenv("ACH_COV_DB2", str(target))

    def boom(*args, **kwargs):
        raise OSError("chmod not permitted here")

    monkeypatch.setattr(os, "chmod", boom)
    result = ach_server._resolve_db("ACH_COV_DB2", "unused.db")
    assert result == str(target.resolve())
    assert target.parent.is_dir()


# --------------------------------------------------------------------------- server: main()


def test_main_serves_when_chains_ok(monkeypatch):
    # server.py 274-278, 284, 287: healthy chains -> print "chains OK" and run() on stdio.
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(ach_server.mcp, "run", fake_run)
    ach_server.main()
    assert captured.get("transport") == "stdio"
    assert captured.get("show_banner") is False


def test_main_refuses_when_chain_broken(monkeypatch):
    # server.py 278-283: a failing chain -> print REFUSING TO SERVE and exit(1) before ever serving.
    broken = ChainStatus(
        server="ach-engine",
        scope="all",
        ok=False,
        head_hash={},
        rows_verified=0,
        mismatch=ChainMismatch(
            table="cells", row_id="1", expected_hash="a" * 64, got_hash="b" * 64
        ),
    )
    monkeypatch.setattr(ach_server.store, "verify_chain", lambda: broken)

    def _no_serve(**kwargs):
        raise AssertionError("main() must not serve on a broken chain")

    monkeypatch.setattr(ach_server.mcp, "run", _no_serve)
    with pytest.raises(SystemExit) as ei:
        ach_server.main()
    assert ei.value.code == 1


# --------------------------------------------------------------------------- server: tool bodies (wire)


async def _drive_lifecycle() -> None:
    # confirm the evidence out-of-band so the analyst_confirmed cells + score_matrix gate pass.
    ach_server.staleness.mark_graded("Ecov1", "analyst_confirmed")
    async with Client(ach_server.mcp) as c:
        # create_matrix (server 136)
        r = await c.call_tool("create_matrix", {"case_id": "cov", "hypotheses": ["H1", "H2"]})
        mid = r.data.matrix_id
        h1 = r.data.hypotheses[0].hypothesis_id
        h2 = r.data.hypotheses[1].hypothesis_id
        # add_hypothesis (server 150)
        r2 = await c.call_tool("add_hypothesis", {"matrix_id": mid, "hypothesis": "H3"})
        assert len(r2.data.hypotheses) == 3
        h3 = next(h.hypothesis_id for h in r2.data.hypotheses if h.text == "H3")
        # rate_cell (server 216) — full coverage, all analyst_confirmed
        rc = await c.call_tool(
            "rate_cell",
            {
                "matrix_id": mid,
                "evidence_id": "Ecov1",
                "hypothesis_id": h1,
                "consistency": "I",
                "strength": "weak",
                "judgment_source": "analyst_confirmed",
            },
        )
        assert rc.data.judgment_source == "analyst_confirmed"
        for h in (h2, h3):
            await c.call_tool(
                "rate_cell",
                {
                    "matrix_id": mid,
                    "evidence_id": "Ecov1",
                    "hypothesis_id": h,
                    "consistency": "C",
                    "strength": "weak",
                    "judgment_source": "analyst_confirmed",
                },
            )
        # score_matrix (server 234) — H1 carries the lone (weak) inconsistency, so it never leads
        sc = await c.call_tool("score_matrix", {"matrix_id": mid})
        assert sc.data.leading in (h2, h3)
        # get_matrix (server 244)
        gm = await c.call_tool("get_matrix", {"matrix_id": mid})
        assert gm.data.matrix_id == mid and len(gm.data.cells) == 3
        # list_matrices (server 261)
        lm = await c.call_tool("list_matrices", {"case_id": "cov"})
        assert any(it.matrix_id == mid for it in lm.data.items)
        # verify_chain (server 270)
        vc = await c.call_tool("verify_chain", {})
        assert vc.data.ok is True


async def _drive_error_translation() -> None:
    async with Client(ach_server.mcp) as c:
        # server 105-106: a business-rule ACHError from the store is mapped to a FastMCP ToolError
        # (its message survives mask_error_details=True, unlike an internal exception).
        with pytest.raises(ToolError) as ei:
            await c.call_tool("score_matrix", {"matrix_id": "no-such-matrix"})
        assert "unknown matrix_id" in str(ei.value)


def test_ach_tools_full_lifecycle():
    asyncio.run(_drive_lifecycle())


def test_ach_error_maps_to_toolerror():
    asyncio.run(_drive_error_translation())
