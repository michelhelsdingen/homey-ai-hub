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

SETTINGS_KEYS = [
    "ollama_url", "ollama_timeout", "claude_api_key", "claude_timeout",
    "default_provider", "global_system_prompt", "max_history_turns",
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


__all__ = [
    "post_save_settings", "post_test_claude", "post_test_ollama",
    "get_ping", "get_settings",
]
