---
phase: 03-vision-support
plan: 01
subsystem: api
tags: [vision, anthropic, ollama, base64, flow-card, python, pytest]

# Dependency graph
requires:
  - phase: 02-conversation-memory-and-system-prompts
    provides: app.py _register_flow_cards() pattern, _get_provider() helper, model_autocomplete listener
provides:
  - LLMProvider ABC with chat_with_image() abstract method
  - ClaudeProvider.chat_with_image() with base64 content blocks, 5MB guard, and media_type normalisation
  - OllamaProvider.chat_with_image() with VISION_MODELS prefix guard and images=[bytes] message field
  - ask_ai_with_image Flow action card JSON with droptoken: ["image"]
  - app.py image_run_listener wired to ask_ai_with_image card
affects: [04-settings-ui, testing, integration-tests]

# Tech tracking
tech-stack:
  added: [base64 (stdlib)]
  patterns: [chat_with_image() follows same error-return convention (str starting with "Error:") as chat(); VISION_MODELS set with prefix-match guard for Ollama; base64 content block list pattern for Anthropic vision API; droptoken guard (nullable check before stream read)]

key-files:
  created:
    - .homeycompose/flow/actions/ask_ai_with_image.json
  modified:
    - lib/providers/base.py
    - lib/providers/claude.py
    - lib/providers/ollama_provider.py
    - tests/test_claude_provider.py
    - tests/test_ollama_provider.py
    - app.py

key-decisions:
  - "All Claude models in MODELS list support vision — no model guard needed for ClaudeProvider"
  - "OllamaProvider uses prefix-match against VISION_MODELS set (e.g. 'llava:13b'.startswith('llava')) — covers tagged variants"
  - "Ollama AsyncClient receives image_bytes directly as images=[bytes] — client handles base64 encoding internally"
  - "Droptoken stream shape is MEDIUM confidence per research (JS SDK context only) — primary pattern implemented with fallback AttributeError handler and self.log() for diagnostics"
  - "image/jpg normalised to image/jpeg in both ClaudeProvider and image_run_listener — Anthropic API rejects image/jpg"

patterns-established:
  - "Vision guard pattern: check model prefix against set before attempting API call, return Error: string on unsupported model"
  - "Droptoken null guard: check args.get('droptoken') is None before stream read, return Error: string"
  - "image_run_listener reuses model_autocomplete — vision and text cards share provider/model selection logic"

requirements-completed: [FLOW-02]

# Metrics
duration: 12min
completed: 2026-03-12
---

# Phase 3 Plan 01: Vision Support — Provider Layer and Flow Card Summary

**chat_with_image() added to LLMProvider ABC, ClaudeProvider (base64 content blocks + 5MB guard), OllamaProvider (VISION_MODELS prefix guard), and wired to new ask_ai_with_image Flow action card with image droptoken**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-12T00:00:00Z
- **Completed:** 2026-03-12T00:12:00Z
- **Tasks:** 2
- **Files modified:** 6 + 1 created

## Accomplishments
- Extended LLMProvider ABC with chat_with_image() abstract method — all 3 concrete methods (chat, list_models, test_connection) unchanged
- ClaudeProvider.chat_with_image() encodes image to base64 content block, enforces 5MB limit, normalises image/jpg to image/jpeg, handles all Anthropic error types
- OllamaProvider.chat_with_image() guards against non-vision models via VISION_MODELS prefix set, passes image_bytes directly to Ollama AsyncClient which handles base64 internally
- New ask_ai_with_image Flow card with droptoken: ["image"], provider dropdown, model autocomplete, and response token
- app.py image_run_listener handles null droptoken, resolves provider/model, reads image stream with fallback diagnostics, calls provider.chat_with_image()
- 8 new test cases added (4 per provider) — all 41 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Provider layer — chat_with_image() ABC + ClaudeProvider + OllamaProvider + tests** - `818db5f` (feat)
2. **Task 2: Flow card JSON and app.py wiring for ask_ai_with_image** - `82c75f6` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `lib/providers/base.py` - Added chat_with_image() abstract method after chat()
- `lib/providers/claude.py` - Added base64 import and chat_with_image() with size/media_type guards
- `lib/providers/ollama_provider.py` - Added VISION_MODELS class set and chat_with_image() with prefix guard
- `tests/test_claude_provider.py` - Added TestClaudeProviderChatWithImage (4 tests)
- `tests/test_ollama_provider.py` - Added TestOllamaProviderChatWithImage (4 tests)
- `.homeycompose/flow/actions/ask_ai_with_image.json` - New Flow card with droptoken: ["image"]
- `app.py` - Added image_run_listener + image_card registrations after clear_card

## Decisions Made
- All Claude models (haiku, sonnet, opus 4-5) support vision — no guard needed; Ollama requires explicit VISION_MODELS set
- Ollama AsyncClient receives raw bytes in `images=[image_bytes]` — client auto-encodes; no manual base64 needed
- Droptoken stream read uses try/except with diagnostic self.log() — medium-confidence SDK shape handled gracefully
- image/jpg normalisation applied at both provider level (ClaudeProvider) and app.py level (belt-and-suspenders)
- model_autocomplete reused on image_card — same provider/model logic works for both text and vision cards

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None — all tests passed on first run.

## User Setup Required
None - no external service configuration required. Live droptoken behaviour requires Homey Pro for integration testing (documented as Phase 3 blocker in STATE.md).

## Next Phase Readiness
- Provider layer and Flow card are ready
- Unit test coverage: 41 tests passing
- Live integration on Homey Pro still required — droptoken stream shape unconfirmed (MEDIUM confidence, per RESEARCH.md Pitfall 5); fallback diagnostics are in place
- Phase 3 remaining plans can proceed with settings UI and integration testing

---
*Phase: 03-vision-support*
*Completed: 2026-03-12*
