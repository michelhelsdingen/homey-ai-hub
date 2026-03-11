---
phase: 01-core-ai-integration
plan: "01"
subsystem: infra
tags: [python, homey, abc, pytest, pytest-asyncio, ruff, pyright, homey-stubs]

# Dependency graph
requires: []
provides:
  - LLMProvider ABC at lib/providers/base.py with chat/list_models/test_connection abstract methods
  - pytest infrastructure with asyncio_mode=auto in pyproject.toml
  - tests/conftest.py with mock_homey and mock_action_card fixtures
  - Minimal app.py scaffold with homey_export = App
  - .homeycompose/app.json manifest with app ID com.michelhelsdingen.homey-ai-hub
affects:
  - 01-02 (ClaudeProvider and OllamaProvider must implement LLMProvider ABC)
  - 01-03 (App wiring uses app.py scaffold and test fixtures)
  - all future phases (LLMProvider interface is the contract all providers implement)

# Tech tracking
tech-stack:
  added:
    - pytest + pytest-asyncio (asyncio_mode=auto)
    - pytest-mock
    - ruff (linter, line-length=100, py312 target)
    - pyright (typeCheckingMode=basic)
    - homey-stubs (Python 3.13+)
  patterns:
    - LLMProvider ABC pattern — providers are pure Python, no Homey SDK dependency
    - All provider methods are async for non-blocking HTTP in Homey event loop
    - Error return convention — chat() returns "Error: ..." string, never raises
    - test_connection() returns tuple[bool, str] for Flow card display

key-files:
  created:
    - lib/providers/base.py
    - tests/conftest.py
    - pyproject.toml
    - app.py
    - .homeycompose/app.json
    - locales/en.json
    - .gitignore
  modified: []

key-decisions:
  - "Used Python 3.13 for local dev tooling (homey-stubs requires >=3.13) while pyproject.toml targets >=3.12"
  - "homey app CLI broken (sharp module issue, no sudo access) — scaffolded manually and validated manifest as JSON"
  - "LLMProvider ABC has no Homey SDK import — providers are pure Python, unit-testable without Homey runtime"

patterns-established:
  - "Provider pattern: implement LLMProvider ABC, return 'Error: ...' strings from chat() instead of raising"
  - "Test pattern: use mock_homey fixture from conftest.py to avoid Homey SDK in unit tests"
  - "Async pattern: all provider methods are async — never use synchronous HTTP in Homey apps"

requirements-completed: []

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 1 Plan 01: Project Scaffold, Provider Abstraction, and Async Foundation Summary

**Homey Python app scaffold with LLMProvider ABC (chat/list_models/test_connection), pytest-asyncio test infrastructure, and mock_homey fixture — everything 01-02 needs to implement providers**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T21:22:39Z
- **Completed:** 2026-03-11T21:27:24Z
- **Tasks:** 3
- **Files modified:** 7 created, 0 modified

## Accomplishments
- LLMProvider ABC defines the contract all provider implementations must follow — pure Python, no Homey SDK, fully unit-testable
- pytest infrastructure configured with asyncio_mode=auto so tests can use async/await without decorators
- mock_homey fixture provides a complete Homey SDK mock (settings, flow cards) for provider and app tests
- Minimal App scaffold in app.py ready for wiring in plan 01-03

## Task Commits

Each task was committed atomically:

1. **Task 1: Initialize Homey app project structure** - `9df83ca` (chore)
2. **Task 2: Create LLMProvider ABC and test infrastructure** - `5935b77` (feat)
3. **Task 3: Verify build and run smoke test** - `df2fd7f` (chore)

**Plan metadata:** _(to be added by final commit)_

## Files Created/Modified
- `lib/providers/base.py` — LLMProvider ABC with async chat(), list_models(), test_connection()
- `tests/conftest.py` — mock_homey and mock_action_card fixtures
- `pyproject.toml` — pytest asyncio_mode=auto, ruff config (line-length=100, py312), pyright basic
- `app.py` — minimal App(homey_app.App) with on_init and homey_export = App
- `.homeycompose/app.json` — valid Homey manifest with app ID com.michelhelsdingen.homey-ai-hub
- `locales/en.json` — empty object placeholder
- `.gitignore` — Python pycache, build artifacts, Homey app.json excluded

## Decisions Made
- Used Python 3.13 for local dev tooling (homey-stubs requires >=3.13) — pyproject.toml still targets >=3.12 to match Homey platform
- Homey CLI (`homey app create`, `homey app build`) is broken locally (sharp module conflict, no sudo) — manual scaffold with JSON validation used as fallback per plan instructions
- LLMProvider ABC deliberately has no Homey SDK import — keeps providers testable without Homey runtime

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .gitignore for Python project**
- **Found during:** Task 3 (smoke test verification)
- **Issue:** Python project had no .gitignore — pycache directories were appearing as untracked files
- **Fix:** Created .gitignore with Python pycache, virtual env, test cache, Homey build artifacts
- **Files modified:** .gitignore
- **Verification:** `git status --short` shows no pycache files
- **Committed in:** df2fd7f (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical)
**Impact on plan:** .gitignore is essential for any Python project. No scope creep.

## Issues Encountered
- Homey CLI (`homey` command) crashes with `Error: Could not load the "sharp" module using the darwin-x64 runtime` — no sudo to fix. Worked around by creating scaffold manually and validating manifest as JSON, exactly as the plan's fallback instructions specified.
- `homey-stubs` requires Python >=3.13 but plan said Python 3.11 is fine for dev. Used pip3.13 with `--break-system-packages` flag for Homebrew Python.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- LLMProvider ABC is ready — 01-02 can implement ClaudeProvider and OllamaProvider immediately
- Test fixtures (mock_homey, mock_action_card) ready for provider unit tests
- pyproject.toml configured — `python3.13 -m pytest tests/ -v` is the test command
- Blocker from STATE.md: Python autocomplete callback signature for Homey Flow cards — still unresolved, relevant for 01-03

---
*Phase: 01-core-ai-integration*
*Completed: 2026-03-11*

## Self-Check: PASSED

All files verified present. All commits verified in git log.
- FOUND: lib/providers/base.py
- FOUND: tests/conftest.py
- FOUND: pyproject.toml
- FOUND: app.py
- FOUND: .homeycompose/app.json
- FOUND: 01-01-SUMMARY.md
- FOUND: 9df83ca (T1), 5935b77 (T2), df2fd7f (T3)
