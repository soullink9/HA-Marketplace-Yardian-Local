# Changelog

## Unreleased

### Repository

- Gitea is the main copy: its runner checks every push and publishes releases (`.gitea/workflows/`), with nothing
  downloaded from GitHub, so it keeps working when GitHub can't be reached. Gitea push-mirrors to GitHub, and every
  push from it publishes on GitHub the releases GitHub doesn't have yet, with the same files and notes, where the
  Marketplace installs from.
- The release helpers live in `scripts/` and are used by both: the version check and notes, building the zip, and
  publishing on Gitea. Every release's notes now start with how to install it.
- The release's zip is now always `yardian_local.zip` (it had the version in its name), so
  `.../releases/latest/download/yardian_local.zip` always gets the newest. Each zip is checked before it's published.
  `yardian_lawn_schedule.yaml`, the blueprint, is still published next to it.

## 1.2.0 (2026-11-04)

- Moved to its own repository, [HA-Marketplace-Yardian-Local](https://github.com/soullink9/HA-Marketplace-Yardian-Local), so it can be installed and updated
  from the Home Assistant Marketplace (Home Assistant 2026.11 and newer). Installing by hand works as before.
- Lists its categories, so it shows up in the right place when browsing the Marketplace. No other changes to how
  the integration works.

## 1.1.1 (2026-11-02)

- No changes to the integration.

## 1.1.0 (2026-11-01)

- No changes to the integration.

## 1.0.2 (2026-11-01)

- A new icon: original artwork of a lawn sprinkler, in place of the Aeon Matrix logo. The logo and dark-mode
  images are removed, so Home Assistant shows the icon everywhere.

## 1.0.0 (2026-11-01)

Initial release.

- Yardian Local integration: local-only control of a Yardian controller (host and access token, set up in the UI).
- Zone switches that always send a run time, so the controller stops each zone on its own; a Stop all button.
- Run times and flow rates kept in Home Assistant (no helpers to create), restored after restarts.
- Estimated water use per zone and in total, ready for the Energy dashboard; the unit is fixed at setup so
  changing Home Assistant's unit system later can't corrupt the history.
- Last watering, Active zone, Watering, Standby and Rain delay sensors; firmware on the device page when the
  controller reports it; a diagnostics download.
- `yardian_local.start_irrigation` and `yardian_local.notify` (a notification that skips missing phones instead of
  stopping the automation).
- Brand images for the integration (Home Assistant 2026.3 and newer show them).
- The fail-safe lawn watering blueprint: fixed-time or finish-before-sunrise schedules, a watering season with
  reminders, watering days and odd/even dates, town rules, weather and forecast skips, recovery after Home
  Assistant or the controller comes back, never watering twice in a day, a safety watchdog and notifications.
