"""Homey REST API client for device control and flow management.

Uses the internal Homey Web API with an owner API token.
Requires the 'homey:manager:api' permission in app.json.
"""
import httpx


class HomeyAPI:
    """Thin async wrapper around Homey's local REST API."""

    def __init__(self, token: str, base_url: str) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {self._token}"}

    async def get_devices(self) -> dict:
        """Get all devices. Returns dict keyed by device ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self._base_url}/api/manager/devices/device",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def set_capability(self, device_id: str, capability: str, value) -> None:
        """Set a capability value on a device (e.g. onoff=True, dim=0.5)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.put(
                f"{self._base_url}/api/manager/devices/device/{device_id}/capability/{capability}",
                headers=self._headers,
                json={"value": value},
            )
            r.raise_for_status()

    async def get_flows(self) -> dict:
        """Get all basic flows. Returns dict keyed by flow ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self._base_url}/api/manager/flow/flow",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def get_advanced_flows(self) -> dict:
        """Get all advanced flows. Returns dict keyed by flow ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self._base_url}/api/manager/flow/advancedflow",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()

    async def trigger_flow(self, flow_id: str) -> None:
        """Trigger a basic flow by ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self._base_url}/api/manager/flow/flow/{flow_id}/trigger",
                headers=self._headers,
            )
            r.raise_for_status()

    async def trigger_advanced_flow(self, flow_id: str) -> None:
        """Trigger an advanced flow by ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{self._base_url}/api/manager/flow/advancedflow/{flow_id}/trigger",
                headers=self._headers,
            )
            r.raise_for_status()

    async def get_zones(self) -> dict:
        """Get all zones. Returns dict keyed by zone ID."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{self._base_url}/api/manager/zones/zone",
                headers=self._headers,
            )
            r.raise_for_status()
            return r.json()
