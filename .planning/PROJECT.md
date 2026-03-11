# Homey AI Hub

## What This Is

A Python Homey app that provides unified AI/LLM integration for Homey smart home via two providers: Ollama (local/self-hosted) and Claude (Anthropic API). Users can send prompts and receive AI-generated responses in Homey Flows, with provider switching and conversation memory. Built with the Homey Python SDK.

## Core Value

Users can leverage AI (both local via Ollama and cloud via Claude) directly in their Homey Flows without being locked into a single provider.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-provider support (Ollama + Claude)
- [ ] Send text prompts via Flow action cards
- [ ] Receive AI responses as Flow tokens
- [ ] Provider selection per Flow card or globally
- [ ] Ollama model selection from installed models
- [ ] Claude model selection (Haiku, Sonnet, Opus)
- [ ] System prompt configuration (global + per-flow)
- [ ] Conversation memory (contextual multi-turn)
- [ ] Settings page for API keys and connection config
- [ ] Image/vision support for vision-capable models

### Out of Scope

- OpenAI/GPT integration — keep v1 focused on Claude + Ollama, add later
- Google Gemini integration — same reasoning
- Smart home device control via natural language — complex, defer to v2
- Flow triggering via AI — defer to v2
- MCP server integration — separate concern (AI Chat Control app does this)
- Voice assistant pipeline — out of scope entirely

## Context

- **Existing Homey AI apps**: OpenAI app (basic, 1yr stale), Gemini AI (advanced but Google-only), Ollama app (basic text only, v1.1.4), AI Chat Control (MCP-based, different approach)
- **Gap**: No Claude/Anthropic app exists. No unified multi-provider app exists. Existing Ollama app is very basic.
- **Ollama instance**: Running on Mac Mini at 192.168.2.214:11434 with models: llama3.1:70b, llama3.1:8b, qwen3-coder, qwen2.5-coder:14b/7b, glm-4.7-flash, gpt-oss:20b
- **Homey Python SDK**: Supports Python 3.14, async/await, Docker for testing, `homey-stubs` for type hints
- **Target**: Homey Pro (user has one for testing)
- **Developer has**: Docker on Mac, Claude API key available, Ollama already running

## Constraints

- **Tech stack**: Homey Python SDK (not Node.js) — deliberate choice to leverage Python AI ecosystem
- **Providers v1**: Only Ollama + Claude — focused scope
- **Testing**: Requires Docker + Homey Pro device
- **Dependencies**: Managed via `homey app dependency install` (not pip)
- **Platform**: Homey Pro only for v1 (Cloud compatibility can come later)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Better AI/ML library ecosystem, native async HTTP | — Pending |
| Claude + Ollama only (no OpenAI/Gemini) | Focused v1, avoid feature bloat | — Pending |
| Text generation first, no device control | Reduce complexity for v1, ship faster | — Pending |
| Eigen gebruik eerst, App Store later | Iterate fast without review overhead | — Pending |

---
*Last updated: 2026-03-11 after initialization*
