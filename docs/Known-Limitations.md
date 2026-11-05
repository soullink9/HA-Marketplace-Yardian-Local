# Known Limitations

What Yardian Local can't do, or doesn't do yet.

## The integration

- **No reconfigure.** To change the controller's IP address or access token, remove the integration and add it again.
  Give the controller a reserved address so this rarely matters. Run times and flow rates set in Home Assistant are
  lost when you remove it, so note them first.
- **New or renamed zones need a reload.** Zones and their names are read when the integration starts. After adding or
  renaming a zone in the Yardian app, reload the integration (**Settings → Devices & services → Yardian Local → ⋮ →
  Reload**).
- **Stopping one zone stops all on Yardian Pro (YP).** The library can only stop everything on those models.
- **Standby and rain delay are read only.** Set them in the Yardian app. The blueprint doesn't read them either; use
  its weather skips, or turn the automation off, to pause watering from Home Assistant.
- **Water use is an estimate**, not a meter reading, and watering while Home Assistant is down isn't counted. See
  [Water Usage and Energy](Water-Usage-and-Energy.md).
- **The water unit can't be changed** after the controller is added (on purpose, to protect the history).
- **The library version follows Home Assistant's.** Home Assistant ships pyyardian for its built-in Yardian
  integration, and that version is the one used, so a fix that needs a newer pyyardian waits until Home Assistant
  Core moves to it.

## The blueprint

- **One zone at a time**, in the order you pick. There's no running zones in parallel, and no cycle-and-soak (splitting
  a zone's time into shorter runs).
- **One cycle a day per automation**, with one set of watering days for all its zones. For a second daily cycle, or
  different days for different zones, make another automation from the blueprint with its own zones, start time and
  days. Give them start times far enough apart that one cycle has finished before the next begins.
- **Sunrise is calculated, not read from a sensor**, to within about two minutes, and a cycle that would have to start
  before midnight starts at midnight.
- **Notifications to Companion app devices** are sent to `notify.mobile_app_<device name>`. If you renamed the
  phone's notify action separately from its device, add it under **Other notify actions** instead.

## Testing

There are no automated tests against a real or simulated controller yet; the blueprint has static checks only. A pull
request adding them is welcome.
