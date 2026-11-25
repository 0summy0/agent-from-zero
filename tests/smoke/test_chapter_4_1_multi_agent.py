import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_4_1_multi_agent",
    ROOT / "chapters" / "stage4-orchestration" / "multi_agent.py",
)
multi_agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(multi_agent)


def test_chapter_module_and_result_contract():
    assert multi_agent.CHAPTER_ID == "4.1-multi-agent"
    assert callable(multi_agent.run_minimal_path)
    result = multi_agent.run_minimal_path()
    assert set(result) == {"draft", "critique", "final", "rounds"}
    json.dumps(result)


def test_one_revision_satisfies_the_critic():
    result = multi_agent.run_minimal_path()
    assert result["rounds"] == 2
    assert "角色分工" in result["draft"]
    assert "独立检查" not in result["draft"]
    assert "独立检查" in result["final"]
    assert result["critique"]["satisfied"] is True
    assert result["critique"]["missing_points"] == []


def test_no_revision_when_the_first_draft_is_complete():
    result = multi_agent.run_minimal_path("请说明角色分工。", ["角色分工"])
    assert result["rounds"] == 1
    assert result["draft"] == result["final"]
    assert result["critique"]["satisfied"] is True


def test_round_limit_stops_an_unfinished_revision():
    result = multi_agent.run_minimal_path(
        "请说明三个要点。",
        ["角色分工", "独立检查", "终止条件"],
    )
    assert result["rounds"] == 2
    assert "终止条件" not in result["final"]
    assert result["critique"]["satisfied"] is False
    assert result["critique"]["missing_points"] == ["终止条件"]


@pytest.mark.parametrize("user_input", ["", " \t\n"])
def test_empty_request_is_rejected(user_input):
    with pytest.raises(ValueError, match="must not be empty"):
        multi_agent.run_minimal_path(user_input)


def test_deterministic_result_and_main_prints_json(capsys):
    first = multi_agent.run_minimal_path()
    second = multi_agent.run_minimal_path()
    assert first == second

    multi_agent.main()
    printed = capsys.readouterr().out
    assert json.loads(printed) == first
