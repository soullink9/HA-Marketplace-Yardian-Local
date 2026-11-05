"""Sensors: active zone, last watering, rain delay, and estimated water use (Energy dashboard ready)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import YardianConfigEntry, YardianCoordinator
from .entity import YardianEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: YardianConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the controller's sensors and a water sensor for every zone."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ActiveZone(coordinator, "active_zone", "Active zone"),
            LastWatering(coordinator, "last_watering", "Last watering"),
            RainDelay(coordinator, "rain_delay", "Rain delay"),
            Water(coordinator, "water_total", "Water used"),
            *(
                Water(coordinator, f"zone_{zone}_water", f"{coordinator.data['zones'][zone][0]} water used", zone)
                for zone in range(len(coordinator.data["zones"]))
            ),
        ]
    )


class ActiveZone(YardianEntity, SensorEntity):
    """Name of the zone(s) running now, or "Idle"."""

    _attr_icon = "mdi:sprinkler-variant"

    @property
    def native_value(self) -> str:
        """Running zone names, comma separated."""
        active = sorted(self.coordinator.data["active"])
        return ", ".join(self.zone_name(zone) for zone in active) if active else "Idle"


class LastWatering(YardianEntity, SensorEntity):
    """When watering last began, from Home Assistant or anywhere else.

    Kept in Home Assistant's storage, so it stays readable while the controller is offline. The blueprint
    finds this sensor through the controller's device and uses it to never water twice in a day.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:history"
    available = True

    @property
    def native_value(self) -> datetime | None:
        """Time of the last start (None until the first watering)."""
        return self.coordinator.last_start


class RainDelay(YardianEntity, SensorEntity):
    """The controller's own rain delay, as it reports it (read only)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    @property
    def native_value(self) -> int | None:
        """Raw value from the controller."""
        return self.coordinator.data["oper"].get("iRainDelay")


class Water(YardianEntity, SensorEntity):
    """Estimated water used: time each zone ran x its flow rate. ``zone`` None is the controller total.

    An estimate, not a meter reading: the controller has no flow sensor. Watering while Home Assistant is
    down isn't counted. The unit is fixed when the integration is set up (gallons or litres).
    """

    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:water"

    def __init__(self, coordinator: YardianCoordinator, key: str, name: str, zone: int | None = None) -> None:
        """Create the total (``zone`` None) or one zone's sensor."""
        super().__init__(coordinator, key, name, zone)
        self._attr_native_unit_of_measurement = UnitOfVolume.GALLONS if coordinator.imperial else UnitOfVolume.LITERS

    @property
    def native_value(self) -> float:
        """Running total."""
        water = self.coordinator.water
        return round(sum(water.values()) if self.zone is None else water.get(self.zone, 0.0), 3)
