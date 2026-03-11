# Requirements: Homey AI Hub

**Defined:** 2026-03-11
**Core Value:** Users can leverage AI (both local via Ollama and cloud via Claude) directly in their Homey Flows without being locked into a single provider.

## v1 Requirements

### Provider Integration

- [x] **PROV-01**: User can configure Ollama connection via IP address and port in settings
- [x] **PROV-02**: User can configure Claude API key in settings
- [x] **PROV-03**: User can select a model per provider (Ollama: from installed models, Claude: Haiku/Sonnet/Opus)
- [x] **PROV-04**: User can set a default provider (Ollama or Claude) in settings
- [x] **PROV-05**: User can test connection to Ollama and Claude from settings page
- [x] **PROV-06**: User can see dynamically fetched model list from Ollama API via autocomplete

### Flow Cards

- [x] **FLOW-01**: User can send a text prompt to selected provider via Flow action card and receive AI response as token
- [x] **FLOW-02**: User can send a prompt with image to a vision-capable model via Flow action card
- [x] **FLOW-03**: User can set system prompt dynamically per flow via action card
- [x] **FLOW-04**: User can use named conversation sessions for isolated multi-turn context
- [x] **FLOW-05**: User can clear a conversation session via Flow action card

### Settings & Configuration

- [x] **CONF-01**: User can configure timeout per provider (default: 30s Claude, 120s Ollama)
- [x] **CONF-02**: User can set a global system prompt in settings
- [x] **CONF-03**: User can configure max conversation history length (sliding window)

## v2 Requirements

### Additional Providers

- **PROV-V2-01**: User can connect OpenAI/GPT models
- **PROV-V2-02**: User can connect Google Gemini models
- **PROV-V2-03**: User can connect any OpenAI-compatible API endpoint

### Smart Home Control

- **CTRL-V2-01**: User can control Homey devices via natural language through AI
- **CTRL-V2-02**: AI can query device status and respond with current state
- **CTRL-V2-03**: AI can trigger existing Homey Flows

### Advanced Features

- **ADV-V2-01**: User can receive streaming/partial responses
- **ADV-V2-02**: User can define custom tools the AI can call
- **ADV-V2-03**: Telegram bot integration for remote AI queries

## Out of Scope

| Feature | Reason |
|---------|--------|
| MCP server on Homey | AI Chat Control app already does this well |
| Voice assistant pipeline | Platform-level concern, not an app feature |
| Device pairing/driver | No physical devices — this is a service app |
| OpenAI/Gemini in v1 | Keep v1 focused on Claude + Ollama, add providers later |
| Real-time streaming to Flow | Homey Flow tokens don't support streaming |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 1 | Complete |
| PROV-02 | Phase 1 | Complete |
| PROV-03 | Phase 1 | Complete |
| PROV-04 | Phase 1 | Complete |
| PROV-05 | Phase 1 | Complete |
| PROV-06 | Phase 1 | Complete |
| FLOW-01 | Phase 1 | Complete |
| FLOW-02 | Phase 3 | Complete |
| FLOW-03 | Phase 2 | Complete |
| FLOW-04 | Phase 2 | Complete |
| FLOW-05 | Phase 2 | Complete |
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 2 | Complete |
| CONF-03 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-11*
*Last updated: 2026-03-12 after plan 03-01 — Phase 3 plan 01 complete, FLOW-02 satisfied (13/14 v1 requirements complete)*
