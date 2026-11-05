# Disclosure

This project was primarily created for personal use and for my family. While I may provide updates, they are not guaranteed. However, if you've stumbled upon this and find it interesting, feel free to download and use it. I had a great time building this and hope you enjoy it.

Note: Built with the assistance of Claude.ai. I’m putting it here now so you don't have to hunt for it below.

<p align="center">
  <img src="docs/images/logo.png" alt="soullink9 logo" width="200">
</p>

# Yardian Local: fail-safe lawn watering

A local-only Home Assistant integration for Yardian sprinkler controllers, plus a blueprint that runs your watering schedule and keeps running safely when Home Assistant doesn't.

[![Open your Home Assistant instance and open this repository in the Marketplace.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=soullink9&repository=HA-Marketplace-Yardian-Local&category=integration)

[![Open your Home Assistant instance and start setting up Yardian Local.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=yardian_local)
[![Open your Home Assistant instance and import the watering blueprint.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fsoullink9%2FHA-Marketplace-Yardian-Local%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fyardian%2Fyardian_lawn_schedule.yaml)

- **Local only**: talks to the controller on your network, never to the cloud
- **Fails safe**: every zone is started with a run time, so the controller stops it on its own even if Home Assistant goes down mid-cycle
- **Never waters twice in a day**, even after a crash or power cut, and picks up a missed start when Home Assistant or the controller comes back in time
- zone switches, run times, a stop-all button, and a safety watchdog that stops any zone left on too long
- start at a fixed time, or finish a set time before sunrise (calculated from your home location)
- a watering season, watering days, odd/even dates, and town rules (watering-allowed sensor, bans, drought level, trash pickup days)
- weather skips from your own rain, rain-rate and temperature sensors and an hourly forecast, all unit-aware
- estimated water use per zone and in total, ready for the **Energy dashboard**
- notifications to any of your phones, including season start and end reminders
- no YAML and no helpers to create: everything is set in the UI

## Install

**Needs:** Home Assistant 2026.9 or newer and a Yardian controller on your network with its access token (shown in the Yardian app).

1. **Download.** Install **Yardian Local** from the Marketplace (**Settings → Marketplace**, Home Assistant 2026.11 and newer), or copy the [`custom_components/yardian_local`](custom_components/yardian_local) folder into `/config/custom_components/` and restart Home Assistant.
2. **Add your controller.** Press the first button above, or go to **Settings → Devices & services → Add integration → Yardian Local**, and enter its IP address and access token. If you use Home Assistant's built-in Yardian integration, remove it so the controller isn't polled twice.
3. **Set run times.** On the controller's device page, set each zone's **run time** (0 skips a zone) and the **Flow rate** if you want water estimates.
4. **Schedule.** Press the second button above to import the blueprint, then create an automation from it and pick your zones and the Stop all button. Every other setting is optional.

The [Installation](docs/Installation.md) page has the details, including updating and removing.

## Documentation

The other pages here cover everything else:

| Page | What's in it |
|---|---|
| [Installation](docs/Installation.md) | Download, setup, the blueprint, updating and removing. |
| [Blueprint Settings](docs/Blueprint-Settings.md) | Every setting: schedule, season, recovery, weather, local rules and notifications. |
| [Fail-Safe and Recovery](docs/Fail-Safe-and-Recovery.md) | What happens when Home Assistant or the controller goes down, and why it never waters twice. |
| [Entities and Actions](docs/Entities-and-Actions.md) | Every entity, the two actions, and the diagnostics download. |
| [Water Usage and Energy](docs/Water-Usage-and-Energy.md) | Finding your flow rate and adding the totals to the Energy dashboard. |
| [Known Limitations](docs/Known-Limitations.md) | What it can't do (yet). |
| [Privacy](docs/Privacy.md) | What leaves your Home Assistant. |
| [Development](docs/Development.md) | The file map and the checks. |

## Privacy

Nothing calls out to the internet. The integration talks only to the controller's address you enter, on your own network. See [Privacy](docs/Privacy.md).

## Contributing

Bug reports and pull requests are welcome: [open an issue](https://github.com/soullink9/HA-Marketplace-Yardian-Local/issues/new/choose). [CONTRIBUTING.md](CONTRIBUTING.md) covers how the code is laid out, how to run the checks and how to release a new version.

## Credits
Work from other people in this project:
- The controller is reached through [pyyardian](https://github.com/aeon-matrix/pyyardian) by Aeon Matrix, installed as a dependency.
- `config_flow.py`, `coordinator.py`, the zone switches and the Standby sensor are adapted from Home Assistant's built-in [Yardian integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/yardian) (Home Assistant Core, [Apache License 2.0](https://github.com/home-assistant/core/blob/dev/LICENSE.md)): the setup with host and access token, how the controller is polled and its errors handled, the zone's enabled flag, and reading standby from `iStandby`. The `start_irrigation` action keeps the built-in integration's name and limits so automations carry over.
- The blueprint's sunrise calculation uses NOAA's [General Solar Position Calculations](https://gml.noaa.gov/grad/solcalc/solareqns.PDF) (public domain).
- The icon is original artwork made for this project. Yardian and Aeon Matrix are trademarks of Aeon Matrix; this project is not affiliated with or endorsed by them.

Everything else was written for this project, with help from Claude, Anthropic's AI model.

## License
[GNU General Public License v3.0](LICENSE). You may use, study, share and change Yardian Local; if you share a changed version, share its source under the same licence.
