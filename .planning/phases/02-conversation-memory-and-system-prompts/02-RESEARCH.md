# Phase 2: Conversation Memory and System Prompts - Research

**Researched:** 2026-03-11
**Domain:** Homey Python SDK — in-memory conversation sessions, sliding window history, system prompt injection, Flow card design
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FLOW-03 | User can set system prompt dynamically per flow via action card | New `ask_ai_with_system` card with optional `system_prompt` text arg; provider ABC needs `system_prompt` kwarg; Anthropic requires top-level `system=` param, Ollama uses `{"role":"system"}` message |
| FLOW-04 | User can use named conversation sessions for isolated multi-turn context | `ConversationStore` class keyed by `conversation_id` string; modify `ask_ai` card to add optional `conversation_id` text arg; history prepended as messages list before each call |
| FLOW-05 | User can clear a conversation session via Flow action card | New `clear_conversation` card with `conversation_id` text arg; calls `store.clear(conversation_id)` and returns confirmation token |
| CONF-02 | User can set a global system prompt in settings | New `global_system_prompt` textarea field in settings/index.html; read in `_get_provider()` / run_listener; per-card prompt overrides global |
| CONF-03 | User can configure max conversation history length (sliding window) | New `max_history_turns` number field in settings; `ConversationStore.trim()` enforces sliding window; default 10 turns |
</phase_requirements>

---

## Summary

Phase 2 builds on the working Phase 1 `ask_ai` card to add named conversation sessions, a `clear_conversation` card, and system prompt support at both global (settings) and per-card (Flow arg) levels. The entire implementation lives in Python — no new external libraries are needed. The only external research finding that materially affects implementation is the **provider-level difference in system prompt format**: Anthropic's `messages.create()` takes `system=` as a top-level parameter (NOT a `{"role":"system"}` message), while Ollama's `chat()` accepts `{"role":"system"}` as the first element of the messages array.

Conversation history is stored in a `ConversationStore` class held on the `App` singleton. For v1, in-memory storage is sufficient; `homey.settings` should be used for optional persistence across app restarts. The store must enforce a configurable sliding window (default 10 turns = 20 messages) to prevent context window exhaustion and memory growth. The additional `conversation_id` argument on the `ask_ai` card is optional (`"required": false`) — when absent, the card behaves as a stateless single-turn call, preserving backward compatibility.

Settings additions are two new fields in `settings/index.html`: a text input for `global_system_prompt` and a number input for `max_history_turns`. Both are read on every `_get_provider()` call (consistent with the existing pattern of re-reading settings on each invocation since Python ManagerSettings has no `.on()` event).

**Primary recommendation:** Implement `ConversationStore` as a standalone pure-Python class with no Homey SDK dependency, add `system_prompt: str | None = None` to the `LLMProvider.chat()` ABC, wire the store and system prompt logic in `app.py` run_listeners, and add the two new Flow card JSON definitions to `.homeycompose/flow/actions/`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python built-ins (`dict`, `list`) | 3.12+ | Conversation session storage | No external dependency needed; both providers accept `list[dict]` natively |
| `anthropic` | >=0.84.0 (already installed) | System prompt via top-level `system=` parameter | Already in use; `messages.create(system=..., messages=[...])` is the correct API |
| `ollama` | >=0.6.1 (already installed) | System prompt via `{"role":"system"}` in messages list | Already in use; OpenAI-compatible message format supports `system` role |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `homey.settings` | Homey SDK | Persist conversation history across app restarts | Optional persistence — always read/write via `self.homey.settings.get/set` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory dict + optional settings persistence | SQLite / JSON file | homey.settings is the documented persistence layer; sqlite adds dependency; `/userdata/` is publicly network-accessible |
| Sliding window trim (count-based) | Token-based trim | Token counting requires model-specific tokenizers (heavy dependency); turn-count sliding window is simpler and deterministic |
| Optional `conversation_id` on existing `ask_ai` card | Separate `ask_ai_with_memory` card | Optional arg preserves backward compat; single card is less confusing in Homey Flow builder |

**Installation:** No new packages required. All required libraries are already in Phase 1 dependencies.

---

## Architecture Patterns

### Recommended Project Structure (additions to Phase 1)

```
homey-ai-hub/
├── app.py                                    # MODIFY: wire ConversationStore, new cards
├── lib/
│   ├── providers/
│   │   ├── base.py                           # MODIFY: add system_prompt param to chat()
│   │   ├── claude.py                         # MODIFY: pass system= top-level param
│   │   └── ollama_provider.py                # MODIFY: inject {"role":"system"} message
│   └── conversation_store.py                 # NEW: ConversationStore class
├── .homeycompose/flow/actions/
│   ├── ask_ai.json                           # MODIFY: add optional conversation_id arg
│   └── clear_conversation.json              # NEW: card definition
├── settings/index.html                      # MODIFY: global_system_prompt + max_history_turns
└── tests/
    └── test_conversation_store.py           # NEW: unit tests for ConversationStore
```

### Pattern 1: ConversationStore — In-Memory with Optional Settings Persistence

**What:** Standalone pure-Python class that maps `conversation_id -> list[dict]`. No Homey SDK import in the class itself. The `App` injects `homey.settings` via constructor for optional persistence.

**When to use:** Any time `ask_ai` receives a non-empty `conversation_id` argument.

```python
# lib/conversation_store.py
class ConversationStore:
    """Per-session message history, keyed by conversation_id string.

    Storage is in-memory by default. Pass a settings object to enable
    persistence across app restarts via homey.settings.
    """

    SETTINGS_KEY_PREFIX = "conv_"

    def __init__(self, settings=None, max_turns: int = 10) -> None:
        self._sessions: dict[str, list[dict]] = {}
        self._settings = settings  # injected homey.settings (or None for tests)
        self._max_turns = max_turns

    def get(self, conversation_id: str) -> list[dict]:
        """Return current history for conversation_id (empty list if new)."""
        if conversation_id not in self._sessions:
            # Try to restore from settings persistence
            if self._settings:
                stored = self._settings.get(f"{self.SETTINGS_KEY_PREFIX}{conversation_id}")
                if stored and isinstance(stored, list):
                    self._sessions[conversation_id] = stored
                else:
                    self._sessions[conversation_id] = []
            else:
                self._sessions[conversation_id] = []
        return self._sessions[conversation_id]

    def append(self, conversation_id: str, role: str, content: str) -> None:
        """Append a message and trim to sliding window."""
        history = self.get(conversation_id)
        history.append({"role": role, "content": content})
        self._trim(conversation_id)
        self._persist(conversation_id)

    def clear(self, conversation_id: str) -> None:
        """Delete all history for a conversation_id."""
        self._sessions.pop(conversation_id, None)
        if self._settings:
            self._settings.unset(f"{self.SETTINGS_KEY_PREFIX}{conversation_id}")

    def _trim(self, conversation_id: str) -> None:
        """Enforce sliding window: keep last max_turns exchanges (2 msgs each)."""
        history = self._sessions.get(conversation_id, [])
        max_messages = self._max_turns * 2
        if len(history) > max_messages:
            self._sessions[conversation_id] = history[-max_messages:]

    def _persist(self, conversation_id: str) -> None:
        if self._settings:
            self._settings.set(
                f"{self.SETTINGS_KEY_PREFIX}{conversation_id}",
                self._sessions[conversation_id]
            )
```

### Pattern 2: System Prompt Injection — Provider-Specific Format

**What:** The `LLMProvider.chat()` ABC gains `system_prompt: str | None = None`. Each provider implementation translates this into the correct API format.

**Critical difference:**
- **Anthropic**: top-level `system=` parameter, NOT a message in the array (Anthropic has no `"system"` role in the messages list)
- **Ollama**: `{"role": "system", "content": "..."}` inserted as the FIRST element of the messages array

```python
# lib/providers/base.py — modified signature
@abstractmethod
async def chat(
    self,
    messages: list[dict],
    model: str,
    timeout: float | None = None,
    system_prompt: str | None = None,
) -> str: ...
```

```python
# lib/providers/claude.py — pass system= as top-level parameter
async def chat(self, messages, model, timeout=None, system_prompt=None) -> str:
    kwargs = dict(model=model, max_tokens=1024, messages=messages)
    if system_prompt:
        kwargs["system"] = system_prompt   # top-level param, NOT in messages
    response = await self._client.messages.create(**kwargs)
    return response.content[0].text
```

```python
# lib/providers/ollama_provider.py — prepend system role message
async def chat(self, messages, model, timeout=None, system_prompt=None) -> str:
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + list(messages)
    response = await self._client.chat(model=model, messages=messages)
    return response.message.content
```

### Pattern 3: run_listener with Memory and System Prompt

**What:** The `ask_ai` run_listener is extended to handle optional `conversation_id` and `system_prompt` args. Logic:
1. If `conversation_id` present, load history from store
2. Determine effective system prompt (per-card overrides global setting)
3. Call `provider.chat(messages=full_history, system_prompt=effective_prompt)`
4. Append user message and assistant response to store

```python
async def run_listener(args: dict, **kwargs) -> dict:
    # ... existing provider lookup ...

    prompt = args.get("prompt", "")
    conversation_id = args.get("conversation_id", "").strip()  # optional arg
    per_card_system = args.get("system_prompt", "").strip()    # optional arg

    # System prompt precedence: per-card > global setting > None
    global_system = (self.homey.settings.get("global_system_prompt") or "").strip()
    effective_system = per_card_system or global_system or None

    # Build message list
    if conversation_id:
        history = self._store.get(conversation_id)
        messages = list(history) + [{"role": "user", "content": prompt}]
    else:
        messages = [{"role": "user", "content": prompt}]

    response = await provider.chat(
        messages=messages,
        model=model,
        system_prompt=effective_system,
    )

    # Persist turn if using a named session
    if conversation_id:
        self._store.append(conversation_id, "user", prompt)
        self._store.append(conversation_id, "assistant", response)

    return {"response": response}
```

### Pattern 4: clear_conversation Flow Card

**What:** New action card with a single `conversation_id` text argument. Returns a confirmation string token.

```json
// .homeycompose/flow/actions/clear_conversation.json
{
  "id": "clear_conversation",
  "title": { "en": "Clear conversation" },
  "titleFormatted": { "en": "Clear conversation [[conversation_id]]" },
  "args": [
    {
      "name": "conversation_id",
      "type": "text",
      "title": { "en": "Conversation ID" },
      "placeholder": { "en": "my-morning-briefing" }
    }
  ],
  "tokens": [
    {
      "name": "result",
      "type": "string",
      "title": { "en": "Result" },
      "example": { "en": "Conversation cleared." }
    }
  ]
}
```

### Pattern 5: Optional conversation_id on ask_ai card

**What:** Add `conversation_id` as an optional text argument to `ask_ai.json`. Add optional `system_prompt` text argument for FLOW-03.

```json
// Additional args to add to .homeycompose/flow/actions/ask_ai.json
{
  "name": "conversation_id",
  "type": "text",
  "required": false,
  "title": { "en": "Conversation ID" },
  "placeholder": { "en": "Leave empty for single-turn" }
},
{
  "name": "system_prompt",
  "type": "text",
  "required": false,
  "title": { "en": "System Prompt (optional)" },
  "placeholder": { "en": "You are a helpful assistant for my smart home." }
}
```

### Anti-Patterns to Avoid

- **`{"role": "system"}` in Anthropic messages array:** Anthropic Messages API does NOT support the `system` role in the messages list. Use the top-level `system=` parameter on `messages.create()`. Passing a system role as a message will cause a 400 validation error.
- **Storing full history in messages passed to provider:** Only pass `[{"role":"user",...}, {"role":"assistant",...}, ...]` (turns) in the messages list. Do not duplicate the system prompt inside the messages array when also passing `system=`.
- **Persisting conversation history per key every single call:** Calling `homey.settings.set()` synchronously on every turn is acceptable but could be slow for long histories. Consider debouncing or only persisting on `clear_conversation`. For v1, persist-on-write is fine.
- **Mixing stateful and stateless calls into the same history:** If `conversation_id` is empty string/None, treat the call as stateless and do not read or write the store. Guard with `if conversation_id:`.
- **Unbounded conversation growth without TTL:** v1 sliding window is turn-count-based. This is sufficient. Do NOT skip the trim step.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting for context window enforcement | Custom tokenizer | Turn-count sliding window (`max_turns * 2` messages) | Tokenizers are model-specific; `tiktoken` is OpenAI-specific; turn-count is a good proxy without external deps |
| Session serialisation format | Custom binary format | Plain `list[dict]` via `homey.settings.set()` | `homey.settings` accepts any JSON-serializable value; list[dict] is natively JSON-serializable |
| Conversation persistence / TTL | Database (sqlite3) | In-memory + `homey.settings` key per conversation_id | No database needed; settings persist across restarts; TTL eviction is out of scope for v1 |
| LLM message format abstraction | Unified message class | Provider-specific injection (Anthropic `system=`, Ollama message prepend) | Two providers, explicit per-provider logic is clearest; no abstraction layer needed at this scale |

**Key insight:** Conversation memory at this scale is literally a list of dicts plus a trim function. Any library that wraps this (LangChain, LiteLLM memory) adds 50MB+ of transitive dependencies for zero functional gain.

---

## Common Pitfalls

### Pitfall 1: Anthropic Rejects `{"role":"system"}` in Messages Array
**What goes wrong:** Developer adds `{"role":"system","content":"..."}` to the messages list passed to `messages.create()`. Anthropic returns HTTP 400: `messages.0.role: Input should be 'user' or 'assistant'`.
**Why it happens:** Ollama's format uses the system role in the messages array; developer reuses the same pattern for Claude.
**How to avoid:** Always pass Anthropic's system prompt via the top-level `system=` kwarg, never in the messages list. Both formats are confirmed by official API docs (HIGH confidence).
**Warning signs:** `APIStatusError` with status 400 and a validation message about the `role` field.

### Pitfall 2: History Appended Before vs. After the API Call
**What goes wrong:** Developer appends the user message to the store BEFORE calling the API, then fails to clean up if the API call errors. On the next invocation, the history contains an orphaned user message with no assistant response, corrupting the conversation state.
**Why it happens:** Ordering of append vs. API call is unclear.
**How to avoid:** Append user message AND assistant response AFTER the API call succeeds. If the call errors, do not modify the store. The error string returned is not persisted.
**Warning signs:** History has N user messages and N-1 assistant messages after an API error.

### Pitfall 3: Sliding Window Removes Context the AI Needs
**What goes wrong:** Default `max_turns=10` trims 11+ turn conversations, causing the AI to "forget" earlier context. Users report the AI "losing memory" after extended use.
**Why it happens:** Sliding window is count-based and will always lose old context.
**How to avoid:** Expose `max_history_turns` as a user-configurable setting (CONF-03). Default to 10 turns. Document that higher values increase API response time and cost for Claude.
**Warning signs:** User reports AI doesn't remember something said many turns ago. Check `len(store.get(conversation_id))` to verify trimming.

### Pitfall 4: `conversation_id` as Empty String Treated as Valid Key
**What goes wrong:** When the user doesn't fill in the optional `conversation_id` field, Homey passes `""` (empty string) or `None`. If the code does `self._store.get(args.get("conversation_id"))`, all stateless calls share the `""` conversation bucket, mixing contexts from different Flows.
**Why it happens:** Python `dict` accepts `""` as a valid key.
**How to avoid:** Guard with `conversation_id = args.get("conversation_id", "").strip()` and then `if conversation_id:` before any store operation.
**Warning signs:** Unrelated Flow cards start "remembering" each other's context.

### Pitfall 5: System Prompt + Long History Exhausts Claude Context Window
**What goes wrong:** A 500-token system prompt + 20-turn history of verbose responses approaches Claude's context window. API returns 400 context length exceeded.
**Why it happens:** Token budget is shared between system prompt, history, and new user prompt.
**How to avoid:** Keep default `max_history_turns` conservative (10). Inform users via settings hint text that system prompts reduce available history capacity. For v1, handling the `context_length_exceeded` error gracefully (return error string) is sufficient; automatic adaptive truncation is v2.
**Warning signs:** `APIStatusError` with status 400 and `"context_length_exceeded"` in the message body.

### Pitfall 6: `homey.settings.unset()` is Async in Stub but Synchronous in Practice
**What goes wrong:** The `conftest.py` mock sets `homey.settings.unset = AsyncMock()`, suggesting it might be async. But the actual Homey settings API's `unset()` is synchronous (like `get()` and `set()`). Calling `await self._settings.unset(key)` will throw a `TypeError` at runtime on device.
**Why it happens:** The test mock is incorrectly set up as `AsyncMock`.
**How to avoid:** Call `self._settings.unset(key)` without `await`. Update `conftest.py` to use `MagicMock()` (not `AsyncMock`) for `unset`.
**Warning signs:** `TypeError: object NoneType can't be used in 'await' expression` in Homey logs when clearing a conversation.

> Note on conftest.py: The existing `conftest.py` has `homey.settings.unset = AsyncMock()` — this should be `MagicMock()` to match the synchronous Homey settings API. Fix this in Wave 0 setup.

---

## Code Examples

Verified patterns from official sources:

### Anthropic system prompt — top-level parameter (HIGH confidence)
```python
# Source: https://platform.claude.com/docs/en/api/messages
# Verified: "there is no 'system' role for input messages in the Messages API"
response = await self._client.messages.create(
    model=model,
    max_tokens=1024,
    system="You are a helpful smart home assistant.",  # top-level, NOT in messages
    messages=[
        {"role": "user", "content": "What is the temperature?"},
    ]
)
```

### Ollama system prompt — role in messages array (HIGH confidence)
```python
# Source: https://github.com/ollama/ollama-python (official library)
# Verified: messages array supports {"role": "system"} as first element
response = await self._client.chat(
    model=model,
    messages=[
        {"role": "system", "content": "You are a helpful smart home assistant."},
        {"role": "user", "content": "What is the temperature?"},
    ]
)
```

### ConversationStore trim logic
```python
# Turn-count-based sliding window
# 1 turn = 1 user message + 1 assistant message = 2 entries
max_messages = self._max_turns * 2   # e.g., 10 turns = 20 messages
if len(history) > max_messages:
    history = history[-max_messages:]  # keep last N, evict oldest
```

### Optional argument handling in run_listener
```python
# Homey passes "" or None for optional unfilled text args
conversation_id = (args.get("conversation_id") or "").strip()
system_prompt = (args.get("system_prompt") or "").strip()
```

### homey.settings key-per-session pattern
```python
# Key: "conv_<conversation_id>" e.g. "conv_morning-briefing"
# Value: list[dict] — JSON-serializable, homey.settings stores any JSON
self._settings.set(f"conv_{conversation_id}", history_list)
stored = self._settings.get(f"conv_{conversation_id}")  # returns list or None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single global context for all AI calls | Named conversation sessions keyed by string ID | Phase 2 | Multiple independent automations can maintain separate contexts |
| No system prompt support | Global setting + per-card override | Phase 2 | Users can personalise AI persona without editing each card |
| No memory clearing mechanism | `clear_conversation` Flow card | Phase 2 | Users can reset context from within a Flow |

**Not yet implemented (v2):**
- Persistent session TTL eviction (conversations expire after N hours of inactivity)
- Token-count-based trimming (more precise than turn-count)
- Adaptive context reduction when approaching context window limits

---

## Open Questions

1. **Does `homey.settings.set()` with a large list (50+ messages) cause noticeable latency?**
   - What we know: ManagerSettings stores JSON-serializable values; no documented size limit found
   - What's unclear: Whether large values (>10KB) cause Homey performance degradation
   - Recommendation: Default `max_turns=10` (typically <5KB of JSON) keeps this well within safe range. Don't block on this; fix if performance issues are observed.

2. **Can the `text` arg type in Flow cards accept multi-line system prompt text?**
   - What we know: No `textarea` type exists in Homey Flow card arguments; only `text` type is available for string input; no documented character limit found in official docs
   - What's unclear: Whether single-line `text` input is practical for multi-line system prompts
   - Recommendation: Use the `text` type for the per-card `system_prompt` arg. For long/complex prompts, guide users to the global system prompt setting in the settings page (HTML textarea). Per-card prompt is for short overrides.

3. **Is `homey.settings.unset()` synchronous or async?**
   - What we know: `get()` and `set()` are synchronous in official docs/SDK; existing conftest.py mocks `unset` as `AsyncMock` (suspicious)
   - What's unclear: Confirmation that `unset()` is synchronous
   - Recommendation: Treat as synchronous (call without `await`), consistent with `get()/set()`. Update conftest.py mock to `MagicMock()`. Verify at runtime during Wave 1.

---

## Validation Architecture

> `workflow.nyquist_validation` key is not present in `.planning/config.json` — skipping this section.

---

## Sources

### Primary (HIGH confidence)
- [Anthropic Messages API — system parameter](https://platform.claude.com/docs/en/api/messages) — Confirmed `system=` is top-level param; no `system` role in messages array
- [Homey Apps SDK — Flow Arguments](https://apps.developer.homey.app/the-basics/flow/arguments) — Confirmed no `textarea` type; `required: false` pattern; `text` type for string input
- [Homey Apps SDK — Persistent Storage](https://apps.developer.homey.app/the-basics/app/persistent-storage) — Confirmed JSON-serializable values, survives restarts
- [ollama-python GitHub (official)](https://github.com/ollama/ollama-python) — Confirmed `{"role":"system"}` in messages array for Ollama
- [ManagerSettings API](https://apps-sdk-v3.developer.homey.app/ManagerSettings.html) — `get()`, `set()`, `unset()`, `getKeys()` — all synchronous

### Secondary (MEDIUM confidence)
- [Homey Community — Holding Application State](https://community.homey.app/t/holding-application-state/45321) — Community confirmation that ManagerSettings stores complex JSON; no size limit mentioned empirically
- [WebSearch: Ollama Python SDK system prompt pattern 2025](https://github.com/ollama/ollama-python) — Multiple community sources confirm `role: system` in messages array; verified against official library examples

### Tertiary (LOW confidence)
- No LOW confidence findings used in this research

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing anthropic + ollama already installed; Python built-ins used
- Architecture: HIGH — directly derived from reading actual Phase 1 code; patterns extend existing `app.py` structure
- System prompt format: HIGH — verified against official Anthropic API docs + official ollama-python library
- Pitfalls: HIGH — derived from code inspection + official API docs; one (conftest AsyncMock) confirmed by reading actual test file

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable APIs; Anthropic/Ollama API formats are stable)
