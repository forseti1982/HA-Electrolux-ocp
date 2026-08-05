"""Sensor-Plattform für Electrolux OCP.

Sensoren werden dynamisch aus den gemeldeten Geräte-Properties erzeugt. Für
erkannte Schlüssel (siehe const.KNOWN_SENSOR_KEYS) werden device_class, Einheit
und Icon gesetzt; unbekannte skalare Properties werden als generische Sensoren
angelegt. Bool-Werte übernimmt die binary_sensor-Plattform.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    KNOWN_BINARY_KEYS,
    KNOWN_SENSOR_KEYS,
    TOTAL_INCREASING_KEYS,
    TRANSLATED_SENSOR_KEYS,
)
from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import ElectroluxEntity, get_reported, humanize, slugify_key

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectroluxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richte die Sensor-Entitäten ein."""
    coordinator = entry.runtime_data
    entities: list[ElectroluxSensor] = []

    for appliance_id, appliance in coordinator.data.items():
        reported = get_reported(appliance)
        for key, value in reported.items():
            # Bool -> binary_sensor; komplexe Werte -> überspringen.
            if isinstance(value, bool):
                continue
            if key in KNOWN_BINARY_KEYS:
                continue
            if not isinstance(value, (str, int, float)):
                continue
            entities.append(ElectroluxSensor(coordinator, appliance_id, key))

    async_add_entities(entities)


class ElectroluxSensor(ElectroluxEntity, SensorEntity):
    """Ein einzelner gemeldeter Property-Wert als Sensor."""

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
        key: str,
    ) -> None:
        """Initialisiere den Sensor."""
        super().__init__(coordinator, appliance_id)
        self._key = key
        self._attr_unique_id = f"{appliance_id}_{key}"
        # i18n: Bei bekanntem Slug übersetzt HA Name + Enum-States selbst.
        # unique_id bleibt am ROH-Key hängen (Automationen). Kein _attr_name
        # setzen, sonst gewinnt dieser über die Übersetzung.
        slug = slugify_key(key)
        if slug in TRANSLATED_SENSOR_KEYS:
            self._attr_translation_key = slug
        else:
            self._attr_name = humanize(key)

        meta = KNOWN_SENSOR_KEYS.get(key)
        if meta is not None:
            device_class, unit, icon, diagnostic = meta
            if device_class:
                self._attr_device_class = device_class
            if unit:
                self._attr_native_unit_of_measurement = unit
                # Kumulative Verbrauchswerte -> TOTAL_INCREASING (Langzeitstatistik),
                # sonst MEASUREMENT.
                self._attr_state_class = (
                    SensorStateClass.TOTAL_INCREASING
                    if key in TOTAL_INCREASING_KEYS
                    else SensorStateClass.MEASUREMENT
                )
            if icon:
                self._attr_icon = icon
            if diagnostic:
                self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Gib den aktuellen Wert der Property zurück."""
        appliance = self.appliance
        if appliance is None:
            return None
        return get_reported(appliance).get(self._key)
