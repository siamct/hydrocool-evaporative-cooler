"""
HydroCool: low-power evaporative food store controller for the Raspberry Pi Pico W.

Water from a header tank trickles down cloth lining the inside walls. An
extract fan draws air out of the store so outside air is pulled in through
the damp cloth, where evaporation cools it. This program:

    - reads inside and outside temperature and humidity every 10 s
    - runs the fan only when it will actually help (see controller.py)
    - logs a row to log.csv on the Pico's flash every minute
    - blinks the LED slowly when running, quickly when the water is low

Copy log.csv off the Pico with Thonny and plot it with analysis/plot_log.py.
"""

import time
from machine import Pin

import config
from controller import FanController
from fan import Fan
from logger import CsvLogger
from sensors import Sensors
from wetbulb import wet_bulb_c


def main():
    led = Pin(config.LED_PIN, Pin.OUT)
    sensors = Sensors(config.DHT_INSIDE_PIN, config.DHT_OUTSIDE_PIN, config.WATER_LOW_PIN)
    fan = Fan(config.FAN_PIN, config.FAN_PWM_FREQUENCY_HZ, config.FAN_MIN_DUTY, config.FAN_MAX_DUTY)
    control = FanController(config.TARGET_TEMP_C, config.TEMP_HYSTERESIS_C,
                            config.HUMIDITY_PURGE_RH, config.HUMIDITY_PURGE_OFF_RH,
                            config.WET_BULB_MARGIN_C)
    log = CsvLogger(config.LOG_FILE, config.LOG_MAX_BYTES)

    print("HydroCool session %d. Logging to %s every %d s." % (log.session, config.LOG_FILE, config.LOG_PERIOD_S))
    started = time.ticks_ms()
    last_log = -config.LOG_PERIOD_S

    while True:
        cycle_start = time.ticks_ms()
        uptime_s = time.ticks_diff(cycle_start, started) // 1000

        if sensors.read():
            t_in, rh_in = sensors.inside.temperature_c, sensors.inside.humidity
            t_out, rh_out = sensors.outside.temperature_c, sensors.outside.humidity
            duty = control.update(t_in, rh_in, t_out, rh_out)
            fan.set(duty)
            wb = wet_bulb_c(t_out, rh_out)

            print("in %.1fC %.0f%%  out %.1fC %.0f%% (wet bulb %.1fC)  fan %.0f%% %s%s" % (
                t_in, rh_in, t_out, rh_out, wb, fan.duty * 100, control.reason,
                "  WATER LOW" if sensors.water_low else ""))

            if uptime_s - last_log >= config.LOG_PERIOD_S:
                if log.write(uptime_s, t_in, rh_in, t_out, rh_out, wb, fan.duty, sensors.water_low, control.reason):
                    last_log = uptime_s
                elif log.full:
                    print("Log file is full; not logging any more.")
        else:
            # Sensor failure: fail safe by leaving the fan as it was and say so.
            print("Sensor read failed (inside %d, outside %d failures)" % (sensors.inside.failures, sensors.outside.failures))

        # LED heartbeat: slow blink normally, fast when the water needs topping up.
        blinks = 4 if sensors.water_low else 1
        for _ in range(blinks):
            led.on()
            time.sleep_ms(80)
            led.off()
            time.sleep_ms(120)

        elapsed_ms = time.ticks_diff(time.ticks_ms(), cycle_start)
        remaining = config.CONTROL_PERIOD_S * 1000 - elapsed_ms
        if remaining > 0:
            time.sleep_ms(remaining)


main()
