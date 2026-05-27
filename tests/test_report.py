"""Report writer test (no LLM)."""
from __future__ import annotations

from jobber import report


def test_write_report_renders_sections():
    requirements = {
        "responsibilities": [{"id": "R1", "text": "Lead a focused team", "keywords": []}],
        "required_quals": [{"id": "Q1", "text": "10+ years experience", "keywords": []}],
        "preferred_quals": [{"id": "P1", "text": "Open-source contributions", "keywords": []}],
    }
    mapping = {
        "mappings": [
            {
                "requirement_id": "R1",
                "requirement_text": "Lead a focused team",
                "fit": "strong",
                "evidence": [
                    {
                        "role_id": "lumen_staff",
                        "bullet_text": "Led the API platform team (12 engineers)",
                        "attribution": "led_org",
                    }
                ],
                "include_in_cover_letter": True,
                "include_in_resume": True,
                "stretch_notes": "",
            }
        ],
        "honest_gaps": [{"keyword": "Swift", "reason": "Not in background"}],
        "thesis_candidates": ["The hardest part of platform work is the 3am page."],
    }
    out = report.write_report(
        company="Beacon Systems",
        role_title="Principal Engineer",
        requirements=requirements,
        mapping=mapping,
    )
    assert "Beacon Systems" in out
    assert "Principal Engineer" in out
    assert "## 1. Requirements Inventory" in out
    assert "lumen_staff" in out
    assert "Swift" in out
    assert "3am page" in out
