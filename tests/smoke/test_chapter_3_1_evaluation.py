import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_3_1_evaluation",
    ROOT / "chapters" / "stage3-reliability" / "evaluation.py",
)
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


def test_chapter_module_imports():
    assert evaluation.CHAPTER_ID == "3.1-evaluation"
    assert callable(evaluation.run_minimal_path)


def test_exact_match_accepts_case_and_whitespace_normalization():
    assert evaluation.exact_match("  PARIS  ", "Paris")
    assert evaluation.exact_match("New   York", "new york")


def test_exact_match_accepts_aliases_but_rejects_wrong_answers():
    assert evaluation.exact_match("four", "4", aliases=["4", "four"])
    assert not evaluation.exact_match("five", "4", aliases=["four"])
    assert not evaluation.exact_match("Paris, France", "Paris")


def test_contains_expected_is_case_insensitive():
    assert evaluation.contains_expected("The answer is PARIS.", "paris")
    assert not evaluation.contains_expected("The answer is Lyon.", "Paris")


def test_evaluate_reports_per_item_results_and_pass_rate():
    dataset = [
        {"id": "a", "input": "2+2?", "expected_answer": "4", "aliases": ["four"]},
        {"id": "b", "input": "Capital?", "expected_answer": "Paris", "aliases": []},
    ]
    report = evaluation.evaluate(dataset, ["FOUR", "Lyon"])
    assert report["total"] == 2
    assert report["passed"] == 1
    assert report["pass_rate"] == 0.5
    assert [item["passed"] for item in report["results"]] == [True, False]
    assert report["results"][0]["prediction"] == "FOUR"
    json.dumps(report)


def test_empty_dataset_is_rejected():
    with pytest.raises(ValueError, match="dataset must not be empty"):
        evaluation.evaluate([], [])


def test_answer_count_must_match_dataset():
    with pytest.raises(ValueError, match="one answer per dataset item"):
        evaluation.evaluate(evaluation.EVALUATION_SET, ["4"])


def test_minimal_path_is_deterministic_and_json_serializable():
    first = evaluation.run_minimal_path()
    second = evaluation.run_minimal_path()
    assert first == second
    assert first["dataset_size"] == 4
    assert first["pass_rate"] == 0.75
    assert [item["passed"] for item in first["results"]] == [True, True, False, True]
    json.dumps(first)
