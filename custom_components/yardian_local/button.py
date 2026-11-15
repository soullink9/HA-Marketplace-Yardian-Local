"""Stop-all button."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import YardianConfigEntry
from .entity import YardianEntity

# Commands go to the controller one at a time; it is a small device.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: YardianConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the button."""
    async_add_entities([StopAll(entry.runtime_data, "stop_all")])


class StopAll(YardianEntity, ButtonEntity):
    """Stops every running zone.

    The blueprint uses this button for its safety stops, and its availability tells the blueprint whether
    the controller can be reached.
    """

    _attr_translation_key = "stop_all"

    async def async_press(self) -> None:
        """Stop all watering."""
        await self._call(self.coordinator.client.stop_irrigation())
