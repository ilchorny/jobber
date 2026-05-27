"""jobber CLI."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import draft as draft_mod
from . import extract, jd, library, profile, render, report
from .llm import LLMConfig

app = typer.Typer(
    help="Generate tailored resumes and cover letters from a JD and a folder of your past materials.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


# ----------------------------- helpers ------------------------------- #


def _slug(text: str, *, maxlen: int = 40) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:maxlen] or "unknown"


def _app_id(company: str, role: str, today: str | None = None) -> str:
    today = today or date.today().isoformat()
    return f"{_slug(company)}_{_slug(role)}_{today}"


def _app_dir(app_id: str) -> Path:
    return profile.home_dir() / "applications" / app_id


def _require_app(app_id: str) -> Path:
    p = _app_dir(app_id)
    if not p.exists():
        console.print(f"[red]Application not found:[/red] {app_id}")
        console.print(f"Expected at: {p}")
        raise typer.Exit(2)
    return p


# ----------------------------- commands ------------------------------- #


@app.command()
def init(
    library_path: Path | None = typer.Option(
        None, "--library", help="Path to a folder of your past resumes/cover letters/JDs/notes."
    ),
    seed_from_claude_memory: bool = typer.Option(
        False,
        "--seed-from-claude-memory",
        help="Read ~/.claude/projects/*/memory/*.md once and seed your local profile.yaml. Opt-in.",
    ),
):
    """Create ~/.jobber/, optionally seed profile from Claude memory, and link a library folder."""
    # If a library is provided, create the home WITHOUT pre-populating library subdirs
    # so we can replace the empty library/ with a symlink. Otherwise create the
    # standard subdir layout so the user can drop files in.
    home = profile.ensure_home(with_library_subdirs=library_path is None)
    console.print(f"[green]Created[/green] {home}")

    if seed_from_claude_memory:
        files = profile.seed_from_claude_memory()
        if files:
            console.print(
                f"[green]Seeded[/green] profile.yaml from {len(files)} Claude memory file(s)."
            )
        else:
            console.print("[yellow]No Claude memory files found.[/yellow] Wrote an empty template.")
            profile.write_template()
    else:
        profile.write_template()
        console.print("[green]Wrote[/green] empty profile.yaml template at " f"{profile.profile_path()}")

    if library_path is not None:
        library_path = library_path.expanduser().resolve()
        if not library_path.exists():
            console.print(f"[red]Library path does not exist:[/red] {library_path}")
            raise typer.Exit(2)
        target = home / "library"
        # Replace any existing empty library/ with a symlink. If the user already
        # has content, refuse rather than clobber.
        if target.is_symlink():
            target.unlink()
        elif target.is_dir():
            if any(target.iterdir()):
                console.print(
                    f"[yellow]{target} already has content; leaving it in place. "
                    "Move your library files into it manually if needed.[/yellow]"
                )
                return
            target.rmdir()
        target.symlink_to(library_path)
        console.print(f"[green]Linked[/green] {target} -> {library_path}")
    else:
        console.print(
            "[yellow]No --library given.[/yellow] Drop your past resumes/cover letters/JDs into "
            f"{home / 'library'} (subfolders: resumes, cover_letters, jds, notes)."
        )


@app.command()
def apply(
    jd_input: str = typer.Argument(..., help="JD URL, path to a JD file, or raw JD text."),
    context: str = typer.Option(
        "",
        "--context",
        "-c",
        help="Free-text context that biases the draft: target thesis, recruiter intel, etc.",
    ),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Skip PDF rendering."),
    draft_model: str | None = typer.Option(
        None, "--draft-model", help="Override the LLM used for final drafting."
    ),
):
    """Run the full pipeline: JD → mapping → cover letter + resume + report → PDFs."""
    profile.ensure_home()

    console.print("[bold]1.[/bold] Ingesting JD…")
    jd_text = jd.ingest(jd_input)
    if not jd_text.strip():
        console.print("[red]Empty JD.[/red]")
        raise typer.Exit(2)

    console.print("[bold]2.[/bold] Indexing your library…")
    idx = library.build_index()
    if not idx.roles:
        console.print(
            "[yellow]Library index is empty.[/yellow] Add files to "
            f"{profile.home_dir() / 'library'} and re-run."
        )
        raise typer.Exit(2)

    console.print("[bold]3.[/bold] Extracting requirements…")
    requirements = extract.extract(jd_text)
    company = (requirements.get("company") or "unknown").strip()
    role_title = (requirements.get("role_title") or "role").strip()
    app_id = _app_id(company, role_title)
    out_dir = _app_dir(app_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "jd.md").write_text(jd_text + "\n")
    (out_dir / "requirements.json").write_text(json.dumps(requirements, indent=2))
    if context:
        (out_dir / "context.md").write_text(context.strip() + "\n")

    console.print(f"[bold]4.[/bold] Mapping requirements to evidence…  ({app_id})")
    prof = profile.load()
    mapping = draft_mod.__dict__  # placeholder so linter doesn't whine; replaced below
    from . import map as map_mod
    mapping = map_mod.build_mapping(
        requirements=requirements,
        library_yaml=idx.as_prompt_yaml(),
        profile_yaml=prof.as_yaml(),
        extra_context=context,
    )
    (out_dir / "mapping.json").write_text(json.dumps(mapping, indent=2))

    console.print("[bold]5.[/bold] Writing mapping report…")
    rep_md = report.write_report(
        company=company,
        role_title=role_title,
        requirements=requirements,
        mapping=mapping,
    )
    (out_dir / "mapping_report.md").write_text(rep_md)

    cfg = LLMConfig()
    draft_m = draft_model or cfg.draft_model

    console.print("[bold]6.[/bold] Drafting cover letter…")
    cover = draft_mod.draft_cover_letter(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=idx.as_prompt_yaml(),
        profile_yaml=prof.as_yaml(),
        extra_context=context,
        model=draft_m,
    )
    (out_dir / "cover_letter.md").write_text(cover + "\n")

    console.print("[bold]7.[/bold] Drafting resume…")
    res = draft_mod.draft_resume(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=idx.as_prompt_yaml(),
        profile_yaml=prof.as_yaml(),
        extra_context=context,
        model=draft_m,
    )
    (out_dir / "resume.md").write_text(res + "\n")

    if not no_pdf:
        console.print("[bold]8.[/bold] Rendering PDFs…")
        for name in ("cover_letter", "resume", "mapping_report"):
            md = out_dir / f"{name}.md"
            pdf = out_dir / f"{name}.pdf"
            try:
                render.md_to_pdf(md, pdf)
                console.print(f"   [green]wrote[/green] {pdf}")
            except Exception as exc:
                console.print(f"   [yellow]skipped[/yellow] {pdf}: {exc}")

    _summary(app_id, mapping)


def _summary(app_id: str, mapping: dict):
    console.print()
    console.print(f"[bold green]Done.[/bold green] Outputs in {_app_dir(app_id)}")

    counts = {"strong": 0, "moderate": 0, "weak": 0, "none": 0}
    for m in mapping.get("mappings") or []:
        fit = m.get("fit", "")
        if fit in counts:
            counts[fit] += 1

    table = Table(title="Fit summary", show_header=True, header_style="bold")
    table.add_column("Fit")
    table.add_column("Count", justify="right")
    for k in ("strong", "moderate", "weak", "none"):
        table.add_row(k, str(counts[k]))
    console.print(table)

    gaps = mapping.get("honest_gaps") or []
    if gaps:
        console.print(
            f"[yellow]Honest gaps flagged:[/yellow] "
            + ", ".join(g.get("keyword", "") for g in gaps if g.get("keyword"))
        )


@app.command(name="map")
def map_cmd(
    app_id: str = typer.Argument(..., help="Application id under ~/.jobber/applications/."),
):
    """Open the saved mapping.json in $EDITOR for re-ranking. Run `jobber draft` afterwards."""
    out_dir = _require_app(app_id)
    mp = out_dir / "mapping.json"
    if not mp.exists():
        console.print(f"[red]No mapping.json at {mp}[/red]")
        raise typer.Exit(2)
    import os
    editor = os.environ.get("EDITOR", "vim")
    subprocess.run([editor, str(mp)], check=False)
    console.print(f"[green]Saved edits to[/green] {mp}. Run `jobber draft {app_id}` to re-render.")


@app.command()
def draft(
    app_id: str = typer.Argument(...),
    draft_model: str | None = typer.Option(None, "--draft-model"),
):
    """Re-run the cover-letter + resume drafting using the existing mapping.json."""
    out_dir = _require_app(app_id)
    try:
        requirements = json.loads((out_dir / "requirements.json").read_text())
        mapping = json.loads((out_dir / "mapping.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        console.print(f"[red]Could not load requirements/mapping:[/red] {exc}")
        raise typer.Exit(2)

    jd_text = (out_dir / "jd.md").read_text() if (out_dir / "jd.md").exists() else ""
    context = (out_dir / "context.md").read_text() if (out_dir / "context.md").exists() else ""

    idx = library.build_index()
    prof = profile.load()

    cover = draft_mod.draft_cover_letter(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=idx.as_prompt_yaml(),
        profile_yaml=prof.as_yaml(),
        extra_context=context,
        model=draft_model,
    )
    (out_dir / "cover_letter.md").write_text(cover + "\n")

    res = draft_mod.draft_resume(
        jd_text=jd_text,
        requirements=requirements,
        mapping=mapping,
        library_yaml=idx.as_prompt_yaml(),
        profile_yaml=prof.as_yaml(),
        extra_context=context,
        model=draft_model,
    )
    (out_dir / "resume.md").write_text(res + "\n")
    console.print(f"[green]Re-drafted[/green] cover_letter.md and resume.md in {out_dir}")


@app.command(name="render")
def render_cmd(app_id: str = typer.Argument(...)):
    """Re-render PDFs from current .md files in the application directory."""
    out_dir = _require_app(app_id)
    for name in ("cover_letter", "resume", "mapping_report"):
        md = out_dir / f"{name}.md"
        if not md.exists():
            continue
        pdf = out_dir / f"{name}.pdf"
        try:
            render.md_to_pdf(md, pdf)
            console.print(f"[green]wrote[/green] {pdf}")
        except Exception as exc:
            console.print(f"[yellow]skipped[/yellow] {pdf}: {exc}")


@app.command(name="claude-install")
def claude_install():
    """Install the Claude Code skill wrapper and permission allowlist."""
    pkg_root = Path(__file__).resolve().parent.parent.parent
    src_skill = pkg_root / "claude" / "SKILL.md"
    if not src_skill.exists():
        console.print(f"[red]Could not find skill template at {src_skill}[/red]")
        raise typer.Exit(2)
    dst_dir = Path.home() / ".claude" / "skills" / "jobber"
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_skill, dst_dir / "SKILL.md")
    console.print(f"[green]Installed[/green] {dst_dir / 'SKILL.md'}")

    # Allowlist `jobber` in Claude Code settings.
    settings_path = Path.home() / ".claude" / "settings.json"
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except json.JSONDecodeError:
            console.print(
                f"[yellow]Could not parse {settings_path}; leaving it alone.[/yellow]"
            )
            return
    permissions = settings.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    rule = "Bash(jobber:*)"
    if rule not in allow:
        allow.append(rule)
        settings_path.write_text(json.dumps(settings, indent=2))
        console.print(f"[green]Allowlisted[/green] `{rule}` in {settings_path}")
    else:
        console.print(f"[green]Already allowlisted[/green] `{rule}`")

    console.print()
    console.print(
        "From inside Claude Code you can now invoke `/jobber` or just ask "
        '"draft an application for this JD: <url>" and Claude will call the CLI.'
    )


if __name__ == "__main__":
    app()
