#!/usr/bin/env python3
"""Egress-isolation check — the data servers must stay network-free (Phase-4 control #1).

`osint-toolkit` is the **sole** external-egress surface. The three MCP *data* servers —
calibration-tracker, evidence-ledger, ach-engine — and their shared helpers
(``common.py``, ``staleness.py``) must never do their own networking. This static check
parses each data-server module with ``ast`` and fails if it directly imports a
network-capable module. ``osint-toolkit`` is deliberately exempt.

It is the direct-import guard the design specifies as a CI gate: it catches the realistic
regression — a change adding ``import requests`` / ``import socket`` to a data server. It
does not trace transitive third-party dependency graphs; the runtime network sandbox
(design control #1) is the backstop for those.

Usage::

    python scripts/check_egress_isolation.py

Exit status is non-zero if any data-server module imports a network module.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# Data servers + shared helpers that MUST stay network-free.
# osint-toolkit (the sole egress surface) is intentionally NOT listed.
DATA_SERVER_ROOTS = (
    "mcp_servers/calibration_tracker",
    "mcp_servers/evidence_ledger",
    "mcp_servers/ach_engine",
    "mcp_servers/common.py",
    "mcp_servers/staleness.py",
)

# Top-level module names that imply the code can open a network connection.
NETWORK_MODULES = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "ftplib",
        "smtplib",
        "telnetlib",
        "poplib",
        "imaplib",
        "nntplib",
        "asyncore",
        "asynchat",
        "xmlrpc",
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "websockets",
        "websocket",
        "pycurl",
        "grpc",
        "paramiko",
    }
)


def _iter_py_files(roots: tuple[str, ...]):
    for root in roots:
        p = Path(root)
        if p.is_dir():
            yield from sorted(p.rglob("*.py"))
        elif p.is_file():
            yield p


def network_imports(path: Path):
    """Yield ``(lineno, module)`` for every direct network import in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in NETWORK_MODULES:
                    yield node.lineno, alias.name
        # `from x import ...`; level > 0 is a relative (internal) import — never network.
        elif (
            isinstance(node, ast.ImportFrom)
            and node.level == 0
            and node.module
            and node.module.split(".")[0] in NETWORK_MODULES
        ):
            yield node.lineno, node.module


def main() -> int:
    violations = [
        (path, lineno, module)
        for path in _iter_py_files(DATA_SERVER_ROOTS)
        for lineno, module in network_imports(path)
    ]
    if violations:
        print("egress isolation FAILED — a data server imports a network module:", file=sys.stderr)
        for path, lineno, module in violations:
            print(f"  {path}:{lineno}: imports {module!r}", file=sys.stderr)
        print(
            "\nThe data servers must stay network-free — osint-toolkit is the sole egress "
            "surface. Route egress through osint-toolkit, or (only if this module truly joins "
            "the egress surface) move it out of the data-server set.",
            file=sys.stderr,
        )
        return 1
    print(
        f"egress isolation OK — no network imports in {len(DATA_SERVER_ROOTS)} data-server roots."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
