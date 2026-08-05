"""Config-Flow für die Electrolux OCP Developer-API Integration."""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from aiohttp import ClientResponseError
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from pyelectroluxgroup.api import ElectroluxHubAPI
from pyelectroluxgroup.token_manager import TokenManager

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_TS,
    DASHBOARD_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .util import scrub_secrets

_LOGGER = logging.getLogger(__name__)


class _ValidationTokenManager(TokenManager):
    """Einfacher In-Memory-TokenManager nur zur Validierung im Config-Flow."""

    def __init__(self, api_key: str, access_token: str, refresh_token: str) -> None:
        self._api_key: str | None = api_key
        self._access_token: str = access_token
        self._refresh_token: str = refresh_token

    def update(
        self,
        access_token: str,
        refresh_token: str,
        api_key: str | None = None,
    ) -> None:
        super().update(access_token, refresh_token, api_key)


STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required(CONF_REFRESH_TOKEN): str,
    }
)


async def _validate_credentials(
    hass: Any, api_key: str, access_token: str, refresh_token: str
) -> str:
    """Prüfe die Zugangsdaten per Testabruf. Gibt einen Account-Fingerprint zurück.

    Wirft ClientResponseError bei HTTP-Fehlern und ValueError bei Token-Problemen.
    """
    session = async_get_clientsession(hass)
    token_manager = _ValidationTokenManager(
        api_key.strip(), access_token.strip(), refresh_token.strip()
    )
    api = ElectroluxHubAPI(session, token_manager)
    appliances = await api.async_get_appliances()
    # Stabiler Fingerprint aus den (sortierten) Appliance-IDs für unique_id.
    ids = sorted(str(a.id) for a in appliances)
    return "|".join(ids) if ids else "electrolux_ocp_account"


class ElectroluxOcpConfigFlow(ConfigFlow, domain=DOMAIN):
    """Verwaltet den Config-Flow für Electrolux OCP."""

    VERSION = 1

    def _entry_data(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Baue die zu speichernden Entry-Daten inkl. Härtungs-Zeitstempel."""
        return {
            CONF_API_KEY: user_input[CONF_API_KEY].strip(),
            CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN].strip(),
            CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN].strip(),
            # Frischer Zeitstempel -> gewinnt beim Setup-Abgleich gegen einen
            # alten Sofort-Store (siehe token_manager.async_prime).
            CONF_TOKEN_TS: time.time(),
        }

    async def _validate(
        self, user_input: dict[str, Any], errors: dict[str, str]
    ) -> str | None:
        """Validiere die 3 Werte; fülle errors und gib den Fingerprint zurück."""
        try:
            return await _validate_credentials(
                self.hass,
                user_input[CONF_API_KEY],
                user_input[CONF_ACCESS_TOKEN],
                user_input[CONF_REFRESH_TOKEN],
            )
        except ClientResponseError as err:
            errors["base"] = "invalid_auth" if err.status in (401, 403) else "cannot_connect"
        except ValueError:
            errors["base"] = "invalid_auth"
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Unerwarteter Fehler bei der Validierung")
            _LOGGER.debug("Detail: %s", scrub_secrets(str(err)))
            errors["base"] = "unknown"
        return None

    # -- Wizard: Erst-Setup --------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt 1 (Wizard-Intro): erklärt in Klartext, wie man die 3 Werte
        holt. Weiter führt zur Eingabe."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["credentials"],
            description_placeholders={"dashboard": DASHBOARD_URL},
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt 2: die 3 Werte erfassen (mit Feld-Hilfen aus den Strings)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            fingerprint = await self._validate(user_input, errors)
            if fingerprint is not None:
                await self.async_set_unique_id(fingerprint)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Electrolux / AEG", data=self._entry_data(user_input)
                )
        return self.async_show_form(
            step_id="credentials",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={"dashboard": DASHBOARD_URL},
        )

    # -- Wizard: Re-Auth (Tokens abgelaufen) ---------------------------------
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Starte den Reauth-Flow (z. B. nach abgelaufenem Refresh-Token)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reauth-Intro: erklärt den Weg, dann weiter zur Eingabe."""
        return self.async_show_menu(
            step_id="reauth_confirm",
            menu_options=["reauth_credentials"],
            description_placeholders={"dashboard": DASHBOARD_URL},
        )

    async def async_step_reauth_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reauth-Eingabe: neue Werte erfassen + Konto-Abgleich."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            fingerprint = await self._validate(user_input, errors)
            if fingerprint is not None:
                if (
                    reauth_entry.unique_id is not None
                    and fingerprint != reauth_entry.unique_id
                ):
                    return self.async_abort(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reauth_entry, data=self._entry_data(user_input)
                )
        return self.async_show_form(
            step_id="reauth_credentials",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={"dashboard": DASHBOARD_URL},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> ElectroluxOcpOptionsFlow:
        """Gib den Options-Flow zurück."""
        return ElectroluxOcpOptionsFlow()


class ElectroluxOcpOptionsFlow(OptionsFlow):
    """Options-Flow: Poll-Intervall anpassen."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Verwalte die Optionen."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=current
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
