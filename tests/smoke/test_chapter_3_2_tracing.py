import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_3_2_tracing",
    ROOT / "chapters" / "stage3-reliability" / "tracing.py",
)
tracing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tracing)


def read_records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_chapter_module_imports():
    assert tracing.CHAPTER_ID == "3.2-tracing"
    assert callable(tracing.run_minimal_path)


def test_trace_has_parent_child_relationships(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    with tracing.TraceWriter(trace_path, clock=lambda: 1.0) as writer:
        with writer.span("agent.run") as root:
            with writer.span("tool.lookup", parent_span_id=root["span_id"]):
                pass

    records = read_records(trace_path)
    assert len(records) == 2
    by_name = {record["name"]: record for record in records}
    assert by_name["agent.run"]["parent_span_id"] is None
    assert by_name["tool.lookup"]["parent_span_id"] == by_name["agent.run"]["span_id"]


def test_duration_is_non_negative_even_if_clock_moves_backwards(tmp_path):
    times = iter([2.0, 1.0])
    trace_path = tmp_path / "trace.jsonl"
    with tracing.TraceWriter(trace_path, clock=lambda: next(times)) as writer:
        with writer.span("agent.run"):
            pass
    assert read_records(trace_path)[0]["duration_ms"] == 0.0


def test_jsonl_has_required_fields_and_parses_line_by_line(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    times = iter([1.0, 1.025])
    with tracing.TraceWriter(trace_path, clock=lambda: next(times)) as writer:
        with writer.span("agent.run", attributes={"question": "2+2?"}):
            pass

    lines = trace_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert set(record) == {
        "span_id",
        "parent_span_id",
        "name",
        "start",
        "end",
        "duration_ms",
        "attributes",
    }
    assert record["duration_ms"] == 25.0
    assert record["attributes"] == {"question": "2+2?", "status": "ok"}


def test_exception_span_is_recorded(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    with tracing.TraceWriter(trace_path, clock=lambda: 1.0) as writer:
        with pytest.raises(RuntimeError, match="lookup failed"):
            with writer.span("agent.run"):
                with writer.span("tool.lookup", parent_span_id="span-001"):
                    raise RuntimeError("lookup failed")

    records = read_records(trace_path)
    assert len(records) == 2
    assert all(record["attributes"]["status"] == "error" for record in records)
    assert all("lookup failed" in record["attributes"]["error"] for record in records)


def test_toy_runner_writes_trace_in_target_directory(tmp_path):
    result = tracing.ToyAgentRunner(tmp_path, clock=lambda: 1.0).run(
        "What is the capital of France?"
    )
    assert result["answer"] == "Paris"
    assert result["span_count"] == 4
    assert (tmp_path / "trace.jsonl").is_file()
    assert len(read_records(tmp_path / "trace.jsonl")) == 4
    json.dumps(result)


def test_fixed_clock_makes_trace_and_result_deterministic(tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = tracing.ToyAgentRunner(first_dir, clock=lambda: 5.0).run("What is 2 + 2?")
    second = tracing.ToyAgentRunner(second_dir, clock=lambda: 5.0).run("What is 2 + 2?")
    assert first == second
    assert read_records(first_dir / "trace.jsonl") == read_records(second_dir / "trace.jsonl")
    assert tracing.run_minimal_path() == tracing.run_minimal_path()
    assert tracing.run_minimal_path()["span_count"] == 4
    json.dumps(tracing.run_minimal_path())
