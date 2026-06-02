"""Map JD requirements to evidence in the library."""
from __future__ import annotations

import json

from .llm import call


SYSTEM = """\
You map each JD requirement to evidence from the user's achievements database.

You will receive:
  1. A JD requirements JSON (responsibilities, required quals, preferred quals).
  2. An achievements database JSON (roles, achievements, publications, patents, education).
     This is the AUTHORITATIVE source for every bullet you may use. Each achievement
     has an `id`, a `role_id`, a `text`, an `attribution`, and `keywords`.
  3. A user profile in YAML (voice rules, attribution overrides, stretches_to_avoid).
  4. Optional extra context the user provided about this application.

Output ONLY valid JSON with this shape:

{
  "company": "",                       # from JD
  "role_title": "",                    # from JD
  "mappings": [
    {
      "requirement_id": "R1",
      "requirement_text": "",
      "fit": "strong | moderate | weak | none",
      "evidence": [
        {
          "achievement_id": "",        # MUST match an entry in achievements[].id
          "attribution": ""             # MUST match achievements[].attribution for that id
        }
      ],
      "include_in_cover_letter": true,
      "include_in_resume": true,
      "stretch_notes": ""               # if fit is "none" or "weak", explain why
    }
  ],
  "honest_gaps": [
    {
      "keyword": "",
      "reason": ""
    }
  ],
  "thesis_candidates": [
    "Short candidate opening thesis for the cover letter, one sentence each"
  ]
}

Rules:
- Evidence references MUST be by achievement_id. Do NOT paste bullet text into evidence
  entries: the drafter will look up the text from the achievements DB by id.
- Do not invent achievements. If no matching achievement exists for a JD requirement,
  return an empty evidence list and fit="none" (or "weak" with stretch_notes).
- Attribution in your evidence entries MUST mirror the achievement's stored attribution.
  Never escalate (e.g., do not relabel a directed_team_reviewed achievement as
  personally_built). If you disagree with stored attribution, do not change it here;
  flag it in stretch_notes.
- For each JD keyword that is also in profile.stretches_to_avoid, add it to honest_gaps
  and set fit="none" for any responsibility that depends on it.
- Default include_in_resume=true for "strong" or "moderate" matches. include_in_cover_letter=true
  for the 5-8 strongest matches.
- Produce 2-3 thesis_candidates anchored in the strongest matches.
"""


def build_mapping(
    *,
    requirements: dict,
    achievements_json: str,
    profile_yaml: str,
    extra_context: str = "",
) -> dict:
    user = (
        "JD REQUIREMENTS (JSON):\n"
        + json.dumps(requirements, indent=2)
        + "\n\nACHIEVEMENTS DB (JSON, AUTHORITATIVE):\n"
        + achievements_json
        + "\n\nUSER PROFILE (YAML):\n"
        + profile_yaml
        + "\n\nEXTRA CONTEXT (free text):\n"
        + (extra_context or "(none)")
    )
    raw = call(system=SYSTEM, user=user, cache_system=False, max_tokens=12000)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = [ln for ln in cleaned.splitlines() if not ln.startswith("```")]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {}
        return json.loads(match.group(0))
