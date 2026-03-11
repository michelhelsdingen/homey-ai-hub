---
phase: 02-conversation-memory-and-system-prompts
plan: "01"
subsystem: conversation
tags: [conversation-history, sliding-window, system-prompt, anthropic, ollama, testing]

# Dependency graph
requires:
  - phase: 01-core-ai-integration
    provides: LLMProvider ABC, ClaudeProvider, OllamaProvider — provider layer this extends
provides:
  - ConversationStore class at lib/conversation_store.py with full CRUD + sliding window
  - system_prompt parameter on LLMProvider.chat() ABC and all implementations
affects:
  - 02-02 (flow integration will wire ConversationStore + system_prompt into Flow run_listener)
  - 02-03 (any further memory/prompt features build on this store)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Settings injection: ConversationStore accepts settings=None constructor arg — no SDK import in store class"
    - "Provider system_prompt: Claude uses top-level system= kwarg; Ollama prepends role=system message"
    - "Sliding window: _trim() caps at max_turns * 2, evicts from the front (oldest first)"

key-files:
  created:
    - lib/conversation_store.py
    - tests/test_conversation_store.py
  modified:
    - lib/providers/base.py
    - lib/providers/claude.py
    - lib/providers/ollama_provider.py
    - tests/conftest.py

key-decisions:
  - "ConversationStore has no Homey SDK import — settings injected via constructor for pure-Python testability"
  - "Claude system_prompt passed as top-level system= kwarg, never in messages array (Anthropic rejects role=system in messages with HTTP 400)"
  - "Ollama system_prompt prepended as first message with role=system (Ollama spec)"
  - "conftest.py fixed: settings.set and settings.unset use MagicMock (synchronous), not AsyncMock — Homey ManagerSettings API is synchronous"

patterns-established:
  - "Settings injection pattern: pass settings object via constructor, guard with if self._settings before use"
  - "Provider kwargs pattern: build kwargs dict then unpack with **kwargs for optional parameters"

requirements-completed:
  - FLOW-04
  - CONF-03

# Metrics
duration: 3min
completed: 2026-03-11
---

# Phase 2 Plan 01: ConversationStore and Provider System Prompt Support Summary

**In-memory ConversationStore with sliding window eviction and per-provider system_prompt injection (Claude top-level kwarg, Ollama prepended message)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-11T22:24:44Z
- **Completed:** 2026-03-11T22:27:44Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ConversationStore class with get/append/clear/_trim/_persist methods and settings injection pattern
- 20 unit tests for ConversationStore covering all edge cases including sliding window eviction and persistence
- system_prompt parameter added to LLMProvider ABC and all three implementations (base, claude, ollama)
- Fixed conftest.py bug: settings.set and settings.unset now use MagicMock (not AsyncMock) — Homey ManagerSettings is synchronous

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/conversation_store.py** - `faae85d` (feat)
2. **Task 2: Extend provider ABC and implementations with system_prompt** - `cc35d35` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `lib/conversation_store.py` - ConversationStore class with sliding window eviction and optional settings persistence
- `tests/test_conversation_store.py` - 20 unit tests covering get/append/clear/_trim/_persist and edge cases
- `lib/providers/base.py` - LLMProvider ABC chat() signature extended with system_prompt parameter
- `lib/providers/claude.py` - ClaudeProvider passes system_prompt as top-level system= kwarg to Anthropic API
- `lib/providers/ollama_provider.py` - OllamaProvider prepends {"role":"system"} message when system_prompt is set
- `tests/conftest.py` - Fixed AsyncMock -> MagicMock for settings.set and settings.unset

## Decisions Made
- ConversationStore settings injection: no Homey SDK import in store — injected via constructor for pure-Python testability
- Claude system prompt: top-level `system=` kwarg (never in messages array — Anthropic rejects role=system in messages with HTTP 400)
- Ollama system prompt: prepended as `{"role":"system"}` first message per Ollama spec
- conftest.py mock fix applied — homey.settings.set and homey.settings.unset changed from AsyncMock to MagicMock

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None — all 33 tests pass after implementation. Baseline was 13 tests; 20 new tests added.

## Test Counts
- **test_conversation_store.py:** 20 tests (all passing)
- **Total test suite:** 33 tests (all passing)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ConversationStore is ready for Phase 2 plan 02 wiring into Flow run_listener
- All provider implementations accept system_prompt — ready for Flow card argument integration
- Full test suite at 33 tests with zero failures

## Self-Check: PASSED

- lib/conversation_store.py: FOUND
- tests/test_conversation_store.py: FOUND
- 02-01-SUMMARY.md: FOUND
- Commit faae85d: FOUND
- Commit cc35d35: FOUND

---
*Phase: 02-conversation-memory-and-system-prompts*
*Completed: 2026-03-11*
