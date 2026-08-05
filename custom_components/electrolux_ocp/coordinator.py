"""DataUpdateCoordinator für die Electrolux OCP Developer-API."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import NoReturn

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from pyelectroluxgroup.api import ElectroluxHubAPI
from pyelectroluxgroup.appliance import Appliance

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .token_manager import ConfigEntryTokenManager
from .util import scrub_secrets

_LOGGER = logging.getLogger(__name__)

# Timeout pro API-Interaktion (Sekunden).
API_TIMEOUT = 30

# Generische, secret-freie UI-Meldungen (Detail nur auf Debug, gescrubbt).
_MSG_AUTH = "Authentifizierung fehlgeschlagen — Tokens prüfen"
_MSG_RATE = "Rate-Limit der Electrolux-API erreicht (HTTP 429) — Poll-Intervall erhöhen"
_MSG_TIMEOUT = "Zeitüberschreitung bei der Electrolux-API"

type ElectroluxConfigEntry = ConfigEntry["ElectroluxDataUpdateCoordinator"]


class ElectroluxDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Appliance]]):
    """Koordiniert das Polling aller Geräte eines OCP-Accounts."""

    config_entry: ElectroluxConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ElectroluxConfigEntry) -> None:
        """Initialisiere den Coordinator."""
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._token_manager = ConfigEntryTokenManager(hass, entry)
        self.api: ElectroluxHubAPI | None = None
        # Gerät-Objekte werden über den Lebenszyklus wiederverwendet, damit
        # Geräte-Info/Capabilities nur einmal (statt bei jedem Poll) geladen
        # werden. Nur der State wird pro Zyklus neu geholt (rate-limit-schonend).
        self._appliances: dict[str, Appliance] = {}

    def _raise_client_error(self, err: ClientResponseError, context: str) -> NoReturn:
        """Bilde einen HTTP-Fehler auf eine generische HA-Exception ab.

        Rohe Fremd-Fehlertexte werden NICHT in die UI gegeben; Detail landet nur
        (gescrubbt) im Debug-Log. In die Meldung fließt nur der Status-Code.
        """
        if err.status in (401, 403):
            raise ConfigEntryAuthFailed(_MSG_AUTH) from err
        if err.status == 429:
            raise UpdateFailed(_MSG_RATE) from err
        _LOGGER.debug("HTTP-Fehler bei %s: %s", context, scrub_secrets(str(err)))
        raise UpdateFailed(f"Fehler bei {context} (HTTP {err.status})") from err

    def _raise_auth_from_value_error(self, err: ValueError) -> NoReturn:
        """pyelectroluxgroup wirft ValueError bei fehlgeschlagenem Token-Refresh."""
        _LOGGER.debug("Token-Refresh fehlgeschlagen: %s", scrub_secrets(str(err)))
        raise ConfigEntryAuthFailed(_MSG_AUTH) from err

    async def _async_setup(self) -> None:
        """Einmalige Einrichtung: API-Client bauen und Geräteliste laden."""
        session = async_get_clientsession(self.hass)
        # HÄRTUNG: vor dem ersten API-Aufruf die frischesten Tokens wählen
        # (Config-Entry vs. redundanter Sofort-Store) — fängt den Neustart-Race
        # ab, bei dem ein rotierter Refresh-Token sonst verloren ginge.
        await self._token_manager.async_prime()
        try:
            async with asyncio.timeout(API_TIMEOUT):
                self.api = ElectroluxHubAPI(session, self._token_manager)
                appliances = await self.api.async_get_appliances()
        except ClientResponseError as err:
            self._raise_client_error(err, "Laden der Geräteliste")
        except ValueError as err:
            self._raise_auth_from_value_error(err)
        except TimeoutError as err:
            raise UpdateFailed(_MSG_TIMEOUT) from err
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Unerwarteter Setup-Fehler: %s", scrub_secrets(str(err)))
            raise UpdateFailed("Unerwarteter Fehler beim Setup") from err

        self._appliances = {appliance.id: appliance for appliance in appliances}
        _LOGGER.debug("OCP: %d Gerät(e) gefunden", len(self._appliances))

    async def _async_update_data(self) -> dict[str, Appliance]:
        """Aktualisiere den Zustand aller bekannten Geräte."""
        if not self._appliances:
            # Fallback, falls _async_setup keine Geräte lieferte.
            return {}

        for appliance in self._appliances.values():
            try:
                async with asyncio.timeout(API_TIMEOUT):
                    await appliance.async_update()
            except ClientResponseError as err:
                self._raise_client_error(err, "Aktualisieren eines Geräts")
            except ValueError as err:
                self._raise_auth_from_value_error(err)
            except TimeoutError as err:
                raise UpdateFailed(_MSG_TIMEOUT) from err
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug(
                    "Unerwarteter Update-Fehler: %s", scrub_secrets(str(err))
                )
                raise UpdateFailed("Unerwarteter Fehler beim Aktualisieren") from err

        return dict(self._appliances)
