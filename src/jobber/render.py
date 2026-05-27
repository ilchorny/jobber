"""Render markdown to PDF via Chrome headless.

Lifted from a working ad-hoc script. macOS path is hard-coded for now; the
function accepts a `chrome_path` override so other platforms or CI can plug
in their own binary.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import markdown


MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DEFAULT_CSS = """
@page { size: Letter; margin: 0.6in; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 10pt; line-height: 1.35; color: #222; }
h1 { font-size: 18pt; margin-top: 0; border-bottom: 2px solid #333; padding-bottom: 4px; }
h2 { font-size: 13pt; margin-top: 18px; border-bottom: 1px solid #999; padding-bottom: 2px; }
h3 { font-size: 11pt; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; }
th, td { border: 1px solid #bbb; padding: 5px 7px; vertical-align: top; text-align: left; }
th { background: #f0f0f0; font-weight: 600; }
code { font-family: Menlo, Monaco, monospace; font-size: 9pt; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }
strong { font-weight: 600; }
ul, ol { margin: 4px 0 4px 18px; }
li { margin: 2px 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 14px 0; }
"""


def _resolve_chrome(chrome_path: str | None) -> str:
    if chrome_path:
        return chrome_path
    env = os.environ.get("JOBBER_CHROME_PATH")
    if env:
        return env
    return MAC_CHROME


def md_to_pdf(
    md_path: Path,
    pdf_path: Path,
    *,
    css: str | None = None,
    chrome_path: str | None = None,
) -> Path:
    """Convert a Markdown file to PDF. Returns the PDF path."""
    md_text = md_path.read_text()
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>{md_path.stem}</title><style>{css or DEFAULT_CSS}</style></head>"
        f"<body>{html_body}</body></html>"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
        tmp.write(html)
        html_path = Path(tmp.name)

    try:
        subprocess.run(
            [
                _resolve_chrome(chrome_path),
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                f"file://{html_path}",
            ],
            check=True,
            capture_output=True,
        )
    finally:
        html_path.unlink(missing_ok=True)
    return pdf_path
