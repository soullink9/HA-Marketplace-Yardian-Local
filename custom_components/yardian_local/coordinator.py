"""Polling, water estimates and saved data for one Yardian controller.

The coordinator is the single place that talks to the controller on a schedule. Every entity reads
from it. It also holds the values that live in Home Assistant rather than on the controller: zone run
times, flow rates, water totals and the time watering last started.
"""

from __future__ import annotations

from datetime import datetime
import logging
import re
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from pyyardian import AsyncYardianClient, NotAuthorizedException

from .const import (
    CONF_UNITS,
    DOMAIN,
    MANUFACTURER,
    MAX_POLL_GAP,
    SAME_START,
    SAVE_EVERY,
    STORAGE_KEY,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type YardianConfigEntry = ConfigEntry[YardianCoordinator]

# Keys in the controller's device info that may hold the firmware version. The API isn't documented,
# so match the likely names but not look-alikes such as "hwVersion" or "apiVersion".
_FIRMWARE_KEY = re.compile(r"(?i)(fw|firmware|sw|software)_?(ver(sion)?)?|version")


class YardianCoordinator(DataUpdateCoordinator[dict]):
    """Poll the controller and keep the Home Assistant side of its data.

    ``data`` after each poll: ``{"zones": [[name, enabled, ...], ...], "active": {zone, ...}, "oper": {...}}``.
    Zone numbers are 0-based here (the controller's numbering); entities show them 1-based.
    """

    config_entry: YardianConfigEntry

    def __init__(self, hass: HomeAssistant, entry: YardianConfigEntry, client: AsyncYardianClient, info: dict) -> None:
        """Set up the coordinator; call ``async_load`` before the first refresh."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = client
        self.yid: str = entry.data["yid"]
        self.raw_info = info  # kept for the diagnostics download
        # Fixed when the entry was first set up (see __init__.py), so stored numbers never change meaning
        # if the user later switches Home Assistant between metric and US customary.
        self.imperial = entry.data[CONF_UNITS] == "imperial"

        # Values owned by Home Assistant. The number entities fill these in from restore state.
        self.run_minutes: dict[int, float] = {}
        self.flow: dict[int | None, float] = {}  # key None = shared rate for all zones
        self.water: dict[int, float] = {}  # estimated volume per zone, in the entry's units
        self.last_start: datetime | None = None  # when watering last began (any zone, any source)

        self._store: Store[dict] = Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry.entry_id))
        self._save_due = False
        self._last_poll: float | None = None

        firmware = next((str(v) for k, v in info.items() if _FIRMWARE_KEY.fullmatch(k)), None)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.yid)},
            manufacturer=MANUFACTURER,
            name=entry.title,
            model=info.get("model") or entry.data.get("model"),
            serial_number=entry.data.get("serialNumber"),
            sw_version=firmware,
        )

    # ------------------------------------------------------------------ saved data

    def _stored(self) -> dict:
        """Return the data to save. Store calls this when it writes, so clear the pending flag here."""
        self._save_due = False
        return {
            "water": {str(zone): total for zone, total in self.water.items()},
            "last_start": self.last_start.isoformat() if self.last_start else None,
        }

    async def async_load(self) -> None:
        """Load water totals and the last watering time saved by an earlier run."""
        data = await self._store.async_load() or {}
        if "water" not in data:  # a bare {zone: total} file (no last watering time): wrap it in the full shape
            data = {"water": data}
        self.water = {int(zone): float(total) for zone, total in data["water"].items()}
        self.last_start = dt_util.parse_datetime(data["last_start"]) if data.get("last_start") else None

    async def async_save(self) -> None:
        """Write everything now (used on unload so a reload never loses or rewinds totals)."""
        await self._store.async_save(self._stored())

    async def async_mark_start(self) -> None:
        """Record that watering started now.

        Saved immediately rather than with the usual delay: the blueprint relies on this time to never
        water twice in a day, and that has to hold even if the power goes out a second later.
        """
        self.last_start = dt_util.utcnow()
        await self.async_save()

    # ------------------------------------------------------------------ polling

    async def _async_update_data(self) -> dict:
        """Poll the controller, then update the water estimate and the last watering time."""
        try:
            state = await self.client.fetch_device_state()
            oper = await self.client.fetch_oper_info()
        except NotAuthorizedException as err:
            raise ConfigEntryError("Invalid access token") from err
        except Exception as err:  # noqa: BLE001 - pyyardian raises several types; any of them means "unreachable"
            raise UpdateFailed(f"Yardian unreachable: {err}") from err

        active = set(state.active_zones)
        was_active = bool(self.data and self.data["active"])

        # Water estimate: every zone that was running at the previous poll ran until now, at its flow rate.
        # Measured with a monotonic clock so a system clock change can't add or remove water.
        now = time.monotonic()
        if self._last_poll is not None and was_active:
            minutes = min(now - self._last_poll, MAX_POLL_GAP) / 60
            for zone in self.data["active"]:
                rate = self.flow.get(zone) or self.flow.get(None) or 0.0  # zone override, else shared rate
                self.water[zone] = self.water.get(zone, 0.0) + rate * minutes
            # Schedule one save and let it happen. Calling async_delay_save on every poll would keep
            # pushing the save back (polls are closer together than the delay), so nothing would be
            # written until watering stopped.
            if not self._save_due:
                self._save_due = True
                self._store.async_delay_save(self._stored, SAVE_EVERY)
        self._last_poll = now

        # Watering that started outside Home Assistant (the Yardian app, the controller's own schedule)
        # also counts as "watered today" for the blueprint.
        if active and not was_active and (self.last_start is None or dt_util.utcnow() - self.last_start > SAME_START):
            await self.async_mark_start()

        return {"zones": state.zones, "active": active, "oper": oper or {}}
