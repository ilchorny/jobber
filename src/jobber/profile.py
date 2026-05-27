"""User profile: voice rules, attribution overrides, contact info.

Lives at ~/.jobber/profile.yaml. Created by `jobber init`. Optionally seeded
from ~/.claude memory files via `jobber init --seed-from-claude-memory`.

Schema is intentionally loose. The LLM consumes the file as YAML text in
system prompts, so users can extend it freely.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_HOME = Path(os.environ.get("JOBBER_HOME", str(Path.home() / ".jobber")))
PROFILE_PATH = DEFAULT_HOME / "profile.yaml"


EMPTY_TEMPLATE = """\
# jobber profile — lives ONLY on your machine. Never committed to a repo.
#
# Fill in or leave blank. Anything missing is just absent from the draft prompts.

contact:
  name: ""              # e.g., "Jane Doe"
  email: ""
  phone: ""
  city: ""

voice:
  # Free-text guidance. The LLM reads this verbatim when drafting.
  # Examples to consider: "thesis-driven, 3-5 paragraphs", "no em-dashes",
  # "open with an opinion not 'I am writing to...'", "350-450 words".
  cover_letter: ""
  resume_summary: ""

constraints:
  # Hard rules. Generated drafts will be checked against these.
  # Example: ["no em-dashes", "no sub-heads in cover letter", "no exclamation points"]
  forbidden_patterns: []

attribution:
  # Map specific projects to attribution language. Keeps drafts honest.
  # Example:
  #   personally_built:
  #     - "Project Foo"
  #   directed_team_reviewed:
  #     - "Project Bar"
  personally_built: []
  directed_team_reviewed: []
  led_org: []

stretches_to_avoid:
  # JD keywords you should NOT shoehorn into drafts. Drafts will flag them as
  # omitted stretches in the mapping report instead.
  # Example: ["methylation", "single-cell", "assembly"]
  - ""
"""


@dataclass
class Profile:
    raw: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return (self.raw.get("contact") or {}).get("name", "") or ""

    @property
    def email(self) -> str:
        return (self.raw.get("contact") or {}).get("email", "") or ""

    def as_yaml(self) -> str:
        return yaml.safe_dump(self.raw, sort_keys=False, allow_unicode=True)


def home_dir() -> Path:
    return Path(os.environ.get("JOBBER_HOME", str(Path.home() / ".jobber")))


def profile_path() -> Path:
    return home_dir() / "profile.yaml"


def ensure_home(*, with_library_subdirs: bool = False) -> Path:
    """Create the jobber home directory.

    By default the `library` directory is left untouched, so the caller (e.g. the
    `init` command) can decide whether to populate it with subdirectories or
    point it at an existing folder via symlink. Set `with_library_subdirs=True`
    to also create the standard `library/{resumes,cover_letters,jds,notes}`
    layout.
    """
    home = home_dir()
    (home / "cache").mkdir(parents=True, exist_ok=True)
    (home / "applications").mkdir(parents=True, exist_ok=True)
    if with_library_subdirs:
        (home / "library" / "resumes").mkdir(parents=True, exist_ok=True)
        (home / "library" / "cover_letters").mkdir(parents=True, exist_ok=True)
        (home / "library" / "jds").mkdir(parents=True, exist_ok=True)
        (home / "library" / "notes").mkdir(parents=True, exist_ok=True)
    else:
        (home / "library").mkdir(parents=True, exist_ok=True)
    return home


def load() -> Profile:
    path = profile_path()
    if not path.exists():
        return Profile(raw={})
    raw = yaml.safe_load(path.read_text()) or {}
    return Profile(raw=raw)


def write_template() -> Path:
    path = profile_path()
    if path.exists():
        return path
    ensure_home()
    path.write_text(EMPTY_TEMPLATE)
    return path


def seed_from_claude_memory(claude_root: Path | None = None) -> list[Path]:
    """Read Claude memory files and write them verbatim into profile.yaml.

    Walks ~/.claude/projects/*/memory/*.md, embeds each file's contents inside
    a single `claude_memory:` block in profile.yaml as a literal multi-line YAML
    string. Downstream prompts read profile.yaml as opaque text, so the exact
    structure is preserved without needing an LLM round-trip during init.

    Returns the list of memory files that were read.
    """
    claude_root = claude_root or (Path.home() / ".claude" / "projects")
    if not claude_root.exists():
        return []
    memory_files = sorted(claude_root.glob("*/memory/*.md"))
    if not memory_files:
        return memory_files

    blocks: list[str] = []
    for mf in memory_files:
        try:
            text = mf.read_text(errors="replace").strip()
        except OSError:
            continue
        blocks.append(f"### {mf.name}\n{text}")

    combined = "\n\n".join(blocks)
    # Indent every line by two spaces for the literal block-scalar in YAML.
    indented = "\n".join("  " + line if line else "  " for line in combined.splitlines())
    body = (
        EMPTY_TEMPLATE.rstrip()
        + "\n\nclaude_memory: |\n"
        + indented
        + "\n"
    )

    ensure_home()
    path = profile_path()
    path.write_text(body)
    return memory_files
