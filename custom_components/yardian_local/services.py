"""Integration-wide actions. (``start_irrigation`` is an entity action, registered in switch.py.)"""

from __future__ import annotations

import logging
import re

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# A target is a notify action: "notify.<name>", or just "<name>" (taken as notify.<name>). Anything else, such as
# "script.water_now" or "shell_command.x", is refused: this action sends notifications and must not become a way
# to call any other action in Home Assistant.
NOTIFY_TARGET = re.compile(r"(?:notify\.)?(?P<name>[a-z0-9_]+)")

NOTIFY_SCHEMA = vol.Schema(
    {
        # Targets are checked one by one in notify() rather than here: a schema error would stop the calling
        # automation, which is exactly what this action exists to prevent (see notify()).
        vol.Required("targets"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("title"): cv.string,
        vol.Required("message"): cv.string,
    }
)


def notify_action_name(target: str) -> str | None:
    """Return the notify action's name for ``target`` (``notify.family`` → ``family``), or None if it isn't one."""
    match = NOTIFY_TARGET.fullmatch(target.strip().lower())
    return match["name"] if match else None


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register ``yardian_local.notify``."""

    async def notify(call: ServiceCall) -> None:
        """Send one notification to several notify actions, never failing.

        Why this exists: when an automation calls a notify action that no longer exists (a phone was
        removed or renamed), Home Assistant stops the whole automation, even with continue_on_error.
        For a sprinkler schedule that would mean no watering. Here a missing, failing or invalid target is
        only logged, and the other targets still get the message. Only actions in the ``notify`` domain
        are ever called.
        """
        for target in call.data["targets"]:
            name = notify_action_name(target)
            if name is None:
                _LOGGER.error("Notification target %r is not a notify action, skipped", target)
                continue
            if not hass.services.has_service("notify", name):
                _LOGGER.warning("Notification target notify.%s not found, skipped", name)
                continue
            try:
                await hass.services.async_call(
                    "notify", name, {"title": call.data.get("title"), "message": call.data["message"]}, blocking=True
                )
            except Exception as err:  # noqa: BLE001 - a notification must never stop watering
                _LOGGER.warning("Notification to notify.%s failed: %s", name, err)

    hass.services.async_register(DOMAIN, "notify", notify, schema=NOTIFY_SCHEMA)
