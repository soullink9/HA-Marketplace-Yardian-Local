"""One switch per zone.

Every start sends the controller a duration, so the controller stops the zone on its own timer even if
Home Assistant goes down. Nothing in this integration ever starts a zone without one.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
import voluptuous as vol

from .coordinator import YardianConfigEntry, YardianCoordinator
from .entity import YardianEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: YardianConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Add a switch for every zone the controller reports, and the start_irrigation action."""
    coordinator = entry.runtime_data
    async_add_entities(YardianZone(coordinator, zone) for zone in range(len(coordinator.data["zones"])))
    # yardian_local.start_irrigation: run a zone for an explicit number of minutes (used by the blueprint).
    entity_platform.async_get_current_platform().async_register_entity_service(
        "start_irrigation",
        {vol.Required("duration"): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440))},
        "async_turn_on",
    )


class YardianZone(YardianEntity, SwitchEntity):
    """A sprinkler zone. Turning it on runs it for its "run time" (or the duration passed in)."""

    _attr_icon = "mdi:sprinkler-variant"

    def __init__(self, coordinator: YardianCoordinator, zone: int) -> None:
        """Create the switch for 0-based ``zone``, named as in the Yardian app."""
        super().__init__(coordinator, f"zone_{zone}", str(coordinator.data["zones"][zone][0]), zone)

    @property
    def available(self) -> bool:
        """Unavailable while the controller is unreachable, or if the zone is disabled in the Yardian app."""
        return super().available and self.coordinator.data["zones"][self.zone][1] == 1

    @property
    def is_on(self) -> bool:
        """On while the controller reports the zone running."""
        return self.zone in self.coordinator.data["active"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zone number (1-based) and run time; the blueprint reads ``run_minutes`` from here."""
        return {"zone": self.zone + 1, "run_minutes": int(self.coordinator.run_minutes.get(self.zone) or 0)}

    async def async_turn_on(self, duration: int | None = None, **kwargs: Any) -> None:
        """Run the zone for ``duration`` minutes, or for its run time when turned on from the UI."""
        minutes = int(duration or self.coordinator.run_minutes.get(self.zone, 0))
        if minutes < 1:
            raise HomeAssistantError(f"{self.name}: run time is 0 minutes")
        await self._call(self.coordinator.client.start_irrigation(self.zone, minutes), started=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the zone.

        On Yardian Pro (YP) models pyyardian can only stop everything, so this stops every running zone.
        That matches how the blueprint runs zones (one at a time).
        """
        await self._call(self.coordinator.client.stop_zone(self.zone))
