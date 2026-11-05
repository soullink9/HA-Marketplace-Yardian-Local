# Entities and Actions

Each controller is one device, named as in the Yardian app. Zone entities use the zone names from the Yardian app.
The controller is polled every 15 seconds.

## Per zone

| Entity | What it does |
|---|---|
| **`<zone>`** (switch) | On while the zone runs. Turning it on runs it for its **run time**; turning it off stops it. Unavailable if the zone is disabled in the Yardian app. Attributes: `zone` (1-based number) and `run_minutes`. |
| **`<zone>` run time** (number, configuration) | Minutes the zone runs when switched on, and what the blueprint uses. 0–120; 0 skips the zone. New zones start at 10. |
| **`<zone>` flow rate** (number, configuration, **disabled by default**) | This zone's own flow rate, for a zone that uses noticeably more or less water than the rest. Left at 0, the zone uses the shared **Flow rate**. |
| **`<zone>` water used** (sensor) | Estimated water this zone has used, in gallons or litres. Only ever goes up. |

On Yardian Pro (YP) models, turning one zone off stops **every** running zone; the library can only stop everything
on those models. The blueprint runs one zone at a time, so that doesn't matter there.

## For the controller

| Entity | What it does |
|---|---|
| **Stop all** (button) | Stops every running zone. Unavailable while the controller can't be reached; the blueprint uses that. |
| **Watering** (binary sensor) | On while any zone runs. |
| **Active zone** (sensor) | The name of the running zone(s), or `Idle`. |
| **Last watering** (sensor, timestamp) | When watering last began, from Home Assistant or anywhere else. Stays readable while the controller is offline. The blueprint uses it to never water twice a day. |
| **Water used** (sensor) | Estimated water used by all zones together, in gallons or litres. Only ever goes up; ready for the Energy dashboard. |
| **Flow rate** (number, configuration) | The flow rate every zone uses for the water estimate, in gal/min or L/min. 0 means no estimate. |
| **Standby** (binary sensor, diagnostic) | On while the controller is in standby, as set in the Yardian app. Read only. |
| **Rain delay** (sensor, diagnostic) | The controller's own rain delay, as it reports it. Read only. |

Run times and flow rates live in Home Assistant, not on the controller. They stay editable while the controller is
offline, and they're restored after a restart. Water totals and the last watering time are saved in
`/config/.storage/`.

The device page also shows the model, serial number and firmware when the controller reports them.

## Actions

### `yardian_local.start_irrigation`

Runs a zone for a set number of minutes. The controller stops it on its own.

```yaml
action: yardian_local.start_irrigation
target:
  entity_id: switch.front_lawn
data:
  duration: 15  # minutes, 1 to 1440
```

It has the same name and limits as the built-in Yardian integration's action, so automations carry over.

### `yardian_local.notify`

Sends one notification to several notify actions, and **never fails**: a target that doesn't exist (a phone that was
removed or renamed) or that errors is skipped and logged, and the others still get the message. In an automation,
a failing notify action would otherwise stop everything after it, which for a sprinkler schedule means no watering.

```yaml
action: yardian_local.notify
data:
  targets:
    - notify.mobile_app_pixel_9
    - notify.family
  title: Sprinklers
  message: Done for today.
```

A target without a dot is treated as a `notify.` action.

## Diagnostics download

**Settings → Devices & services → Yardian Local → ⋮ → Download diagnostics** gives the controller's raw device
information, operating information and zone list. The access token, Yardian ID, serial number and IOTC ID are
removed, so the file is safe to attach to an issue. It's the quickest way to support a new model.
