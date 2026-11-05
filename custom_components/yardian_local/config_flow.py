"""Setup from the UI: host and access token, checked against the controller before saving."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyyardian import AsyncYardianClient, NotAuthorizedException
import voluptuous as vol

from .const import DOMAIN

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Required(CONF_ACCESS_TOKEN): str})


class YardianLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a Yardian controller."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for host and token; one entry per controller (keyed by its Yardian ID)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = await AsyncYardianClient.create(
                    async_get_clientsession(self.hass), user_input[CONF_HOST], token=user_input[CONF_ACCESS_TOKEN]
                )
                info = await client.fetch_device_info()
            except NotAuthorizedException:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001 - wrong address, offline, timeout: all "can't connect" to the user
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info["yid"])
                self._abort_if_unique_id_configured()
                # Device info (yid, model, serial number) is kept with the entry for the device page.
                return self.async_create_entry(title=info.get("name") or "Yardian", data=user_input | info)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)
