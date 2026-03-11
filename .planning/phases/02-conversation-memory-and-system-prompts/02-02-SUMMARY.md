---
phase: 02-conversation-memory-and-system-prompts
plan: "02"
subsystem: api
tags: [homey, flow-cards, conversation, system-prompt, settings]

requires:
  - phase: 02-01
    provides: ConversationStore class, LLMProvider.chat(system_prompt=...) support

provides:
  - ask_ai flow card accepts optional conversation_id and system_prompt args
  - clear_conversation flow card for resetting named conversation sessions
  - settings/index.html with global_system_prompt textarea and max_history_turns input
  - app.py wired with ConversationStore, system prompt precedence, and history persistence

affects:
  - phase-03-image-support
  - phase-04-additional-providers

tech-stack:
  added: []
  patterns:
    - "System prompt precedence: per-card arg > global setting > None"
    - "Store-after-success: only persist messages when API call succeeds (no error prefix)"
    - "Conversation sessions opt-in: empty conversation_id = stateless single-turn"

key-files:
  created:
    - .homeycompose/flow/actions/clear_conversation.json
  modified:
    - .homeycompose/flow/actions/ask_ai.json
    - settings/index.html
    - app.py

key-decisions:
  - "Backward compat preserved: empty conversation_id skips store entirely, single-turn behavior unchanged"
  - "System prompt precedence enforced in run_listener: per-card > global_system_prompt setting > None"
  - "Messages persisted only on success: response.startswith('Error:') check prevents storing failed turns"

patterns-established:
  - "Optional flow card args use required=false in JSON schema"
  - "Conversation history retrieved via self._store.get(id) then list(history) + new user message"

requirements-completed:
  - FLOW-03
  - FLOW-04
  - FLOW-05
  - CONF-02
  - CONF-03

duration: 4min
completed: 2026-03-11
---

# Phase 02 Plan 02: Flow Card Wiring — Memory, System Prompts, and Clear Conversation Summary

**ask_ai flow card extended with optional conversation_id and system_prompt args, clear_conversation card added, settings page extended with global system prompt and max history turns, and app.py wired to ConversationStore with system prompt precedence logic**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-11T22:32:03Z
- **Completed:** 2026-03-11T22:35:31Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- ask_ai.json updated with optional `conversation_id` and `system_prompt` args preserving backward compatibility
- clear_conversation.json created with conversation_id arg and result string token
- settings/index.html extended with Conversation Settings section (textarea + number input) with load/save wired
- app.py fully wired: ConversationStore initialized on startup, system prompt precedence applied, history retrieved/persisted per call, clear_conversation card registered

## Task Commits

Each task was committed atomically:

1. **Task 1: Update ask_ai.json and create clear_conversation.json** - `b9af3da` (feat)
2. **Task 2: Extend settings/index.html with global_system_prompt and max_history_turns** - `c571700` (feat)
3. **Task 3: Wire ConversationStore and system prompt into app.py** - `551ac00` (feat)

**Plan metadata:** (docs: complete plan — added after state updates)

## Files Created/Modified

- `.homeycompose/flow/actions/ask_ai.json` - Added optional conversation_id and system_prompt args, updated titleFormatted
- `.homeycompose/flow/actions/clear_conversation.json` - New file: clear_conversation card with result token
- `settings/index.html` - Added Conversation Settings section with global_system_prompt textarea and max_history_turns number input
- `app.py` - Imported ConversationStore, wired on_init, extended ask_ai run_listener, registered clear_conversation card

## Decisions Made

- Backward compatibility maintained: empty `conversation_id` string skips store entirely — single-turn behavior is unchanged
- System prompt precedence applied in run_listener: per-card arg takes priority over global setting; both fall back to None
- Messages stored only after successful API call: `response.startswith("Error:")` guard prevents persisting failed turns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Settings fields are UI-configurable in the Homey app settings page.

## Next Phase Readiness

- All 5 requirements covered: FLOW-03, FLOW-04, FLOW-05, CONF-02, CONF-03
- Phase 2 fully complete — ConversationStore built (02-01) and wired (02-02)
- Ready for Phase 3 (image support) or Phase 4 (additional providers)
- Existing blocker still applies: Homey CLI sharp module conflict blocks live Docker testing on Homey Pro

---
*Phase: 02-conversation-memory-and-system-prompts*
*Completed: 2026-03-11*

## Self-Check: PASSED

All created/modified files verified:
- FOUND: `.homeycompose/flow/actions/ask_ai.json`
- FOUND: `.homeycompose/flow/actions/clear_conversation.json`
- FOUND: `settings/index.html`
- FOUND: `app.py`
- FOUND: `.planning/phases/02-conversation-memory-and-system-prompts/02-02-SUMMARY.md`

All commits verified:
- FOUND: `b9af3da` - feat(02-02): ask_ai.json and clear_conversation.json
- FOUND: `c571700` - feat(02-02): settings/index.html conversation settings
- FOUND: `551ac00` - feat(02-02): app.py ConversationStore wiring
