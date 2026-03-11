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


class TestOllamaProviderChatWithImage:
    async def test_chat_with_image_returns_response_for_vision_model(self, ollama_provider):
        mock_response = MagicMock()
        mock_response.message.content = "I see a living room."

        with patch.object(ollama_provider._client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            result = await ollama_provider.chat_with_image(
                prompt="What is in this image?",
                image_bytes=b"\xff\xd8\xff" + b"\x00" * 100,
                media_type="image/jpeg",
                model="llava:13b",
            )

        assert result == "I see a living room."

    async def test_chat_with_image_rejects_non_vision_model(self, ollama_provider):
        result = await ollama_provider.chat_with_image(
            prompt="Describe this.",
            image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
            media_type="image/jpeg",
            model="llama3.1:8b",
        )
        assert result.startswith("Error:")
        assert "vision" in result.lower()

    async def test_chat_with_image_passes_image_bytes_in_messages(self, ollama_provider):
        mock_response = MagicMock()
        mock_response.message.content = "Looks like a kitchen."

        image_data = b"\xff\xd8\xff" + b"\x00" * 80
        captured_kwargs = {}

        async def capture_chat(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(ollama_provider._client, "chat", side_effect=capture_chat):
            await ollama_provider.chat_with_image(
                prompt="What room is this?",
                image_bytes=image_data,
                media_type="image/jpeg",
                model="llava:7b",
            )

        messages = captured_kwargs.get("messages", [])
        user_message = next((m for m in messages if m.get("role") == "user"), None)
        assert user_message is not None
        assert user_message.get("images") == [image_data]

    async def test_chat_with_image_returns_error_on_connection_failure(self, ollama_provider):
        with patch.object(ollama_provider._client, "chat", new_callable=AsyncMock) as mock_chat:
            mock_chat.side_effect = ConnectionError("Connection refused")
            result = await ollama_provider.chat_with_image(
                prompt="Describe this.",
                image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
                media_type="image/jpeg",
                model="llava:13b",
            )
        assert result.startswith("Error:")
