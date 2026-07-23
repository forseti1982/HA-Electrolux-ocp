"""Basis-Entität + Hilfsfunktionen für Electrolux OCP."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from pyelectroluxgroup.appliance import Appliance

from .const import DOMAIN, MANUFACTURER
from .coordinator import ElectroluxDataUpdateCoordinator


def get_reported(appliance: Appliance) -> dict[str, Any]:
    """Gib das gemeldete State-Dict eines Geräts robust zurück.

    Die OCP-API liefert den Zustand unter ``properties.reported``. Struktur und
    genaue Schlüssel sind geräteabhängig (# VERIFY). Diese Funktion greift
    defensiv zu und liefert im Zweifel ein leeres Dict.
    """
    try:
        state = appliance.state_data or {}
        props = state.get("properties", {}) or {}
        reported = props.get("reported", {}) or {}
        if isinstance(reported, dict):
            return reported
    except Exception:  # noqa: BLE001
        pass
    return {}


def get_capabilities(appliance: Appliance) -> dict[str, Any]:
    """Gib das Capabilities-Dict eines Geräts robust zurück.

    # VERIFY: Die genaue Capabilities-Struktur der OCP-API ist geräteabhängig.
    Beobachtet: flaches Dict property_name -> {access, type, values?, min?, max?,
    step?}. Diese Funktion greift defensiv zu.
    """
    try:
        caps = appliance.capabilities_data or {}
        if isinstance(caps, dict):
            return caps
    except Exception:  # noqa: BLE001
        pass
    return {}


def is_writable(cap: Any) -> bool:
    """Prüfe, ob eine Capability schreibbar ist (access enthält 'write')."""
    if not isinstance(cap, dict):
        return False
    access = str(cap.get("access", "")).lower()
    return "write" in access


def humanize(key: str) -> str:
    """Wandle einen camelCase/snake_case-Property-Key in einen lesbaren Namen."""
    import re

    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", key.replace("_", " "))
    return spaced.strip().capitalize()


class ElectroluxEntity(CoordinatorEntity[ElectroluxDataUpdateCoordinator]):
    """Basisklasse für alle Electrolux-Entitäten."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
    ) -> None:
        """Initialisiere die Entität."""
        super().__init__(coordinator)
        self._appliance_id = appliance_id

    @property
    def appliance(self) -> Appliance | None:
        """Gib das zugehörige Appliance-Objekt zurück (oder None)."""
        return self.coordinator.data.get(self._appliance_id)

    @property
    def available(self) -> bool:
        """Verfügbar, wenn Coordinator ok und Gerät verbunden ist."""
        if not super().available:
            return False
        appliance = self.appliance
        if appliance is None:
            return False
        try:
            state = appliance.state_data or {}
            connection = state.get("connectionState")
            if connection is not None:
                return str(connection).lower() in ("connected", "online", "true")
        except Exception:  # noqa: BLE001
            return True
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Geräte-Info für die Device-Registry."""
        appliance = self.appliance
        name = self._appliance_id
        model: str | None = None
        sw: str | None = None
        info: dict[str, Any] = {}
        if appliance is not None:
            name = appliance.initial_data.get("applianceName") or self._appliance_id
            info = appliance.info_data or {}
            model = info.get("model") or appliance.initial_data.get("applianceType")

        return DeviceInfo(
            identifiers={(DOMAIN, self._appliance_id)},
            name=name,
            manufacturer=info.get("brand") or MANUFACTURER,
            model=model,
            serial_number=info.get("serialNumber"),
        )
