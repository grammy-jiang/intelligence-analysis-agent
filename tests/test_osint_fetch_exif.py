"""EXIF parsing (Pillow, memory-safe) + fetch redirect re-validation (injected opener, no real egress)."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from mcp_servers.osint_toolkit.egress import EgressError, fetch_pinned
from mcp_servers.osint_toolkit.exif import dms_to_decimal, parse_exif


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (120, 30, 200)).save(buf, "JPEG")
    return buf.getvalue()


# --- EXIF -----------------------------------------------------------------
def test_dms_to_decimal():
    assert dms_to_decimal((51, 30, 0), "N") == pytest.approx(51.5)
    assert dms_to_decimal((0, 7, 30), "W") == pytest.approx(-0.125)


def test_parse_exif_clean_jpeg():
    assert parse_exif(_jpeg()) == {}  # no EXIF, no crash


def test_parse_exif_adversarial_never_raises():
    assert parse_exif(b"not an image") == {}
    assert parse_exif(b"\xff\xd8\xff broken jpeg bytes") == {}
    assert parse_exif(b"") == {}


# --- fetch redirect re-validation (the security-critical hop check) --------
def _resolver(mapping):
    return lambda host: mapping.get(host, [])


PUBLIC = {"good.com": ["93.184.216.34"]}


def test_fetch_happy_path():
    def opener(host, ip, url):
        assert ip == "93.184.216.34"  # connects to the pinned IP, not a re-resolve
        return 200, {"content-type": "text/html"}, b"<html>ok</html>"

    final, body, ct = fetch_pinned("https://good.com/x", opener=opener, resolver=_resolver(PUBLIC))
    assert body == b"<html>ok</html>" and ct == "text/html"


def test_fetch_redirect_to_blocked_ip_refused():
    # a 302 to a metadata IP must be refused on the NEXT hop's re-validation
    def opener(host, ip, url):
        return 302, {"location": "https://169.254.169.254/latest/meta-data"}, b""

    with pytest.raises(EgressError, match="blocked IP"):
        fetch_pinned("https://good.com/x", opener=opener, resolver=_resolver(PUBLIC))


def test_fetch_redirect_to_scheme_downgrade_refused():
    def opener(host, ip, url):
        return 302, {"location": "file:///etc/passwd"}, b""

    with pytest.raises(EgressError, match="scheme"):
        fetch_pinned("https://good.com/x", opener=opener, resolver=_resolver(PUBLIC))


def test_fetch_too_many_redirects():
    def opener(host, ip, url):
        return 302, {"location": "https://good.com/loop"}, b""

    with pytest.raises(EgressError, match="too many redirects"):
        fetch_pinned("https://good.com/x", opener=opener, resolver=_resolver(PUBLIC), max_redirects=3)


def test_fetch_size_cap():
    def opener(host, ip, url):
        return 200, {}, b"x" * 100

    with pytest.raises(EgressError, match="size cap"):
        fetch_pinned("https://good.com/x", opener=opener, resolver=_resolver(PUBLIC), max_bytes=10)
