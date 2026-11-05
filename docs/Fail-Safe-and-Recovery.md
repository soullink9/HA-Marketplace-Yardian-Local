# Fail-Safe and Recovery

A sprinkler schedule has two jobs that matter more than any feature: **never leave water running**, and **never
water twice in a day**. This page explains how Yardian Local and its blueprint keep both promises, and what happens
when Home Assistant or the controller goes down.

## Water never keeps running

**Every start carries a duration.** Nothing in this integration starts a zone without telling the controller how
long to run it. The zone switches send the zone's run time, and the blueprint sends each zone's minutes through
`yardian_local.start_irrigation`. The controller stops the zone on its own timer, so if Home Assistant crashes, loses
power or loses the network mid-cycle, the zone still stops on time.

On top of that, Home Assistant watches too:

- **The safety cap.** The blueprint never runs a zone longer than **Max minutes per zone**. If any selected zone is
  on for longer than the cap plus 2 minutes, however it was started (the app, the controller's own schedule, a
  person), the blueprint presses **Stop all** and tells you.
- **Each zone is checked.** If a zone doesn't come on within 2 minutes of being started, or is still on 2 minutes
  after it should have finished, the blueprint presses **Stop all**, ends the cycle and tells you.
- **At startup.** When Home Assistant starts and finds a selected zone running, it stops it (unless you turned
  **Stop any running zone when Home Assistant starts** off).

## Never watering twice in a day

Before starting, the blueprint checks two things, and skips today if either shows today's cycle already started:

1. **The automation's own last run time.**
2. **The integration's Last watering sensor.** It records when watering last began, from any source: the blueprint,
   a zone switch, the Yardian app or the controller's own schedule. It's saved to disk **immediately** (not after the
   usual delay), so it survives a power cut a second later.

Because the second check is stored by the integration, a crash, restart or power cut can't make the blueprint forget
that today was handled.

## When Home Assistant goes down

| Situation | What happens |
|---|---|
| Down **mid-cycle** | The running zone stops on the controller's timer. The rest of today's zones don't run (today counts as watered). |
| Down at the **scheduled start**, back within the late-start window | The cycle starts as soon as Home Assistant is back (after waiting up to 5 minutes for your sensors to load), with "Late start" in the notification. |
| Down at the scheduled start, back **after** the window | Today is skipped and you're told when it came back. Tomorrow runs as normal. |
| Back with water running | That zone is stopped at startup (unless turned off in the settings). |

## When the controller goes down

| Situation | What happens |
|---|---|
| Offline at the scheduled start | The blueprint waits for it, at most until the late-start window ends. If it's back in time, the cycle runs; if not, today is skipped and you're told. |
| Comes back online later, still within the window | The cycle starts then. |
| Offline mid-cycle | The zone that was running stops on the controller's own timer if the controller is still powered. The blueprint can't see it finish, so 2 minutes after its time is up it presses Stop all, ends the cycle and tells you. |

The **Stop all** button goes unavailable while the controller can't be reached; that's how the blueprint knows.

## Never too early, never twice from different triggers

- The blueprint only starts within a minute of the scheduled time (or later, in recovery). It never starts early.
- Only one run at a time: if a run is already in progress, other triggers don't start another.
- Before the first zone, any zone already running is stopped, so two zones never run at once.

## What it can't protect against

- **A zone started outside Home Assistant while Home Assistant is down** runs for whatever duration it was given
  there; nothing in Home Assistant can stop it until it's back.
- **The controller's own schedule** in the Yardian app still runs if you leave it on. Turn it off if the blueprint is
  your schedule.

See also [Known Limitations](Known-Limitations.md).
