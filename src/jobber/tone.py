"""Tone profile: structured style notes extracted from the user's past cover
letters, used by the drafter as authoritative voice guidance.

Lives at ~/.jobber/tone.json. Gitignored. Local-only. Human-editable.

The achievements DB captures *what* the candidate has done. The tone profile
captures *how* they write about it. Without this, the drafter falls back on a
generic "professional cover letter" register that often reads as polished
marketing copy rather than the user's actual voice.

Schema (informal):

  {
    "schema_version": 1,
    "generated_at": "<ISO>",
    "source_files": ["library/cover_letters/...", ...],
    "tone_descriptor": "One or two sentences describing the overall register.",
    "openers": [
      "Quoted opening sentence or pattern from a past letter.",
      ...
    ],
    "closers": [
      "Quoted closing sentence or pattern.",
      ...
    ],
    "section_pivots": [
      "Phrases used to move between paragraphs ('A few specifics on fit.', 'Three things.')",
      ...
    ],
    "recurring_phrases": [
      "Phrases that recur across letters and feel distinctively this writer.",
      ...
    ],
    "sentence_rhythm": "Free-text observation about cadence, sentence length, mix of short/long.",
    "vocabulary_notes": "Free-text observation about word choice. e.g. plain Anglo-Saxon vs Latinate, technical vs general, hedged vs declarative.",
    "things_avoided": [
      "Patterns absent from the user's letters that the drafter might otherwise default to. e.g. 'I am writing to express interest', exclamation points, etc.",
      ...
    ]
  }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import profile

SCHEMA_VERSION = 1
FILENAME = "tone.json"


EMPTY = {
    "schema_version": SCHEMA_VERSION,
    "generated_at": None,
    "source_files": [],
    "tone_descriptor": "",
    "openers": [],
    "closers": [],
    "section_pivots": [],
    "recurring_phrases": [],
    "sentence_rhythm": "",
    "vocabulary_notes": "",
    "things_avoided": [],
}


def db_path() -> Path:
    return profile.home_dir() / FILENAME


def load() -> dict:
    p = db_path()
    if not p.exists():
        return dict(EMPTY)
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(EMPTY)
    for k, v in EMPTY.items():
        data.setdefault(k, v)
    return data


def save(data: dict) -> Path:
    data = dict(data)
    data["schema_version"] = SCHEMA_VERSION
    data["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")
    return p


def as_prompt_text(data: dict) -> str:
    """Compact human-readable rendering for the drafter's system prompt."""
    if not (data.get("openers") or data.get("recurring_phrases") or data.get("tone_descriptor")):
        return "(no tone profile yet; fall back on the candidate's profile.voice rules)"
    out: list[str] = []
    if data.get("tone_descriptor"):
        out.append(f"OVERALL TONE: {data['tone_descriptor']}")
    if data.get("sentence_rhythm"):
        out.append(f"RHYTHM: {data['sentence_rhythm']}")
    if data.get("vocabulary_notes"):
        out.append(f"VOCABULARY: {data['vocabulary_notes']}")
    if data.get("openers"):
        out.append("OPENING PATTERNS (quoted from the user's own past letters):")
        for s in data["openers"]:
            out.append(f"  - {s}")
    if data.get("section_pivots"):
        out.append("SECTION PIVOTS:")
        for s in data["section_pivots"]:
            out.append(f"  - {s}")
    if data.get("recurring_phrases"):
        out.append("RECURRING PHRASES (use naturally where context fits):")
        for s in data["recurring_phrases"]:
            out.append(f"  - {s}")
    if data.get("closers"):
        out.append("CLOSING PATTERNS:")
        for s in data["closers"]:
            out.append(f"  - {s}")
    if data.get("things_avoided"):
        out.append("DO NOT USE (absent from the user's past letters):")
        for s in data["things_avoided"]:
            out.append(f"  - {s}")
    return "\n".join(out)


# ----------------------------- extractor --------------------------- #


EXTRACT_SYSTEM = """\
You are extracting a STRUCTURED TONE PROFILE from a writer's past cover letters.
The goal is to capture how this specific person writes, so a future drafter can
mimic their voice instead of falling back on generic "professional cover letter"
patterns.

You will receive the full text of one or more past cover letters. Output ONLY
valid JSON in this exact shape (omit empty arrays):

{
  "tone_descriptor": "One or two sentences describing the overall register. Be concrete: 'matter-of-fact and thesis-driven; declarative sentences; no hedging' is better than 'professional'.",
  "openers": [
    "QUOTE the actual first sentence (or 1-2 lines) from each distinct letter. Do not paraphrase."
  ],
  "closers": [
    "QUOTE the actual closing sentence(s) of each letter."
  ],
  "section_pivots": [
    "Phrases the writer uses to start new paragraphs or pivot between ideas. QUOTE them. e.g. 'A few specifics on fit.' or 'Three things I bring.'"
  ],
  "recurring_phrases": [
    "Phrases that appear in more than one letter, or feel distinctively this writer. QUOTE them."
  ],
  "sentence_rhythm": "Free-text observation: typical sentence length, mix of short and long, use of one-word sentences, parenthetical asides, etc.",
  "vocabulary_notes": "Free-text observation about word choice: Latinate vs Anglo-Saxon, technical vs general, declarative vs hedged, use of contractions, jargon level, etc.",
  "things_avoided": [
    "Concrete patterns that are ABSENT from the writer's letters and that a drafter might otherwise default to. e.g. 'I am writing to express interest in', exclamation points, 'passionate about', em-dashes."
  ]
}

Rules:
- Quote actual text from the letters. Do not invent phrases.
- If you cannot find an opener/closer/pivot pattern in the input, leave its array empty rather than fabricating one.
- Be specific in `tone_descriptor`, `sentence_rhythm`, and `vocabulary_notes`. Vague answers ('professional', 'clear') are useless.
- The `things_avoided` list should be derived from what is *not* present in the letters, not from general writing advice.
"""


def extract_from_library() -> dict:
    """Read library/cover_letters/* and produce a tone profile."""
    from .library import _read_text_from_file
    from .llm import call

    library_root = profile.home_dir() / "library"
    cl_root = library_root / "cover_letters"
    if not cl_root.exists():
        return dict(EMPTY)

    samples: list[tuple[Path, str]] = []
    for path in sorted(cl_root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        text = _read_text_from_file(path)
        if text.strip():
            samples.append((path, text.strip()))

    if not samples:
        return dict(EMPTY)

    user_blob = "\n\n".join(
        f"--- {path.relative_to(library_root)} ---\n{text}" for path, text in samples
    )
    raw = call(system=EXTRACT_SYSTEM, user=user_blob, cache_system=True, max_tokens=6000)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return dict(EMPTY)
        data = json.loads(match.group(0))

    # Normalize and stamp provenance.
    for k, v in EMPTY.items():
        data.setdefault(k, v)
    data["source_files"] = [
        str(path.relative_to(library_root)) for path, _ in samples
    ]
    data["schema_version"] = SCHEMA_VERSION
    return data
