---
phase: 04-app-store-polish
plan: 02
subsystem: api
tags: [homey, flow-cards, locales, gitignore, error-handling]

# Dependency graph
requires:
  - phase: 03-vision-support
    provides: ask_ai_with_image flow card and image_run_listener in app.py
provides:
  - App Store compliant titleFormatted strings for both flow cards (no parentheses)
  - env.json excluded from git via .gitignore
  - Complete locales/en.json with 18 keys including conversation settings
  - Hardened list_models() calls with try/except in run_listener and image_run_listener
affects: [app-store-submission, settings-ui, flow-card-display]

# Tech tracking
tech-stack:
  added: []
  patterns: [defensive try/except around external API calls that can fail on network errors]

key-files:
  created: []
  modified:
    - .homeycompose/flow/actions/ask_ai.json
    - .homeycompose/flow/actions/ask_ai_with_image.json
    - .gitignore
    - locales/en.json
    - app.py

key-decisions:
  - "titleFormatted uses 'with [[model]]' syntax (no parentheses) per App Store guidelines"
  - "env.json gitignored to prevent API keys and credentials from being committed"
  - "list_models() failures return descriptive error response tokens instead of raising uncaught exceptions"

patterns-established:
  - "External provider calls that may fail on network errors are always wrapped in try/except returning descriptive error responses"

requirements-completed: []

# Metrics
duration: 2min
completed: 2026-03-12
---

# Phase 4 Plan 2: App Store Polish — Compliance Fixes Summary

**App Store compliant flow card titles, secured .gitignore, complete locale file, and hardened list_models() error handling in both flow card listeners**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-11T23:24:09Z
- **Completed:** 2026-03-11T23:26:14Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Replaced parentheses-based model display with "with [[model]]" syntax in both flow card titleFormatted strings
- Added env.json to .gitignore preventing secrets from ever being accidentally committed
- Extended locales/en.json from 13 to 18 keys, adding global_system_prompt, max_history_turns, and conversation_settings entries
- Wrapped both list_models() call sites in app.py with try/except so Ollama connectivity errors return graceful error responses instead of crashing

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix flow card titleFormatted, add env.json to .gitignore, and complete locales/en.json** - `c9f5a22` (feat)
2. **Task 2: Harden list_models() calls in app.py with try/except** - `c2c7696` (fix)

## Files Created/Modified
- `.homeycompose/flow/actions/ask_ai.json` - titleFormatted changed from parentheses to "with [[model]]" syntax
- `.homeycompose/flow/actions/ask_ai_with_image.json` - titleFormatted changed from parentheses to "with [[model]] about image" syntax
- `.gitignore` - Added env.json exclusion with descriptive comment
- `locales/en.json` - Added 5 new keys: setting_global_system_prompt, setting_global_system_prompt_hint, setting_max_history_turns, setting_max_history_turns_hint, conversation_settings
- `app.py` - Both list_models() call sites wrapped in try/except in run_listener and image_run_listener

## Decisions Made
- titleFormatted uses "with [[model]]" syntax (no parentheses) per Homey App Store flow card guidelines
- env.json gitignored to prevent API keys (claude_api_key, ollama_url) from being accidentally committed
- list_models() failures return descriptive error response tokens ("Error: Could not fetch models for {name}: {e}") instead of raising uncaught exceptions — consistent with existing error response pattern in app.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All four App Store polish concerns addressed: flow card compliance, security, localization, first-run hardening
- Ready for App Store submission preparation or integration testing on Homey Pro

---
*Phase: 04-app-store-polish*
*Completed: 2026-03-12*

## Self-Check: PASSED

- FOUND: .homeycompose/flow/actions/ask_ai.json
- FOUND: .homeycompose/flow/actions/ask_ai_with_image.json
- FOUND: .gitignore
- FOUND: locales/en.json
- FOUND: app.py
- FOUND: .planning/phases/04-app-store-polish/04-02-SUMMARY.md
- FOUND: commit c9f5a22
- FOUND: commit c2c7696
