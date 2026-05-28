"""Tone profile module tests (no LLM)."""
from __future__ import annotations

import json

import pytest

from jobber import tone


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBBER_HOME", str(tmp_path / "jobber"))
    yield


def test_load_empty_when_missing():
    data = tone.load()
    assert data["schema_version"] == tone.SCHEMA_VERSION
    assert data["openers"] == []
    assert data["recurring_phrases"] == []
    assert data["tone_descriptor"] == ""


def test_save_load_roundtrip():
    data = {
        "tone_descriptor": "Matter-of-fact and thesis-driven.",
        "openers": ["The assay is necessary but not sufficient."],
        "recurring_phrases": ["I would welcome the chance to discuss"],
        "things_avoided": ["I am writing to express interest"],
    }
    tone.save(data)
    loaded = tone.load()
    assert loaded["tone_descriptor"] == "Matter-of-fact and thesis-driven."
    assert loaded["openers"] == ["The assay is necessary but not sufficient."]
    assert loaded["generated_at"] is not None


def test_as_prompt_text_renders_populated_profile():
    data = {
        "tone_descriptor": "Matter-of-fact.",
        "openers": ["Thesis sentence one.", "Thesis sentence two."],
        "recurring_phrases": ["I would welcome the chance"],
        "things_avoided": ["I am writing to express interest"],
        "sentence_rhythm": "Short, declarative.",
        "vocabulary_notes": "Plain Anglo-Saxon.",
        "section_pivots": [],
        "closers": [],
    }
    out = tone.as_prompt_text(data)
    assert "Matter-of-fact." in out
    assert "Thesis sentence one." in out
    assert "I would welcome the chance" in out
    assert "DO NOT USE" in out
    assert "I am writing to express interest" in out


def test_as_prompt_text_handles_empty():
    out = tone.as_prompt_text(dict(tone.EMPTY))
    assert "no tone profile" in out.lower()
