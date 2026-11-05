"""Settings that live in Home Assistant: zone run times and flow rates.

They are number entities so they can be changed from a dashboard, and they restore their values after a
restart. The controller never sees them; the coordinator and the blueprint read them.
"""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberMode, RestoreNumber
from homeassistant.const import EntityCategory, UnitOfTime, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEFAULT_RUN_MINUTES
from .coordinator import YardianConfigEntry, YardianCoordinator
from .entity import YardianEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: YardianConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add the shared flow rate, plus a run time and an (optional) flow rate for every zone."""
    coordinator = entry.runtime_data
    zones = range(len(coordinator.data["zones"]))
    async_add_entities(
        [
            FlowRate(coordinator, None),
            *(ZoneRunTime(coordinator, zone) for zone in zones),
            *(FlowRate(coordinator, zone) for zone in zones),
        ]
    )


class _Setting(YardianEntity, RestoreNumber):
    """A number whose value lives in ``coordinator.<_values_attr>[zone]`` (``zone`` None = the controller)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _values_attr = ""
    _default = 0.0
    # Home Assistant-side settings stay editable while the controller is offline.
    available = True

    @property
    def _values(self) -> dict:
        """The coordinator dict this setting is stored in."""
        return getattr(self.coordinator, self._values_attr)

    async def async_added_to_hass(self) -> None:
        """Restore the value saved before the last restart (or use the default the first time)."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        self._values[self.zone] = last.native_value if last and last.native_value is not None else self._default
        self.coordinator.async_update_listeners()  # e.g. the zone switch shows the restored run time

    @property
    def native_value(self) -> float | None:
        """Current value."""
        return self._values.get(self.zone)

    async def async_set_native_value(self, value: float) -> None:
        """Change the value (from the UI or an action)."""
        self._values[self.zone] = value
        self.coordinator.async_update_listeners()


class ZoneRunTime(_Setting):
    """Minutes a zone runs (0 = skip it). Used when the zone is switched on and by the blueprint."""

    _attr_icon = "mdi:timer-outline"
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _values_attr = "run_minutes"
    _default = DEFAULT_RUN_MINUTES

    def __init__(self, coordinator: YardianCoordinator, zone: int) -> None:
        """Create the run time for 0-based ``zone``."""
        super().__init__(coordinator, f"zone_{zone}_minutes", f"{coordinator.data['zones'][zone][0]} run time", zone)


class FlowRate(_Setting):
    """Flow rate used for the water estimate.

    ``zone`` None is the shared rate every zone uses. The per-zone rates are disabled by default; enable
    one only for a zone that uses noticeably more or less water (left at 0, a zone uses the shared rate).
    """

    _attr_device_class = NumberDeviceClass.VOLUME_FLOW_RATE
    _attr_icon = "mdi:water-pump"
    _attr_native_max_value = 200
    _attr_native_step = 0.1
    _values_attr = "flow"

    def __init__(self, coordinator: YardianCoordinator, zone: int | None) -> None:
        """Create the shared rate (``zone`` None) or one zone's override."""
        if zone is None:
            super().__init__(coordinator, "flow", "Flow rate")
        else:
            super().__init__(coordinator, f"zone_{zone}_flow", f"{coordinator.data['zones'][zone][0]} flow rate", zone)
            self._attr_entity_registry_enabled_default = False
        self._attr_native_unit_of_measurement = (
            UnitOfVolumeFlowRate.GALLONS_PER_MINUTE if coordinator.imperial else UnitOfVolumeFlowRate.LITERS_PER_MINUTE
        )
