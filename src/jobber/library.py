"""Read text out of library files (pdf/docx/md/txt/html).

The library folder is the raw corpus the user drops resumes, cover letters, and
JDs into. Two extractors consume it: `achievements.extract_from_library` builds
the structured achievements DB, and `tone.extract_from_library` builds the tone
profile from past cover letters. Neither the mapper nor the drafter reads the
library directly anymore — they use the structured outputs.
"""
from __future__ import annotations

from pathlib import Path


def _read_text_from_file(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return ""
    if suf == ".docx":
        try:
            from docx import Document
            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    if suf in {".md", ".markdown", ".txt", ".rst", ".html", ".htm"}:
        try:
            return path.read_text(errors="replace")
        except OSError:
            return ""
    return ""
