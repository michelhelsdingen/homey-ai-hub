---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: in_progress
last_updated: "2026-03-12T00:12:00Z"
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Users can leverage AI (Claude and Ollama) directly in Homey Flows without being locked into a single provider
**Current focus:** Phase 3 IN PROGRESS — Vision Support (03-01 complete)

## Current Position

Phase: 3 of 4 (Vision Support) — IN PROGRESS
Plan: 1 of 1+ in current phase (Plan 03-01 COMPLETE)
Status: 03-01 complete — provider layer and ask_ai_with_image Flow card delivered
Last activity: 2026-03-12 — Completed plan 03-01 (Provider Layer and Flow Card for Vision Support)

Progress: [██████████████░░░░░░] 70% (phases 1-2 complete + 03-01 complete)

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
| 03-vision-support | 1 | 12 min | 12 min |

**Recent Trend:**
- Last 6 plans: 01-01 (5 min), 01-02 (5 min), 01-03 (8 min), 02-01 (3 min), 02-02 (4 min), 03-01 (12 min)
- Trend: Consistent ~5-6 min/plan (03-01 slightly longer due to 8 new tests + 2 new provider methods)

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
- [03-01]: All Claude models (haiku/sonnet/opus 4-5) support vision — no guard needed for ClaudeProvider.chat_with_image()
- [03-01]: OllamaProvider uses VISION_MODELS prefix-match set — covers tagged variants (e.g. "llava:13b" starts with "llava")
- [03-01]: Ollama AsyncClient receives image_bytes directly as images=[bytes] — client handles base64 encoding internally
- [03-01]: Droptoken stream shape is MEDIUM confidence (JS SDK only) — fallback AttributeError handler + self.log() diagnostics in image_run_listener
- [03-01]: image/jpg normalised to image/jpeg in both ClaudeProvider and image_run_listener (belt-and-suspenders)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 RESOLVED]: Python autocomplete callback signature confirmed — model_autocomplete(query: str, **card_args) with card_args.get("args", {}).get("provider") pattern works
- [Phase 1 ACTIVE]: Homey CLI sharp module conflict blocks homey app run/build — must fix sharp before live Docker testing on Homey Pro
- [Phase 1 ACTIVE]: Homey CLI sharp module conflict blocks homey app run/build — must fix sharp before live Docker testing on Homey Pro
- [Phase 3 ACTIVE]: Image droptoken stream shape unconfirmed in Python SDK — primary pattern implemented with fallback diagnostics; validate on Homey Pro during integration testing

## Session Continuity

Last session: 2026-03-12
Stopped at: Completed 03-01-PLAN.md — Provider Layer and Flow Card for Vision Support
Resume file: None
