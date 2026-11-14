"""
Fan control for the evaporative store. Pure logic, no hardware, so it can be
tested on a PC.

The fan pulls air out of the store. Fresh air comes in through the wet cloth
on the walls and is cooled as the water evaporates. More airflow cools faster
but also uses the water faster, so the fan is run in steps rather than flat out.
"""

from wetbulb import wet_bulb_c


class FanController:
    def __init__(self, target_c, hysteresis_c, purge_rh, purge_off_rh, wet_bulb_margin_c):
        self.target_c = target_c
        self.hysteresis_c = hysteresis_c
        self.purge_rh = purge_rh
        self.purge_off_rh = purge_off_rh
        self.wet_bulb_margin_c = wet_bulb_margin_c
        self.cooling = False
        self.purging = False
        self.reason = "off"

    def update(self, t_in, rh_in, t_out, rh_out):
        """Return the fan duty (0..1) for the current readings."""
        # Temperature control with hysteresis so the fan does not chatter.
        if t_in > self.target_c + self.hysteresis_c:
            self.cooling = True
        elif t_in < self.target_c - self.hysteresis_c:
            self.cooling = False

        # Humidity purge: saturated air inside means no more evaporation.
        if rh_in > self.purge_rh:
            self.purging = True
        elif rh_in < self.purge_off_rh:
            self.purging = False

        if not self.cooling and not self.purging:
            self.reason = "at target"
            return 0.0

        # How far above the physical limit are we? Scale the fan with it.
        floor = wet_bulb_c(t_out, rh_out)
        headroom = t_in - floor
        if headroom < self.wet_bulb_margin_c:
            self.reason = "at wet-bulb limit"
            return 0.4 if self.purging else 0.0

        if self.purging and not self.cooling:
            self.reason = "humidity purge"
            return 0.5

        # Fan speed rises with how far above target the store is: half speed at
        # the target, full speed 4 C above it. Smooth, so no stepping between duties.
        excess = t_in - self.target_c
        self.reason = "cooling"
        return max(0.5, min(1.0, 0.5 + 0.125 * excess))
