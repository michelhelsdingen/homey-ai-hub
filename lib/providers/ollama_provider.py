"""Ollama local model provider implementation."""
from ollama import AsyncClient, ResponseError

from lib.providers.base import LLMProvider, ToolCall, ToolRoundResult


class OllamaProvider(LLMProvider):
    """LLM provider wrapping the Ollama local model server.

    Uses ollama.AsyncClient exclusively — the sync client blocks Homey's event loop.
    Defaults to 120s timeout to handle cold model loading (models unload after 5min idle).
    """

    DEFAULT_HOST = "http://192.168.2.214:11434"
    DEFAULT_TIMEOUT = 120.0
    VISION_MODELS = {"llava", "llava-phi3", "moondream", "qwen2.5vl", "llama3.2-vision", "bakllava", "minicpm-v"}

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

    async def chat_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        media_type: str,
        model: str,
        timeout: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Send a prompt + image to Ollama and return the response text."""
        is_vision = any(model.startswith(vm) for vm in self.VISION_MODELS)
        if not is_vision:
            return (
                f"Error: Model '{model}' does not support vision. "
                "Use a vision model (e.g. llava, qwen2.5vl, llama3.2-vision)."
            )
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt, "images": [image_bytes]})
            response = await self._client.chat(model=model, messages=messages)
            return response.message.content
        except ResponseError as e:
            return f"Error: Ollama error: {e}"
        except (ConnectionError, OSError) as e:
            return f"Error: Cannot reach Ollama at {self._host}: {e}"
        except Exception as e:
            return f"Error: Unexpected Ollama error: {e}"

    async def chat_with_tools_round(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict],
        system_prompt: str | None = None,
    ) -> ToolRoundResult:
        """Single round of Ollama tool-use chat."""
        ollama_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
            for t in tools
        ]
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        try:
            response = await self._client.chat(model=model, messages=msgs, tools=ollama_tools)
        except ResponseError as e:
            return ToolRoundResult(text=f"Error: Ollama error: {e}")
        except (ConnectionError, OSError) as e:
            return ToolRoundResult(text=f"Error: Cannot reach Ollama: {e}")

        if response.message.tool_calls:
            tool_calls = []
            for tc in response.message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.function.name,  # Ollama has no tool_call_id
                    name=tc.function.name,
                    arguments=tc.function.arguments,  # Already a dict in Ollama
                ))
            raw = [{"role": "assistant", "content": response.message.content or "", "tool_calls": [{"function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in response.message.tool_calls]}]
            return ToolRoundResult(text=None, tool_calls=tool_calls, raw_messages=raw)

        return ToolRoundResult(text=response.message.content or "")

    def format_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> list[dict]:
        """Format tool result for Ollama."""
        return [{"role": "tool", "content": result}]

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
