"""The integration's own code, run against stand-ins for Home Assistant and a fake controller (tests/stubs.py).

Covers what the security review asked for: the notify action only calls notify actions, malformed controller
answers and damaged saved data don't crash anything or invent water, and the diagnostics file holds no network
details. Nothing here talks to a real controller or a real Home Assistant.

Run:  python3 tests/test_integration.py   (Python's standard library only; prints PASS/FAIL per check)
"""

import asyncio
import logging
import math
import sys

import stubs  # registers the stand-ins; must come before the integration's imports

from custom_components.yardian_local import diagnostics, services
from custom_components.yardian_local.coordinator import YardianCoordinator
from custom_components.yardian_local.number import FlowRate, ZoneRunTime
from custom_components.yardian_local.sensor import RainDelay
from custom_components.yardian_local.switch import YardianZone

FAILURES = []


def check(ok, message):
    """Print one result and remember failures."""
    print(("PASS " if ok else "FAIL ") + message)
    if not ok:
        FAILURES.append(message)


def make_coordinator(client=None):
    hass = stubs.HomeAssistant()
    entry = stubs.FakeEntry()
    coordinator = YardianCoordinator(hass, entry, client or stubs.FakeClient(), {"model": "PRO1902"})
    entry.runtime_data = coordinator
    return hass, entry, coordinator


# ---------------------------------------------------------------- yardian_local.notify


async def test_notify():
    hass = stubs.HomeAssistant()
    services.async_setup_services(hass)
    received = []

    async def record(call):
        received.append(call.data)

    async def broken(call):
        raise RuntimeError("phone gone")

    for domain, name in [("notify", "family"), ("notify", "mobile_app_pixel_9"), ("notify", "broken")]:
        hass.services.async_register(domain, name, broken if name == "broken" else record)
    ran_script = []
    hass.services.async_register("script", "water_now", lambda call: ran_script.append(call))
    hass.services.async_register("shell_command", "family", lambda call: ran_script.append(call))
    hass.services.async_register("homeassistant", "restart", lambda call: ran_script.append(call))

    targets = [
        "notify.family",
        "mobile_app_pixel_9",  # no domain: taken as notify.mobile_app_pixel_9
        "script.water_now",
        "shell_command.family",
        "homeassistant.restart",
        "notify.script.water_now",  # a name with a dot in it, aimed at another domain
        "notify.",
        "notify.missing",
        "notify.broken",
        "../notify.family",
    ]
    await hass.services.call_validated("yardian_local", "notify", {"targets": targets, "title": "T", "message": "M"})
    called = [(domain, name) for domain, name, _ in hass.services.calls]
    check(not ran_script, "notify: script., shell_command. and homeassistant. targets are never called")
    check(all(domain == "notify" for domain, _ in called), f"notify: only notify actions are called ({called})")
    check(
        called == [("notify", "family"), ("notify", "mobile_app_pixel_9"), ("notify", "broken")],
        "notify: valid targets still get the message, in order, past invalid, missing and failing ones",
    )
    check(received == [{"title": "T", "message": "M"}] * 2, "notify: each target gets the title and message")

    hass.services.calls.clear()
    await hass.services.call_validated("yardian_local", "notify", {"targets": "NOTIFY.Family", "message": "M"})
    check(
        hass.services.calls[:1] == [("notify", "family", {"title": None, "message": "M"})],
        "notify: case and a single target are accepted",
    )

    for name, target in [("a dict", {"domain": "script"}), ("None", None)]:
        try:
            await hass.services.call_validated("yardian_local", "notify", {"targets": [target], "message": "M"})
            rejected = False
        except stubs.Invalid:
            rejected = True
        check(rejected, f"notify: a target that isn't text ({name}) is refused by the schema")

    for target, expected in [("notify.family", "family"), ("family", "family"), (" notify.Family ", "family")]:
        check(services.notify_action_name(target) == expected, f"notify_action_name({target!r}) is {expected!r}")
    for target in ["script.x", "notify.a.b", "notify.", "", "notify.fam ily", "light.kitchen", "notify.x;y"]:
        check(services.notify_action_name(target) is None, f"notify_action_name({target!r}) is refused")


# ---------------------------------------------------------------- controller answers


async def test_controller_data():
    client = stubs.FakeClient(zones=[["Front", 1], ["Back", 0], "junk", ["Short"]], active={0, 3, 7, -1, True, "1"})
    hass, entry, coordinator = make_coordinator(client)
    await coordinator.async_refresh()
    data = coordinator.data
    check(coordinator.last_update_success, "controller: a zone list with malformed entries still loads")
    check(
        data["zones"][2] == ["Zone 3", 0] and data["zones"][3] == ["Zone 4", 0],
        "controller: malformed zones become disabled placeholders",
    )
    check(
        data["active"] == {0, 3},
        f"controller: running zones outside the list, negative, bool or text are ignored ({data['active']})",
    )
    zones = [YardianZone(coordinator, zone) for zone in range(4)]
    check(
        [zone.available for zone in zones] == [True, False, False, False],
        "controller: placeholder zones' switches are unavailable",
    )

    # The controller later reports fewer zones than at setup: the extra switches go unavailable, not IndexError.
    client.zones, client.active = [["Front", 1]], [5]
    await coordinator.async_refresh()
    try:
        states = [zone.available for zone in zones]
        crashed = None
    except IndexError as err:
        states, crashed = None, err
    check(
        crashed is None and states == [True, False, False, False],
        f"controller: a zone that disappeared is unavailable ({crashed or states})",
    )

    for bad in [None, "zones", 5, {"0": ["Front", 1]}]:
        client.zones = bad
        await coordinator.async_refresh()
        check(
            not coordinator.last_update_success, f"controller: a zone list that isn't a list ({bad!r}) fails the poll"
        )

    client.zones, client.active = [["Front", 1]], None
    await coordinator.async_refresh()
    check(
        coordinator.last_update_success and coordinator.data["active"] == set(),
        "controller: no running-zone list means none running",
    )

    sensor = RainDelay(coordinator, "rain_delay")
    for raw, expected in [(3600, 3600), (0, 0), (-5, None), ("3600", None), (True, None), (1.5, None), (None, None)]:
        client.oper = {"iRainDelay": raw}
        await coordinator.async_refresh()
        check(sensor.native_value == expected, f"rain delay: {raw!r} shows as {expected!r}")
    client.oper = ["not", "a", "dict"]
    await coordinator.async_refresh()
    check(
        coordinator.last_update_success and coordinator.data["oper"] == {},
        "controller: operating info that isn't a dict is ignored",
    )


# ---------------------------------------------------------------- saved data


async def test_saved_data():
    cases = [
        (
            "valid file",
            {"water": {"0": 12.5, "1": 3}, "last_start": "2026-11-20T06:00:00+00:00"},
            {0: 12.5, 1: 3.0},
            True,
        ),
        ("bare {zone: total} file", {"0": 4.0}, {0: 4.0}, False),
        ("empty file", None, {}, False),
        ("NaN, infinity, negative", {"water": {"0": "nan", "1": "inf", "2": -3, "3": 1.0}}, {3: 1.0}, False),
        ("non-numeric total and zone", {"water": {"0": "lots", "x": 2, "4": None, "5": [1]}}, {}, False),
        ("negative zone", {"water": {"-1": 2}}, {}, False),
        ("water not a dict", {"water": [1, 2, 3]}, {}, False),
        ("file not a dict", [1, 2, 3], {}, False),
        ("bad last_start", {"water": {}, "last_start": "yesterday"}, {}, False),
        ("last_start not text", {"water": {}, "last_start": 12345}, {}, False),
        ("last_start in the future", {"water": {}, "last_start": "2999-01-01T06:00:00+00:00"}, {}, False),
        ("last_start without a time zone", {"water": {}, "last_start": "2026-11-20T06:00:00"}, {}, False),
    ]
    for name, saved, water, has_start in cases:
        _, _, coordinator = make_coordinator()
        coordinator._store.saved = saved
        try:
            await coordinator.async_load()
            error = None
        except Exception as err:  # noqa: BLE001 - any exception is the failure being tested for
            error = err
        ok = error is None and coordinator.water == water and (coordinator.last_start is not None) == has_start
        check(
            ok,
            f"saved data, {name}: loads as {water}, last watering {'kept' if has_start else 'none'} ({error or coordinator.water})",
        )
        check(
            all(math.isfinite(v) and v >= 0 for v in coordinator.water.values()),
            f"saved data, {name}: every total is finite and >= 0",
        )

    _, _, coordinator = make_coordinator()
    await coordinator.async_refresh()
    for cls, zone, restored, expected in [
        (ZoneRunTime, 0, 25.0, 25.0),
        (ZoneRunTime, 0, math.nan, 10),
        (ZoneRunTime, 0, math.inf, 10),
        (ZoneRunTime, 0, -1.0, 10),
        (ZoneRunTime, 0, 10_000.0, 10),
        (ZoneRunTime, 0, None, 10),
        (FlowRate, None, 7.5, 7.5),
        (FlowRate, None, math.nan, 0.0),
        (FlowRate, None, 500.0, 0.0),
    ]:
        entity = cls(coordinator, zone)
        entity.last_number_data = type("Last", (), {"native_value": restored})() if restored is not None else None
        await entity.async_added_to_hass()
        check(
            entity.native_value == expected,
            f"restored {cls.__name__} {restored!r} becomes {expected!r} ({entity.native_value!r})",
        )


# ---------------------------------------------------------------- water estimate, now that data is checked


async def test_water_estimate():
    client = stubs.FakeClient(zones=[["Front", 1], ["Back", 1]], active=[0, 9])
    _, _, coordinator = make_coordinator(client)
    coordinator.flow[None] = 6.0
    await coordinator.async_refresh()
    coordinator._last_poll -= 30  # 30 seconds pass
    await coordinator.async_refresh()
    check(set(coordinator.water) == {0}, f"water: only real running zones are credited ({coordinator.water})")
    check(abs(coordinator.water[0] - 3.0) < 0.1, f"water: 30 s at 6 L/min is about 3 L ({coordinator.water[0]:.2f})")


# ---------------------------------------------------------------- diagnostics


async def test_diagnostics():
    client = stubs.FakeClient(
        zones=[["Front", 1], ["Back", 1]],
        oper={
            "sIotcUid": "IOTC-123",
            "iRainDelay": 0,
            "iStandby": 0,
            "region": "US",
            "iMasterValveId": 3,
            "iTimezoneOffset": -28800,
            "sIp": "192.168.1.50",
            "wifi": {"sSSID": "HomeNet", "password": "hunter2", "rssi": -60},
            "network": {"mac_address": "AA:BB:CC:DD:EE:FF", "gateway": "192.168.1.1", "hostname": "yardian-1234"},
            "lat": 37.1,
            "longitude": -122.0,
            "extra": ["10.0.0.7", "fe80::1", "06:00:00", "Front lawn"],
            "sensor1": {"mode": 1},
        },
    )
    _, entry, coordinator = make_coordinator(client)
    coordinator.raw_info = {
        "name": "Yardian",
        "model": "PRO1902",
        "serialNumber": "SN1",
        "yid": "YID1",
        "zones": 8,
        "access_token": "secret",
        "localIP": "192.168.1.50",
        "macAddr": "aa-bb-cc-dd-ee-ff",
        "ssid": "HomeNet",
        "host": "yardian.local",
        "fwVersion": "4.1",
    }
    await coordinator.async_refresh()
    result = await diagnostics.async_get_config_entry_diagnostics(None, entry)
    text = repr(result)
    secrets = [
        "IOTC-123",
        "192.168.1",
        "HomeNet",
        "hunter2",
        "AA:BB",
        "aa-bb",
        "yardian-1234",
        "yardian.local",
        "SN1",
        "YID1",
        "secret",
        "37.1",
        "-122.0",
        "10.0.0.7",
        "fe80::1",
    ]
    leaked = [secret for secret in secrets if secret in text]
    check(not leaked, f"diagnostics: no identifiers, network details or location ({leaked})")
    kept = {
        "model": result["device_info"].get("model"),
        "zones": result["device_info"].get("zones"),
        "fwVersion": result["device_info"].get("fwVersion"),
        "iRainDelay": result["oper_info"].get("iRainDelay"),
        "region": result["oper_info"].get("region"),
        "iMasterValveId": result["oper_info"].get("iMasterValveId"),
        "iTimezoneOffset": result["oper_info"].get("iTimezoneOffset"),
        "sensor1": result["oper_info"].get("sensor1"),
    }
    check(
        kept["model"] == "PRO1902" and kept["zones"] == 8 and kept["fwVersion"] == "4.1" and kept["iRainDelay"] == 0,
        f"diagnostics: the fields that help support a model stay ({kept})",
    )
    check(
        kept["region"] == "US"
        and kept["iMasterValveId"] == 3
        and kept["iTimezoneOffset"] == -28800
        and kept["sensor1"] == {"mode": 1},
        "diagnostics: ordinary operating fields are not over-redacted",
    )
    check("06:00:00" in text and "Front lawn" in text, "diagnostics: times and names aren't mistaken for addresses")
    check(result["zones"] == [["Front", 1], ["Back", 1]], "diagnostics: the zone list is included")


async def main():
    await test_notify()
    await test_controller_data()
    await test_saved_data()
    await test_water_estimate()
    await test_diagnostics()


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)  # the integration logs every skipped target and bad value; the checks say enough
    asyncio.run(main())
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        sys.exit(1)
    print("All checks passed.")
