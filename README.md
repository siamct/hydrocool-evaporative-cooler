# HydroCool pump controller

Controller for the water pump on HydroCool, a uni group project. A Raspberry Pi Pico drives the pump and a 16x2 LCD, and a desktop app talks to it over USB serial so the pump can be run from either the hardware or the PC.

## What it does

- **Pump speed** comes from a knob (potentiometer), or from the desktop app, which overrides the knob until you hand control back.
- **Lock** stops the pump. It can be toggled from a button on the board or from the app, and both stay in sync.
- **LCD** shows the current speed and whether the pump is locked.
- **Status LEDs** for power, pump running, locked and low water.

## How the two sides talk

Plain text lines over USB serial at 115200 baud.

| PC → Pico | Meaning |
|---|---|
| `SPEED:<0-100>` | Set pump speed (overrides the knob) |
| `POT_MODE` | Give control back to the knob |
| `LOCK:<0/1>` | Lock or unlock the pump |
| `LED_LOW:<0/1>` | Low-water LED on or off |

| Pico → PC | Meaning |
|---|---|
| `STATE:SPEED:<0-100>` | Current speed, sent every 100 ms |
| `STATE:LOCK:<0/1>` | Lock was toggled with the board button |
| `STATE:POT_MODE` | Knob control was selected with the board button |

## Hardware

| Pin | Connected to |
|---|---|
| GP26 (ADC) | Speed potentiometer |
| GP15 | Pump PWM (50 Hz) |
| GP14 | LCD backlight PWM (brightness follows pump speed) |
| GP16–GP21 | 16x2 LCD in 4-bit mode (RS, E, D4–D7) |
| GP10–GP13 | LEDs: power, pump, locked, low water |
| GP6 / GP7 | Buttons: lock toggle, back to knob control |

## Files

```
firmware/main.py          runs on the Pico (MicroPython)
gui/hydrocool_gui.py      desktop app (Python, tkinter + pyserial)
```

To run the app: `pip install pyserial`, then `python gui/hydrocool_gui.py`. It picks the Pico's port automatically if it can find it; press Connect.

## Tidied up after the project

The original was written against a deadline. Since then I've cleaned it up without changing what it does or the serial messages:

- **Firmware:** pins and settings named at the top, the LCD and buttons are small classes, the LCD only redraws when something changes, a garbled serial line is ignored instead of crashing it, and app speeds are clamped to 0–100.
- **App:** finds the Pico's port by itself, says whether the speed is coming from the knob or the app, keeps the lock tick box in sync when the board button is pressed, and notices if the cable is pulled.
