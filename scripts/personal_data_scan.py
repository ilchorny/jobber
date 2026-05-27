#!/usr/bin/env python3
"""Pre-commit guard: refuse commits that contain obvious personal-data leaks.

Reads a configurable blocklist from `.personal-data-blocklist` (one entry per line:
exact strings or regex prefixed with `re:`). Scans the staged content of files
passed on the command line; exits non-zero with a clear error if any entry hits.

Default blocklist (if no file exists): an empty list. The hook does nothing.

To add personal terms to block locally, create `.personal-data-blocklist` in the
repo root with entries like:

    your.name@example.com
    re:\\b[Yy]our[ _]?[Nn]ame\\b
    +1 555 555 5555

This file should itself NOT be committed (it is in .gitignore).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCKLIST_PATH = ROOT / ".personal-data-blocklist"


def load_blocklist() -> list[tuple[str, re.Pattern[str] | None]]:
    if not BLOCKLIST_PATH.exists():
        return []
    out: list[tuple[str, re.Pattern[str] | None]] = []
    for raw in BLOCKLIST_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            pattern = line[3:]
            out.append((line, re.compile(pattern)))
        else:
            out.append((line, None))
    return out


def scan_file(path: Path, entries: list[tuple[str, re.Pattern[str] | None]]) -> list[str]:
    """Return a list of human-readable hit messages for `path`."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return []
    hits: list[str] = []
    for entry, regex in entries:
        if regex is not None:
            if regex.search(text):
                hits.append(f"{path}: regex `{entry}` matched")
        else:
            if entry in text:
                hits.append(f"{path}: literal `{entry}` present")
    return hits


def main(paths: list[str]) -> int:
    entries = load_blocklist()
    if not entries:
        return 0
    all_hits: list[str] = []
    for p in paths:
        path = Path(p)
        if not path.exists() or not path.is_file():
            continue
        all_hits.extend(scan_file(path, entries))
    if all_hits:
        sys.stderr.write("personal-data-scan: blocked commit due to personal data\n")
        for hit in all_hits:
            sys.stderr.write(f"  {hit}\n")
        sys.stderr.write(
            "\nIf this is a false positive, edit `.personal-data-blocklist` or "
            "remove the offending content from the staged files.\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
