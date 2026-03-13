"""Smart home AI controller — orchestrates device control via tool use."""
from __future__ import annotations

import json
from lib.homey_api import HomeyAPI
from lib.providers.base import LLMProvider, ToolRoundResult

MAX_TOOL_ROUNDS = 5

# Normalized tool definitions (provider-agnostic)
SMART_HOME_TOOLS = [
    {
        "name": "control_zone",
        "description": "Control all matching devices in a zone. Use this to turn off all lights in a room, set all thermostats, etc. This is the preferred tool for zone-level commands like 'turn off the lights in the office'.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone_name": {"type": "string", "description": "The zone/room name (e.g. 'Kantoor', 'Woonkamer', 'Slaapkamer')"},
                "device_class": {"type": "string", "description": "Filter by device class: light, thermostat, sensor, socket, speaker, tv, etc. Use 'light' for lamps/lights."},
                "capability": {"type": "string", "description": "The capability to set (e.g. onoff, dim, target_temperature)"},
                "value": {"description": "The value to set. Boolean for onoff, number 0-1 for dim, number for temperature."},
            },
            "required": ["zone_name", "device_class", "capability", "value"],
        },
    },
    {
        "name": "control_device",
        "description": "Control a specific single device by its ID. Use control_zone for room-level commands instead.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string", "description": "The device ID from the device list"},
                "capability": {"type": "string", "description": "The capability ID to set (e.g. onoff, dim, target_temperature)"},
                "value": {"description": "The value to set. Boolean for onoff, number 0-1 for dim, number for temperature."},
            },
            "required": ["device_id", "capability", "value"],
        },
    },
    {
        "name": "trigger_flow",
        "description": "Trigger/run a Homey Flow or Advanced Flow by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "flow_id": {"type": "string", "description": "The flow ID from the flow list"},
                "is_advanced": {"type": "boolean", "description": "True if this is an advanced flow, false for basic flow"},
            },
            "required": ["flow_id"],
        },
    },
]


# Capabilities the AI can actually control (skip read-only sensors)
CONTROLLABLE_CAPS = {
    "onoff", "dim", "light_hue", "light_saturation", "light_temperature", "light_mode",
    "target_temperature", "thermostat_mode", "volume_set", "volume_mute",
    "channel_up", "channel_down", "locked", "windowcoverings_set",
    "windowcoverings_state", "button",
}

# Read-only caps worth showing status for (compact)
STATUS_CAPS = {
    "measure_temperature", "measure_humidity", "measure_power", "measure_battery",
    "alarm_motion", "alarm_contact", "alarm_smoke", "alarm_water",
}


def _build_device_context_from_cache(devices: dict, zones: dict) -> str:
    """Build compact device context from pre-fetched data."""
    zone_names: dict[str, str] = {zid: z.get("name", "Unknown") for zid, z in zones.items()}

    # Group devices by zone for cleaner context
    by_zone: dict[str, list[str]] = {}
    for did, dev in devices.items():
        if not dev.get("available", False):
            continue
        name = dev.get("name", "Unknown")
        zone = zone_names.get(dev.get("zone", ""), "Unknown")
        dev_class = dev.get("class", "")
        caps = dev.get("capabilitiesObj", {})

        cap_parts = []
        for cap_id, cap_data in caps.items():
            if cap_id in CONTROLLABLE_CAPS or cap_id in STATUS_CAPS:
                val = cap_data.get("value")
                cap_parts.append(f"{cap_id}={val}")

        if not cap_parts:
            continue
        line = f"  - {name} [{dev_class}] id:{did} | {', '.join(cap_parts)}"
        by_zone.setdefault(zone, []).append(line)

    lines = ["## Devices by Zone\n"]
    for zone, devs in sorted(by_zone.items()):
        lines.append(f"**{zone}:**")
        lines.extend(devs)
    lines.append(f"\n## Available Zones: {', '.join(sorted(zone_names.values()))}")
    return "\n".join(lines)


async def build_flow_context(api: HomeyAPI) -> str:
    """Fetch flows and return a compact context string for the AI."""
    lines = ["## Available Flows\n"]

    try:
        flows = await api.get_flows()
        for fid, flow in flows.items():
            if not flow.get("enabled", True):
                continue
            name = flow.get("name", "Unknown")
            lines.append(f"- **{name}** (id: `{fid}`, type: basic)")
    except Exception:
        pass

    try:
        adv_flows = await api.get_advanced_flows()
        for fid, flow in adv_flows.items():
            if not flow.get("enabled", True):
                continue
            name = flow.get("name", "Unknown")
            lines.append(f"- **{name}** (id: `{fid}`, type: advanced)")
    except Exception:
        pass

    return "\n".join(lines)


def build_system_prompt(device_context: str, flow_context: str, custom_prompt: str | None = None) -> str:
    """Build the system prompt with device/flow context."""
    parts = [
        "You are a smart home controller with DIRECT access to real devices via tools.",
        "You MUST use the provided tools (control_zone, control_device, trigger_flow) to execute commands.",
        "NEVER say you cannot control devices — you CAN and MUST use the tools.",
        "NEVER suggest the user do it manually — YOU do it with the tools.",
        "After using tools, confirm what you did in a brief response.",
        "Respond in the same language as the user's message.",
    ]
    if custom_prompt:
        parts.append(f"\nAdditional instructions: {custom_prompt}")
    parts.append(f"\n{device_context}")
    parts.append(f"\n{flow_context}")
    return "\n".join(parts)


def _coerce_value(value, capability: str):
    """Coerce string values from LLMs to the correct type for Homey capabilities."""
    if isinstance(value, str):
        low = value.lower().strip()
        if low in ("true", "on", "yes", "1"):
            return True
        if low in ("false", "off", "no", "0"):
            return False
        try:
            return float(low) if "." in low else int(low)
        except ValueError:
            pass
    return value


async def execute_tool(api: HomeyAPI, name: str, arguments: dict, device_cache: dict | None = None, zone_cache: dict | None = None) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "control_zone":
        zone_name = (arguments.get("zone_name") or "").strip().lower()
        device_class = (arguments.get("device_class") or "").strip().lower()
        capability = arguments.get("capability", "")
        value = _coerce_value(arguments.get("value"), capability)

        devices = device_cache or await api.get_devices()
        zones = zone_cache or await api.get_zones()

        # Find matching zone(s) by fuzzy name match
        zone_ids = [zid for zid, z in zones.items() if zone_name in z.get("name", "").lower()]
        if not zone_ids:
            return json.dumps({"success": False, "error": f"No zone found matching '{zone_name}'. Available zones: {[z.get('name') for z in zones.values()]}"})

        controlled = []
        errors = []
        for did, dev in devices.items():
            if not dev.get("available", False):
                continue
            if dev.get("zone") not in zone_ids:
                continue
            if device_class and dev.get("class", "").lower() != device_class:
                continue
            if capability not in dev.get("capabilities", []):
                continue
            try:
                await api.set_capability(did, capability, value)
                controlled.append(dev.get("name", did))
            except Exception as e:
                errors.append(f"{dev.get('name', did)}: {e}")

        if not controlled and not errors:
            return json.dumps({"success": False, "error": f"No devices found in zone '{zone_name}' with class '{device_class}' and capability '{capability}'"})

        result = {"success": True, "controlled": controlled, "count": len(controlled)}
        if errors:
            result["errors"] = errors
        return json.dumps(result)

    if name == "control_device":
        device_id = arguments.get("device_id", "")
        capability = arguments.get("capability", "")
        value = _coerce_value(arguments.get("value"), capability)
        try:
            await api.set_capability(device_id, capability, value)
            return json.dumps({"success": True, "message": f"Set {capability}={value} on device {device_id}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    elif name == "trigger_flow":
        flow_id = arguments.get("flow_id", "")
        is_advanced = arguments.get("is_advanced", False)
        try:
            if is_advanced:
                await api.trigger_advanced_flow(flow_id)
            else:
                await api.trigger_flow(flow_id)
            return json.dumps({"success": True, "message": f"Triggered flow {flow_id}"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return json.dumps({"error": f"Unknown tool: {name}"})


async def run_smart_home(
    provider: LLMProvider,
    api: HomeyAPI,
    prompt: str,
    model: str,
    system_prompt_extra: str | None = None,
    log=None,
) -> tuple[str, list[str]]:
    """Run the full smart home control loop.

    Returns (ai_response, actions_taken).
    """
    # Fetch devices/zones once, reuse for context + tool execution
    device_cache = await api.get_devices()
    zone_cache = await api.get_zones()

    device_context = _build_device_context_from_cache(device_cache, zone_cache)
    flow_context = await build_flow_context(api)
    system = build_system_prompt(device_context, flow_context, system_prompt_extra)

    messages: list[dict] = [{"role": "user", "content": prompt}]
    actions_taken: list[str] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        if log:
            log(f"smart_home: round {round_num + 1}, messages={len(messages)}")

        try:
            result: ToolRoundResult = await provider.chat_with_tools_round(
                messages=messages,
                model=model,
                tools=SMART_HOME_TOOLS,
                system_prompt=system,
            )
        except NotImplementedError:
            return "Error: This provider/model does not support smart home control (no tool use).", []
        except Exception as e:
            return f"Error: AI call failed: {e}", []

        # Append the AI's response messages to history
        messages.extend(result.raw_messages)

        # If text response → check for refusal (model ignoring tools)
        if result.text is not None:
            refusal_phrases = [
                "kan niet", "kan geen", "cannot", "can't", "don't have access",
                "no access", "niet mogelijk", "unable to", "geen toegang",
                "niet in staat", "zelf doen", "do it yourself", "manually",
            ]
            is_refusal = any(p in result.text.lower() for p in refusal_phrases)
            if is_refusal and round_num == 0:
                # Model refused on first try — nudge it to use tools
                if log:
                    log(f"smart_home: model refused, retrying with nudge")
                messages.append({"role": "assistant", "content": result.text})
                messages.append({"role": "user", "content": "You have real tools connected to real devices. Use the control_zone or control_device tool NOW. Do not refuse."})
                continue
            return result.text, actions_taken

        # Execute tool calls
        for tc in result.tool_calls:
            if log:
                log(f"smart_home: tool={tc.name}, args={tc.arguments}")
            tool_result = await execute_tool(api, tc.name, tc.arguments, device_cache=device_cache, zone_cache=zone_cache)
            actions_taken.append(f"{tc.name}({tc.arguments})")

            # Append tool result to messages
            result_msgs = provider.format_tool_result(tc.id, tc.name, tool_result)
            messages.extend(result_msgs)

    return "Error: Too many tool call rounds. The AI could not complete the task.", actions_taken
