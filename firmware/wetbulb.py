"""
Psychrometric helpers shared by the firmware and the analysis scripts.

Evaporative cooling cannot take air below its wet-bulb temperature, so the
wet-bulb temperature of the outside air is the theoretical floor for the
store. Comparing the measured inside temperature with it shows how close
the design gets to the limit.

No dependencies beyond math, so it runs on MicroPython too.
"""

import math


def wet_bulb_c(temp_c, rh_percent):
    """
    Wet-bulb temperature from dry-bulb temperature and relative humidity.
    Stull (2011) empirical fit, accurate to about 0.3 C for 5-99 % RH and
    -20 to 50 C, which covers anything a food store will see.
    """
    t = temp_c
    rh = max(1.0, min(100.0, rh_percent))
    return (t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
            + math.atan(t + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
            - 4.686035)


def dew_point_c(temp_c, rh_percent):
    """Magnus formula dew point."""
    a, b = 17.625, 243.04
    rh = max(1.0, min(100.0, rh_percent))
    gamma = math.log(rh / 100.0) + a * temp_c / (b + temp_c)
    return b * gamma / (a - gamma)


def cooling_efficiency(temp_out_c, rh_out_percent, temp_in_c):
    """
    Saturation efficiency of an evaporative cooler: how much of the possible
    wet-bulb depression was achieved, 0..1. Commercial pads reach 0.7-0.9;
    a cloth-lined box does well to reach 0.5.
    """
    wb = wet_bulb_c(temp_out_c, rh_out_percent)
    depression = temp_out_c - wb
    if depression <= 0.1:
        return 0.0
    return max(0.0, min(1.0, (temp_out_c - temp_in_c) / depression))
