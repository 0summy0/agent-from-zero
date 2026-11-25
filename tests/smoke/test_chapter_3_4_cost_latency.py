import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_3_4_cost_latency",
    ROOT / "chapters" / "stage3-reliability" / "cost_latency.py",
)
cost_latency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cost_latency)


def test_chapter_module_and_result_contract():
    assert cost_latency.CHAPTER_ID == "3.4-cost-latency"
    assert callable(cost_latency.run_minimal_path)
    result = cost_latency.run_minimal_path()
    assert result["first_call"]["cache_hit"] is False
    assert result["cached_call"]["cache_hit"] is True
    assert result["cached_call"]["response"] == result["first_call"]["response"]
    assert result["cached_call"]["cost_usd"] < result["first_call"]["cost_usd"]
    assert result["cached_call"]["latency_ms"] < result["first_call"]["latency_ms"]
    assert result["routing_example"]["model"] == "strong_model"
    json.dumps(result)


def test_token_cache_hit_and_key_normalization():
    cache = cost_latency.TokenCache()
    cache.set("  Explain\tresponse\ncaching.  ", "cached answer")
    assert cache.get("Explain response caching.") == "cached answer"
    assert "Explain   response caching." in cache
    assert cache.stats() == {"entries": 1, "hits": 1, "misses": 0}


def test_token_cache_miss_and_case_preservation():
    cache = cost_latency.TokenCache()
    assert cache.get("Explain caching") is None
    cache.set("Explain caching", "answer")
    assert cache.get("explain caching") is None
    assert cache.stats() == {"entries": 1, "hits": 0, "misses": 2}


def test_model_router_rules():
    router = cost_latency.ModelRouter()
    assert router.route("What is 2 + 2?") == "cheap_model"
    assert router.route("Compare two database designs.") == "strong_model"
    assert router.route("请设计一个容错架构。") == "strong_model"
    assert router.route("word " * 21) == "strong_model"
    assert router.route_decision("What is 2 + 2?")["reason"] == "short_simple_request"
    assert router.route_decision("Compare two designs.")["reason"] == "complexity_marker"


def test_simulated_cost_and_latency_calculations():
    assert cost_latency.estimate_tokens("12345678") == 2
    assert cost_latency.estimate_cost_usd("cheap_model", 10, 5) == 0.000003
    assert cost_latency.estimate_latency_ms("cheap_model", 10, 5) == 6.8
    assert cost_latency.estimate_cost_usd("strong_model", 10, 5) == 0.0000125
    assert cost_latency.estimate_latency_ms("strong_model", 10, 5) == 20.05
    assert cost_latency.estimate_cost_usd("cheap_model", 10, 5, True) == 0.0
    assert cost_latency.estimate_latency_ms("cheap_model", 10, 5, True) == 0.25


def test_invalid_counts_and_unknown_model_are_rejected():
    with pytest.raises(ValueError):
        cost_latency.estimate_cost_usd("cheap_model", -1, 0)
    with pytest.raises(ValueError):
        cost_latency.estimate_latency_ms("unknown", 1, 1)
    with pytest.raises(ValueError):
        cost_latency.ModelRouter(complexity_threshold=0)


def test_minimal_path_is_deterministic_and_main_prints_json(capsys):
    first = cost_latency.run_minimal_path()
    second = cost_latency.run_minimal_path()
    assert first == second
    assert first["cache_stats"] == {"entries": 1, "hits": 1, "misses": 1}
    cost_latency.main()
    printed = capsys.readouterr().out
    assert json.loads(printed) == first
