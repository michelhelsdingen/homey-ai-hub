"""Unit tests for ConversationStore."""
import pytest
from unittest.mock import MagicMock

from lib.conversation_store import ConversationStore


@pytest.fixture
def store():
    """ConversationStore without settings (in-memory only)."""
    return ConversationStore()


@pytest.fixture
def mock_settings():
    """Mock Homey settings object (all methods synchronous)."""
    settings = MagicMock()
    settings.get = MagicMock(return_value=None)
    settings.set = MagicMock()
    settings.unset = MagicMock()
    return settings


@pytest.fixture
def store_with_settings(mock_settings):
    """ConversationStore with mock settings for persistence tests."""
    return ConversationStore(settings=mock_settings), mock_settings


class TestGetMethod:
    """Tests for ConversationStore.get()."""

    def test_get_returns_empty_list_for_unknown_id(self, store):
        """get() returns an empty list for an unknown conversation_id."""
        result = store.get("unknown-id")
        assert result == []

    def test_get_returns_empty_list_for_another_unknown_id(self, store):
        """get() returns empty list for any new conversation_id."""
        assert store.get("session-abc") == []
        assert store.get("session-xyz") == []

    def test_get_restores_from_settings_on_first_access(self):
        """get() loads history from settings when settings contains a stored list."""
        mock_settings = MagicMock()
        stored_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        mock_settings.get = MagicMock(return_value=stored_history)
        s = ConversationStore(settings=mock_settings)

        result = s.get("session-1")

        assert result == stored_history
        mock_settings.get.assert_called_once_with("conv_session-1")

    def test_get_returns_empty_when_settings_returns_non_list(self):
        """get() returns empty list when settings returns non-list value."""
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value="invalid-string")
        s = ConversationStore(settings=mock_settings)

        result = s.get("session-1")

        assert result == []

    def test_get_returns_empty_when_settings_returns_none(self):
        """get() returns empty list when settings returns None."""
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        s = ConversationStore(settings=mock_settings)

        result = s.get("session-1")

        assert result == []


class TestAppendMethod:
    """Tests for ConversationStore.append()."""

    def test_append_adds_message_retrievable_via_get(self, store):
        """append() adds a message that is retrievable via get()."""
        store.append("session-1", "user", "Hello")
        result = store.get("session-1")
        assert result == [{"role": "user", "content": "Hello"}]

    def test_append_multiple_messages_preserves_order(self, store):
        """append() preserves message order."""
        store.append("session-1", "user", "Hello")
        store.append("session-1", "assistant", "Hi there")
        store.append("session-1", "user", "How are you?")

        result = store.get("session-1")
        assert len(result) == 3
        assert result[0] == {"role": "user", "content": "Hello"}
        assert result[1] == {"role": "assistant", "content": "Hi there"}
        assert result[2] == {"role": "user", "content": "How are you?"}

    def test_append_different_conversations_are_isolated(self, store):
        """append() keeps different conversation_ids isolated."""
        store.append("session-A", "user", "Message in A")
        store.append("session-B", "user", "Message in B")

        assert store.get("session-A") == [{"role": "user", "content": "Message in A"}]
        assert store.get("session-B") == [{"role": "user", "content": "Message in B"}]


class TestTrimMethod:
    """Tests for ConversationStore._trim() (sliding window eviction)."""

    def test_trim_enforces_max_turns_times_two_cap(self):
        """_trim() caps messages at max_turns * 2, evicting oldest."""
        s = ConversationStore(max_turns=2)  # max 4 messages
        s.append("sess", "user", "msg1")
        s.append("sess", "assistant", "msg2")
        s.append("sess", "user", "msg3")
        s.append("sess", "assistant", "msg4")
        # Now at cap — adding one more should evict oldest
        s.append("sess", "user", "msg5")

        result = s.get("sess")
        assert len(result) == 4  # max_turns * 2 = 4
        assert result[0]["content"] == "msg2"  # msg1 was evicted
        assert result[-1]["content"] == "msg5"

    def test_trim_evicts_oldest_messages(self):
        """_trim() always evicts from the beginning (oldest messages first)."""
        s = ConversationStore(max_turns=1)  # max 2 messages
        s.append("sess", "user", "old1")
        s.append("sess", "assistant", "old2")
        s.append("sess", "user", "new1")  # triggers eviction of old1

        result = s.get("sess")
        assert len(result) == 2
        assert result[0]["content"] == "old2"
        assert result[1]["content"] == "new1"

    def test_trim_does_not_evict_within_limit(self):
        """_trim() does not evict when under the limit."""
        s = ConversationStore(max_turns=5)  # max 10 messages
        for i in range(8):
            s.append("sess", "user", f"msg{i}")

        result = s.get("sess")
        assert len(result) == 8

    def test_default_max_turns_is_ten(self):
        """Default max_turns is 10, so up to 20 messages are kept."""
        s = ConversationStore()
        for i in range(20):
            s.append("sess", "user", f"msg{i}")

        result = s.get("sess")
        assert len(result) == 20

    def test_trim_removes_extra_when_exceeds_limit(self):
        """_trim() enforces the limit after each append."""
        s = ConversationStore(max_turns=10)  # max 20
        for i in range(25):
            s.append("sess", "user", f"msg{i}")

        result = s.get("sess")
        assert len(result) == 20
        assert result[0]["content"] == "msg5"  # first 5 evicted


class TestClearMethod:
    """Tests for ConversationStore.clear()."""

    def test_clear_removes_session_from_memory(self, store):
        """clear() removes the session so get() returns empty list."""
        store.append("session-1", "user", "Hello")
        store.clear("session-1")

        assert store.get("session-1") == []

    def test_clear_calls_settings_unset_once(self):
        """clear() calls settings.unset() exactly once with correct key."""
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        mock_settings.set = MagicMock()
        mock_settings.unset = MagicMock()
        s = ConversationStore(settings=mock_settings)

        s.append("session-1", "user", "Hello")
        s.clear("session-1")

        mock_settings.unset.assert_called_once_with("conv_session-1")

    def test_clear_on_unknown_id_does_not_raise(self, store):
        """clear() on a non-existent session_id does not raise."""
        store.clear("never-existed")  # Should not raise

    def test_clear_does_not_call_unset_without_settings(self, store):
        """clear() without settings does not fail."""
        store.append("session-1", "user", "Hello")
        store.clear("session-1")  # Should complete without error
        assert store.get("session-1") == []


class TestPersistMethod:
    """Tests for ConversationStore._persist()."""

    def test_persist_calls_settings_set_with_correct_key(self):
        """_persist() calls settings.set() with the correct prefixed key."""
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        mock_settings.set = MagicMock()
        mock_settings.unset = MagicMock()
        s = ConversationStore(settings=mock_settings)

        s.append("my-session", "user", "Hello")

        mock_settings.set.assert_called_with(
            "conv_my-session",
            [{"role": "user", "content": "Hello"}],
        )

    def test_persist_updates_after_each_append(self):
        """_persist() is called after every append."""
        mock_settings = MagicMock()
        mock_settings.get = MagicMock(return_value=None)
        mock_settings.set = MagicMock()
        mock_settings.unset = MagicMock()
        s = ConversationStore(settings=mock_settings)

        s.append("sess", "user", "msg1")
        s.append("sess", "assistant", "msg2")

        # set() called twice (once per append)
        assert mock_settings.set.call_count == 2

    def test_persist_does_not_call_set_without_settings(self, store):
        """_persist() does nothing when no settings provided."""
        store.append("sess", "user", "Hello")
        # No error raised, no settings calls
