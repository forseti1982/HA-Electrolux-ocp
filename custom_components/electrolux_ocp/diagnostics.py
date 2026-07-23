"""Diagnostics für Electrolux OCP — mit Redaktion aller Secrets/PII."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_API_KEY, CONF_REFRESH_TOKEN
from .coordinator import ElectroluxConfigEntry
from .entity import get_capabilities, get_reported

# Felder, die niemals in Diagnostics/Logs auftauchen dürfen.
# Achtung: async_redact_data redaktiert nur WERTE anhand ihrer Keys, niemals
# Dict-Keys selbst. Deshalb werden die Geräte unten mit anonymen Keys
# ("appliance_0", …) statt der echten Appliance-ID indexiert.
TO_REDACT = {
    CONF_API_KEY,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    "accessToken",
    "refreshToken",
    "api_key",
    "applianceId",
    "deviceId",
    "serialNumber",
    "serial_number",
    "pnc",
    "mac",
    "macAddress",
    "address",
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
    # Sortiert + enumeriert: keine echte Geräte-/Serien-ID als Dict-Key (die von
    # async_redact_data nicht erfasst würde). Reihenfolge deterministisch.
    for idx, (_appliance_id, appliance) in enumerate(
        sorted((coordinator.data or {}).items())
    ):
        appliances[f"appliance_{idx}"] = {
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
