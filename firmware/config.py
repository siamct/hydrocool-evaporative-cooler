"""
Pins and settings for the HydroCool controller (Raspberry Pi Pico W).
"""

# ----- Sensors -----
# Two DHT22 temperature / humidity sensors: one inside the store, one outside.
DHT_INSIDE_PIN = 15
DHT_OUTSIDE_PIN = 16

# Float switch in the header tank, closes to GND when the water is low.
WATER_LOW_PIN = 17

# ----- Fan -----
# 12 V extract fan switched by a logic-level MOSFET, PWM on this pin.
FAN_PIN = 20
FAN_PWM_FREQUENCY_HZ = 25_000
FAN_MIN_DUTY = 0.35        # below this the fan stalls
FAN_MAX_DUTY = 1.00

# ----- Control -----
# The fan pulls humid air out of the store so fresh air is drawn in over the
# wet cloth. It runs when the inside is warmer than the target, or when the
# inside air is so humid that evaporation has stopped.
TARGET_TEMP_C = 18.0           # evaporative cooling cannot reach fridge temperatures; aim for a cool larder
TEMP_HYSTERESIS_C = 1.0            # fan on above target + h, off below target - h
HUMIDITY_PURGE_RH = 85.0           # run the fan when inside RH goes above this
HUMIDITY_PURGE_OFF_RH = 75.0

# If the inside is already within this many degrees of the wet-bulb
# temperature, more airflow cannot cool it further, so hold the fan at minimum.
WET_BULB_MARGIN_C = 0.5

CONTROL_PERIOD_S = 10              # how often sensors are read and the fan updated

# ----- Logging -----
LOG_FILE = "log.csv"
LOG_PERIOD_S = 60                  # one row per minute
LOG_MAX_BYTES = 1_200_000          # stop logging before the flash fills up (Pico W has ~850 kB free)

LED_PIN = "LED"
