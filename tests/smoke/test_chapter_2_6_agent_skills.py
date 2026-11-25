import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_6_agent_skills",
    ROOT / "chapters" / "stage2-agent-core" / "skills.py",
)
skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(skills)


@pytest.fixture
def library(tmp_path):
    skills.write_skill(
        tmp_path,
        "summarize",
        "summarize",
        "Condense a passage into three factual bullet points.",
        "Read the passage. Return exactly three bullets.",
    )
    skills.write_skill(
        tmp_path,
        "translate",
        "translate",
        "Translate short English text into Chinese.",
        "Translate the input without adding commentary.",
    )
    return skills.SkillLibrary(tmp_path)


def test_chapter_module_imports():
    assert skills.CHAPTER_ID == "2.6-agent-skills"
    assert callable(skills.run_minimal_path)


def test_discovers_two_skills_in_stable_order(library):
    discovered = library.list_skills()
    assert [skill["name"] for skill in discovered] == ["summarize", "translate"]
    assert all(set(skill) == {"name", "description"} for skill in discovered)


def test_loads_specified_skill(library):
    loaded = library.load_skill("translate")
    assert loaded["name"] == "translate"
    assert loaded["description"] == "Translate short English text into Chinese."
    assert loaded["instructions"] == "Translate the input without adding commentary."


def test_missing_skill_raises(library):
    with pytest.raises(KeyError, match="skill not found"):
        library.load_skill("missing")


def test_unloaded_skill_does_not_enter_prompt(library):
    loaded = library.load_skill("summarize")
    prompt = library.render_skill_prompt(loaded)
    assert "summarize" in prompt
    assert "Return exactly three bullets." in prompt
    assert "translate" not in prompt
    assert "Translate the input" not in prompt


def test_minimal_path_is_deterministic_and_serializable():
    first = skills.run_minimal_path()
    second = skills.run_minimal_path()
    assert first == second
    assert json.loads(json.dumps(first)) == first
    assert [skill["name"] for skill in first["discovered_skills"]] == [
        "summarize",
        "translate",
    ]
    assert first["skill_name"] == "summarize"
    assert "translate" not in first["prompt"]
