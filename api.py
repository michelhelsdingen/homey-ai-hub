"""Homey Web API endpoints for Homey AI Hub.

Exposes connection test endpoints called by the settings page.
Method naming convention: post_{path_with_hyphens_as_underscores}
"""
from homey import app as homey_app

from lib.providers.claude import ClaudeProvider
from lib.providers.ollama_provider import OllamaProvider


class Api(homey_app.Api):
    async def post_test_claude(self, body: dict, **kwargs) -> dict:
        """POST /test-claude — test Claude API connectivity."""
        claude_key = self.homey.settings.get("claude_api_key")
        if not claude_key:
            return {
                "success": False,
                "message": "Claude API key not configured. Enter your key and save first.",
            }
        timeout = float(self.homey.settings.get("claude_timeout") or ClaudeProvider.DEFAULT_TIMEOUT)
        provider = ClaudeProvider(api_key=claude_key, timeout=timeout)
        success, message = await provider.test_connection()
        return {"success": success, "message": message}

    async def post_test_ollama(self, body: dict, **kwargs) -> dict:
        """POST /test-ollama — test Ollama server connectivity."""
        host = self.homey.settings.get("ollama_url") or OllamaProvider.DEFAULT_HOST
        timeout = float(
            self.homey.settings.get("ollama_timeout") or OllamaProvider.DEFAULT_TIMEOUT
        )
        provider = OllamaProvider(host=host, timeout=timeout)
        success, message = await provider.test_connection()
        return {"success": success, "message": message}


homey_export = Api
