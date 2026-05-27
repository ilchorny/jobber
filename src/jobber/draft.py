"""Draft the cover letter and resume from JD + mapping + profile + library."""
from __future__ import annotations

import json

from .llm import call


COVER_SYSTEM = """\
You draft a cover letter for the candidate. Inputs you receive:
  1. JD requirements JSON
  2. Mapping JSON (requirements ↔ evidence with fit ratings, attribution, thesis_candidates)
  3. Library YAML
  4. User profile YAML (voice rules, constraints, attribution overrides)
  5. Optional extra context

Output ONLY the cover letter in Markdown. Nothing else. No preamble, no explanation, no code fences.

General rules:
- Use the candidate's voice as described in profile.voice.cover_letter.
- Honor every entry in profile.constraints.forbidden_patterns (e.g. "no em-dashes" → use periods/colons/commas instead).
- Respect attribution exactly. Use the phrasing implied by each mapping evidence entry's attribution.
- Pick one thesis from thesis_candidates (or compose a stronger one) and open with it. No "I am writing to express interest" filler.
- Cite specific evidence: 2-4 inline parentheticals are fine (publications, study names, metrics).
- Cover only the strongest matches (mapping entries where include_in_cover_letter=true).
- If a JD keyword is in honest_gaps, do not mention it in the cover letter.
- Default length: 350-450 words unless the profile says otherwise.
- Standard structure: opening thesis paragraph, 2-3 evidence paragraphs, optional pre-empt of a known gap, brief closing offering a conversation. No sub-heads. No bullet lists.
"""


RESUME_SYSTEM = """\
You draft a one-to-two page resume in Markdown. Inputs:
  1. JD requirements JSON
  2. Mapping JSON
  3. Library YAML (the canonical source of bullets — never invent new bullets)
  4. User profile YAML

Output ONLY the resume in Markdown. No preamble, no explanation.

General rules:
- Header: candidate's name (large), then contact lines (city, phone, email) and a tagline.
- Tagline: 4-5 pipe-separated themes that mirror the JD's top requirements where evidence supports.
- Summary paragraph: short, hits the JD's vocabulary where backed by evidence. Use library bullets as the source of truth.
- Professional Experience: roles in reverse-chronological order. Each role: company (bold), title and dates (italics), then 3-7 bullet points pulled from library.bullets. Use the JD's vocabulary verbatim where the bullet supports it.
- Respect attribution rigorously. Personally-built bullets may say "personally built / designed / wrote"; directed_team_reviewed bullets must say "directed / led / reviewed and approved"; led_org bullets must say "led" or "managed".
- Honor profile.constraints.forbidden_patterns.
- Selected Publications section pulled directly from library.publications.
- Education section if present in library or profile.
- No content from honest_gaps.
"""


def _stringify(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return cleaned.strip()


def _common_user(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    library_yaml: str,
    profile_yaml: str,
    extra_context: str,
) -> str:
    return (
        "JD TEXT:\n"
        + jd_text
        + "\n\nJD REQUIREMENTS (JSON):\n"
        + json.dumps(requirements, indent=2)
        + "\n\nMAPPING (JSON):\n"
        + json.dumps(mapping, indent=2)
        + "\n\nLIBRARY (YAML):\n"
        + library_yaml
        + "\n\nUSER PROFILE (YAML):\n"
        + profile_yaml
        + "\n\nEXTRA CONTEXT (free text, may be empty):\n"
        + (extra_context or "(none)")
    )


def draft_cover_letter(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    library_yaml: str,
    profile_yaml: str,
    extra_context: str = "",
    model: str | None = None,
) -> str:
    user = _common_user(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=library_yaml,
        profile_yaml=profile_yaml,
        extra_context=extra_context,
    )
    raw = call(system=COVER_SYSTEM, user=user, cache_system=False, model=model, max_tokens=4000)
    return _stringify(raw)


def draft_resume(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    library_yaml: str,
    profile_yaml: str,
    extra_context: str = "",
    model: str | None = None,
) -> str:
    user = _common_user(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=library_yaml,
        profile_yaml=profile_yaml,
        extra_context=extra_context,
    )
    raw = call(system=RESUME_SYSTEM, user=user, cache_system=False, model=model, max_tokens=6000)
    return _stringify(raw)
