"""Unit tests for ClaudeProvider — all HTTP calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from lib.providers.claude import ClaudeProvider


@pytest.fixture
def claude_provider():
    return ClaudeProvider(api_key="sk-ant-test-key", timeout=5.0)


class TestClaudeProviderChat:
    async def test_chat_returns_response_text(self, claude_provider):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Paris is the capital of France.")]

        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await claude_provider.chat(
                messages=[{"role": "user", "content": "What is the capital of France?"}],
                model="claude-haiku-4-5",
            )

        assert result == "Paris is the capital of France."

    async def test_chat_returns_error_on_rate_limit(self, claude_provider):
        from anthropic import RateLimitError
        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = RateLimitError(
                message="rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )
            result = await claude_provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="claude-haiku-4-5",
            )
        assert result.startswith("Error:")
        assert "rate" in result.lower()

    async def test_chat_returns_error_on_connection_failure(self, claude_provider):
        from anthropic import APIConnectionError
        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = APIConnectionError(request=MagicMock())
            result = await claude_provider.chat(
                messages=[{"role": "user", "content": "hi"}],
                model="claude-haiku-4-5",
            )
        assert result.startswith("Error:")


class TestClaudeProviderListModels:
    async def test_list_models_returns_static_list(self, claude_provider):
        models = await claude_provider.list_models()
        assert isinstance(models, list)
        assert len(models) == 3
        assert "claude-haiku-4-5" in models
        assert "claude-sonnet-4-5" in models
        assert "claude-opus-4-5" in models


class TestClaudeProviderTestConnection:
    async def test_test_connection_returns_true_on_success(self, claude_provider):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hi")]

        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            success, message = await claude_provider.test_connection()

        assert success is True
        assert "OK" in message or "Claude" in message

    async def test_test_connection_returns_false_on_invalid_key(self, claude_provider):
        from anthropic import APIStatusError
        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = APIStatusError(
                message="unauthorized",
                response=MagicMock(status_code=401, headers={}),
                body={},
            )
            success, message = await claude_provider.test_connection()

        assert success is False
        assert "invalid" in message.lower() or "401" in message


class TestClaudeProviderChatWithImage:
    async def test_chat_with_image_returns_response_text(self, claude_provider):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="The image shows a cat.")]

        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await claude_provider.chat_with_image(
                prompt="What is in this image?",
                image_bytes=b"\xff\xd8\xff" + b"\x00" * 100,  # small JPEG-like bytes
                media_type="image/jpeg",
                model="claude-haiku-4-5",
            )

        assert isinstance(result, str)
        assert result == "The image shows a cat."

    async def test_chat_with_image_normalizes_jpg_media_type(self, claude_provider):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="A photo.")]

        captured_kwargs = {}

        async def capture_create(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(claude_provider._client.messages, "create", side_effect=capture_create):
            await claude_provider.chat_with_image(
                prompt="Describe this.",
                image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
                media_type="image/jpg",
                model="claude-haiku-4-5",
            )

        # Verify the media_type was normalized to image/jpeg
        messages = captured_kwargs.get("messages", [])
        image_block = messages[0]["content"][0]
        assert image_block["source"]["media_type"] == "image/jpeg"

    async def test_chat_with_image_rejects_large_image(self, claude_provider):
        large_bytes = b"\x00" * 5_000_001
        result = await claude_provider.chat_with_image(
            prompt="What is this?",
            image_bytes=large_bytes,
            media_type="image/jpeg",
            model="claude-haiku-4-5",
        )
        assert result.startswith("Error:")
        assert "5MB" in result

    async def test_chat_with_image_returns_error_on_api_error(self, claude_provider):
        from anthropic import APIStatusError
        with patch.object(claude_provider._client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = APIStatusError(
                message="bad request",
                response=MagicMock(status_code=400, headers={}),
                body={},
            )
            result = await claude_provider.chat_with_image(
                prompt="Describe this.",
                image_bytes=b"\xff\xd8\xff" + b"\x00" * 50,
                media_type="image/jpeg",
                model="claude-haiku-4-5",
            )
        assert result.startswith("Error:")
