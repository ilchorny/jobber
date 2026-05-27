"""Drafter helper tests (no LLM)."""
from __future__ import annotations

from jobber.draft import _strip_em_dashes


def test_strip_em_dashes_in_structured_lines():
    line = "**Quantum-Si, Inc.** — *Vice President (May 2023 – May 2026)*"
    out = _strip_em_dashes(line)
    assert "—" not in out
    assert "|" in out
    assert "–" in out  # en-dash in date range preserved


def test_strip_em_dashes_in_prose_uses_comma():
    line = "Set methods strategy across signal processing — including error modeling."
    out = _strip_em_dashes(line)
    assert "—" not in out
    assert ", including error modeling." in out


def test_strip_em_dashes_no_spaces_falls_to_comma():
    line = "model—throughput tradeoffs"
    out = _strip_em_dashes(line)
    assert "—" not in out
    assert "," in out


def test_strip_em_dashes_preserves_clean_text():
    text = "Plain text with no funny dashes."
    assert _strip_em_dashes(text) == text
