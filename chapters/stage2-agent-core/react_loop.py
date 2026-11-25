import ast
import json
import math
import operator
import re

CHAPTER_ID = "2.3-react-loop"
DEFAULT_QUESTION = "Calculate (128 + 256) * 3, then look up the country of Shanghai."

CITY_DATA = {
    "beijing": {"name": "Beijing", "country": "China", "timezone": "UTC+8"},
    "shanghai": {"name": "Shanghai", "country": "China", "timezone": "UTC+8"},
    "paris": {"name": "Paris", "country": "France", "timezone": "UTC+1"},
    "tokyo": {"name": "Tokyo", "country": "Japan", "timezone": "UTC+9"},
}

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_CALCULATION_PATTERN = re.compile(
    r"\b(?:calculate|compute)\s+([0-9(+\-][0-9\s.+*/()\-]*?)"
    r"(?=\s*(?:,|then\b|and\b|[?.!]|$))",
    re.IGNORECASE,
)
_CITY_PATTERNS = (
    re.compile(
        r"\b(?:look\s*up|lookup)\s+(?:the\s+country\s+of\s+)?"
        r"([A-Za-z][A-Za-z -]*?)(?=\s*(?:[?.!,]|$))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat\s+country\s+is\s+([A-Za-z][A-Za-z -]*?)\s+in\b",
        re.IGNORECASE,
    ),
)


def _evaluate(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("non-finite number")
        if abs(value) > 1e12:
            raise ValueError("number is too large")
        return value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return _BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("unsupported arithmetic syntax")


def calculator(expression):
    """Evaluate a small arithmetic expression without eval() or external code."""
    if not isinstance(expression, str) or not expression.strip():
        return {"ok": False, "tool": "calculator", "error": "empty expression"}
    if len(expression) > 120:
        return {"ok": False, "tool": "calculator", "error": "expression too long"}

    try:
        tree = ast.parse(expression.strip(), mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 32:
            raise ValueError("expression too complex")
        result = _evaluate(tree.body)
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("non-finite result")
        if abs(result) > 1e12:
            raise ValueError("result too large")
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return {"ok": False, "tool": "calculator", "error": "invalid arithmetic expression"}

    return {
        "ok": True,
        "tool": "calculator",
        "expression": expression.strip(),
        "result": result,
    }


def lookup_city(city):
    """Look up a city in the local table; this tool never uses the network."""
    if not isinstance(city, str) or not city.strip():
        return {"ok": False, "tool": "lookup_city", "error": "empty city name"}
    key = " ".join(city.casefold().split())
    data = CITY_DATA.get(key)
    if data is None:
        return {"ok": False, "tool": "lookup_city", "error": "city not found"}
    return {"ok": True, "tool": "lookup_city", **data}


def _calculation_expression(question):
    match = _CALCULATION_PATTERN.search(question)
    return match.group(1).strip() if match else None


def _city_name(question):
    for pattern in _CITY_PATTERNS:
        match = pattern.search(question)
        if match:
            city = re.split(r"\s+(?:and|then)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
            return city.strip(" ,.!?")
    return None


def _successful_observation(trace, tool_name):
    for step in trace:
        action = step["action"]
        observation = step["observation"]
        if action["tool"] == tool_name and observation and observation.get("ok"):
            return observation
    return None


def _format_number(value):
    if isinstance(value, int) or value.is_integer():
        return str(int(value))
    return format(value, ".12g")


def deterministic_planner(question, trace):
    """Choose the next action from fixed rules and earlier observations."""
    if not isinstance(question, str):
        question = ""
    expression = _calculation_expression(question)
    city = _city_name(question)

    if expression is None and city is None:
        return {
            "thought": "The request does not match a supported local tool pattern, so I will stop safely.",
            "action": {
                "tool": "finish",
                "input": {
                    "answer": "I can only solve the local arithmetic and city lookup patterns in this chapter."
                },
            },
        }

    calculation = _successful_observation(trace, "calculator")
    city_result = _successful_observation(trace, "lookup_city")

    if expression is not None and calculation is None:
        return {
            "thought": "The question contains an arithmetic request, so I will call the local calculator.",
            "action": {"tool": "calculator", "input": {"expression": expression}},
        }
    if city is not None and city_result is None:
        return {
            "thought": "The question asks about a city, so I will call the local city lookup tool.",
            "action": {"tool": "lookup_city", "input": {"city": city}},
        }

    answer_parts = []
    if calculation is not None:
        answer_parts.append(f"Calculation result: {_format_number(calculation['result'])}.")
    if city_result is not None:
        answer_parts.append(f"{city_result['name']} is in {city_result['country']}.")
    return {
        "thought": "All requested observations are complete, so no more tools are needed.",
        "action": {"tool": "finish", "input": {"answer": " ".join(answer_parts)}},
    }


TOOLS = {"calculator": calculator, "lookup_city": lookup_city}


def run_react_loop(question=DEFAULT_QUESTION, max_steps=4):
    """Run Thought -> Action -> Observation until finish, tool error, or the limit."""
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")

    trace = []
    answer = None
    stop_reason = "max_steps"

    for step_number in range(1, max_steps + 1):
        decision = deterministic_planner(question, trace)
        action = decision["action"]
        if action["tool"] == "finish":
            trace.append(
                {
                    "step": step_number,
                    "thought": decision["thought"],
                    "action": action,
                    "observation": None,
                }
            )
            answer = action["input"]["answer"]
            stop_reason = "answered"
            break

        tool = TOOLS.get(action["tool"])
        observation = tool(**action["input"]) if tool else {"ok": False, "error": "unknown tool"}
        trace.append(
            {
                "step": step_number,
                "thought": decision["thought"],
                "action": action,
                "observation": observation,
            }
        )
        if not observation.get("ok"):
            answer = "Stopped safely because the requested local tool could not complete the task."
            stop_reason = "tool_error"
            break

    return {
        "chapter": CHAPTER_ID,
        "question": question,
        "max_steps": max_steps,
        "status": "answered" if stop_reason == "answered" else "stopped",
        "stop_reason": stop_reason,
        "answer": answer,
        "trace": trace,
    }


def run_minimal_path():
    return run_react_loop(DEFAULT_QUESTION, max_steps=4)


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
