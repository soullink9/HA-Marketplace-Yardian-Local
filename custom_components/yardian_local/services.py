"""Integration-wide actions. (``start_irrigation`` is an entity action, registered in switch.py.)"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

NOTIFY_SCHEMA = vol.Schema(
    {
        vol.Required("targets"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("title"): cv.string,
        vol.Required("message"): cv.string,
    }
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register ``yardian_local.notify``."""

    async def notify(call: ServiceCall) -> None:
        """Send one notification to several notify actions, never failing.

        Why this exists: when an automation calls a notify action that no longer exists (a phone was
        removed or renamed), Home Assistant stops the whole automation, even with continue_on_error.
        For a sprinkler schedule that would mean no watering. Here a missing or failing target is only
        logged, and the other targets still get the message.
        """
        for target in call.data["targets"]:
            domain, name = target.split(".", 1) if "." in target else ("notify", target)
            if not hass.services.has_service(domain, name):
                _LOGGER.warning("Notification target %s not found, skipped", target)
                continue
            try:
                await hass.services.async_call(
                    domain, name, {"title": call.data.get("title"), "message": call.data["message"]}, blocking=True
                )
            except Exception as err:  # noqa: BLE001 - a notification must never stop watering
                _LOGGER.warning("Notification to %s failed: %s", target, err)

    hass.services.async_register(DOMAIN, "notify", notify, schema=NOTIFY_SCHEMA)
