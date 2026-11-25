import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_3_react_loop",
    ROOT / "chapters" / "stage2-agent-core" / "react_loop.py",
)
react_loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(react_loop)


def test_chapter_module_imports():
    assert react_loop.CHAPTER_ID == "2.3-react-loop"
    assert callable(react_loop.run_minimal_path)


def test_loop_converges_after_using_both_tools():
    result = react_loop.run_minimal_path()
    tools = [step["action"]["tool"] for step in result["trace"]]

    assert result["status"] == "answered"
    assert result["stop_reason"] == "answered"
    assert tools == ["calculator", "lookup_city", "finish"]
    assert "1152" in result["answer"]
    assert "Shanghai is in China" in result["answer"]


def test_trace_contains_thought_action_and_observation():
    result = react_loop.run_minimal_path()
    tool_steps = result["trace"][:-1]

    assert len(tool_steps) == 2
    for step in tool_steps:
        assert step["thought"]
        assert step["action"]["tool"] in {"calculator", "lookup_city"}
        assert step["action"]["input"]
        assert step["observation"]["ok"] is True
    assert result["trace"][-1]["observation"] is None


def test_max_steps_stops_the_loop():
    result = react_loop.run_react_loop(react_loop.DEFAULT_QUESTION, max_steps=1)

    assert result["stop_reason"] == "max_steps"
    assert result["status"] == "stopped"
    assert result["answer"] is None
    assert len(result["trace"]) == 1
    assert result["trace"][0]["action"]["tool"] == "calculator"


def test_unknown_question_stops_without_calling_tools():
    result = react_loop.run_react_loop("Tell me a joke about penguins.")

    assert result["stop_reason"] == "answered"
    assert len(result["trace"]) == 1
    assert result["trace"][0]["action"]["tool"] == "finish"
    assert "only solve" in result["answer"]


def test_tool_error_stops_safely():
    result = react_loop.run_react_loop("Look up the country of Atlantis.")

    assert result["stop_reason"] == "tool_error"
    assert result["trace"][-1]["observation"]["ok"] is False
    assert "Stopped safely" in result["answer"]


def test_minimal_path_is_deterministic_and_json_serializable():
    first = react_loop.run_minimal_path()
    second = react_loop.run_minimal_path()

    assert first == second
    assert json.loads(json.dumps(first)) == first


@pytest.mark.parametrize("max_steps", [0, -1, True, 1.5])
def test_invalid_max_steps_is_rejected(max_steps):
    with pytest.raises(ValueError):
        react_loop.run_react_loop(react_loop.DEFAULT_QUESTION, max_steps=max_steps)
