"""Achievements DB tests (no LLM)."""
from __future__ import annotations

import json

import pytest

from jobber import achievements as ach


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBBER_HOME", str(tmp_path / "jobber"))
    yield


def test_load_returns_empty_when_missing():
    data = ach.load()
    assert data["schema_version"] == ach.SCHEMA_VERSION
    assert data["roles"] == []
    assert data["achievements"] == []


def test_write_and_load_roundtrip():
    data = {
        "roles": [{"id": "acme_swe", "company": "Acme", "title": "SWE", "dates": "2020-2024"}],
        "achievements": [
            {
                "id": "acme_built_thing",
                "role_id": "acme_swe",
                "text": "Built the thing.",
                "attribution": "personally_built",
                "keywords": ["python", "platform"],
                "evidence_citation": "",
            }
        ],
        "publications": [],
        "patents": [],
        "education": [],
    }
    path = ach.save(data)
    assert path.exists()
    loaded = ach.load()
    assert loaded["achievements"][0]["id"] == "acme_built_thing"
    assert loaded["generated_at"] is not None


def test_validate_catches_unknown_attribution():
    data = {
        "roles": [{"id": "r1"}],
        "achievements": [
            {"id": "a1", "role_id": "r1", "attribution": "magically_appeared"},
        ],
    }
    problems = ach.validate(data)
    assert any("unknown attribution" in p for p in problems)


def test_validate_catches_dangling_role_ref():
    data = {
        "roles": [{"id": "r1"}],
        "achievements": [
            {"id": "a1", "role_id": "ghost"},
        ],
    }
    problems = ach.validate(data)
    assert any("ghost" in p for p in problems)


def test_validate_catches_duplicate_ids():
    data = {
        "achievements": [
            {"id": "a1", "attribution": "personally_built"},
            {"id": "a1", "attribution": "led_org"},
        ],
    }
    problems = ach.validate(data)
    assert any("duplicate" in p for p in problems)


def test_as_prompt_json_strips_empty_and_notes():
    data = {
        "roles": [{"id": "r1", "company": "Acme", "title": "", "dates": ""}],
        "achievements": [
            {
                "id": "a1",
                "role_id": "r1",
                "text": "Built it.",
                "attribution": "personally_built",
                "keywords": [],
                "notes": "internal note that should not leak",
                "evidence_citation": "",
            }
        ],
    }
    out = ach.as_prompt_json(data)
    payload = json.loads(out)
    assert "internal note" not in out
    assert payload["achievements"][0]["text"] == "Built it."
    # Empty keywords and empty evidence_citation should be stripped.
    assert "keywords" not in payload["achievements"][0]
    assert "evidence_citation" not in payload["achievements"][0]
