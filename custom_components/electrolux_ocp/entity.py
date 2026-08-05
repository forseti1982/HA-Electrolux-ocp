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


def build_command(key: str, value: Any) -> dict[str, Any]:
    """Baue den OCP-Command-Body aus einem (evtl. slash-verschachtelten) Key.

    Die Electrolux-OCP-API erwartet VERSCHACHTELTE Container: ein Capability-Key
    wie ``userSelections/extraSilentOption`` MUSS als
    ``{"userSelections": {"extraSilentOption": value}}`` gesendet werden. Ein
    flacher Body ``{"userSelections/extraSilentOption": value}`` wird von der API
    abgelehnt (``COMMAND_VALIDATION_ERROR: Capability not found``) und aeussert
    sich am Geraet als HTTP 500 — auch bei fuer das Programm ERLAUBTEN Optionen.

    Top-Level-Keys ohne ``/`` (z. B. ``executeCommand``, ``waterHardness``)
    bleiben flach. Mehrsegmentige Pfade werden generisch von innen nach aussen
    verschachtelt.

    Beleg (verifiziert 2026-08):
      * pyelectroluxgroup==0.2.7 appliance.send_command -> sendet ``json=command``
        unveraendert an ``appliances/{id}/command``.
      * TTLucian/ha-electrolux RELEASE_NOTES_v3.4.8 + switch.py/select.py/button.py:
        ``command = {entity_source: {entity_attr: value}}`` (Split am ``/``),
        flacher Body wird von der API mit "Capability not found" abgelehnt.
    """
    parts = [p for p in str(key).split("/") if p != ""]
    if not parts:
        return {}
    body: Any = value
    for part in reversed(parts):
        body = {part: body}
    return body


def get_nested(data: Any, key: str) -> Any:
    """Lies einen (evtl. slash-verschachtelten) Wert aus dem reported-State.

    Der reported-State spiegelt die Container-Struktur der API: ein Key wie
    ``userSelections/extraSilentOption`` liegt als ``reported["userSelections"]
    ["extraSilentOption"]``. Ein flaches ``reported.get(key)`` mit dem Slash-Key
    liefert daher faelschlich ``None``. Diese Funktion navigiert die Segmente.
    """
    cur: Any = data
    for part in str(key).split("/"):
        if part == "":
            continue
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


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


def slugify_key(key: str) -> str:
    """Leite aus einem Property-/Capability-Key einen stabilen HA-translation_key ab.

    camelCase wird an Grossbuchstaben getrennt, alles kleingeschrieben und jede
    Folge nicht-alphanumerischer Zeichen (inkl. ``/``) zu ``_`` zusammengefasst.
    Ergebnis ist ein gültiger HA-Slug (``a-z0-9_``), der zu den Einträgen in
    ``translations/*.json`` passt. Die ``unique_id`` bleibt hiervon unberührt —
    sie leitet sich weiterhin aus dem ROH-Key ab (Automationen hängen daran).

    Beispiele:
        ``applianceState`` -> ``appliance_state``
        ``userSelections/extraPowerOption`` -> ``user_selections_extra_power_option``
        ``programUID`` -> ``program_u_i_d``
    """
    import re

    spaced = re.sub(r"(?<!^)(?=[A-Z])", "_", key)
    lowered = spaced.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "_", lowered)
    return collapsed.strip("_")


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
