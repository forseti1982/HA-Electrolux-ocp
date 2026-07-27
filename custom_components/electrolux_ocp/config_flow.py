"""Config-Flow für die Electrolux OCP Developer-API Integration."""

from __future__ import annotations

import logging
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster Schritt: 3 Tokens vom Developer-Dashboard erfassen."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                fingerprint = await _validate_credentials(
                    self.hass,
                    user_input[CONF_API_KEY],
                    user_input[CONF_ACCESS_TOKEN],
                    user_input[CONF_REFRESH_TOKEN],
                )
            except ClientResponseError as err:
                if err.status in (401, 403):
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Unerwarteter Fehler bei der Validierung")
                _LOGGER.debug("Detail: %s", scrub_secrets(str(err)))
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(fingerprint)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Electrolux / AEG",
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                        CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN].strip(),
                        CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN].strip(),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "dashboard": "https://developer.electrolux.one/dashboard"
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Starte den Reauth-Flow (z. B. nach abgelaufenem Refresh-Token)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bestätige die neuen Tokens im Reauth-Flow."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                fingerprint = await _validate_credentials(
                    self.hass,
                    user_input[CONF_API_KEY],
                    user_input[CONF_ACCESS_TOKEN],
                    user_input[CONF_REFRESH_TOKEN],
                )
            except ClientResponseError as err:
                errors["base"] = (
                    "invalid_auth" if err.status in (401, 403) else "cannot_connect"
                )
            except ValueError:
                errors["base"] = "invalid_auth"
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Unerwarteter Fehler bei der Reauth-Validierung")
                _LOGGER.debug("Detail: %s", scrub_secrets(str(err)))
                errors["base"] = "unknown"
            else:
                # Konto-Abgleich: die neuen Tokens müssen zum selben Konto gehören
                # wie der Entry, sonst würde ein Entry still auf ein fremdes Konto
                # umgebogen. Fingerprint = sortierte Appliance-IDs = unique_id.
                if (
                    reauth_entry.unique_id is not None
                    and fingerprint != reauth_entry.unique_id
                ):
                    return self.async_abort(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY].strip(),
                        CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN].strip(),
                        CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN].strip(),
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "dashboard": "https://developer.electrolux.one/dashboard"
            },
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
