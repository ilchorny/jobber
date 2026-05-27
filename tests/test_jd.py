"""Tests that don't need an LLM."""
from __future__ import annotations

from pathlib import Path

from jobber import jd


def test_ingest_text_passthrough():
    assert jd.ingest("Hello world") == "Hello world"


def test_ingest_local_file(tmp_path: Path):
    p = tmp_path / "jd.md"
    p.write_text("# Role\n\nResponsibilities: foo.\n")
    out = jd.ingest(str(p))
    assert "Responsibilities" in out


def test_html_to_text_strips_tags_and_scripts():
    html = "<html><head><script>alert(1)</script><style>x{}</style></head><body><p>Hello <b>world</b></p></body></html>"
    out = jd.html_to_text(html)
    assert "alert" not in out
    assert "Hello world" in out
