"""Mapping report writer."""
from __future__ import annotations

from datetime import date


def write_report(
    *,
    company: str,
    role_title: str,
    requirements: dict,
    mapping: dict,
    profile_summary: str = "",
) -> str:
    """Return a Markdown mapping report."""
    today = date.today().isoformat()
    out: list[str] = []
    out.append(f"# JD → Resume / Cover Letter Mapping Report\n")
    out.append(f"**Role:** {role_title or '(unspecified)'}  ")
    out.append(f"**Company:** {company or '(unspecified)'}  ")
    out.append(f"**Date:** {today}\n")
    out.append("---\n")

    # 1. Requirements inventory
    out.append("## 1. Requirements Inventory\n")
    for section, items in (
        ("Responsibilities", requirements.get("responsibilities", [])),
        ("Required Qualifications", requirements.get("required_quals", [])),
        ("Preferred Qualifications", requirements.get("preferred_quals", [])),
    ):
        if not items:
            continue
        out.append(f"### {section}\n")
        out.append("| # | Requirement |")
        out.append("|---|---|")
        for it in items:
            text = (it.get("text") or "").replace("|", "\\|")
            out.append(f"| {it.get('id', '?')} | {text} |")
        out.append("")

    # 2. Evidence mapping
    out.append("## 2. Evidence Mapping\n")
    out.append("| JD ID | Requirement | Evidence | Fit | In Cover Letter | In Resume |")
    out.append("|---|---|---|---|---|---|")
    for m in mapping.get("mappings", []):
        rid = m.get("requirement_id", "?")
        rtext = (m.get("requirement_text") or "")[:140].replace("|", "\\|")
        ev_parts = []
        for ev in m.get("evidence", []) or []:
            role = ev.get("role_id", "")
            bullet = (ev.get("bullet_text") or "").replace("|", "\\|")
            attr = ev.get("attribution", "")
            if role:
                ev_parts.append(f"**{role}** ({attr}): {bullet}")
            else:
                ev_parts.append(f"({attr}): {bullet}")
        ev_str = "<br>".join(ev_parts) or "—"
        fit = m.get("fit", "")
        cl = "Yes" if m.get("include_in_cover_letter") else "No"
        rs = "Yes" if m.get("include_in_resume") else "No"
        out.append(f"| {rid} | {rtext} | {ev_str} | {fit} | {cl} | {rs} |")
    out.append("")

    # 3. Honest gaps
    gaps = mapping.get("honest_gaps") or []
    if gaps:
        out.append("## 3. Honest Gaps (Keywords Deliberately NOT Inserted)\n")
        out.append("| Keyword | Reason |")
        out.append("|---|---|")
        for g in gaps:
            kw = (g.get("keyword") or "").replace("|", "\\|")
            reason = (g.get("reason") or "").replace("|", "\\|")
            out.append(f"| {kw} | {reason} |")
        out.append("")

    # 4. Thesis candidates
    thesis = mapping.get("thesis_candidates") or []
    if thesis:
        out.append("## 4. Thesis Candidates\n")
        for t in thesis:
            out.append(f"- {t}")
        out.append("")

    if profile_summary:
        out.append("## 5. Profile Summary Used for This Draft\n")
        out.append(profile_summary)
        out.append("")

    return "\n".join(out)
