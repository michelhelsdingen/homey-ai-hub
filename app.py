"""Homey AI Hub — main application entry point."""
from homey import app as homey_app
from homey.flow_card import ArgumentAutocompleteResult

from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider


class App(homey_app.App):
    async def on_init(self) -> None:
        self.log("Homey AI Hub starting...")
        self._providers: dict = {}
        await self._init_providers()
        await self._register_flow_cards()
        self.log("Homey AI Hub ready.")

    async def _init_providers(self) -> None:
        """Initialize AI providers from current settings.

        Called at startup and re-called on each Flow run to pick up settings changes.
        Note: ManagerSettings has no .on() event in Python SDK — re-read on each call.
        """
        self._providers = {}

        # Ollama is always available (no auth required)
        ollama_url = self.homey.settings.get("ollama_url") or OllamaProvider.DEFAULT_HOST
        ollama_timeout = float(
            self.homey.settings.get("ollama_timeout") or OllamaProvider.DEFAULT_TIMEOUT
        )
        self._providers["ollama"] = OllamaProvider(host=ollama_url, timeout=ollama_timeout)

        # Claude requires API key — skip if not configured
        claude_key = self.homey.settings.get("claude_api_key")
        if claude_key:
            claude_timeout = float(
                self.homey.settings.get("claude_timeout") or ClaudeProvider.DEFAULT_TIMEOUT
            )
            self._providers["claude"] = ClaudeProvider(api_key=claude_key, timeout=claude_timeout)

    def _get_provider(self, provider_name: str | None):
        """Look up a provider, refreshing from settings first."""
        # Refresh provider config (picks up any settings changes since last call)
        # We rebuild providers on each call because Python ManagerSettings has no .on() event
        ollama_url = self.homey.settings.get("ollama_url") or OllamaProvider.DEFAULT_HOST
        ollama_timeout = float(
            self.homey.settings.get("ollama_timeout") or OllamaProvider.DEFAULT_TIMEOUT
        )
        self._providers["ollama"] = OllamaProvider(host=ollama_url, timeout=ollama_timeout)

        claude_key = self.homey.settings.get("claude_api_key")
        if claude_key:
            claude_timeout = float(
                self.homey.settings.get("claude_timeout") or ClaudeProvider.DEFAULT_TIMEOUT
            )
            self._providers["claude"] = ClaudeProvider(api_key=claude_key, timeout=claude_timeout)
        elif "claude" in self._providers:
            del self._providers["claude"]

        name = provider_name or self.homey.settings.get("default_provider") or "ollama"
        return self._providers.get(name), name

    async def _register_flow_cards(self) -> None:
        """Register all Flow action card listeners."""
        ask_card = self.homey.flow.get_action_card("ask_ai")

        async def run_listener(args: dict, **kwargs) -> dict:
            provider_name = args.get("provider")
            provider, name = self._get_provider(provider_name)

            if not provider:
                return {
                    "response": (
                        f"Error: Provider '{name}' not configured. "
                        "Check Settings > Homey AI Hub."
                    )
                }

            prompt = args.get("prompt", "")
            if not prompt:
                return {"response": "Error: No prompt provided."}

            # Extract model from autocomplete result (dict) or string
            model_arg = args.get("model")
            if isinstance(model_arg, dict):
                model = model_arg.get("name") or model_arg.get("id") or ""
            else:
                model = str(model_arg) if model_arg else ""

            if not model:
                # Fall back to first available model
                models = await provider.list_models()
                model = models[0] if models else ""

            if not model:
                return {"response": f"Error: No model selected and no models available for {name}."}

            self.log(f"ask_ai: provider={name}, model={model}, prompt_len={len(prompt)}")

            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )
            return {"response": response}

        ask_card.register_run_listener(run_listener)

        async def model_autocomplete(
            query: str, **card_args
        ) -> list[ArgumentAutocompleteResult]:
            provider_name = card_args.get("args", {}).get("provider", "ollama")
            provider, _ = self._get_provider(provider_name)

            if not provider:
                return []

            models = await provider.list_models()
            results: list[ArgumentAutocompleteResult] = [
                {"name": m, "description": "", "data": {"id": m}} for m in models
            ]
            if query:
                results = [r for r in results if query.lower() in r["name"].lower()]
            return results

        ask_card.register_argument_autocomplete_listener("model", model_autocomplete)


homey_export = App
