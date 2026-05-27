"""Achievements database: the authoritative store for every bullet, publication,
patent, and credential the user has.

Lives at ~/.jobber/achievements.json. Gitignored. Local-only.

The achievements DB is the *primary* evidence source for every cover letter and
resume jobber generates. The library folder (`~/.jobber/library/`) is supplementary:
useful for voice samples and as input to the bootstrap extractor, but every fact
that lands in a final draft must trace back to an entry here.

Schema (informal):

  {
    "schema_version": 1,
    "generated_at": "<ISO timestamp>",
    "roles": [
      {
        "id": "company_role_slug",          # stable; referenced by achievements
        "company": "...",
        "title": "...",
        "dates": "...",                      # free text
        "city": "..."                        # optional
      }
    ],
    "achievements": [
      {
        "id": "stable-slug",                 # unique within the DB
        "role_id": "...",                    # matches a roles[].id, or null for cross-role items
        "text": "Concrete accomplishment, in user's own phrasing.",
        "attribution": "personally_built | directed_team_reviewed | led_org | co_led | co_author | contributed | partnered_external",
        "keywords": ["short", "tags", "matching JD vocabulary"],
        "evidence_citation": "PLoS ONE 17(4) 2022",  # optional
        "source_files": ["library/.../resume.pdf"],   # optional provenance
        "notes": ""                           # optional internal note, not used in drafts
      }
    ],
    "publications": [
      { "id": "...", "citation": "...", "role": "co_author | first_author | senior_author" }
    ],
    "patents": [
      { "id": "...", "title": "...", "role": "inventor | drafter", "number": "" }
    ],
    "education": [
      { "id": "...", "credential": "...", "institution": "...", "year": "..." }
    ]
  }

Attribution semantics drive the drafter's word choice:
  personally_built       → "I built / wrote / designed / implemented"
  directed_team_reviewed → "I directed the team that built; I reviewed and approved"
  led_org                → "I led" / "the organization I led"
  co_led                 → "I co-led"
  co_author              → "I co-authored"
  contributed            → "I contributed to"
  partnered_external     → "I partnered with X"
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from . import profile

SCHEMA_VERSION = 1
DB_FILENAME = "achievements.json"

VALID_ATTRIBUTIONS = {
    "personally_built",
    "directed_team_reviewed",
    "led_org",
    "co_led",
    "co_author",
    "contributed",
    "partnered_external",
}


EMPTY_DB = {
    "schema_version": SCHEMA_VERSION,
    "generated_at": None,
    "roles": [],
    "achievements": [],
    "publications": [],
    "patents": [],
    "education": [],
}


def db_path() -> Path:
    return profile.home_dir() / DB_FILENAME


def load() -> dict:
    p = db_path()
    if not p.exists():
        return dict(EMPTY_DB)
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(EMPTY_DB)
    # Defensive: ensure all top-level lists exist.
    for k in ("roles", "achievements", "publications", "patents", "education"):
        data.setdefault(k, [])
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def save(data: dict) -> Path:
    data = dict(data)
    data["schema_version"] = SCHEMA_VERSION
    data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return p


def write_empty_template() -> Path:
    """Write an empty achievements.json if none exists. Returns the path."""
    p = db_path()
    if p.exists():
        return p
    return save(dict(EMPTY_DB))


def as_prompt_json(data: dict) -> str:
    """Compact JSON for downstream LLM prompts. Strips internal/empty fields."""
    pruned = {
        "roles": data.get("roles") or [],
        "achievements": [
            {k: v for k, v in a.items() if k != "notes" and v not in (None, "", [], {})}
            for a in (data.get("achievements") or [])
        ],
        "publications": data.get("publications") or [],
        "patents": data.get("patents") or [],
        "education": data.get("education") or [],
    }
    return json.dumps(pruned, indent=2)


def validate(data: dict) -> list[str]:
    """Return a list of human-readable validation problems."""
    problems: list[str] = []

    role_ids: set[str] = set()
    for r in data.get("roles", []):
        rid = r.get("id", "")
        if not rid:
            problems.append("role with no id")
            continue
        if rid in role_ids:
            problems.append(f"duplicate role id: {rid}")
        role_ids.add(rid)

    ach_ids: set[str] = set()
    for a in data.get("achievements", []):
        aid = a.get("id", "")
        if not aid:
            problems.append("achievement with no id")
            continue
        if aid in ach_ids:
            problems.append(f"duplicate achievement id: {aid}")
        ach_ids.add(aid)
        attr = a.get("attribution", "")
        if attr and attr not in VALID_ATTRIBUTIONS:
            problems.append(
                f"achievement {aid!r} has unknown attribution {attr!r}; "
                f"valid values: {sorted(VALID_ATTRIBUTIONS)}"
            )
        rid = a.get("role_id")
        if rid and rid not in role_ids:
            problems.append(f"achievement {aid!r} references unknown role_id {rid!r}")

    return problems


# ----------------------------- bootstrap extractor --------------------------- #


EXTRACT_SYSTEM = """\
You convert a folder of past resumes, cover letters, JDs, and notes into a structured
achievements database. The user will edit your output by hand, so accuracy and
conservativeness matter more than completeness.

Output ONLY valid JSON matching this exact schema (omit fields you cannot fill):

{
  "roles": [
    { "id": "company_role_slug", "company": "", "title": "", "dates": "", "city": "" }
  ],
  "achievements": [
    {
      "id": "stable-slug",
      "role_id": "company_role_slug",
      "text": "One concrete accomplishment in the user's own phrasing.",
      "attribution": "personally_built | directed_team_reviewed | led_org | co_led | co_author | contributed | partnered_external",
      "keywords": [],
      "evidence_citation": "",
      "source_files": []
    }
  ],
  "publications": [
    { "id": "first_author_year_journal", "citation": "", "role": "co_author | first_author | senior_author" }
  ],
  "patents": [],
  "education": [
    { "id": "credential_school_year", "credential": "", "institution": "", "year": "" }
  ]
}

Rules:
- Deduplicate across files. Multiple resumes describing the same role get merged.
- Each achievement should be a single concrete accomplishment. Split run-on bullets.
- Attribution heuristic from prose:
    "Personally built / designed / wrote / implemented"     -> personally_built
    "Directed the team that built / Led the development of" -> directed_team_reviewed
    "Co-led" / "Co-led the development"                     -> co_led
    "Led" alone (with no review/built signal)               -> led_org
    "Contributed to"                                        -> contributed
    "Partnered with [external organization]"                -> partnered_external
    Author credit on a paper                                -> co_author
  When the prose is ambiguous, default to led_org and let the user override.
- IMPORTANT: if the user's notes or memory explicitly correct an attribution (e.g.
  "X was directed, not personally built"), honor that correction over the resume prose.
- Stable ids: lowercase, snake_case, derived from company and accomplishment.
- Do NOT invent facts, metrics, citations, or attributions. If unsure, omit.
"""


def extract_from_library(profile_yaml: str | None = None) -> dict:
    """Read the library folder, ask the LLM to produce a draft achievements DB.

    Importing inside the function keeps tests cheap when the LLM is not used.
    """
    from . import library
    from .llm import call

    library_root = profile.home_dir() / "library"
    if not library_root.exists():
        return dict(EMPTY_DB)

    chunks: list[str] = []
    for path in sorted(library_root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        text = library._read_text_from_file(path)
        if not text.strip():
            continue
        try:
            rel = path.relative_to(library_root)
        except ValueError:
            rel = path
        chunks.append(f"--- {rel} ---\n{text.strip()}")

    if not chunks:
        return dict(EMPTY_DB)

    user_blob = "\n\n".join(chunks)
    if profile_yaml:
        user_blob = "USER PROFILE (apply attribution overrides):\n" + profile_yaml + "\n\nLIBRARY:\n" + user_blob

    raw = call(system=EXTRACT_SYSTEM, user=user_blob, cache_system=True, max_tokens=16000)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return dict(EMPTY_DB)
        parsed = json.loads(match.group(0))

    # Normalize: ensure all top-level lists exist.
    for k in ("roles", "achievements", "publications", "patents", "education"):
        parsed.setdefault(k, [])
    parsed["schema_version"] = SCHEMA_VERSION
    return parsed
