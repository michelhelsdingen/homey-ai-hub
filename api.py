"""Homey Web API endpoints for Homey AI Hub.

Exposes connection test and settings endpoints called by the settings page.
Note: Homey.set() from the frontend is broken in the Python SDK
(ManagerSettings.__on_settings_set signature mismatch), so we save
settings via API endpoints using homey.settings.set() server-side.
"""
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from homey.homey import Homey

from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider
from lib.providers.openai_provider import OpenAIProvider

SETTINGS_KEYS = [
    "ollama_url", "ollama_timeout", "claude_api_key", "claude_timeout",
    "openai_api_key", "openai_timeout",
    "default_provider", "default_model_ollama", "default_model_claude", "default_model_openai",
    "fallback_enabled", "fallback_order",
    "global_system_prompt", "max_history_turns",
]


async def _save_keys(homey: Homey, body: dict[str, Any], keys: list[str]) -> list[str]:
    """Save whitelisted keys from body to Homey settings. Returns saved key names."""
    saved = []
    for key in keys:
        if key in body and body[key] is not None:
            await homey.settings.set(key, body[key])
            saved.append(key)
    return saved


async def post_save_settings(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /save_settings — save all settings from the frontend."""
    saved = await _save_keys(homey, body, SETTINGS_KEYS)
    print(f"[api] Saved settings: {saved}")
    return {"success": True, "message": f"Saved {len(saved)} setting(s)"}


async def post_test_claude(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /test_claude — save Claude settings from body, then test connectivity."""
    await _save_keys(homey, body, ["claude_api_key", "claude_timeout"])

    claude_key = homey.settings.get("claude_api_key")
    if not claude_key:
        return {
            "success": False,
            "message": "Claude API key not configured. Enter your key and try again.",
        }
    timeout = float(homey.settings.get("claude_timeout") or ClaudeProvider.DEFAULT_TIMEOUT)
    provider = ClaudeProvider(api_key=claude_key, timeout=timeout)
    success, message = await provider.test_connection()
    return {"success": success, "message": message}


async def post_test_ollama(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /test_ollama — save Ollama settings from body, then test connectivity."""
    import httpx

    await _save_keys(homey, body, ["ollama_url", "ollama_timeout"])

    host = homey.settings.get("ollama_url") or OllamaProvider.DEFAULT_HOST
    # Normalize scheme to lowercase (iOS may capitalize Http://)
    if host.startswith("Http://"):
        host = "http://" + host[7:]
    elif host.startswith("Https://"):
        host = "https://" + host[8:]

    print(f"[api] post_test_ollama: testing {host}")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{host}/api/tags")
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            count = len(models)
            if count == 0:
                return {"success": True, "message": f"Connected to {host} — no models installed"}
            preview = ", ".join(models[:3])
            suffix = f" (+{count - 3} more)" if count > 3 else ""
            return {"success": True, "message": f"Ollama OK — {count} model(s): {preview}{suffix}"}
    except httpx.ConnectError:
        return {"success": False, "message": f"Cannot reach Ollama at {host} — is it running?"}
    except httpx.TimeoutException:
        return {"success": False, "message": f"Ollama at {host} timed out (5s)"}
    except Exception as e:
        return {"success": False, "message": f"Ollama error: {e}"}


async def post_test_openai(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /test_openai — save OpenAI settings from body, then test connectivity."""
    await _save_keys(homey, body, ["openai_api_key", "openai_timeout"])

    openai_key = homey.settings.get("openai_api_key")
    if not openai_key:
        return {
            "success": False,
            "message": "OpenAI API key not configured. Enter your key and try again.",
        }
    timeout = float(homey.settings.get("openai_timeout") or OpenAIProvider.DEFAULT_TIMEOUT)
    provider = OpenAIProvider(api_key=openai_key, timeout=timeout)
    success, message = await provider.test_connection()
    return {"success": success, "message": message}


async def get_ping(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """GET /ping — simple health check."""
    return {"success": True, "message": "pong"}


async def get_settings(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """GET /settings — load all settings for the frontend."""
    result = {}
    for key in SETTINGS_KEYS:
        result[key] = homey.settings.get(key)
    return result


async def post_webhook(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /webhook — receive external message and fire trigger card.

    Body: {"message": "...", "flag": "optional-tag"}
    This fires the 'webhook_received' trigger so Homey flows can react.
    """
    message = (body.get("message") or "").strip()
    flag = (body.get("flag") or "").strip()

    if not message:
        return {"success": False, "message": "No message provided"}

    print(f"[api] Webhook received: flag={flag!r}, message_len={len(message)}")

    # Fire the webhook trigger card directly — homey.flow returns the same registered instance
    trigger = homey.flow.get_trigger_card("webhook_received")
    await trigger.trigger({"message": message, "flag": flag})

    return {"success": True, "message": f"Webhook received (flag={flag})"}


async def post_run_tests(
    *, homey: Homey, query: dict[str, str], params: dict[str, str], body: dict[str, Any]
) -> dict:
    """POST /run_tests — run automated tests by calling app run listeners directly."""
    import time

    app = getattr(homey, "_app_instance", None)
    if not app:
        return {"success": False, "message": "App not ready", "results": []}

    results = []

    async def run_test(test_name: str, coro, validate_fn=None):
        """Run a test coroutine and record result."""
        start = time.time()
        try:
            data = await coro
            elapsed = round(time.time() - start, 1)

            response_text = ""
            if isinstance(data, dict):
                response_text = data.get("response", data.get("result", str(data)))
            else:
                response_text = str(data)

            if isinstance(response_text, str) and response_text.startswith("Error:"):
                results.append({"test": test_name, "status": "fail", "error": response_text, "time": elapsed})
                return

            if validate_fn and not validate_fn(response_text):
                results.append({"test": test_name, "status": "fail", "error": f"Validation failed. Response: {response_text[:200]}", "time": elapsed})
                return

            results.append({"test": test_name, "status": "pass", "response": response_text[:200], "time": elapsed})
        except Exception as e:
            elapsed = round(time.time() - start, 1)
            results.append({"test": test_name, "status": "fail", "error": str(e), "time": elapsed})

    # Test 1: Simple AI card — basic question (fastest possible)
    await run_test(
        "AI: simple question",
        app._run_ai({"prompt": "Reply with ONLY the number 4", "conversation_id": "", "system_prompt": ""}),
        validate_fn=lambda r: "4" in r,
    )

    # Test 2: Clear conversation (no AI call, instant)
    conv_id = f"test_{int(time.time())}"
    await run_test(
        "Clear conversation",
        app._clear_conversation({"conversation_id": conv_id}),
    )

    # Test 3: Custom AI card with explicit provider
    default_provider = homey.settings.get("default_provider") or "ollama"
    default_model = homey.settings.get(f"default_model_{default_provider}") or ""
    await run_test(
        f"AI Custom: {default_provider}",
        app._run_ai({
            "prompt": "Reply OK",
            "provider": default_provider,
            "model": {"name": default_model, "id": default_model} if default_model else "",
            "conversation_id": "",
            "system_prompt": "",
        }),
    )

    # Summary
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    total_time = sum(r.get("time", 0) for r in results)

    return {
        "success": failed == 0,
        "message": f"{passed}/{passed + failed} tests passed in {total_time:.1f}s",
        "results": results,
    }


__all__ = [
    "post_save_settings", "post_test_claude", "post_test_ollama", "post_test_openai",
    "get_ping", "get_settings", "post_webhook", "post_run_tests",
]
