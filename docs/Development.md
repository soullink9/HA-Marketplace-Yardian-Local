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
  README.md            what each test checks
  test_blueprint.py    static checks for the blueprint
  test_release.py      the release scripts, publishing against a fake Gitea
  requirements.txt     what the checks need: PyYAML and Jinja2
scripts/             the release helpers both release workflows use (see Tests and releases below)
.gitea/workflows/    tests and releases on Gitea, the main copy (no GitHub needed)
.github/workflows/   GitHub's checks (hassfest, the Marketplace's) and its copy of each release
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
python3 tests/test_release.py
python3 scripts/build_package.py
```

`test_blueprint.py` catches the easy mistakes in a long hand-edited blueprint: an input defined but never used (or
the reverse), the two start-time calculations drifting apart, a template that doesn't parse, and an action the
blueprint isn't meant to call. There are no automated tests against a controller yet, so try changes on a real controller
before releasing. `test_release.py` checks the release scripts, and `build_package.py` builds the zip, checks it
installs and copies the blueprint next to it. Gitea's runner runs all of these on every push; GitHub runs them too,
plus Home Assistant's `hassfest` and the Marketplace's checks.

## Tests and releases: the files

Gitea is the main copy of this repository; it push-mirrors to GitHub, the public copy people install from.

| File | What it does |
|---|---|
| `.gitea/workflows/test.yml` | Runs every check on each push to Gitea (lint, the tests and building the zip, on Python 3.14), with no actions downloaded from GitHub |
| `.gitea/workflows/release.yml` | Publishes a release on Gitea (Run workflow button, or a pushed version tag); its tag then reaches GitHub through the push mirror |
| `.github/workflows/release.yml` | After any push from Gitea's mirror (or from its Run workflow button), publishes every version tag GitHub has no release for yet, with the same files, title and notes as Gitea's: the copy the Marketplace installs from |
| `.github/workflows/ci.yml` | GitHub's checks on every push: lint, the tests and Home Assistant's `hassfest` (which comes from GitHub, so it runs only there) |
| `.github/workflows/validate.yml` | The Marketplace's own checks (the HACS action), which its catalog requires; GitHub only, for the same reason |
| `scripts/release_notes.py` | Shared by both release workflows: checks the version, gives the release's title, writes the notes (install steps with the zip's address on GitHub, then the changelog section) |
| `scripts/build_package.py` | Builds `dist/yardian_local.zip`, the same bytes every time, and checks it with `check_package.py`; copies `yardian_lawn_schedule.yaml` next to it |
| `scripts/check_package.py` | Checks the zip the way it gets installed: one `yardian_local/` folder, a manifest for that domain at the repository's version, the icon, exactly the integration's files |
| `scripts/publish_gitea_release.py` | Creates or updates the Gitea release and uploads its files, through Gitea's API (standard library only) |
| `scripts/plan_github_releases.py` | Used by the GitHub release workflow: lists the version tags GitHub has no published release for yet, oldest first, and which one becomes "Latest" (standard library only) |
| `tests/test_release.py` | Tests all five scripts, publishing against a fake Gitea server |
