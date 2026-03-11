# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Users can leverage AI (Claude and Ollama) directly in Homey Flows without being locked into a single provider
**Current focus:** Phase 1 — Core AI Integration

## Current Position

Phase: 1 of 4 (Core AI Integration)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-03-11 — Completed plan 01-02 (ClaudeProvider + OllamaProvider + unit tests)

Progress: [██░░░░░░░░] 17%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 5 min
- Total execution time: 10 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-ai-integration | 2 | 10 min | 5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (5 min), 01-02 (5 min)
- Trend: Consistent 5 min/plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Init]: Python over Node.js — better async HTTP, native AI ecosystem
- [Init]: Claude + Ollama only for v1 — focused scope, no OpenAI/Gemini
- [Research]: Build order enforced by architecture — providers first (no Homey SDK dep, fully unit-testable), then app wiring (needs Docker + Homey Pro)
- [Research]: Use `AsyncAnthropic` and `ollama.AsyncClient` exclusively — synchronous HTTP blocks the entire Homey event loop
- [01-01]: Used Python 3.13 for local dev tooling (homey-stubs requires >=3.13); pyproject.toml targets >=3.12 for Homey platform compat
- [01-01]: Homey CLI broken locally (sharp module conflict) — scaffolded manually; JSON validation used for manifest verification
- [01-01]: LLMProvider ABC has no Homey SDK import — keeps providers pure Python and unit-testable without Homey runtime
- [01-02]: ClaudeProvider uses AsyncAnthropic with max_retries=0 — prevents 10-20s hang on Claude API errors in Homey Flow context
- [01-02]: OllamaProvider file named ollama_provider.py (not ollama.py) — naming it ollama.py would shadow the ollama library
- [01-02]: Homey CLI dependency install broken (sharp conflict) — using requirements.txt as workaround for Homey Python app dependencies

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Python autocomplete callback signature for Homey Flow cards not confirmed with running code example — resolve during Phase 1 planning (check Homey developer forum or SDK source)
- [Phase 3]: Image droptoken handling in Python SDK not confirmed — documented in JS SDK context only; validate during Phase 3 planning

## Session Continuity

Last session: 2026-03-11
Stopped at: Completed 01-02-PLAN.md — ClaudeProvider, OllamaProvider, and unit tests complete
Resume file: None
