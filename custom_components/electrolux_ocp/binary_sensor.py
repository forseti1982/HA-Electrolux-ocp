"""Binary-Sensor-Plattform für Electrolux OCP.

Erzeugt binäre Sensoren für bool-Properties sowie für erkannte Schlüssel wie
Türzustand oder Salz-/Klarspüler-Warnungen. Zusätzlich immer ein
Konnektivitäts-Sensor pro Gerät.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DOOR_OPEN_VALUES,
    KNOWN_BINARY_KEYS,
    PROBLEM_TRUE_VALUES,
    TRANSLATED_BINARY_KEYS,
)
from .coordinator import ElectroluxConfigEntry, ElectroluxDataUpdateCoordinator
from .entity import ElectroluxEntity, get_reported, humanize, slugify_key

_LOGGER = logging.getLogger(__name__)

# Fest angelegte Alarm-Sensoren aus dem gemeldeten ``alerts``-Array. Sie werden
# IMMER erzeugt (nicht nur bei aktivem Alarm), damit Automationen und die
# Lovelace-Karte stabil darauf verweisen können.
# (translation_key, unique_id-Suffix, Alarm-Code)
ALERT_SENSORS: tuple[tuple[str, str, str], ...] = (
    ("salt_missing", "alert_salt_missing", "DISH_ALARM_SALT_MISSING"),
    ("rinse_aid_low", "alert_rinse_aid_low", "DISH_ALARM_RINSE_AID_LOW"),
)


def _alert_codes(appliance: Any) -> set[str]:
    """Aktive Alarm-Codes aus ``reported['alerts']`` robust als Menge lesen.

    Das Feld kann fehlen, ``None`` oder eine Liste aus Strings ODER Objekten
    (mit ``code``/``alert``/``name``) sein. Im Zweifel: leere Menge.
    """
    if appliance is None:
        return set()
    raw = get_reported(appliance).get("alerts")
    if not isinstance(raw, list):
        return set()
    codes: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            codes.add(item)
        elif isinstance(item, dict):
            code = item.get("code") or item.get("alert") or item.get("name")
            if isinstance(code, str):
                codes.add(code)
    return codes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ElectroluxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Richte die Binary-Sensor-Entitäten ein."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []

    for appliance_id, appliance in coordinator.data.items():
        # Konnektivität immer anbieten.
        entities.append(ElectroluxConnectivitySensor(coordinator, appliance_id))

        # Alarm-Sensoren (Salz fehlt / Klarspüler niedrig) IMMER anlegen.
        for translation_key, uid_suffix, alert_code in ALERT_SENSORS:
            entities.append(
                ElectroluxAlertSensor(
                    coordinator, appliance_id, translation_key, uid_suffix, alert_code
                )
            )

        reported = get_reported(appliance)
        for key, value in reported.items():
            if key in KNOWN_BINARY_KEYS or isinstance(value, bool):
                entities.append(
                    ElectroluxBinarySensor(coordinator, appliance_id, key)
                )

    async_add_entities(entities)


class ElectroluxConnectivitySensor(ElectroluxEntity, BinarySensorEntity):
    """Konnektivitäts-Sensor (connectionState)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator, appliance_id: str) -> None:
        super().__init__(coordinator, appliance_id)
        self._attr_unique_id = f"{appliance_id}_connectivity"
        # Name kommt aus der Übersetzung (translation_key "connectivity"),
        # damit er der HA-Sprache folgt. Kein _attr_name mehr (überschriebe sie).

    @property
    def available(self) -> bool:
        # Konnektivitäts-Sensor soll auch dann verfügbar sein, wenn das Gerät
        # gerade offline ist (er zeigt genau das an).
        from homeassistant.helpers.update_coordinator import CoordinatorEntity

        return CoordinatorEntity.available.fget(self) and self.appliance is not None

    @property
    def is_on(self) -> bool | None:
        appliance = self.appliance
        if appliance is None:
            return None
        state = appliance.state_data or {}
        connection = state.get("connectionState")
        if connection is None:
            return None
        return str(connection).lower() in ("connected", "online", "true")


class ElectroluxBinarySensor(ElectroluxEntity, BinarySensorEntity):
    """Binärer Sensor aus einer gemeldeten Property."""

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
        key: str,
    ) -> None:
        super().__init__(coordinator, appliance_id)
        self._key = key
        self._attr_unique_id = f"{appliance_id}_{key}"
        # i18n: bekannter Slug -> HA übersetzt den Namen; sonst humanize-Fallback.
        slug = slugify_key(key)
        if slug in TRANSLATED_BINARY_KEYS:
            self._attr_translation_key = slug
        else:
            self._attr_name = humanize(key)

        meta = KNOWN_BINARY_KEYS.get(key)
        if meta is not None:
            device_class, icon, diagnostic = meta
            if device_class:
                self._attr_device_class = BinarySensorDeviceClass(device_class)
            if icon:
                self._attr_icon = icon
            if diagnostic:
                self._attr_entity_category = EntityCategory.DIAGNOSTIC

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
        # Erkannte Enums für Tür / Warnungen interpretieren (# VERIFY Enums).
        if self._attr_device_class == BinarySensorDeviceClass.DOOR:
            return _match(value, DOOR_OPEN_VALUES)
        if self._attr_device_class == BinarySensorDeviceClass.PROBLEM:
            return _match(value, PROBLEM_TRUE_VALUES)
        # Fallback: Wahrheitswert aus String ableiten.
        return _match(value, {"ON", "TRUE", "OPEN", "ACTIVE", "RUNNING"})


class ElectroluxAlertSensor(ElectroluxEntity, BinarySensorEntity):
    """Fester Alarm-Sensor: on, wenn ein bestimmter Code in ``alerts`` steht.

    device_class=problem => Home Assistant stellt on/off als Problem/OK dar. Der
    Name kommt aus der Übersetzung (translation_key), folgt also der HA-Sprache.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: ElectroluxDataUpdateCoordinator,
        appliance_id: str,
        translation_key: str,
        uid_suffix: str,
        alert_code: str,
    ) -> None:
        super().__init__(coordinator, appliance_id)
        self._alert_code = alert_code
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{appliance_id}_{uid_suffix}"

    @property
    def is_on(self) -> bool:
        return self._alert_code in _alert_codes(self.appliance)


def _match(value: Any, truthy: set[Any]) -> bool:
    """Prüfe, ob ein Wert (case-insensitiv bei Strings) als "on" gilt."""
    if value in truthy:
        return True
    if isinstance(value, str):
        return value.upper() in {v.upper() for v in truthy if isinstance(v, str)}
    return False
