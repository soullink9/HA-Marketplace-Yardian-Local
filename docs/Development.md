# Development

For anyone changing the code. [CONTRIBUTING.md](../CONTRIBUTING.md) has the rules the code keeps, how to check a change
and how to release.

## Files

```
custom_components/yardian_local/
  __init__.py        connects to one controller, fixes the unit system on first setup, sets up the platforms
  const.py           domain, poll interval, water-counting limits, storage key; each value says why
  coordinator.py     polling, the water estimate, saved data (water totals, last watering)
  entity.py          the base entity: device, unique ID, sending commands
  switch.py          a switch per zone, and the start_irrigation action
  number.py          run times and flow rates (kept in Home Assistant, restored after restarts)
  sensor.py          Active zone, Last watering, Rain delay, Water used (total and per zone)
  binary_sensor.py   Watering, Standby
  button.py          Stop all
  services.py        the notify action
  diagnostics.py     the diagnostics download (identifiers removed)
  config_flow.py     the setup form: host and access token
  services.yaml, translations/en.json, brand/
blueprints/automation/yardian/
  yardian_lawn_schedule.yaml   the schedule; its header comment maps the flow
tests/
  test_blueprint.py    static checks for the blueprint
  requirements.txt     what the checks need: PyYAML and Jinja2
docs/    these pages
```

## How data flows

- `YardianCoordinator` polls the controller every 15 seconds (`fetch_device_state`, `fetch_oper_info`). Its `data` is
  the zone list, the set of running zones (0-based) and the operating info. Every entity reads from it.
- The coordinator also holds what lives in Home Assistant: `run_minutes` and `flow` (filled in by the number entities
  from their restored state), `water` and `last_start` (saved in `.storage/`).
- **Water:** each poll credits the zones that were running at the previous poll with the time since then (capped at
  `MAX_POLL_GAP`), at their flow rate, measured with a monotonic clock. One delayed save is scheduled at a time, so it
  isn't pushed back by every poll.
- **Last watering:** `async_mark_start` saves immediately. Zone switches call it when they start a zone, and polling
  calls it when watering starts from anywhere else (not within 2 minutes of a start Home Assistant made).

## How the blueprint decides

Triggers: `schedule` (the minute the cycle should start), `ha_start`, `controller_back` (the Stop all button leaves
`unavailable`), `watchdog` (a zone on longer than the cap plus 2 minutes) and `reminder`.

1. Silent exits: not a watering day, out of season, too early, another run busy, or today already handled (the
   automation's `last_triggered` or the **Last watering** sensor, found through the Stop all button's device).
2. Past the recovery window: notify, stop.
3. Controller offline: wait for it, until the recovery window ends.
4. Weather and local rules: skip with the reasons.
5. Run zones one at a time with `yardian_local.start_irrigation`, checking each starts and stops on time.

**The start time is calculated twice**: in the `schedule` trigger and in the `start_ts` variable. They must stay
identical; `test_blueprint.py` fails if they differ.

## Checks

```sh
pip install -r tests/requirements.txt
ruff check && ruff format --check
python3 tests/test_blueprint.py
```

`test_blueprint.py` catches the easy mistakes in a long hand-edited blueprint: an input defined but never used (or
the reverse), the two start-time calculations drifting apart, a template that doesn't parse, and an action the
blueprint isn't meant to call. There are no automated tests against a controller yet, so try changes on a real controller
before releasing. CI also runs Home Assistant's `hassfest`.
