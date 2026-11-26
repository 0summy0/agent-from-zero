import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_1_3_attention",
    ROOT / "chapters" / "stage1-how-lm-works" / "attention.py",
)
attention = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(attention)


def test_chapter_module_imports():
    assert attention.CHAPTER_ID == "1.3-attention"
    assert callable(attention.run_minimal_path)


def test_each_attention_row_is_normalized():
    result = attention.run_minimal_path()
    for demo in ("full_window", "context_window"):
        rows = result[demo]["rows"]
        assert all(math.isclose(sum(row["attention_weights"]), 1.0, abs_tol=1e-6) for row in rows)


def test_output_dimensions_match_the_toy_vectors():
    result = attention.run_minimal_path()
    dimension = result["vector_dimension"]
    for demo in ("full_window", "context_window"):
        rows = result[demo]["rows"]
        assert all(len(row["context_vector"]) == dimension for row in rows)
        assert all(len(row["scaled_scores"]) == len(result[demo]["kept_tokens"]) for row in rows)
        assert all(
            len(row["attention_weights"]) == len(result[demo]["kept_tokens"]) for row in rows
        )


def test_truncation_keeps_the_most_recent_tokens_in_order():
    result = attention.run_minimal_path()
    truncated = result["context_window"]
    assert truncated["window_size"] == 3
    assert truncated["kept_tokens"] == ["small", "models", "too"]
    assert truncated["dropped_tokens"] == ["I", "like"]
    assert len(truncated["rows"]) == 3
    assert attention.truncate_to_recent_tokens(attention.TOY_TOKENS, 8) == attention.TOY_TOKENS


@pytest.mark.parametrize("window_size", [0, -1, 1.5, True])
def test_invalid_window_size_is_rejected(window_size):
    with pytest.raises(ValueError):
        attention.truncate_to_recent_tokens(attention.TOY_TOKENS, window_size)


def test_output_is_json_serializable_and_deterministic():
    first = attention.run_minimal_path()
    second = attention.run_minimal_path()
    assert first == second
    assert json.loads(json.dumps(first)) == first


def test_softmax_handles_large_scores_stably():
    weights = attention.softmax([1000.0, 1000.0])
    assert weights == [0.5, 0.5]
    assert math.isclose(sum(weights), 1.0, abs_tol=1e-12)
