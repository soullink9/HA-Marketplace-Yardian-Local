"""Diagnostics download (Settings → Devices & services → Yardian Local → ⋮ → Download diagnostics).

Shows what the controller actually reports, which is the quickest way to support a new model or field.
Identifiers are redacted so the file is safe to attach to an issue.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import YardianConfigEntry

REDACT = {CONF_ACCESS_TOKEN, "yid", "serialNumber", "sIotcUid"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: YardianConfigEntry) -> dict[str, Any]:
    """Return the controller's raw device info, operating info and zone list."""
    coordinator = entry.runtime_data
    return {
        "device_info": async_redact_data(coordinator.raw_info, REDACT),
        "oper_info": async_redact_data(coordinator.data["oper"], REDACT),
        "zones": coordinator.data["zones"],
        "active": sorted(coordinator.data["active"]),
    }
