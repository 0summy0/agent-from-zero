---
id: appendix-real-llm-planner
title_zh: "附录：把确定性 planner 换成真实 LLM"
title_en: "Appendix: Replacing the Deterministic Planner with a Real LLM"
prereq: "完成 2.1、2.3 和 4.4；理解 Python 函数、JSON 和依赖注入"
est_minutes: unmeasured
ram_min_mb: 64
ram_basis: estimate
needs_api_key: false
source_revision: 1
---
<!-- AUTHOR: summy -->

# Appendix: Replacing the Deterministic Planner with a Real LLM

## 1. Why the agent loop is already complete

The capstone already has most of the engineering a real agent needs: structured plan validation, a tool whitelist, step limits, traces, evidence citations, security scanning, and evaluation.

Only `deterministic_planner()` is fixed today: it uses rules to choose the next action. A real LLM does not require replacing the whole agent. It only replaces this decision function.

## 2. The planner interface contract

The current planner receives the question and existing trace, then returns:

```python
{
    "thought": "Why this action was chosen",
    "plan": {
        "action": "calculator",
        "arguments": {"expression": "2 + 2"},
        "confidence": 0.99,
    },
}
```

The `plan` must still pass `validate_plan()`, and tools must still pass `execute_action()`. The model cannot bypass the whitelist and execute commands directly.

## 3. Inject the model with dependency injection

The `LLMPlanner` below is not tied to a provider. It only requires an injected `complete(payload)` function. The example uses a local fake provider, so no API key is needed.

```python
import json

from agent_from_zero import capstone


class LLMPlanner:
    def __init__(self, complete, tool_schemas):
        self.complete = complete
        self.tool_schemas = tool_schemas

    def __call__(self, question, trace):
        payload = {
            "question": question,
            "trace": trace,
            "tools": self.tool_schemas,
            "instruction": "Return one JSON plan. Do not execute tools.",
        }
        raw = self.complete(payload)
        plan = json.loads(raw)
        return {"thought": "The model proposed the next validated plan.", "plan": plan}


def fake_complete(payload):
    return json.dumps(
        {
            "action": "calculator",
            "arguments": {"expression": "6 + 2"},
            "confidence": 0.9,
        }
    )


planner = LLMPlanner(fake_complete, capstone._ARGUMENT_SCHEMAS)
decision = planner("Calculate 6 + 2", [])
valid, errors = capstone.validate_plan(decision["plan"])
print(valid, errors)
print(capstone.execute_action(decision["plan"]))
```

The point is not the fake provider. It is the interface: a real provider only needs to implement the same `complete(payload)` function.

## 4. What a real API provider should do

A real `complete(payload)` usually needs to:

- send the system instruction, tool schemas, user question, and compact trace to the model;
- require JSON only and forbid direct tool execution;
- handle timeouts, rate limits, non-JSON output, and schema validation failures;
- read the API key from an environment variable instead of source code or logs;
- record the model name, latency, token usage, and raw plan for review.

Even when the model returns a plan, it must still pass `validate_plan()` and `execute_action()`. **The model proposes; the program authorizes and executes.**

## 5. Why the outer loop does not change

The existing loop can still:

- run at most `MAX_STEPS` steps;
- record thought, action, and observation at every step;
- call only tools in the registry;
- abstain when evidence is missing;
- return usage, memory, security, and evaluation at the end.

You replace only the source of the next-action decision. Tool execution, evidence chains, auditing, and stop conditions remain unchanged.

## 6. Exercise and boundaries

Try implementing two providers:

1. `FakeProvider`: returns fixed plans for offline tests.
2. `HTTPProvider`: calls an OpenAI-compatible endpoint of your choice and reads the key from the environment.

Then write tests confirming that invalid JSON, unknown tools, invalid arguments, and step-limit exhaustion all fail safely.

This appendix does not add real API calls to the default test suite because the core course must remain offline, zero-GPU, and free of paid keys. Real models introduce cost, latency, privacy, and uncertainty, so they belong in an explicit advanced track.
