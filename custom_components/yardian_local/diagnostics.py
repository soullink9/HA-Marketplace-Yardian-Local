"""Diagnostics download (Settings → Devices & services → Yardian Local → ⋮ → Download diagnostics).

Shows what the controller actually reports, which is the quickest way to support a new model or field.
Identifiers and network details are redacted so the file is safe to attach to an issue.
"""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from .coordinator import YardianConfigEntry

# The controller's API isn't documented and differs between models, so fields are redacted by what their name
# looks like rather than by an exact list: the access token, Yardian ID, serial number and IOTC ID, and anything
# about its network (host name, IP and MAC addresses, Wi-Fi name and password) or its location. Names are matched
# without case and without "_", "-" or spaces, so "sIotcUid", "mac_address" and "wifiSSID" are all caught.
_SECRET_KEY = re.compile(
    r"token|yid|serial|uid|passw|psk|secret|host|mac|ssid|wifi|wlan|ipaddr|ipv[46]|gateway|netmask|subnet|dns"
    r"|address|latitude|longitude|location|email"
)
# Short names that would match too much as a fragment ("ip" is in "zip"), so only the whole name, or the name with
# a one-letter type prefix the controller uses ("sIp"), is redacted.
_SECRET_NAME = re.compile(r"[a-z]?(ip|lat|lon|lng|gps|geo)")
# Values that are network addresses are redacted whatever their field is called.
_SECRET_VALUE = re.compile(
    r"\d{1,3}(\.\d{1,3}){3}(:\d+)?"  # IPv4 address, optionally with a port
    r"|[0-9a-f]{2}([:-][0-9a-f]{2}){5}"  # MAC address
    r"|[0-9a-f]{1,4}(:[0-9a-f]{1,4}){7}|(?=.*::)[0-9a-f:]{2,39}",  # IPv6 address, in full or shortened with "::"
    re.IGNORECASE,
)


def _is_secret_key(key: Any) -> bool:
    """True if a field with this name may identify the controller, its network or its location."""
    name = re.sub(r"[\s_-]", "", str(key)).lower()
    return bool(_SECRET_KEY.search(name) or _SECRET_NAME.fullmatch(name))


def redact(data: Any) -> Any:
    """Return ``data`` with identifying fields and network addresses replaced by ``**REDACTED**``, at any depth."""
    if isinstance(data, dict):
        return {key: REDACTED if _is_secret_key(key) else redact(value) for key, value in data.items()}
    if isinstance(data, list | tuple):
        return [redact(item) for item in data]
    if isinstance(data, str) and _SECRET_VALUE.fullmatch(data.strip()):
        return REDACTED
    return data


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: YardianConfigEntry) -> dict[str, Any]:
    """Return the controller's raw device info, operating info and zone list."""
    coordinator = entry.runtime_data
    return {
        "device_info": redact(coordinator.raw_info),
        "oper_info": redact(coordinator.data["oper"]),
        "zones": redact(coordinator.data["zones"]),
        "active": sorted(coordinator.data["active"]),
    }
