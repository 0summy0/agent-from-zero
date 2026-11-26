import ast
import json
import math
import operator
import re

CHAPTER_ID = "2.2-tool-calling"

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_JSON_FENCE = re.compile(r"```(?:json)?[\t ]*\r?\n(.*?)```", re.IGNORECASE | re.DOTALL)
_CITY_NAMES = {
    "beijing": "Beijing",
    "shanghai": "Shanghai",
    "shenzhen": "Shenzhen",
}


def _evaluate_arithmetic(node):
    if isinstance(node, ast.Expression):
        return _evaluate_arithmetic(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_arithmetic(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_arithmetic(node.left)
        right = _evaluate_arithmetic(node.right)
        return _BINARY_OPERATORS[type(node.op)](left, right)
    raise ValueError("calculator supports only numbers and arithmetic operators")


def calculator(expression):
    """Evaluate a small arithmetic language without eval or exec."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression must be a non-empty string")
    if len(expression) > 200:
        raise ValueError("expression must be at most 200 characters")

    try:
        result = _evaluate_arithmetic(ast.parse(expression.strip(), mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("calculator could not evaluate the expression") from exc

    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("calculator result must be finite")
    return result


def lookup_city(city):
    """Look up a city in a fixed local table; no network is used."""
    if not isinstance(city, str) or not city.strip():
        raise ValueError("city must be a non-empty string")
    canonical_name = _CITY_NAMES.get(city.strip().casefold())
    if canonical_name is None:
        raise ValueError(f"unknown city: {city}")
    return {"city": canonical_name, "country": "China", "timezone": "Asia/Shanghai"}


TOOL_REGISTRY = {
    "calculator": {"handler": calculator, "parameters": {"expression": str}},
    "lookup_city": {"handler": lookup_city, "parameters": {"city": str}},
}
ALLOWED_TOOLS = frozenset(TOOL_REGISTRY)


def _reject_nonstandard_constant(value):
    raise ValueError(f"non-standard JSON constant: {value}")


def _load_json_object(text):
    candidate = text.strip()
    fenced_blocks = _JSON_FENCE.findall(candidate)
    if len(fenced_blocks) > 1:
        raise ValueError("expected exactly one JSON code block")
    if fenced_blocks:
        candidate = fenced_blocks[0].strip()
    elif candidate.startswith("```"):
        raise ValueError("unsupported or unterminated Markdown fence")
    try:
        plan = json.loads(candidate, parse_constant=_reject_nonstandard_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(plan, dict):
        raise ValueError("tool plan must be a JSON object")
    return plan


def parse_plan(plan):
    """Accept a plan object or JSON text and return a validated copy."""
    if isinstance(plan, str):
        plan = _load_json_object(plan)
    if not isinstance(plan, dict):
        raise ValueError("tool plan must be an object")

    errors = []
    required = {"action", "arguments", "confidence"}
    missing = sorted(required - plan.keys())
    unexpected = sorted(plan.keys() - required)
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if unexpected:
        errors.append(f"unexpected fields: {', '.join(unexpected)}")
    if "action" in plan and (not isinstance(plan["action"], str) or not plan["action"].strip()):
        errors.append("action must be a non-empty string")
    if "arguments" in plan and not isinstance(plan["arguments"], dict):
        errors.append("arguments must be an object")
    if "confidence" in plan:
        confidence = plan["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            errors.append("confidence must be a number")
        elif not 0 <= confidence <= 1:
            errors.append("confidence must be between 0 and 1")
    if errors:
        raise ValueError("invalid tool plan: " + "; ".join(errors))

    return {
        "action": plan["action"],
        "arguments": dict(plan["arguments"]),
        "confidence": plan["confidence"],
    }


def call_tool(tool_name, arguments, allowed_tools=ALLOWED_TOOLS):
    """Check the registry, allowlist, and parameters before invoking a tool."""
    if not isinstance(tool_name, str) or tool_name not in TOOL_REGISTRY:
        raise ValueError(f"unknown tool: {tool_name}")
    if tool_name not in allowed_tools:
        raise ValueError(f"tool is not allowed: {tool_name}")
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")

    specification = TOOL_REGISTRY[tool_name]
    parameters = specification["parameters"]
    missing = sorted(parameters.keys() - arguments.keys())
    unexpected = sorted(arguments.keys() - parameters.keys())
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise ValueError(f"invalid arguments for {tool_name}: {'; '.join(details)}")
    for name, expected_type in parameters.items():
        if not isinstance(arguments[name], expected_type):
            raise ValueError(f"argument {name} must be {expected_type.__name__}")

    result = specification["handler"](**arguments)
    return {"tool": tool_name, "arguments": dict(arguments), "result": result}


def execute_plan(plan, allowed_tools=ALLOWED_TOOLS):
    parsed = parse_plan(plan)
    return call_tool(parsed["action"], parsed["arguments"], allowed_tools=allowed_tools)


def run_minimal_path():
    plan = {
        "action": "calculator",
        "arguments": {"expression": "(6 + 2) * 7"},
        "confidence": 0.99,
    }
    return {"chapter": CHAPTER_ID, **execute_plan(plan)}


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
