"""Diagnostics für Electrolux OCP — mit Redaktion aller Secrets/PII."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_API_KEY, CONF_REFRESH_TOKEN
from .coordinator import ElectroluxConfigEntry
from .entity import get_capabilities, get_reported

# Felder, die niemals in Diagnostics/Logs auftauchen dürfen.
TO_REDACT = {
    CONF_API_KEY,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    "accessToken",
    "refreshToken",
    "api_key",
    "serialNumber",
    "serial_number",
    "pnc",
    "email",
    "userId",
    "unique_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ElectroluxConfigEntry
) -> dict[str, Any]:
    """Erzeuge einen redaktierten Diagnose-Dump."""
    coordinator = entry.runtime_data

    appliances: dict[str, Any] = {}
    for appliance_id, appliance in (coordinator.data or {}).items():
        appliances[appliance_id] = {
            "type": appliance.initial_data.get("applianceType"),
            "info": appliance.info_data,
            "capabilities": get_capabilities(appliance),
            "reported": get_reported(appliance),
            "connectionState": (appliance.state_data or {}).get("connectionState"),
            "status": (appliance.state_data or {}).get("status"),
        }

    data = {
        "entry_data": dict(entry.data),
        "entry_options": dict(entry.options),
        "appliances": appliances,
    }
    return async_redact_data(data, TO_REDACT)
