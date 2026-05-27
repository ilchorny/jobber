"""Extract requirements from a JD."""
from __future__ import annotations

import json

from .llm import call

SYSTEM = """\
You extract requirements from a job description. Output ONLY valid JSON with this shape:

{
  "company": "",
  "role_title": "",
  "responsibilities": [
    { "id": "R1", "text": "", "keywords": [] }
  ],
  "required_quals": [
    { "id": "Q1", "text": "", "keywords": [] }
  ],
  "preferred_quals": [
    { "id": "P1", "text": "", "keywords": [] }
  ],
  "role_emphasis": ""
}

Rules:
- Number responsibilities R1..Rn, required Q1..Qn, preferred P1..Pn in source order.
- For each item, extract the key noun phrases / verb phrases as `keywords` (lowercase, deduplicated).
- Preserve the JD's exact vocabulary in `keywords` (verbatim phrases, not paraphrases).
- If a requirement is a list of domains (e.g. "basecalling, variant calling, error modeling"), keep them as separate keywords.
- Do not invent quals that are not present.
"""


def extract(jd_text: str) -> dict:
    raw = call(system=SYSTEM, user=jd_text, cache_system=False, max_tokens=4000)
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
