"""Yardian Local: control a Yardian sprinkler controller over the local network only.

How the pieces fit:
- coordinator.py polls the controller and keeps run times, flow rates, water totals and the last
  watering time (the Home Assistant side of the data).
- entity.py is the base class; each platform file adds one kind of entity.
- services.py adds ``yardian_local.notify``; switch.py adds ``yardian_local.start_irrigation``.
- The blueprint in blueprints/automation/yardian/ is the schedule. It relies on two things from here:
  every zone start carries a duration (so the controller always stops on its own), and the
  "Last watering" sensor (so a day is never watered twice, even after a crash).
"""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN, CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from pyyardian import AsyncYardianClient, NetworkException, NotAuthorizedException

from .const import CONF_UNITS, DOMAIN
from .coordinator import YardianConfigEntry, YardianCoordinator
from .services import async_setup_services

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

# Set up from the UI only; there is nothing to put in configuration.yaml.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's actions once, however many controllers are added."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: YardianConfigEntry) -> bool:
    """Connect to one controller and create its entities."""
    # Fix the unit system the first time the entry is set up. Water totals and flow rates are stored as
    # plain numbers, so if they followed the current unit system, switching Home Assistant to another one
    # would silently turn litres into gallons (and break the Energy dashboard's history).
    if CONF_UNITS not in entry.data:
        units = "imperial" if hass.config.units is US_CUSTOMARY_SYSTEM else "metric"
        hass.config_entries.async_update_entry(entry, data={**entry.data, CONF_UNITS: units})

    try:
        client = await AsyncYardianClient.create(
            async_get_clientsession(hass), entry.data[CONF_HOST], token=entry.data[CONF_ACCESS_TOKEN]
        )
        info = await client.fetch_device_info()
    except NotAuthorizedException as err:
        raise ConfigEntryError("Invalid access token") from err
    except (NetworkException, OSError, TimeoutError) as err:
        # Home Assistant retries later; the entities show as unavailable meanwhile.
        raise ConfigEntryNotReady(f"Yardian unreachable: {err}") from err

    coordinator = YardianCoordinator(hass, entry, client, info or {})
    await coordinator.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: YardianConfigEntry) -> bool:
    """Save totals now, then remove the entities (on reload, restart or removal)."""
    # Without this, a pending delayed save could land after the reloaded entry has already read the
    # file, and the water total would go backwards.
    await entry.runtime_data.async_save()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
