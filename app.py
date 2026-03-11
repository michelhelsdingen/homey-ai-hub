"""Homey AI Hub — main application entry point."""
from homey import app as homey_app
from homey.flow_card import ArgumentAutocompleteResult

from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider
from lib.conversation_store import ConversationStore


class App(homey_app.App):
    async def on_init(self) -> None:
        self.log("Homey AI Hub starting...")
        self._providers: dict = {}
        max_turns = int(self.homey.settings.get("max_history_turns") or 10)
        self._store = ConversationStore(settings=self.homey.settings, max_turns=max_turns)
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

            # Extract model (handles autocomplete dict or plain string)
            model_arg = args.get("model")
            if isinstance(model_arg, dict):
                model = model_arg.get("name") or model_arg.get("id") or ""
            else:
                model = str(model_arg) if model_arg else ""

            if not model:
                try:
                    models = await provider.list_models()
                    model = models[0] if models else ""
                except Exception as e:
                    return {"response": f"Error: Could not fetch models for {name}: {e}"}

            if not model:
                return {"response": f"Error: No model selected and no models available for {name}."}

            # Optional conversation session
            conversation_id = (args.get("conversation_id") or "").strip()

            # System prompt precedence: per-card > global setting > None
            per_card_system = (args.get("system_prompt") or "").strip()
            global_system = (self.homey.settings.get("global_system_prompt") or "").strip()
            effective_system = per_card_system or global_system or None

            # Build message list (with history if using a named session)
            if conversation_id:
                history = self._store.get(conversation_id)
                messages = list(history) + [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": prompt}]

            self.log(
                f"ask_ai: provider={name}, model={model}, "
                f"prompt_len={len(prompt)}, "
                f"conv_id={conversation_id or 'none'}, "
                f"system_prompt={'yes' if effective_system else 'no'}"
            )

            response = await provider.chat(
                messages=messages,
                model=model,
                system_prompt=effective_system,
            )

            # Persist turn ONLY after successful API call (not if response starts with "Error:")
            if conversation_id and not response.startswith("Error:"):
                self._store.append(conversation_id, "user", prompt)
                self._store.append(conversation_id, "assistant", response)

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

        clear_card = self.homey.flow.get_action_card("clear_conversation")

        async def clear_run_listener(args: dict, **kwargs) -> dict:
            conversation_id = (args.get("conversation_id") or "").strip()
            if not conversation_id:
                return {"result": "Error: No conversation ID provided."}
            self._store.clear(conversation_id)
            self.log(f"clear_conversation: cleared '{conversation_id}'")
            return {"result": f"Conversation '{conversation_id}' cleared."}

        clear_card.register_run_listener(clear_run_listener)

        image_card = self.homey.flow.get_action_card("ask_ai_with_image")

        async def image_run_listener(args: dict, **kwargs) -> dict:
            # Guard: droptoken is nullable — user may not have connected an image token
            droptoken = args.get("droptoken")
            if droptoken is None:
                return {"response": "Error: No image provided. Connect an image token to this card."}

            provider_name = args.get("provider")
            provider, name = self._get_provider(provider_name)
            if not provider:
                return {
                    "response": (
                        f"Error: Provider '{name}' not configured. "
                        "Check Settings > Homey AI Hub."
                    )
                }

            prompt = args.get("prompt", "").strip()
            if not prompt:
                return {"response": "Error: No prompt provided."}

            # Extract model (handles autocomplete dict or plain string — same pattern as ask_ai)
            model_arg = args.get("model")
            if isinstance(model_arg, dict):
                model = model_arg.get("name") or model_arg.get("id") or ""
            else:
                model = str(model_arg) if model_arg else ""

            if not model:
                try:
                    models = await provider.list_models()
                    model = models[0] if models else ""
                except Exception as e:
                    return {"response": f"Error: Could not fetch models for {name}: {e}"}

            if not model:
                return {"response": f"Error: No model selected and no models available for {name}."}

            # Read image from Homey droptoken
            # MEDIUM confidence: exact Python SDK shape — primary pattern based on SDK docs
            # If this fails with AttributeError, inspect: self.log(f"droptoken attrs: {dir(droptoken)}")
            try:
                image_stream = await droptoken.get_stream()
                # Expected shape: {"meta": {"contentType": str, "filename": str}, "data": <BytesIO-like>}
                image_bytes = image_stream["data"].read()
                media_type = (image_stream.get("meta") or {}).get("contentType") or "image/jpeg"
            except (TypeError, KeyError, AttributeError) as e:
                # Fallback: stream may be returned as a different object shape
                self.log(f"ask_ai_with_image: droptoken shape unexpected: {type(image_stream)}, attrs: {dir(image_stream)}, error: {e}")
                return {"response": f"Error: Could not read image from droptoken: {e}. Check app logs for droptoken shape."}

            # Normalize MIME type: Anthropic rejects "image/jpg" — must be "image/jpeg"
            if media_type == "image/jpg":
                media_type = "image/jpeg"

            self.log(
                f"ask_ai_with_image: provider={name}, model={model}, "
                f"media_type={media_type}, image_size={len(image_bytes)}, prompt_len={len(prompt)}"
            )

            response = await provider.chat_with_image(
                prompt=prompt,
                image_bytes=image_bytes,
                media_type=media_type,
                model=model,
            )
            return {"response": response}

        image_card.register_run_listener(image_run_listener)
        # Reuse existing model_autocomplete — same provider/model logic works for vision card
        image_card.register_argument_autocomplete_listener("model", model_autocomplete)


homey_export = App
