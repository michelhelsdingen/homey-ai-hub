"""Per-session conversation history store with sliding window eviction."""
from __future__ import annotations


class ConversationStore:
    """Map conversation_id -> list[dict] message history.

    Storage is in-memory. Pass a Homey settings object to enable
    persistence across app restarts via homey.settings.
    """

    SETTINGS_KEY_PREFIX = "conv_"

    def __init__(self, settings=None, max_turns: int = 10) -> None:
        self._sessions: dict[str, list[dict]] = {}
        self._settings = settings
        self._max_turns = max_turns

    def get(self, conversation_id: str) -> list[dict]:
        """Return current history for conversation_id (empty list if new)."""
        if conversation_id not in self._sessions:
            if self._settings:
                stored = self._settings.get(f"{self.SETTINGS_KEY_PREFIX}{conversation_id}")
                self._sessions[conversation_id] = stored if isinstance(stored, list) else []
            else:
                self._sessions[conversation_id] = []
        return self._sessions[conversation_id]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        """Append a message and enforce sliding window."""
        history = self.get(conversation_id)
        history.append({"role": role, "content": content})
        self._trim(conversation_id)
        self._persist(conversation_id)

    def clear(self, conversation_id: str) -> None:
        """Delete all history for a conversation_id."""
        self._sessions.pop(conversation_id, None)
        if self._settings:
            self._settings.unset(f"{self.SETTINGS_KEY_PREFIX}{conversation_id}")

    def _trim(self, conversation_id: str) -> None:
        """Keep last max_turns exchanges (2 messages per turn)."""
        history = self._sessions.get(conversation_id, [])
        max_messages = self._max_turns * 2
        if len(history) > max_messages:
            self._sessions[conversation_id] = history[-max_messages:]

    def _persist(self, conversation_id: str) -> None:
        if self._settings:
            self._settings.set(
                f"{self.SETTINGS_KEY_PREFIX}{conversation_id}",
                self._sessions[conversation_id],
            )
