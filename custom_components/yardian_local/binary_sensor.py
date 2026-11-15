"""Binary sensors: watering (any zone running) and the controller's standby mode."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import YardianConfigEntry
from .entity import YardianEntity

# Every value comes from the coordinator's poll, so there is nothing to limit.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: YardianConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the two binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities([Watering(coordinator, "watering"), Standby(coordinator, "standby")])


class Watering(YardianEntity, BinarySensorEntity):
    """On while any zone is running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "watering"

    @property
    def is_on(self) -> bool:
        """True if the controller reports a running zone."""
        return bool(self.coordinator.data["active"])


class Standby(YardianEntity, BinarySensorEntity):
    """On while the controller is in standby (set in the Yardian app; read only here)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "standby"

    @property
    def is_on(self) -> bool:
        """The controller reports standby as an end time; standby is on until then."""
        end = self.coordinator.data["oper"].get("iStandby")
        return isinstance(end, int) and end > dt_util.utcnow().timestamp()
