import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_4_memory_context",
    ROOT / "chapters" / "stage2-agent-core" / "memory.py",
)
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)


def test_chapter_module_imports():
    assert memory.CHAPTER_ID == "2.4-memory-context"
    assert callable(memory.run_minimal_path)


def test_recent_window_respects_its_message_limit():
    store = memory.MemoryStore(max_messages=2)
    evicted = []
    for content in ("first", "second", "third", "fourth"):
        evicted.extend(store.add_message("user", content))

    assert len(store.messages) == 2
    assert [message["content"] for message in store.messages] == ["third", "fourth"]
    assert [message["content"] for message in evicted] == ["first", "second"]
    assert store.evicted_count == 2


def test_summary_retains_an_early_key_fact_after_eviction():
    store = memory.MemoryStore(max_messages=2)
    store.add_message("user", memory.KEY_FACT)
    store.add_message("assistant", "Understood.")
    store.add_message("user", "Now we are discussing a different topic.")
    store.add_message("assistant", "The recent window has moved on.")

    recent_text = "\n".join(message["content"] for message in store.messages)
    assert memory.KEY_FACT not in recent_text
    assert memory.KEY_FACT in store.summary


def test_character_budget_truncates_context():
    store = memory.MemoryStore(max_messages=5, char_budget=30)
    store.add_message("user", "A long message that cannot fit into the tiny context budget.")

    context = store.build_context()
    snapshot = store.snapshot()
    assert len(context) == 30
    assert context.startswith("...")
    assert snapshot["context_chars"] <= store.char_budget
    assert snapshot["approximate_tokens"] == 8
    assert snapshot["truncated"] is True


def test_summary_is_lossy_for_long_old_messages():
    store = memory.MemoryStore(max_messages=1, summary_message_chars=12)
    store.add_message("user", "abcdefghijklmnopqrstuvwxyz")
    store.add_message("assistant", "new")

    assert store.summary == "user: abcdefghi..."
    assert "mnopqrstuvwxyz" not in store.summary


def test_minimal_path_demonstrates_summary_retention():
    result = memory.run_minimal_path()

    assert result["window_contains_key_fact"] is False
    assert result["summary_contains_key_fact"] is True
    assert result["evicted_messages"][0]["content"] == memory.KEY_FACT
    assert result["snapshot"]["recent_message_count"] == 3


def test_minimal_path_is_deterministic_and_json_serializable():
    first = memory.run_minimal_path()
    second = memory.run_minimal_path()

    assert first == second
    assert json.loads(json.dumps(first)) == first
    assert json.loads(json.dumps(first["snapshot"])) == first["snapshot"]
