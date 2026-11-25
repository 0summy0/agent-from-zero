import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_4_3_realtime_voice",
    ROOT / "chapters" / "stage4-orchestration" / "realtime_voice.py",
)
realtime_voice = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(realtime_voice)


def test_chapter_module_and_result_contract():
    assert realtime_voice.CHAPTER_ID == "4.3-realtime-voice"
    assert callable(realtime_voice.run_minimal_path)
    result = realtime_voice.run_minimal_path()
    assert result["chapter"] == "4.3-realtime-voice"
    json.dumps(result)


def test_partial_transcripts_only_update_current_text():
    session = realtime_voice.RealtimeSession()
    session.handle({"type": "transcript.partial", "text": "请"})
    session.handle({"type": "transcript.partial", "text": "请帮我总结"})
    state = session.snapshot()

    assert state["current_transcript"] == "请帮我总结"
    assert state["final_transcripts"] == []
    assert state["pending_responses"] == []
    assert state["emitted_responses"] == []
    assert state["cancelled_responses"] == []
    assert [item["outcome"] for item in state["event_log"]] == [
        "transcript_updated",
        "transcript_updated",
    ]


def test_final_queues_exactly_one_deterministic_answer():
    session = realtime_voice.RealtimeSession()
    session.handle({"type": "transcript.final", "text": "你好"})
    queued = session.snapshot()

    assert queued["current_transcript"] == ""
    assert queued["final_transcripts"] == ["你好"]
    assert len(queued["pending_responses"]) == 1
    assert queued["pending_responses"][0]["text"] == "确定性回答：你好"
    assert queued["emitted_responses"] == []

    session.handle({"type": "response.create"})
    emitted = session.snapshot()
    assert emitted["pending_responses"] == []
    assert len(emitted["emitted_responses"]) == 1
    assert emitted["emitted_responses"] == queued["pending_responses"]

    session.handle({"type": "response.create"})
    assert session.snapshot()["emitted_responses"] == emitted["emitted_responses"]
    assert session.snapshot()["event_log"][-1]["outcome"] == "create_ignored"


def test_cancel_discards_an_answer_before_it_is_emitted():
    session = realtime_voice.RealtimeSession()
    session.handle({"type": "transcript.final", "text": "讲个笑话"})
    session.handle({"type": "response.cancel"})
    cancelled = session.snapshot()

    assert cancelled["pending_responses"] == []
    assert cancelled["emitted_responses"] == []
    assert len(cancelled["cancelled_responses"]) == 1
    assert cancelled["cancelled_responses"][0]["text"] == "确定性回答：讲个笑话"

    session.handle({"type": "response.create"})
    assert session.snapshot()["emitted_responses"] == []


def test_cancel_cannot_unsend_an_emitted_answer():
    session = realtime_voice.RealtimeSession()
    session.handle({"type": "transcript.final", "text": "你好"})
    session.handle({"type": "response.create"})
    session.handle({"type": "response.cancel"})
    state = session.snapshot()

    assert len(state["emitted_responses"]) == 1
    assert state["cancelled_responses"] == []
    assert state["event_log"][-1]["outcome"] == "cancel_ignored"


def test_minimal_path_preserves_event_order_and_cancels_once():
    result = realtime_voice.run_minimal_path()
    assert [(item["event"], item["outcome"]) for item in result["event_log"]] == [
        ("transcript.partial", "transcript_updated"),
        ("transcript.partial", "transcript_updated"),
        ("transcript.partial", "transcript_updated"),
        ("transcript.final", "response_queued"),
        ("response.create", "response_emitted"),
        ("transcript.final", "response_queued"),
        ("response.cancel", "response_cancelled"),
    ]
    assert [item["text"] for item in result["emitted_responses"]] == [
        "确定性回答：请帮我总结"
    ]
    assert [item["text"] for item in result["cancelled_responses"]] == [
        "确定性回答：讲个笑话"
    ]
    assert result["pending_responses"] == []


def test_results_are_deterministic_and_main_prints_json(capsys):
    first = realtime_voice.run_minimal_path()
    second = realtime_voice.run_minimal_path()
    assert first == second

    realtime_voice.main()
    printed = capsys.readouterr().out
    assert json.loads(printed) == first
