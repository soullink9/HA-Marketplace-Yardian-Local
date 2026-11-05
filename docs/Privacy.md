# Privacy

## What leaves your Home Assistant

**Nothing calls out to the internet.** The integration talks only to the controller's address you entered, on your
own network, through the [pyyardian](https://github.com/aeon-matrix/pyyardian) library. There's no cloud connection,
analytics or update check.

The blueprint only reads entities already in your Home Assistant (your weather sensors, forecast and town sensors) and
sends notifications through your own notify actions.

## What's stored in Home Assistant

- **The controller's address and access token**, plus the device information it reported at setup (Yardian ID,
  model, serial number), in Home Assistant's own configuration storage.
- **Run times and flow rates**, as the number entities' saved states.
- **Water totals and the last watering time**, in `/config/.storage/yardian_local.<entry id>.water`.

## Sharing diagnostics and logs

The diagnostics download removes the access token, Yardian ID, serial number and IOTC ID, so it's safe to attach to
an issue. Logs aren't filtered the same way: check them for anything private before posting.
