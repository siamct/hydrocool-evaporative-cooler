"""
Extract fan on a PWM pin through a logic-level MOSFET.
"""

from machine import PWM, Pin


class Fan:
    def __init__(self, pin, frequency_hz, min_duty, max_duty):
        self._pwm = PWM(Pin(pin))
        self._pwm.freq(frequency_hz)
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.duty = 0.0
        self.set(0.0)

    def set(self, duty):
        """duty 0..1. Anything above zero is clamped to the stall-free range."""
        if duty <= 0:
            duty = 0.0
        else:
            duty = max(self.min_duty, min(self.max_duty, duty))
        self.duty = duty
        self._pwm.duty_u16(int(duty * 65_535))

    @property
    def running(self):
        return self.duty > 0
