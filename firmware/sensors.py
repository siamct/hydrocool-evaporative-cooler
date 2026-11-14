"""
Inside and outside DHT22 sensors plus the tank float switch.

DHT22s are slow (one reading every 2 s at most) and occasionally fail a
checksum, so each read is retried and the last good value is kept.
"""

import time

import dht
from machine import Pin


class Dht22:
    def __init__(self, pin):
        self._sensor = dht.DHT22(Pin(pin))
        self.temperature_c = None
        self.humidity = None
        self.failures = 0

    def read(self, retries=3):
        """Update temperature_c and humidity. Returns True on a good reading."""
        for _ in range(retries):
            try:
                self._sensor.measure()
                self.temperature_c = self._sensor.temperature()
                self.humidity = self._sensor.humidity()
                return True
            except OSError:
                self.failures += 1
                time.sleep_ms(500)
        return False


class Sensors:
    def __init__(self, inside_pin, outside_pin, water_low_pin):
        self.inside = Dht22(inside_pin)
        self.outside = Dht22(outside_pin)
        self._water_low = Pin(water_low_pin, Pin.IN, Pin.PULL_UP)

    def read(self):
        ok_in = self.inside.read()
        time.sleep_ms(100)
        ok_out = self.outside.read()
        return ok_in and ok_out

    @property
    def water_low(self):
        return self._water_low.value() == 0
