import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_1_1_tokenizer",
    ROOT / "chapters" / "stage1-how-lm-works" / "tokenizer.py",
)
tokenizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tokenizer)
TYPES = {
    "string": str,
    "integer": int,
    "boolean": bool,
    "list[string]": list,
    "list[integer]": list,
}


def assert_golden_shape(value, shape, path="result"):
    if isinstance(shape, dict):
        assert isinstance(value, dict), f"{path} must be an object"
        assert set(value) == set(shape), f"{path} fields differ from golden"
        for key, child_shape in shape.items():
            assert_golden_shape(value[key], child_shape, f"{path}.{key}")
        return
    assert type(value) is TYPES[shape], f"{path} must be {shape}"
    if shape == "list[string]":
        assert all(type(item) is str for item in value), f"{path} items must be strings"
    if shape == "list[integer]":
        assert all(type(item) is int for item in value), f"{path} items must be integers"


def test_chapter_module_imports():
    assert tokenizer.CHAPTER_ID == "1.1-tokenizer"
    assert callable(tokenizer.run_minimal_path)


@pytest.mark.requires_network
def test_tokenizer_minimal_path_matches_golden():
    result = tokenizer.run_minimal_path()
    golden = json.loads((ROOT / "tests" / "golden" / "1.1-tokenizer.json").read_text(encoding="utf-8"))
    assert_golden_shape(result, golden)
    assert result["chinese"]["characters"] == 10
    assert result["english"]["characters"] == 25
    for sample in (result["chinese"], result["english"]):
        assert sample["token_count"] == len(sample["token_ids"]) == len(sample["tokens"])
        assert sample["token_count"] > 0
    assert result["token_count_difference"] == result["chinese"]["token_count"] - result["english"]["token_count"]
    assert result["model_weights_downloaded"] is False
