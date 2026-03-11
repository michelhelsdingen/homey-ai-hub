---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-11T23:27:26.637Z"
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-11)

**Core value:** Users can leverage AI (Claude and Ollama) directly in Homey Flows without being locked into a single provider
**Current focus:** Phase 4 COMPLETE — App Store Polish (04-01 and 04-02 complete)

## Current Position

Phase: 4 of 4 (App Store Polish) — COMPLETE
Plan: 2 of 2 in current phase (Plan 04-02 COMPLETE)
Status: 04-02 complete — Flow card compliance, .gitignore security, locales, and error hardening delivered
Last activity: 2026-03-12 — Completed plan 04-02 (App Store Compliance Fixes)

Progress: [████████████████████] 100% (all phases complete)

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
| Phase 04-app-store-polish P01 | 5 | 2 tasks | 5 files |
| Phase 04-app-store-polish P02 | 2 | 2 tasks | 5 files |

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
- [Phase 04-app-store-polish]: version 1.0.0 — first public App Store release; brandColor #1a73e8; runtime python; platforms local; pythonVersion 3.14
- [Phase 04-app-store-polish]: PNG generation uses Python struct/zlib standard library only — no external dependencies needed for solid-color promo images
- [Phase 04-app-store-polish]: titleFormatted uses 'with [[model]]' syntax (no parentheses) per App Store guidelines
- [Phase 04-app-store-polish]: env.json gitignored to prevent API keys from being committed
- [Phase 04-app-store-polish]: list_models() failures return descriptive error response tokens instead of raising uncaught exceptions

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 RESOLVED]: Python autocomplete callback signature confirmed — model_autocomplete(query: str, **card_args) with card_args.get("args", {}).get("provider") pattern works
- [Phase 1 ACTIVE]: Homey CLI sharp module conflict blocks homey app run/build — must fix sharp before live Docker testing on Homey Pro
- [Phase 1 ACTIVE]: Homey CLI sharp module conflict blocks homey app run/build — must fix sharp before live Docker testing on Homey Pro
- [Phase 3 ACTIVE]: Image droptoken stream shape unconfirmed in Python SDK — primary pattern implemented with fallback diagnostics; validate on Homey Pro during integration testing

## Session Continuity

Last session: 2026-03-12
Stopped at: Completed 04-02-PLAN.md — App Store Compliance Fixes
Resume file: None
