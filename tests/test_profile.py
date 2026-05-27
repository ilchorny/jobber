"""Profile load/save tests (no LLM)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from jobber import profile


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBBER_HOME", str(tmp_path / "jobber"))
    yield


def test_ensure_home_creates_subdirs_when_requested():
    home = profile.ensure_home(with_library_subdirs=True)
    for sub in ["library/resumes", "library/cover_letters", "library/jds", "library/notes", "cache", "applications"]:
        assert (home / sub).is_dir()


def test_ensure_home_leaves_library_empty_by_default():
    home = profile.ensure_home()
    # library/ exists but is empty; cache/ and applications/ exist
    assert (home / "library").is_dir()
    assert (home / "cache").is_dir()
    assert (home / "applications").is_dir()
    assert not any((home / "library").iterdir())


def test_write_template_empty():
    p = profile.write_template()
    assert p.exists()
    assert "voice:" in p.read_text()


def test_load_returns_empty_when_missing():
    prof = profile.load()
    assert prof.raw == {}
    assert prof.name == ""
