# Phase 4: App Store Polish - Research

**Researched:** 2026-03-12
**Domain:** Homey App Store submission requirements, manifest compliance, first-run UX, security audit
**Confidence:** HIGH (official Homey SDK docs verified)

---

## Summary

Phase 4 is a delivery boundary phase: no new functional requirements are added, but the app must pass Homey App Store review before it can be submitted publicly. The work falls into four distinct areas: (1) manifest compliance (missing required fields: `brandColor`, `runtime`, `platforms`, `pythonVersion`), (2) assets (no `assets/icon.svg` or `assets/images/*.png` files exist at all), (3) flow card title compliance (parentheses in `ask_ai` title violate guidelines; titles should be short and imperative), and (4) first-run hardening and localization consistency.

The `env.json` angle is a non-issue by design: the app uses `homey.settings` to store API keys, not `env.json`. The `.gitignore` does not mention `env.json` — but since the file does not exist and credentials are in settings (correct pattern), this just needs a single `.gitignore` line as a precaution. The biggest gap discovered is that the `assets/` directory does not exist at all, meaning `homey app validate --level publish` will fail immediately.

**Primary recommendation:** Fix the manifest gaps first (brandColor, runtime, platforms, pythonVersion), create placeholder assets so validation passes, then fix the three flow card title issues, then verify first-run error paths and localization completeness.

---

## Manifest Gaps (Current vs Required)

Current `.homeycompose/app.json` is missing these fields required for App Store submission:

| Field | Required? | Current Value | Required Value |
|-------|-----------|---------------|----------------|
| `brandColor` | MANDATORY | missing | Any hex color, not too bright |
| `runtime` | MANDATORY | missing | `"python"` |
| `platforms` | MANDATORY | missing | `["local"]` (this is a Homey Pro app, not cloud) |
| `pythonVersion` | Recommended | missing | `"3.14"` (current Homey Python runtime) |
| `support` | Required for Verified Devs | missing | URL or mailto |
| `source` | Recommended | missing | GitHub URL |
| `bugs` | Recommended | missing | GitHub issues URL |
| `images.xlarge` | Optional | missing | `/assets/images/xlarge.png` |

The `category` field uses an array (`["tools"]`) — the manifest spec shows `category` as a single string. This may or may not cause validation issues; worth checking against `homey app validate`.

Confidence: HIGH — verified against https://apps.developer.homey.app/the-basics/app/manifest

---

## Assets Gap

No `assets/` directory exists anywhere in the repo. The manifest references:
- `/assets/images/small.png` (250×175 px, JPG or PNG)
- `/assets/images/large.png` (500×350 px, JPG or PNG)

Also required by `homey app validate --level publish`:
- `/assets/icon.svg` — SVG with transparent background, 960×960px canvas, no background color

Missing:
```
assets/
├── icon.svg          # App icon — SVG, transparent bg, 960×960 canvas
└── images/
    ├── small.png     # 250×175 px
    ├── large.png     # 500×350 px
    └── xlarge.png    # 1000×700 px (optional but recommended)
```

Confidence: HIGH — verified against guidelines and manifest docs

---

## Standard Stack

### Homey CLI (validation and publish)
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| `homey` CLI | global npm | `homey app validate --level publish` | Known sharp conflict on this machine — see INTEGRATION_TEST_NOTES.md |
| `homey app publish` | same | Submits to App Store | Triggers version bump prompt |

**The sharp module conflict** (documented in STATE.md) blocks `homey app run` and `homey app build` but does not block static validation of JSON files. Manual JSON validation is the established workaround for this project.

### No new dependencies needed
This is a polish/compliance phase. No new Python packages or npm packages are required.

---

## Architecture Patterns

### Flow Card Title Format
Official guidelines (verified at apps.developer.homey.app/app-store/guidelines):
- Short and clear — users must "instantly know what the action does"
- Imperative verb form: "Lock door", "Send message", "Ask AI"
- No parentheses
- No When/And/Then in the title
- No device names in the title
- `titleFormatted` uses `[[arg_name]]` syntax to show arguments inline

**Current titles and compliance status:**

| Card | Current `title.en` | Current `titleFormatted.en` | Issue |
|------|---------------------|------------------------------|-------|
| `ask_ai` | `"Ask AI"` | `"Ask [[provider]] AI ([[model]]): [[prompt]]"` | Parentheses around `[[model]]` violate guidelines |
| `ask_ai_with_image` | `"Ask AI about image"` | `"Ask [[provider]] AI ([[model]]) about image: [[prompt]]"` | Parentheses around `[[model]]` violate guidelines |
| `clear_conversation` | `"Clear conversation"` | `"Clear conversation [[conversation_id]]"` | OK — compliant |

The `title` fields are all clean and short. Only the `titleFormatted` strings have parentheses issues.

**Recommended fixes:**
```json
// ask_ai titleFormatted — remove parentheses around [[model]]
"titleFormatted": { "en": "Ask [[provider]] AI with [[model]]: [[prompt]]" }

// ask_ai_with_image titleFormatted — remove parentheses around [[model]]
"titleFormatted": { "en": "Ask [[provider]] AI with [[model]] about image: [[prompt]]" }
```

Confidence: HIGH — parentheses prohibition is explicit in the guidelines

---

### First-Run Behavior Audit

**What the app does today on a fresh install with no settings:**

1. `on_init()` reads `max_history_turns` — falls back to `10` if not set. OK.
2. `_init_providers()`: Ollama is always initialized with `DEFAULT_HOST` (`http://localhost:11434`). Claude is skipped if no API key. OK.
3. Any Flow card run with `provider="claude"` when no key configured returns: `"Error: Provider 'claude' not configured. Check Settings > Homey AI Hub."` — actionable message. OK.
4. Any Flow card run with `provider="ollama"` when Ollama is unreachable: the OllamaProvider will return an error message from `provider.chat()`. Should be graceful.

**Gap to verify:** What happens if `ask_ai` is run with no model selected and Ollama is unreachable? The code path `models = await provider.list_models()` may throw instead of returning an empty list if Ollama is down. This needs a defensive check.

**Settings page first-run behavior:** The settings page loads without error — it shows empty fields and hints. No crash path. The "Test Connection" buttons handle errors gracefully via try/catch.

Confidence: MEDIUM — code is reviewed, but `list_models()` error path not verified against actual provider implementations

---

### Localization Consistency Audit

**Current locales:** Only `en.json` exists (correct — English mandatory).

**Localization gaps found:**

| Issue | Location | Detail |
|-------|----------|--------|
| `en.json` keys are unused | `locales/en.json` | 14 keys defined but settings page uses hardcoded English strings directly in HTML, not `Homey.__(...)` calls |
| `en.json` missing keys | `locales/en.json` | Keys for `global_system_prompt`, `max_history_turns`, `conversation_settings` section are not in `en.json` |
| Flow card args not in locale | Flow JSON files | Flow card arg labels use inline `"en"` strings — this is correct Homey pattern, not a gap |

The `locales/en.json` appears disconnected from the actual settings page — the HTML has its own hardcoded English text. This is not necessarily a review blocker since the settings page renders correctly, but the locale file should at minimum be internally consistent with the app.

**App description** in `app.json`:
```json
"description": { "en": "Multi-provider AI integration for Homey Flows — Claude and Ollama" }
```
This uses an em-dash (—). Should be fine, but the guidelines say "engaging one-liner" — this reads as technical jargon, not a user benefit statement. Consider: "Use Claude and Ollama AI directly in your Homey Flows."

Confidence: MEDIUM — observed from file review; Homey does not publish explicit rules about `en.json` usage in settings pages

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Icon creation | Custom SVG drawing tool | Create SVG directly in a text editor or use a vector editor. The icon is a simple file requirement. |
| Image resizing | Python PIL scripts | Create correctly-sized PNGs directly. For a service app, simple solid-color placeholder images suffice to pass validation. |
| Manifest validation | Custom JSON schema checker | `homey app validate` (when CLI is fixed) OR `homey app validate` from another machine without the sharp issue |

---

## Common Pitfalls

### Pitfall 1: category as array vs string
**What goes wrong:** The current `app.json` has `"category": ["tools"]` (array). The manifest docs show `"category": "tools"` (string). Validation may reject the array form.
**How to avoid:** Change to `"category": "tools"` in `.homeycompose/app.json`.
**Confidence:** MEDIUM — manifest example shows string; current code uses array

### Pitfall 2: `brandColor` too bright fails validation
**What goes wrong:** Athom's validator rejects colors that are "too bright" (high luminance). Pure white (`#FFFFFF`) or neon colors will fail.
**How to avoid:** Use a mid-range saturation color. For an AI/tech app, dark blues or purples work well. Example: `#1a73e8` (Google blue used in the settings page already).
**Confidence:** HIGH — explicitly stated in manifest docs

### Pitfall 3: No assets directory = immediate validate failure
**What goes wrong:** `homey app validate --level publish` checks for the existence of icon.svg and image files. With no `assets/` directory the validation fails before any other checks run.
**How to avoid:** Create the `assets/` directory with placeholder files before attempting any validation.
**Confidence:** HIGH

### Pitfall 4: `list_models()` can throw on unconfigured Ollama
**What goes wrong:** If a user runs an `ask_ai` Flow card without selecting a model and Ollama is unreachable, `provider.list_models()` may raise an exception rather than return an empty list. The card error handler only checks the return value.
**How to avoid:** Wrap `list_models()` call in a try/except in `run_listener`. If it throws, return a descriptive error token.
**Confidence:** MEDIUM — code path identified but provider implementation not inspected

### Pitfall 5: Submitting without running `homey app validate --level publish`
**What goes wrong:** Many manifest issues (missing fields, invalid images) are caught by the CLI validator. Skipping it means discovering rejections from Athom reviewers after a 2-week wait.
**How to avoid:** Fix the sharp conflict or run validation on a Linux/ARM machine (Docker). The sharp conflict is in image processing CLI only — a Docker container with Node.js on linux/amd64 or linux/arm64 will not have this issue.
**Confidence:** HIGH

### Pitfall 6: Partial localization = rejection
**What goes wrong:** The guidelines explicitly state: "If you translate Flow cards, make sure to translate all Flow cards, device settings, capabilities." For English-only apps this means all keys must be consistent and complete.
**How to avoid:** Only ship one locale (`en.json`), ensure all user-visible text uses consistent terminology, and do not mix Dutch/English (not currently an issue, but something to verify in settings HTML).
**Confidence:** HIGH

---

## Code Examples

### Manifest with all required fields
```json
// Source: https://apps.developer.homey.app/the-basics/app/manifest
{
  "id": "com.michelhelsdingen.homey-ai-hub",
  "version": "1.0.0",
  "compatibility": ">=12.0.0",
  "runtime": "python",
  "platforms": ["local"],
  "sdk": 3,
  "brandColor": "#1a73e8",
  "pythonVersion": "3.14",
  "name": { "en": "Homey AI Hub" },
  "description": { "en": "Use Claude and Ollama AI directly in your Homey Flows." },
  "category": "tools",
  "permissions": ["homey:manager:flow"],
  "images": {
    "small": "/assets/images/small.png",
    "large": "/assets/images/large.png",
    "xlarge": "/assets/images/xlarge.png"
  },
  "author": {
    "name": "Michel Helsdingen",
    "email": "michel@example.com"
  },
  "source": "https://github.com/michelhelsdingen/homey-ai-hub",
  "bugs": { "url": "https://github.com/michelhelsdingen/homey-ai-hub/issues" }
}
```

### Compliant flow card titleFormatted (no parentheses)
```json
// Source: https://apps.developer.homey.app/app-store/guidelines (Flow Card Requirements)
{
  "title": { "en": "Ask AI" },
  "titleFormatted": { "en": "Ask [[provider]] AI with [[model]]: [[prompt]]" }
}

{
  "title": { "en": "Ask AI about image" },
  "titleFormatted": { "en": "Ask [[provider]] AI with [[model]] about image: [[prompt]]" }
}
```

### Defensive list_models in run_listener
```python
# Pattern: wrap list_models() in try/except so unconfigured Ollama doesn't crash the card
if not model:
    try:
        models = await provider.list_models()
        model = models[0] if models else ""
    except Exception as e:
        return {"response": f"Error: Could not fetch models for {name}: {e}"}

if not model:
    return {"response": f"Error: No model selected and no models available for {name}."}
```

### gitignore entry for env.json
```
# Homey environment variables (contains secrets — never commit)
env.json
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Manual manifest editing | Homey Compose (`.homeycompose/app.json`) | Generated `app.json` at build time — never edit `app.json` directly |
| Static flow card titles only | `title` + `titleFormatted` | `titleFormatted` inlines argument values for clarity in Flow editor |
| Hardcoded credentials in app | `env.json` (gitignored) or `homey.settings` | Settings approach (used here) is the right pattern — no credentials in source |

---

## Open Questions

1. **`category` array vs string**
   - What we know: Current manifest uses `"category": ["tools"]` (array); manifest docs show `"category": "tools"` (string)
   - What's unclear: Whether the Homey CLI validator accepts both forms or only string
   - Recommendation: Change to string form to match official example; no functional difference

2. **`pythonVersion` value**
   - What we know: Manifest docs say `"3.14"` is current; Homey runs Python on their hardware
   - What's unclear: Whether Homey Pro 2023+ hardware actually runs 3.14 or still 3.11/3.12 for Python apps
   - Recommendation: Use `"3.14"` per official docs; if app fails to start on Homey Pro, try `"3.12"`

3. **`platforms` field value**
   - What we know: Options are `"local"` and/or `"cloud"`. This app requires Ollama (local network) and Claude (internet).
   - What's unclear: Whether `["local"]` is correct (the app runs on Homey Pro hardware — "local" refers to Homey Bridge vs Homey Pro) or whether `["local", "cloud"]` is needed since Claude calls go to the internet
   - Recommendation: Use `["local"]` — "platforms" refers to the Homey device type (local = Homey Pro, cloud = Homey Bridge), not network access patterns

4. **Sharp conflict blocking CLI validation**
   - What we know: `homey app validate` fails with sharp module error on this machine
   - What's unclear: Whether a Docker-based workaround is feasible before submission
   - Recommendation: Run `docker run --rm -v $(pwd):/app node:20 sh -c "npm install -g homey && homey app validate"` as a workaround, or fix the local sharp issue

---

## Full Compliance Checklist

Items that must be true before submission:

### Manifest
- [ ] `brandColor` added (hex, not too bright)
- [ ] `runtime: "python"` added
- [ ] `platforms: ["local"]` added
- [ ] `pythonVersion: "3.14"` added
- [ ] `category` changed from array to string `"tools"`
- [ ] `description` updated to user-benefit language
- [ ] `source` and `bugs` URLs added (optional but recommended)
- [ ] `version` updated to `1.0.0` for first public release

### Assets
- [ ] `assets/icon.svg` created (SVG, transparent background, 960×960 canvas)
- [ ] `assets/images/small.png` created (250×175 px)
- [ ] `assets/images/large.png` created (500×350 px)
- [ ] `assets/images/xlarge.png` created (1000×700 px, optional)

### Flow Card Titles
- [ ] `ask_ai.json` `titleFormatted` — parentheses removed from `[[model]]`
- [ ] `ask_ai_with_image.json` `titleFormatted` — parentheses removed from `[[model]]`
- [ ] `clear_conversation.json` — already compliant, no change needed

### Security
- [ ] `env.json` added to `.gitignore` (file doesn't exist, but entry prevents accidental creation)
- [ ] Verify no `claude_api_key` or `ollama_url` values appear in any tracked file

### First-Run Hardening
- [ ] `list_models()` call in `run_listener` wrapped in try/except
- [ ] Verify app starts cleanly with all settings empty (no crashes)
- [ ] Verify error messages are actionable when no provider is configured

### Localization
- [ ] All user-visible text is English-only (no Dutch strings)
- [ ] No typos in flow card titles, arg labels, or settings page
- [ ] `en.json` keys are internally consistent (even if not all used in settings page)
- [ ] `ask_ai` arg title `"System Prompt (optional)"` — parentheses here are in a label field, not a card title, which is fine

---

## Sources

### Primary (HIGH confidence)
- https://apps.developer.homey.app/app-store/guidelines — complete guidelines extracted and verified
- https://apps.developer.homey.app/the-basics/app/manifest — all required manifest fields
- https://apps.developer.homey.app/the-basics/app — env.json usage and security
- https://apps.developer.homey.app/app-store/publishing — submission process

### Secondary (MEDIUM confidence)
- https://apps.developer.homey.app/the-basics/flow — flow card title best practices
- Current project code (`app.py`, flow JSON files, `settings/index.html`) — audited directly

---

## Metadata

**Confidence breakdown:**
- Manifest gaps: HIGH — verified against official SDK manifest docs
- Asset requirements: HIGH — verified against guidelines and CLI docs
- Flow card title rules: HIGH — parentheses prohibition is explicit in guidelines
- First-run hardening: MEDIUM — code reviewed, `list_models()` error path inferred not tested
- Localization: MEDIUM — `en.json` disconnection from HTML is observed but not confirmed as blocker

**Research date:** 2026-03-12
**Valid until:** 2026-06-12 (Homey SDK guidelines change infrequently)
