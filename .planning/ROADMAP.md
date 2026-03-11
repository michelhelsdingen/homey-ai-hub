# Roadmap: Homey AI Hub

## Overview

Build a Homey Pro Python app that exposes Claude and Ollama as Flow action cards. The work proceeds from the inside out: provider abstraction and core ask_ai card first (testable without Homey hardware), then conversation memory and system prompt configuration, then vision/image support, then App Store polish. Each phase adds a coherent capability on top of the previous.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core AI Integration** - Working Homey app with ask_ai Flow card routing to Claude or Ollama, model selection, settings, and connection validation
- [ ] **Phase 2: Conversation Memory and System Prompts** - Named conversation sessions with persistent history, sliding window, clear card, and system prompt configuration
- [ ] **Phase 3: Vision Support** - Image-capable Flow card for vision models (Ollama qwen2.5vl, Claude 3+)
- [ ] **Phase 4: App Store Polish** - Submission-ready app with compliant card titles, localization, icon, and security audit

## Phase Details

### Phase 1: Core AI Integration
**Goal**: Users can send a text prompt to Claude or Ollama from a Homey Flow and receive an AI response as a Flow token
**Depends on**: Nothing (first phase)
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05, PROV-06, FLOW-01, CONF-01
**Success Criteria** (what must be TRUE):
  1. User can configure Ollama host/port and Claude API key in the settings page and save them
  2. User can run the ask_ai Flow action card with a prompt and receive a non-empty AI response token
  3. User can select Claude or Ollama as the provider per card, and select from available models (Claude: Haiku/Sonnet/Opus; Ollama: live autocomplete from installed models)
  4. User can trigger a connection test from the settings page and see a clear pass/fail result
  5. When the LLM call fails (bad key, timeout, unreachable host), the Flow card returns a descriptive error token instead of silently failing
**Plans**: TBD

Plans:
- [x] 01-01: Project scaffold, provider abstraction, and async foundation
- [x] 01-02: Ollama and Claude provider implementations with unit tests
- [x] 01-03: Flow card wiring, settings page, and Docker integration test

### Phase 2: Conversation Memory and System Prompts
**Goal**: Users can have multi-turn AI conversations in Flows using named session IDs, with full system prompt control
**Depends on**: Phase 1
**Requirements**: FLOW-03, FLOW-04, FLOW-05, CONF-02, CONF-03
**Success Criteria** (what must be TRUE):
  1. User can pass the same conversation ID to ask_ai across multiple Flow executions and the AI remembers prior turns in that session
  2. User can run the clear_conversation Flow card to reset a named session, after which the next ask_ai call starts fresh
  3. User can set a global system prompt in settings that applies to all AI calls unless overridden per card
  4. User can set a per-card system prompt in the ask_ai action card that overrides the global system prompt for that execution
  5. Conversation history never exceeds the configured max length (sliding window evicts oldest turns)
**Plans**: TBD

Plans:
- [ ] 02-01: ConversationStore with sliding window and settings persistence
- [ ] 02-02: Flow cards for system prompt override and clear conversation

### Phase 3: Vision Support
**Goal**: Users can send an image alongside a prompt to vision-capable models from a Homey Flow
**Depends on**: Phase 2
**Requirements**: FLOW-02
**Success Criteria** (what must be TRUE):
  1. User can use the ask_ai_with_image Flow action card, attach an image droptoken, and receive a text response that reflects the image content
  2. Sending an image to a non-vision model returns a clear error token explaining the model does not support vision
**Plans**: TBD

Plans:
- [ ] 03-01: Image droptoken handling and vision provider implementations

### Phase 4: App Store Polish
**Goal**: The app passes Homey App Store review and is safe to submit publicly
**Depends on**: Phase 3
**Requirements**: (none new — delivery boundary for submission readiness)
**Success Criteria** (what must be TRUE):
  1. All Flow card titles pass App Store guidelines (short, imperative, no parentheses, English-only)
  2. The app.json contains no API keys or credentials (env.json is empty or gitignored)
  3. The app installs cleanly on a fresh Homey Pro with no settings configured and shows actionable guidance instead of crashing
  4. The settings page, card titles, and app description are consistent English with no partial translations
**Plans**: TBD

Plans:
- [ ] 04-01: App Store compliance audit and first-run hardening

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core AI Integration | 3/3 | Complete | 2026-03-11 |
| 2. Conversation Memory and System Prompts | 0/2 | Not started | - |
| 3. Vision Support | 0/1 | Not started | - |
| 4. App Store Polish | 0/1 | Not started | - |
