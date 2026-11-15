"""Yardian Local: control a Yardian sprinkler controller over the local network only.

How the pieces fit:
- coordinator.py polls the controller and keeps run times, flow rates, water totals and the last
  watering time (the Home Assistant side of the data).
- entity.py is the base class; each platform file adds one kind of entity. Names and icons are in
  translations/en.json and icons.json.
- services.py adds ``yardian_local.notify``; switch.py adds ``yardian_local.start_irrigation``.
- The blueprint in blueprints/automation/yardian/ is the schedule. It relies on two things from here:
  every zone start carries a duration (so the controller always stops on its own), and the
  "Last watering" sensor (so a day is never watered twice, even after a crash).
"""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from pyyardian import AsyncYardianClient, NetworkException, NotAuthorizedException

from .const import DOMAIN
from .coordinator import YardianConfigEntry, YardianCoordinator
from .services import async_setup_services

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

# Set up from the UI only; there is nothing to put in configuration.yaml.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's actions once, however many controllers are added."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: YardianConfigEntry) -> None:
    """Connect to one controller and create its entities.

    Succeeds or raises a ConfigEntry* exception (Home Assistant's pattern since 2026.11): a rejected token starts
    the re-authentication flow, an unreachable controller is retried later.
    """
    try:
        client = await AsyncYardianClient.create(
            async_get_clientsession(hass), entry.data[CONF_HOST], token=entry.data[CONF_ACCESS_TOKEN]
        )
        info = await client.fetch_device_info()
    except NotAuthorizedException as err:
        raise ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="invalid_auth") from err
    except (NetworkException, OSError, TimeoutError) as err:
        # Home Assistant retries later; the entities show as unavailable meanwhile.
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="cannot_connect", translation_placeholders={"error": str(err)}
        ) from err

    coordinator = YardianCoordinator(hass, entry, client, info or {})
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: YardianConfigEntry) -> None:
    """Save totals now, then remove the entities (on reload, restart or removal)."""
    # Without this, a pending delayed save could land after the reloaded entry has already read the
    # file, and the water total would go backwards.
    await entry.runtime_data.async_save()
    # Raises a translated ConfigEntryError if a platform fails to unload, so the user sees why.
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
