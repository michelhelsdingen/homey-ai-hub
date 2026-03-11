"""Ollama local model provider implementation."""
from ollama import AsyncClient, ResponseError

from lib.providers.base import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM provider wrapping the Ollama local model server.

    Uses ollama.AsyncClient exclusively — the sync client blocks Homey's event loop.
    Defaults to 120s timeout to handle cold model loading (models unload after 5min idle).
    """

    DEFAULT_HOST = "http://192.168.2.214:11434"
    DEFAULT_TIMEOUT = 120.0

    def __init__(self, host: str = DEFAULT_HOST, timeout: float = DEFAULT_TIMEOUT) -> None:
        """Initialize with Ollama server URL and timeout.

        Args:
            host: Ollama server URL, e.g. "http://192.168.2.214:11434".
            timeout: Request timeout in seconds (default 120s for cold starts).
        """
        self._host = host
        self._timeout = timeout
        self._client = AsyncClient(host=host, timeout=timeout)

    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Send messages to Ollama and return the response text."""
        try:
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + list(messages)
            response = await self._client.chat(
                model=model,
                messages=messages,
            )
            return response.message.content
        except ResponseError as e:
            return f"Error: Ollama error: {e}"
        except (ConnectionError, OSError) as e:
            return f"Error: Cannot reach Ollama at {self._host}: {e}"
        except Exception as e:
            return f"Error: Unexpected Ollama error: {e}"

    async def list_models(self) -> list[str]:
        """Return currently installed Ollama model names.

        Returns empty list if Ollama is unreachable (graceful degradation).
        """
        try:
            models_response = await self._client.list()
            return [m.model for m in models_response.models]
        except Exception:
            return []

    async def test_connection(self) -> tuple[bool, str]:
        """Test Ollama connectivity by listing installed models."""
        try:
            models = await self._client.list()
            model_names = [m.model for m in models.models]
            count = len(model_names)
            if count == 0:
                return (True, f"Ollama connected at {self._host} — no models installed yet")
            return (True, f"Ollama OK at {self._host} — {count} model(s): {', '.join(model_names[:3])}")
        except (ConnectionError, OSError) as e:
            return (False, f"Cannot reach Ollama at {self._host}: {e}")
        except Exception as e:
            return (False, f"Ollama connection failed: {e}")
