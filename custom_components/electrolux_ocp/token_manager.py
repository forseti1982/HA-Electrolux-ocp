"""Token-Manager, der die OCP-Tokens restart-fest persistiert.

Die OCP-API rotiert bei jedem ``token/refresh`` den Refresh-Token mit. Der
frühere Ansatz schrieb den neuen Token nur via ``async_update_entry`` zurück —
das aber **verzögert** (debounced) auf die Platte. Ein Neustart kurz nach einer
Rotation startete daher mit dem alten, bereits verbrauchten Refresh-Token →
HTTP 400/401 → Zwangs-Reauth.

Härtung (mehrschichtig, damit das nie wieder passiert):
  1. Redundanter, SOFORT geschriebener Token-Store (``helpers.storage.Store``),
     der nicht debounced ist und den Neustart-Race übersteht.
  2. Zeitstempel-basierter „frischester gewinnt"-Abgleich beim Setup
     (``async_prime``): der jüngere von Config-Entry vs. Store gewinnt, der
     ältere wird nachgezogen. So überlebt eine Rotation auch dann, wenn der
     Entry-Write beim Neustart verloren ging — und eine frische Re-Auth
     überschreibt trotzdem korrekt einen alten Store.
  3. Leere/None-Tokens werden NIE persistiert (schützt vor Lib-Ausrutschern).
  4. Persistieren läuft thread-/loop-sicher (``call_soon_threadsafe``), falls
     die Bibliothek ``update()`` je aus einem Executor-Thread aufruft.
  5. Store-Lesefehler sind nicht fatal (Fallback auf Config-Entry) + klare Logs.

Keine Secrets im Log.
"""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from pyelectroluxgroup.token_manager import TokenManager

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_TS,
    TOKEN_STORE_KEY,
    TOKEN_STORE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class ConfigEntryTokenManager(TokenManager):
    """TokenManager mit doppelter, restart-fester Token-Persistenz."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialisiere aus dem Config-Entry (ohne super().__init__, das sofort
        persistieren würde) und lege den redundanten Sofort-Store an."""
        self._hass = hass
        self._entry = entry
        self._api_key: str | None = entry.data[CONF_API_KEY]
        self._access_token: str = entry.data[CONF_ACCESS_TOKEN]
        self._refresh_token: str = entry.data[CONF_REFRESH_TOKEN]
        self._ts: float = float(entry.data.get(CONF_TOKEN_TS, 0.0))
        self._store: Store = Store(
            hass, TOKEN_STORE_VERSION, f"{TOKEN_STORE_KEY}_{entry.entry_id}"
        )

    # -- interne Helfer ------------------------------------------------------
    def _snapshot(self) -> dict:
        return {
            CONF_API_KEY: self._api_key,
            CONF_ACCESS_TOKEN: self._access_token,
            CONF_REFRESH_TOKEN: self._refresh_token,
            CONF_TOKEN_TS: self._ts,
        }

    @callback
    def _write_entry(self) -> None:
        new_data = {
            **self._entry.data,
            CONF_ACCESS_TOKEN: self._access_token,
            CONF_REFRESH_TOKEN: self._refresh_token,
            CONF_TOKEN_TS: self._ts,
        }
        if self._api_key is not None:
            new_data[CONF_API_KEY] = self._api_key
        self._hass.config_entries.async_update_entry(self._entry, data=new_data)

    @callback
    def _persist(self) -> None:
        """Beide Ziele schreiben: Config-Entry (Wahrheit für Config-Flow) UND
        den Sofort-Store (delay=0 → nicht debounced, übersteht Neustart)."""
        self._write_entry()
        self._store.async_delay_save(self._snapshot, 0)

    # -- Setup-Abgleich ------------------------------------------------------
    async def async_prime(self) -> None:
        """Vor dem ersten API-Aufruf: frischeste Tokens wählen (Entry vs. Store).

        Schliesst den Neustart-Race: ging der Entry-Write einer Rotation beim
        Neustart verloren, hat der Sofort-Store den neueren Token — der gewinnt.
        Eine frische Re-Auth (Entry-Zeitstempel = jetzt) gewinnt umgekehrt gegen
        einen alten Store.
        """
        try:
            stored = await self._store.async_load()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Electrolux: Token-Store nicht lesbar, nutze Config-Entry")
            _LOGGER.debug("Store-Lesefehler: %s", err)
            stored = None

        entry_ts = float(self._entry.data.get(CONF_TOKEN_TS, 0.0))
        store_ts = float(stored.get(CONF_TOKEN_TS, 0.0)) if stored else -1.0

        if stored and store_ts > entry_ts and stored.get(CONF_REFRESH_TOKEN):
            # Store ist frischer → adoptieren und Entry nachziehen.
            self._api_key = stored.get(CONF_API_KEY) or self._api_key
            self._access_token = stored[CONF_ACCESS_TOKEN]
            self._refresh_token = stored[CONF_REFRESH_TOKEN]
            self._ts = store_ts
            self._write_entry()
            _LOGGER.info(
                "Electrolux: frischeren Token aus Sofort-Store wiederhergestellt "
                "(Neustart-Race abgefangen)"
            )
        else:
            # Config-Entry ist Wahrheit (Erstlauf oder frische Re-Auth).
            if self._ts <= 0.0:
                self._ts = time.time()
                self._write_entry()
            await self._store.async_save(self._snapshot())

    # -- von pyelectroluxgroup bei jeder Rotation aufgerufen -----------------
    def update(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str | None = None,
    ) -> None:
        """Tokens aktualisieren + doppelt (Entry + Sofort-Store) persistieren."""
        # Schicht 3: niemals leere Tokens speichern.
        if not access_token or not refresh_token:
            _LOGGER.warning("Electrolux: leeren Token im update() ignoriert")
            return

        super().update(access_token, refresh_token, api_key)
        self._ts = time.time()

        # Schicht 4: loop-sicher persistieren (auch aus Executor-Thread).
        try:
            asyncio.get_running_loop()
            on_loop = True
        except RuntimeError:
            on_loop = False
        if on_loop:
            self._persist()
        else:
            self._hass.loop.call_soon_threadsafe(self._persist)

        _LOGGER.debug("OCP-Tokens rotiert + doppelt persistiert (Entry + Store)")
