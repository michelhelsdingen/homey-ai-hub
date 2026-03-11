# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Users can leverage AI (Claude and Ollama) directly in Homey Flows without being locked into a single provider
**Current focus:** Phase 1 — Core AI Integration

## Current Position

Phase: 1 of 4 (Core AI Integration)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2026-03-11 — Completed plan 01-01 (scaffold + LLMProvider ABC)

Progress: [█░░░░░░░░░] 8%

## Performance Metrics

**Velocity:**
- Total plans completed: 1
- Average duration: 5 min
- Total execution time: 5 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-ai-integration | 1 | 5 min | 5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (5 min)
- Trend: Baseline established

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Python autocomplete callback signature for Homey Flow cards not confirmed with running code example — resolve during Phase 1 planning (check Homey developer forum or SDK source)
- [Phase 3]: Image droptoken handling in Python SDK not confirmed — documented in JS SDK context only; validate during Phase 3 planning

## Session Continuity

Last session: 2026-03-11
Stopped at: Completed 01-01-PLAN.md — project scaffold, LLMProvider ABC, test infra complete
Resume file: None
