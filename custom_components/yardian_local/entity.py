"""Base class shared by every Yardian Local entity."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import YardianCoordinator


class YardianEntity(CoordinatorEntity[YardianCoordinator]):
    """An entity on the controller's device, optionally tied to one zone (0-based ``zone``).

    Names and icons come from ``_attr_translation_key`` (translations/en.json and icons.json). A zone entity's
    name gets the zone's name from the Yardian app as ``{zone_name}``.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: YardianCoordinator, key: str, zone: int | None = None) -> None:
        """Create the entity. ``key`` must never change: it is part of the unique ID."""
        super().__init__(coordinator)
        self.zone = zone
        self._attr_unique_id = f"{coordinator.yid}_{key}"
        self._attr_device_info = coordinator.device_info
        if zone is not None:
            self._attr_translation_placeholders = {"zone_name": self.zone_name(zone)}

    def zone_name(self, zone: int) -> str:
        """Return the zone's name as set in the Yardian app."""
        zones = self.coordinator.data["zones"]
        return str(zones[zone][0]) if zone < len(zones) else f"Zone {zone + 1}"

    async def _call(self, command: Awaitable, started: bool = False) -> None:
        """Send a command to the controller, then refresh so the UI catches up quickly.

        ``started=True`` records the time as the last watering start (zone switches pass this).
        Any failure becomes a HomeAssistantError so the UI shows it and automations can continue past it.
        """
        try:
            await command
        except Exception as err:  # noqa: BLE001 - pyyardian raises several types; report them all the same way
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if started:
            await self.coordinator.async_mark_start()
        await self.coordinator.async_request_refresh()
