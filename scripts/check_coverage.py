#!/usr/bin/env python3
"""Per-module coverage gate — core modules >= 95%, others >= 90% (not just the average).

Reads a coverage.py JSON report (`pytest --cov-report=json` / `coverage json`) and fails if
any measured ``mcp_servers`` module falls below its floor. This complements the global
``fail_under`` in pyproject: it enforces the floor *per file*, so a well-covered module can
never mask a thin one.

Core = the durable state / integrity / security logic (must clear the higher bar). Everything
else measured — the FastMCP tool wrappers and the OSINT IO helpers — must clear the lower bar.

Usage::

    pytest --cov=mcp_servers --cov-report=json    # writes coverage.json
    python scripts/check_coverage.py [coverage.json]

Exit status is non-zero if any module is below its floor.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CORE_MIN = 95.0
OTHER_MIN = 90.0

# Core modules — the higher bar. Everything else measured gets OTHER_MIN.
CORE = frozenset(
    {
        "mcp_servers/common.py",
        "mcp_servers/staleness.py",
        "mcp_servers/ach_engine/store.py",
        "mcp_servers/ach_engine/models.py",
        "mcp_servers/calibration_tracker/store.py",
        "mcp_servers/calibration_tracker/models.py",
        "mcp_servers/evidence_ledger/store.py",
        "mcp_servers/evidence_ledger/models.py",
        "mcp_servers/osint_toolkit/egress.py",
        "mcp_servers/osint_toolkit/models.py",
    }
)


def main(argv: list[str]) -> int:
    report = Path(argv[0]) if argv else Path("coverage.json")
    try:
        data = json.loads(report.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read coverage report {report}: {exc}", file=sys.stderr)
        return 2

    rows, failures = [], []
    for name, fdata in sorted(data.get("files", {}).items()):
        path = name.replace("\\", "/")
        n = fdata["summary"]["num_statements"]
        if n == 0:  # trivial (e.g. __init__.py) — nothing to measure
            continue
        pct = fdata["summary"]["percent_covered"]
        floor = CORE_MIN if path in CORE else OTHER_MIN
        tier = "core " if path in CORE else "other"
        ok = pct + 1e-9 >= floor
        rows.append((ok, pct, floor, tier, path))
        if not ok:
            failures.append((path, tier.strip(), pct, floor))

    for ok, pct, floor, tier, path in rows:
        print(f"{'ok ' if ok else 'LOW'} {pct:5.1f}%  (>= {floor:.0f}% {tier})  {path}")

    if failures:
        print(f"\ncoverage gate FAILED — {len(failures)} module(s) below floor:", file=sys.stderr)
        for path, tier, pct, floor in failures:
            print(f"  {path}: {pct:.1f}% < {floor:.0f}% ({tier})", file=sys.stderr)
        return 1

    print(
        f"\ncoverage gate OK — all {len(rows)} modules meet their floor "
        f"(core >= {CORE_MIN:.0f}%, other >= {OTHER_MIN:.0f}%)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
