# Installation

**Needs:** Home Assistant 2026.9 or newer, and a Yardian controller on the same network as Home Assistant, with its
**access token** (shown in the Yardian app).

## From the Marketplace

In Home Assistant 2026.11 and newer, open **Settings → Marketplace**, search for **Yardian Local** and install it, then
restart Home Assistant. Updates then show up under **Settings → Updates**.

If it isn't listed yet, add it from its link instead: this repository's address,
`https://github.com/soullink9/HA-Marketplace-Yardian-Local`. Adding from a link needs Home Assistant to be connected to GitHub.

To install by hand instead, follow the steps below.

## 1. Download

Copy the [`custom_components/yardian_local`](../custom_components/yardian_local) folder from this repository into
`/config/custom_components/` (so you end up with `/config/custom_components/yardian_local/manifest.json`), then
restart Home Assistant.

Home Assistant installs the one library it needs, [pyyardian](https://github.com/aeon-matrix/pyyardian), by itself
on the first start.

## 2. Add the controller

1. Give the controller a fixed (reserved) IP address in your router, so it can't move.
2. Go to **Settings → Devices & services → Add integration → Yardian Local**.
3. Enter the controller's **IP address** and its **access token** from the Yardian app.

Home Assistant checks both before saving. The controller becomes a device with a switch per zone and the entities
listed in [Entities and Actions](Entities-and-Actions.md).

**If you use Home Assistant's built-in Yardian integration, remove it**, so the controller isn't polled twice and the
two don't fight over the zones. Automations that used its `yardian.start_irrigation` action can switch to
`yardian_local.start_irrigation`, which takes the same `duration`.

**The water unit is fixed now.** Water totals and flow rates use gallons if Home Assistant was set to US customary
units when you added the controller, and litres otherwise. Changing Home Assistant's unit system later doesn't change
them, so the Energy dashboard's history stays correct.

## 3. Set run times

On the controller's device page, under **Configuration**:

- Set each zone's **run time** in minutes (0 skips the zone). New zones start at 10 minutes.
- Set **Flow rate** if you want water estimates. [Water Usage and Energy](Water-Usage-and-Energy.md) shows how to
  find it.

These live in Home Assistant, not on the controller, and are kept across restarts. Turning a zone's switch on runs it
for its run time.

## 4. Import the blueprint and schedule

The blueprint is the schedule: it decides when to water, skips for weather and town rules, and runs the zones.

1. Go to **Settings → Automations & scenes → Blueprints → Import blueprint** and paste:
   `https://github.com/soullink9/HA-Marketplace-Yardian-Local/blob/main/blueprints/automation/yardian/yardian_lawn_schedule.yaml`
   (or copy [`blueprints/automation/yardian/yardian_lawn_schedule.yaml`](../blueprints/automation/yardian/yardian_lawn_schedule.yaml)
   into `/config/blueprints/automation/yardian/` and reload automations).
2. Open the blueprint and choose **Create automation**.
3. Pick your **zones** in the order they should run, and the controller's **Stop all** button. Everything else has a
   sensible default; [Blueprint Settings](Blueprint-Settings.md) explains each one.
4. Save.

To pause watering at any time, turn the automation off. If you also use the Yardian app's own schedule, turn that
off, or the lawn may be watered by both.

## Updating

Replace the `yardian_local` folder with the new version from this repository and restart. To update the blueprint,
re-import it from the same address (Home Assistant asks before overwriting) and reload automations. Your automation
keeps its settings. The [changelog](../CHANGELOG.md) lists what changed.

## Removing

1. Delete the automation(s) made from the blueprint.
2. **Settings → Devices & services → Yardian Local → ⋮ → Delete**.
3. Delete the `/config/custom_components/yardian_local` folder and restart.
