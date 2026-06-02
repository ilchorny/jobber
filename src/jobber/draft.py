"""Draft the cover letter and resume from JD + mapping + achievements + tone profile."""
from __future__ import annotations

import json

from .llm import call


COVER_SYSTEM = """\
You draft a cover letter for the candidate. Inputs you receive:
  1. JD requirements JSON
  2. Mapping JSON (requirements -> achievement_id with fit ratings, thesis_candidates)
  3. Achievements DB JSON (AUTHORITATIVE source of every bullet you may reference)
  4. User profile YAML (voice rules, constraints, attribution overrides)
  5. Tone profile (AUTHORITATIVE voice guidance extracted from the user's past letters)
  6. Optional extra context

Output ONLY the cover letter in Markdown. Nothing else. No preamble, no explanation, no code fences.

General rules:
- VOICE: the tone profile is authoritative. Match its `tone_descriptor`, `sentence_rhythm`, and `vocabulary_notes`. Use the quoted `openers` / `section_pivots` / `closers` patterns (or compose ones that sound the same). Weave in `recurring_phrases` where the context fits naturally. Treat `things_avoided` as a strict do-not-use list. Do NOT fall back on generic "professional cover letter" register if the tone profile contradicts it.
- profile.voice.cover_letter still applies for things the tone profile does not cover.
- Honor every entry in profile.constraints.forbidden_patterns (e.g. "no em-dashes" -> use periods/colons/commas instead).
- Do not use em-dashes (—) in any context, including title formatting. Use commas, periods, or pipes (|) instead. (An ASCII hyphen-minus is fine; an en-dash – is fine for date ranges only.)
- Look up each evidence entry by achievement_id in the Achievements DB. Use the achievement's `text`, and shape your language around its `attribution`:
    personally_built       -> "I built / designed / wrote / implemented"
    directed_team_reviewed -> "I directed the team that built / I reviewed and approved"
    led_org                -> "I led" / "the organization I led"
    co_led                 -> "I co-led"
    co_author              -> "I co-authored"
    contributed            -> "I contributed to"
    partnered_external     -> "I partnered with X on"
  Never escalate attribution (e.g. never say "I built" when the DB says "directed_team_reviewed").
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
  2. Mapping JSON (achievement_id references)
  3. Achievements DB JSON (AUTHORITATIVE source of every bullet)
  4. User profile YAML

Output ONLY the resume in Markdown. No preamble, no explanation.

General rules:
- Header: candidate's name (large), then contact lines (city, phone, email) and a tagline.
- Tagline: 4-5 pipe-separated themes that mirror the JD's top requirements where evidence supports.
- Summary paragraph: short, hits the JD's vocabulary where backed by evidence. Use Achievements DB as the source of truth.
- Professional Experience: roles in reverse-chronological order from `roles`. Each role: company (bold), title and dates (italics), then 3-7 bullet points pulled from achievements (filtered by role_id, ordered by relevance to the JD). Use the JD's vocabulary verbatim where the achievement text supports it; do not invent new facts.
- Respect attribution rigorously. The achievement's `attribution` field is non-negotiable:
    personally_built       -> "Built / Designed / Wrote / Implemented" (no qualifier)
    directed_team_reviewed -> "Directed the team that built / Reviewed and approved" (do NOT use "personally" prefix)
    led_org                -> "Led" / "Managed"
    co_led                 -> "Co-led"
    co_author              -> "Co-author on" / "Co-authored"
    contributed            -> "Contributed to"
    partnered_external     -> "Partnered with X on"
  Do NOT spray the word "Personally" onto bullets that are not personally_built.
- Honor profile.constraints.forbidden_patterns.
- Do not use em-dashes (—) anywhere in the resume, including header separators. Use spaces, commas, or pipes (|) instead. En-dashes (–) in date ranges are fine.
- Selected Publications section from `publications`. Cite each as the publications[].citation.
- Education section from `education`.
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


def _strip_em_dashes(text: str) -> str:
    """Replace em-dashes with safer alternatives.

    Heuristic: on markdown header / role / publication-citation lines (lines
    that include bold/italic markers), use a pipe (`|`) as the separator. In
    prose, use a comma. En-dashes between dates (e.g. "2023 – 2026") are kept
    because they are conventional and not an LLM tell.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        if "—" not in line:
            out_lines.append(line)
            continue
        is_structured = ("**" in line) or (line.lstrip().startswith("#"))
        if is_structured:
            line = line.replace(" — ", " | ")
        else:
            line = line.replace(" — ", ", ")
        # Any remaining em-dashes (no spaces around them) get a comma.
        line = line.replace("—", ",")
        out_lines.append(line)
    return "\n".join(out_lines)


def _common_user(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    achievements_json: str,
    profile_yaml: str,
    tone_text: str,
    extra_context: str,
) -> str:
    return (
        "JD TEXT:\n"
        + jd_text
        + "\n\nJD REQUIREMENTS (JSON):\n"
        + json.dumps(requirements, indent=2)
        + "\n\nMAPPING (JSON):\n"
        + json.dumps(mapping, indent=2)
        + "\n\nACHIEVEMENTS DB (JSON, AUTHORITATIVE):\n"
        + achievements_json
        + "\n\nUSER PROFILE (YAML):\n"
        + profile_yaml
        + "\n\nTONE PROFILE (AUTHORITATIVE voice guidance):\n"
        + (tone_text or "(no tone profile yet)")
        + "\n\nEXTRA CONTEXT:\n"
        + (extra_context or "(none)")
    )


def draft_cover_letter(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    achievements_json: str,
    profile_yaml: str,
    tone_text: str = "",
    extra_context: str = "",
    model: str | None = None,
) -> str:
    user = _common_user(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        achievements_json=achievements_json,
        profile_yaml=profile_yaml,
        tone_text=tone_text,
        extra_context=extra_context,
    )
    raw = call(system=COVER_SYSTEM, user=user, cache_system=False, model=model, max_tokens=4000)
    return _strip_em_dashes(_stringify(raw))


def draft_resume(
    *,
    jd_text: str,
    requirements: dict,
    mapping: dict,
    achievements_json: str,
    profile_yaml: str,
    tone_text: str = "",
    extra_context: str = "",
    model: str | None = None,
) -> str:
    user = _common_user(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        achievements_json=achievements_json,
        profile_yaml=profile_yaml,
        tone_text=tone_text,
        extra_context=extra_context,
    )
    raw = call(system=RESUME_SYSTEM, user=user, cache_system=False, model=model, max_tokens=6000)
    return _strip_em_dashes(_stringify(raw))
