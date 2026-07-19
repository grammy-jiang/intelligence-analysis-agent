"""Direct unit tests for the shared hash-chain manifest helper (`mcp_servers.common.Manifest`) and the
edge/error branches of `mcp_servers.staleness.StalenessStore`.

These target coverage the cross-server integration test (test_cross_server_staleness.py) leaves open:

common.Manifest
  - check(): the in-memory vacuous pass, and the missing-file-but-empty-store legitimate pass.
  - _read_state() / check(): tolerance of blank lines in the manifest file.
  - seed(): the trust-on-first-use migration — no-op (pathless / manifest already present) vs. write path.

staleness.StalenessStore
  - the best-effort 0600 hardening swallowing an os.chmod OSError.
  - the _head() unknown-table guard (an explicit ValueError, not a stripped assert).
  - seed_manifest_baseline(): in-memory no-op, existing-manifest no-op, and a real predating-DB migration.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_servers.common import GENESIS, Manifest
from mcp_servers.staleness import StalenessStore

_TABLES = ("stale_events", "grade_signals")


# --------------------------------------------------------------------------- #
# common.Manifest.check() — the two vacuous / legitimate passes
# --------------------------------------------------------------------------- #
def test_manifest_in_memory_check_is_vacuous_pass():
    """A pathless (in-memory) manifest attests nothing, so check() passes without touching the disk."""
    m = Manifest(None, _TABLES)
    ok, mm = m.check({"stale_events": "de" * 32}, {"stale_events": 1})
    assert ok is True and mm is None


def test_manifest_missing_file_empty_store_passes(tmp_path):
    """No manifest file yet AND every table still at GENESIS (a fresh, empty store) is a legitimate pass
    — not a fail-closed. Only a non-GENESIS table with no manifest is treated as tampering."""
    m = Manifest(str(tmp_path / "absent.manifest.jsonl"), _TABLES)
    ok, mm = m.check(dict.fromkeys(_TABLES, GENESIS), dict.fromkeys(_TABLES, 0))
    assert ok is True and mm is None


def test_manifest_missing_file_nonempty_fails_closed(tmp_path):
    """A non-GENESIS table with no manifest file at all means the file was lost/deleted — fail closed."""
    m = Manifest(str(tmp_path / "absent.manifest.jsonl"), _TABLES)
    ok, mm = m.check({"stale_events": "de" * 32, "grade_signals": GENESIS}, {"stale_events": 1})
    assert ok is False
    assert mm is not None and mm.row_id == "<manifest-missing>"


# --------------------------------------------------------------------------- #
# common.Manifest — blank lines are tolerated on both read paths
# --------------------------------------------------------------------------- #
def test_manifest_tolerates_blank_lines(tmp_path):
    """A blank line in the manifest file must be skipped by BOTH _read_state (on construction) and check
    (during verification) without corrupting the recovered head/counts or the self-chain walk."""
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db)
    try:
        st.mark_stale("E1", "grade")
        st.mark_graded("E1", "analyst_confirmed")
        assert st.verify_chain().ok is True
    finally:
        st.close()

    mp = Path(db + ".manifest.jsonl")
    lines = [ln for ln in mp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 2  # two appends -> two manifest entries to sandwich a blank line between
    # Inject an INTERIOR blank line so the for-loop actually iterates it (not merely a trailing newline).
    mp.write_text(lines[0] + "\n\n" + "\n".join(lines[1:]) + "\n", encoding="utf-8")

    # _read_state must skip the blank line and still recover the true tail head + per-table counts.
    m = Manifest(str(mp), _TABLES)
    assert m._head != GENESIS
    assert m._counts.get("stale_events") == 1 and m._counts.get("grade_signals") == 1

    # check() (via verify_chain on a freshly reopened store) must likewise skip it and still reconcile.
    st2 = StalenessStore(db)
    try:
        assert st2.verify_chain().ok is True
    finally:
        st2.close()


# --------------------------------------------------------------------------- #
# common.Manifest.seed() — trust-on-first-use migration
# --------------------------------------------------------------------------- #
def test_manifest_seed_pathless_is_noop():
    """seed() on a pathless (in-memory) manifest writes nothing and reports zero entries."""
    m = Manifest(None, _TABLES)
    assert m.seed({"stale_events": "de" * 32}, {"stale_events": 1}) == 0


def test_manifest_seed_writes_then_is_idempotent(tmp_path):
    """seed() attests each non-GENESIS table exactly once (skipping still-GENESIS tables), creates the
    file, and is a no-op on any later call because the manifest now exists (trust-on-first-use)."""
    mp = str(tmp_path / "seed.manifest.jsonl")
    heads = {"stale_events": "ab" * 32, "grade_signals": GENESIS}  # one attested, one still empty
    counts = {"stale_events": 3, "grade_signals": 0}

    written = Manifest(mp, _TABLES).seed(heads, counts)
    assert written == 1  # only the non-GENESIS table is attested
    assert os.path.exists(mp)

    # A second manifest instance sees the existing file, so seeding is a no-op.
    assert Manifest(mp, _TABLES).seed(heads, counts) == 0


# --------------------------------------------------------------------------- #
# staleness.StalenessStore — construction hardening + guards
# --------------------------------------------------------------------------- #
def test_chmod_failure_is_swallowed(tmp_path, monkeypatch):
    """The 0600 hardening of the DB + WAL sidecars is best-effort: an OSError from os.chmod must be
    swallowed so the store still opens (a read-only or exotic filesystem must not brick startup)."""

    def boom(*_a, **_k):
        raise OSError("chmod not permitted")

    monkeypatch.setattr(os, "chmod", boom)
    st = StalenessStore(str(tmp_path / "stale.db"))  # must construct despite every chmod raising
    try:
        assert st.verify_chain().ok is True
    finally:
        st.close()


def test_head_rejects_unknown_table(tmp_path):
    """_head() guards against a non-whitelisted table name with an explicit ValueError (not an assert,
    which -O / PYTHONOPTIMIZE would strip, re-opening the f-string SQL-identifier interpolation)."""
    st = StalenessStore(str(tmp_path / "stale.db"))
    try:
        with pytest.raises(ValueError, match="unknown table"):
            st._head("bobby_tables")
    finally:
        st.close()


# --------------------------------------------------------------------------- #
# staleness.StalenessStore.seed_manifest_baseline()
# --------------------------------------------------------------------------- #
def test_seed_manifest_baseline_in_memory_is_noop():
    """An in-memory store has no manifest path, so baseline seeding attests nothing."""
    st = StalenessStore(":memory:")
    try:
        assert st.seed_manifest_baseline() == 0
    finally:
        st.close()


def test_seed_manifest_baseline_noop_when_manifest_exists(tmp_path):
    """Once normal writes have created the manifest, baseline seeding is a trust-on-first-use no-op."""
    st = StalenessStore(str(tmp_path / "stale.db"))
    try:
        st.mark_graded("E1", "analyst_confirmed")  # first append creates the manifest file
        assert os.path.exists(st.manifest_path)
        assert st.seed_manifest_baseline() == 0
    finally:
        st.close()


def test_seed_manifest_baseline_migrates_predating_db(tmp_path):
    """A DB predating the manifest (simulated: write rows, delete the manifest, reopen) is migrated on
    startup — baseline seeding attests one entry per non-empty table starting from GENESIS, and the
    reopened store then verifies against the freshly seeded manifest."""
    db = str(tmp_path / "stale.db")
    st = StalenessStore(db)
    try:
        st.mark_stale("E1", "grade")
        st.mark_graded("E1", "analyst_confirmed")
    finally:
        st.close()

    os.remove(db + ".manifest.jsonl")  # simulate a DB written before the manifest anchor existed

    st2 = StalenessStore(
        db
    )  # fresh open: its manifest sees no file -> seeds the chain from GENESIS
    try:
        written = st2.seed_manifest_baseline()
        assert written == 2  # both stale_events and grade_signals carry a non-GENESIS head
        assert os.path.exists(db + ".manifest.jsonl")
        assert st2.verify_chain().ok is True  # the seeded manifest reconciles with the live rows
    finally:
        st2.close()
