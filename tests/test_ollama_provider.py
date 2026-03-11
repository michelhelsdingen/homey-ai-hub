"""Unit tests for OllamaProvider — all HTTP calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lib.providers.ollama_provider import OllamaProvider


@pytest.fixture
def ollama_provider():
    return OllamaProvider(host="http://192.168.2.214:11434", timeout=5.0)


def _make_model(name: str):
    m = MagicMock()
    m.model = name
    return m


class TestOllamaProviderChat:
    async def test_chat_returns_response_text(self, ollama_provider):
        mock_response = MagicMock()
        mock_response.message.content = "The sky is blue."

        with patch.object(ollama_provider._client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            result = await ollama_provider.chat(
                messages=[{"role": "user", "content": "Why is the sky blue?"}],
                model="llama3.1:8b",
            )

        assert result == "The sky is blue."

    async def test_chat_returns_error_on_response_error(self, ollama_provider):
        from ollama import ResponseError
        with patch.object(ollama_provider._client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = ResponseError("model not found")
            result = await ollama_provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="nonexistent:model",
            )
        assert result.startswith("Error:")

    async def test_chat_returns_error_on_connection_failure(self, ollama_provider):
        with patch.object(ollama_provider._client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = ConnectionError("Connection refused")
            result = await ollama_provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="llama3.1:8b",
            )
        assert result.startswith("Error:")
        assert "192.168.2.214" in result


class TestOllamaProviderListModels:
    async def test_list_models_returns_model_names(self, ollama_provider):
        mock_list = MagicMock()
        mock_list.models = [_make_model("llama3.1:8b"), _make_model("llama3.1:70b")]

        with patch.object(ollama_provider._client, "list", new_callable=AsyncMock) as mock_list_fn:
            mock_list_fn.return_value = mock_list
            models = await ollama_provider.list_models()

        assert models == ["llama3.1:8b", "llama3.1:70b"]

    async def test_list_models_returns_empty_on_error(self, ollama_provider):
        with patch.object(ollama_provider._client, "list", new_callable=AsyncMock) as mock_list_fn:
            mock_list_fn.side_effect = ConnectionError("unreachable")
            models = await ollama_provider.list_models()
        assert models == []


class TestOllamaProviderTestConnection:
    async def test_test_connection_returns_true_with_models(self, ollama_provider):
        mock_list = MagicMock()
        mock_list.models = [_make_model("llama3.1:8b")]

        with patch.object(ollama_provider._client, "list", new_callable=AsyncMock) as mock_list_fn:
            mock_list_fn.return_value = mock_list
            success, message = await ollama_provider.test_connection()

        assert success is True
        assert "Ollama" in message

    async def test_test_connection_returns_false_on_unreachable(self, ollama_provider):
        with patch.object(ollama_provider._client, "list", new_callable=AsyncMock) as mock_list_fn:
            mock_list_fn.side_effect = ConnectionError("refused")
            success, message = await ollama_provider.test_connection()

        assert success is False
        assert "192.168.2.214" in message
