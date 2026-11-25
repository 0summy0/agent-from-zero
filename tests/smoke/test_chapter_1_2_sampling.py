import importlib.util
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_1_2_sampling",
    ROOT / "chapters" / "stage1-how-lm-works" / "sampling.py",
)
sampling = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sampling)


def test_chapter_module_imports():
    assert sampling.CHAPTER_ID == "1.2-sampling"
    assert callable(sampling.run_minimal_path)


def test_distributions_are_normalized():
    result = sampling.run_minimal_path()
    for key in ("base_distribution", "tempered_distribution", "nucleus_distribution"):
        assert math.isclose(sum(result[key].values()), 1.0, abs_tol=1e-5)


def test_temperature_sharpens_distribution():
    model = sampling.build_bigram(sampling.CORPUS)
    base = sampling.next_token_distribution(model, "the")
    cold = sampling.apply_temperature(base, 0.5)
    hot = sampling.apply_temperature(base, 2.0)
    assert max(cold.values()) > max(base.values()) > max(hot.values())


def test_top_p_keeps_enough_mass_and_is_deterministic():
    first = sampling.run_minimal_path()
    second = sampling.run_minimal_path()
    assert first == second
    assert first["nucleus_original_mass"] >= first["top_p"]
    assert first["sampled_token"] in first["nucleus_distribution"]


@pytest.mark.parametrize("temperature", [0, -1])
def test_invalid_temperature_is_rejected(temperature):
    with pytest.raises(ValueError):
        sampling.apply_temperature({"a": 1.0}, temperature)
