# Phase 1: Core AI Integration - Research

**Researched:** 2026-03-11
**Domain:** Homey Python SDK + Anthropic Claude API + Ollama Python client
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROV-01 | User can configure Ollama connection via IP address and port in settings | Settings HTML page reads/writes `self.homey.settings`. OllamaProvider constructed with `host=` at init and on settings change. |
| PROV-02 | User can configure Claude API key in settings | Same settings pattern — masked `password` input type in settings HTML. ClaudeProvider constructed with `api_key=`. |
| PROV-03 | User can select a model per provider (Ollama: from installed models, Claude: Haiku/Sonnet/Opus) | `autocomplete` argument type with `register_argument_autocomplete_listener()` confirmed working in Python. Ollama: `client.list()` live call. Claude: static list. |
| PROV-04 | User can set a default provider (Ollama or Claude) in settings | `default_provider` key in ManagerSettings. Flow card falls back to this when no provider arg given. |
| PROV-05 | User can test connection to Ollama and Claude from settings page | Settings page JS calls Homey API endpoint; app exposes test endpoint via `api.py`. |
| PROV-06 | User can see dynamically fetched model list from Ollama API via autocomplete | `autocomplete_listener` calls `ollama.AsyncClient.list()` — confirmed pattern. Filter by query for responsiveness. |
| FLOW-01 | User can send a text prompt to selected provider via Flow action card and receive AI response as token | `register_run_listener` returns `{"response": text}` dict. Card JSON declares `tokens` array. Advanced Flow only. |
| CONF-01 | User can configure timeout per provider (default: 30s Claude, 120s Ollama) | `timeout` setting read in provider constructor; passed to `httpx_client` override for Claude, `httpx` AsyncClient timeout for Ollama. |
</phase_requirements>

---

## Summary

Phase 1 establishes the entire functional core of the app: two AI providers (Claude and Ollama), their settings configuration, the primary Flow action card, and connection testing. All other phases (conversation memory, vision) extend this foundation.

The Homey Python SDK is confirmed to support all required patterns: `register_run_listener` for Flow action card execution, `register_argument_autocomplete_listener` for live Ollama model listing, and `self.homey.settings.get/set` for persistent configuration. The Python SDK mirrors the JavaScript SDK's event model but uses snake_case method names. The key confirmed finding is the autocomplete callback signature — the previously flagged blocker in STATE.md is resolved.

Build order within this phase follows the dependency graph: providers first (pure Python, no Homey runtime), then Flow card JSON (no Python), then app wiring in `app.py` (requires Homey runtime), then settings UI (frontend only). This allows unit-testing providers in isolation before any Docker testing is needed.

**Primary recommendation:** Build `ClaudeProvider` and `OllamaProvider` as pure Python classes implementing `LLMProvider` ABC first. Wire them into `app.py` last. Settings page is standalone HTML/JS calling `Homey.get/set`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Homey Python SDK | Latest (managed by Homey CLI) | App runtime, Flow card registration, settings API | The only way to build Python apps on Homey Pro. Provides `App`, `FlowCardAction`, `ManagerSettings`. |
| `anthropic` | `>=0.84.0` | Claude API client (async) | Official Anthropic SDK. `AsyncAnthropic` is required — sync client blocks event loop. |
| `ollama` | `>=0.6.1` | Ollama local model client (async) | Official Ollama Python library. `AsyncClient` with `chat()`, `list()`, `generate()`. |
| Python | 3.14 | Runtime | Pinned by Homey platform — no choice needed. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `homey-stubs` | Latest (PyPI) | Type hints for Homey SDK classes | Always — enables Pyright static analysis of SDK calls. Dev-only dependency. |
| `pytest` | `>=8.0` | Test runner | All unit tests for provider classes. |
| `pytest-asyncio` | `>=1.0.0` | Async test support | Required for testing `async def` provider methods. Use `asyncio_mode = "auto"`. |
| `pytest-mock` | Latest | Mock SDK and API calls | Homey SDK unavailable in test env — all `self.homey.*` calls must be mocked. |
| `pyright` | Latest | Static type checking | Recommended by official Homey docs for use with `homey-stubs`. |
| `ruff` | `>=0.9.0` | Linting + formatting | Replaces black + flake8 + isort. 2025 standard. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `anthropic.AsyncAnthropic` | `httpx.AsyncClient` + raw REST | Official SDK handles auth, retries, streaming, type safety. Raw REST is reimplementation. |
| `ollama.AsyncClient` | `httpx.AsyncClient` direct to REST | Official library wraps all endpoints. Direct REST offers no benefit. |
| In-memory `dict` for provider registry | LangChain, LiteLLM | LangChain is 50MB+; LiteLLM adds another abstraction layer. Both overkill for two providers. |

**Installation:**
```bash
# Production dependencies (via Homey CLI — mandatory)
homey app dependency install anthropic
homey app dependency install ollama

# Dev dependencies (pip — local only, never deployed)
pip install pytest pytest-asyncio pytest-mock pyright ruff homey-stubs
```

---

## Architecture Patterns

### Recommended Project Structure

```
homey-ai-hub/
├── app.py                          # App class, on_init, Flow card wiring
├── app.json                        # AUTO-GENERATED — edit .homeycompose instead
├── .homeycompose/
│   ├── app.json                    # App metadata, permissions
│   └── flow/
│       └── actions/
│           └── ask_ai.json         # "Ask AI" action card definition
├── lib/
│   └── providers/
│       ├── base.py                 # Abstract LLMProvider ABC
│       ├── claude.py               # ClaudeProvider
│       └── ollama_provider.py      # OllamaProvider (not ollama.py — avoid name clash)
├── settings/
│   └── index.html                  # API key, Ollama URL, provider config, test buttons
├── api.py                          # Homey API endpoint for settings test (connection test)
├── locales/
│   └── en.json                     # English strings only (no partial translations)
└── tests/
    ├── conftest.py                 # Shared fixtures (mock homey, mock clients)
    ├── test_claude_provider.py
    └── test_ollama_provider.py
```

### Pattern 1: Abstract Provider Base Class

**What:** `LLMProvider` ABC defines the interface both providers implement. App code only calls `LLMProvider` methods.

**When to use:** Always — enables provider switching, testability, and future expansion.

```python
# lib/providers/base.py
# Source: Architecture confirmed from official Homey docs + provider SDK docs
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float = 30.0,
    ) -> str:
        """Return the assistant response text."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs."""
        ...

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Return (success, message) for connection test."""
        ...
```

### Pattern 2: ClaudeProvider Using AsyncAnthropic

**What:** Wraps `AsyncAnthropic` client. Creates client once; passes `api_key` and configures timeout via `httpx_client` override.

**When to use:** Always for Claude — synchronous `Anthropic()` client is forbidden in async context.

```python
# lib/providers/claude.py
# Source: https://pypi.org/project/anthropic/ + official Anthropic async docs
import httpx
from anthropic import AsyncAnthropic, APIConnectionError, RateLimitError, APIStatusError

class ClaudeProvider(LLMProvider):
    MODELS = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-5"]

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._client = AsyncAnthropic(
            api_key=api_key,
            http_client=httpx.AsyncClient(timeout=timeout),
        )
        self._timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
    ) -> str:
        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages,
            )
            return response.content[0].text
        except RateLimitError:
            return "Error: Claude rate limited. Wait 30 seconds and retry."
        except APIConnectionError as e:
            return f"Error: Cannot reach Claude API: {e}"
        except APIStatusError as e:
            return f"Error: Claude API error {e.status_code}: {e.message}"

    async def list_models(self) -> list[str]:
        return self.MODELS

    async def test_connection(self) -> tuple[bool, str]:
        try:
            # Minimal test: list models (no API call needed — static list)
            # Real test: send a minimal message
            response = await self._client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return (True, "Claude connection OK")
        except Exception as e:
            return (False, f"Claude connection failed: {e}")
```

### Pattern 3: OllamaProvider Using AsyncClient

**What:** Wraps `ollama.AsyncClient`. Dynamically lists models via `client.list()`. Uses generous timeout (120s default) for cold-start model loading.

**When to use:** Always for Ollama.

```python
# lib/providers/ollama_provider.py
# Source: https://github.com/ollama/ollama-python (official)
from ollama import AsyncClient, ResponseError
import httpx

class OllamaProvider(LLMProvider):
    def __init__(self, host: str = "http://192.168.2.214:11434", timeout: float = 120.0) -> None:
        self._client = AsyncClient(host=host, timeout=timeout)
        self._host = host

    async def chat(
        self,
        messages: list[dict],
        model: str,
        timeout: float | None = None,
    ) -> str:
        try:
            response = await self._client.chat(
                model=model,
                messages=messages,
            )
            return response.message.content
        except ResponseError as e:
            return f"Error: Ollama error: {e}"
        except (ConnectionError, OSError) as e:
            return f"Error: Cannot reach Ollama at {self._host}: {e}"

    async def list_models(self) -> list[str]:
        try:
            models_response = await self._client.list()
            return [m.model for m in models_response.models]
        except Exception:
            return []

    async def test_connection(self) -> tuple[bool, str]:
        try:
            models = await self.list_models()
            return (True, f"Ollama OK — {len(models)} model(s) available")
        except Exception as e:
            return (False, f"Ollama connection failed: {e}")
```

### Pattern 4: App Singleton as Registry and Wiring Point

**What:** `App.on_init()` constructs all providers, registers all Flow card listeners. No globals, no module-level state. Settings change listener reinitializes providers when API key or URL changes.

**When to use:** Always — Homey guarantees one App instance.

```python
# app.py
# Source: https://apps.developer.homey.app/the-basics/app (official Python example)
from homey import app
from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider

class App(app.App):
    async def on_init(self) -> None:
        self._providers: dict = {}
        await self._init_providers()
        await self._register_flow_cards()
        # NOTE: ManagerSettings does NOT have a Python .on() event method
        # confirmed from python-apps-sdk-v3 API — re-init on each call instead

    async def _init_providers(self) -> None:
        self._providers = {}
        ollama_url = self.homey.settings.get("ollama_url") or "http://192.168.2.214:11434"
        ollama_timeout = float(self.homey.settings.get("ollama_timeout") or 120.0)
        self._providers["ollama"] = OllamaProvider(host=ollama_url, timeout=ollama_timeout)

        claude_key = self.homey.settings.get("claude_api_key")
        if claude_key:
            claude_timeout = float(self.homey.settings.get("claude_timeout") or 30.0)
            self._providers["claude"] = ClaudeProvider(api_key=claude_key, timeout=claude_timeout)

    async def _register_flow_cards(self) -> None:
        from homey.flow_card import ArgumentAutocompleteResult

        ask_card = self.homey.flow.get_action_card("ask_ai")

        async def run_listener(args: dict, **kwargs) -> dict:
            provider_name = args.get("provider") or self.homey.settings.get("default_provider") or "ollama"
            provider = self._providers.get(provider_name)
            if not provider:
                return {"response": f"Error: Provider '{provider_name}' not configured."}
            try:
                response = await provider.chat(
                    messages=[{"role": "user", "content": args["prompt"]}],
                    model=args.get("model", {}).get("name") if isinstance(args.get("model"), dict) else args.get("model", ""),
                )
                return {"response": response}
            except Exception as e:
                return {"response": f"Error: {e}"}

        ask_card.register_run_listener(run_listener)

        async def model_autocomplete(query: str, **card_args) -> list[ArgumentAutocompleteResult]:
            provider_name = card_args.get("args", {}).get("provider", "ollama")
            provider = self._providers.get(provider_name)
            if not provider:
                return []
            models = await provider.list_models()
            results = [{"name": m, "description": "", "data": {"id": m}} for m in models]
            if query:
                results = [r for r in results if query.lower() in r["name"].lower()]
            return results

        ask_card.register_argument_autocomplete_listener("model", model_autocomplete)

homey_export = App
```

### Pattern 5: Flow Action Card JSON with Tokens

**What:** Declare the card in `.homeycompose/flow/actions/ask_ai.json`. Use `autocomplete` type for model. Declare `tokens` for the response output.

**When to use:** Always — `tokens` is required for the response to appear in Advanced Flow.

```json
// .homeycompose/flow/actions/ask_ai.json
// Source: https://apps.developer.homey.app/the-basics/flow/tokens (official docs)
{
  "id": "ask_ai",
  "title": {
    "en": "Ask AI"
  },
  "titleFormatted": {
    "en": "Ask AI: [[prompt]]"
  },
  "args": [
    {
      "name": "prompt",
      "type": "text",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "What is the weather like?" }
    },
    {
      "name": "provider",
      "type": "dropdown",
      "title": { "en": "Provider" },
      "values": [
        { "id": "ollama", "label": { "en": "Ollama (local)" } },
        { "id": "claude", "label": { "en": "Claude (cloud)" } }
      ]
    },
    {
      "name": "model",
      "type": "autocomplete",
      "title": { "en": "Model" },
      "placeholder": { "en": "Select model..." }
    }
  ],
  "tokens": [
    {
      "name": "response",
      "type": "string",
      "title": { "en": "AI Response" },
      "example": { "en": "The weather in Amsterdam is 15°C and partly cloudy." }
    }
  ]
}
```

### Pattern 6: Settings Page with Connection Test

**What:** `settings/index.html` reads/writes via `Homey.get/set()` JavaScript API. Connection test button calls an API endpoint defined in `api.py`.

**When to use:** For PROV-01, PROV-02, PROV-04, PROV-05, CONF-01.

```html
<!-- settings/index.html — relevant snippet -->
<script>
  // Read setting
  const apiKey = await Homey.get('claude_api_key');

  // Write setting
  await Homey.set('claude_api_key', document.getElementById('claude_api_key').value);

  // Test connection (calls api.py endpoint)
  async function testClaude() {
    const result = await Homey.api('POST', '/test-claude', {});
    document.getElementById('claude_status').textContent = result.message;
  }
</script>
```

```python
# api.py — connection test endpoint
# Source: https://apps.developer.homey.app/advanced/api (official docs pattern)
from homey import app as homey_app

class Api(homey_app.Api):
    async def post_test_claude(self, body: dict, **kwargs) -> dict:
        provider = self.homey.app._providers.get("claude")
        if not provider:
            return {"success": False, "message": "Claude API key not configured"}
        success, message = await provider.test_connection()
        return {"success": success, "message": message}

    async def post_test_ollama(self, body: dict, **kwargs) -> dict:
        provider = self.homey.app._providers.get("ollama")
        if not provider:
            return {"success": False, "message": "Ollama not initialized"}
        success, message = await provider.test_connection()
        return {"success": success, "message": message}

homey_export = Api
```

### Anti-Patterns to Avoid

- **Synchronous HTTP in run listeners:** Using `requests.post()` inside an `async def` blocks the Homey event loop for the entire LLM call duration (potentially 60+ seconds). Use `AsyncAnthropic` and `ollama.AsyncClient` exclusively.
- **Returning before LLM responds:** Not awaiting the full LLM call before returning the run listener. The response token will be empty. Always `await provider.chat(...)` before `return {"response": ...}`.
- **Editing app.json directly:** `app.json` is auto-generated from `.homeycompose/`. All manifest edits go in `.homeycompose/`. Manual edits to `app.json` are silently overwritten by `homey app build`.
- **Module named `ollama.py`:** Python file named `ollama.py` will shadow the `ollama` library import. Name it `ollama_provider.py`.
- **Static model list for Ollama:** Using a fixed list in the compose JSON stales when users install new models. Always use `autocomplete` type backed by live `client.list()`.
- **Missing null-check on settings:** `self.homey.settings.get("claude_api_key")` returns `None` on first install. Using it directly as a string causes `TypeError`. Always check for `None`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude API client | Custom httpx REST calls | `anthropic.AsyncAnthropic` | Handles auth headers, retries on 429/503, streaming, type-safe responses |
| Ollama client | Custom httpx calls to Ollama REST API | `ollama.AsyncClient` | Handles model listing, chat, embeddings — all endpoints wrapped |
| HTTP timeout handling for Claude | Manual `asyncio.wait_for` wrapper | `httpx.AsyncClient(timeout=N)` passed to `AsyncAnthropic(http_client=...)` | Anthropic SDK accepts custom httpx client; cleaner than wrapping |
| Connection test logic | Custom health check HTTP calls | Provider's own `test_connection()` method calling real API | Already wraps the exact SDK's error surfaces |

**Key insight:** Both AI provider SDKs are async-native and handle the edge cases (auth, retries, timeouts, error types) that would require hundreds of lines if hand-rolled.

---

## Common Pitfalls

### Pitfall 1: Flow Run Listener Returns Before LLM Responds

**What goes wrong:** The `run_listener` returns a dict before the `await provider.chat(...)` completes, resulting in an empty `{{response}}` token.

**Why it happens:** Async chains broken — forgetting `await`, mixing sync/async, or catching exceptions silently and returning before the await.

**How to avoid:** Wrap the entire provider call in a try/except inside the run listener, `await` the call, return the result dict only after the await resolves.

**Warning signs:** Downstream Flow cards receive empty or `None` response token. No error appears in Homey logs.

### Pitfall 2: Ollama Cold Start Timeout

**What goes wrong:** Ollama unloads models after 5 minutes idle. Next request after idle triggers a cold reload — 30-120 seconds for small models, 300+ seconds for 70B models. Default 30s timeouts cause failures that appear random.

**How to avoid:** Default Ollama timeout to 120 seconds. Expose `ollama_timeout` setting (default: 120). Test explicitly with a cold Ollama server.

**Warning signs:** Works during active testing, fails for users after an hour of inactivity.

### Pitfall 3: Missing Settings on First Install

**What goes wrong:** `self.homey.settings.get("claude_api_key")` returns `None` on fresh install. Using it without null-check raises `TypeError` in `ClaudeProvider.__init__()`.

**How to avoid:** Gate `ClaudeProvider` initialization behind `if claude_key:`. Display "Provider not configured" error in Flow response token rather than crashing.

**Warning signs:** App crashes immediately after installation before any configuration.

### Pitfall 4: ManagerSettings Has No Python `.on()` Event Method

**What goes wrong:** The ARCHITECTURE.md pattern `self.homey.settings.on("set", callback)` does not exist in the Python SDK's `ManagerSettings`. The Python SDK does not expose event listeners on settings — only `get`, `set`, `unset`, `get_settings`.

**How to avoid:** Re-read settings on each Flow card invocation (not just at init). Or re-initialize providers on each run listener call by reading current settings. This is the safest pattern given the Python SDK's API.

**Warning signs:** Settings changes (new API key, changed Ollama URL) have no effect until app restart.

### Pitfall 5: Autocomplete Listener Returns Non-Filtered Results

**What goes wrong:** Autocomplete callback returns the full model list without filtering by `query`. The UI appears unresponsive as typing doesn't narrow results.

**How to avoid:** Always filter: `[r for r in results if query.lower() in r["name"].lower()]`. When `query` is empty string, return all results (the initial dropdown open).

**Warning signs:** Typing in the model field doesn't narrow the list.

### Pitfall 6: Claude SDK Auto-Retry Masking Real Errors

**What goes wrong:** `AsyncAnthropic` retries 429/503 errors up to 2 times by default with exponential backoff. If Claude is overloaded, the Flow card appears to hang for 10-20 seconds before returning an error. Users think the app froze.

**How to avoid:** Set `max_retries=0` on `AsyncAnthropic` for the Flow card path (fast-fail). Handle 429 explicitly with a clear user message. Let the user retry from the Flow.

**Warning signs:** Flow card occasionally hangs for 10-20 seconds on Claude errors.

### Pitfall 7: Autocomplete for Model Includes Provider Context

**What goes wrong:** The `model` autocomplete callback needs to know which `provider` was selected to show the right models (Ollama: live list, Claude: static list). The `card_args` dict passed to the autocomplete listener contains the currently-selected values of other args.

**How to avoid:** Access `card_args.get("args", {}).get("provider")` to get the currently-selected provider in the autocomplete callback.

**Warning signs:** Model dropdown always shows Ollama models even when Claude is selected.

---

## Code Examples

Verified patterns from official sources:

### Autocomplete Listener Registration (Python, confirmed)

```python
# Source: https://apps.developer.homey.app/the-basics/flow/arguments (official Python example)
from homey import app
from homey.flow_card import ArgumentAutocompleteResult

class App(app.App):
    async def on_init(self) -> None:
        launch_app_card = self.homey.flow.get_action_card("play_artist")

        async def autocomplete_listener(
            query, **card_args
        ) -> list[ArgumentAutocompleteResult]:
            results: list[ArgumentAutocompleteResult] = [
                {
                    "name": "Wolfgang Amadeus Mozart",
                    "description": "...",
                    "icon": "https://path.to/icon.svg",
                    "data": {"id": "..."},
                },
            ]
            return [r for r in results if query.lower() in r["name"].lower()]

        launch_app_card.register_argument_autocomplete_listener(
            "artist", autocomplete_listener
        )
```

### Run Listener Returning Tokens (Python, confirmed)

```python
# Source: https://apps.developer.homey.app/the-basics/flow/tokens (official Python example)
async def run_listener(card_arguments, **trigger_kwargs) -> dict:
    await some_api.do_work()
    return {
        "response": "The result text",   # matches token name in JSON
    }

action_card.register_run_listener(run_listener)
```

### Ollama AsyncClient Model List (confirmed from ollama-python GitHub)

```python
# Source: https://github.com/ollama/ollama-python (official)
from ollama import AsyncClient

client = AsyncClient(host="http://192.168.2.214:11434", timeout=120)
models_response = await client.list()
model_names = [m.model for m in models_response.models]
```

### Ollama AsyncClient Chat (confirmed)

```python
# Source: https://github.com/ollama/ollama-python (official)
response = await client.chat(
    model="llama3.1:8b",
    messages=[{"role": "user", "content": "Hello"}],
)
text = response.message.content
```

### AsyncAnthropic Messages Create (confirmed)

```python
# Source: https://pypi.org/project/anthropic/ (official)
import httpx
from anthropic import AsyncAnthropic

client = AsyncAnthropic(
    api_key="sk-ant-...",
    http_client=httpx.AsyncClient(timeout=30.0),
)
response = await client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
)
text = response.content[0].text
```

### ManagerSettings Read/Write (confirmed from Python SDK docs)

```python
# Source: https://python-apps-sdk-v3.developer.homey.app/manager/settings.html
# Read (sync)
value = self.homey.settings.get("claude_api_key")

# Write (async)
await self.homey.settings.set("claude_api_key", "sk-ant-...")

# Delete (async)
await self.homey.settings.unset("claude_api_key")

# Read all (sync)
all_settings = self.homey.settings.get_settings()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JS-only Homey apps | Python 3.14 supported natively | 2024 (Homey Pro) | Can use Python AI ecosystem directly |
| `Anthropic()` sync client | `AsyncAnthropic()` required for async apps | Always, but critical here | Sync client blocks entire event loop |
| Static model dropdowns | `autocomplete` type with live API query | SDK v3 feature | Ollama models auto-populated, never stale |
| `pytest-asyncio` `event_loop` fixture | `asyncio_mode = "auto"` in config | pytest-asyncio 1.0 (May 2025) | Breaking change — old fixture approach fails |

**Deprecated/outdated:**
- `pytest-asyncio` `@pytest.mark.asyncio` per-test: replaced by `asyncio_mode = "auto"` global config
- `this.homey.settings.on("set", cb)` (JS pattern): does NOT exist in Python `ManagerSettings` — re-read settings per call instead

---

## Open Questions

1. **Settings change listener pattern in Python**
   - What we know: Python `ManagerSettings` has `get`, `set`, `unset`, `get_settings` only — no `.on()` event method confirmed.
   - What's unclear: Whether there's an alternative Python pattern (e.g., a `Homey`-level event, or a Web API callback) to reactively reinitialize providers when API key changes.
   - Recommendation: Re-read relevant settings at the start of each Flow card run listener invocation (`self.homey.settings.get(...)` is synchronous and fast). This avoids stale provider state without needing an event listener. Re-initialize provider objects if settings differ from cached values.

2. **API endpoint routing convention for `api.py`**
   - What we know: `api.py` with `homey_export = Api` is the Python pattern for Homey Web API endpoints. The settings HTML calls `Homey.api('POST', '/test-claude', {})`.
   - What's unclear: Exact method naming convention that maps URL path `/test-claude` to Python method name. JS SDK uses `onPost('/test-claude')` — Python equivalent method naming is `post_test_claude` based on pattern inference.
   - Recommendation: Verify exact Python `Api` class method naming convention by checking `python-apps-sdk-v3.developer.homey.app/api.html` during implementation. Plan for the `post_test_claude` convention but confirm before coding.

3. **Ollama `AsyncClient` timeout parameter**
   - What we know: `AsyncClient(host=..., timeout=...)` syntax is used in examples. The `timeout` parameter type and exact behavior (connect timeout vs. read timeout) is not confirmed from official docs.
   - What's unclear: Whether `timeout` is a float (seconds) or an `httpx.Timeout` object.
   - Recommendation: During implementation, check `ollama-python` source or PyPI docs. Default to `httpx.Timeout(connect=5.0, read=120.0)` pattern if float doesn't work.

---

## Sources

### Primary (HIGH confidence)
- `https://apps.developer.homey.app/the-basics/flow/arguments` — Python autocomplete callback signature, `register_argument_autocomplete_listener` confirmed
- `https://apps.developer.homey.app/the-basics/flow/tokens` — Python run listener token return format confirmed
- `https://apps.developer.homey.app/the-basics/app` — Python App class, `on_init`, `homey_export = App`, `self.homey.settings.get()` confirmed
- `https://python-apps-sdk-v3.developer.homey.app/manager/settings.html` — ManagerSettings API: `get`, `set`, `unset`, `get_settings` — no `.on()` event method
- `https://python-apps-sdk-v3.developer.homey.app/` — Full Python SDK index, all 20 managers confirmed
- `https://pypi.org/project/anthropic/` — Version 0.84.0, `AsyncAnthropic`, `httpx` integration
- `https://github.com/ollama/ollama-python` — `AsyncClient`, `.chat()`, `.list()`, response shapes
- Pre-research files: `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `FEATURES.md` — HIGH confidence, previously verified

### Secondary (MEDIUM confidence)
- `https://apps-sdk-v3.developer.homey.app/ManagerSettings.html` — Confirmed `set`/`unset` events exist in JS SDK; Python equivalent not confirmed
- `https://apps.developer.homey.app/advanced/custom-views/app-settings` — Settings HTML pattern using `Homey.get/set` JS API

### Tertiary (LOW confidence)
- API endpoint method naming convention `post_test_claude` — inferred from Python snake_case patterns, not directly confirmed from official Python SDK API docs. Validate during implementation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — official SDK docs + PyPI pages confirmed versions and API shapes
- Architecture: HIGH — all patterns verified from official Homey Python SDK docs
- Pitfalls: HIGH — critical pitfalls (cold start, blocking event loop, missing settings) confirmed from official sources and pre-research
- Autocomplete callback: HIGH — exact Python signature confirmed from official docs (resolves STATE.md blocker)
- Settings change listener: MEDIUM — absence of `.on()` confirmed; workaround pattern is pragmatic but not from official example

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (Homey SDK stable; anthropic releases weekly but API shape is stable)
