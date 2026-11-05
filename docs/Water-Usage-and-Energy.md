# Water Usage and Energy

Yardian controllers have no flow sensor, so the integration **estimates** water use: how long each zone ran,
times its flow rate. Get the flow rate right and the estimate is close; it's not a meter reading.

## Units

Water totals use **gallons** and flow rates **gal/min** if Home Assistant was set to US customary units when you added
the controller, and **litres** and **L/min** otherwise. The unit is fixed at that moment on purpose: if it followed
Home Assistant's unit system, switching the system later would silently turn litres into gallons and break the
Energy dashboard's history.

## Finding your flow rate

The best source is your water meter:

1. Make sure nothing else in the house uses water.
2. Note the meter reading.
3. Run one zone for exactly 5 minutes (set its run time to 5 and turn its switch on).
4. Note the reading again. **Flow rate = (second reading − first) ÷ 5.**

Set that as **Flow rate** on the controller's device page (under **Configuration**). Every zone uses it.

If one zone uses noticeably more or less water (drip lines next to rotors, for example), measure that zone the same
way, enable its own **`<zone>` flow rate** entity (it's disabled by default: open it from the device page and turn on
**Enabled**), and set it there. A zone flow rate left at 0 uses the shared rate.

Without a water meter, your irrigation installer's design sheet often lists gallons per minute per zone.

## Adding it to the Energy dashboard

1. **Settings → Dashboards → Energy**, then in the **Water consumption** section choose **Add water source**.
2. Pick the controller's **Water used** sensor.

Add **either** the total **or** the per-zone sensors, not both, or the water is counted twice.

## How it's counted

- Every 15 seconds, each zone that was running at the previous poll is credited with the time since then, at its flow
  rate.
- After a gap (controller offline, Home Assistant busy), at most 60 seconds is credited at once, so a long gap can't
  invent water that may not have flowed.
- Totals are saved at least once a minute while watering, and when the integration is reloaded or stopped, so a crash
  loses at most about a minute of counting.
- The totals only ever go up. Changing a flow rate only affects watering from then on.

## What isn't counted

- **Watering while Home Assistant is down**, since nothing is polling the controller then.
- **A flow rate of 0** means no estimate for that zone.
