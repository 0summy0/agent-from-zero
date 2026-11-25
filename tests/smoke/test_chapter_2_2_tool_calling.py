import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_2_tool_calling",
    ROOT / "chapters" / "stage2-agent-core" / "tool_calling.py",
)
tool_calling = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool_calling)


def test_chapter_module_imports():
    assert tool_calling.CHAPTER_ID == "2.2-tool-calling"
    assert callable(tool_calling.run_minimal_path)


def test_correct_calculation():
    result = tool_calling.execute_plan(
        {
            "action": "calculator",
            "arguments": {"expression": "2 + 3 * 4"},
            "confidence": 0.9,
        }
    )
    assert result == {
        "tool": "calculator",
        "arguments": {"expression": "2 + 3 * 4"},
        "result": 14,
    }


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError, match="unknown tool"):
        tool_calling.call_tool("shell", {})


@pytest.mark.parametrize(
    "arguments",
    [{}, {"expression": 3}, {"expression": "2 + 2", "extra": True}],
)
def test_parameter_errors_are_rejected(arguments):
    with pytest.raises(ValueError, match="invalid arguments|argument expression"):
        tool_calling.call_tool("calculator", arguments)


def test_tool_outside_allowlist_is_rejected():
    plan = {
        "action": "lookup_city",
        "arguments": {"city": "Beijing"},
        "confidence": 0.8,
    }
    with pytest.raises(ValueError, match="not allowed"):
        tool_calling.execute_plan(plan, allowed_tools={"calculator"})


def test_plan_json_and_fence_are_parsed():
    plan = '```json\n{"action":"calculator","arguments":{"expression":"8/2"},"confidence":1}\n```'
    assert tool_calling.execute_plan(plan)["result"] == 4.0


def test_invalid_plan_is_rejected():
    with pytest.raises(ValueError, match="missing fields: confidence"):
        tool_calling.parse_plan({"action": "calculator", "arguments": {}})


def test_lookup_city_uses_local_data():
    result = tool_calling.lookup_city(" beijing ")
    assert result == {"city": "Beijing", "country": "China", "timezone": "Asia/Shanghai"}


def test_calculator_rejects_calls_and_non_arithmetic_syntax():
    with pytest.raises(ValueError, match="numbers and arithmetic"):
        tool_calling.calculator("__import__('os').getcwd()")


def test_run_minimal_path_is_deterministic_and_json_serializable():
    first = tool_calling.run_minimal_path()
    second = tool_calling.run_minimal_path()
    assert first == second
    assert first["tool"] == "calculator"
    assert first["arguments"] == {"expression": "(6 + 2) * 7"}
    assert first["result"] == 56
    json.dumps(first)


def test_main_prints_pretty_json(capsys):
    tool_calling.main()
    output = capsys.readouterr().out
    assert output.startswith('{\n  "chapter":')
    assert json.loads(output)["chapter"] == tool_calling.CHAPTER_ID
