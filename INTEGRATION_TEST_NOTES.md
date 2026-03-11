# Integration Test Notes — Plan 01-03

## Status

CI-verifiable checks: PASSED
Docker-based end-to-end test: BLOCKED (homey CLI sharp conflict)

## CI Verification Results (2026-03-11)

All static and unit verifications passed:

- `app.py` — syntax OK
- `api.py` — syntax OK
- `.homeycompose/flow/actions/ask_ai.json` — valid JSON, structure OK
- `settings/index.html` — all required elements present
- 13 unit tests — all passing (pytest)

## Blocked: homey app build

The `homey app build` command fails locally with:

```
Error: Could not load the "sharp" module using the darwin-x64 runtime
```

This is the same known issue documented in 01-01-SUMMARY.md and STATE.md decisions.

Homey CLI version: global npm install at `/usr/local/bin/homey`

## Docker Test Steps (when CLI is fixed)

Prerequisites:
- Fix sharp: `npm install -g homey --include=optional` or use a compatible Node/arm64 build
- Docker Desktop running
- `homey login` or `homey login --local` with Homey Pro on LAN

Steps:
1. `cd /Users/michelhelsdingen/Documents/Homey/homey-ai-hub`
2. `homey app build` — verify app.json generated from .homeycompose/
3. `homey app run` — select Homey Pro when prompted

Expected startup logs:
- `Homey AI Hub starting...`
- `Homey AI Hub ready.`
- No Python exceptions or import errors

Settings verification:
- Open Homey app > More > Apps > Homey AI Hub > Settings
- Set Ollama URL: `http://192.168.2.214:11434`
- Click "Test Ollama Connection" — expect green "Ollama OK at ..."
- (Optional) Enter Claude API key, click "Test Claude Connection"

Flow card verification:
1. Open Advanced Flow editor
2. Add action: "Ask AI"
3. Set Prompt: "What is 2+2?"
4. Set Provider: Ollama
5. Click Model dropdown — expect live Ollama model list
6. Select a model (e.g. `llama3.1:8b`)
7. Run the Flow
8. Check `{{response}}` token — expect non-empty answer

Error handling verification:
- Provider: Claude (no API key configured)
- Expected `{{response}}`: "Error: Provider 'claude' not configured. Check Settings > Homey AI Hub."

## Workaround for homey CLI

The app was manually scaffolded in 01-01 using JSON validation in lieu of `homey app validate`.
All logic, file structure, and manifest JSON are correct per SDK documentation.
The sharp module issue is in the CLI image processing module, unrelated to app runtime behavior.
