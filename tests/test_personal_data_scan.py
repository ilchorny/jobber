"""Privacy guard: the pre-commit personal-data scanner."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNER = REPO_ROOT / "scripts" / "personal_data_scan.py"


def _run(args: list[str], blocklist: str | None, repo_root: Path) -> subprocess.CompletedProcess:
    blocklist_path = repo_root / ".personal-data-blocklist"
    if blocklist is not None:
        blocklist_path.write_text(blocklist)
    else:
        if blocklist_path.exists():
            blocklist_path.unlink()
    return subprocess.run(
        [sys.executable, str(SCANNER), *args],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )


def test_no_blocklist_passes(tmp_path: Path):
    # Create a minimal copy of the scanner in a tmp root so we don't write to the real repo.
    repo_root = tmp_path
    (repo_root / "scripts").mkdir()
    (repo_root / "scripts" / "personal_data_scan.py").write_text(SCANNER.read_text())
    target = repo_root / "file.txt"
    target.write_text("hello world")
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "personal_data_scan.py"), str(target)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0


def test_literal_match_blocks(tmp_path: Path):
    repo_root = tmp_path
    (repo_root / "scripts").mkdir()
    (repo_root / "scripts" / "personal_data_scan.py").write_text(SCANNER.read_text())
    (repo_root / ".personal-data-blocklist").write_text("secret-string\n")
    target = repo_root / "file.txt"
    target.write_text("oops secret-string leaked")
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "personal_data_scan.py"), str(target)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode != 0
    assert "literal" in result.stderr.lower()


def test_regex_match_blocks(tmp_path: Path):
    repo_root = tmp_path
    (repo_root / "scripts").mkdir()
    (repo_root / "scripts" / "personal_data_scan.py").write_text(SCANNER.read_text())
    (repo_root / ".personal-data-blocklist").write_text(r"re:\b\d{3}-\d{2}-\d{4}\b" + "\n")
    target = repo_root / "file.txt"
    target.write_text("don't put 123-45-6789 in commits")
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "personal_data_scan.py"), str(target)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode != 0
    assert "regex" in result.stderr.lower()
