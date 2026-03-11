# Technology Stack

**Project:** Homey AI Hub (Homey Python app with multi-provider LLM integration)
**Researched:** 2026-03-11
**Mode:** Ecosystem

---

## Recommended Stack

### Core: Homey Python SDK

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Homey Python SDK | Latest (managed by Homey CLI) | App runtime, Flow cards, Settings | The only way to build Python apps that run on Homey Pro. Supports Python 3.14, async/await throughout. |
| Python | 3.14 (pinned by Homey platform) | Runtime language | Homey Pro runs "the latest available full release, currently 3.14" — no version choice needed. |
| homey-stubs | Latest via PyPI | Type hints and IDE autocomplete for Homey SDK classes | Official Athom package for Pyright-based static type checking. Referenced in official SDK docs. |

**MEDIUM confidence** — The SDK runtime details (Python 3.14, async lifecycle, Flow card registration pattern) are confirmed by official Homey developer docs fetched directly. `homey-stubs` is referenced in official docs but PyPI page failed to load for version verification; treat as a dev-only dependency to install as needed.

**Critical SDK patterns confirmed:**

- App entry point: `app.py` with async class extending `Homey.App`
- Lifecycle: `async def on_init(self) -> None` is the single entry point
- Settings: `self.homey.settings.get("key")` / `self.homey.settings.set("key", value)` — JSON-serializable only
- Flow action registration: `card = self.homey.flow.get_action_card("card_id")` + `card.register_run_listener(async_fn)`
- Flow token return: action handler returns a `dict` matching token keys defined in manifest
- Dependencies: managed via `homey app dependency install` (NOT pip directly); pre-compiled into `.python_cache`

---

### AI/LLM Libraries

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `anthropic` | `>=0.84.0` (latest: 0.84.0 as of Feb 25 2026) | Claude API client | Official Anthropic SDK. Provides both sync `Anthropic` and async `AsyncAnthropic` clients powered by httpx. Supports streaming via `client.messages.stream()` context manager. Maintained rapidly (weekly releases). |
| `ollama` | `>=0.6.1` (latest: 0.6.1 as of Nov 13 2025) | Ollama local model client | Official Ollama Python library. Provides `AsyncClient` with identical interface to sync client. Has `chat()`, `generate()`, `list()`, `embed()`, and streaming via `stream=True`. Minimal dependency footprint. |

**HIGH confidence** — Both are official clients from the model providers, verified via PyPI and GitHub.

**Key async patterns:**

```python
# Anthropic async streaming
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=api_key)
async with client.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=conversation_history,
) as stream:
    async for text in stream.text_stream:
        response_text += text

# Ollama async streaming
from ollama import AsyncClient

client = AsyncClient(host="http://192.168.2.214:11434")
async for chunk in await client.chat(
    model="llama3.1:8b",
    messages=conversation_history,
    stream=True,
):
    response_text += chunk["message"]["content"]

# Ollama list available models
models_response = await client.list()
model_names = [m.model for m in models_response.models]
```

---

### HTTP / Async

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `httpx` | Pulled in transitively by `anthropic` SDK | HTTP transport for Anthropic SDK | The `anthropic` package requires httpx as its internal HTTP client. Do NOT install separately — just let it come as a transitive dependency. |

**No additional HTTP library needed.** The `anthropic` SDK already embeds httpx. The `ollama` library handles its own transport. Avoid adding `aiohttp` or `requests` as explicit dependencies — they add weight without benefit for this use case.

**Note on aiohttp vs httpx:** If future requirements need raw HTTP calls beyond what the provider SDKs offer, prefer `httpx` (AsyncClient) over `aiohttp`. Rationale: httpx supports both sync and async, has cleaner API, and is already in the dependency tree. `aiohttp` is marginally faster for very high concurrency scenarios that are irrelevant for a Homey app handling 1-10 req/min.

---

### Conversation Memory

| Pattern | Library | Why |
|---------|---------|-----|
| In-memory message list | Python built-ins (`list`, `dict`) | For v1, store `messages: list[dict]` per conversation session in the App class. No external dependency. Conversation IDs keyed off a string identifier. |

**Do NOT use LangChain for memory management.** It is an unnecessary heavyweight dependency for what amounts to a list of `{"role": "...", "content": "..."}` dicts. Both `anthropic` and `ollama` accept OpenAI-compatible message arrays directly.

**Conversation history pattern:**
```python
# Store per conversation_id in app state
self._conversations: dict[str, list[dict]] = {}

def _get_or_create_conversation(self, conv_id: str) -> list[dict]:
    if conv_id not in self._conversations:
        self._conversations[conv_id] = []
    return self._conversations[conv_id]

def _append_message(self, conv_id: str, role: str, content: str) -> None:
    history = self._get_or_create_conversation(conv_id)
    history.append({"role": role, "content": content})

def _trim_to_token_budget(self, history: list[dict], max_turns: int = 20) -> list[dict]:
    # Keep system prompt + last N exchanges
    return history[-max_turns * 2:]
```

---

### Type Safety & Code Quality (Dev Only)

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| `pyright` | Latest | Static type checking | The official Homey SDK recommends Pyright specifically (not mypy) for use with `homey-stubs`. Use VS Code Pylance extension (which uses Pyright internally). |
| `ruff` | Latest (`>=0.9.0`) | Linting + formatting | Replaces black + isort + flake8. Single tool, Rust-speed, 2025 standard for new Python projects. Configured in `pyproject.toml`. |

**MEDIUM confidence** — Pyright recommendation verified via official Homey docs. Ruff recommendation verified via multiple 2025 sources.

---

### Testing

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pytest` | `>=8.0` | Test runner | Standard Python test runner. No alternative justified for this project size. |
| `pytest-asyncio` | `>=1.0.0` | Async test support | Required for testing async code. **Version 1.0.0 (May 2025) introduced breaking changes** — dropped `event_loop` fixture, uses `loop_scope` config. Use `asyncio_mode = "auto"` in `pytest.ini` or `pyproject.toml` to avoid decorating every test. |
| `pytest-mock` | Latest | Mock external API calls | Homey SDK is unavailable in test environment; all `self.homey.*` calls must be mocked. Provider API calls (Anthropic, Ollama) must be mocked for unit tests. |

**HIGH confidence** — pytest-asyncio 1.0 release date verified. Breaking change re: event_loop fixture is documented in multiple sources.

**Testing constraint:** Homey apps cannot be fully integration-tested without Docker + actual Homey Pro device. Unit tests cover: provider client logic, conversation management, settings handling. Integration tests require `homey app run` with Docker.

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## Dependency Management

**Use `homey app dependency install <package>` — NOT `pip install`.** The Homey CLI pre-compiles Python dependencies for cross-platform distribution and stores them in `.python_cache`. Installing via pip bypasses this and will fail on device deployment.

```bash
# Install production dependencies
homey app dependency install anthropic
homey app dependency install ollama

# Dev dependencies (NOT via homey CLI — local dev only)
pip install pytest pytest-asyncio pytest-mock pyright ruff
```

**Python version constraint:** Homey runs Python 3.14. All dependencies must support Python 3.14. Both `anthropic` (requires >=3.9) and `ollama` (requires >=3.8) are compatible. No issues anticipated.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Claude client | `anthropic` SDK | `requests` + raw REST | Official SDK handles auth, retries, streaming, type safety. Raw REST would be hand-rolled reimplementation. |
| Ollama client | `ollama` library | `httpx` direct to REST | Official library wraps all Ollama API endpoints. Direct REST is lower-level with no benefit. |
| Async HTTP (extra) | `httpx` (transitive) | `aiohttp` | httpx already in dependency tree via anthropic. aiohttp adds 400KB+ for no benefit at this request volume. |
| Memory management | In-memory dict | LangChain, LangMem | LangChain is 50MB+ of transitive dependencies for list management. Over-engineered for v1. |
| Type checking | Pyright | mypy | Homey SDK officially recommends Pyright for use with homey-stubs. Homey SDK docs explicitly mention Pyright, not mypy. |
| Linting | ruff | black + flake8 + isort | Ruff replaces all three, is faster, has same output, is 2025 standard. |

---

## Project Structure

```
com.example.homey-ai-hub/
├── app.py               # Main App class, on_init, Flow card registration
├── app.json             # App manifest (id, name, permissions)
├── env.json             # Sensitive config (API keys, not in source control)
├── .homeycompose/
│   └── app.json         # Compose manifest (alternative to app.json)
├── .homeycompose/flow/
│   └── actions/
│       ├── ask_ai.json  # "Ask AI" action card definition
│       └── ask_ai_with_provider.json
├── settings/
│   └── index.html       # Settings page (API keys, provider config)
├── lib/
│   ├── providers/
│   │   ├── base.py      # Abstract BaseProvider
│   │   ├── claude.py    # ClaudeProvider using anthropic SDK
│   │   └── ollama.py    # OllamaProvider using ollama SDK
│   └── conversation.py  # ConversationManager (in-memory history)
├── locales/
│   ├── en.json
│   └── nl.json
└── tests/               # pytest tests (dev only, not packaged)
    ├── test_claude.py
    ├── test_ollama.py
    └── test_conversation.py
```

---

## Not Included (Out of Scope for v1)

| Library | Why Not |
|---------|---------|
| `langchain` | 50MB+ dependency for simple message list management. Overkill. |
| `openai` SDK | Out of scope for v1 (project decision: Claude + Ollama only) |
| `pydantic-settings` | Homey provides its own settings API via `homey.settings`. No `.env` files needed. |
| `fastapi` / `aiohttp` web server | Homey provides its own Web API layer via `api.py`. Not needed. |
| `sqlite3` / any database | Conversation history in-memory only for v1. No persistence needed. |

---

## Sources

- [Homey Apps SDK — App structure and Python runtime](https://apps.developer.homey.app/the-basics/app) — HIGH confidence, official docs
- [Homey Apps SDK — Flow cards](https://apps.developer.homey.app/the-basics/flow) — HIGH confidence, official docs
- [Homey Apps SDK — Flow tokens](https://apps.developer.homey.app/the-basics/flow/tokens) — HIGH confidence, official docs
- [Homey Apps SDK — App Settings](https://apps.developer.homey.app/advanced/custom-views/app-settings) — HIGH confidence, official docs
- [anthropic PyPI page](https://pypi.org/project/anthropic/) — HIGH confidence, official package registry; v0.84.0, Feb 25 2026
- [anthropic GitHub releases](https://github.com/anthropics/anthropic-sdk-python/releases) — HIGH confidence, official
- [Anthropic streaming docs](https://platform.claude.com/docs/en/api/messages-streaming) — HIGH confidence, official
- [ollama Python library PyPI](https://pypi.org/project/ollama/) — HIGH confidence, official; v0.6.1, Nov 13 2025
- [ollama-python GitHub](https://github.com/ollama/ollama-python) — HIGH confidence, official
- [pytest-asyncio 1.0 release](https://pypi.org/project/pytest-asyncio/) — HIGH confidence, official PyPI
- [Ruff FAQ](https://docs.astral.sh/ruff/faq/) — HIGH confidence, official docs
