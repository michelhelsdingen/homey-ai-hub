# Domain Pitfalls: Homey AI Hub

**Domain:** Homey Python app + multi-provider LLM integration
**Researched:** 2026-03-11
**Scope:** Homey Python SDK, Ollama HTTP API, Anthropic Claude API, Flow card architecture, conversation memory

---

## Critical Pitfalls

Mistakes that cause rewrites, app store rejections, or fundamental breakage.

---

### Pitfall 1: Flow Action Cards That Return Before LLM Responds

**What goes wrong:** An action card that fires an LLM request (Ollama or Claude) resolves its promise immediately — before the response arrives — so the next Flow card runs with an empty or undefined token value.

**Why it happens:** Developers misunderstand that `registerRunListener` must return a promise that only resolves when the work is finished. If the async chain is broken (e.g., forgetting `await`, mixing sync code into async flow), the card completes with no data.

**Consequences:** Users get blank AI response tokens in subsequent Flow cards. Silent failure — no error, just empty values. Extremely confusing to debug without access to Homey logs.

**Prevention:**
- Always `await` the full LLM response chain inside the run listener
- Return the response object (e.g., `{ response: "..." }`) only after the HTTP call completes
- For Ollama streaming mode, collect the full streamed response before resolving
- Test with actual slow model calls (70B on CPU is a good stress test)

**Detection:** Flow cards downstream receive empty or undefined tokens. Adding `this.log()` calls around the HTTP request will show whether the await is working.

**Phase:** Phase 1 (Flow card implementation)

---

### Pitfall 2: Ollama 5-Minute Model Unload Timeout Causing Apparent Failures

**What goes wrong:** Ollama unloads models from memory after 5 minutes of inactivity by default. The next request after idle triggers a cold reload — for llama3.1:70b this can take 30-120 seconds depending on hardware. If no timeout headroom is built in, the Homey app's HTTP call either times out or returns a misleading error.

**Why it happens:** Developers test with a warm model (just used it), ship the app, then users fire it after an hour of inactivity and it "doesn't work."

**Consequences:** App appears broken. Users file issues. Developer cannot reproduce in development because the model is always warm during testing.

**Prevention:**
- Set a generous HTTP timeout for Ollama calls: minimum 120 seconds for 7B-13B models, 300 seconds for 30B+ models
- Expose timeout as a configurable setting in the app settings UI
- Implement a "keep-alive" ping mechanism or document the cold-start behavior to users
- Test explicitly with a cold Ollama server before shipping

**Detection:** Request succeeds with warm model, times out or errors with cold. If Ollama logs show "loading model..." this is the cause.

**Phase:** Phase 1 (Ollama provider integration)

---

### Pitfall 3: API Keys Stored in env.json Published to App Store

**What goes wrong:** Developers put their own Anthropic API key in `env.json` for testing, forget to remove it, and publish. The `env.json` file is bundled and sent to the Homey App Store infrastructure when an app is submitted.

**Why it happens:** `env.json` is a convenient development shortcut. The line between "my dev credentials" and "the app's credentials" blurs when iterating quickly.

**Consequences:** API key exposure. Potential billing liability. Possible immediate revocation by Anthropic.

**Prevention:**
- Never put the user's own API key in `env.json` — env.json is for developer OAuth client IDs/secrets, not user credentials
- User-supplied API keys (Claude API key, Ollama host URL) must go through `ManagerSettings` (Settings UI → stored in Homey's settings store)
- Add `env.json` to `.gitignore` immediately. Keep it empty or with only non-sensitive placeholder values
- Validate at submission: ensure env.json contains nothing sensitive

**Detection:** Run `cat /path/to/app/env.json` before any publish. If it has a real API key, strip it.

**Phase:** Phase 1 (project setup, settings implementation)

---

### Pitfall 4: Conversation History Growing Unboundedly Until Context Window Exhaustion

**What goes wrong:** Each exchange appends to the stored conversation array. After 20-50 turns (depending on model and verbosity), the total token count exceeds the model's context window. The API returns a 400 error (Claude: `context_length_exceeded`; Ollama: model-specific error). The app crashes or silently returns nothing.

**Why it happens:** Simple list-append conversation management works in demos. Nobody tests 50+ message conversations. Token counting is invisible until it breaks.

**Consequences:** Claude API: 400 error with clear message but app must handle it. Ollama: behavior varies by model — some truncate silently, some error, some hallucinate. If not handled, the entire conversation feature becomes unreliable at scale.

**Prevention:**
- Implement a sliding window: keep last N messages (configurable, default 10-20 exchanges)
- Add a `max_history_messages` setting with a sane default
- Before each API call, calculate approximate token count and trim if over 80% of model's context limit
- Provide a "clear conversation" action card so users can reset context manually
- For Claude specifically: track the input token count from API responses

**Detection:** Error appears after many conversation turns. Check response objects for `usage.input_tokens` approaching model limits.

**Phase:** Phase 2 (conversation memory implementation)

---

### Pitfall 5: Homey App Memory Leak From Unbounded In-Memory Conversation Storage

**What goes wrong:** Conversation histories for all Flow executions are stored in-memory in a Python dict keyed by conversation ID. Homey Pro 2023 has ~2GB RAM total, with ~300MB available for apps after system usage. Apps causing memory pressure trigger system-wide slowdowns and force Homey to kill processes.

**Why it happens:** It's natural to cache conversations in a dict. With dozens of Flows each maintaining conversation context, the in-memory footprint grows continuously.

**Consequences:** Homey reports "Memory full" errors. Other apps are affected. Homey may auto-restart apps or reboot. Users lose conversation context on restart anyway.

**Prevention:**
- Cap conversation history entries (trim by length, not just token count)
- Implement TTL-based eviction: clear conversations not used for 24h
- Store conversation history in `ManagerSettings` (persisted JSON) rather than pure in-memory, so it survives restarts AND allows periodic cleanup
- Be conservative with memory: measure app heap usage during testing

**Detection:** Gradually growing memory usage in Homey's system stats (sysInternals app). Flows that were fast become slow over days.

**Phase:** Phase 2 (conversation memory architecture)

---

### Pitfall 6: Blocking the Python Async Event Loop With Synchronous HTTP Calls

**What goes wrong:** Python's asyncio is cooperative. A synchronous HTTP call (e.g., `requests.get()`) inside an `async def` function freezes the entire event loop. Every other pending operation in the Homey app stalls until the LLM call completes. With a 70B model taking 60+ seconds, this is catastrophic.

**Why it happens:** `requests` is the most familiar Python HTTP library. Developers write `requests.post(ollama_url, ...)` inside an async function without realizing it blocks.

**Consequences:** During an LLM call, no other app operations can run. Settings can't be read. Other Flow cards queue up and time out. The app effectively freezes.

**Prevention:**
- Use `httpx` (async-native) or `aiohttp` for ALL HTTP calls, including Ollama
- For the Anthropic SDK, use `AsyncAnthropic`, not `Anthropic`
- Never use `requests`, `urllib`, or any sync HTTP client in the Homey app code
- Structure all LLM calls as `async def` with `await` throughout

**Detection:** App seems unresponsive during LLM calls. Multiple Flow executions back up. Profiling would show the event loop blocked on a sync call.

**Phase:** Phase 1 (provider client implementations)

---

## Moderate Pitfalls

Mistakes that cause significant user friction or require rework but don't break the system entirely.

---

### Pitfall 7: Not Handling Ollama Service Unavailability Gracefully

**What goes wrong:** The Ollama server at 192.168.2.214:11434 is on a local Mac Mini. It can be offline (machine asleep, network issue, Ollama process crashed). The app makes an HTTP call to an unavailable host and either hangs until timeout or throws an unhandled exception that kills the Flow without a useful error message.

**Prevention:**
- Wrap all Ollama HTTP calls in try/except with specific handling for `ConnectionError`, `TimeoutError`
- Return a user-friendly error string as the response token rather than crashing: `"Ollama unavailable: could not connect to 192.168.2.214:11434"`
- Add a connection test action card: "Test Ollama connection" that users can fire manually
- Implement configurable host URL so users can point to any Ollama instance, not just the default

**Phase:** Phase 1 (Ollama provider + error handling)

---

### Pitfall 8: Claude API Rate Limit Errors Not Surfaced Usefully in Flows

**What goes wrong:** Anthropic returns 429 (rate limit) or 529 (overloaded) errors. Without proper handling, the Flow action card rejects its promise with a raw HTTP error, which Homey displays as a generic "Flow failed" notification with no actionable detail.

**Prevention:**
- Catch `anthropic.RateLimitError` and `anthropic.APIStatusError` explicitly
- The Anthropic Python SDK auto-retries 429/503 errors (2 times by default with exponential backoff) — ensure this is enabled
- For 529 (overload), implement a user-visible fallback message rather than a silent failure
- Surface the error type in the response token: `{ response: null, error: "Claude rate limited, retry in 30s" }`

**Phase:** Phase 1 (Claude provider implementation)

---

### Pitfall 9: Homey App Initialization Fails Silently When Settings Are Missing

**What goes wrong:** `on_init()` tries to read an API key or Ollama host from settings. On first install, these settings don't exist yet. The app crashes or behaves unexpectedly because the code doesn't handle "not set" gracefully.

**Why it happens:** Developers write `api_key = self.homey.settings.get("claude_api_key")` and immediately use it without checking for `None`.

**Prevention:**
- Always check for `None`/empty values from settings at app init and at call time
- On missing required settings, set the app to a "not configured" state rather than crashing
- Provide clear error messaging: "Claude API key not set. Configure in app settings."
- Implement a `_check_configuration()` helper called at the start of every Flow action

**Phase:** Phase 1 (app initialization + settings architecture)

---

### Pitfall 10: Ollama Model List Populated Once at Init, Stales When User Adds Models

**What goes wrong:** The available models dropdown in Flow cards is populated from `GET /api/tags` at app startup. If the user installs a new Ollama model after the app starts, it won't appear in Homey until the app restarts.

**Prevention:**
- Use Homey's `autocomplete` argument type for the model selector, which queries models dynamically on Flow card open rather than at startup
- Implement the `autocomplete` callback to call `GET /api/tags` live each time the dropdown opens
- Cache the result for 30 seconds to avoid hammering Ollama on every keystroke

**Phase:** Phase 1 (Flow card model selection implementation)

---

### Pitfall 11: System Prompt Too Long Consumes Context Budget Before User Prompt

**What goes wrong:** Users configure a detailed global system prompt (e.g., 500+ tokens describing their smart home setup). With every message, this is prepended to the API call. The effective conversation history budget shrinks significantly, making the "memory" feature seem to forget context faster than expected.

**Prevention:**
- Recommend keeping system prompts under 200 tokens in the UI
- Calculate and display approximate token count of the system prompt in settings
- Apply system prompt compression warnings if prompt exceeds a threshold
- Document the tradeoff clearly: longer system prompt = shorter conversation memory

**Phase:** Phase 2 (system prompt + conversation memory)

---

### Pitfall 12: userdata/ Folder Files Are Publicly Accessible Over Network

**What goes wrong:** Any binary data (e.g., images for vision features) stored in `/userdata/` is accessible at `https://<homey-ip>/app/com.yourapp.id/userdata/filename`. A predictable filename makes user data accessible to anyone on the local network.

**Prevention:**
- If storing images in userdata, always use UUID-based filenames (e.g., `uuid4().hex + ".jpg"`)
- Store the mapping (conversation-id → filename) in ManagerSettings
- Delete images from userdata after they've been processed by the vision API
- Prefer in-memory handling for vision: fetch the image, encode to base64, send to API, discard

**Phase:** Phase 3 (vision/image support, if implemented)

---

### Pitfall 13: app.json Manual Edits Overwritten by Build Process

**What goes wrong:** Developer edits `app.json` directly to add Flow cards or update permissions. Running `homey app build` regenerates `app.json` from `.homeycompose/` and silently overwrites all manual changes.

**Why it happens:** `app.json` looks like the canonical manifest. The `.homeycompose/` split structure is non-obvious.

**Prevention:**
- Never edit `app.json` directly — it is auto-generated
- All manifest changes go in `.homeycompose/app.json`, `.homeycompose/flow/` etc.
- Add a comment to `app.json` header: "AUTO-GENERATED — edit .homeycompose instead"
- If using version control, commit `.homeycompose/` not `app.json`

**Phase:** Phase 1 (project structure setup)

---

## Minor Pitfalls

Quality and polish issues that degrade user experience.

---

### Pitfall 14: Flow Card Titles That Fail App Store Review

**What goes wrong:** Flow card titles like "Send a prompt to the AI and get a response" are rejected for: being too long, containing parentheses, being grammatically phrased rather than imperative, or including the app name.

**Homey App Store rules (verified):**
- Titles must be short and clear
- No parentheses in titles
- No device names or app names in card titles
- Imperative phrasing preferred

**Prevention:**
- Draft all Flow card titles against the guideline checklist before coding
- Example good title: "Ask AI" — bad title: "Send a prompt to AI (Ollama/Claude)"

**Phase:** Phase 1 (Flow card design)

---

### Pitfall 15: Driver/Device Access From App.on_init() Fails With SDK Error

**What goes wrong:** Python Homey SDK SDK v3 restriction: you cannot access drivers from `App.on_init()`. Calling `self.homey.drivers.get_driver('my-driver')` during app initialization throws an exception.

**Prevention:**
- Initialize only shared state (API clients, settings readers) in `App.on_init()`
- Access driver-specific resources in `Driver.on_init()` and `Device.on_init()` via `self.homey.app`
- Pattern: create client objects in `App.on_init()`, store on `self`, access via `self.homey.app.ollama_client` from devices/drivers

**Phase:** Phase 1 (app architecture)

---

### Pitfall 16: Large LLM Responses Causing Flow Execution Slowdowns Visible to Users

**What goes wrong:** Ollama with llama3.1:70b generates 500-token responses at 8 tokens/sec — that's 60+ seconds. Homey Flows have no "loading" indicator for action cards. Users repeatedly trigger the Flow assuming it failed, creating duplicate requests queued against the same Ollama instance.

**Prevention:**
- Implement idempotency: track in-flight requests per conversation ID, return a "request already in progress" response for duplicates
- Consider adding a "max response tokens" setting with a default of 256 tokens (fast) vs 1024 tokens (detailed)
- Document response time expectations in the app description
- For the MVP: lean toward smaller/faster models (llama3.1:8b) as the default

**Phase:** Phase 1 (UX design for async responses)

---

### Pitfall 17: App Store Rejection for Missing or Wrong Translations

**What goes wrong:** App is built with English-only UI. When submitted to App Store, if the description, readme, or any string has partial Dutch/German/etc. translations (e.g., from copy-paste of a template), it gets rejected for translation inconsistency.

**Prevention:**
- For initial release: English-only throughout. Do not add partial translations.
- Homey App Store rule: if you translate to a language, translate everything consistently
- Keep `en` as the only locale in `.homeycompose/locales/` until explicitly adding full translations

**Phase:** Pre-submission (any phase)

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| Phase 1 | Ollama HTTP client | Sync `requests` library blocking event loop | Use `httpx` async client exclusively |
| Phase 1 | Claude API client | `Anthropic()` sync client blocks event loop | Use `AsyncAnthropic()` always |
| Phase 1 | Flow action card | Promise resolves before LLM responds | Await full HTTP response before returning token dict |
| Phase 1 | Ollama cold start | 120s+ timeout on first request after idle | Configure timeout >= 120s, test cold state |
| Phase 1 | Settings on first install | `None` value crashes on missing API key | Null-check all settings reads, fail gracefully |
| Phase 1 | Model selection dropdown | Static list stales when models are added | Use `autocomplete` callback to fetch live |
| Phase 1 | manifest | Manual `app.json` edits overwritten | Edit only `.homeycompose/` files |
| Phase 2 | Conversation memory | Unbounded history exhausts context window | Sliding window, default 20 messages max |
| Phase 2 | Memory storage | In-memory dict grows without bound | TTL eviction + persist to ManagerSettings |
| Phase 2 | System prompt | Long system prompt eats context budget | Warn users, recommend < 200 tokens |
| Phase 3 | Vision images | userdata files publicly accessible | UUID filenames, delete after API call |
| Pre-ship | App Store review | Flow card titles fail formatting guidelines | Short, imperative, no parentheses |
| Pre-ship | API key in env.json | Developer key published accidentally | Audit env.json before any submission |

---

## Sources

- [Homey Apps SDK — Persistent Storage](https://apps.developer.homey.app/the-basics/app/persistent-storage) — MEDIUM confidence (official docs)
- [Homey Apps SDK — Flow Cards](https://apps.developer.homey.app/the-basics/flow) — HIGH confidence (official docs)
- [Homey Apps SDK — App Lifecycle](https://apps.developer.homey.app/the-basics/app) — HIGH confidence (official docs)
- [Homey Apps SDK — Images](https://apps.developer.homey.app/advanced/images) — HIGH confidence (official docs)
- [Homey App Store Guidelines](https://apps.developer.homey.app/app-store/guidelines) — HIGH confidence (official docs)
- [Homey SDK v3 — App.on_init() Driver Access Restriction](https://apps.developer.homey.app/upgrade-guides/upgrading-to-sdk-v3) — HIGH confidence (official docs)
- [Homey Community: Secure API Key Storage](https://community.homey.app/t/how-to-securely-store-username-and-password-for-an-api-within-my-app/72180) — MEDIUM confidence (community)
- [Homey Community: Flow Execution Time Limits](https://community.homey.app/t/flow-execution-time-limit-persistent-delays/65690) — MEDIUM confidence (community)
- [Ollama FAQ — Model Unload Timeout](https://docs.ollama.com/faq) — HIGH confidence (official docs)
- [Ollama API Errors](https://docs.ollama.com/api/errors) — HIGH confidence (official docs)
- [Collabnix: Ollama Production Pitfalls](https://collabnix.com/ollama-api-integration-building-production-ready-llm-applications/) — LOW confidence (blog, verified against Ollama docs)
- [Anthropic Python SDK — Error Handling & Retry](https://deepwiki.com/anthropics/anthropic-sdk-python/4.5-request-lifecycle-and-error-handling) — MEDIUM confidence (third-party verified against official docs)
- [Anthropic API Errors](https://docs.anthropic.com/en/api/errors) — HIGH confidence (official docs)
- [Anthropic Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) — HIGH confidence (official docs)
- [LLM Context Window Degradation Research (CMU)](https://demiliani.com/2025/11/02/understanding-llm-performance-degradation-a-deep-dive-into-context-window-limits/) — MEDIUM confidence (research-backed blog)
- [Async LLM Blocking Event Loop](https://deepankarm.github.io/posts/detecting-event-loop-blocking-in-asyncio/) — MEDIUM confidence (technical blog)
- [Homey Pro 2023 Memory Constraints](https://community.homey.app/t/homey-pro-2023-memory-question/88599) — MEDIUM confidence (community empirical data)
