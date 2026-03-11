# Project Research Summary

**Project:** Homey AI Hub
**Domain:** Homey Pro Python app — multi-provider LLM integration (Claude + Ollama)
**Researched:** 2026-03-11
**Confidence:** HIGH

## Executive Summary

Homey AI Hub is a Homey Pro app that exposes multi-provider LLM capabilities (Anthropic Claude and self-hosted Ollama) as Flow action cards. The architecture is well-understood: a Python app using the Homey SDK runs as a singleton, registers Flow action cards in `on_init`, and routes card invocations through a provider abstraction layer. Both provider SDKs (`anthropic` and `ollama`) are mature official libraries with async-native clients, making the core integration straightforward. The unique value proposition — combining cloud and local AI in a single Homey app — is a genuine gap in the existing market; no competitor does this.

The recommended approach is to build in dependency order from the inside out: provider abstraction layer first (fully testable without Homey runtime), then conversation memory, then Flow card JSON definitions, then app wiring, then the settings UI. This order is not just preference — it is enforced by the architecture. Provider classes and conversation store have no Homey SDK dependency and can be unit-tested with plain `pytest`. The app wiring in `app.py` depends on all of them and requires Docker + Homey Pro to test end-to-end.

The primary risks are operational rather than architectural. Ollama cold-start latency (30-120s after 5-minute idle) will silently break flows if timeouts are not set generously. Conversation history unbounded growth will exhaust context windows after 20-50 turns. The async event loop blocks catastrophically if any synchronous HTTP call slips into the code. All three are known, documented, and preventable with specific implementation choices — none require rework of the architecture.

---

## Key Findings

### Recommended Stack

The Homey Python SDK mandates Python 3.14 (platform-managed, no version choice) with an async-first lifecycle: a single `App` class, a single `async def on_init()` entry point, and all Homey APIs accessed via `self.homey.*`. Dependencies must be installed via `homey app dependency install` (not pip) to ensure cross-platform pre-compilation. Both AI provider SDKs are official, async-native, and actively maintained.

**Core technologies:**
- `anthropic >=0.84.0`: Claude API client — official SDK, async-native (`AsyncAnthropic`), built-in retry logic and streaming
- `ollama >=0.6.1`: Ollama API client — official library, `AsyncClient` with identical sync/async API, minimal footprint
- Homey Python SDK (latest): app runtime and Flow card registration — the only supported way to build Python apps on Homey Pro
- `homey-stubs`: dev-only type hints for Pyright — required for IDE support with Homey SDK classes
- `pytest >=8.0` + `pytest-asyncio >=1.0.0`: test runner — note: v1.0.0 broke `event_loop` fixture, requires `asyncio_mode = "auto"` in config
- `ruff`: linting and formatting — replaces black + flake8 + isort as 2025 standard
- No LangChain, no LiteLLM, no additional HTTP libraries — each is an over-engineered dependency for this use case

### Expected Features

No existing Homey app combines Claude and Ollama. The market is segmented: cloud-only (OpenAI, Gemini, OpenRouter) vs. local-only (Ollama). Multi-provider is the core differentiator. Conversation memory with named sessions (conversation IDs per Flow) is the next significant gap — existing apps either lack it entirely or implement it as a single global context.

**Must have (table stakes):**
- Send prompt, get text response via Flow action card with `{{response}}` token
- API key and Ollama host/port configuration in settings page
- Model selection per flow card (dynamic autocomplete for Ollama, fixed set for Claude)
- System prompt configuration (global minimum, per-card override preferred)
- Connection test / status in settings
- Descriptive error messages surfaced to Flow (not silent failures)

**Should have (differentiators in v1.0):**
- Multi-provider support — pick Claude or Ollama per flow card invocation
- Conversation memory with named session IDs — same ID persists context across executions
- Clear conversation action card — reset named conversation explicitly
- Vision / image analysis via flow card — image droptoken for vision-capable models
- Dynamic Ollama model list via autocomplete callback (live API query, not static list)
- Configurable timeout — required for 30B+ local models

**Defer to v2+:**
- Additional providers (OpenAI, Gemini, OpenRouter)
- Partial/streaming response cards in Flows
- Natural language device control (entirely different product scope)
- MCP server integration (AI Chat Control already covers this)
- Persistent cross-session vector memory / RAG

### Architecture Approach

The app has no physical devices, so the entire implementation lives at the App level: Flow action cards registered in `App.on_init()`, a `providers/` abstraction layer with an ABC defining `chat()` and `list_models()`, a `ConversationStore` keyed by conversation ID, and a settings HTML page. The Homey runtime guarantees a single App instance, making it the natural registry and wiring point. Conversation history persists to `homey.settings` (JSON) as the only available storage primitive — `userdata/` is unsuitable because its files are publicly accessible over the local network.

**Major components:**
1. `providers/base.py` — `LLMProvider` abstract base class defining `async chat()` and `async list_models()`; no Homey dependency
2. `providers/ollama.py` + `providers/claude.py` — concrete implementations wrapping official SDKs; independently testable
3. `memory/conversation_store.py` — in-memory dict with `homey.settings` persistence; TTL eviction to prevent memory leaks
4. `.homeycompose/flow/actions/` — declarative JSON defining card titles, argument types, and return tokens; never edit `app.json` directly
5. `app.py` — App singleton: reads settings, initializes providers, registers all Flow card run-listeners, handles settings-change reconfiguration
6. `settings/index.html` — Homey settings page: API key inputs (masked), Ollama URL, default provider/model, system prompt, connection test button

### Critical Pitfalls

1. **Async event loop blocking** — Using `requests` or any synchronous HTTP client inside an `async def` freezes the entire Homey app for the duration of the LLM call. Prevention: use `ollama.AsyncClient` and `anthropic.AsyncAnthropic` exclusively; never import `requests`.

2. **Flow card resolving before LLM responds** — Forgetting `await` anywhere in the async chain causes the action card to return an empty token. Prevention: always `await` the full provider response chain before returning the token dict from the run listener.

3. **Ollama cold-start timeout** — Models unload after 5 minutes idle; first request after idle takes 30-120s for large models. Prevention: set HTTP timeout >= 120s for small models, >= 300s for 30B+; expose as a configurable setting; test with a cold Ollama server.

4. **Conversation history context exhaustion** — Unbounded message history hits context window limits after 20-50 turns (Claude: 400 error; Ollama: silent truncation or error). Prevention: sliding window with configurable max (default 20 messages); implement "clear conversation" action card.

5. **API key in env.json published to App Store** — `env.json` is bundled in app submissions. Prevention: user API keys go through the settings UI only; `env.json` stays empty or in `.gitignore`; audit before any submission.

---

## Implications for Roadmap

Based on research, the architecture has clear dependency layers that enforce build order. Suggested phase structure:

### Phase 1: Foundation and Core AI Integration

**Rationale:** Providers and Flow card wiring are the foundational dependency for everything else. Architecture research confirms providers are testable without Homey runtime — build and validate them first. This phase also addresses the highest-density set of critical pitfalls.

**Delivers:** A working Homey app with `ask_ai` action card routing to either Claude or Ollama, model selection via autocomplete, settings page with API key configuration and connection test, and proper error handling throughout.

**Addresses:**
- Send prompt, get response (table stakes #1)
- Provider/model selection per card
- API key + Ollama host configuration
- Connection validation
- Error handling with descriptive messages
- Dynamic Ollama model list (autocomplete)

**Avoids:**
- Async event loop blocking (use `AsyncClient` / `AsyncAnthropic` exclusively)
- Flow card returning before LLM responds (full await chain)
- Ollama cold-start failure (generous timeouts, configurable)
- Settings crash on first install (null-check all settings reads)
- Manifest overwrite (always edit `.homeycompose/`, never `app.json`)
- API key in env.json (design settings UI first)

### Phase 2: Conversation Memory and System Prompts

**Rationale:** Memory depends on a working provider layer from Phase 1. Conversation ID routing, sliding window logic, and persistence to `homey.settings` are self-contained additions that don't require changes to the provider abstraction. This grouping keeps Phase 1 lean and testable.

**Delivers:** Named conversation sessions with persistent history, configurable sliding window (default 20 messages), clear conversation action card, global and per-card system prompt override.

**Addresses:**
- Conversation memory with named session IDs (differentiator)
- Clear conversation action card
- System prompt (global + per-card)
- Per-card provider selection (full multi-provider value)

**Avoids:**
- Unbounded history exhausting context window (sliding window from day one)
- In-memory dict memory leak on Homey Pro (TTL eviction + settings persistence)
- System prompt consuming too much context budget (token count warning in UI)

### Phase 3: Vision and Image Support

**Rationale:** Vision builds on the working prompt/response card as an extension. Image droptokens require a specific Homey Flow argument type (`image`). This is medium complexity and depends on Phases 1-2 being stable. Deferred to Phase 3 to avoid scope creep in the foundational build.

**Delivers:** `ask_ai_with_image` action card accepting an image droptoken, compatible with vision-capable models (Ollama: `qwen2.5vl`, `gemma3`; Claude: claude-3+ models).

**Addresses:**
- Vision / image analysis (differentiator)

**Avoids:**
- userdata publicly accessible (use in-memory base64 encoding, delete after API call, UUID filenames if storage needed)

### Phase 4: Polish and App Store Preparation

**Rationale:** App Store submission has specific review requirements that are best addressed as a focused phase rather than scattered across implementation. This phase also covers documentation, localization strategy, and submission audit.

**Delivers:** App Store-ready submission: English-only localization (no partial translations), Flow card titles passing review guidelines (short, imperative, no parentheses), env.json audit, app description, icon, and changelog.

**Avoids:**
- Flow card title rejections (audit against guidelines)
- Translation inconsistency rejection (English-only until full translation is resourced)
- API key in env.json published accidentally

### Phase Ordering Rationale

- Providers before app wiring: `providers/` has no Homey SDK dependency and is fully unit-testable with `pytest`. Building it first lets you validate the AI integration before needing Docker + Homey Pro hardware.
- Memory after providers: `ConversationStore` only needs a working provider layer to be useful. Bundling memory into Phase 1 would add risk without benefit.
- Vision after memory: vision is an additive feature with its own pitfall set (userdata exposure). Keeping it isolated reduces Phase 1-2 scope.
- App Store prep last: review requirements are blocking for submission, not development. Deferring avoids premature polish of things that may change.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 1:** Homey autocomplete argument type for dynamic model lists needs confirmed implementation pattern — official docs describe the type but the Python SDK callback signature for autocomplete is not verified with a code example.
- **Phase 3:** Homey image droptoken handling in Python SDK needs verification — image token type is documented in JS SDK context; Python equivalent callback signature is unconfirmed.

Phases with standard patterns (skip research-phase):

- **Phase 2:** Conversation memory is in-memory dict + JSON serialization to `homey.settings`. Both patterns are confirmed and simple. No research needed.
- **Phase 4:** App Store guidelines are fully documented. Checklist application, no research needed.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Both `anthropic` and `ollama` are official SDKs verified via PyPI and GitHub. Homey Python SDK patterns verified via official docs with Python code examples confirmed. Minor gap: `homey-stubs` PyPI page failed to load for version check — treat as dev-only install. |
| Features | HIGH | Competitive analysis based on live Homey App Store pages + community forum threads + GitHub source for two apps. Feature gaps are clearly identifiable. |
| Architecture | HIGH | Architecture patterns are based entirely on official Homey Apps SDK docs with Python examples. All component boundaries verified. Only minor unverified item: Python autocomplete callback signature. |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls (async blocking, cold-start, context window) verified against official docs and multiple sources. Memory leak/Homey RAM estimates based on community empirical data (MEDIUM confidence). App Store title rules verified (HIGH). |

**Overall confidence:** HIGH

### Gaps to Address

- **Python autocomplete callback signature:** The `autocomplete` argument type is documented for Flow cards, but the exact Python SDK callback signature (how the autocomplete handler is registered and what arguments it receives) was not confirmed with a running code example. Resolve during Phase 1 planning by checking the Homey developer forum or SDK source.
- **homey-stubs PyPI version:** Could not verify the current PyPI version of `homey-stubs` during research. Install as dev dependency and verify at project setup; it should not affect app functionality.
- **Image droptoken Python SDK pattern:** Homey image token handling is documented in JS SDK context. The Python equivalent for accepting an image in a Flow card run listener needs validation. Flag for Phase 3 planning.

---

## Sources

### Primary (HIGH confidence)
- [Homey Apps SDK — App structure and Python runtime](https://apps.developer.homey.app/the-basics/app)
- [Homey Apps SDK — Flow cards](https://apps.developer.homey.app/the-basics/flow)
- [Homey Apps SDK — Flow tokens](https://apps.developer.homey.app/the-basics/flow/tokens)
- [Homey Apps SDK — App Settings](https://apps.developer.homey.app/advanced/custom-views/app-settings)
- [Homey Apps SDK — Persistent Storage](https://apps.developer.homey.app/the-basics/app/persistent-storage)
- [Homey App Store Guidelines](https://apps.developer.homey.app/app-store/guidelines)
- [Homey SDK v3 — Upgrade Guide](https://apps.developer.homey.app/upgrade-guides/upgrading-to-sdk-v3)
- [anthropic PyPI](https://pypi.org/project/anthropic/) — v0.84.0
- [ollama Python library PyPI](https://pypi.org/project/ollama/) — v0.6.1
- [Anthropic API — Messages Streaming](https://platform.claude.com/docs/en/api/messages-streaming)
- [Anthropic API — Errors](https://docs.anthropic.com/en/api/errors)
- [Anthropic API — Rate Limits](https://platform.claude.com/docs/en/api/rate-limits)
- [Ollama FAQ — Model Unload Timeout](https://docs.ollama.com/faq)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) — v1.0.0 breaking changes
- [OpenAI app on Homey](https://homey.app/en-us/app/com.openai.ChatGPT/OpenAI/)
- [Ollama app on Homey](https://homey.app/en-us/app/com.ollama/Ollama/)
- [Gemini AI app on Homey](https://homey.app/en-us/app/com.dimapp.geminiai/Gemini-AI/)
- [AI Chat Control app on Homey](https://homey.app/en-us/app/nl.joonix.aichatcontrol/AI-Chat-Control/)
- [OpenRouter app on Homey](https://homey.app/en-us/app/be.titansofindustry.openrouter/OpenRouter/)

### Secondary (MEDIUM confidence)
- [Homey Community — Secure API Key Storage](https://community.homey.app/t/how-to-securely-store-username-and-password-for-an-api-within-my-app/72180)
- [Homey Community — Flow Execution Time Limits](https://community.homey.app/t/flow-execution-time-limit-persistent-delays/65690)
- [Homey Community — Homey Pro 2023 Memory](https://community.homey.app/t/homey-pro-2023-memory-question/88599)
- [Homey Community — Ollama app forum thread](https://community.homey.app/t/app-pro-ollama-use-local-llms-in-your-flows/143768)
- [AI Chat Control GitHub](https://github.com/jvmenen/homey-ai-chat-control)
- [OpenRouter GitHub](https://github.com/timbroddin/homey-openrouter/)
- [Multi-provider LLM adapter patterns](https://brics-econ.org/interoperability-patterns-to-abstract-large-language-model-providers)

### Tertiary (LOW confidence)
- [Homey AI Extensions community discussion](https://community.homey.app/t/ai-extensions-and-tools-for-homey/135948) — user desire signals, small sample
- [Collabnix: Ollama Production Pitfalls](https://collabnix.com/ollama-api-integration-building-production-ready-llm-applications/) — verified against official Ollama docs

---
*Research completed: 2026-03-11*
*Ready for roadmap: yes*
