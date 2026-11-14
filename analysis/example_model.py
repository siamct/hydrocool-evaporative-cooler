"""
Produce an example log file from a simple thermal model, so plot_log.py can
be demonstrated without a Pico attached.

The data in data/example_log.csv comes from this script, not from a
measurement. It uses a lumped model: the store air moves towards the
wet-bulb temperature of the incoming air at a rate set by the fan, and
towards the outside temperature through the walls. Outside conditions follow
a warm afternoon that cools into the evening.

    python example_model.py            writes ../data/example_log.csv
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware"))

from controller import FanController  # noqa: E402  (same logic as the Pico runs)
from wetbulb import wet_bulb_c        # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "example_log.csv")

HOURS = 6.0
STEP_S = 10          # control period, as on the Pico
LOG_EVERY_S = 60


def outside_conditions(t_s):
    """Warm afternoon: 27 C and 45 % RH, falling to 19 C and 65 % RH over six hours."""
    frac = t_s / (HOURS * 3600)
    temp = 27.0 - 8.0 * (0.5 - 0.5 * math.cos(math.pi * frac))
    rh = 45.0 + 20.0 * (0.5 - 0.5 * math.cos(math.pi * frac))
    return temp, rh


def main():
    rng = random.Random(3)
    control = FanController(target_c=18.0, hysteresis_c=1.0, purge_rh=85.0, purge_off_rh=75.0, wet_bulb_margin_c=0.5)

    t_in = 26.0            # store starts at room temperature
    rh_in = 50.0
    rows = []
    last_log = -LOG_EVERY_S

    for t_s in range(0, int(HOURS * 3600), STEP_S):
        t_out, rh_out = outside_conditions(t_s)
        wb = wet_bulb_c(t_out, rh_out)

        duty = control.update(t_in + rng.gauss(0, 0.1), rh_in + rng.gauss(0, 1.0), t_out, rh_out)

        # Air exchange through the wet cloth cools towards the wet bulb; the
        # cloth is never a perfect pad, so the best it reaches is part way.
        efficiency = 0.55
        supply_temp = t_out - efficiency * (t_out - wb)
        k_fan = 0.0009 * (duty / 1.0) + 0.00005      # per second; natural draught when the fan is off
        k_wall = 0.00006                             # heat leaking through the polystyrene walls
        t_in += (k_fan * (supply_temp - t_in) + k_wall * (t_out - t_in)) * STEP_S

        # Humidity inside rises when air is still and drops when the fan purges.
        rh_target = 92.0 if duty == 0 else 70.0 + 10.0 * (1 - duty)
        rh_in += (rh_target - rh_in) * 0.002 * STEP_S

        if t_s - last_log >= LOG_EVERY_S:
            rows.append((1, t_s, t_in, rh_in, t_out, rh_out, wb, duty, 0, control.reason))
            last_log = t_s

    with open(OUT, "w", newline="") as f:
        f.write("session,uptime_s,t_in_c,rh_in,t_out_c,rh_out,wet_bulb_out_c,fan_duty,water_low,reason\n")
        for r in rows:
            f.write("%d,%d,%.1f,%.1f,%.1f,%.1f,%.2f,%.2f,%d,%s\n" % r)
    print("wrote %d rows to %s" % (len(rows), os.path.normpath(OUT)))


if __name__ == "__main__":
    main()
