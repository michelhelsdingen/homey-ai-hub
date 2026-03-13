"""Homey AI Hub — main application entry point."""
import os
import sys

# Ensure app directory is in Python path — Homey runtime may not add /app/ to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from homey import app as homey_app
from homey.flow_card import ArgumentAutocompleteResult

from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider
from lib.providers.openai_provider import OpenAIProvider
from lib.conversation_store import ConversationStore
from lib.homey_api import HomeyAPI
from lib.smart_home import run_smart_home


class App(homey_app.App):
    async def on_init(self) -> None:
        self.log("Homey AI Hub starting...")
        self._providers: dict = {}
        self._homey_api: HomeyAPI | None = None
        max_turns = int(self.homey.settings.get("max_history_turns") or 10)
        self._store = ConversationStore(settings=self.homey.settings, max_turns=max_turns)
        await self._init_providers()
        await self._init_homey_api()
        await self._register_flow_cards()
        # Expose app instance so api.py test runner can call _run_ai() directly
        self.homey._app_instance = self
        self.log("Homey AI Hub ready.")

    async def _init_homey_api(self) -> None:
        """Initialize the Homey REST API client for device/flow control."""
        try:
            token = await self.homey.api.get_owner_api_token()
            local_url = await self.homey.api.get_local_url()
            self._homey_api = HomeyAPI(token=token, base_url=local_url)
            self.log(f"Homey API initialized: {local_url}")
        except Exception as e:
            self.log(f"Warning: Could not initialize Homey API (smart home control disabled): {e}")
            self.log(f"homey.api attrs: {dir(self.homey.api)}")
            self._homey_api = None

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

        # OpenAI requires API key — skip if not configured
        openai_key = self.homey.settings.get("openai_api_key")
        if openai_key:
            openai_timeout = float(
                self.homey.settings.get("openai_timeout") or OpenAIProvider.DEFAULT_TIMEOUT
            )
            self._providers["openai"] = OpenAIProvider(api_key=openai_key, timeout=openai_timeout)

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

        openai_key = self.homey.settings.get("openai_api_key")
        if openai_key:
            openai_timeout = float(
                self.homey.settings.get("openai_timeout") or OpenAIProvider.DEFAULT_TIMEOUT
            )
            self._providers["openai"] = OpenAIProvider(api_key=openai_key, timeout=openai_timeout)
        elif "openai" in self._providers:
            del self._providers["openai"]

        name = provider_name or self.homey.settings.get("default_provider") or "ollama"
        return self._providers.get(name), name

    def _build_fallback_chain(self, primary_provider: str | None = None, primary_model: str | None = None) -> list[tuple]:
        """Returns list of (provider_instance, model_name, provider_name_str) tuples to try in order."""
        chain = []

        # Primary
        prov_name = primary_provider or self.homey.settings.get("default_provider") or "ollama"
        provider, _ = self._get_provider(prov_name)
        model = primary_model or self.homey.settings.get(f"default_model_{prov_name}") or ""
        if provider:
            chain.append((provider, model, prov_name))

        # Fallback
        if self.homey.settings.get("fallback_enabled"):
            order_str = self.homey.settings.get("fallback_order") or "claude,openai,ollama"
            order = [p.strip() for p in order_str.split(",") if p.strip()]
            for fb_name in order:
                if fb_name == prov_name:
                    continue
                fb_provider, _ = self._get_provider(fb_name)
                if fb_provider:
                    fb_model = self.homey.settings.get(f"default_model_{fb_name}") or ""
                    chain.append((fb_provider, fb_model, fb_name))

        return chain

    async def _resolve_model(self, provider, model: str, provider_name: str) -> str:
        """If model is empty, fetch first model from provider's list_models()."""
        if model:
            return model
        try:
            models = await provider.list_models()
            return models[0] if models else ""
        except Exception:
            return ""

    async def _model_autocomplete(self, query: str, **card_args) -> list[ArgumentAutocompleteResult]:
        """Autocomplete handler for model argument on custom AI cards."""
        provider_name = (
            card_args.get("args", {}).get("provider")
            or card_args.get("provider")
            or "ollama"
        )
        provider, _ = self._get_provider(provider_name)
        if not provider:
            return []
        try:
            models = await provider.list_models()
        except Exception:
            return []
        results = [{"name": m, "description": "", "data": {"id": m}} for m in models]
        if query:
            q = query.lower()
            is_current_selection = any(r["name"].lower() == q for r in results)
            if not is_current_selection:
                filtered = [r for r in results if q in r["name"].lower()]
                if filtered:
                    results = filtered
        return results

    async def _run_ai(self, args: dict) -> dict:
        """Unified AI handler — handles BOTH text Q&A AND device control, with fallback."""
        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            return {"response": "Error: No prompt provided."}

        # Resolve provider/model from args (custom cards) or defaults (simple cards)
        provider_name = args.get("provider")  # None for simple cards
        model_arg = args.get("model")
        if isinstance(model_arg, dict):
            model = model_arg.get("name") or model_arg.get("id") or ""
        else:
            model = str(model_arg) if model_arg else ""

        chain = self._build_fallback_chain(provider_name, model)
        if not chain:
            return {"response": "Error: No AI provider configured. Check Settings."}

        # Conversation history
        conversation_id = (args.get("conversation_id") or "").strip()
        per_card_system = (args.get("system_prompt") or "").strip()
        global_system = (self.homey.settings.get("global_system_prompt") or "").strip()
        effective_system = per_card_system or global_system or None

        last_error = ""
        for provider, prov_model, prov_name in chain:
            resolved_model = await self._resolve_model(provider, prov_model, prov_name)
            if not resolved_model:
                last_error = f"No model available for {prov_name}"
                continue

            self.log(f"ai: trying {prov_name}/{resolved_model}")

            # Try smart home path first (tool use — AI decides whether to use tools)
            if self._homey_api:
                try:
                    response, actions = await run_smart_home(
                        provider=provider, api=self._homey_api,
                        prompt=prompt, model=resolved_model,
                        system_prompt_extra=effective_system, log=self.log,
                    )
                    if not response.startswith("Error:"):
                        if conversation_id:
                            self._store.append(conversation_id, "user", prompt)
                            self._store.append(conversation_id, "assistant", response)
                        await self._response_trigger.trigger({
                            "response": response, "provider": prov_name,
                            "model": resolved_model, "prompt": prompt,
                        })
                        return {"response": response}
                    last_error = response
                    self.log(f"ai: {prov_name} failed: {response}, trying next")
                    continue
                except Exception as e:
                    last_error = f"Error: {prov_name} failed: {e}"
                    self.log(f"ai: {prov_name} exception: {e}, trying next")
                    continue

            # Fallback: pure text chat (no Homey API available)
            if conversation_id:
                history = self._store.get(conversation_id)
                messages = list(history) + [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": prompt}]

            response = await provider.chat(
                messages=messages, model=resolved_model,
                system_prompt=effective_system,
            )
            if not response.startswith("Error:"):
                if conversation_id:
                    self._store.append(conversation_id, "user", prompt)
                    self._store.append(conversation_id, "assistant", response)
                await self._response_trigger.trigger({
                    "response": response, "provider": prov_name,
                    "model": resolved_model, "prompt": prompt,
                })
                return {"response": response}
            last_error = response
            self.log(f"ai: {prov_name} chat failed: {response}, trying next")

        return {"response": last_error or "Error: All providers failed."}

    async def _run_ai_image(self, args: dict) -> dict:
        """Image handler with fallback."""
        droptoken = args.get("droptoken")
        if droptoken is None:
            return {"response": "Error: No image provided. Connect an image token to this card."}

        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            return {"response": "Error: No prompt provided."}

        # Read image from droptoken
        try:
            image_stream = await droptoken.get_stream()
            image_bytes = image_stream["data"].read()
            media_type = (image_stream.get("meta") or {}).get("contentType") or "image/jpeg"
        except (TypeError, KeyError, AttributeError) as e:
            self.log(f"ai_image: droptoken error: {type(droptoken)}, {e}")
            return {"response": f"Error: Could not read image: {e}"}

        if media_type == "image/jpg":
            media_type = "image/jpeg"

        # Resolve provider/model
        provider_name = args.get("provider")
        model_arg = args.get("model")
        if isinstance(model_arg, dict):
            model = model_arg.get("name") or model_arg.get("id") or ""
        else:
            model = str(model_arg) if model_arg else ""

        chain = self._build_fallback_chain(provider_name, model)
        if not chain:
            return {"response": "Error: No AI provider configured. Check Settings."}

        last_error = ""
        for provider, prov_model, prov_name in chain:
            resolved_model = await self._resolve_model(provider, prov_model, prov_name)
            if not resolved_model:
                last_error = f"No model available for {prov_name}"
                continue

            self.log(f"ai_image: trying {prov_name}/{resolved_model}, image_size={len(image_bytes)}")

            response = await provider.chat_with_image(
                prompt=prompt, image_bytes=image_bytes,
                media_type=media_type, model=resolved_model,
            )
            if not response.startswith("Error:"):
                await self._response_trigger.trigger({
                    "response": response, "provider": prov_name,
                    "model": resolved_model, "prompt": prompt,
                })
                return {"response": response}
            last_error = response
            self.log(f"ai_image: {prov_name} failed: {response}, trying next")

        return {"response": last_error or "Error: All providers failed."}

    async def _clear_conversation(self, args: dict, **kwargs) -> dict:
        """Clear a named conversation history."""
        conversation_id = (args.get("conversation_id") or "").strip()
        if not conversation_id:
            return {"result": "Error: No conversation ID provided."}
        self._store.clear(conversation_id)
        self.log(f"clear_conversation: cleared '{conversation_id}'")
        return {"result": f"Conversation '{conversation_id}' cleared."}

    async def _register_flow_cards(self) -> None:
        """Register all Flow action and trigger card listeners."""
        # Triggers (unchanged)
        self._response_trigger = self.homey.flow.get_trigger_card("ai_response_received")
        self._webhook_trigger = self.homey.flow.get_trigger_card("webhook_received")

        # Simple AI card (uses defaults from settings)
        ai_card = self.homey.flow.get_action_card("ai")
        ai_card.register_run_listener(lambda args, **kw: self._run_ai(args))

        # Custom AI card (user picks provider/model)
        ai_custom_card = self.homey.flow.get_action_card("ai_custom")
        ai_custom_card.register_run_listener(lambda args, **kw: self._run_ai(args))
        ai_custom_card.register_argument_autocomplete_listener("model", self._model_autocomplete)

        # Simple Image card
        ai_image_card = self.homey.flow.get_action_card("ai_image")
        ai_image_card.register_run_listener(lambda args, **kw: self._run_ai_image(args))

        # Custom Image card
        ai_image_custom_card = self.homey.flow.get_action_card("ai_image_custom")
        ai_image_custom_card.register_run_listener(lambda args, **kw: self._run_ai_image(args))
        ai_image_custom_card.register_argument_autocomplete_listener("model", self._model_autocomplete)

        # Clear conversation (unchanged logic)
        clear_card = self.homey.flow.get_action_card("clear_conversation")
        clear_card.register_run_listener(self._clear_conversation)


homey_export = App
