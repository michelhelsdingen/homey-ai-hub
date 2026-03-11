---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: active
last_updated: "2026-03-11T22:35:31.000Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Users can leverage AI (Claude and Ollama) directly in Homey Flows without being locked into a single provider
**Current focus:** Phase 2 COMPLETE — Conversation Memory and System Prompts

## Current Position

Phase: 2 of 4 (Conversation Memory and System Prompts) — COMPLETE
Plan: 2 of 2 in current phase (Plan 02-02 COMPLETE)
Status: Phase 2 complete — both 02-01 and 02-02 done
Last activity: 2026-03-11 — Completed plan 02-02 (Flow Card Wiring — Memory, System Prompts, and Clear Conversation)

Progress: [██████████] 100% (of planned phases 1-2)

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 5 min
- Total execution time: 25 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-core-ai-integration | 3 | 18 min | 6 min |
| 02-conversation-memory-and-system-prompts | 2 | 7 min | 3.5 min |

**Recent Trend:**
- Last 5 plans: 01-01 (5 min), 01-02 (5 min), 01-03 (8 min), 02-01 (3 min), 02-02 (4 min)
- Trend: Consistent ~4-5 min/plan

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
- [01-03]: Provider registry rebuilt on each _get_provider() call — Python ManagerSettings has no .on() event, stale settings prevention requires re-reading on every invocation
- [01-03]: model_autocomplete returns ArgumentAutocompleteResult dicts (name/description/data) — not plain strings; required by Homey SDK autocomplete contract
- [01-03]: run_listener extracts model from dict or string — handles both autocomplete dict and plain string inputs robustly
- [Phase 02]: ConversationStore uses settings injection pattern (no Homey SDK import) — pure-Python testable
- [Phase 02]: Claude system_prompt as top-level system= kwarg (Anthropic rejects role=system in messages array with HTTP 400)
- [Phase 02]: conftest.py fixed: settings.set/unset use MagicMock not AsyncMock — Homey ManagerSettings API is synchronous
- [02-02]: Backward compat preserved: empty conversation_id skips store entirely, single-turn behavior unchanged
- [02-02]: System prompt precedence enforced in run_listener: per-card > global_system_prompt setting > None
- [02-02]: Messages persisted only on success: response.startswith('Error:') check prevents storing failed turns

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 RESOLVED]: Python autocomplete callback signature confirmed — model_autocomplete(query: str, **card_args) with card_args.get("args", {}).get("provider") pattern works
- [Phase 1 ACTIVE]: Homey CLI sharp module conflict blocks homey app run/build — must fix sharp before live Docker testing on Homey Pro
- [Phase 3]: Image droptoken handling in Python SDK not confirmed — documented in JS SDK context only; validate during Phase 3 planning

## Session Continuity

Last session: 2026-03-11
Stopped at: Completed 02-02-PLAN.md — Flow Card Wiring: Memory, System Prompts, and Clear Conversation
Resume file: None
