"""Select-Plattform für Electrolux OCP.

Erzeugt Auswahl-Entitäten für schreibbare Capabilities mit einer festen
Werteliste (z. B. Betriebsmodus). Die Zuordnung basiert auf dem Capabilities-
Dokument des Geräts.

# VERIFY: Schreib-Kommandos und die genaue Capability-Struktur wurden ohne
echte Tokens NICHT live getestet. Der Kommando-Body wird als {key: value}
gesendet (siehe Appliance.send_command in pyelectroluxgroup).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import TRANSLATED_SELECT_KEYS
from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import (
    ElectroluxEntity,
    build_command,
    get_capabilities,
    get_nested,
    get_reported,
    humanize,
    is_writable,
    slugify_key,
)

_LOGGER = logging.getLogger(__name__)

# Interne/versteckte Options-Keys (Test-/Diagnose-Programme), die NIE in der
# Bedienoberflaeche erscheinen duerfen. Jeder Options-Key, der eines dieser
# Fragmente enthaelt (z. B. MACHINE_SETTINGS_HIDDEN_TEST), wird aus den
# Select-Optionen entfernt -> verschwindet aus dem nativen Dropdown UND aus den
# Programm-Pills der Karte. Ist der aktuell gemeldete Wert eine gefilterte
# Option, liefert current_option sauber None (kein Crash, siehe unten).
HIDDEN_OPTION_FRAGMENTS: tuple[str, ...] = ("_HIDDEN", "HIDDEN_TEST")


def _is_hidden_option(value: Any) -> bool:
    """True, wenn der Options-Key als intern/versteckt gilt (Fragment-Match)."""
    up = str(value).upper()
    return any(frag in up for frag in HIDDEN_OPTION_FRAGMENTS)


def _values_list(cap: dict[str, Any]) -> list[str] | None:
    """Extrahiere die Optionsliste aus einer Capability, sonst None.

    Versteckte/interne Options-Keys (siehe HIDDEN_OPTION_FRAGMENTS) werden
    herausgefiltert, bevor die Liste an die Entitaet geht.
    """
    values = cap.get("values")
    raw: list[str] | None = None
    if isinstance(values, dict) and values:
        raw = list(values.keys())
    elif isinstance(values, list) and values:
        raw = [str(v) for v in values]
    if raw is None:
        return None
    filtered = [v for v in raw if not _is_hidden_option(v)]
    return filtered or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectroluxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richte die Select-Entitäten ein."""
    coordinator = entry.runtime_data
    entities: list[ElectroluxSelect] = []

    for appliance_id, appliance in coordinator.data.items():
        for key, cap in get_capabilities(appliance).items():
            if not is_writable(cap):
                continue
            options = _values_list(cap) if isinstance(cap, dict) else None
            if options is None:
                continue
            entities.append(
                ElectroluxSelect(coordinator, appliance_id, key, options)
            )

    async_add_entities(entities)


class ElectroluxSelect(ElectroluxEntity, SelectEntity):
    """Schreibbare Auswahl-Capability."""

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
        key: str,
        options: list[str],
    ) -> None:
        super().__init__(coordinator, appliance_id)
        self._key = key
        self._attr_unique_id = f"{appliance_id}_{key}_select"
        # i18n: bekannter Slug -> HA übersetzt Name UND Optionen (state.<ENUM>);
        # sonst humanize-Fallback (Optionen bleiben roh).
        slug = slugify_key(key)
        if slug in TRANSLATED_SELECT_KEYS:
            self._attr_translation_key = slug
        else:
            self._attr_name = humanize(key)
        self._attr_options = options

    @property
    def current_option(self) -> str | None:
        appliance = self.appliance
        if appliance is None:
            return None
        # Slash-Keys liegen im reported-State verschachtelt (siehe get_nested).
        value = get_nested(get_reported(appliance), self._key)
        if value is None:
            return None
        value = str(value)
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        """Sende das Kommando zum Setzen der Option."""
        appliance = self.appliance
        if appliance is None:
            raise HomeAssistantError("Gerät nicht verfügbar")
        try:
            # OCP erwartet verschachtelte Container fuer Slash-Keys, z. B.
            # {"userSelections": {"programUID": option}}. Flacher Body -> Ablehnung.
            await appliance.send_command(build_command(self._key, option))
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(
                f"Kommando fehlgeschlagen: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
