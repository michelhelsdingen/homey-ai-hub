"""OpenAI provider implementation."""
import base64
import json
import httpx
from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError

from lib.providers.base import LLMProvider, ToolCall, ToolRoundResult


class OpenAIProvider(LLMProvider):
    """LLM provider wrapping the OpenAI API.

    Uses AsyncOpenAI exclusively — the sync client blocks Homey's event loop.
    """

    MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-nano",
        "gpt-4.1-mini",
        "gpt-4.1",
        "o4-mini",
    ]
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key
        self._timeout = timeout
        self._client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )

    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        try:
            msgs = list(messages)
            if system_prompt:
                msgs.insert(0, {"role": "system", "content": system_prompt})

            response = await self._client.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except RateLimitError:
            return "Error: OpenAI rate limited. Please wait and retry."
        except APIConnectionError as e:
            return f"Error: Cannot reach OpenAI API: {e}"
        except APIStatusError as e:
            return f"Error: OpenAI API error {e.status_code}: {e.message}"
        except Exception as e:
            return f"Error: Unexpected OpenAI error: {e}"

    async def chat_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        media_type: str,
        model: str,
        timeout: float | None = None,
        system_prompt: str | None = None,
    ) -> str:
        if len(image_bytes) > 20_000_000:
            return "Error: Image too large (>20MB)."
        if media_type == "image/jpg":
            media_type = "image/jpeg"
        try:
            image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{media_type};base64,{image_data}"

            msgs: list[dict] = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            })

            response = await self._client.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except RateLimitError:
            return "Error: OpenAI rate limited. Please wait and retry."
        except APIConnectionError as e:
            return f"Error: Cannot reach OpenAI API: {e}"
        except APIStatusError as e:
            return f"Error: OpenAI API error {e.status_code}: {e.message}"
        except Exception as e:
            return f"Error: Unexpected OpenAI error: {e}"

    async def chat_with_tools_round(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict],
        system_prompt: str | None = None,
    ) -> ToolRoundResult:
        """Single round of OpenAI tool-use chat."""
        openai_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
            for t in tools
        ]
        msgs = list(messages)
        if system_prompt:
            msgs.insert(0, {"role": "system", "content": system_prompt})

        try:
            response = await self._client.chat.completions.create(
                model=model, messages=msgs, tools=openai_tools, max_tokens=1024,
            )
        except RateLimitError:
            return ToolRoundResult(text="Error: OpenAI rate limited. Wait a moment and try again.")
        except APIConnectionError as e:
            return ToolRoundResult(text=f"Error: Cannot reach OpenAI API: {e}")
        except APIStatusError as e:
            return ToolRoundResult(text=f"Error: OpenAI API error {e.status_code}: {e.message}")

        msg = response.choices[0].message

        if response.choices[0].finish_reason == "tool_calls" and msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))
            raw = [{"role": "assistant", "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in msg.tool_calls]}]
            return ToolRoundResult(text=None, tool_calls=tool_calls, raw_messages=raw)

        return ToolRoundResult(text=msg.content or "")

    def format_tool_result(self, tool_call_id: str, tool_name: str, result: str) -> list[dict]:
        """Format tool result for OpenAI."""
        return [{"role": "tool", "tool_call_id": tool_call_id, "content": result}]

    async def list_models(self) -> list[str]:
        """Return curated list of popular OpenAI models."""
        return list(self.MODELS)

    async def test_connection(self) -> tuple[bool, str]:
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return (True, "OpenAI connection OK")
        except RateLimitError:
            return (False, "OpenAI rate limited — API key valid but quota exceeded")
        except APIConnectionError as e:
            return (False, f"Cannot reach OpenAI API: {e}")
        except APIStatusError as e:
            if e.status_code == 401:
                return (False, "OpenAI API key invalid or expired")
            return (False, f"OpenAI API error {e.status_code}: {e.message}")
        except Exception as e:
            return (False, f"OpenAI connection failed: {e}")
