# Unified Flow Cards + Provider Fallback — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Merge ask_ai + control_home into unified AI cards (simple + extended), add image variants, implement provider fallback chain with default models per provider.

**Architecture:** Replace 4 action cards with 5 (2 AI, 2 Image, 1 Clear). Simple cards use defaults from settings, extended cards let user pick provider/model. On failure, auto-fallback to next configured provider with its default model.

**Tech Stack:** Homey SDK 3 (Python), homeycompose flow cards (JSON), existing provider classes

---

## Task 1: New Flow Card JSON Definitions

**Files:**
- Create: `.homeycompose/flow/actions/ai.json`
- Create: `.homeycompose/flow/actions/ai_custom.json`
- Create: `.homeycompose/flow/actions/ai_image.json`
- Create: `.homeycompose/flow/actions/ai_image_custom.json`
- Delete: `.homeycompose/flow/actions/ask_ai.json`
- Delete: `.homeycompose/flow/actions/ask_ai_with_image.json`
- Delete: `.homeycompose/flow/actions/control_home.json`
- Keep: `.homeycompose/flow/actions/clear_conversation.json` (no changes)

### Step 1: Create `ai.json` (simple — uses defaults)

```json
{
  "id": "ai",
  "title": { "en": "Ask or command AI" },
  "titleFormatted": { "en": "AI: [[prompt]]" },
  "hint": { "en": "Ask a question or give a command. AI answers or controls your devices." },
  "args": [
    {
      "type": "text",
      "name": "prompt",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "Turn off the lights / What's the weather?" }
    },
    {
      "type": "text",
      "name": "conversation_id",
      "title": { "en": "Conversation ID" },
      "placeholder": { "en": "Leave empty for single-turn" },
      "required": false
    },
    {
      "type": "text",
      "name": "system_prompt",
      "title": { "en": "Extra instructions" },
      "placeholder": { "en": "Always respond in Dutch" },
      "required": false
    }
  ]
}
```

### Step 2: Create `ai_custom.json` (extended — choose provider/model)

```json
{
  "id": "ai_custom",
  "title": { "en": "Ask or command AI (custom)" },
  "titleFormatted": { "en": "AI [[provider]]/[[model]]: [[prompt]]" },
  "hint": { "en": "Same as AI card but with custom provider and model." },
  "args": [
    {
      "type": "dropdown",
      "name": "provider",
      "title": { "en": "Provider" },
      "values": [
        { "id": "ollama", "label": { "en": "Ollama (local)" } },
        { "id": "claude", "label": { "en": "Claude" } },
        { "id": "openai", "label": { "en": "OpenAI" } }
      ]
    },
    {
      "type": "autocomplete",
      "name": "model",
      "title": { "en": "Model" },
      "placeholder": { "en": "Select model..." }
    },
    {
      "type": "text",
      "name": "prompt",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "Turn off the lights / What's the weather?" }
    },
    {
      "type": "text",
      "name": "conversation_id",
      "title": { "en": "Conversation ID" },
      "placeholder": { "en": "Leave empty for single-turn" },
      "required": false
    },
    {
      "type": "text",
      "name": "system_prompt",
      "title": { "en": "Extra instructions" },
      "placeholder": { "en": "Always respond in Dutch" },
      "required": false
    }
  ]
}
```

### Step 3: Create `ai_image.json` (simple image — uses defaults)

```json
{
  "id": "ai_image",
  "title": { "en": "Analyze image with AI" },
  "titleFormatted": { "en": "AI: analyze [[droptoken]] — [[prompt]]" },
  "droptoken": ["image"],
  "hint": { "en": "Send an image to AI for analysis. Uses your default provider." },
  "args": [
    {
      "type": "text",
      "name": "prompt",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "What do you see in this image?" }
    }
  ]
}
```

### Step 4: Create `ai_image_custom.json` (extended image)

```json
{
  "id": "ai_image_custom",
  "title": { "en": "Analyze image with AI (custom)" },
  "titleFormatted": { "en": "AI [[provider]]/[[model]]: [[droptoken]] — [[prompt]]" },
  "droptoken": ["image"],
  "hint": { "en": "Analyze image with a specific provider and model." },
  "args": [
    {
      "type": "dropdown",
      "name": "provider",
      "title": { "en": "Provider" },
      "values": [
        { "id": "ollama", "label": { "en": "Ollama (local)" } },
        { "id": "claude", "label": { "en": "Claude" } },
        { "id": "openai", "label": { "en": "OpenAI" } }
      ]
    },
    {
      "type": "autocomplete",
      "name": "model",
      "title": { "en": "Model" },
      "placeholder": { "en": "Select model..." }
    },
    {
      "type": "text",
      "name": "prompt",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "What do you see?" }
    }
  ]
}
```

### Step 5: Delete old card files

```bash
rm .homeycompose/flow/actions/ask_ai.json
rm .homeycompose/flow/actions/ask_ai_with_image.json
rm .homeycompose/flow/actions/control_home.json
```

### Step 6: Commit

```bash
git add .homeycompose/flow/actions/
git commit -m "feat: replace 4 flow cards with 5 unified cards (simple + custom)"
```

---

## Task 2: Settings — Default Models + Fallback Config

**Files:**
- Modify: `settings/index.html`
- Modify: `api.py`

### Step 1: Add new settings keys to `api.py`

Add to `SETTINGS_KEYS`:
```python
"default_model_ollama", "default_model_claude", "default_model_openai",
"fallback_enabled", "fallback_order",
```

### Step 2: Update `settings/index.html`

Add to each provider section a "Default Model" text input:
```html
<label for="default_model_ollama">Default Model</label>
<input type="text" id="default_model_ollama" placeholder="llama3.1">
<p class="hint">Used when no model is selected in the Flow card</p>
```

Add a new "Fallback" section after Defaults:
```html
<div class="section">
  <h2>Fallback</h2>
  <label><input type="checkbox" id="fallback_enabled"> Enable provider fallback</label>
  <p class="hint">If the primary provider fails, automatically try the next one.</p>

  <label for="fallback_order">Fallback order (comma-separated)</label>
  <input type="text" id="fallback_order" placeholder="claude,openai,ollama">
  <p class="hint">Order in which providers are tried. Only configured providers are used.</p>
</div>
```

Update `gatherAll()` and `loadSettings()` to include new fields. The checkbox needs special handling (`checked` property).

### Step 3: Commit

```bash
git add settings/index.html api.py
git commit -m "feat: add default model per provider + fallback settings"
```

---

## Task 3: Fallback Logic in `app.py`

**Files:**
- Modify: `app.py`

### Step 1: Add `_build_fallback_chain()` method

Returns list of `(provider_instance, model_name)` tuples to try in order.

```python
def _build_fallback_chain(self, primary_provider: str | None = None, primary_model: str | None = None) -> list[tuple]:
    """Build ordered list of (provider, model) to try.

    For simple cards: starts with default_provider + default_model.
    For custom cards: starts with user-selected provider/model.
    If fallback enabled: appends remaining configured providers + their default models.
    """
    chain = []

    # Primary
    prov_name = primary_provider or self.homey.settings.get("default_provider") or "ollama"
    provider, _ = self._get_provider(prov_name)
    model = primary_model or self.homey.settings.get(f"default_model_{prov_name}") or ""
    if provider:
        chain.append((provider, model, prov_name))

    # Fallback
    if self.homey.settings.get("fallback_enabled"):
        order_str = self.homey.settings.get("fallback_order") or "claude,openai,ollama"
        order = [p.strip() for p in order_str.split(",") if p.strip()]
        for fb_name in order:
            if fb_name == prov_name:
                continue  # skip primary
            fb_provider, _ = self._get_provider(fb_name)
            if fb_provider:
                fb_model = self.homey.settings.get(f"default_model_{fb_name}") or ""
                chain.append((fb_provider, fb_model, fb_name))

    return chain
```

### Step 2: Add `_resolve_model()` helper

If model is empty, fetch first model from provider:
```python
async def _resolve_model(self, provider, model: str, provider_name: str) -> str:
    if model:
        return model
    try:
        models = await provider.list_models()
        return models[0] if models else ""
    except Exception:
        return ""
```

### Step 3: Commit

```bash
git add app.py
git commit -m "feat: add fallback chain builder to App"
```

---

## Task 4: Unified AI Run Listener

**Files:**
- Modify: `app.py`

### Step 1: Create unified `_run_ai()` method

This replaces both `run_listener` (ask_ai) and `control_run_listener` (control_home):

```python
async def _run_ai(self, args: dict, use_smart_home: bool = True) -> dict:
    """Unified AI handler — text Q&A + optional device control with fallback."""
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return {"response": "Error: No prompt provided."}

    # Resolve provider/model from args or defaults
    provider_name = args.get("provider")  # None for simple cards
    model_arg = args.get("model")
    if isinstance(model_arg, dict):
        model = model_arg.get("name") or model_arg.get("id") or ""
    else:
        model = str(model_arg) if model_arg else ""

    chain = self._build_fallback_chain(provider_name, model)
    if not chain:
        return {"response": "Error: No AI provider configured. Check Settings."}

    # Conversation history
    conversation_id = (args.get("conversation_id") or "").strip()
    per_card_system = (args.get("system_prompt") or "").strip()
    global_system = (self.homey.settings.get("global_system_prompt") or "").strip()
    effective_system = per_card_system or global_system or None

    last_error = ""
    for provider, prov_model, prov_name in chain:
        resolved_model = await self._resolve_model(provider, prov_model, prov_name)
        if not resolved_model:
            last_error = f"No model available for {prov_name}"
            continue

        self.log(f"ai: trying {prov_name}/{resolved_model}")

        # Smart home path (tool use)
        if use_smart_home and self._homey_api:
            try:
                response, actions = await run_smart_home(
                    provider=provider, api=self._homey_api,
                    prompt=prompt, model=resolved_model,
                    system_prompt_extra=effective_system, log=self.log,
                )
                if not response.startswith("Error:"):
                    # Persist conversation
                    if conversation_id:
                        self._store.append(conversation_id, "user", prompt)
                        self._store.append(conversation_id, "assistant", response)
                    # Fire trigger
                    await self._response_trigger.trigger({
                        "response": response, "provider": prov_name,
                        "model": resolved_model, "prompt": prompt,
                    })
                    return {"response": response}
                last_error = response
            except Exception as e:
                last_error = f"Error: {prov_name} failed: {e}"
                self.log(f"ai: {prov_name} failed, trying next: {e}")
                continue
        else:
            # Pure text chat path
            if conversation_id:
                history = self._store.get(conversation_id)
                messages = list(history) + [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": prompt}]

            response = await provider.chat(
                messages=messages, model=resolved_model,
                system_prompt=effective_system,
            )
            if not response.startswith("Error:"):
                if conversation_id:
                    self._store.append(conversation_id, "user", prompt)
                    self._store.append(conversation_id, "assistant", response)
                await self._response_trigger.trigger({
                    "response": response, "provider": prov_name,
                    "model": resolved_model, "prompt": prompt,
                })
                return {"response": response}
            last_error = response
            self.log(f"ai: {prov_name} failed: {response}, trying next")

    return {"response": last_error or "Error: All providers failed."}
```

**Note:** The smart home path tries `run_smart_home()` which internally decides whether to use tools based on the AI's judgment. A question like "what's the weather" will get a text answer. A command like "turn off lights" will use tools.

### Step 2: Commit

```bash
git add app.py
git commit -m "feat: unified _run_ai() with fallback chain"
```

---

## Task 5: Register New Cards + Remove Old Registrations

**Files:**
- Modify: `app.py`

### Step 1: Rewrite `_register_flow_cards()`

Replace all old card registrations. The new structure:

```python
async def _register_flow_cards(self) -> None:
    # Triggers (unchanged)
    self._response_trigger = self.homey.flow.get_trigger_card("ai_response_received")
    self._webhook_trigger = self.homey.flow.get_trigger_card("webhook_received")

    # --- Simple AI card (uses defaults, smart home enabled) ---
    ai_card = self.homey.flow.get_action_card("ai")
    ai_card.register_run_listener(lambda args, **kw: self._run_ai(args))

    # --- Custom AI card (user picks provider/model) ---
    ai_custom_card = self.homey.flow.get_action_card("ai_custom")
    ai_custom_card.register_run_listener(lambda args, **kw: self._run_ai(args))
    ai_custom_card.register_argument_autocomplete_listener("model", self._model_autocomplete)

    # --- Simple Image card ---
    ai_image_card = self.homey.flow.get_action_card("ai_image")
    ai_image_card.register_run_listener(lambda args, **kw: self._run_ai_image(args))

    # --- Custom Image card ---
    ai_image_custom_card = self.homey.flow.get_action_card("ai_image_custom")
    ai_image_custom_card.register_run_listener(lambda args, **kw: self._run_ai_image(args))
    ai_image_custom_card.register_argument_autocomplete_listener("model", self._model_autocomplete)

    # --- Clear conversation (unchanged) ---
    clear_card = self.homey.flow.get_action_card("clear_conversation")
    clear_card.register_run_listener(self._clear_conversation)
```

### Step 2: Extract `_model_autocomplete` and `_clear_conversation` as methods

Move existing inline functions to class methods for reuse across cards.

### Step 3: Create `_run_ai_image()` method

Similar to `_run_ai` but calls `provider.chat_with_image()` with fallback:

```python
async def _run_ai_image(self, args: dict) -> dict:
    droptoken = args.get("droptoken")
    if droptoken is None:
        return {"response": "Error: No image provided."}

    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return {"response": "Error: No prompt provided."}

    # Read image from droptoken
    try:
        image_stream = await droptoken.get_stream()
        image_bytes = image_stream["data"].read()
        media_type = (image_stream.get("meta") or {}).get("contentType") or "image/jpeg"
    except Exception as e:
        return {"response": f"Error: Could not read image: {e}"}

    if media_type == "image/jpg":
        media_type = "image/jpeg"

    # Build chain and try with fallback
    provider_name = args.get("provider")
    model_arg = args.get("model")
    if isinstance(model_arg, dict):
        model = model_arg.get("name") or model_arg.get("id") or ""
    else:
        model = str(model_arg) if model_arg else ""

    chain = self._build_fallback_chain(provider_name, model)
    last_error = ""
    for provider, prov_model, prov_name in chain:
        resolved_model = await self._resolve_model(provider, prov_model, prov_name)
        if not resolved_model:
            continue
        response = await provider.chat_with_image(
            prompt=prompt, image_bytes=image_bytes,
            media_type=media_type, model=resolved_model,
        )
        if not response.startswith("Error:"):
            await self._response_trigger.trigger({
                "response": response, "provider": prov_name,
                "model": resolved_model, "prompt": prompt,
            })
            return {"response": response}
        last_error = response
        self.log(f"ai_image: {prov_name} failed: {response}")

    return {"response": last_error or "Error: All providers failed."}
```

### Step 4: Commit

```bash
git add app.py
git commit -m "feat: register unified cards with fallback"
```

---

## Task 6: Deploy & Test

### Step 1: Deploy

```bash
npx homey app install
```

### Step 2: Test checklist

**Simple flow on phone:**
- [ ] AI card visible in DAN section
- [ ] AI card works for text question ("Wat is 2+2?")
- [ ] AI card works for device command ("Zet de lampen in de woonkamer uit")
- [ ] Image card visible (if droptokens work in simple flows)
- [ ] Clear conversation visible and works

**Advanced flow on web:**
- [ ] All 5 cards visible
- [ ] Custom AI card: provider dropdown + model autocomplete works
- [ ] Custom Image card: provider/model + droptoken works

**Fallback:**
- [ ] Enable fallback in settings, set order
- [ ] Use simple AI card — works with default provider
- [ ] Temporarily break primary provider (wrong API key) — verify fallback fires
- [ ] Check logs: should show "trying next provider"

**Regression:**
- [ ] Conversation history still works (set conversation_id, ask two related questions)
- [ ] Trigger card "AI has responded" fires and has correct tokens
- [ ] Webhook trigger still works

### Step 3: Commit final

```bash
git add -A
git commit -m "feat: unified AI cards + provider fallback chain"
```
