"""Registrierung der mitgelieferten Lovelace-Karte (electrolux-ocp-card).

Beim Setup der Integration wird die Karten-JS als statischer Pfad ausgeliefert
und als Frontend-Modul eingehängt. Dadurch ist `type: custom:electrolux-ocp-card`
ohne manuelles Hinzufügen einer Lovelace-Ressource verfügbar — installieren =
Daten + Grafik.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import CARD_FILENAME, CARD_URL_PATH, CARD_VERSION, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Prozessweiter Guard: Static-Path und Extra-JS-URL nur EINMAL registrieren,
# auch wenn mehrere Config-Entries (mehrere Konten) eingerichtet werden.
_REGISTERED_KEY = f"{DOMAIN}_frontend_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Registriere die Karte einmalig für die gesamte HA-Instanz."""
    if hass.data.get(_REGISTERED_KEY):
        return

    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    # Dateisystem-Zugriff im Executor, um den Event-Loop nicht zu blockieren.
    if not await hass.async_add_executor_job(card_path.is_file):
        _LOGGER.warning("Karten-Datei nicht gefunden, überspringe: %s", card_path)
        return

    # Import bewusst lokal, um die http-Komponente nur bei Bedarf zu laden.
    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(card_path), True)]
    )

    # add_extra_js_url hängt das Modul als Frontend-Ressource ein. Cache-Busting
    # über den Versions-Query, damit Browser eine neue Kartenversion laden.
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={CARD_VERSION}")

    hass.data[_REGISTERED_KEY] = True
    _LOGGER.debug("Electrolux-OCP-Karte registriert unter %s", CARD_URL_PATH)

    # Hinweis: Weder async_register_static_paths noch add_extra_js_url bieten eine
    # stabile öffentliche API zum sauberen Entfernen. Da die Registrierung
    # prozessweit und über alle Entries geteilt ist, wird sie bewusst NICHT beim
    # Unload eines einzelnen Entries zurückgenommen (das würde andere Entries
    # brechen). Sie ist idempotent und überlebt bis zum HA-Neustart.
