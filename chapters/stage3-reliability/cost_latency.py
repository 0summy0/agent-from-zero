"""Chapter 3.4: deterministic, simulated token cost and latency controls."""

from __future__ import annotations

import json
import math
import unicodedata

CHAPTER_ID = "3.4-cost-latency"

# These prices and timings are teaching assumptions, not provider billing data.
MODEL_PRICING = {
    "cheap_model": {
        "input_usd_per_million_tokens": 0.10,
        "output_usd_per_million_tokens": 0.40,
        "base_latency_ms": 6.0,
        "input_latency_ms_per_token": 0.02,
        "output_latency_ms_per_token": 0.12,
    },
    "strong_model": {
        "input_usd_per_million_tokens": 0.50,
        "output_usd_per_million_tokens": 1.50,
        "base_latency_ms": 18.0,
        "input_latency_ms_per_token": 0.08,
        "output_latency_ms_per_token": 0.25,
    },
}
CACHE_HIT_LATENCY_MS = 0.25
COMPLEXITY_MARKERS = (
    "analyze",
    "analyse",
    "compare",
    "design",
    "architecture",
    "debug",
    "implement",
    "reason",
    "step by step",
    "trade-off",
    "分析",
    "比较",
    "设计",
    "架构",
    "调试",
    "实现",
    "推理",
    "逐步",
    "权衡",
)


def normalize_prompt(prompt: str) -> str:
    """Collapse whitespace while preserving case, punctuation, and meaning."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string")
    normalized = unicodedata.normalize("NFKC", prompt)
    return " ".join(normalized.split())


def estimate_tokens(text: str) -> int:
    """Use a transparent toy heuristic: roughly one token per four characters."""
    return math.ceil(len(normalize_prompt(text)) / 4)


class TokenCache:
    """An in-memory cache keyed by normalized prompt text."""

    def __init__(self):
        self._responses: dict[str, str] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def normalize_key(prompt: str) -> str:
        return normalize_prompt(prompt)

    def get(self, prompt: str) -> str | None:
        key = self.normalize_key(prompt)
        if key in self._responses:
            self.hits += 1
            return self._responses[key]
        self.misses += 1
        return None

    def set(self, prompt: str, response: str) -> None:
        if not isinstance(response, str):
            raise TypeError("response must be a string")
        self._responses[self.normalize_key(prompt)] = response

    def __contains__(self, prompt: object) -> bool:
        if not isinstance(prompt, str):
            return False
        return self.normalize_key(prompt) in self._responses

    def __len__(self) -> int:
        return len(self._responses)

    def stats(self) -> dict:
        return {"entries": len(self), "hits": self.hits, "misses": self.misses}


def _validate_token_count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("token counts must be non-negative integers")


def estimate_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit: bool = False,
) -> float:
    """Calculate simulated cost from token counts and per-million-token prices."""
    if model not in MODEL_PRICING:
        raise ValueError(f"unknown model: {model}")
    _validate_token_count(input_tokens)
    _validate_token_count(output_tokens)
    if cache_hit:
        return 0.0
    pricing = MODEL_PRICING[model]
    cost = (
        input_tokens * pricing["input_usd_per_million_tokens"]
        + output_tokens * pricing["output_usd_per_million_tokens"]
    ) / 1_000_000
    return round(cost, 12)


def estimate_latency_ms(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit: bool = False,
) -> float:
    """Calculate simulated latency from a base delay and per-token delays."""
    if model not in MODEL_PRICING:
        raise ValueError(f"unknown model: {model}")
    _validate_token_count(input_tokens)
    _validate_token_count(output_tokens)
    if cache_hit:
        return CACHE_HIT_LATENCY_MS
    pricing = MODEL_PRICING[model]
    latency = (
        pricing["base_latency_ms"]
        + input_tokens * pricing["input_latency_ms_per_token"]
        + output_tokens * pricing["output_latency_ms_per_token"]
    )
    return round(latency, 3)


def simulate_completion(
    prompt: str,
    model: str,
    response: str,
    cache_hit: bool = False,
) -> dict:
    """Return a JSON-serializable completion and its simulated usage."""
    if not isinstance(response, str):
        raise TypeError("response must be a string")
    normalized = normalize_prompt(prompt)
    input_tokens = estimate_tokens(normalized)
    output_tokens = estimate_tokens(response)
    return {
        "prompt": normalized,
        "response": response,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_hit": cache_hit,
        "cost_usd": estimate_cost_usd(model, input_tokens, output_tokens, cache_hit),
        "latency_ms": estimate_latency_ms(model, input_tokens, output_tokens, cache_hit),
    }


class ModelRouter:
    """Route short requests to cheap_model and complex requests to strong_model."""

    def __init__(self, complexity_threshold: int = 20):
        if (
            isinstance(complexity_threshold, bool)
            or not isinstance(complexity_threshold, int)
            or complexity_threshold <= 0
        ):
            raise ValueError("complexity_threshold must be a positive integer")
        self.complexity_threshold = complexity_threshold

    def route_decision(self, prompt: str) -> dict:
        token_count = estimate_tokens(prompt)
        folded = normalize_prompt(prompt).casefold()
        marker = next((item for item in COMPLEXITY_MARKERS if item in folded), None)
        if token_count > self.complexity_threshold:
            model = "strong_model"
            reason = "token_count_exceeds_threshold"
        elif marker is not None:
            model = "strong_model"
            reason = "complexity_marker"
        else:
            model = "cheap_model"
            reason = "short_simple_request"
        return {
            "model": model,
            "reason": reason,
            "estimated_tokens": token_count,
            "complexity_marker": marker,
        }

    def route(self, prompt: str) -> str:
        return self.route_decision(prompt)["model"]

    def complete(self, prompt: str, cache: TokenCache | None = None) -> dict:
        cache = TokenCache() if cache is None else cache
        normalized = normalize_prompt(prompt)
        model = self.route(normalized)
        cached_response = cache.get(normalized)
        cache_hit = cached_response is not None
        if cache_hit:
            response = cached_response
        elif "2+2" in normalized.replace(" ", "") or "2＋2" in normalized:
            response = "4"
        else:
            response = f"Simulated answer from {model}."
        if not cache_hit:
            cache.set(normalized, response)
        return simulate_completion(normalized, model, response, cache_hit)


def run_minimal_path() -> dict:
    """Show a cache miss, a normalized cache hit, and one routing decision."""
    prompt = "What is 2 + 2?"
    cache = TokenCache()
    router = ModelRouter()
    first_call = router.complete(prompt, cache)
    cached_call = router.complete("  What   is\t2 + 2?  ", cache)
    complex_prompt = "Design a fault-tolerant architecture and explain the trade-offs."
    routing = {"prompt": complex_prompt, **router.route_decision(complex_prompt)}
    return {
        "first_call": first_call,
        "cached_call": cached_call,
        "cost_reduction_usd": round(first_call["cost_usd"] - cached_call["cost_usd"], 9),
        "latency_reduction_ms": round(first_call["latency_ms"] - cached_call["latency_ms"], 3),
        "cache_stats": cache.stats(),
        "routing_example": routing,
    }


def main() -> None:
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
