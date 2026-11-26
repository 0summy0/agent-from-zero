import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from agent_from_zero import capstone

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_3_react_loop",
    ROOT / "chapters" / "stage2-agent-core" / "react_loop.py",
)
react_loop = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(react_loop)


def load_schema(name: str) -> dict:
    return json.loads((ROOT / "tests" / "golden" / name).read_text(encoding="utf-8"))


def test_react_loop_matches_golden_contract():
    schema = load_schema("2.3-react-loop.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(react_loop.run_minimal_path())


def test_capstone_matches_golden_contract():
    schema = load_schema("4.4-capstone.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(capstone.run("What is the capital of France?"))
