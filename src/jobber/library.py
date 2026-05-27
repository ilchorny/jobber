"""Library indexer: read a folder of past resumes/cover letters/JDs/notes,
extract evidence facts with the LLM, cache the index.

Cache key: a hash of (file path, mtime) for every library file. If anything
changes, the index is rebuilt.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from . import profile
from .llm import call

INDEX_FILENAME = "library_index.json"

EXTRACT_SYSTEM = """\
You are extracting a structured evidence library from a user's past job-search materials.

Output ONLY valid JSON matching this schema:
{
  "roles": [
    {
      "id": "short-stable-id",          # e.g. "quantumsi_vp"
      "company": "",
      "title": "",
      "dates": "",                       # free text, e.g. "May 2023 to May 2026"
      "capabilities": [],                # short tags, e.g. "basecalling", "ml_methods"
      "bullets": [
        {
          "text": "",                    # one accomplishment, complete sentence
          "attribution": "personally_built | directed_team_reviewed | led_org | co_author | participant",
          "evidence_source": ""          # filename(s) from which this bullet was drawn
        }
      ]
    }
  ],
  "publications": [
    { "citation": "", "role": "" }
  ],
  "personal_projects": [
    { "name": "", "one_liner": "", "capabilities": [] }
  ]
}

Rules:
- Deduplicate across files. If multiple resumes describe the same role, merge bullets.
- Attribution language must match how the user described it. Default to "led_org" if unclear.
- Do not invent facts. If a bullet only appears in one source, that is fine.
- Keep bullet text close to the user's phrasing.
- Use stable role ids derived from company name (lowercase, no spaces).
"""


@dataclass
class LibraryIndex:
    roles: list[dict]
    publications: list[dict]
    personal_projects: list[dict]
    fingerprint: str

    def as_json(self) -> str:
        return json.dumps(
            {
                "roles": self.roles,
                "publications": self.publications,
                "personal_projects": self.personal_projects,
                "fingerprint": self.fingerprint,
            },
            indent=2,
        )

    def as_prompt_yaml(self) -> str:
        """Compact text representation for downstream prompts."""
        import yaml
        return yaml.safe_dump(
            {
                "roles": self.roles,
                "publications": self.publications,
                "personal_projects": self.personal_projects,
            },
            sort_keys=False,
            allow_unicode=True,
        )


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


def _fingerprint(library_root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(library_root.rglob("*")):
        if path.is_file():
            try:
                stat = path.stat()
                h.update(str(path.relative_to(library_root)).encode())
                h.update(str(stat.st_mtime_ns).encode())
                h.update(str(stat.st_size).encode())
            except OSError:
                continue
    return h.hexdigest()[:16]


def _cache_path() -> Path:
    return profile.home_dir() / "cache" / INDEX_FILENAME


def load_cached() -> LibraryIndex | None:
    p = _cache_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return LibraryIndex(
            roles=data.get("roles", []),
            publications=data.get("publications", []),
            personal_projects=data.get("personal_projects", []),
            fingerprint=data.get("fingerprint", ""),
        )
    except (OSError, json.JSONDecodeError):
        return None


def build_index(*, force: bool = False) -> LibraryIndex:
    """Read the library, extract evidence with the LLM, cache result."""
    library_root = profile.home_dir() / "library"
    fp = _fingerprint(library_root)

    if not force:
        cached = load_cached()
        if cached and cached.fingerprint == fp:
            return cached

    # Gather all readable text.
    chunks: list[str] = []
    for path in sorted(library_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        text = _read_text_from_file(path)
        if not text.strip():
            continue
        rel = path.relative_to(library_root)
        chunks.append(f"--- {rel} ---\n{text.strip()}")

    if not chunks:
        idx = LibraryIndex(roles=[], publications=[], personal_projects=[], fingerprint=fp)
        _cache_path().parent.mkdir(parents=True, exist_ok=True)
        _cache_path().write_text(idx.as_json())
        return idx

    user_blob = "\n\n".join(chunks)
    raw = call(system=EXTRACT_SYSTEM, user=user_blob, cache_system=True, max_tokens=16000)
    data = _safe_json(raw)

    idx = LibraryIndex(
        roles=data.get("roles", []),
        publications=data.get("publications", []),
        personal_projects=data.get("personal_projects", []),
        fingerprint=fp,
    )
    _cache_path().parent.mkdir(parents=True, exist_ok=True)
    _cache_path().write_text(idx.as_json())
    return idx


def _safe_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find the first {...} block.
        import re
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
