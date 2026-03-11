"""Claude (Anthropic) provider implementation."""
import httpx
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError, APIStatusError

from lib.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """LLM provider wrapping the Anthropic Claude API.

    Uses AsyncAnthropic exclusively — the sync client blocks Homey's event loop.
    Sets max_retries=0 for fast-fail behavior in Flow context.
    """

    MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize with API key and timeout.

        Args:
            api_key: Anthropic API key (sk-ant-...).
            timeout: Request timeout in seconds (default 30s).
        """
        self._api_key = api_key
        self._timeout = timeout
        self._client = AsyncAnthropic(
            api_key=api_key,
            http_client=httpx.AsyncClient(timeout=timeout),
            max_retries=0,  # Fast-fail — let Flow handle retry
        )

    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
    ) -> str:
        """Send messages to Claude and return the response text."""
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages,
            )
            return response.content[0].text
        except RateLimitError:
            return "Error: Claude rate limited. Please wait 30 seconds and retry."
        except APIConnectionError as e:
            return f"Error: Cannot reach Claude API: {e}"
        except APIStatusError as e:
            return f"Error: Claude API error {e.status_code}: {e.message}"
        except Exception as e:
            return f"Error: Unexpected Claude error: {e}"

    async def list_models(self) -> list[str]:
        """Return supported Claude models (static list)."""
        return list(self.MODELS)

    async def test_connection(self) -> tuple[bool, str]:
        """Test Claude connectivity by sending a minimal message."""
        try:
            response = await self._client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return (True, "Claude connection OK")
        except RateLimitError:
            return (False, "Claude rate limited — API key valid but quota exceeded")
        except APIConnectionError as e:
            return (False, f"Cannot reach Claude API: {e}")
        except APIStatusError as e:
            if e.status_code == 401:
                return (False, "Claude API key invalid or expired")
            return (False, f"Claude API error {e.status_code}: {e.message}")
        except Exception as e:
            return (False, f"Claude connection failed: {e}")
