"""The shared egress guard — the single security-critical SSRF chokepoint (design v3 control #3).

Every outbound call validates here. Deterministic-testable: DNS resolution is injected (`resolver`) so the
SSRF matrix (blocked ranges, canonicalization, DNS-rebinding) is exercised without real network. The live
`fetch` (not here) resolves once, opens a socket to the returned pinned IP, and layers TLS over it — never
re-resolving by hostname (anti-rebinding).
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit

Resolver = Callable[[str], list[str]]

# Extra blocked ranges beyond ipaddress's is_private/is_loopback/is_link_local/is_reserved/is_multicast.
_EXTRA_BLOCKED = [ipaddress.ip_network(c) for c in ("0.0.0.0/8", "100.64.0.0/10")]


class EgressError(Exception):
    """A URL failed the egress guard; the caller surfaces it as a ToolError (fail-closed)."""


def _ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # includes 169.254.0.0/16 (cloud metadata 169.254.169.254)
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _ip_blocked(ip.ipv4_mapped)  # ::ffff:a.b.c.d
    return any(ip.version == net.version and ip in net for net in _EXTRA_BLOCKED)


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Return the IP if `host` is a CANONICAL IP literal; raise on a non-canonical numeric literal
    (decimal/octal/hex — the classic blocklist-bypass forms); return None for a real domain name."""
    h = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # Not a valid IP string. Reject anything that is trying to be a numeric literal (all-digits, dotted
        # all-digits, or 0x/0-prefixed) — parse-don't-normalize (control #3).
        stripped = h.replace(".", "")
        if stripped.isdigit() or h.lower().startswith("0x"):
            raise EgressError(f"non-canonical IP literal rejected: {host}") from None
        return None
    if str(ip) != h:  # e.g. leading zeros / non-canonical form that ip_address happened to accept
        raise EgressError(f"non-canonical IP literal rejected: {host}") from None
    return ip


def _default_resolver(host: str) -> list[str]:
    try:
        return list({str(info[4][0]) for info in socket.getaddrinfo(host, None)})
    except (socket.gaierror, UnicodeError, OSError):
        # S10: gaierror is the common case, but an IDNA-invalid host raises UnicodeError and other name-service
        # failures raise plain OSError; all must resolve to "no IPs" (→ fail-closed EgressError) rather than
        # escape the EgressError taxonomy the caller converts to a ToolError.
        return []


MAX_FETCH_BYTES = 25 * 1024 * 1024
_REDIRECT_CODES = {301, 302, 303, 307, 308}
# opener(host, pinned_ip, url) -> (status:int, headers:dict[str,str], body:bytes). Injectable for tests.
Opener = "Callable[[str, str, str], tuple[int, dict, bytes]]"


def validate_url(
    url: str, allowed_hosts: set[str] | None = None, resolver: Resolver = _default_resolver
) -> tuple[str, str]:
    """Validate a URL for egress; return (hostname, pinned_ip) or raise EgressError. Re-applied by the caller
    to the initial URL AND to every redirect hop (control #3)."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise EgressError(f"scheme not allowed (https only): {parts.scheme or '(none)'}")
    if parts.username or parts.password:
        raise EgressError("userinfo in URL not allowed (host-confusion defense)")
    host = parts.hostname
    if not host:
        raise EgressError("no host in URL")

    # MF3: factor the port into the egress decision. urlsplit parses `port` lazily and raises ValueError on a
    # malformed value; a nonstandard port often fronts an internal service reachable even on a public IP, so
    # fail closed to 443 only rather than let the live fetcher silently substitute 443 for a different endpoint.
    try:
        port = parts.port
    except ValueError:
        raise EgressError("invalid port in URL") from None
    if port is not None and port != 443:
        raise EgressError(f"port not allowed (https/443 only): {port}")

    literal = _parse_ip_literal(host)
    if literal is not None:
        if _ip_blocked(literal):
            raise EgressError(f"blocked IP literal: {literal}")
        return host, str(literal)

    if allowed_hosts is not None and host.lower() not in allowed_hosts:
        raise EgressError(f"host not in connector allowlist: {host}")

    ips = resolver(host)
    if not ips:
        raise EgressError(f"no DNS resolution for {host}")
    pinned: str | None = None
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if _ip_blocked(ip):
            raise EgressError(
                f"host {host} resolves to blocked IP {ip} (rebinding / internal target)"
            )
        pinned = pinned or ip_str
    assert pinned is not None  # noqa: S101 - invariant: ips is non-empty by caller contract (post-resolution)
    return host, pinned


def _resolve_redirect(base: str, location: str) -> str:
    return urljoin(base, location)


def _pinned_https_get(host: str, ip: str, url: str) -> tuple[int, dict, bytes]:
    """Real fetch: connect to the validated pinned IP, TLS with SNI=host (cert validated against host), GET —
    never re-resolving the hostname (anti-rebinding). Used only behind OSINT_LIVE against a real host."""
    parts = urlsplit(url)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    port = (
        parts.port or 443
    )  # MF3: honor the validated port (validate_url has already restricted it to 443)
    ctx = ssl.create_default_context()
    raw_sock = socket.create_connection((ip, port), timeout=15)
    # M4: wrap_socket runs BEFORE the try/finally below. A handshake failure (bad cert / timeout — routine for
    # an SSRF-hardened fetcher probing hostile hosts) would otherwise leak raw_sock's fd, since `tls` never
    # binds and the finally's tls.close() never runs. Close the underlying socket on any wrap failure.
    try:
        tls = ctx.wrap_socket(raw_sock, server_hostname=host)
    except BaseException:
        raw_sock.close()
        raise
    try:
        conn = http.client.HTTPSConnection(host, timeout=15)
        conn.sock = tls  # reuse the pre-connected, pinned, cert-validated socket (no re-resolve)
        conn.request(
            "GET",
            path,
            headers={"Host": host, "Connection": "close", "User-Agent": "osint-toolkit"},
        )
        resp = conn.getresponse()
        body = resp.read(MAX_FETCH_BYTES + 1)
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, body
    finally:
        tls.close()


def fetch_pinned(
    url, *, max_bytes=MAX_FETCH_BYTES, max_redirects=5, opener=None, resolver=_default_resolver
):
    """Fetch through the guard, re-validating scheme + IP on EVERY redirect hop (control #3). Returns
    (final_url, body, content_type). `opener(host, ip, url)` is injectable for tests; default = pinned-TLS GET."""
    opener = opener or _pinned_https_get
    cur, hops = url, 0
    while True:
        host, ip = validate_url(cur, resolver=resolver)  # per-hop re-validation (scheme + IP-block)
        status, headers, body = opener(host, ip, cur)
        if status in _REDIRECT_CODES and headers.get("location"):
            hops += 1
            if hops > max_redirects:
                raise EgressError("too many redirects")
            cur = _resolve_redirect(cur, headers["location"])
            continue
        if len(body) > max_bytes:
            raise EgressError("response exceeds size cap")
        return cur, body, headers.get("content-type")
