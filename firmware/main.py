"""HydroCool pump controller (MicroPython, Raspberry Pi Pico).

Pump speed comes from the knob, or from the desktop app over USB serial.
Lock stops the pump. A 16x2 LCD shows speed and lock state.
See the README for the serial messages.
"""

import select
import sys

import machine
import utime

# --- Pins ---------------------------------------------------------------
POT_PIN = 26
PUMP_PIN = 15
BACKLIGHT_PIN = 14
LCD_PINS = {"rs": 16, "e": 17, "d4": 18, "d5": 19, "d6": 20, "d7": 21}
LED_PINS = {"power": 10, "pump": 11, "locked": 12, "low_water": 13}
BUTTON_PINS = (6, 7)          # lock toggle, back to knob control

# --- Settings -----------------------------------------------------------
PUMP_PWM_FREQ = 50
BACKLIGHT_PWM_FREQ = 1000
PUMP_MIN_DUTY = 1500          # lowest duty that still turns the pump
PUMP_DEADBAND = 1100          # knob readings below this count as "off"
DEBOUNCE_MS = 200
LOOP_MS = 100

# --- Hardware -----------------------------------------------------------
pot = machine.ADC(POT_PIN)

pump = machine.PWM(machine.Pin(PUMP_PIN))
pump.freq(PUMP_PWM_FREQ)

backlight = machine.PWM(machine.Pin(BACKLIGHT_PIN))
backlight.freq(BACKLIGHT_PWM_FREQ)

leds = {name: machine.Pin(pin, machine.Pin.OUT) for name, pin in LED_PINS.items()}


class Button:
    """Active-low button with debounce. pressed() is true once per press."""

    def __init__(self, pin):
        self.pin = machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP)
        self.last = 1
        self.last_time = 0

    def pressed(self):
        now = utime.ticks_ms()
        value = self.pin.value()
        was_up = self.last == 1
        self.last = value
        if value == 0 and was_up and utime.ticks_diff(now, self.last_time) > DEBOUNCE_MS:
            self.last_time = now
            return True
        return False


class LCD:
    """HD44780-style 16x2 LCD in 4-bit mode."""

    def __init__(self, rs, e, d4, d5, d6, d7):
        out = machine.Pin.OUT
        self.rs = machine.Pin(rs, out)
        self.e = machine.Pin(e, out)
        self.data = [machine.Pin(p, out) for p in (d4, d5, d6, d7)]
        self.shown = (None, None)
        self._init()

    def _pulse(self):
        self.e.value(1)
        utime.sleep_us(40)
        self.e.value(0)
        utime.sleep_us(40)

    def _nibble(self, n):
        for bit, pin in enumerate(self.data):
            pin.value((n >> bit) & 1)
        self._pulse()

    def _byte(self, b):
        self._nibble(b >> 4)
        self._nibble(b & 0x0F)

    def _command(self, b):
        self.rs.value(0)
        self._byte(b)

    def _init(self):
        self.rs.value(0)
        utime.sleep_ms(20)
        for _ in range(3):
            self._nibble(0b0011)
            utime.sleep_ms(5)
        self._nibble(0b0010)          # 4-bit mode
        self._command(0b00101000)     # 2 lines, 5x8 font
        self._command(0b00001100)     # display on, no cursor
        self._command(0b00000110)     # move right after each character
        self._command(0b00000001)     # clear
        utime.sleep_ms(2)

    def show(self, line1, line2):
        """Write both lines, padded to 16 characters. Skips if nothing changed."""
        lines = (line1[:16].ljust(16), line2[:16].ljust(16))
        if lines == self.shown:
            return
        for address, text in zip((0x80, 0xC0), lines):
            self._command(address)
            self.rs.value(1)
            for ch in text:
                self._byte(ord(ch))
        self.shown = lines


# --- State --------------------------------------------------------------
locked = False
gui_speed = None              # None = knob control, 0-100 = app override
buttons = [Button(p) for p in BUTTON_PINS]
lcd = LCD(**LCD_PINS)


def send(message):
    print(message)            # USB serial back to the app


def set_locked(value):
    global locked
    locked = value
    leds["locked"].value(locked)


def pump_duty(percent):
    """Map 0-100 % onto the pump's PWM range, skipping the dead zone where it stalls."""
    raw = int(percent / 100 * 65535)
    duty = int((raw - PUMP_DEADBAND) * (65535 - PUMP_MIN_DUTY) / (65535 - PUMP_DEADBAND) + PUMP_MIN_DUTY)
    return max(0, min(65535, duty))


def apply_speed(percent):
    if locked or percent == 0:
        pump.duty_u16(0)
        backlight.duty_u16(0)
        leds["pump"].off()
    else:
        pump.duty_u16(pump_duty(percent))
        backlight.duty_u16(int(percent / 100 * 65535))
        leds["pump"].on()


def handle_command(line):
    global gui_speed
    try:
        if line.startswith("SPEED:"):
            gui_speed = max(0, min(100, int(line[6:])))
        elif line.startswith("LOCK:"):
            set_locked(bool(int(line[5:])))
        elif line.startswith("LED_LOW:"):
            leds["low_water"].value(int(line[8:]))
        elif line == "POT_MODE":
            gui_speed = None
    except ValueError:
        pass                  # ignore a garbled line rather than crash


def update():
    """One pass of the control loop: commands, buttons, pump, report, LCD."""
    global gui_speed
    while poll.poll(0):
        handle_command(sys.stdin.readline().strip())

    if buttons[0].pressed():
        set_locked(not locked)
        send("STATE:LOCK:" + str(int(locked)))
    if buttons[1].pressed():
        gui_speed = None
        send("STATE:POT_MODE")

    if gui_speed is None:
        percent = int(pot.read_u16() / 65535 * 100)
    else:
        percent = gui_speed

    apply_speed(percent)
    send("STATE:SPEED:" + str(0 if locked else percent))
    lcd.show("Speed: " + str(percent) + "%", "LOCKED" if locked else "UNLOCKED")


poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

if __name__ == "__main__":
    leds["power"].on()
    send("READY")
    while True:
        update()
        utime.sleep_ms(LOOP_MS)
