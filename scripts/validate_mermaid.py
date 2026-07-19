#!/usr/bin/env python3
"""Validate Mermaid diagrams embedded in Markdown files.

A dependency-free, pre-commit-friendly *structural* validator for ```mermaid
fenced code blocks. It does **not** render diagrams (a faithful render needs a
headless browser via ``mmdc``); it catches the mistakes that actually break
rendering or slip past review:

  * an unterminated ```mermaid fence — silently swallows the rest of the doc;
  * an empty diagram block;
  * a missing / misspelled diagram-type header (``graph``, ``flowchart``, …);
  * unbalanced ``()`` ``[]`` ``{}`` brackets (outside quoted strings).

Fenced-code parsing follows CommonMark closely enough for real documents: the
fence marker may be ``` or ~~~ (length ≥ 3), fences may be indented, and a
``mermaid`` fence nested inside a longer outer code fence (i.e. shown as an
example) is treated as literal content, never validated.

Usage::

    validate_mermaid.py FILE [FILE ...]

Exit status is non-zero if any block fails a check. Files with no ``mermaid``
blocks — or no Markdown extension — pass trivially, so it is safe to point the
hook at every staged file.
"""

from __future__ import annotations

import re
import sys

# Recognised Mermaid diagram-type headers (lower-cased, hyphen-preserving).
# The first word of a diagram's first significant line must be one of these.
KNOWN_TYPES: frozenset[str] = frozenset(
    {
        "graph",
        "flowchart",
        "flowchart-elk",
        "sequencediagram",
        "classdiagram",
        "classdiagram-v2",
        "statediagram",
        "statediagram-v2",
        "erdiagram",
        "journey",
        "gantt",
        "pie",
        "quadrantchart",
        "requirementdiagram",
        "gitgraph",
        "mindmap",
        "timeline",
        "zenuml",
        "sankey",
        "sankey-beta",
        "xychart",
        "xychart-beta",
        "block",
        "block-beta",
        "packet",
        "packet-beta",
        "architecture",
        "architecture-beta",
        "kanban",
        "radar",
        "radar-beta",
        "treemap",
        "treemap-beta",
        "info",
        "c4context",
        "c4container",
        "c4component",
        "c4dynamic",
        "c4deployment",
    }
)

MARKDOWN_SUFFIXES = (".md", ".markdown", ".mdown", ".mkd", ".mkdn")

# An opening fence: optional indent, then >=3 backticks or tildes, then an info
# string whose first token is the language.
_OPEN_FENCE = re.compile(r"^(?P<indent>\s*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
# A closing fence: only indent + a run of the same marker + optional trailing space.
_CLOSE_FENCE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})\s*$")


class MermaidError:
    """One validation failure, anchored to a 1-based line in a file."""

    def __init__(self, path: str, line: int, message: str) -> None:
        self.path = path
        self.line = line
        self.message = message

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: mermaid: {self.message}"


def _iter_mermaid_blocks(lines: list[str]):
    """Yield ``(start_line, content_lines, closed)`` for each ```mermaid block.

    ``start_line`` is the 1-based line number of the opening fence; ``closed`` is
    False when the fence ran to end-of-file without a matching close. Generic
    (non-mermaid) code fences are tracked so their contents — including any inner
    ```mermaid shown as an example — are skipped, not validated.
    """
    in_block = False
    fence_char = ""
    fence_len = 0
    lang = ""
    start_line = 0
    content: list[str] = []

    for idx, raw in enumerate(lines, start=1):
        if not in_block:
            m = _OPEN_FENCE.match(raw)
            if m:
                fence = m.group("fence")
                fence_char = fence[0]
                fence_len = len(fence)
                lang = m.group("info").strip().split(" ")[0].split("\t")[0].lower()
                in_block = True
                start_line = idx
                content = []
            continue

        # Inside a fenced block: only a matching closing fence ends it.
        close = _CLOSE_FENCE.match(raw)
        if close:
            marker = close.group("fence")
            if marker[0] == fence_char and len(marker) >= fence_len:
                if lang == "mermaid":
                    yield start_line, content, True
                in_block = False
                continue
        content.append(raw)

    if in_block and lang == "mermaid":
        yield start_line, content, False


def _significant_lines(content: list[str]) -> list[str]:
    """Drop blanks, ``%%`` comments/directives, and a leading ``---`` frontmatter
    block, returning the lines that carry diagram structure."""
    out: list[str] = []
    in_frontmatter = False
    seen_significant = False
    for raw in content:
        stripped = raw.strip()
        if not stripped:
            continue
        # A leading `---` opens a YAML frontmatter block; skip to its close.
        if not seen_significant and not in_frontmatter and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        # `%%` line comments and `%%{init …}%%` directives are not structure.
        if stripped.startswith("%%"):
            continue
        seen_significant = True
        out.append(stripped)
    return out


def _brackets_balanced(sig: list[str]) -> bool:
    """True if ``()`` ``[]`` ``{}`` are net-balanced outside double-quoted text.

    If quotes are themselves unbalanced across the block we cannot reliably strip
    them, so we decline to judge (return True) rather than raise a false alarm.
    """
    text = "\n".join(sig)
    if text.count('"') % 2 != 0:
        return True
    pairs = {")": "(", "]": "[", "}": "{"}
    counts = {"(": 0, "[": 0, "{": 0}
    in_quote = False
    for ch in text:
        if ch == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch in counts:
            counts[ch] += 1
        elif ch in pairs:
            counts[pairs[ch]] -= 1
    return all(v == 0 for v in counts.values())


def _first_word(line: str) -> str:
    return re.split(r"[\s:]", line, maxsplit=1)[0].lower()


def validate_file(path: str) -> list[MermaidError]:
    """Return every mermaid validation error found in ``path`` (possibly empty)."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [MermaidError(path, 1, f"could not read file ({exc})")]

    errors: list[MermaidError] = []
    for start_line, content, closed in _iter_mermaid_blocks(lines):
        if not closed:
            errors.append(
                MermaidError(path, start_line, "unterminated ```mermaid fence (no closing ```)")
            )
            continue

        sig = _significant_lines(content)
        if not sig:
            errors.append(MermaidError(path, start_line, "empty mermaid block"))
            continue

        header = _first_word(sig[0])
        if header not in KNOWN_TYPES:
            errors.append(
                MermaidError(
                    path,
                    start_line,
                    f"first line is not a recognised diagram type: {sig[0]!r}",
                )
            )

        if not _brackets_balanced(sig):
            errors.append(
                MermaidError(path, start_line, "unbalanced () [] or {} brackets in the diagram")
            )

    return errors


def main(argv: list[str]) -> int:
    errors: list[MermaidError] = []
    checked = 0
    for path in argv:
        if not path.lower().endswith(MARKDOWN_SUFFIXES):
            continue
        checked += 1
        errors.extend(validate_file(path))

    if errors:
        for err in errors:
            print(str(err), file=sys.stderr)
        n = len(errors)
        print(
            f"\nmermaid: {n} problem{'s' if n != 1 else ''} in {checked} markdown file(s).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
