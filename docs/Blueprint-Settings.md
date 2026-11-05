# Blueprint Settings

Every setting in the **Yardian – fail-safe lawn watering** blueprint, in the order the form shows them. Only the
**zones** and the **Stop all button** are required.

## Controller

| Setting | Default | What it does |
|---|---|---|
| **Zones (in run order)** | | The zone switches to run, one at a time, in this order. Each runs for its **run time** number on the controller's device page; a zone with 0 is skipped. |
| **Stop-all button** | | The controller's **Stop all** button. Used for every safety stop, and to tell whether the controller is reachable. |
| **Max minutes per zone (safety cap)** | 35 | No zone runs longer than this, even if its run time is higher. Any selected zone that stays on longer than this plus 2 minutes, however it was started, is stopped. |
| **Pause between zones** | 30 s | Wait between one zone ending and the next starting. |

## Schedule

| Setting | Default | What it does |
|---|---|---|
| **Start mode** | Finish before sunrise | **Finish before sunrise** works out the start time each day so the cycle ends before sunrise. **Fixed start time** always starts at the same time. |
| **Finish this long before sunrise** | 30 min | Sunrise mode only. 0 finishes right at sunrise. |
| **Fixed start time** | 04:00 | Fixed mode only. |
| **Watering days** | every day | The days of the week to water. |
| **Season starts / Season ends** | Jan 1 – Dec 31 | Only the month and day are used. Outside the season nothing waters. A season can cross New Year (Oct 1 – Apr 30). Leave Jan 1 – Dec 31 to water all year. |

**How sunrise mode works out the start:** it adds up the run time of every zone that will run (capped, plus a
minute each) and the pauses between them, then starts that long, plus your offset, before sunrise. Sunrise is
calculated from your home location (**Settings → System → General**) to within about two minutes; there's no sun
sensor to pick. If the cycle is so long it would have to start before midnight, it starts at midnight. Without a home
location, sunrise mode can't run (you're notified); use a fixed start time instead.

## Recovery after downtime

| Setting | Default | What it does |
|---|---|---|
| **Late-start window** | 60 min | If Home Assistant or the controller comes back within this long after the scheduled start, and today hasn't been watered, the cycle starts then. Later than that, today is skipped and you're told. 0 means no late starts. |
| **Stop any running zone when Home Assistant starts** | on | When Home Assistant starts and a selected zone is running, it's stopped. |

[Fail-Safe and Recovery](Fail-Safe-and-Recovery.md) explains what happens in each situation.

## Weather skips

All optional: leave a sensor empty to turn that check off. Sensor values are converted automatically, so set the
thresholds in the **Threshold units** you pick, whatever units your sensors report.

| Setting | Default | What it does |
|---|---|---|
| **Threshold units** | Imperial | Inches and °F, or millimetres and °C, for the thresholds below. |
| **Rain in the last day** | | A rain **total** for roughly the past day ("Daily rain", "24h rain"). Not an event, hourly, weekly or yearly total, and not a rain rate. |
| **Skip if rain in the last day is at least** | 0.25 in | About 6 mm in metric. |
| **Rain rate** | | A rain **rate** sensor (in/h or mm/h). Checked at the start and again **before every zone**, so rain that starts mid-cycle ends the cycle. |
| **Skip if rain rate is above** | 0 | 0 skips on any rain at all. |
| **Outdoor temperature** | | Your outdoor air temperature. |
| **Skip if temperature (now or forecast) is below** | 40 °F | About 4 °C. Also applies to the forecast low. |
| **Forecast** | | A weather entity with an **hourly** forecast (Met.no, NWS, OpenWeatherMap…). |
| **Forecast look-ahead** | 12 h | How far ahead the forecast checks look. |
| **Skip if chance of rain is at least** | 60 % | The highest hourly chance of rain in the look-ahead. |
| **Skip if forecast rain total is at least** | 0.25 in | The rain forecast across the look-ahead, added up. |

A sensor that's unavailable or not a number is ignored, so a broken weather station never stops watering on its own.
If the forecast can't be fetched, the forecast checks are skipped.

## Local watering rules

All optional. A sensor that's unavailable is ignored rather than blocking watering.

| Setting | Default | What it does |
|---|---|---|
| **Watering allowed today** | | A binary sensor that's **on** on days you may water and **off** when you may not. Watering is skipped when it's off. Use this if your town has watering days. |
| **Odd / even day rule** | Any date | For towns that only allow odd or even dates. Works together with **Watering days**: both must allow the day. |
| **Total watering ban** | | A binary sensor that's **on** only when **all** outdoor watering is banned. Don't use a "restrictions in effect" sensor here if watering is still allowed on some days; use **Watering allowed today** for that. |
| **Drought level** | | A sensor showing a US Drought Monitor level such as "D1 Moderate drought". Only the D0–D4 part is read. |
| **Skip at or above drought level** | Never | The level at which to stop watering. |
| **Skip on pickup days** | | Date sensors such as "Next trash pickup". Watering is skipped on the day any of them shows, so bins and crews at the curb don't get sprayed. |

## Notifications

| Setting | Default | What it does |
|---|---|---|
| **Phones / tablets** | | Devices with the Home Assistant Companion app. |
| **Other notify actions** | | Advanced: other notify actions such as `notify.family`, separated by commas. |
| **Notify on** | all | **Cycle started**, **Cycle finished**, **Skipped** (weather, rules, late recovery), **Safety stop / fault**, **Season start / end reminders**. |
| **Season reminder lead time** | 7 days | How long before the season starts and ends to remind you to turn the water on, or to shut it off and winterize. 0 is on the day. Not sent for a Jan 1 – Dec 31 season. |
| **Season reminder time** | 10:00 | When the reminder is sent. |

Notifications go through `yardian_local.notify`, which skips a phone that's been removed or renamed instead of
stopping the automation. A missing phone never stops watering.

## The messages

| Title | When |
|---|---|
| Sprinklers: started | The cycle began (with "Late start" after recovery), with zone count and minutes. |
| Sprinklers: done | Every zone ran. |
| Sprinklers: skipped today | Weather or local rules (with the reasons), or past the late-start window, or the controller stayed offline. |
| Sprinklers: stopped for rain | Rain started mid-cycle, so the rest was skipped. |
| Sprinklers: safety stop | A zone ran past the safety cap and was stopped. |
| Sprinklers: fault | A zone didn't start; the cycle was aborted. |
| Sprinklers: stopped at startup | Water was running when Home Assistant started. |
| Sprinklers: nothing to run | No selected zone is available with a run time above 0. |
| Sprinklers: can't schedule | Sunrise mode without a home location. |
| Sprinklers: season reminder | The season starts or ends soon. |
