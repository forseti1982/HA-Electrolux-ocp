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
    ACTIVE_APPLIANCE_STATES,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    IDLE_SCAN_INTERVAL,
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

# HÄRTUNG 18.08.2026 — warum es diese Schwellen gibt:
# Vorher führte EIN einziger 401/403 sofort zu ConfigEntryAuthFailed, also zur
# Zwangs-Neuanmeldung von Hand. Damit reichte ein einzelner Aussetzer der
# Gegenstelle, um die Integration bis zum nächsten Handgriff lahmzulegen —
# obwohl der Refresh-Token gültig war. Genau das ist Martins wöchentliches
# "schon wieder neu verbinden".
#
# 403 ist bei dieser API KEIN sicheres Zeichen für falsche Zugangsdaten: die
# Electrolux-Entwickler-API kennt dokumentierte Kontingente, und ein
# erschöpftes Kontingent antwortet ebenfalls mit 403. Ein 403 als
# "Anmeldedaten kaputt" zu deuten war die eigentliche Fehldiagnose.
#
# Neue Regel: erst nach MEHREREN aufeinanderfolgenden Fehlern wird die
# Neuanmeldung verlangt. Ein einzelner Aussetzer führt nur noch zu
# UpdateFailed — die Entitäten werden kurz unavailable, HA versucht es von
# selbst wieder, und niemand muss etwas tun.
_AUTH_FAILURES_BEFORE_REAUTH = 3   # 401: recht eindeutig, aber nie beim ersten Mal
_FORBIDDEN_FAILURES_BEFORE_REAUTH = 10  # 403: meist Kontingent, sehr geduldig

# Die Fehlerserien MÜSSEN ausserhalb des Coordinator-Objekts leben. Grund:
# Scheitert bereits das Setup, verwirft HA den Coordinator und baut bei jedem
# Wiederholungsversuch einen neuen — ein Zähler am Objekt startet dann jedes Mal
# bei null und erreicht die Schwelle NIE. Bei wirklich abgelaufenen Zugangsdaten
# würde die Integration endlos wiederholen und nie zur Neuanmeldung auffordern.
# Schlüssel ist die entry_id; der Inhalt überlebt einen HA-Neustart bewusst
# nicht — nach einem Neustart soll wieder mit voller Geduld begonnen werden.
_STREAKS: dict[str, dict[str, int]] = {}


def _gemeldeter_zustand(appliance: Appliance) -> str:
    """Lies applianceState aus dem gemeldeten Zustand des Geraets.

    Bewusst hier lokal und NICHT aus entity.py importiert: entity.py importiert
    seinerseits den Coordinator, ein Import in die Gegenrichtung erzeugt einen
    Ringschluss und die Integration laedt gar nicht mehr. Genau das ist beim
    Einbau am 18.08. passiert und wurde vor dem Festschreiben bemerkt.
    """
    try:
        props = (appliance.state_data or {}).get("properties", {}) or {}
        reported = props.get("reported", {}) or {}
        return str(reported.get("applianceState") or "").upper()
    except Exception:  # noqa: BLE001
        return ""

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
        # Aufeinanderfolgende Auth-Fehler. Wird bei jedem erfolgreichen Poll
        # zurückgesetzt; erst ab den Schwellen oben wird die Neuanmeldung
        # verlangt. Vorher genügte ein einziger Fehler.
        # Der eingestellte Takt gilt als SCHNELLER Takt (waehrend Betrieb).
        self._fast_interval = scan_interval
        self._streaks = _STREAKS.setdefault(
            entry.entry_id, {"auth": 0, "forbidden": 0}
        )

    def _raise_client_error(self, err: ClientResponseError, context: str) -> NoReturn:
        """Bilde einen HTTP-Fehler auf eine HA-Exception ab.

        Rohe Fremd-Fehlertexte gehen NICHT in die UI; Detail nur gescrubbt ins
        Log. Entscheidend ist die Unterscheidung, die vorher fehlte: ein
        einzelner 401/403 ist ein Aussetzer, kein Grund für eine Neuanmeldung
        von Hand.
        """
        if err.status == 401:
            self._streaks["auth"] += 1
            # WARNING statt debug: bei der Neuanmeldung am 18.08. stand im
            # Protokoll KEIN Grund. Ab jetzt ist der Status immer sichtbar.
            _LOGGER.warning(
                "Electrolux: HTTP 401 bei %s (%d. Mal in Folge, Neuanmeldung ab %d)",
                context, self._streaks["auth"], _AUTH_FAILURES_BEFORE_REAUTH,
            )
            if self._streaks["auth"] >= _AUTH_FAILURES_BEFORE_REAUTH:
                raise ConfigEntryAuthFailed(_MSG_AUTH) from err
            raise UpdateFailed(f"Vorübergehend abgewiesen bei {context} (HTTP 401)") from err

        if err.status == 403:
            self._streaks["forbidden"] += 1
            _LOGGER.warning(
                "Electrolux: HTTP 403 bei %s (%d. Mal in Folge). 403 bedeutet bei "
                "dieser API meist ein erschöpftes Tageskontingent, nicht falsche "
                "Zugangsdaten — Poll-Intervall prüfen. Neuanmeldung erst ab %d.",
                context, self._streaks["forbidden"], _FORBIDDEN_FAILURES_BEFORE_REAUTH,
            )
            if self._streaks["forbidden"] >= _FORBIDDEN_FAILURES_BEFORE_REAUTH:
                raise ConfigEntryAuthFailed(_MSG_AUTH) from err
            raise UpdateFailed(_MSG_RATE) from err

        if err.status == 429:
            raise UpdateFailed(_MSG_RATE) from err

        _LOGGER.debug("HTTP-Fehler bei %s: %s", context, scrub_secrets(str(err)))
        raise UpdateFailed(f"Fehler bei {context} (HTTP {err.status})") from err

    def _raise_auth_from_value_error(self, err: ValueError) -> NoReturn:
        """Ein ValueError ist NICHT automatisch ein Anmeldeproblem.

        pyelectroluxgroup wirft ValueError sowohl beim fehlgeschlagenen
        Token-Refresh als auch bei unerwarteten Antworten (z. B. kaputtes JSON
        bei einer Störung der Gegenstelle). Vorher führte JEDER ValueError zur
        Zwangs-Neuanmeldung — eine einzelne fehlerhafte Antwort reichte also,
        um die Integration bis zum Handgriff auszuknocken.
        """
        text = scrub_secrets(str(err)).lower()
        ist_token_problem = any(
            wort in text for wort in ("token", "refresh", "auth", "credential", "unauthor")
        )
        if not ist_token_problem:
            _LOGGER.warning(
                "Electrolux: unerwartete Antwort (kein Anmeldeproblem): %s", text
            )
            raise UpdateFailed("Unerwartete Antwort der Electrolux-API") from err

        self._streaks["auth"] += 1
        _LOGGER.warning(
            "Electrolux: Token-Refresh fehlgeschlagen (%d. Mal in Folge, "
            "Neuanmeldung ab %d): %s",
            self._streaks["auth"], _AUTH_FAILURES_BEFORE_REAUTH, text,
        )
        if self._streaks["auth"] >= _AUTH_FAILURES_BEFORE_REAUTH:
            raise ConfigEntryAuthFailed(_MSG_AUTH) from err
        raise UpdateFailed("Token-Refresh vorübergehend fehlgeschlagen") from err

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

        self._takt_anpassen()

        # Erfolgreicher Durchlauf — Fehlerserien zurücksetzen. Ohne das würden
        # sich vereinzelte Aussetzer über Tage zur Zwangs-Neuanmeldung addieren.
        if self._streaks["auth"] or self._streaks["forbidden"]:
            _LOGGER.info(
                "Electrolux: wieder erreichbar, Fehlerserie zurückgesetzt "
                "(401er: %d, 403er: %d)",
                self._streaks["auth"], self._streaks["forbidden"],
            )
        self._streaks["auth"] = 0
        self._streaks["forbidden"] = 0
        return dict(self._appliances)

    def _takt_anpassen(self) -> None:
        """Poll-Takt an den tatsaechlichen Betrieb anpassen.

        Laeuft irgendein Geraet ein Programm, wird schnell gepollt, damit die
        Fertig-Ansage sitzt. Steht alles still, wird auf den Leerlauf-Takt
        gedrosselt. Ist der Zustand unbekannt, gilt bewusst SCHNELL — im
        Zweifel lieber ein paar Abrufe zu viel als eine verpasste Meldung.
        """
        aktiv = False
        for appliance in self._appliances.values():
            zustand = _gemeldeter_zustand(appliance)
            if not zustand or zustand.replace(" ", "") in ACTIVE_APPLIANCE_STATES:
                aktiv = True
                break

        gewuenscht = timedelta(
            seconds=self._fast_interval if aktiv else IDLE_SCAN_INTERVAL
        )
        if self.update_interval != gewuenscht:
            self.update_interval = gewuenscht
            _LOGGER.debug(
                "Electrolux: Takt auf %s s gesetzt (%s)",
                int(gewuenscht.total_seconds()),
                "Betrieb" if aktiv else "Leerlauf",
            )
