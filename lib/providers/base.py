"""Abstract base class for all LLM providers."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Common interface for all AI provider implementations.

    Providers are pure Python — no Homey SDK dependency.
    All methods are async to support non-blocking HTTP calls.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
    ) -> str:
        """Send messages to the AI and return the assistant response text.

        Args:
            messages: OpenAI-compatible message list, e.g.
                [{"role": "user", "content": "Hello"}]
            model: Model ID string (provider-specific)
            timeout: Optional per-call timeout override in seconds.
                If None, use the provider's default timeout.

        Returns:
            Assistant response as plain text string.
            On error, returns a human-readable error string starting with "Error:".
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs for this provider.

        Returns:
            List of model ID strings. Empty list on error.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Test connectivity to the provider.

        Returns:
            (True, success_message) on success.
            (False, error_message) on failure.
        """
        ...
