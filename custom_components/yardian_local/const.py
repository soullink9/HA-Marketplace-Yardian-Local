"""Constants for the Yardian Local integration.

Changing a value here changes behaviour for everyone, so each one says why it is what it is.
"""

from datetime import timedelta

DOMAIN = "yardian_local"
MANUFACTURER = "Aeon Matrix"  # maker of the Yardian controllers

# How often the controller is polled. 15 s keeps the zone switches and the water estimate close to
# real time without loading the controller; the official integration uses 30 s.
UPDATE_INTERVAL = timedelta(seconds=15)

# Water is estimated from the time between two polls. If polls stop for a while (controller offline,
# Home Assistant busy) we never credit more than this many seconds at once, so a long gap can't
# invent water that may not have flowed.
MAX_POLL_GAP = 60

# Water totals are written to disk at least this often while a zone is running, so a crash or power
# cut loses at most this many seconds of counting.
SAVE_EVERY = 60

# A zone start seen by polling within this long after Home Assistant itself started a zone is the same
# start, so it doesn't overwrite "last watering" again.
SAME_START = timedelta(minutes=2)

# Run time new zones get before the user sets their own (minutes).
DEFAULT_RUN_MINUTES = 10

# Storage file under .storage/ holding the water totals and the last watering time.
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN + ".{entry_id}.water"

# Entry data key that fixes the unit system on first setup ("imperial" or "metric").
CONF_UNITS = "units"
