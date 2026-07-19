#!/usr/bin/env python3
"""Compile every ```mermaid block in the given Markdown files with the real Mermaid compiler.

This does NOT re-implement Mermaid parsing — it shells out to mermaid-cli
(``@mermaid-js/mermaid-cli``, the ``mmdc`` binary), which parses and renders each
diagram through Mermaid itself. A file passes only if every mermaid block compiles;
``mmdc`` exits non-zero on the first diagram that fails to parse.

``mmdc`` is located via ``$MMDC``, then ``PATH``, then ``npx --yes @mermaid-js/mermaid-cli``.
It drives headless Chromium through Puppeteer, so the diagrams are validated exactly as
they render. ``--no-sandbox`` is passed (required as root / in CI) and
``$PUPPETEER_EXECUTABLE_PATH`` is honored when a browser is provided out of band.

Usage::

    check_mermaid.py FILE [FILE ...]

Exit status is non-zero if any diagram fails to compile, or if ``mmdc`` cannot be run at
all (the check fails loud rather than skipping silently). Markdown files without a mermaid
block — and non-Markdown arguments — are ignored, so it is safe to point at every file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MARKDOWN_SUFFIXES = (".md", ".markdown", ".mdown", ".mkd", ".mkdn")
_MERMAID_FENCE = re.compile(r"^\s*(`{3,}|~{3,})\s*mermaid\b", re.IGNORECASE | re.MULTILINE)


def _mmdc_command() -> list[str] | None:
    """Return the argv prefix that runs mmdc, or None if it cannot be found."""
    override = os.environ.get("MMDC")
    if override:
        return override.split()
    found = shutil.which("mmdc")
    if found:
        return [found]
    if shutil.which("npx"):
        return ["npx", "--yes", "@mermaid-js/mermaid-cli@11"]
    return None


def _has_mermaid(path: str) -> bool:
    try:
        return bool(_MERMAID_FENCE.search(Path(path).read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError):
        return False


def main(argv: list[str]) -> int:
    targets = [a for a in argv if a.lower().endswith(MARKDOWN_SUFFIXES) and _has_mermaid(a)]
    if not targets:
        return 0

    cmd = _mmdc_command()
    if cmd is None:
        print(
            "mermaid: mmdc not found and npx is unavailable — install Node.js and "
            "@mermaid-js/mermaid-cli (npm install -g @mermaid-js/mermaid-cli).",
            file=sys.stderr,
        )
        return 1

    # Puppeteer needs --no-sandbox as root / in CI; honor an out-of-band browser.
    pptr: dict = {"args": ["--no-sandbox", "--disable-setuid-sandbox"]}
    exe = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if exe:
        pptr["executablePath"] = exe

    failures: list[tuple[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "puppeteer.json"
        cfg.write_text(json.dumps(pptr), encoding="utf-8")
        for i, path in enumerate(targets):
            proc = subprocess.run(  # noqa: S603 - fixed mmdc argv; paths are argv elements, never a shell string
                [
                    *cmd,
                    "--input",
                    path,
                    "--output",
                    str(Path(tmp) / f"out-{i}.md"),
                    "--quiet",
                    "--puppeteerConfigFile",
                    str(cfg),
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0:
                print(f"mermaid ok: {path}")
            else:
                failures.append((path, (proc.stderr or proc.stdout).strip()))

    if failures:
        print("\nmermaid: diagram(s) failed to compile:", file=sys.stderr)
        for path, err in failures:
            print(f"\n  {path}:\n{err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
