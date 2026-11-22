"""Polling, water estimates and saved data for one Yardian controller.

The coordinator is the single place that talks to the controller on a schedule. Every entity reads
from it. It also holds the values that live in Home Assistant rather than on the controller: zone run
times, flow rates, water totals and the time watering last started.
"""

from __future__ import annotations

from datetime import datetime
import logging
import math
import re
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
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


def _is_int(value: Any) -> bool:
    """True for a real integer (``bool`` is an ``int`` in Python, but never a zone number or a count)."""
    return isinstance(value, int) and not isinstance(value, bool)


def clean_zones(raw: Any) -> list[list] | None:
    """Return the controller's zone list in the shape entities read, or None if it isn't a list at all.

    Each zone is ``[name, enabled, ...]``. The controller's API isn't documented, so a zone entry that isn't a
    list of at least two items is replaced by a disabled placeholder: its switch shows as unavailable instead of
    every entity failing on it.
    """
    if not isinstance(raw, list | tuple):
        return None
    zones = []
    for number, zone in enumerate(raw):
        if isinstance(zone, list | tuple) and len(zone) >= 2:
            zones.append(list(zone))
        else:
            _LOGGER.debug("Zone %s from the controller is malformed (%r); shown as disabled", number + 1, zone)
            zones.append([f"Zone {number + 1}", 0])
    return zones


def clean_active(raw: Any, zone_count: int) -> set[int]:
    """Return the running zones the controller reported that are real zone numbers (0-based, within the list)."""
    try:
        reported = list(raw)
    except TypeError:
        return set()
    return {zone for zone in reported if _is_int(zone) and 0 <= zone < zone_count}


def clean_water(raw: Any) -> dict[int, float]:
    """Return saved water totals that make sense: a zone number and a finite, non-negative amount.

    The file is Home Assistant's, but it can be damaged (a crash mid-write, a hand edit). One bad entry is
    dropped and logged rather than stopping the integration from loading, or showing NaN in the Energy dashboard.
    """
    if not isinstance(raw, dict):
        return {}
    water = {}
    for zone, total in raw.items():
        try:
            number, amount = int(zone), float(total)
        except TypeError, ValueError:
            number, amount = -1, math.nan
        if number >= 0 and math.isfinite(amount) and amount >= 0:
            water[number] = amount
        else:
            _LOGGER.warning("Ignored a saved water total that isn't valid (zone %r, total %r)", zone, total)
    return water


def clean_last_start(raw: Any) -> datetime | None:
    """Return the saved last watering time, or None if it's missing, unreadable or in the future.

    None makes the blueprint fall back on the automation's own last run to decide whether today was watered. A
    time in the future is refused because it would stop polling from ever recording a later start (see
    ``SAME_START`` in ``_async_update_data``).
    """
    if not isinstance(raw, str):
        return None
    try:
        parsed = dt_util.parse_datetime(raw)
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None or parsed > dt_util.utcnow():
        _LOGGER.warning("Ignored a saved last watering time that isn't valid (%r)", raw)
        return None
    return parsed


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
        # Fixed when the controller was added (see config_flow.py), so stored numbers never change meaning
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
        if not isinstance(data, dict):
            data = {}
        if "water" not in data:  # a bare {zone: total} file (no last watering time): wrap it in the full shape
            data = {"water": data}
        self.water = clean_water(data["water"])
        self.last_start = clean_last_start(data.get("last_start"))

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
            # The token was changed in the Yardian app: Home Assistant asks the user for the new one.
            raise ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="invalid_auth") from err
        except Exception as err:  # noqa: BLE001 - pyyardian raises several types; any of them means "unreachable"
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err

        # The controller's answers are checked before anything uses them: a zone list that isn't a list makes this
        # poll fail (entities show unavailable until a good one arrives), and running zones that aren't real zone
        # numbers are ignored, so they can't be credited water or crash an entity.
        zones = clean_zones(state.zones)
        if zones is None:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="bad_response")
        active = clean_active(state.active_zones, len(zones))
        if not isinstance(oper, dict):
            oper = {}
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

        return {"zones": zones, "active": active, "oper": oper}
