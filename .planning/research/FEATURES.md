# Feature Landscape

**Domain:** Homey AI/LLM integration app
**Researched:** 2026-03-11
**Scope:** Feature analysis of existing Homey AI apps — OpenAI (com.openai.ChatGPT), Gemini AI (com.dimapp.geminiai), Ollama (com.ollama by smarthomesven), AI Chat Control (nl.joonix.aichatcontrol), OpenRouter (be.titansofindustry.openrouter)

---

## Competitive Landscape Summary

| App | Provider | Conversation | Vision | Device Control | Model Select | System Prompt |
|-----|----------|-------------|--------|----------------|--------------|---------------|
| OpenAI | OpenAI only | Yes (clear history card) | No (DALL-E generation only) | No | Hard-coded | No |
| Gemini AI | Google only | Yes (2hr window) | Yes (camera snapshot) | Yes (via HomeyScript) | Flash/Pro/Gemini 3 | Yes (custom instructions) |
| Ollama | Ollama only | No | Yes (qwen2.5vl, gemma3) | No | All installed models | Yes (global + per-flow) |
| AI Chat Control | Any MCP-compatible | N/A (MCP tools paradigm) | No | Yes (full device access) | N/A | No |
| OpenRouter | 200+ models via OpenRouter | No | No | No | Yes (autocomplete search) | Yes (per-card) |

---

## Table Stakes

Features users expect from any Homey AI app. Missing = product feels incomplete or users pick a competitor.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Send prompt, get text response via flow action card | Core use case — every AI app has this | Low | Returns response as flow token for Advanced Flow |
| Response as flow token | Needed to use output in subsequent flow cards (TTS, notification, etc.) | Low | Must use Advanced Flow — standard flows cannot receive action tokens |
| API key configuration in app settings | Required to authenticate with external services | Low | Needs masked input field for security |
| Connection test / status indicator | Users need feedback that API is reachable | Low | Gemini and OpenRouter do this; OpenAI/Ollama do not |
| System prompt configuration | All apps provide this — sets AI persona/rules | Low | Global setting minimum; per-flow override is better |
| Model selection | All apps expose model choice; users have preferences | Medium | Ollama: dynamic list from API; Claude: fixed set (Haiku/Sonnet/Opus) |
| Error handling visible to user | When API fails, flow must surface the error | Low | SDK: reject promise with message; Advanced Flow supports error paths |
| Ollama host/port configuration | Required for self-hosted setup | Low | Default 11434, IP address input |
| Basic settings page | Required by Homey App Store review | Low | Standard Homey app requirement |

---

## Differentiators

Features that set a product apart. Not universally expected, but create real value and retention.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-provider support (Ollama + Claude in one app) | Only app offering local + cloud AI without vendor lock-in | Medium | No existing app combines these two; unique gap in the market |
| Conversation memory with named sessions | Enables multi-turn flows (e.g. "doorbell assistant" keeps context) | Medium | Gemini does this within a 2hr window; OpenAI has global clear-history; no app supports named/isolated sessions |
| Per-flow system prompt override | Different automation contexts need different AI personas | Low-Medium | Ollama app has this; OpenAI/Gemini do not at flow-card level |
| Vision / image analysis via flow card | Analyze camera snapshots in Flows | Medium | Ollama and Gemini support this; requires image token droptoken in flow card |
| Provider selection per flow card | Choose Ollama for cost, Claude for quality, per use case | Medium | No existing app does this — unique to multi-provider design |
| Conversation clear card | Allow flows to reset conversation context explicitly | Low | OpenAI has "Clear chat history" action card; others lack this |
| Dynamic Ollama model list from API | No stale config — always reflects installed models | Low-Medium | Requires autocomplete argument type querying live Ollama API |
| Timeout configuration | Long-running local models (70B) need adjustable timeouts | Low | 70B on local hardware can take 30-60s; hardcoded timeout causes failures |
| Response streaming acknowledgement | Flows can react to partial responses without blocking | High | OpenAI implements partial response cards — complex, low priority for v1 |

---

## Anti-Features

Features to explicitly NOT build in v1. Each has a clear reason and a "what to do instead" answer.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Natural language device control | Requires Homey API access + tool-calling + safety guardrails — entire separate product | Use AI Chat Control app (nl.joonix.aichatcontrol) for this use case |
| MCP server / MCP tools | Different paradigm entirely; existing app does this well | Defer — AI Chat Control already covers this. Not a gap. |
| Voice assistant pipeline | Requires speech-to-text integration, latency challenges, microphone permissions | Out of scope — Athom is building native voice AI; compete with platform = losing |
| Flow generation from natural language | Meta-feature; requires deep Homey API knowledge + flow schema generation | Request from community but not an app-level feature; future Athom feature |
| DALL-E / image generation | Different use case from LLM text generation; adds provider complexity | OpenAI app covers this; not a gap worth filling |
| OpenAI / Gemini / OpenRouter support | Existing apps cover these; spreads focus without adding unique value | Focused v1 on Claude + Ollama only — add later if community requests |
| Partial / streaming responses in flows | High complexity, low practical value for home automation use cases | Return full response synchronously; streaming only makes sense for chat UI |
| Persistent cross-session memory (RAG/vector) | Overkill for home automation; adds infrastructure dependency | Conversation memory within session is sufficient; global facts go in system prompt |
| Billing / usage tracking dashboard | OpenRouter does this; not Homey's paradigm | Use Anthropic console + Ollama's free nature; no billing UI needed |
| Web UI / configuration dashboard outside settings | Homey's paradigm is settings page + flows | All config in settings page; flow logic in flow cards |

---

## Feature Dependencies

Dependencies between features that determine build order.

```
API key settings → Any provider API calls
Ollama host/port settings → Ollama model listing → Dynamic model selection → Ollama flow card
System prompt (global setting) → System prompt override per flow card
Basic prompt/response card → Conversation memory (extends basic card with context)
Conversation memory → Per-session conversation ID → Conversation clear card
Basic prompt/response card → Vision/image card (extends with image droptoken)
Error handling in cards → Error path in Advanced Flow (platform dependency)
```

---

## MVP Recommendation

### Must have (v1.0):

1. **Send prompt, get response** — action card with `{{response}}` token, for both Ollama and Claude
2. **Provider/model selection** — per flow card: pick provider + model
3. **API key + host config** in settings page
4. **System prompt** — global setting, overridable per flow card
5. **Connection validation** — test button or status capability in settings
6. **Error handling** — clear error messages surfaced to flow (reject with descriptive message)
7. **Dynamic Ollama model list** — autocomplete from live Ollama API

### Include in v1.0 (high value, manageable complexity):

8. **Conversation memory** — optional conversation ID argument; same ID = same context
9. **Clear conversation card** — action card to reset named conversation
10. **Vision/image support** — image droptoken on prompt card for vision-capable models

### Defer to v2:

- Partial/streaming response cards
- Natural language device control
- Additional providers (OpenAI, Gemini, OpenRouter)
- Flow-triggering from AI responses
- Response caching

---

## Flow Card Inventory (Proposed)

### Action Cards

| Card ID | Title | Inputs | Outputs | Advanced Flow Only |
|---------|-------|--------|---------|-------------------|
| `action_ask` | Ask [Provider] a question | prompt (string), model (autocomplete), conversation_id (string, optional), system_prompt (string, optional) | `{{response}}` (string) | Yes |
| `action_ask_with_image` | Ask [Provider] a question with image | prompt (string), image (image droptoken), model (autocomplete), conversation_id (string, optional) | `{{response}}` (string) | Yes |
| `action_clear_conversation` | Clear conversation | conversation_id (string) | none | No |
| `action_set_system_prompt` | Set system prompt | system_prompt (string) | none | No |

### No Trigger Cards in v1

No natural trigger surfaces for AI output — all flows are user-initiated or automation-triggered. Streaming/partial response triggers are deferred.

### No Condition Cards in v1

Conditions on AI output require knowing the output before the condition runs — logical impossibility. Users use downstream cards with IF logic in Advanced Flow instead.

---

## Platform Constraints Affecting Features

| Constraint | Impact |
|------------|--------|
| Action tokens only work in Advanced Flow | All useful AI response handling requires Advanced Flow; document this prominently |
| Image token type is `image` (stream + metadata) | Vision feature requires correct droptoken typing, not just string URL |
| No native async streaming in Homey flows | Full response must be awaited synchronously before flow continues |
| Homey Python SDK app size limits | Large dependency trees (e.g., full LangChain) are not feasible |
| Flow rejection = flow stops | API errors must throw with clear messages; silent failures are bad UX |
| App settings page is the only UI surface | No custom web UI; all configuration happens in settings page |

---

## Sources

- [OpenAI app on Homey](https://homey.app/en-us/app/com.openai.ChatGPT/OpenAI/) — flow card details, HIGH confidence
- [OpenAI Community Forum thread](https://community.homey.app/t/app-pro-openai-chatgpt/74750) — user feedback, MEDIUM confidence
- [Ollama app on Homey](https://homey.app/en-us/app/com.ollama/Ollama/) — flow cards, capabilities, HIGH confidence
- [Ollama Community Forum thread](https://community.homey.app/t/app-pro-ollama-use-local-llms-in-your-flows/143768) — settings, limitations, MEDIUM confidence
- [Gemini AI app on Homey](https://homey.app/en-us/app/com.dimapp.geminiai/Gemini-AI/) — HIGH confidence
- [Gemini AI Community Forum thread](https://community.homey.app/t/app-pro-gemini-ai-looking-for-testers-for-new-smart-home-features/149146) — feature details, MEDIUM confidence
- [AI Chat Control app on Homey](https://homey.app/en-us/app/nl.joonix.aichatcontrol/AI-Chat-Control/) — HIGH confidence
- [AI Chat Control GitHub](https://github.com/jvmenen/homey-ai-chat-control) — implementation details, MEDIUM confidence
- [OpenRouter app on Homey](https://homey.app/en-us/app/be.titansofindustry.openrouter/OpenRouter/) — HIGH confidence
- [OpenRouter GitHub](https://github.com/timbroddin/homey-openrouter/) — flow cards, tokens, MEDIUM confidence
- [Homey Apps SDK — Flow](https://apps.developer.homey.app/the-basics/flow) — platform constraints, HIGH confidence
- [Homey Apps SDK — Tokens](https://apps.developer.homey.app/the-basics/flow/tokens) — token types and limitations, HIGH confidence
- [Homey AI Extensions community discussion](https://community.homey.app/t/ai-extensions-and-tools-for-homey/135948) — user desires, LOW confidence (small sample)
