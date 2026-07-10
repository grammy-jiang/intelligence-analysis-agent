"""SSRF guard matrix (design v3 control #3) — deterministic, DNS injected. The reviewer's required cases."""

from __future__ import annotations

import pytest

from mcp_servers.osint_toolkit.egress import EgressError, validate_url


def _resolver(mapping):
    return lambda host: mapping.get(host, [])


# --- scheme + userinfo -----------------------------------------------------
@pytest.mark.parametrize("url", ["http://example.com", "file:///etc/passwd", "gopher://x", "ftp://x"])
def test_scheme_rejected(url):
    with pytest.raises(EgressError, match="scheme"):
        validate_url(url, allowed_hosts={"example.com"})


def test_userinfo_rejected():
    with pytest.raises(EgressError, match="userinfo"):
        validate_url("https://user:pw@example.com", allowed_hosts={"example.com"})


# --- blocked IP literals (metadata, private, loopback, link-local, CGNAT, unspecified) ---
@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1",
        "https://10.0.0.1",
        "https://192.168.1.1",
        "https://172.16.0.1",
        "https://169.254.169.254",  # cloud metadata
        "https://100.64.0.1",  # CGNAT
        "https://0.0.0.0",
        "https://[::1]",
        "https://[fc00::1]",
        "https://[fe80::1]",
    ],
)
def test_blocked_ip_literals(url):
    with pytest.raises(EgressError, match="blocked IP"):
        validate_url(url)


# --- non-canonical / obfuscated numeric literals (blocklist-bypass class) ---
@pytest.mark.parametrize(
    "url",
    [
        "https://2130706433",  # decimal 127.0.0.1
        "https://0x7f000001",  # hex
        "https://017700000001",  # octal-ish
        "https://[::ffff:169.254.169.254]",  # IPv4-mapped IPv6 -> metadata
        "https://127.0.0.01",  # leading zero, non-canonical
    ],
)
def test_noncanonical_literals_rejected(url):
    with pytest.raises(EgressError):
        validate_url(url)


# --- allowlist + DNS rebinding ---------------------------------------------
def test_host_not_in_allowlist():
    with pytest.raises(EgressError, match="allowlist"):
        validate_url("https://evil.com", allowed_hosts={"good.com"}, resolver=_resolver({"evil.com": ["1.2.3.4"]}))


def test_dns_rebinding_to_internal_blocked():
    # a permitted host that resolves to a loopback/internal IP (rebinding) must be refused
    with pytest.raises(EgressError, match="blocked IP"):
        validate_url(
            "https://good.com", allowed_hosts={"good.com"}, resolver=_resolver({"good.com": ["127.0.0.1"]})
        )


def test_no_resolution():
    with pytest.raises(EgressError, match="no DNS"):
        validate_url("https://good.com", allowed_hosts={"good.com"}, resolver=_resolver({}))


# --- the happy path pins the validated public IP ---------------------------
def test_valid_public_host_pins_ip():
    host, ip = validate_url(
        "https://good.com/path?q=1", allowed_hosts={"good.com"}, resolver=_resolver({"good.com": ["93.184.216.34"]})
    )
    assert host == "good.com" and ip == "93.184.216.34"


def test_valid_public_ip_literal():
    host, ip = validate_url("https://93.184.216.34")
    assert ip == "93.184.216.34"
