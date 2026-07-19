"""Extra branch coverage for the OSINT egress guard (SSRF chokepoint) and EXIF GPS extraction.

Targets the error/edge branches that the existing suites leave uncovered:

  egress.py  — the IPv4-mapped-IPv6 recursion, non-canonical IPv6 literal rejection, empty-authority
               and malformed-port guards in ``validate_url``, plus the real pinned-TLS GET body path in
               ``_pinned_https_get`` (query append + success read + finally-close).
  exif.py    — the GPSInfo -> gps_lat/gps_lon decimal path, the scalar-tag ``elif`` branch, and the
               adversarial-GPS ``except`` branch.

All deterministic: the raw socket, the TLS handshake, and ``http.client.HTTPSConnection`` are faked, so no
real network is touched. IP literals and malformed URLs are validated without DNS.
"""

from __future__ import annotations

import io
import ssl

import pytest
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from mcp_servers.osint_toolkit import egress as eg
from mcp_servers.osint_toolkit.egress import EgressError, validate_url
from mcp_servers.osint_toolkit.exif import parse_exif

# =========================================================================
# egress.validate_url — canonicalization / host / port branches
# =========================================================================


def test_ipv4_mapped_ipv6_public_is_unwrapped_and_allowed():
    # egress.py:38-39 — an IPv4-mapped IPv6 literal whose is_private/is_loopback/... flags are all False
    # reaches the `ip.ipv4_mapped is not None` recursion; ::ffff:8.8.8.8 unwraps to public 8.8.8.8 -> allowed.
    # (The blocked-mapped cases like ::ffff:169.254.169.254 short-circuit on is_private and never reach it.)
    host, ip = validate_url("https://[::ffff:8.8.8.8]")
    assert host == "::ffff:8.8.8.8"
    assert ip == "::ffff:8.8.8.8"


@pytest.mark.parametrize(
    "url",
    [
        "https://[0::1]",  # ip_address accepts it but canonicalizes to ::1
        "https://[2001:db8:0:0:0:0:0:1]",  # -> 2001:db8::1
    ],
)
def test_noncanonical_ipv6_literal_rejected(url):
    # egress.py:57 — ip_address ACCEPTS the string, but str(ip) != host (non-canonical expanded form),
    # which is the parse-don't-normalize rejection distinct from the all-digits/0x path at line 54.
    with pytest.raises(EgressError, match="non-canonical IP literal"):
        validate_url(url)


def test_no_host_in_url_rejected():
    # egress.py:88-89 — https scheme but an empty authority (triple slash) yields hostname == None.
    with pytest.raises(EgressError, match="no host in URL"):
        validate_url("https:///path/only")


@pytest.mark.parametrize("url", ["https://good.com:99999", "https://good.com:notaport"])
def test_invalid_port_rejected(url):
    # egress.py:96-97 — urlsplit resolves .port lazily and raises ValueError on an out-of-range or
    # non-numeric value; the guard converts that to a fail-closed EgressError (never a raw ValueError).
    with pytest.raises(EgressError, match="invalid port in URL"):
        validate_url(url)


# =========================================================================
# egress._pinned_https_get — the real pinned-TLS GET body path (no network)
# =========================================================================


def test_pinned_get_success_body_path(monkeypatch):
    # egress.py:135 (query append) + 149-161 (HTTPSConnection over the pinned TLS socket, read, finally-close).
    # Fake every I/O layer: create_connection -> dummy socket, wrap_socket -> fake TLS, HTTPSConnection -> fake.
    captured: dict[str, object] = {}

    class FakeTLS:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    fake_tls = FakeTLS()

    class FakeResp:
        status = 206

        def read(self, n):
            captured["read_n"] = n
            return b"pinned-body-bytes"

        def getheaders(self):
            return [("Content-Type", "text/html; charset=utf-8"), ("X-Extra", "v")]

    class FakeConn:
        def __init__(self, host, timeout=None):
            captured["conn_host"] = host
            self.sock = None

        def request(self, method, path, headers=None):
            captured["method"] = method
            captured["path"] = path
            captured["headers"] = headers

        def getresponse(self):
            return FakeResp()

    monkeypatch.setattr(eg.socket, "create_connection", lambda *a, **k: object())
    monkeypatch.setattr(
        ssl.SSLContext, "wrap_socket", lambda self, sock, server_hostname=None: fake_tls
    )
    monkeypatch.setattr(eg.http.client, "HTTPSConnection", FakeConn)

    status, headers, body = eg._pinned_https_get(
        "good.com", "93.184.216.34", "https://good.com/p?a=1&b=2"
    )

    assert status == 206
    assert body == b"pinned-body-bytes"
    # egress.py:159 lower-cases header keys
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert headers["x-extra"] == "v"
    # egress.py:135 appended the query string onto the path
    assert captured["path"] == "/p?a=1&b=2"
    assert captured["method"] == "GET"
    assert captured["conn_host"] == "good.com"
    # egress.py:158 reads one byte past the cap so the caller can detect an over-cap body
    assert captured["read_n"] == eg.MAX_FETCH_BYTES + 1
    # egress.py:161 finally-block released the pinned TLS socket
    assert fake_tls.closed is True


# =========================================================================
# exif.parse_exif — GPS extraction + adversarial-GPS branch
# =========================================================================


def _r(n, d=1):
    return IFDRational(n, d)


def _jpeg_with_exif(gps_ifd, extra=None):
    """Build an in-memory JPEG carrying a GPSInfo IFD (and optional top-level tags)."""
    img = Image.new("RGB", (16, 16), (10, 20, 30))
    exif = img.getexif()
    for tag, value in (extra or {}).items():
        exif[tag] = value
    exif[0x8825] = gps_ifd  # GPSInfo IFD tag
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def test_parse_exif_extracts_gps_and_scalar_tags():
    # exif.py:34-56 — GPSInfo dict -> gps_lat/gps_lon (rounded decimals, signed by the N/S/E/W ref),
    # plus the elif branch (39-40) that emits scalar str/int tags.
    data = _jpeg_with_exif(
        {
            1: "N",
            2: (_r(51), _r(30), _r(0)),  # 51 deg 30' 00" N -> 51.5
            3: "W",
            4: (_r(0), _r(7), _r(30)),  # 0 deg 07' 30" W -> -0.125
        },
        extra={0x0131: "unit-test-software", 0x0112: 1},  # Software (str), Orientation (int)
    )
    out = parse_exif(data)
    assert out["gps_lat"] == "51.5"
    assert out["gps_lon"] == "-0.125"
    assert out["Software"] == "unit-test-software"
    assert out["Orientation"] == "1"


def test_parse_exif_malformed_gps_hits_except_branch():
    # exif.py:57-58 — GPSLatitude is present/truthy but has only 2 of 3 DMS components, so dms_to_decimal
    # raises on the tuple unpack; the bare except swallows it and no gps_* key is emitted (never crashes).
    data = _jpeg_with_exif(
        {
            1: "N",
            2: (_r(51), _r(30)),  # malformed: missing the seconds component
            3: "W",
            4: (_r(0), _r(7), _r(30)),
        }
    )
    out = parse_exif(data)
    assert "gps_lat" not in out
    assert "gps_lon" not in out
    assert isinstance(out, dict)  # returned normally, did not raise
