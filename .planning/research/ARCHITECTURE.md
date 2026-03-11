# Architecture Patterns

**Domain:** Homey Python app — multi-provider LLM integration
**Researched:** 2026-03-11
**Confidence:** HIGH (based on official Homey Apps SDK docs + confirmed Python support)

---

## Recommended Architecture

This app has no physical devices to pair. It exposes Flow action cards at the app level, not the driver level. The central challenge is routing a Flow card invocation through a provider abstraction layer to either Ollama or Claude, then returning the AI response as a Flow token.

```
Homey Runtime
│
├── app.py  ←  App singleton (initializes everything)
│       │
│       ├── Registers Flow action cards (on_init)
│       ├── Holds provider_registry (dict of provider instances)
│       └── Reads settings (API keys, default provider, system prompt)
│
├── providers/
│   ├── base.py          ←  Abstract base class: LLMProvider
│   ├── ollama.py        ←  OllamaProvider (AsyncClient from ollama library)
│   └── claude.py        ←  ClaudeProvider (AsyncAnthropic from anthropic library)
│
├── memory/
│   └── conversation_store.py  ←  In-memory dict + homey.settings persistence
│
├── .homeycompose/
│   ├── app.json         ←  App metadata
│   └── flow/
│       └── actions/
│           ├── ask_ai.json          ←  "Ask AI: [prompt]" → returns response token
│           ├── ask_ai_provider.json ←  "Ask AI with [provider]: [prompt]"
│           └── ask_ai_system.json   ←  "Ask AI with system prompt: [system] [prompt]"
│
└── settings/
    └── index.html       ←  API key, Ollama URL, default provider, default model
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `app.py` (App class) | Bootstraps app, registers all Flow card run-listeners, holds shared state | providers/, memory/, Homey runtime |
| `providers/base.py` | Defines `LLMProvider` abstract interface: `async chat(messages, model, **opts)` | Nothing (interface only) |
| `providers/ollama.py` | Wraps `ollama.AsyncClient` — list models, send chat, handle HTTP errors | Ollama HTTP API at configured host |
| `providers/claude.py` | Wraps `anthropic.AsyncAnthropic` — send messages, handle rate limits/auth | Anthropic Messages API (cloud) |
| `memory/conversation_store.py` | Per-session message history dict (keyed by conversation_id), optional persistence via `homey.settings` | app.py reads/writes; `homey.settings` for persistence |
| `.homeycompose/flow/actions/` | Declarative JSON defining card titles, args, and return tokens | Compiled by Homey CLI into app.json |
| `settings/index.html` | Web UI for Ollama URL, Claude API key, default provider/model, system prompt | Reads/writes via `homey.settings` JS API |

---

## Data Flow

### Flow card invocation (single request)

```
User triggers Flow
    → Homey calls run_listener(card_arguments)
    → app.py extracts: prompt, provider_name, model, system_prompt
    → Looks up provider in provider_registry
    → Calls provider.chat(messages=[...], model=model)
    → Provider issues async HTTP request (ollama or anthropic)
    → Response text received
    → run_listener returns {"response": text, "model": model}
    → Homey injects tokens into Advanced Flow
```

### Conversation memory flow

```
Flow card with conversation_id arg
    → app.py looks up history in conversation_store
    → Prepends history to messages list: [system, ...history, new_user_msg]
    → Calls provider.chat(messages)
    → Appends user message + assistant response to history
    → Persists updated history to homey.settings (JSON-serialized)
    → Returns response token
```

### Settings read at startup

```
App.on_init()
    → self.homey.settings.get("ollama_url") → OllamaProvider(host=...)
    → self.homey.settings.get("claude_api_key") → ClaudeProvider(api_key=...)
    → self.homey.settings.get("default_provider") → stored as self._default_provider
    → Register on_settings callback to reinitialize providers on change
```

---

## Patterns to Follow

### Pattern 1: Provider Abstraction via Abstract Base Class

**What:** Define a common `LLMProvider` ABC that both Ollama and Claude implement. App code only sees `LLMProvider`.

**When:** Always — this is the core architectural decision enabling provider switching.

```python
# providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str   # "user" | "assistant" | "system"
    content: str

class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> str:
        """Return assistant response text."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return available model IDs."""
        ...
```

### Pattern 2: App singleton as registry + wiring point

**What:** `App.on_init()` constructs all providers, registers all Flow card listeners. No globals, no module-level state.

**When:** Always — Homey's architecture guarantees one App instance.

```python
# app.py
from homey import app as homey_app
from .providers.ollama import OllamaProvider
from .providers.claude import ClaudeProvider
from .memory.conversation_store import ConversationStore

class App(homey_app.App):
    async def on_init(self) -> None:
        self._store = ConversationStore(self.homey.settings)
        self._providers = await self._init_providers()
        await self._register_flow_cards()

    async def _init_providers(self) -> dict:
        providers = {}
        ollama_url = self.homey.settings.get("ollama_url") or "http://192.168.2.214:11434"
        providers["ollama"] = OllamaProvider(host=ollama_url)

        claude_key = self.homey.settings.get("claude_api_key")
        if claude_key:
            providers["claude"] = ClaudeProvider(api_key=claude_key)
        return providers

    async def _register_flow_cards(self) -> None:
        ask_card = self.homey.flow.get_action_card("ask_ai")
        ask_card.register_run_listener(self._on_ask_ai)

    async def _on_ask_ai(self, args: dict, **kwargs) -> dict:
        provider_name = args.get("provider") or self.homey.settings.get("default_provider", "ollama")
        provider = self._providers[provider_name]
        response = await provider.chat(
            messages=[{"role": "user", "content": args["prompt"]}],
            model=args.get("model") or self.homey.settings.get(f"{provider_name}_model"),
        )
        return {"response": response}

homey_export = App
```

### Pattern 3: Flow token returns for Advanced Flow

**What:** Action cards declare `tokens` in their compose JSON. Run listeners return a matching dict.

**When:** All AI response cards — this is how the response text reaches subsequent Flow cards.

```json
// .homeycompose/flow/actions/ask_ai.json
{
  "title": { "en": "Ask AI: [[prompt]]" },
  "titleFormatted": { "en": "Ask AI: [[prompt]]" },
  "args": [
    { "name": "prompt", "type": "text", "title": { "en": "Prompt" } }
  ],
  "tokens": [
    {
      "name": "response",
      "type": "string",
      "title": { "en": "AI Response" },
      "example": { "en": "The weather today is..." }
    }
  ]
}
```

Note: Cards with `tokens` only appear in Advanced Flow, not standard Flow. This is expected behavior.

### Pattern 4: Settings-driven reconfiguration

**What:** Listen for settings changes and reinitialize providers without app restart.

**When:** API key or Ollama URL is updated in the settings page.

```python
# In App.on_init():
self.homey.settings.on("set", self._on_setting_changed)

async def _on_setting_changed(self, key: str) -> None:
    if key in ("ollama_url", "claude_api_key", "ollama_model", "claude_model"):
        self._providers = await self._init_providers()
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Driver-based architecture for AI providers

**What:** Creating a "provider" as a Homey Device with driver.py + device.py.

**Why bad:** Providers are not physical or virtual devices. Using the device model forces users to pair "AI providers" like devices — wrong mental model, wrong UX. Homey devices have capabilities, lifecycle events (online/offline), and pair wizard flows that don't apply to LLM API clients.

**Instead:** App-level Flow cards registered in `App.on_init()`. The provider is an internal implementation detail.

### Anti-Pattern 2: Synchronous HTTP in run listeners

**What:** Using `requests` library or any blocking HTTP call inside a Flow card run listener.

**Why bad:** Homey's Python runtime is fully async. Blocking calls block the entire event loop, causing timeouts and degraded app performance.

**Instead:** Use `ollama.AsyncClient` and `anthropic.AsyncAnthropic` exclusively. Both are native async.

### Anti-Pattern 3: Storing conversation history per Flow execution without a key

**What:** Storing all conversation history in a single global list.

**Why bad:** Different Flows or Flow executions will corrupt each other's conversation context. Parallel executions race.

**Instead:** Key conversation history by a `conversation_id` string argument on the Flow card. Each Flow/automation has its own conversation thread.

### Anti-Pattern 4: Hardcoding model names in Flow card JSON

**What:** Making model selection a fixed dropdown in the compose JSON with static values.

**Why bad:** Ollama models change as users install/remove them. Static list goes stale.

**Instead:** Use `autocomplete` argument type for model selection. The run listener's autocomplete callback calls `provider.list_models()` dynamically.

### Anti-Pattern 5: Keeping full conversation history without bounds

**What:** Appending every message to history forever without truncation.

**Why bad:** Context window limits (Ollama models: 4K-128K tokens; Claude: 200K tokens). Large histories slow responses and increase cost/memory.

**Instead:** Implement a sliding window: keep last N turns (configurable in settings, default 10). For Claude, consider using the official context management API.

---

## Build Order (Component Dependencies)

The architecture has clear dependency layers. Build bottom-up:

```
Layer 1 — Provider Abstraction (no Homey dependencies)
  providers/base.py            ← standalone ABC, no dependencies
  providers/ollama.py          ← depends on ollama library + base.py
  providers/claude.py          ← depends on anthropic library + base.py

Layer 2 — Memory (no Homey dependencies in core logic)
  memory/conversation_store.py ← depends on base types only; homey.settings is injected

Layer 3 — Homey Flow definitions (no Python dependencies)
  .homeycompose/flow/actions/  ← JSON only, no Python

Layer 4 — App wiring (depends on all above)
  app.py                       ← depends on layers 1-3 + Homey SDK

Layer 5 — Settings UI (depends on Homey settings API)
  settings/index.html          ← depends on Homey settings JS API
```

**Implication for phases:**

1. Build providers/ first — testable with plain `pytest` and no Homey runtime
2. Build conversation_store.py next — testable independently with mock settings
3. Define flow card JSON — no code, fast iteration
4. Wire app.py — requires Docker + Homey Pro to test end-to-end
5. Build settings page — UI polish, can come after functional app works

---

## Scalability Considerations

| Concern | Current scope (2 providers) | Adding a 3rd provider | At 10+ providers |
|---------|----------------------------|-----------------------|-----------------|
| Provider routing | Dict lookup in app.py | Add new class implementing `LLMProvider` | Same pattern, no architectural change |
| Flow card arguments | `provider` arg as text/dropdown | Update autocomplete values | Consider dynamic autocomplete from registry |
| Settings page | Static fields per provider | Add section for new provider | Consider dynamic settings generation |
| Conversation memory | In-memory dict per conversation_id | No change needed | May need LRU eviction if many active conversations |
| Token usage/cost | Not tracked | — | Add usage tracking via provider response metadata |

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| App-level Flow cards (not driver-level) | No devices to pair; AI providers are services not physical hardware |
| Abstract base class over protocol/duck-typing | Explicit interface makes provider contract clear; mypy can verify conformance via homey-stubs |
| No LiteLLM or unified LLM library | Adds a heavy dependency with its own abstractions; direct SDK calls are simpler, more debuggable, and avoid version conflicts in Homey's Docker build |
| Conversation ID as Flow argument | Each automation gets its own context; prevents cross-contamination |
| Settings-driven provider init | API keys never in code; reconfigurable without restart |
| `homey.settings` for conversation persistence | Only available storage primitive; `/userdata/` is publicly accessible so not suitable for API keys or conversation content |

---

## Sources

- [Homey Apps SDK — App structure](https://apps.developer.homey.app/the-basics/app) — HIGH confidence (official docs, Python examples confirmed)
- [Homey Apps SDK — Drivers & Devices](https://apps.developer.homey.app/the-basics/devices) — HIGH confidence (official docs)
- [Homey Apps SDK — Flow cards](https://apps.developer.homey.app/the-basics/flow) — HIGH confidence (official docs)
- [Homey Apps SDK — Flow tokens](https://apps.developer.homey.app/the-basics/flow/tokens) — HIGH confidence (official docs, Python example confirmed)
- [Homey Apps SDK — Persistent Storage](https://apps.developer.homey.app/the-basics/app/persistent-storage) — HIGH confidence (official docs)
- [ollama/ollama-python AsyncClient](https://github.com/ollama/ollama-python) — HIGH confidence (official library)
- [anthropics/anthropic-sdk-python AsyncAnthropic](https://github.com/anthropics/anthropic-sdk-python) — HIGH confidence (official library)
- [Multi-provider LLM adapter patterns](https://brics-econ.org/interoperability-patterns-to-abstract-large-language-model-providers) — MEDIUM confidence (academic/community)
