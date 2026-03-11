---
phase: 02-conversation-memory-and-system-prompts
verified: 2026-03-11T23:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 2: Conversation Memory and System Prompts — Verification Report

**Phase Goal:** Users can have multi-turn AI conversations in Flows using named session IDs, with full system prompt control
**Verified:** 2026-03-11T23:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can pass the same conversation ID to ask_ai across multiple Flow executions and the AI remembers prior turns in that session | VERIFIED | `app.py:108-112` — when `conversation_id` is non-empty, `self._store.get(conversation_id)` retrieves history and prepends it to the message list; history is persisted after each successful call |
| 2 | User can run the clear_conversation Flow card to reset a named session, after which the next ask_ai call starts fresh | VERIFIED | `clear_conversation.json` exists with correct structure; `app.py:155-165` registers `clear_run_listener` that calls `self._store.clear(conversation_id)` |
| 3 | User can set a global system prompt in settings that applies to all AI calls unless overridden per card | VERIFIED | `settings/index.html:66-68` — `global_system_prompt` textarea in Conversation Settings section; `app.py:104` reads it; `saveAll()` at line 102 persists it |
| 4 | User can set a per-card system prompt in the ask_ai action card that overrides the global system prompt for that execution | VERIFIED | `ask_ai.json:39-44` — `system_prompt` arg with `required: false`; `app.py:103-105` — `effective_system = per_card_system or global_system or None` correctly enforces per-card > global > None precedence |
| 5 | Conversation history never exceeds the configured max length (sliding window evicts oldest turns) | VERIFIED | `lib/conversation_store.py:42-47` — `_trim()` caps at `max_turns * 2`, slices with `history[-max_messages:]`; `max_turns` sourced from settings at init (`app.py:14`); behavioral test confirmed |

**Score:** 5/5 truths verified

---

## Required Artifacts

### Plan 02-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `lib/conversation_store.py` | ConversationStore class with get/append/clear/_trim/_persist | VERIFIED | All 5 methods present, no SDK import, settings injected via constructor |
| `tests/test_conversation_store.py` | Unit tests for all store behavior | VERIFIED | 20 tests covering all edge cases |
| `lib/providers/base.py` | LLMProvider.chat() ABC with system_prompt param | VERIFIED | `system_prompt: str | None = None` at line 18, documented in docstring |
| `lib/providers/claude.py` | ClaudeProvider.chat() passes system_prompt as top-level system= kwarg | VERIFIED | Lines 43-44: `kwargs["system"] = system_prompt` (not in messages array) |
| `lib/providers/ollama_provider.py` | OllamaProvider.chat() prepends role=system message | VERIFIED | Lines 37-38: prepends `{"role": "system", "content": system_prompt}` + list(messages) |
| `tests/conftest.py` | settings.set and settings.unset use MagicMock (not AsyncMock) | VERIFIED | Lines 12-13: both use `MagicMock()` |

### Plan 02-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.homeycompose/flow/actions/ask_ai.json` | Optional conversation_id and system_prompt args | VERIFIED | Both args present with `required: false`, placed after model arg |
| `.homeycompose/flow/actions/clear_conversation.json` | New card with conversation_id arg and result token | VERIFIED | id=clear_conversation, has conversation_id arg, has result token |
| `settings/index.html` | global_system_prompt textarea and max_history_turns number input | VERIFIED | Both fields present in "Conversation Settings" section; both in loadSettings fields array; both saved in saveAll() |
| `app.py` | ConversationStore initialized on startup, wired in ask_ai, clear_conversation registered | VERIFIED | ConversationStore imported (line 7), initialized on_init (line 14-15), ask_ai run_listener fully wired (lines 99-130), clear_conversation registered (lines 155-165) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py on_init` | `ConversationStore` | `from lib.conversation_store import ConversationStore` | WIRED | Import at line 7, instantiated at line 15 with `settings=self.homey.settings, max_turns=...` |
| `ask_ai run_listener` | `ConversationStore.get()` | `self._store.get(conversation_id)` | WIRED | Line 109, guarded by `if conversation_id:` |
| `ask_ai run_listener` | `ConversationStore.append()` | `self._store.append(...)` after API call | WIRED | Lines 129-130, only executed when `conversation_id` non-empty AND response does not start with "Error:" |
| `ask_ai run_listener` | `provider.chat(system_prompt=...)` | `effective_system` passed as kwarg | WIRED | Line 121-125, `system_prompt=effective_system` |
| `clear_run_listener` | `ConversationStore.clear()` | `self._store.clear(conversation_id)` | WIRED | Line 161, guarded for empty conversation_id |
| `settings/index.html saveAll()` | `global_system_prompt` setting | `Homey.set('global_system_prompt', ...)` | WIRED | Line 102 |
| `settings/index.html saveAll()` | `max_history_turns` setting | `Homey.set('max_history_turns', parseInt(...) || 10)` | WIRED | Line 103 |
| `settings/index.html loadSettings()` | both new settings fields | fields array includes both keys | WIRED | Line 81 includes `'global_system_prompt'` and `'max_history_turns'` |

**Critical wiring verified:**
- Store-after-success guard: history only appended when `conversation_id` is non-empty AND `not response.startswith("Error:")` — matches plan requirement
- Empty conversation_id guard: `(args.get("conversation_id") or "").strip()` — stateless single-turn preserved when blank
- System prompt precedence: `per_card_system or global_system or None` — correct short-circuit evaluation

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FLOW-03 | 02-02 | User can set system prompt dynamically per flow via action card | SATISFIED | `ask_ai.json` has optional `system_prompt` arg; `app.py` applies per-card > global precedence |
| FLOW-04 | 02-01, 02-02 | User can use named conversation sessions for isolated multi-turn context | SATISFIED | `ConversationStore` class built; wired into ask_ai run_listener with session isolation |
| FLOW-05 | 02-02 | User can clear a conversation session via Flow action card | SATISFIED | `clear_conversation.json` created; `clear_run_listener` registered in `app.py` |
| CONF-02 | 02-02 | User can set a global system prompt in settings | SATISFIED | `global_system_prompt` textarea in settings; read and applied in app.py run_listener |
| CONF-03 | 02-01, 02-02 | User can configure max conversation history length (sliding window) | SATISFIED | `max_history_turns` in settings; read at startup (`app.py:14`); enforced by `ConversationStore._trim()` |

All 5 phase requirements satisfied. No orphaned requirements. REQUIREMENTS.md traceability table correctly marks all 5 as Complete for Phase 2.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/conftest.py` | 3 | `AsyncMock` imported but never used in any fixture | Info | No functional impact — unused import only |

No blockers or warnings found.

---

## Human Verification Required

### 1. Multi-turn memory in live Homey Flow

**Test:** Create a Homey Flow with two ask_ai cards using the same conversation_id (e.g. "test-session"). First card asks "My name is Alice." Second card asks "What is my name?" Trigger the Flow.
**Expected:** The second AI response references "Alice" — proving history is preserved across card executions in the same Flow run.
**Why human:** Requires live Homey Pro device with Homey Python SDK running; cannot verify inter-card state pass-through programmatically.

### 2. clear_conversation resets memory across Flow executions

**Test:** Run a Flow with ask_ai (conversation_id="test"), then run the clear_conversation card with the same ID, then run ask_ai again with the same ID and a follow-up question.
**Expected:** The second ask_ai response shows no memory of the first question — demonstrating the clear actually removed stored history.
**Why human:** Requires live Homey runtime to test cross-Flow-execution persistence.

### 3. Global system prompt visible in Settings UI

**Test:** Open Homey App > Homey AI Hub > Settings. Scroll to "Conversation Settings" section.
**Expected:** A textarea labeled "Global System Prompt" and a number input labeled "Max Conversation History (turns)" are visible, editable, and persist after saving.
**Why human:** Settings UI rendering requires browser-based Homey settings frame.

---

## Gaps Summary

No gaps found. All automated checks passed.

- `lib/conversation_store.py` exists and is fully implemented with all required methods
- All three providers have `system_prompt: str | None = None` in their `chat()` signatures
- Claude passes system_prompt as top-level `system=` kwarg (correct — Anthropic rejects role=system in messages array)
- Ollama prepends `{"role":"system"}` as first message (correct per Ollama spec)
- `ask_ai.json` has both optional args with `required: false`
- `clear_conversation.json` exists with correct structure and result token
- `settings/index.html` has both new fields wired into loadSettings and saveAll
- `app.py` initializes ConversationStore with settings injection and max_turns from settings
- Store-after-success guard prevents persisting failed turns
- Empty conversation_id guard preserves backward-compatible single-turn behavior
- Full test suite passes: 33 tests, 0 failures (20 new ConversationStore tests + 13 pre-existing)
- All 5 commits from plan execution are present in git history (faae85d, cc35d35, b9af3da, c571700, 551ac00)

---

_Verified: 2026-03-11T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
