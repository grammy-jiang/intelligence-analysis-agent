"""Unit tests for osint-toolkit modules: opaque-token artifacts (control #12) + egress audit (control #10)."""

from __future__ import annotations

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
