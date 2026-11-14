"""
CSV logging to the Pico's own flash.

There is no battery-backed clock on a Pico W, so each row records seconds
since power-on and every power cycle starts a new session number. The
analysis script turns these into relative time.
"""

import os


class CsvLogger:
    HEADER = "session,uptime_s,t_in_c,rh_in,t_out_c,rh_out,wet_bulb_out_c,fan_duty,water_low,reason\n"

    def __init__(self, path, max_bytes):
        self.path = path
        self.max_bytes = max_bytes
        self.session = self._next_session()
        self.full = False
        if self.session == 1:
            with open(self.path, "w") as f:
                f.write(self.HEADER)

    def _next_session(self):
        """Count sessions already in the file so the new one gets the next number."""
        try:
            last = 0
            with open(self.path) as f:
                f.readline()  # header
                for line in f:
                    try:
                        last = int(line.split(",", 1)[0])
                    except ValueError:
                        pass
            return last + 1
        except OSError:
            return 1

    def _size(self):
        try:
            return os.stat(self.path)[6]
        except OSError:
            return 0

    def write(self, uptime_s, t_in, rh_in, t_out, rh_out, wet_bulb_out, fan_duty, water_low, reason):
        if self.full:
            return False
        if self._size() > self.max_bytes:
            self.full = True
            return False
        row = "%d,%d,%.1f,%.1f,%.1f,%.1f,%.2f,%.2f,%d,%s\n" % (
            self.session, uptime_s, t_in, rh_in, t_out, rh_out, wet_bulb_out, fan_duty,
            1 if water_low else 0, reason)
        with open(self.path, "a") as f:
            f.write(row)
        return True
