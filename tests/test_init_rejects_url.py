"""init must reject URLs in --library and explain the Claude Code path.

Critical invariant: rejection must NOT clobber an existing profile.yaml.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from jobber.cli import app


def test_init_rejects_drive_url_without_clobbering(tmp_path, monkeypatch):
    home = tmp_path / "jobber"
    monkeypatch.setenv("JOBBER_HOME", str(home))
    home.mkdir()
    # Pretend the user already had a real, populated profile.
    seeded = home / "profile.yaml"
    seeded.write_text("# my real profile\ncontact:\n  name: Alex Park\n")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--library", "https://drive.google.com/drive/folders/abc123"],
    )
    assert result.exit_code != 0
    assert "URL" in result.stdout or "url" in result.stdout
    # The profile must NOT have been overwritten.
    assert seeded.read_text() == "# my real profile\ncontact:\n  name: Alex Park\n"


def test_init_rejects_http_url(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBBER_HOME", str(tmp_path / "jobber"))
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--library", "https://example.com/some/path"],
    )
    assert result.exit_code != 0


def test_init_rejects_nonexistent_path_without_clobbering(tmp_path, monkeypatch):
    home = tmp_path / "jobber"
    monkeypatch.setenv("JOBBER_HOME", str(home))
    home.mkdir()
    seeded = home / "profile.yaml"
    seeded.write_text("# my real profile\n")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", "--library", str(tmp_path / "does-not-exist")],
    )
    assert result.exit_code != 0
    assert seeded.read_text() == "# my real profile\n"
