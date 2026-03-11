# Phase 3: Vision Support — Research

**Researched:** 2026-03-11
**Domain:** Homey image droptokens, Anthropic Vision API, Ollama vision models
**Confidence:** MEDIUM — Anthropic and Ollama APIs verified via official docs (HIGH); Homey Python droptoken image API is partially inferred from JS SDK documentation (MEDIUM/LOW for exact Python method signatures)

---

## Summary

Phase 3 adds a new `ask_ai_with_image` Flow action card. The user attaches an image droptoken (from a camera, snapshot, or other image-producing card), provides a text prompt, selects a provider and model, and receives a text response. The image is read from the droptoken, converted to base64 bytes, and forwarded to the provider in provider-specific format.

The Anthropic SDK for Python has a well-documented vision API: the user message content becomes a list of content blocks, with an `image` block (base64 + media type) placed before the `text` block. The Ollama Python AsyncClient accepts raw bytes in the `images` field of a message dict and handles base64 encoding internally. Both paths are straightforward extensions of the existing `chat()` method signature.

The critical uncertainty is the exact Python SDK API for reading image bytes from a Homey droptoken. The JS SDK exposes `args.droptoken.getStream()` returning a ReadableStream with `contentType` and `filename`. The Python SDK documentation shows `get_stream()` returning a dict with `meta` (contentType, filename) and `data` keys. Because this is only confirmed via a secondary fetch of the Tokens SDK page (not a primary official Python-specific reference), this must be treated as MEDIUM confidence and verified in Wave 0 by inspecting the live Homey Python SDK source or a quick smoke test.

**Primary recommendation:** Build `ask_ai_with_image` as a new standalone Flow card with its own JSON definition and a new `chat_with_image()` method on both providers. Do not modify the existing `ask_ai` card — this keeps backward compatibility intact and avoids touching the working Phase 2 implementation.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FLOW-02 | User can send a prompt with image to a vision-capable model via Flow action card | New `ask_ai_with_image` card with droptoken type `image`; ClaudeProvider and OllamaProvider both extended with `chat_with_image()`; non-vision model guard returns clear error token |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic (AsyncAnthropic) | >=0.84.0 (already installed) | Claude vision via base64 content blocks | Already in requirements.txt; AsyncAnthropic.messages.create() accepts image content blocks natively |
| ollama (AsyncClient) | >=0.6.1 (already installed) | Ollama vision via `images` parameter | Already in requirements.txt; AsyncClient.chat() accepts `images: [bytes]` in message dict; Image class auto-encodes |
| base64 (stdlib) | Python stdlib | Encode image bytes for Anthropic | No install needed; standard_b64encode(bytes).decode() pattern is the official Anthropic Python example |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mimetypes (stdlib) | Python stdlib | Infer media_type from content_type header | Map `image/jpeg` → `"image/jpeg"` for Anthropic content block |

### No New Dependencies
No new packages are required. This phase is implemented entirely with existing `anthropic`, `ollama`, and Python stdlib.

**Installation:**
```bash
# No new packages — requirements.txt unchanged
```

---

## Architecture Patterns

### Recommended Project Structure
```
lib/
├── providers/
│   ├── base.py          # Add chat_with_image() ABC method
│   ├── claude.py        # Implement chat_with_image() with content blocks
│   └── ollama_provider.py  # Implement chat_with_image() with images param
.homeycompose/
└── flow/
    └── actions/
        ├── ask_ai.json          # UNCHANGED — backward compat preserved
        └── ask_ai_with_image.json  # NEW — droptoken: ["image"]
tests/
├── test_claude_provider.py      # Add vision tests
└── test_ollama_provider.py      # Add vision tests
app.py                           # Register ask_ai_with_image card listener
```

### Pattern 1: New ABC Method `chat_with_image()`
**What:** Add a new abstract method to LLMProvider that accepts image bytes and media type alongside the text prompt. Keeps `chat()` pure for text-only; no risk of breaking existing flows.
**When to use:** Always for image-bearing calls. Never overload `chat()` with optional image bytes.
**Example:**
```python
# lib/providers/base.py — extend existing ABC
@abstractmethod
async def chat_with_image(
    self,
    prompt: str,
    image_bytes: bytes,
    media_type: str,
    model: str,
    timeout: float | None = None,
    system_prompt: str | None = None,
) -> str:
    """Send a prompt + image to the AI and return the assistant response text.

    Args:
        prompt: Text question about the image.
        image_bytes: Raw image binary data.
        media_type: MIME type, e.g. "image/jpeg", "image/png".
        model: Model ID string (must be vision-capable).
        timeout: Optional per-call timeout override in seconds.
        system_prompt: Optional system instruction string.

    Returns:
        Assistant response as plain text string.
        On error, returns human-readable error string starting with "Error:".
    """
    ...
```

### Pattern 2: Claude vision content block
**What:** Anthropic messages API uses a list-of-content-blocks for vision. Image block comes before text block in the content array.
**When to use:** Every ClaudeProvider.chat_with_image() call.
**Example:**
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/vision
import base64

async def chat_with_image(self, prompt, image_bytes, media_type, model, ...):
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,   # "image/jpeg", "image/png", etc.
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]
    kwargs = dict(model=model, max_tokens=1024, messages=messages)
    if system_prompt:
        kwargs["system"] = system_prompt
    response = await self._client.messages.create(**kwargs)
    return response.content[0].text
```

### Pattern 3: Ollama vision via images parameter
**What:** Ollama chat messages accept an `images` key alongside `content`. The Ollama Python client's `Image` class auto-converts bytes to base64. Passing `bytes` directly is safe.
**When to use:** Every OllamaProvider.chat_with_image() call.
**Example:**
```python
# Source: https://docs.ollama.com/capabilities/vision
# Source: https://deepwiki.com/ollama/ollama-python/4.3-multimodal-capabilities
async def chat_with_image(self, prompt, image_bytes, media_type, model, ...):
    messages = [
        {
            "role": "user",
            "content": prompt,
            "images": [image_bytes],   # bytes — AsyncClient auto-encodes to base64
        }
    ]
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages
    response = await self._client.chat(model=model, messages=messages)
    return response.message.content
```

### Pattern 4: Homey droptoken image reading
**What:** In the run_listener, `args["droptoken"]` is the image object passed by Homey. Call `await args["droptoken"].get_stream()` to read image bytes and content type.
**When to use:** In the `ask_ai_with_image` run_listener.
**Confidence:** MEDIUM — based on JS SDK pattern (`args.droptoken.getStream()`) and secondary Python SDK documentation. The exact dict structure of the result needs verification in Wave 0.
**Expected pattern (to verify):**
```python
# Expected — verify against Homey Python SDK source on device
async def run_listener(args: dict, **kwargs) -> dict:
    droptoken = args.get("droptoken")
    if droptoken is None:
        return {"response": "Error: No image provided."}
    image_stream = await droptoken.get_stream()
    # image_stream may be dict: {"meta": {"contentType": ..., "filename": ...}, "data": ...}
    # OR the stream object itself with .read() — VERIFY on live Homey
    image_bytes = image_stream["data"].read()     # adjust based on actual API
    media_type = image_stream["meta"]["contentType"]  # e.g. "image/jpeg"
```
**Alternative:** If `get_stream()` returns a ReadableStream-like object (not a dict), use:
```python
image_bytes = b"".join([chunk async for chunk in droptoken.get_stream()])
# contentType may be a property on the stream object: stream.content_type
```

### Pattern 5: ask_ai_with_image card JSON — droptoken definition
**What:** `droptoken` is a top-level property alongside `args` in the Flow card JSON. It takes an array of allowed types. The droptoken appears as `args["droptoken"]` in the run_listener.
**Example:**
```json
{
  "id": "ask_ai_with_image",
  "title": { "en": "Ask AI about image" },
  "titleFormatted": { "en": "Ask [[provider]] AI ([[model]]) about image: [[prompt]]" },
  "droptoken": ["image"],
  "args": [
    {
      "name": "prompt",
      "type": "text",
      "title": { "en": "Prompt" },
      "placeholder": { "en": "What is in this image?" }
    },
    {
      "name": "provider",
      "type": "dropdown",
      "title": { "en": "Provider" },
      "values": [
        { "id": "ollama", "label": { "en": "Ollama (local)" } },
        { "id": "claude", "label": { "en": "Claude (cloud)" } }
      ]
    },
    {
      "name": "model",
      "type": "autocomplete",
      "title": { "en": "Model" },
      "placeholder": { "en": "Select model..." }
    }
  ],
  "tokens": [
    {
      "name": "response",
      "type": "string",
      "title": { "en": "AI Response" },
      "example": { "en": "The image shows a living room with the lights on." }
    }
  ]
}
```

### Pattern 6: Non-vision model guard
**What:** Return a clear error token when a non-vision model is selected. Claude all models support vision (claude-haiku-4-5, claude-sonnet-4-5, claude-opus-4-5). For Ollama, known vision models include llava, llava-phi3, moondream, qwen2.5vl, llama3.2-vision. Maintain a class-level `VISION_MODELS` set for Ollama; Claude always passes through.
**When to use:** At the start of OllamaProvider.chat_with_image() before making the API call.
**Example:**
```python
# In OllamaProvider
VISION_MODELS = {"llava", "llava-phi3", "moondream", "qwen2.5vl", "llama3.2-vision"}

async def chat_with_image(self, prompt, image_bytes, media_type, model, ...):
    # Check if model name starts with any known vision model prefix
    is_vision = any(model.startswith(vm) for vm in self.VISION_MODELS)
    if not is_vision:
        return f"Error: Model '{model}' does not support vision. Use a vision model (e.g. llava, qwen2.5vl, llama3.2-vision)."
    ...
```

### Anti-Patterns to Avoid
- **Storing image bytes in ConversationStore:** Do not persist image bytes in conversation history. Images should be single-turn only in this phase — pass `conversation_id` support is intentionally omitted from `ask_ai_with_image` to avoid unbounded memory growth.
- **Modifying ask_ai.json or the existing run_listener:** This would break Phase 2's already-verified implementation. New card = new file = zero risk.
- **Guessing media_type from filename extension:** Always use the `contentType` from the Homey droptoken stream — it is authoritative. Fallback to `image/jpeg` only if contentType is absent.
- **Treating Claude models as potentially non-vision:** All Claude 3+ models (which is the entire supported list: haiku-4-5, sonnet-4-5, opus-4-5) support vision. No guard needed for Claude.
- **Using synchronous read on the droptoken stream:** The app is async. All I/O on the droptoken must use `await`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Base64 encoding | Custom encoder | `base64.standard_b64encode(bytes).decode()` | stdlib, zero overhead |
| Image bytes auto-encode for Ollama | Manual base64 call | Pass `bytes` directly to `images` param | Ollama `Image` class handles encoding automatically |
| Vision capability detection for Claude | Model allowlist | Skip check — all supported Claude models have vision | All three models in ClaudeProvider.MODELS are Claude 3+ |
| Image resizing/compression | PIL/Pillow pipeline | None — pass through as received | Homey snapshots are typically small; Anthropic auto-downsizes; Ollama handles any size |

**Key insight:** Both Anthropic and Ollama APIs absorb the image encoding complexity. The implementation is a thin adapter: read bytes from Homey droptoken → pass bytes to provider method → return text response.

---

## Common Pitfalls

### Pitfall 1: Droptoken is None
**What goes wrong:** User creates a Flow with `ask_ai_with_image` but does not attach an image token. `args["droptoken"]` is `None`. Calling `.get_stream()` on `None` raises `AttributeError`.
**Why it happens:** Droptokens are always nullable in Homey — the SDK documentation explicitly warns about this.
**How to avoid:** Guard: `if args.get("droptoken") is None: return {"response": "Error: No image provided. Connect an image token to this card."}`
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'get_stream'` in Homey logs.

### Pitfall 2: Non-vision Ollama model silently fails or returns garbled text
**What goes wrong:** User selects `llama3.2` (text-only) instead of `llama3.2-vision`. Ollama may accept the request and return text that ignores the image, or raise a `ResponseError`.
**Why it happens:** Ollama's REST API accepts the `images` field for any model but only vision models actually process it.
**How to avoid:** The `VISION_MODELS` prefix check in `OllamaProvider.chat_with_image()` catches this before making the API call.
**Warning signs:** Response text that makes no reference to the image content, or a `ResponseError` from Ollama.

### Pitfall 3: Media type mismatch with Anthropic
**What goes wrong:** Passing `media_type="image/jpg"` instead of `"image/jpeg"` causes a 400 API error from Anthropic.
**Why it happens:** Anthropic's API is strict about media type strings. Homey may produce `image/jpg` from some cameras.
**How to avoid:** Normalize: map `"image/jpg"` → `"image/jpeg"` before building the content block. The full supported list is: `image/jpeg`, `image/png`, `image/gif`, `image/webp`.
**Warning signs:** `APIStatusError 400: invalid media_type` in provider error return.

### Pitfall 4: Anthropic image size limit exceeded
**What goes wrong:** A high-resolution camera snapshot (>5MB) is rejected by the Anthropic API with a 413 or 400 error.
**Why it happens:** Anthropic enforces a 5MB per-image limit for API requests.
**How to avoid:** Check `len(image_bytes) > 5_000_000` before calling the API. Return a clear error if exceeded: `"Error: Image too large (>5MB). Use a lower-resolution snapshot."`
**Warning signs:** `APIStatusError 413` or request timeout on large images.

### Pitfall 5: Python droptoken API differs from JS SDK
**What goes wrong:** The actual Python SDK method is not `get_stream()` but something else, or the returned object structure differs from JS.
**Why it happens:** The Homey Python SDK documentation for image droptokens is sparse; it mirrors the JS SDK but exact Python-isms (dict vs object, sync vs async) are not confirmed in official Python-specific docs.
**How to avoid:** Wave 0 must include a smoke test: inspect `type(args["droptoken"])` and `dir(args["droptoken"])` in a live Homey run, or check the homey-sdk-python source in the Homey device's installed packages.
**Warning signs:** `AttributeError` on `.get_stream()` — try `.getStream()` (camelCase) or inspect available methods.

---

## Code Examples

Verified patterns from official sources:

### Claude — image content block (Python, async)
```python
# Source: https://platform.claude.com/docs/en/build-with-claude/vision
import base64

image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
response = await self._client.messages.create(
    model=model,
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,  # "image/jpeg"
                        "data": image_data,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }
    ],
)
return response.content[0].text
```

### Ollama — images field with bytes (Python, async)
```python
# Source: https://docs.ollama.com/capabilities/vision
# Source: https://deepwiki.com/ollama/ollama-python/4.3-multimodal-capabilities
response = await self._client.chat(
    model=model,
    messages=[
        {
            "role": "user",
            "content": prompt,
            "images": [image_bytes],  # bytes — SDK auto-encodes to base64
        }
    ],
)
return response.message.content
```

### Homey droptoken — reading image bytes (Python, expected pattern)
```python
# Source: Homey SDK tokens page (Python SDK section) — MEDIUM confidence
# Verify on live Homey; adjust based on actual object shape
droptoken = args.get("droptoken")
if droptoken is None:
    return {"response": "Error: No image provided."}
image_stream = await droptoken.get_stream()
image_bytes = image_stream["data"].read()
media_type = image_stream["meta"]["contentType"]
```

### ask_ai_with_image card registration in app.py
```python
# Pattern consistent with existing clear_conversation registration
image_card = self.homey.flow.get_action_card("ask_ai_with_image")

async def image_run_listener(args: dict, **kwargs) -> dict:
    # Guard: droptoken may be None
    droptoken = args.get("droptoken")
    if droptoken is None:
        return {"response": "Error: No image provided."}

    provider_name = args.get("provider")
    provider, name = self._get_provider(provider_name)
    if not provider:
        return {"response": f"Error: Provider '{name}' not configured."}

    prompt = args.get("prompt", "")
    if not prompt:
        return {"response": "Error: No prompt provided."}

    model_arg = args.get("model")
    model = model_arg.get("name") if isinstance(model_arg, dict) else str(model_arg or "")

    # Read image from droptoken
    image_stream = await droptoken.get_stream()
    image_bytes = image_stream["data"].read()
    media_type = image_stream["meta"]["contentType"] or "image/jpeg"

    # Normalize media_type
    if media_type == "image/jpg":
        media_type = "image/jpeg"

    response = await provider.chat_with_image(
        prompt=prompt,
        image_bytes=image_bytes,
        media_type=media_type,
        model=model,
    )
    return {"response": response}

image_card.register_run_listener(image_run_listener)

# Reuse existing model_autocomplete for image card
image_card.register_argument_autocomplete_listener("model", model_autocomplete)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate vision API endpoint | Vision via content blocks in standard messages API | Claude 3 launch (2024) | Single client, no extra auth |
| Ollama images as file paths on disk | Ollama images as bytes in message dict | ollama-python v0.3+ (2024) | No temp file needed |
| JS-only Homey apps | Python apps on Homey Pro 2023+ | Homey SDK Python support (2023) | Python providers fully supported |

**Deprecated/outdated:**
- Passing `role=system` in messages array for Claude: HTTP 400. Use top-level `system=` kwarg (already correct in Phase 2).
- Ollama `generate()` endpoint for vision: deprecated in favor of `chat()` with images.

---

## Open Questions

1. **Exact Python SDK method for reading image droptoken bytes**
   - What we know: JS SDK uses `await args.droptoken.getStream()` returning ReadableStream with `contentType` and `filename`. Python SDK page mentions `get_stream()` returning `{"meta": {...}, "data": ...}`.
   - What's unclear: The exact Python return type — is `data` a BytesIO, a bytes object, or an async generator? Is the method camelCase (`getStream`) or snake_case (`get_stream`)?
   - Recommendation: Wave 0 task must inspect the live object. Add a `self.log(f"droptoken type: {type(droptoken)}, attrs: {[a for a in dir(droptoken) if not a.startswith('_')]}")` smoke test in the run_listener before full implementation.

2. **Conversation history + images**
   - What we know: `ask_ai_with_image` has no `conversation_id` argument in the proposed design.
   - What's unclear: Should users be able to use image calls in a named session?
   - Recommendation: Out of scope for Phase 3. Keep the card stateless (single-turn only). Vision messages with history would require storing image bytes in ConversationStore, which has unbounded memory implications. Defer to v2.

3. **Ollama vision model enumeration**
   - What we know: Known vision models: llava, llava-phi3, moondream, qwen2.5vl, llama3.2-vision, bakllava, minicpm-v.
   - What's unclear: New vision models appear frequently. The prefix-match approach (`VISION_MODELS` set) may miss newly installed models.
   - Recommendation: Use prefix matching for safety but document that users should select vision-capable models. A future improvement could query model metadata via `ollama.show(model)` to check capabilities.

---

## Sources

### Primary (HIGH confidence)
- https://platform.claude.com/docs/en/build-with-claude/vision — Anthropic official vision docs, Python base64 content block example, media types, size limits
- https://docs.ollama.com/capabilities/vision — Ollama official vision docs, images parameter format
- https://deepwiki.com/ollama/ollama-python/4.3-multimodal-capabilities — Ollama Python library Image class, bytes handling, AsyncClient usage

### Secondary (MEDIUM confidence)
- https://apps.developer.homey.app/the-basics/flow/tokens — Homey official Flow tokens page; mentions Python `get_stream()` returning `{"meta": {...}, "data": ...}` but limited Python-specific detail
- https://apps.developer.homey.app/the-basics/flow/arguments — Homey official Flow arguments page; confirms `droptoken: ["image"]` JSON syntax
- https://apps.developer.homey.app/advanced/images — Homey Images advanced page; Python `set_stream()` / `set_url()` / `set_path()` confirmed, `get_stream()` mentioned

### Tertiary (LOW confidence — needs validation)
- Homey Community Forum — image droptoken handling is underspecified; no Python-specific example found in community
- Secondary WebFetch of Homey tokens page — Python `get_stream()` returning dict with `meta` and `data` keys; unverified against live SDK

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — No new dependencies; existing anthropic and ollama libraries fully support vision
- Claude vision API: HIGH — Official docs with complete Python examples
- Ollama vision API: HIGH — Official docs + library deepwiki confirm bytes-in-images-param approach
- Homey droptoken image Python API: MEDIUM/LOW — JS SDK pattern clear; Python exact shape unconfirmed; Wave 0 must verify
- Pitfalls: HIGH for API limits and media types (official docs); MEDIUM for non-vision model behavior (empirical)

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (stable APIs; Ollama vision model list evolves faster)
