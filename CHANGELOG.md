# Changelog

## 1.2.0 (2026-11-04)

- Moved to its own repository, [HA-Marketplace-Yardian-Local](https://github.com/soullink9/HA-Marketplace-Yardian-Local), so it can be installed and updated
  from the Home Assistant Marketplace (Home Assistant 2026.11 and newer). Installing by hand works as before.
- No changes to how the integration works.

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
