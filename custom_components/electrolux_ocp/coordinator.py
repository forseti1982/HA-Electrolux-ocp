"""DataUpdateCoordinator für die Electrolux OCP Developer-API."""

from __future__ import annotations

import logging
from datetime import timedelta

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

_LOGGER = logging.getLogger(__name__)

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

    async def _async_setup(self) -> None:
        """Einmalige Einrichtung: API-Client bauen und Geräteliste laden."""
        session = async_get_clientsession(self.hass)
        try:
            self.api = ElectroluxHubAPI(session, self._token_manager)
            appliances = await self.api.async_get_appliances()
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    "Authentifizierung fehlgeschlagen — Tokens prüfen"
                ) from err
            raise UpdateFailed(f"Fehler beim Laden der Geräteliste: {err}") from err
        except ValueError as err:
            # pyelectroluxgroup wirft ValueError, wenn der Token-Refresh scheitert.
            raise ConfigEntryAuthFailed(str(err)) from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unerwarteter Fehler beim Setup: {err}") from err

        self._appliances = {appliance.id: appliance for appliance in appliances}
        _LOGGER.debug("OCP: %d Gerät(e) gefunden", len(self._appliances))

    async def _async_update_data(self) -> dict[str, Appliance]:
        """Aktualisiere den Zustand aller bekannten Geräte."""
        if not self._appliances:
            # Fallback, falls _async_setup keine Geräte lieferte.
            return {}

        for appliance in self._appliances.values():
            try:
                await appliance.async_update()
            except ClientResponseError as err:
                if err.status in (401, 403):
                    raise ConfigEntryAuthFailed(
                        "Authentifizierung fehlgeschlagen — Tokens prüfen"
                    ) from err
                if err.status == 429:
                    raise UpdateFailed(
                        "Rate-Limit der Electrolux-API erreicht (HTTP 429) — "
                        "Poll-Intervall erhöhen"
                    ) from err
                raise UpdateFailed(
                    f"Fehler beim Aktualisieren von {appliance.id}: {err}"
                ) from err
            except ValueError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
            except Exception as err:  # noqa: BLE001
                raise UpdateFailed(
                    f"Unerwarteter Fehler bei {appliance.id}: {err}"
                ) from err

        return dict(self._appliances)
