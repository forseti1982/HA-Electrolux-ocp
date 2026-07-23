"""Token-Manager, der die OCP-Tokens im Home-Assistant Config-Entry persistiert."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pyelectroluxgroup.token_manager import TokenManager

from .const import CONF_ACCESS_TOKEN, CONF_API_KEY, CONF_REFRESH_TOKEN

_LOGGER = logging.getLogger(__name__)


class ConfigEntryTokenManager(TokenManager):
    """TokenManager, der Access-/Refresh-Token im Config-Entry speichert.

    Die OCP-API rotiert bei jedem ``token/refresh`` den Refresh-Token mit.
    Damit ein Neustart von Home Assistant nicht mit einem verbrauchten
    Refresh-Token startet, schreiben wir jedes Update zurück in den
    Config-Entry.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialisiere den Token-Manager aus dem Config-Entry."""
        # Bewusst KEIN super().__init__()-Aufruf: die Basisklasse würde sofort
        # update() (und damit ein Persistieren) auslösen. Wir setzen die
        # internen Felder direkt.
        self._hass = hass
        self._entry = entry
        self._api_key: str | None = entry.data[CONF_API_KEY]
        self._access_token: str = entry.data[CONF_ACCESS_TOKEN]
        self._refresh_token: str = entry.data[CONF_REFRESH_TOKEN]

    def update(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str | None = None,
    ) -> None:
        """Aktualisiere die Tokens und persistiere sie im Config-Entry."""
        super().update(access_token, refresh_token, api_key)

        new_data = {
            **self._entry.data,
            CONF_ACCESS_TOKEN: self._access_token,
            CONF_REFRESH_TOKEN: self._refresh_token,
        }
        if self._api_key is not None:
            new_data[CONF_API_KEY] = self._api_key

        # async_update_entry ist thread-/loop-sicher aufrufbar und schreibt
        # den Entry persistent. Wird aus dem Event-Loop (async) heraus gerufen.
        self._hass.config_entries.async_update_entry(self._entry, data=new_data)
        _LOGGER.debug("OCP-Tokens im Config-Entry aktualisiert")
