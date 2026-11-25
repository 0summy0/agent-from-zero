"""Chapter 4.3: an event-driven realtime voice session without audio I/O."""

from __future__ import annotations

import json
from collections.abc import Mapping

CHAPTER_ID = "4.3-realtime-voice"
EVENT_TYPES = (
    "transcript.partial",
    "transcript.final",
    "response.create",
    "response.cancel",
)


def deterministic_answer(text: str) -> str:
    """Return a stable teaching response; no model or network is involved."""
    return f"确定性回答：{text}"


class RealtimeSession:
    """Track transcript turns and responses as ordered text events arrive."""

    def __init__(self) -> None:
        self._current_transcript = ""
        self._final_transcripts: list[str] = []
        self._pending_responses: list[dict[str, str]] = []
        self._emitted_responses: list[dict[str, str]] = []
        self._cancelled_responses: list[dict[str, str]] = []
        self._event_log: list[dict[str, object]] = []
        self._next_response_id = 1

    def _queue_response(self, text: str) -> dict[str, str]:
        response = {
            "response_id": f"response-{self._next_response_id}",
            "source_text": text,
            "text": deterministic_answer(text),
        }
        self._next_response_id += 1
        self._pending_responses.append(response)
        return response

    def snapshot(self) -> dict[str, object]:
        """Return a detached, JSON-serializable copy of the session state."""
        return {
            "current_transcript": self._current_transcript,
            "final_transcripts": list(self._final_transcripts),
            "pending_responses": [dict(item) for item in self._pending_responses],
            "emitted_responses": [dict(item) for item in self._emitted_responses],
            "cancelled_responses": [dict(item) for item in self._cancelled_responses],
            "event_log": [dict(item) for item in self._event_log],
        }

    def handle(self, event: Mapping[str, object]) -> dict[str, object]:
        """Apply one event and return the resulting state snapshot."""
        if not isinstance(event, Mapping):
            raise TypeError("event must be a mapping")
        event_type = event.get("type")
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event_type!r}")

        if event_type in ("transcript.partial", "transcript.final"):
            text = event.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("transcript events require non-empty text")
            if event_type == "transcript.partial":
                self._current_transcript = text
                record: dict[str, object] = {
                    "event": event_type,
                    "text": text,
                    "outcome": "transcript_updated",
                }
            else:
                self._final_transcripts.append(text)
                self._current_transcript = ""
                response = self._queue_response(text)
                record = {
                    "event": event_type,
                    "text": text,
                    "outcome": "response_queued",
                    "response_id": response["response_id"],
                }
        elif event_type == "response.create":
            if self._pending_responses:
                response = self._pending_responses.pop(0)
                self._emitted_responses.append(response)
                record = {
                    "event": event_type,
                    "outcome": "response_emitted",
                    "response_id": response["response_id"],
                }
            else:
                record = {"event": event_type, "outcome": "create_ignored"}
        else:
            target_id = event.get("response_id")
            if target_id is not None and (
                not isinstance(target_id, str) or not target_id.strip()
            ):
                raise ValueError("response_id must be a non-empty string")
            if target_id is None:
                cancelled = self._pending_responses
                self._pending_responses = []
                self._cancelled_responses.extend(cancelled)
                if len(cancelled) == 1:
                    record = {
                        "event": event_type,
                        "outcome": "response_cancelled",
                        "response_id": cancelled[0]["response_id"],
                    }
                elif cancelled:
                    record = {
                        "event": event_type,
                        "outcome": "responses_cancelled",
                        "response_ids": [item["response_id"] for item in cancelled],
                    }
                else:
                    record = {"event": event_type, "outcome": "cancel_ignored"}
            else:
                match = next(
                    (
                        index
                        for index, item in enumerate(self._pending_responses)
                        if item["response_id"] == target_id
                    ),
                    None,
                )
                if match is None:
                    record = {"event": event_type, "outcome": "cancel_ignored"}
                else:
                    response = self._pending_responses.pop(match)
                    self._cancelled_responses.append(response)
                    record = {
                        "event": event_type,
                        "outcome": "response_cancelled",
                        "response_id": response["response_id"],
                    }

        self._event_log.append(record)
        return self.snapshot()

    def handle_event(self, event: Mapping[str, object]) -> dict[str, object]:
        """Alias for handle(), spelling out that the input is an event."""
        return self.handle(event)


def run_minimal_path() -> dict[str, object]:
    """Demonstrate partial transcripts, one emitted answer, and one cancel."""
    session = RealtimeSession()
    events = (
        {"type": "transcript.partial", "text": "请"},
        {"type": "transcript.partial", "text": "请帮我"},
        {"type": "transcript.partial", "text": "请帮我总结"},
        {"type": "transcript.final", "text": "请帮我总结"},
        {"type": "response.create"},
        {"type": "transcript.final", "text": "讲个笑话"},
        {"type": "response.cancel"},
    )
    for event in events:
        session.handle(event)
    return {"chapter": CHAPTER_ID, **session.snapshot()}


def main() -> None:
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
