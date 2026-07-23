"""Switch-Plattform für Electrolux OCP.

Erzeugt Schalter für schreibbare boolesche Capabilities.

# VERIFY: Schreib-Kommandos und Capability-Struktur wurden ohne echte Tokens
NICHT live getestet. Der Kommando-Body wird als {key: bool} gesendet.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import (
    ElectroluxEntity,
    get_capabilities,
    get_reported,
    humanize,
    is_writable,
)

_LOGGER = logging.getLogger(__name__)


def _is_boolean_cap(cap: dict[str, Any]) -> bool:
    """Prüfe, ob eine Capability ein boolescher Schalter ist."""
    cap_type = str(cap.get("type", "")).lower()
    if cap_type in ("boolean", "bool"):
        return True
    values = cap.get("values")
    if isinstance(values, dict):
        keys = {str(k).upper() for k in values}
        # z. B. {"ON","OFF"} oder {"TRUE","FALSE"}
        return keys in ({"ON", "OFF"}, {"TRUE", "FALSE"}, {"ENABLED", "DISABLED"})
    return False


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectroluxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richte die Switch-Entitäten ein."""
    coordinator = entry.runtime_data
    entities: list[ElectroluxSwitch] = []

    for appliance_id, appliance in coordinator.data.items():
        for key, cap in get_capabilities(appliance).items():
            if not is_writable(cap) or not isinstance(cap, dict):
                continue
            if not _is_boolean_cap(cap):
                continue
            entities.append(ElectroluxSwitch(coordinator, appliance_id, key))

    async_add_entities(entities)


class ElectroluxSwitch(ElectroluxEntity, SwitchEntity):
    """Schreibbare boolesche Capability als Schalter."""

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
        key: str,
    ) -> None:
        super().__init__(coordinator, appliance_id)
        self._key = key
        self._attr_unique_id = f"{appliance_id}_{key}_switch"
        self._attr_name = humanize(key)

    @property
    def is_on(self) -> bool | None:
        appliance = self.appliance
        if appliance is None:
            return None
        value: Any = get_reported(appliance).get(self._key)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return str(value).upper() in ("ON", "TRUE", "ENABLED")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._send(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._send(False)

    async def _send(self, state: bool) -> None:
        appliance = self.appliance
        if appliance is None:
            raise HomeAssistantError("Gerät nicht verfügbar")
        try:
            await appliance.send_command({self._key: state})
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Kommando fehlgeschlagen: {err}") from err
        await self.coordinator.async_request_refresh()
