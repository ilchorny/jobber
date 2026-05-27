"""finalize command behavior — does it copy drafts into the library?"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from jobber.cli import app


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "jobber"
    home.mkdir()
    (home / "library" / "resumes").mkdir(parents=True)
    (home / "library" / "cover_letters").mkdir(parents=True)
    (home / "library" / "jds").mkdir(parents=True)
    (home / "applications").mkdir()
    monkeypatch.setenv("JOBBER_HOME", str(home))
    return home


def test_finalize_copies_files(home):
    app_id = "acme_swe_2026-01-01"
    out_dir = home / "applications" / app_id
    out_dir.mkdir()
    (out_dir / "cover_letter.md").write_text("# Cover letter contents")
    (out_dir / "resume.md").write_text("# Resume contents")
    (out_dir / "jd.md").write_text("# JD contents")

    runner = CliRunner()
    result = runner.invoke(app, ["finalize", app_id])
    assert result.exit_code == 0, result.stdout

    assert (home / "library" / "cover_letters" / f"{app_id}_cover_letter.md").read_text() == "# Cover letter contents"
    assert (home / "library" / "resumes" / f"{app_id}_resume.md").read_text() == "# Resume contents"
    assert (home / "library" / "jds" / f"{app_id}_jd.md").read_text() == "# JD contents"


def test_finalize_overwrites_existing(home):
    app_id = "acme_swe_2026-01-01"
    out_dir = home / "applications" / app_id
    out_dir.mkdir()
    (out_dir / "cover_letter.md").write_text("v2")
    (home / "library" / "cover_letters" / f"{app_id}_cover_letter.md").write_text("v1")

    runner = CliRunner()
    result = runner.invoke(app, ["finalize", app_id])
    assert result.exit_code == 0, result.stdout

    assert (home / "library" / "cover_letters" / f"{app_id}_cover_letter.md").read_text() == "v2"


def test_finalize_skips_missing(home):
    app_id = "acme_swe_2026-01-01"
    out_dir = home / "applications" / app_id
    out_dir.mkdir()
    (out_dir / "cover_letter.md").write_text("only this exists")

    runner = CliRunner()
    result = runner.invoke(app, ["finalize", app_id])
    assert result.exit_code == 0, result.stdout
    assert (home / "library" / "cover_letters" / f"{app_id}_cover_letter.md").exists()
    # Resume and JD don't exist in src; should NOT be created.
    assert not (home / "library" / "resumes" / f"{app_id}_resume.md").exists()
    assert not (home / "library" / "jds" / f"{app_id}_jd.md").exists()


def test_finalize_errors_when_app_missing(home):
    runner = CliRunner()
    result = runner.invoke(app, ["finalize", "nonexistent_app"])
    assert result.exit_code != 0
