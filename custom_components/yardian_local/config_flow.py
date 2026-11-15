"""Setup from the UI: host and access token, checked against the controller before saving.

Also handles a token that stops working (re-authentication) and a controller that moved to a new address
(Reconfigure), both without removing the entry, so entities, history and saved water totals stay.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pyyardian import AsyncYardianClient, NotAuthorizedException
import voluptuous as vol

from .const import CONF_UNITS, DOMAIN

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_ACCESS_TOKEN): str})
STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})
STEP_RECONFIGURE_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


class YardianLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a Yardian controller."""

    VERSION = 1

    async def _async_connect(self, host: str, token: str) -> tuple[dict[str, Any], dict[str, str]]:
        """Ask the controller for its device info; return it, or the form errors to show instead."""
        try:
            client = await AsyncYardianClient.create(async_get_clientsession(self.hass), host, token=token)
            return await client.fetch_device_info(), {}
        except NotAuthorizedException:
            return {}, {"base": "invalid_auth"}
        except Exception:  # noqa: BLE001 - wrong address, offline, timeout: all "can't connect" to the user
            return {}, {"base": "cannot_connect"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for host and token; one entry per controller (keyed by its Yardian ID)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await self._async_connect(user_input[CONF_HOST], user_input[CONF_ACCESS_TOKEN])
            if not errors:
                await self.async_set_unique_id(info["yid"])
                self._abort_if_unique_id_configured()
                # The unit system is fixed now, once. Water totals and flow rates are stored as plain numbers, so
                # if they followed the current unit system, switching Home Assistant to another one later would
                # silently turn litres into gallons (and break the Energy dashboard's history).
                units = "imperial" if self.hass.config.units is US_CUSTOMARY_SYSTEM else "metric"
                # Device info (yid, model, serial number) is kept with the entry for the device page.
                return self.async_create_entry(
                    title=info.get("name") or "Yardian", data=user_input | info | {CONF_UNITS: units}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_SCHEMA, user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The controller rejected the token (it was changed in the Yardian app): ask for the new one."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the new access token and check it against the same controller."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await self._async_connect(entry.data[CONF_HOST], user_input[CONF_ACCESS_TOKEN])
            if not errors:
                await self.async_set_unique_id(info["yid"])
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            description_placeholders={"name": entry.title},
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the controller's address (e.g. after it got a new IP), keeping everything else."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            info, errors = await self._async_connect(user_input[CONF_HOST], entry.data[CONF_ACCESS_TOKEN])
            if not errors:
                # Refuse a different controller at the new address: its zones would take over this one's entities.
                await self.async_set_unique_id(info["yid"])
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(STEP_RECONFIGURE_SCHEMA, user_input or entry.data),
            errors=errors,
        )
