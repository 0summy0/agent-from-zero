import json
import re

from jsonschema import Draft202012Validator

CHAPTER_ID = "2.1-structured-output"

TOOL_PLAN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "ToolPlan",
    "type": "object",
    "properties": {
        "action": {"type": "string", "minLength": 1, "pattern": r"\S"},
        "arguments": {"type": "object"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["action", "arguments", "confidence"],
    "additionalProperties": False,
}

Draft202012Validator.check_schema(TOOL_PLAN_SCHEMA)
_PLAN_VALIDATOR = Draft202012Validator(TOOL_PLAN_SCHEMA)
_JSON_FENCE = re.compile(r"```(?:json)?[\t ]*\r?\n(.*?)```", re.IGNORECASE | re.DOTALL)


def validate_plan(plan):
    """Return (is_valid, errors) for a Python object against ToolPlan."""
    errors = [
        f"{error.json_path}: {error.message}"
        for error in sorted(
            _PLAN_VALIDATOR.iter_errors(plan),
            key=lambda error: (error.json_path, error.message),
        )
    ]
    return not errors, errors


def _reject_nonstandard_constant(value):
    raise ValueError(f"non-standard JSON constant: {value}")


def repair_json(text):
    """Extract one JSON object, optionally from a Markdown JSON fence.

    This repairs the transport wrapper, not the plan itself. Missing fields and
    wrong value types remain the responsibility of validate_plan().
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("JSON text must be a non-empty string")

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


def run_minimal_path():
    valid_plan = {
        "action": "lookup_city",
        "arguments": {"city": "Beijing"},
        "confidence": 0.9,
    }
    invalid_plan = {
        "action": "calculator",
        "arguments": {"expression": "2 + 2"},
    }

    valid, valid_errors = validate_plan(valid_plan)
    invalid, invalid_errors = validate_plan(invalid_plan)
    return {
        "chapter": CHAPTER_ID,
        "valid_plan": {
            "plan": valid_plan,
            "valid": valid,
            "errors": valid_errors,
        },
        "invalid_plan": {
            "plan": invalid_plan,
            "valid": invalid,
            "errors": invalid_errors,
        },
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
