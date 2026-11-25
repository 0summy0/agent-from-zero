import json
import time
from contextlib import contextmanager
from pathlib import Path


CHAPTER_ID = "3.2-tracing"


class TraceWriter:
    """Write one JSON object per completed span to a JSONL file."""

    def __init__(self, path, clock=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or time.monotonic
        self._active = {}
        self._records = []
        self._counter = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def start_span(self, name, parent_span_id=None, attributes=None):
        self._counter += 1
        span_id = f"span-{self._counter:03d}"
        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "start": self.clock(),
            "attributes": dict(attributes or {}),
        }
        self._active[span_id] = span
        return span

    def end_span(self, span, error=None):
        span_id = span["span_id"]
        if span_id not in self._active:
            raise ValueError(f"span is not active: {span_id}")
        end = self.clock()
        attributes = dict(span["attributes"])
        attributes["status"] = "error" if error is not None else "ok"
        if error is not None:
            attributes["error"] = str(error)
        record = {
            "span_id": span_id,
            "parent_span_id": span["parent_span_id"],
            "name": span["name"],
            "start": span["start"],
            "end": end,
            "duration_ms": round(max(0.0, end - span["start"]) * 1000, 3),
            "attributes": attributes,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        del self._active[span_id]
        self._records.append(record)
        return record

    @contextmanager
    def span(self, name, parent_span_id=None, attributes=None):
        span = self.start_span(name, parent_span_id=parent_span_id, attributes=attributes)
        try:
            yield span
        except Exception as exc:
            self.end_span(span, error=exc)
            raise
        else:
            self.end_span(span)

    @property
    def records(self):
        return list(self._records)

    def close(self):
        remaining = list(self._active)
        for span_id in remaining:
            self.end_span(self._active[span_id], error="span closed before completion")


class ToyAgentRunner:
    """Run a deterministic plan/tool/answer chain and save its trace."""

    def __init__(self, output_dir, clock=None):
        self.output_dir = Path(output_dir)
        self.trace_path = self.output_dir / "trace.jsonl"
        self.clock = clock

    def run(self, question, fail_tool=False):
        records = []
        with TraceWriter(self.trace_path, clock=self.clock) as writer:
            with writer.span("agent.run", attributes={"question": question}) as root:
                with writer.span(
                    "agent.plan", parent_span_id=root["span_id"], attributes={"step": 1}
                ) as plan:
                    pass
                with writer.span(
                    "tool.lookup",
                    parent_span_id=plan["span_id"],
                    attributes={"query": question},
                ) as tool:
                    if fail_tool:
                        raise RuntimeError("toy lookup failed")
                    if "2 + 2" in question:
                        answer = "4"
                    elif "capital of France" in question:
                        answer = "Paris"
                    else:
                        answer = "I do not know"
                with writer.span(
                    "agent.answer",
                    parent_span_id=root["span_id"],
                    attributes={"answer": answer},
                ):
                    pass
            records = writer.records

        key_names = {"agent.run", "tool.lookup", "agent.answer"}
        return {
            "chapter": CHAPTER_ID,
            "question": question,
            "answer": answer,
            "status": "ok",
            "span_count": len(records),
            "key_spans": [
                {
                    "span_id": record["span_id"],
                    "parent_span_id": record["parent_span_id"],
                    "name": record["name"],
                    "status": record["attributes"]["status"],
                }
                for record in records
                if record["name"] in key_names
            ],
        }


def run_minimal_path():
    import tempfile

    with tempfile.TemporaryDirectory(prefix="agent-trace-") as output_dir:
        result = ToyAgentRunner(output_dir, clock=lambda: 1.0).run("What is 2 + 2?")
    return result


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
