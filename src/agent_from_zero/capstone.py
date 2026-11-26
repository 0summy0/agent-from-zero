"""Chapter 4.4: Local Research Desk, a deterministic teaching capstone.

The project combines evidence-grounded retrieval, validated plans, a bounded
ReAct loop, local tools, prompt-injection scanning, context summaries, JSONL
traces, and small evaluation metrics. It is a teaching project, not a production
agent: the planner uses fixed rules and the knowledge base is deliberately tiny.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import operator
import re
import tempfile
import unicodedata
from pathlib import Path

from jsonschema import Draft202012Validator

from .security_rules import INJECTION_RULES

CHAPTER_ID = "4.4-capstone"
PROJECT_NAME = "Local Research Desk"
MAX_STEPS = 4

KNOWLEDGE_BASE = (
    {
        "id": "kb-capital-france",
        "title": "Capital of France",
        "keywords": ("paris", "capital", "france"),
        "text": "Paris is the capital of France.",
        "source": "local-knowledge-base",
    },
    {
        "id": "kb-capital-canada",
        "title": "Capital of Canada",
        "keywords": ("ottawa", "capital", "canada"),
        "text": "Ottawa is the capital of Canada.",
        "source": "local-knowledge-base",
    },
    {
        "id": "kb-capital-japan",
        "title": "Capital of Japan",
        "keywords": ("tokyo", "capital", "japan"),
        "text": "Tokyo is the capital of Japan.",
        "source": "local-knowledge-base",
    },
    {
        "id": "kb-timezone-tokyo",
        "title": "Timezone of Tokyo",
        "keywords": ("tokyo", "timezone", "utc+9"),
        "text": "Tokyo uses Asia/Tokyo, which is UTC+9 without daylight saving time.",
        "source": "local-knowledge-base",
    },
    {
        "id": "kb-product-atlas-note",
        "title": "Atlas Note product facts",
        "keywords": ("atlas", "note", "features", "offline", "markdown", "exports"),
        "text": "Atlas Note stores research notes locally, works offline, and exports Markdown.",
        "source": "local-product-catalog",
    },
)

CITY_DATA = {
    "beijing": {
        "name": "Beijing",
        "country": "China",
        "timezone": "Asia/Shanghai",
    },
    "shanghai": {
        "name": "Shanghai",
        "country": "China",
        "timezone": "Asia/Shanghai",
    },
    "paris": {
        "name": "Paris",
        "country": "France",
        "timezone": "Europe/Paris",
    },
    "tokyo": {
        "name": "Tokyo",
        "country": "Japan",
        "timezone": "Asia/Tokyo",
    },
}

STOP_WORDS = frozenset(
    "a an and are as at be by can did do does for from how i in is it me of on or "
    "please tell that the their there these this to was were what when where which "
    "who with about features feature".split()
)

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

_CALCULATION_PATTERN = re.compile(
    r"\b(?:calculate|compute|what\s+is)\s+"
    r"([0-9(+\-][0-9\s.+*/()\-]*?)"
    r"(?=\s*(?:,|then\b|and\b|[?.!]|$))|"
    r"\b(?:计算|算一下)\s+"
    r"([0-9(+\-][0-9\s.+*/()\-]*?)"
    r"(?=\s*(?:，|然后|和|[?？！。]|$))",
    re.IGNORECASE,
)
_CITY_PATTERNS = (
    re.compile(
        r"\b(?:look\s*up|lookup)(?:\s+(?:the\s+)?country\s+of|\s+city)?\s+"
        r"([A-Za-z][A-Za-z -]*?)(?=\s*(?:,|then\b|and\b|[?.!]|$))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat\s+country\s+is\s+([A-Za-z][A-Za-z -]*?)\s+in\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhere\s+is\s+([A-Za-z][A-Za-z -]*?)(?:\s+located)?"
        r"(?=\s*(?:[?.!,]|$))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btime\s*zone\s+(?:of|for)\s+([A-Za-z]+)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat\s+time\s*zone\s+does\s+([A-Za-z]+)\s+use\b",
        re.IGNORECASE,
    ),
)

_ARGUMENT_SCHEMAS = {
    "calculator": {
        "type": "object",
        "properties": {"expression": {"type": "string", "minLength": 1, "maxLength": 200}},
        "required": ["expression"],
        "additionalProperties": False,
    },
    "lookup_city": {
        "type": "object",
        "properties": {"city": {"type": "string", "minLength": 1, "maxLength": 80}},
        "required": ["city"],
        "additionalProperties": False,
    },
    "search_knowledge": {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 1, "maxLength": 2000}},
        "required": ["query"],
        "additionalProperties": False,
    },
    "finish": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "minLength": 1},
            "status": {"enum": ["grounded", "abstain"]},
            "evidence_ids": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
            },
            "reason": {"type": "string", "minLength": 1},
        },
        "required": ["answer", "status", "evidence_ids", "reason"],
        "additionalProperties": False,
    },
}

PLAN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "LocalResearchDeskPlan",
    "type": "object",
    "properties": {
        "action": {"enum": sorted(_ARGUMENT_SCHEMAS)},
        "arguments": {"type": "object"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["action", "arguments", "confidence"],
    "additionalProperties": False,
    "allOf": [
        {
            "if": {"properties": {"action": {"const": action}}},
            "then": {"properties": {"arguments": schema}},
        }
        for action, schema in _ARGUMENT_SCHEMAS.items()
    ]
    + [
        {
            "if": {
                "properties": {
                    "action": {"const": "finish"},
                    "arguments": {"properties": {"status": {"const": status}}},
                }
            },
            "then": {
                "properties": {
                    "arguments": {
                        "properties": {
                            "evidence_ids": {
                                "minItems" if status == "grounded" else "maxItems": 1
                                if status == "grounded"
                                else 0
                            }
                        }
                    }
                }
            },
        }
        for status in ("grounded", "abstain")
    ],
}
Draft202012Validator.check_schema(PLAN_SCHEMA)
_PLAN_VALIDATOR = Draft202012Validator(PLAN_SCHEMA)


def validate_plan(plan):
    """Return (is_valid, errors) for a plan object."""
    errors = [
        f"{error.json_path}: {error.message}"
        for error in sorted(
            _PLAN_VALIDATOR.iter_errors(plan),
            key=lambda error: (error.json_path, error.message),
        )
    ]
    return not errors, errors


def scan_prompt_injection(prompt):
    """Normalize text and apply a small, ordered set of injection rules."""
    normalized = unicodedata.normalize("NFKC", prompt).casefold()
    normalized = " ".join(normalized.split())
    matched_rules = [name for name, pattern in INJECTION_RULES if pattern.search(normalized)]
    return {
        "allowed": not matched_rules,
        "risk_level": "high" if matched_rules else "low",
        "matched_rules": matched_rules,
    }


def _tokenize(text):
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def _evidence(record):
    return {
        "id": record["id"],
        "title": record["title"],
        "text": record["text"],
        "source": record["source"],
    }


def retrieve_knowledge(question):
    """Require one local record to cover every content keyword."""
    keywords = set(_tokenize(question)) - STOP_WORDS
    if not keywords:
        return []

    matches = []
    for record in KNOWLEDGE_BASE:
        priority_terms = set(_tokenize(" ".join(record["keywords"]))) | set(
            _tokenize(record["title"])
        )
        searchable_terms = priority_terms | set(_tokenize(record["text"]))
        if keywords.issubset(searchable_terms):
            score = len(keywords & priority_terms)
            matches.append((score, record))

    matches.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [_evidence(record) for _, record in matches]


def _evaluate_arithmetic(node):
    if isinstance(node, ast.Expression):
        return _evaluate_arithmetic(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite number")
        if abs(value) > 1e12:
            raise ValueError("number is too large")
        return value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_arithmetic(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_arithmetic(node.left)
        right = _evaluate_arithmetic(node.right)
        return _BINARY_OPERATORS[type(node.op)](left, right)
    raise ValueError("only numbers and arithmetic operators are allowed")


def _format_number(value):
    if isinstance(value, int) or value.is_integer():
        return str(int(value))
    return format(value, ".12g")


def calculator(expression):
    """Evaluate bounded arithmetic without eval(), names, calls, or powers."""
    failure = {"ok": False, "tool": "calculator", "error": "invalid arithmetic expression"}
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 200:
        return failure
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 32:
            raise ValueError("expression too complex")
        result = _evaluate_arithmetic(tree)
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("non-finite result")
        if abs(result) > 1e12:
            raise ValueError("result too large")
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError, RecursionError):
        return failure
    return {
        "ok": True,
        "tool": "calculator",
        "expression": expression.strip(),
        "result": result,
    }


def lookup_city(city):
    """Look up a city in a fixed local table; never use the network."""
    if not isinstance(city, str) or not city.strip():
        return {"ok": False, "tool": "lookup_city", "error": "empty city name"}
    key = " ".join(city.casefold().split())
    data = CITY_DATA.get(key)
    if data is None:
        return {"ok": False, "tool": "lookup_city", "error": "city not found"}
    text = f"{data['name']} is a city in {data['country']}; its timezone is {data['timezone']}."
    return {
        "ok": True,
        "tool": "lookup_city",
        "record": {
            "id": f"city-{key}",
            "title": f"{data['name']} city facts",
            "text": text,
            "source": "local-city-table",
        },
    }


def search_knowledge(query):
    """Return local records; an empty result is a valid retrieval observation."""
    records = retrieve_knowledge(query)
    return {"ok": True, "tool": "search_knowledge", "found": bool(records), "records": records}


TOOL_REGISTRY = {
    "calculator": calculator,
    "lookup_city": lookup_city,
    "search_knowledge": search_knowledge,
}
ALLOWED_TOOLS = frozenset(TOOL_REGISTRY)


def execute_action(plan):
    """Validate a plan and execute only a registered, side-effect-free tool."""
    valid, errors = validate_plan(plan)
    if not valid:
        raise ValueError("invalid tool plan: " + "; ".join(errors))
    action = plan["action"]
    if action == "finish":
        raise ValueError("finish is a control action, not a tool")
    if action not in ALLOWED_TOOLS:
        raise ValueError(f"unknown tool: {action}")
    return TOOL_REGISTRY[action](**plan["arguments"])


class ContextMemory:
    """Keep recent messages plus a lossy summary and a character budget."""

    def __init__(self, max_messages=4, char_budget=640, summary_message_chars=96):
        self.max_messages = max_messages
        self.char_budget = char_budget
        self.summary_message_chars = summary_message_chars
        self.messages = []
        self.summary = ""
        self.evicted_count = 0

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        evicted = []
        while len(self.messages) > self.max_messages:
            old = self.messages.pop(0)
            compact = " ".join(old["content"].split())
            if len(compact) > self.summary_message_chars:
                compact = compact[: self.summary_message_chars - 3] + "..."
            fragment = f"{old['role']}: {compact}"
            self.summary = f"{self.summary} | {fragment}" if self.summary else fragment
            self.evicted_count += 1
            evicted.append(dict(old))
        return evicted

    def build_context(self):
        sections = []
        if self.summary:
            sections.append(f"Earlier summary: {self.summary}")
        sections.append("Recent messages:")
        sections.extend(f"{item['role']}: {item['content']}" for item in self.messages)
        full = "\n".join(sections)
        if len(full) <= self.char_budget:
            return full
        return "..." + full[-(self.char_budget - 3) :]

    def snapshot(self):
        context = self.build_context()
        return {
            "summary": self.summary,
            "recent_messages": [dict(item) for item in self.messages],
            "recent_message_count": len(self.messages),
            "evicted_message_count": self.evicted_count,
            "context": context,
            "context_chars": len(context),
            "approximate_tokens": (len(context) + 3) // 4,
            "truncated": len(self.build_context()) < len(self._full_context()),
        }

    def _full_context(self):
        sections = []
        if self.summary:
            sections.append(f"Earlier summary: {self.summary}")
        sections.append("Recent messages:")
        sections.extend(f"{item['role']}: {item['content']}" for item in self.messages)
        return "\n".join(sections)


def _calculation_expression(question):
    match = _CALCULATION_PATTERN.search(question)
    if not match:
        return None
    return next(group.strip() for group in match.groups() if group is not None)


def _city_name(question):
    for pattern in _CITY_PATTERNS:
        match = pattern.search(question)
        if match:
            city = re.split(r"\s+(?:and|then)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[
                0
            ]
            return city.strip(" ,.!?")
    return None


def _has_observation(trace, action):
    return any(
        step["action"]["action"] == action and step["observation"] is not None for step in trace
    )


def _observation(trace, action):
    for step in trace:
        if step["action"]["action"] == action and step["observation"] is not None:
            return step["observation"]
    return None


def _finish_plan(answer, status, evidence, reason):
    return {
        "action": "finish",
        "arguments": {
            "answer": answer,
            "status": status,
            "evidence_ids": [item["id"] for item in evidence],
            "reason": reason,
        },
        "confidence": 1.0,
    }


def _abstain(reason, answer=None):
    message = answer or "I don't know; no verifiable local evidence is available for this question."
    return _finish_plan(message, "abstain", [], reason)


def deterministic_planner(question, trace):
    """Choose one validated action from fixed rules and earlier observations."""
    expression = _calculation_expression(question)
    city = _city_name(question)
    knowledge_needed = city is None and (expression is None or bool(retrieve_knowledge(question)))

    if expression is not None and not _has_observation(trace, "calculator"):
        return {
            "thought": "The request contains arithmetic, so I will use the bounded local calculator.",
            "plan": {
                "action": "calculator",
                "arguments": {"expression": expression},
                "confidence": 0.99,
            },
        }
    if city is not None and not _has_observation(trace, "lookup_city"):
        return {
            "thought": "The request names a supported city pattern, so I will query the local city table.",
            "plan": {
                "action": "lookup_city",
                "arguments": {"city": city},
                "confidence": 0.99,
            },
        }
    if knowledge_needed and not _has_observation(trace, "search_knowledge"):
        return {
            "thought": "I will search the local records and let the evidence gate decide whether to answer.",
            "plan": {
                "action": "search_knowledge",
                "arguments": {"query": question},
                "confidence": 0.99,
            },
        }

    failed_actions = {"calculator", "lookup_city", "search_knowledge"} & {
        step["action"]["action"]
        for step in trace
        if step["observation"] is not None and not step["observation"].get("ok")
    }
    if failed_actions:
        return {
            "thought": "A required local tool failed, so I will stop without guessing.",
            "plan": _abstain(
                "tool_unavailable", "I can't verify this request from the available local tools."
            ),
        }
    if knowledge_needed:
        retrieval = _observation(trace, "search_knowledge")
        if retrieval is None or not retrieval["found"]:
            return {
                "thought": "Retrieval returned no supporting record, so the evidence gate requires abstention.",
                "plan": _abstain("no_local_evidence"),
            }

    evidence = []
    answer_parts = []
    calculation = _observation(trace, "calculator")
    city_result = _observation(trace, "lookup_city")
    retrieval = _observation(trace, "search_knowledge")
    if calculation is not None:
        rendered = _format_number(calculation["result"])
        evidence.append(
            {
                "id": "calculator",
                "title": "Local calculation",
                "text": f"{calculation['expression']} = {rendered}",
                "source": "safe-calculator",
            }
        )
        answer_parts.append(f"Calculation result: {rendered}. [calculator]")
    if city_result is not None:
        record = city_result["record"]
        evidence.append(record)
        answer_parts.append(f"{record['text']} [{record['id']}]")
    if retrieval is not None and retrieval["records"]:
        record = retrieval["records"][0]
        evidence.append(record)
        answer_parts.append(f"{record['text']} [{record['id']}]")

    if evidence:
        return {
            "thought": "Every requested local observation is complete, so I will answer with citations.",
            "plan": _finish_plan(
                " ".join(answer_parts), "grounded", evidence, "supported_by_local_observations"
            ),
        }
    return {
        "thought": "The request matches no supported local task, so I will abstain.",
        "plan": _abstain(
            "unsupported_request",
            "I can only answer the local knowledge, city, and arithmetic patterns in this project.",
        ),
    }


def _estimate_tokens(text):
    return (len(" ".join(text.split())) + 3) // 4


def _write_trace(directory, question, trace, status, evidence):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "trace.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for step in trace:
            event = {"event": "step", **step}
            stream.write(
                json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            )
        summary = {
            "event": "result",
            "question": question,
            "status": status,
            "evidence_ids": [item["id"] for item in evidence],
        }
        stream.write(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
        )
    return path


def _evaluate(status, evidence, answer, trace, security):
    evidence_ids = {item["id"] for item in evidence}
    cited_ids = {item["id"] for item in evidence if f"[{item['id']}]" in answer}
    grounded = status == "grounded"
    return {
        "task_success": grounded,
        "abstained": status == "abstain",
        "injection_blocked": status == "rejected" and not security["allowed"],
        "evidence_count": len(evidence),
        "citation_coverage": round(len(cited_ids) / len(evidence_ids), 3) if evidence_ids else 0.0,
        "citations_supported": grounded and cited_ids == evidence_ids,
        "steps_used": len(trace),
        "within_step_limit": len(trace) <= MAX_STEPS,
    }


def run(question, *, trace_dir=None):
    """Run one deterministic local research task and return JSON-safe data."""
    if not isinstance(question, str):
        raise TypeError("question must be a string")
    if not question.strip():
        raise ValueError("question must not be empty")
    if len(question) > 2000:
        raise ValueError("question must be at most 2000 characters")

    security = scan_prompt_injection(question)
    memory = ContextMemory()
    memory.add_message(
        "system", "Answer only from local evidence; cite IDs; abstain when unsupported."
    )
    memory.add_message("user", question)
    trace = []
    evidence = []
    status = "abstain"
    answer = "I don't know; no verifiable local evidence is available for this question."
    stop_reason = "max_steps"
    input_tokens = _estimate_tokens(question)
    output_tokens = 0
    tool_calls = 0

    if not security["allowed"]:
        status = "rejected"
        stop_reason = "prompt_injection"
        answer = "Request rejected because it matches a prompt-injection safety rule."
        thought = "The safety scan found disallowed instruction patterns; no tool will run."
        trace.append(
            {
                "step": 1,
                "thought": thought,
                "action": {"tool": "reject", "input": {"matched_rules": security["matched_rules"]}},
                "observation": security,
            }
        )
        output_tokens += _estimate_tokens(thought + answer)
        memory.add_message("assistant", thought)
    else:
        for step_number in range(1, MAX_STEPS + 1):
            context = memory.build_context()
            input_tokens += _estimate_tokens(context)
            decision = deterministic_planner(question, trace)
            plan = decision["plan"]
            valid, errors = validate_plan(plan)
            if not valid:
                raise RuntimeError(
                    "internal planner produced an invalid plan: " + "; ".join(errors)
                )

            action = plan["action"]
            observation = None if action == "finish" else execute_action(plan)
            trace.append(
                {
                    "step": step_number,
                    "thought": decision["thought"],
                    "action": plan,
                    "plan_valid": True,
                    "observation": observation,
                }
            )
            output_tokens += _estimate_tokens(decision["thought"])
            memory.add_message("assistant", decision["thought"])
            if observation is not None:
                tool_calls += 1
                memory.add_message(
                    "tool", json.dumps(observation, ensure_ascii=False, sort_keys=True)
                )

            if action == "finish":
                arguments = plan["arguments"]
                status = arguments["status"]
                answer = arguments["answer"]
                known_ids = {
                    item["id"]
                    for step in trace
                    if step["observation"] is not None
                    for item in step["observation"].get("records", [])
                }
                for step in trace:
                    record = step["observation"].get("record") if step["observation"] else None
                    if record:
                        known_ids.add(record["id"])
                if status == "grounded" and "calculator" in arguments["evidence_ids"]:
                    known_ids.add("calculator")
                by_id = {}
                for step in trace:
                    observation_data = step["observation"]
                    if not observation_data:
                        continue
                    by_id.update({item["id"]: item for item in observation_data.get("records", [])})
                    if observation_data.get("record"):
                        by_id[observation_data["record"]["id"]] = observation_data["record"]
                    if observation_data.get("tool") == "calculator" and observation_data.get("ok"):
                        rendered = _format_number(observation_data["result"])
                        by_id["calculator"] = {
                            "id": "calculator",
                            "title": "Local calculation",
                            "text": f"{observation_data['expression']} = {rendered}",
                            "source": "safe-calculator",
                        }
                if not set(arguments["evidence_ids"]).issubset(known_ids):
                    raise RuntimeError("finish plan cites an unknown evidence ID")
                evidence = [by_id[item_id] for item_id in arguments["evidence_ids"]]
                stop_reason = "answered" if status == "grounded" else "abstained"
                break
        else:
            status = "abstain"
            answer = "I stopped at the four-step limit and will not guess."
            stop_reason = "max_steps"
            evidence = []

    output_tokens += _estimate_tokens(answer)
    memory.add_message("assistant", answer)

    temporary_trace = trace_dir is None
    if temporary_trace:
        with tempfile.TemporaryDirectory(prefix="local-research-desk-") as temporary_root:
            trace_path = _write_trace(Path(temporary_root), question, trace, status, evidence)
            trace_name = trace_path.name
        trace_directory = None
    else:
        trace_directory = Path(trace_dir).expanduser()
        trace_path = _write_trace(trace_directory, question, trace, status, evidence)
        trace_name = trace_path.name

    checked = sum("plan_valid" in step for step in trace)
    usage = {
        "model": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "token_estimate": "normalized characters divided by four",
        "contexts_built": checked,
        "tool_calls": tool_calls,
        "network_calls": 0,
        "cost_usd": 0.0,
    }
    return {
        "chapter": CHAPTER_ID,
        "project": PROJECT_NAME,
        "question": question,
        "answer": answer,
        "status": status,
        "stop_reason": stop_reason,
        "evidence": evidence,
        "trace": trace,
        "trace_file": {
            "name": trace_name,
            "directory": None if trace_directory is None else str(trace_directory.resolve()),
            "temporary": temporary_trace,
            "event_count": len(trace) + 1,
        },
        "usage": usage,
        "memory": memory.snapshot(),
        "plan_validation": {"checked": checked, "passed": checked, "errors": []},
        "security": security,
        "evaluation": _evaluate(status, evidence, answer, trace, security),
        "max_steps": MAX_STEPS,
        "teaching_scope": "deterministic rules and tiny local data; not a production agent",
    }


def run_demo(trace_dir=None):
    """Run one grounded case and one no-evidence case."""
    root = Path(trace_dir).expanduser() if trace_dir is not None else None
    grounded = run(
        "What is the capital of France?",
        trace_dir=root / "grounded" if root is not None else None,
    )
    abstention = run(
        "What is the capital of Atlantis?",
        trace_dir=root / "abstain" if root is not None else None,
    )
    cases = {"grounded": grounded, "abstain": abstention}
    total_tokens = sum(item["usage"]["total_tokens"] for item in cases.values())
    grounded_cases = [item for item in cases.values() if item["status"] == "grounded"]
    citation_pass_rate = (
        sum(item["evaluation"]["citations_supported"] for item in grounded_cases)
        / len(grounded_cases)
        if grounded_cases
        else 0.0
    )
    return {
        "project": PROJECT_NAME,
        "mode": "demo",
        "statuses": [grounded["status"], abstention["status"]],
        "cases": cases,
        "evaluation": {
            "cases": 2,
            "grounded_count": sum(item["status"] == "grounded" for item in cases.values()),
            "abstention_count": sum(item["status"] == "abstain" for item in cases.values()),
            "task_success_rate": sum(item["status"] == "grounded" for item in cases.values()) / 2,
            "citation_pass_rate": citation_pass_rate,
            "average_steps": sum(len(item["trace"]) for item in cases.values()) / 2,
            "total_estimated_tokens": total_tokens,
            "cost_usd": 0.0,
        },
    }


def main(argv=None):
    """CLI entry point: one positional question or --demo, printed as JSON."""
    parser = argparse.ArgumentParser(description=PROJECT_NAME)
    parser.add_argument("question", nargs="?", help="one local research question")
    parser.add_argument("--demo", action="store_true", help="run grounded and abstention examples")
    parser.add_argument(
        "--trace-dir", help="directory for trace.jsonl (default: a temporary directory)"
    )
    args = parser.parse_args(argv)
    if args.demo and args.question:
        parser.error("use either a positional question or --demo, not both")
    if not args.demo and not args.question:
        parser.error("provide a question or use --demo")
    result = run_demo(args.trace_dir) if args.demo else run(args.question, trace_dir=args.trace_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
