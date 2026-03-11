---
phase: 01-core-ai-integration
verified: 2026-03-11T22:00:00Z
status: human_needed
score: 5/5 must-haves verified
re_verification: false
human_verification:
  - test: "Install app on Homey Pro and run ask_ai Flow card with a real prompt"
    expected: "Flow card returns a non-empty AI response token visible in Advanced Flow log"
    why_human: "homey app build/run blocked by sharp module conflict in Homey CLI — cannot verify end-to-end execution programmatically"
  - test: "Open settings page on Homey, enter a Claude API key, press Test Claude Connection"
    expected: "Status shows green pass/fail message from Claude API within 30s"
    why_human: "Settings page calls Homey.api() which requires Homey runtime — cannot simulate browser-Homey bridge programmatically"
  - test: "Open settings page, enter Ollama URL, press Test Ollama Connection while Ollama is running"
    expected: "Status shows green message listing installed models"
    why_human: "Requires live Ollama server and Homey runtime"
---

# Phase 1: Core AI Integration Verification Report

**Phase Goal:** Users can send a text prompt to Claude or Ollama from a Homey Flow and receive an AI response as a Flow token
**Verified:** 2026-03-11T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can configure Ollama host/port and Claude API key in settings and save them | VERIFIED | `settings/index.html` has `ollama_url`, `ollama_timeout`, `claude_api_key`, `claude_timeout` inputs; `saveAll()` calls `Homey.set()` for all five fields; `loadSettings()` reads them back on page open |
| 2 | User can run the ask_ai Flow action card with a prompt and receive a non-empty AI response token | VERIFIED (code path) / NEEDS HUMAN (runtime) | `ask_ai.json` declares `response` token of type `string`; `run_listener` in `app.py` returns `{"response": response}` from `provider.chat()`; end-to-end blocked by Homey CLI sharp conflict |
| 3 | User can select Claude or Ollama per card; model autocomplete works (Claude: 3 models; Ollama: live list) | VERIFIED | `ask_ai.json` has provider dropdown with `ollama`/`claude` values and model autocomplete arg; `model_autocomplete()` in `app.py` calls `provider.list_models()` filtered by query; Claude returns 3 static models; Ollama calls `AsyncClient.list()` |
| 4 | User can trigger a connection test from settings and see a clear pass/fail result | VERIFIED | `settings/index.html` `testClaude()`/`testOllama()` call `Homey.api('POST', '/test-claude', {})` and `'/test-ollama'`; display `result.message` with `.ok`/`.fail` CSS class; `api.py` endpoints return `{"success": bool, "message": str}` |
| 5 | When LLM call fails, Flow card returns descriptive error token instead of silently failing | VERIFIED | All `chat()` error paths in `ClaudeProvider` and `OllamaProvider` return strings starting with `"Error:"`; `run_listener` returns `{"response": response}` unconditionally; provider-not-found and no-model cases also return error strings |

**Score:** 5/5 truths verified in code

### Required Artifacts

| Artifact | Provides | Status | Details |
|----------|----------|--------|---------|
| `lib/providers/base.py` | LLMProvider ABC with chat/list_models/test_connection | VERIFIED | 52 lines; abstract methods with full docstrings; no Homey SDK import |
| `lib/providers/claude.py` | Concrete Claude LLM provider | VERIFIED | 79 lines; AsyncAnthropic, max_retries=0, httpx timeout; 4 error cases handled |
| `lib/providers/ollama_provider.py` | Concrete Ollama LLM provider | VERIFIED | 72 lines; ollama.AsyncClient, 120s timeout; 3 error cases; graceful list_models |
| `app.py` | Flow card wiring + provider registry | VERIFIED | 128 lines; `_get_provider()` re-reads settings on every call; `run_listener` returns response token; `model_autocomplete` registered; `homey_export = App` |
| `api.py` | POST /test-claude and POST /test-ollama | VERIFIED | 38 lines; both endpoints read fresh settings, instantiate provider, call `test_connection()`; return `{success, message}`; `homey_export = Api` |
| `.homeycompose/flow/actions/ask_ai.json` | Flow card declaration | VERIFIED | All required fields: `id`, `title`, `titleFormatted`, `args` (prompt text, provider dropdown, model autocomplete), `tokens` (response string) |
| `settings/index.html` | Settings UI with save and test | VERIFIED | All 5 settings fields present; `saveAll()` saves all; `testClaude()`/`testOllama()` save current values before calling API; status feedback with CSS classes |
| `.homeycompose/app.json` | App manifest | VERIFIED | App ID `com.michelhelsdingen.homey-ai-hub`, sdk=3, `homey:manager:flow` permission present |
| `locales/en.json` | UI string keys | VERIFIED | 14 keys covering settings labels, hints, button labels, status strings |
| `tests/conftest.py` | Test fixtures | VERIFIED | `mock_homey` and `mock_action_card` fixtures present and substantive |
| `tests/test_claude_provider.py` | ClaudeProvider unit tests | VERIFIED | 6 tests covering chat success, rate limit error, connection error, list_models, test_connection success, test_connection 401 |
| `tests/test_ollama_provider.py` | OllamaProvider unit tests | VERIFIED | 7 tests covering chat success, ResponseError, ConnectionError, list_models, list_models error, test_connection success, test_connection unreachable |
| `requirements.txt` | Homey deployment dependencies | VERIFIED | `anthropic>=0.84.0`, `ollama>=0.6.1` |
| `pyproject.toml` | Test + lint config | VERIFIED | `asyncio_mode = "auto"`, ruff line-length=100, pyright basic |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py` | `ClaudeProvider` / `OllamaProvider` | Import + instantiation in `_get_provider()` | WIRED | Lines 5-6 import both; lines 48/55 instantiate with settings; line 68 `_get_provider()` called in `run_listener` |
| `app.py` | `ask_ai` Flow card | `homey.flow.get_action_card("ask_ai")` + `register_run_listener` | WIRED | Line 64 gets card; line 105 registers run listener; line 124 registers autocomplete listener |
| `run_listener` | AI response token | `return {"response": response}` | WIRED | Line 103 returns dict matching token name `response` declared in `ask_ai.json` |
| `settings/index.html` | `api.py /test-claude` | `Homey.api('POST', '/test-claude', {})` | WIRED | Line 110 in settings; api.py `post_test_claude` method naming matches convention |
| `settings/index.html` | `api.py /test-ollama` | `Homey.api('POST', '/test-ollama', {})` | WIRED | Line 130 in settings; api.py `post_test_ollama` method naming matches convention |
| `api.py` | `test_connection()` result | Returns `{"success": bool, "message": str}` | WIRED | Lines 23-24 and 32-33 call `test_connection()` and return result; settings page reads `result.success` and `result.message` |
| `_get_provider()` | Settings re-read on every call | `self.homey.settings.get()` called at top of `_get_provider()` | WIRED | Lines 44-59; provider rebuilt unconditionally; `default_provider` fallback on line 59 satisfies PROV-04 |
| `ClaudeProvider.chat()` | Error contract | Returns `"Error: ..."` string, never raises | WIRED | All 4 except clauses in `claude.py` return error strings; same for `ollama_provider.py` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROV-01 | 01-02, 01-03 | User can configure Ollama connection via IP/port in settings | SATISFIED | `ollama_url` field in settings/index.html; `_get_provider()` reads it at line 44; passed to `OllamaProvider(host=...)` |
| PROV-02 | 01-02, 01-03 | User can configure Claude API key in settings | SATISFIED | `claude_api_key` password field in settings/index.html; `api.py` line 15 and `app.py` line 33 read it; passed to `ClaudeProvider(api_key=...)` |
| PROV-03 | 01-02, 01-03 | User can select a model per provider | SATISFIED | `model` autocomplete arg in `ask_ai.json`; `model_autocomplete()` routes to correct provider's `list_models()`; Claude returns 3 static models; Ollama returns live list |
| PROV-04 | 01-03 | User can set a default provider in settings | SATISFIED | `default_provider` select in settings/index.html; `_get_provider()` line 59 falls back to `self.homey.settings.get("default_provider") or "ollama"` |
| PROV-05 | 01-02, 01-03 | User can test connection to Ollama and Claude from settings | SATISFIED | Two test buttons in settings/index.html; `testClaude()`/`testOllama()` call `api.py` endpoints; result shown in status div |
| PROV-06 | 01-02, 01-03 | User can see dynamically fetched Ollama model list via autocomplete | SATISFIED | `OllamaProvider.list_models()` calls `AsyncClient.list()` live; `model_autocomplete()` in app.py returns live results; query filtering applied |
| FLOW-01 | 01-03 | User can send a text prompt via Flow action card and receive AI response as token | SATISFIED (code) / NEEDS HUMAN (runtime) | `ask_ai.json` declares response token; `run_listener` returns `{"response": ...}`; blocked on live test |
| CONF-01 | 01-02, 01-03 | User can configure timeout per provider | SATISFIED | `ollama_timeout` and `claude_timeout` fields in settings; `_get_provider()` reads both at lines 45-46, 52-53; passed to provider constructors |

**All 8 Phase 1 requirements covered. No orphaned requirements.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO/FIXME/placeholder comments. No empty implementations. No `return null` / `return {}` stubs. No console.log-only handlers. Error contract ("Error:" prefix) consistently applied across both providers.

### Human Verification Required

#### 1. End-to-End Flow Card Execution

**Test:** Install app on Homey Pro (after resolving `homey app build` sharp conflict), create an Advanced Flow with the `ask_ai` action card, configure a provider and model, run the Flow with a prompt.
**Expected:** Flow execution completes and the `response` token contains a non-empty AI-generated string.
**Why human:** `homey app build` is blocked by the sharp module conflict in the local Homey CLI. All code paths are verified statically, but real execution requires the Homey runtime.

#### 2. Settings Save and Retrieve Round-Trip

**Test:** Open the settings page in the Homey app, fill in Ollama URL and Claude API key, click Save Settings, close and reopen settings.
**Expected:** Values persist — the fields are pre-filled with the saved values on reopen.
**Why human:** `Homey.get()` / `Homey.set()` require the Homey runtime bridge. The code is correct (`loadSettings()` runs on page open), but persistence requires the Homey storage backend.

#### 3. Connection Test Buttons

**Test:** From settings page, press "Test Ollama Connection" while Ollama is reachable, and "Test Claude Connection" with a valid API key.
**Expected:** Green status message appears with model count (Ollama) or "Claude connection OK" (Claude) within the configured timeout.
**Why human:** Requires live network, Homey runtime, and real provider credentials.

### Gaps Summary

No code gaps found. All five success criteria from the ROADMAP.md are satisfied at the implementation level:

1. Settings page has all required fields with correct `Homey.get/set` wiring.
2. `run_listener` returns a `{"response": ...}` token; all error paths return descriptive strings.
3. Provider dropdown and live model autocomplete are declared in `ask_ai.json` and wired in `app.py`.
4. Connection test buttons call `api.py` endpoints which call `test_connection()` and display results.
5. All `chat()` error paths return `"Error: ..."` strings — no silent failures.

The only outstanding item is the live end-to-end test which is blocked by the Homey CLI `sharp` module conflict on the local machine. This is a tooling environment issue, not a code defect. The INTEGRATION_TEST_NOTES.md documents the steps to complete testing once the CLI is fixed.

---

_Verified: 2026-03-11T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
