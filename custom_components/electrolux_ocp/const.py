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
# Monotoner Zeitstempel jedes Token-Schreibvorgangs (Rotation ODER Re-Auth).
# Dient dem "frischester gewinnt"-Abgleich zwischen Config-Entry (debounced)
# und dem redundanten Sofort-Store beim Setup — schliesst den Neustart-Race.
CONF_TOKEN_TS: Final = "token_ts"

# Redundanter, SOFORT persistierter Token-Store (übersteht den Neustart-Race,
# weil async_update_entry nur verzögert auf die Platte schreibt).
TOKEN_STORE_VERSION: Final = 1
TOKEN_STORE_KEY: Final = "electrolux_ocp_tokens"

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
CARD_VERSION: Final = "0.2.2"
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

# Verbrauchs-Keys: kumulativ → SensorStateClass.TOTAL_INCREASING (Langzeit-
# statistik; vermeidet die "energy + measurement"-Warnung von Home Assistant).
TOTAL_INCREASING_KEYS: Final = {"waterConsumption", "energyConsumption"}

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

# ---------------------------------------------------------------------------
# Mehrsprachigkeit (i18n): translation_keys, für die Name- UND State-Über-
# setzungen in translations/*.json hinterlegt sind.
#
# Die Slugs entstehen aus slugify_key(roh_key). Ist der Slug einer Entität hier
# enthalten, wird _attr_translation_key gesetzt (HA übersetzt Name + Enum-States
# in die Benutzersprache). Sonst greift der humanize()-Fallback (kein
# _attr_translation_key), damit unbekannte Properties trotzdem einen lesbaren
# Namen behalten. unique_ids bleiben in JEDEM Fall unverändert.
#
# # VERIFY: Die exakten Enum-Werte/Keys sind geräte-/firmwareabhängig und ohne
# echte Tokens nicht live verifiziert. Fehlt eine Übersetzung, zeigt HA den
# rohen Enum-Wert — also nie schlechter als bisher, nur unübersetzt.
# ---------------------------------------------------------------------------

TRANSLATED_SENSOR_KEYS: Final[set[str]] = {
    "appliance_state",
    "appliance_mode",
    "cycle_phase",
    "water_hardness",
    "end_of_cycle_sound",
    "display_on_floor",
    "handle_free_door_opening",
    "network_interface_always_on",
    "remote_control",
    "display_light",
    "connectivity_state",
    "rinse_aid_level",
    "start_time",
    "time_to_end",
    "total_cycle_counter",
    "cpv",
}

TRANSLATED_BINARY_KEYS: Final[set[str]] = {
    "connectivity",
    "door_state",
    "extra_info_temperature_enable",
    "key_tone",
    "pre_select_last",
    "water_hardness_sensor_enable",
    # Fest angelegte Alarm-Sensoren aus reported['alerts'].
    "salt_missing",
    "rinse_aid_low",
}

TRANSLATED_SELECT_KEYS: Final[set[str]] = {
    "water_hardness",
    "end_of_cycle_sound",
    "display_on_floor",
    "handle_free_door_opening",
    "network_interface_always_on",
    "execute_command",
    "program_u_i_d",
}

TRANSLATED_SWITCH_KEYS: Final[set[str]] = {
    "key_tone",
    "network_interface_always_on",
    "water_hardness_sensor_enable",
    "user_selections_auto_door_opener",
    "user_selections_extra_power_option",
    "user_selections_extra_silent_option",
    "user_selections_glass_care_option",
    "user_selections_one_rack_option",
    "user_selections_sanitize_option",
    "user_selections_spray_zone_option",
    "user_selections_xtra_dry_option",
    "user_selections_zone_clean_option",
}
