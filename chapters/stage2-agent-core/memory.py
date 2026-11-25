import json

CHAPTER_ID = "2.4-memory-context"
KEY_FACT = "My timezone is UTC+8 and my preferred editor is Vim."


class MemoryStore:
    """Keep a recent message window plus a lossy summary of older messages."""

    def __init__(self, max_messages=3, char_budget=240, summary_message_chars=80):
        if isinstance(max_messages, bool) or not isinstance(max_messages, int) or max_messages < 1:
            raise ValueError("max_messages must be a positive integer")
        if isinstance(char_budget, bool) or not isinstance(char_budget, int) or char_budget < 1:
            raise ValueError("char_budget must be a positive integer")
        if (
            isinstance(summary_message_chars, bool)
            or not isinstance(summary_message_chars, int)
            or summary_message_chars < 4
        ):
            raise ValueError("summary_message_chars must be an integer of at least 4")

        self.max_messages = max_messages
        self.char_budget = char_budget
        self.summary_message_chars = summary_message_chars
        self.messages = []
        self.summary = ""
        self.evicted_count = 0

    def _summarize_content(self, content):
        compact = " ".join(content.split())
        if len(compact) > self.summary_message_chars:
            return compact[: self.summary_message_chars - 3] + "..."
        return compact

    def add_message(self, role, content):
        """Append one message and return any messages evicted from the window."""
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")

        self.messages.append({"role": role, "content": content})
        evicted = []
        while len(self.messages) > self.max_messages:
            old_message = self.messages.pop(0)
            compact = self._summarize_content(old_message["content"])
            fragment = f"{old_message['role']}: {compact}"
            self.summary = f"{self.summary} | {fragment}" if self.summary else fragment
            self.evicted_count += 1
            evicted.append(dict(old_message))
        return evicted

    def _full_context(self):
        sections = []
        if self.summary:
            sections.append(f"Earlier summary: {self.summary}")
        sections.append("Recent messages:")
        sections.extend(f"{message['role']}: {message['content']}" for message in self.messages)
        return "\n".join(sections)

    def build_context(self):
        """Pack summary and recent messages, dropping oldest text if over budget."""
        text = self._full_context()
        if len(text) <= self.char_budget:
            return text
        if self.char_budget <= 3:
            return text[: self.char_budget]
        return "..." + text[-(self.char_budget - 3) :]

    def snapshot(self):
        """Return a JSON-serializable view without exposing mutable internals."""
        context = self.build_context()
        return {
            "max_messages": self.max_messages,
            "char_budget": self.char_budget,
            "summary_message_chars": self.summary_message_chars,
            "summary": self.summary,
            "recent_messages": [dict(message) for message in self.messages],
            "recent_message_count": len(self.messages),
            "evicted_message_count": self.evicted_count,
            "context": context,
            "context_chars": len(context),
            "approximate_tokens": (len(context) + 3) // 4,
            "truncated": len(self._full_context()) > self.char_budget,
        }


def run_minimal_path():
    store = MemoryStore(max_messages=3, char_budget=420)
    messages = [
        ("user", KEY_FACT),
        ("assistant", "Understood."),
        ("user", "I am learning how agents use context."),
        ("assistant", "Keep important facts available."),
        ("user", "The local calculator returned 12."),
        ("assistant", "That result is now part of the recent context."),
    ]

    evicted_messages = []
    for role, content in messages:
        evicted_messages.extend(store.add_message(role, content))

    snapshot = store.snapshot()
    recent_text = "\n".join(message["content"] for message in snapshot["recent_messages"])
    return {
        "chapter": CHAPTER_ID,
        "key_fact": KEY_FACT,
        "evicted_message_count": snapshot["evicted_message_count"],
        "window_contains_key_fact": KEY_FACT in recent_text,
        "summary_contains_key_fact": KEY_FACT in snapshot["summary"],
        "evicted_messages": evicted_messages,
        "snapshot": snapshot,
    }


def main():
    print(json.dumps(run_minimal_path(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
