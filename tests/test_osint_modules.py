"""Unit tests for osint-toolkit modules: opaque-token artifacts (control #12) + egress audit (control #10)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from mcp_servers.osint_toolkit.artifacts import ArtifactError, ArtifactStore
from mcp_servers.osint_toolkit.audit import EgressAudit

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32


def test_artifact_put_read_hash_type(tmp_path):
    s = ArtifactStore(str(tmp_path / "art"))
    tok = s.put(JPEG)
    assert tok.startswith("art_")
    assert s.read(tok) == JPEG
    assert len(s.compute_hash(tok)) == 64
    assert s.detect_type(tok) == "image/jpeg"


def test_artifact_rejects_non_token_and_traversal(tmp_path):
    s = ArtifactStore(str(tmp_path / "art"))
    for bad in ["../../etc/passwd", "/etc/passwd", "art_notlongenough", "evil", "art_" + "g" * 32]:
        with pytest.raises(ArtifactError, match="invalid artifact_ref"):
            s.read(bad)


def test_artifact_unknown_token(tmp_path):
    s = ArtifactStore(str(tmp_path / "art"))
    with pytest.raises(ArtifactError, match="unknown artifact_ref"):
        s.read("art_" + "0" * 32)


def test_audit_allowlist_and_chain(tmp_path):
    a = EgressAudit(str(tmp_path / "audit.db"))
    try:
        # `query` is deliberately not loggable for search; connector is. Pass both; only connector persists.
        a.record("search", {"connector": "web", "query": "SENSITIVE case id", "max_results": 20}, "-", "attempt")
        a.record("fetch", {"host": "example.com", "url": "https://example.com/secret?key=abc"}, "1.2.3.4", "ok")
        assert a.count() == 2
        assert a.verify_chain().ok is True
        # confirm the secret-bearing fields never hit the row
        raw = sqlite3.connect(str(tmp_path / "audit.db"))
        rows = "".join(r[0] for r in raw.execute("SELECT fields FROM egress_log"))
        raw.close()
        assert "SENSITIVE" not in rows and "secret?key" not in rows and "query" not in rows and "url" not in rows
    finally:
        a.close()


def test_audit_chain_detects_tamper(tmp_path):
    a = EgressAudit(str(tmp_path / "audit.db"))
    try:
        a.record("fetch", {"host": "example.com"}, "1.2.3.4", "ok")
        raw = sqlite3.connect(str(tmp_path / "audit.db"))
        raw.execute("UPDATE egress_log SET resolved_ip='9.9.9.9'")
        raw.commit()
        raw.close()
        assert a.verify_chain().ok is False
    finally:
        a.close()


def test_audit_detects_tail_truncation(tmp_path):
    # MF3: deleting trailing audit rows (e.g. erasing an attempt->ok egress pair to hide an event) leaves a
    # self-consistent SHORTER chain — a forward-only re-derivation would still report ok. The external manifest
    # anchor (attested head + row count) must catch it.
    a = EgressAudit(str(tmp_path / "audit.db"))
    try:
        a.record("fetch", {"host": "a.com"}, "1.1.1.1", "attempt (live)")
        a.record("fetch", {"host": "a.com"}, "1.1.1.1", "ok")
        assert a.verify_chain().ok is True
        raw = sqlite3.connect(str(tmp_path / "audit.db"))
        raw.execute("DELETE FROM egress_log WHERE seq=(SELECT MAX(seq) FROM egress_log)")
        raw.commit()
        raw.close()
        st = a.verify_chain()
        assert st.ok is False and st.mismatch is not None and st.mismatch.table == "egress_log"
    finally:
        a.close()


def test_audit_missing_manifest_fails_closed(tmp_path):
    # MF3: with the DB rows surviving but the manifest deleted, verify must NOT pass vacuously.
    a = EgressAudit(str(tmp_path / "audit.db"))
    try:
        a.record("fetch", {"host": "a.com"}, "1.1.1.1", "ok")
        assert a.verify_chain().ok is True
        import os

        os.remove(str(tmp_path / "audit.db.manifest.jsonl"))
        assert a.verify_chain().ok is False
    finally:
        a.close()


def test_audit_manifest_middle_line_edit_detected(tmp_path):
    # review item #7: the egress manifest is now SELF-CHAINED (prev_manifest_hash / manifest_hash) so editing a
    # NON-TERMINAL line is detected. The prior head+count anchor only checked the LAST line's head + the total
    # count, so an edit to a middle line (head unchanged for the tail, count unchanged) slipped through.
    a = EgressAudit(str(tmp_path / "audit.db"))
    try:
        for i in range(3):
            a.record("fetch", {"host": f"h{i}.com"}, "1.1.1.1", "ok")
        assert a.verify_chain().ok is True
        mp = str(tmp_path / "audit.db.manifest.jsonl")
        with open(mp, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        assert len(lines) >= 3  # a genuine middle line exists
        e = json.loads(lines[1])  # a MIDDLE line — neither the tail head nor the total count changes
        e["head"] = "0" * 64
        lines[1] = json.dumps(e)
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        st = a.verify_chain()
        assert st.ok is False and st.mismatch is not None and st.mismatch.table == "egress_log"
    finally:
        a.close()
