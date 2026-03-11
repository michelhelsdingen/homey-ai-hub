---
phase: 01-core-ai-integration
plan: "02"
subsystem: providers
tags: [python, anthropic, ollama, async, pytest, llm-providers, httpx]

# Dependency graph
requires:
  - phase: 01-core-ai-integration
    plan: "01"
    provides: LLMProvider ABC at lib/providers/base.py with chat/list_models/test_connection abstract methods
provides:
  - ClaudeProvider at lib/providers/claude.py — concrete LLMProvider for Anthropic Claude API
  - OllamaProvider at lib/providers/ollama_provider.py — concrete LLMProvider for local Ollama server
  - Unit tests at tests/test_claude_provider.py and tests/test_ollama_provider.py
  - requirements.txt declaring anthropic>=0.84.0 and ollama>=0.6.1
affects:
  - 01-03-app-wiring (imports ClaudeProvider and OllamaProvider directly)
  - Any phase using AI chat or model listing

# Tech tracking
tech-stack:
  added:
    - anthropic 0.84.0 (AsyncAnthropic client)
    - ollama 0.6.1 (AsyncClient)
    - httpx 0.28.1 (async HTTP for Claude timeout control)
  patterns:
    - AsyncAnthropic with max_retries=0 for fast-fail in Flow context
    - ollama.AsyncClient (file named ollama_provider.py to avoid shadowing)
    - All errors returned as "Error: ..." strings — never raised to caller
    - requirements.txt for Homey Python app dependency declaration

key-files:
  created:
    - lib/providers/claude.py
    - lib/providers/ollama_provider.py
    - tests/test_claude_provider.py
    - tests/test_ollama_provider.py
    - requirements.txt
  modified: []

key-decisions:
  - "ClaudeProvider uses AsyncAnthropic with max_retries=0 — prevents 10-20s hang on Claude API errors in Homey Flow context"
  - "OllamaProvider file named ollama_provider.py (not ollama.py) — naming it ollama.py would shadow the ollama library"
  - "OllamaProvider default timeout 120s — cold model loading can take 300s for large models; 120s is a reasonable default"
  - "Homey CLI dependency install broken (sharp module conflict) — using requirements.txt as workaround for deployment"
  - "pip install via --break-system-packages for Homebrew python3.13 — required to install test dependencies locally"

patterns-established:
  - "Error pattern: All provider errors return 'Error: ...' strings; never raise exceptions to callers"
  - "Async pattern: AsyncAnthropic and ollama.AsyncClient — synchronous clients block Homey's event loop"
  - "File naming: Provider files use descriptive names (ollama_provider.py) to avoid shadowing installed libraries"
  - "Testing: All HTTP calls mocked via unittest.mock.AsyncMock — no real API keys needed for tests"

requirements-completed: [PROV-01, PROV-02, PROV-03, PROV-05, PROV-06, CONF-01]

# Metrics
duration: 5min
completed: 2026-03-11
---

# Phase 1 Plan 02: Ollama and Claude Provider Implementations with Unit Tests Summary

**AsyncAnthropic and ollama.AsyncClient concrete providers with 13 passing unit tests, max_retries=0 fast-fail, and "Error:" error contract**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-11T21:31:12Z
- **Completed:** 2026-03-11T21:36:33Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- ClaudeProvider implementing LLMProvider with AsyncAnthropic, httpx timeout, max_retries=0 fast-fail
- OllamaProvider implementing LLMProvider with ollama.AsyncClient, 120s default timeout, graceful degradation
- 13 unit tests (6 Claude, 7 Ollama) — all passing, all HTTP calls mocked
- requirements.txt created for Homey deployment (anthropic + ollama)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install provider dependencies and implement ClaudeProvider** - `15ae107` (feat)
2. **Task 2: Implement OllamaProvider** - `f14db90` (feat)
3. **Task 3: Write and run unit tests for both providers** - `0659dff` (test)

## Files Created/Modified

- `lib/providers/claude.py` — ClaudeProvider: AsyncAnthropic, max_retries=0, 30s timeout, 3 Claude models
- `lib/providers/ollama_provider.py` — OllamaProvider: ollama.AsyncClient, 120s timeout, graceful list_models
- `tests/test_claude_provider.py` — 6 unit tests covering chat, list_models, test_connection
- `tests/test_ollama_provider.py` — 7 unit tests covering chat, list_models, test_connection
- `requirements.txt` — Homey deployment dependency declarations (anthropic>=0.84.0, ollama>=0.6.1)

## Decisions Made

- `max_retries=0` on AsyncAnthropic — without this, the Anthropic SDK retries 429/503 errors for 10-20s which blocks Homey Flows
- File named `ollama_provider.py` not `ollama.py` — a file named `ollama.py` would shadow the installed `ollama` library causing import failure
- OllamaProvider default timeout 120s — 30s default would fail on cold model loading; 120s balances responsiveness and reliability
- Used `requirements.txt` instead of `homey app dependency install` — Homey CLI is broken locally (sharp module conflict documented in 01-01)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Created requirements.txt for Homey deployment**
- **Found during:** Task 1 (installing dependencies)
- **Issue:** Plan specifies `homey app dependency install` but Homey CLI is broken (sharp module conflict from 01-01). No mechanism existed to declare Python dependencies for Homey deployment.
- **Fix:** Created `requirements.txt` with `anthropic>=0.84.0` and `ollama>=0.6.1` — standard Homey Python app dependency mechanism
- **Files modified:** requirements.txt (created)
- **Verification:** File exists with correct entries
- **Committed in:** `15ae107` (Task 1 commit)

**2. [Rule 3 - Blocking] Used --break-system-packages for python3.13 pip install**
- **Found during:** Task 1 (local test environment setup)
- **Issue:** Homebrew Python 3.13 blocks pip installs without explicit override. Both `pip3.13 install` and `pip3.13 install --user` failed with PEP 668 error.
- **Fix:** Used `python3.13 -m pip install anthropic ollama --break-system-packages` — acceptable for local dev tooling
- **Files modified:** None (local environment only)
- **Verification:** `python3.13 -c "import anthropic; import ollama"` succeeds
- **Committed in:** N/A (environment setup only)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 blocking)
**Impact on plan:** Both auto-fixes necessary for correct operation. The requirements.txt is essential for deployment. No scope creep.

## Issues Encountered

None beyond the known Homey CLI sharp module conflict (documented in 01-01 and again here).

## User Setup Required

None — no external service configuration required for this plan. Provider credentials are handled in 01-03 (app wiring).

## Next Phase Readiness

- Both provider implementations complete and unit-tested — ready for 01-03 (app wiring into Homey SDK)
- ClaudeProvider and OllamaProvider satisfy all interface requirements of LLMProvider ABC
- Error contract ("Error:" prefix) established and tested — 01-03 can rely on this
- Blocker from STATE.md (Python autocomplete callback signature) still unresolved — relevant for 01-03

---
*Phase: 01-core-ai-integration*
*Completed: 2026-03-11*

## Self-Check: PASSED

- FOUND: lib/providers/claude.py
- FOUND: lib/providers/ollama_provider.py
- FOUND: tests/test_claude_provider.py
- FOUND: tests/test_ollama_provider.py
- FOUND: requirements.txt
- FOUND commit: 15ae107 (ClaudeProvider)
- FOUND commit: f14db90 (OllamaProvider)
- FOUND commit: 0659dff (unit tests)
