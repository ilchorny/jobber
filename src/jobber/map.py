"""Map JD requirements to evidence in the library."""
from __future__ import annotations

import json

from .llm import call


SYSTEM = """\
You map each JD requirement to evidence from the user's library.

You will receive:
  1. A JD requirements JSON (responsibilities, required quals, preferred quals).
  2. A library index in YAML (roles, publications, personal_projects).
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
          "role_id": "",                # from library index, or ""
          "bullet_text": "",             # quoted from library (may be lightly tightened)
          "attribution": "personally_built | directed_team_reviewed | led_org | co_author | participant"
        }
      ],
      "include_in_cover_letter": true,
      "include_in_resume": true,
      "stretch_notes": ""               # if fit is "none" or "weak", explain why
    }
  ],
  "honest_gaps": [
    {
      "keyword": "",                    # e.g. "methylation"
      "reason": ""                      # e.g. "Not in the user's background per profile.stretches_to_avoid"
    }
  ],
  "thesis_candidates": [
    "Short candidate opening thesis for the cover letter, one sentence each"
  ]
}

Rules:
- Use ONLY evidence that appears in the library index. Do not invent bullets or roles.
- Respect attribution rigorously. If the profile says a project was directed_team_reviewed, do not present it as personally_built.
- For each JD keyword that is also in profile.stretches_to_avoid, add an entry to honest_gaps and set fit to "none" for any responsibility that depends on it.
- Default include_in_resume=true for any "strong" or "moderate" match. include_in_cover_letter=true for the top 5-8 strongest matches.
- Produce 2-3 thesis_candidates anchored in the strongest matches.
"""


def build_mapping(
    *,
    requirements: dict,
    library_yaml: str,
    profile_yaml: str,
    extra_context: str = "",
) -> dict:
    user = (
        "JD REQUIREMENTS (JSON):\n"
        + json.dumps(requirements, indent=2)
        + "\n\nLIBRARY (YAML):\n"
        + library_yaml
        + "\n\nUSER PROFILE (YAML):\n"
        + profile_yaml
        + "\n\nEXTRA CONTEXT (free text, may be empty):\n"
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
