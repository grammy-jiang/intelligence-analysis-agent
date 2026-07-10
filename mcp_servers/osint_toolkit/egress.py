"""The shared egress guard — the single security-critical SSRF chokepoint (design v3 control #3).

Every outbound call validates here. Deterministic-testable: DNS resolution is injected (`resolver`) so the
SSRF matrix (blocked ranges, canonicalization, DNS-rebinding) is exercised without real network. The live
`fetch` (not here) resolves once, opens a socket to the returned pinned IP, and layers TLS over it — never
re-resolving by hostname (anti-rebinding).
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

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
        return list({info[4][0] for info in socket.getaddrinfo(host, None)})
    except socket.gaierror:
        return []


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
            raise EgressError(f"host {host} resolves to blocked IP {ip} (rebinding / internal target)")
        pinned = pinned or ip_str
    assert pinned is not None
    return host, pinned
