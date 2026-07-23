"""Konstanten für die Electrolux OCP Developer-API Integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "electrolux_ocp"

# Config-Entry-Felder
CONF_API_KEY: Final = "api_key"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Poll-Intervall.
# Hinweis: Die Electrolux Developer-API ist rate-limitiert. Referenz-Clients
# (homebridge-electrolux-devices) warnen ausdrücklich vor Poll-Intervallen
# unter 120 Sekunden. Default daher konservativ, aber vom User anpassbar.
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
RECOMMENDED_MIN_SCAN_INTERVAL: Final = 120
MIN_UPDATE_INTERVAL: Final = timedelta(seconds=MIN_SCAN_INTERVAL)

MANUFACTURER: Final = "Electrolux Group"

# Setup-URL für die Anleitung im Config-Flow
DASHBOARD_URL: Final = "https://developer.electrolux.one/dashboard"

# Mitgelieferte Lovelace-Karte (wird beim Setup automatisch registriert).
# CARD_VERSION dient dem Cache-Busting — bei Änderung an der Karte erhöhen.
CARD_VERSION: Final = "0.1.0"
CARD_FILENAME: Final = "electrolux-ocp-card.js"
CARD_URL_PATH: Final = "/electrolux_ocp/electrolux-ocp-card.js"

# ---------------------------------------------------------------------------
# Kuratierte Metadaten für bekannte Geräte-Eigenschaften ("reported"-Keys).
#
# # VERIFY: Die exakten Property-Schlüssel der OCP-API sind geräte- und
# firmwareabhängig und konnten ohne echte Tokens NICHT live verifiziert werden.
# Die Integration erzeugt Entitäten DYNAMISCH aus den tatsächlich gemeldeten
# Properties; diese Tabelle liefert lediglich schönere Metadaten (Einheit,
# device_class, Icon), wo der Schlüssel erkannt wird. Unbekannte Properties
# werden trotzdem als generische Sensoren angelegt.
# ---------------------------------------------------------------------------

# key -> (device_class, unit, icon, entity_category_is_diagnostic)
KNOWN_SENSOR_KEYS: Final[dict[str, tuple[str | None, str | None, str | None, bool]]] = {
    # Geschirrspüler / generisch
    "applianceState": (None, None, "mdi:state-machine", False),
    "applianceMode": (None, None, "mdi:tune", False),
    "cyclePhase": (None, None, "mdi:progress-clock", False),
    "displayTemperature": ("temperature", "°C", None, False),
    "targetTemperatureC": ("temperature", "°C", None, False),
    "waterHardness": (None, None, "mdi:water-percent", True),
    "waterSoftenerMode": (None, None, "mdi:water-percent", True),
    "rinseAidLevel": (None, None, "mdi:cup-water", False),
    "saltLevel": (None, None, "mdi:shaker-outline", False),
    "programUID": (None, None, "mdi:playlist-play", False),
    # Zeitwerte (Sekunden) -> als duration dargestellt
    "timeToEnd": ("duration", "s", "mdi:timer-sand", False),
    "runningTime": ("duration", "s", "mdi:timer", False),
    "startTime": ("duration", "s", "mdi:timer-play", False),
    "remainingTime": ("duration", "s", "mdi:timer-sand", False),
    # Verbrauch
    "waterConsumption": ("water", "L", None, True),
    "energyConsumption": ("energy", "kWh", None, True),
    # Waschmaschine / Trockner (generisch)
    "spinSpeed": (None, "rpm", "mdi:rotate-right", False),
    "temperature": ("temperature", "°C", None, False),
}

# Property-Keys, die als binary_sensor behandelt werden.
# key -> (device_class, icon, entity_category_is_diagnostic)
KNOWN_BINARY_KEYS: Final[dict[str, tuple[str | None, str | None, bool]]] = {
    "doorState": ("door", None, False),
    "doorOpen": ("door", None, False),
    "doorLock": ("lock", None, False),
    "rinseAidState": ("problem", "mdi:cup-water", False),
    "saltState": ("problem", "mdi:shaker-outline", False),
    "runningState": ("running", None, False),
}

# Property-Werte, die auf Türzustand "offen" hindeuten (# VERIFY: genaue Enums)
DOOR_OPEN_VALUES: Final = {"OPEN", "OPENED", "DOOR_OPEN", True, "ON"}
# Werte, die "Warnung/nachfüllen" bedeuten (# VERIFY)
PROBLEM_TRUE_VALUES: Final = {"LOW", "EMPTY", "NEEDS_REFILL", "TRUE", True, "ON"}
