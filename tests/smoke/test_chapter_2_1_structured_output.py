import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_1_structured_output",
    ROOT / "chapters" / "stage2-agent-core" / "structured_output.py",
)
structured_output = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(structured_output)


def test_chapter_module_imports():
    assert structured_output.CHAPTER_ID == "2.1-structured-output"
    assert callable(structured_output.run_minimal_path)


def test_valid_plan_passes():
    plan = {
        "action": "calculator",
        "arguments": {"expression": "2 + 2"},
        "confidence": 0.9,
    }
    assert structured_output.validate_plan(plan) == (True, [])


def test_missing_field_fails():
    plan = {"action": "calculator", "arguments": {}}
    valid, errors = structured_output.validate_plan(plan)
    assert not valid
    assert any("confidence" in error for error in errors)


@pytest.mark.parametrize(
    ("field", "value"),
    [("arguments", []), ("confidence", "high"), ("confidence", True)],
)
def test_wrong_field_type_fails(field, value):
    plan = {"action": "calculator", "arguments": {}, "confidence": 0.5}
    plan[field] = value
    valid, errors = structured_output.validate_plan(plan)
    assert not valid
    assert any(field in error for error in errors)


def test_repair_json_extracts_markdown_fence():
    text = 'Result:\n```json\n{"action": "lookup_city", "arguments": {}, "confidence": 0.8}\n```\nDone.'
    assert structured_output.repair_json(text) == {
        "action": "lookup_city",
        "arguments": {},
        "confidence": 0.8,
    }


def test_repair_json_rejects_invalid_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        structured_output.repair_json('```json\n{"action": }\n```')


def test_repair_json_rejects_non_object_json():
    with pytest.raises(ValueError, match="JSON object"):
        structured_output.repair_json("[1, 2, 3]")


def test_run_minimal_path_compares_valid_and_invalid_plans():
    result = structured_output.run_minimal_path()
    assert result["chapter"] == structured_output.CHAPTER_ID
    assert result["valid_plan"]["valid"] is True
    assert result["valid_plan"]["errors"] == []
    assert result["invalid_plan"]["valid"] is False
    assert result["invalid_plan"]["errors"]
    json.dumps(result)


def test_main_prints_pretty_json(capsys):
    structured_output.main()
    output = capsys.readouterr().out
    assert output.startswith('{\n  "chapter":')
    assert json.loads(output)["chapter"] == structured_output.CHAPTER_ID
