"""HydroCool desktop app: control the pump over USB serial.

    pip install pyserial
    python gui/hydrocool_gui.py
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import serial
import serial.tools.list_ports

BAUD = 115200
PICO_USB_VID = 0x2E8A

# Colours
BG = "#F8F8F6"
CARD = "#FFFFFF"
BORDER = "#D3D1C7"
TEXT = "#1A1A18"
MUTED = "#5F5E5A"
ACCENT = "#185FA5"
OK = "#3B6D11"
BAD = "#A32D2D"
LED_OFF = "#B4B2A9"
LED_COLOURS = {"Power": "#639922", "Pump": "#378ADD", "Locked": "#E24B4A", "Low water": "#EF9F27"}

PRESETS = [("Stop", 0), ("Low 30%", 30), ("Mid 60%", 60), ("High 90%", 90)]


def find_pico_port():
    """Best guess at which serial port is the Pico."""
    for p in serial.tools.list_ports.comports():
        if p.vid == PICO_USB_VID or "Pico" in (p.description or "") or "MicroPython" in (p.description or ""):
            return p.device
    return None


class PicoLink:
    """Serial connection to the Pico. Incoming lines go onto a queue for the GUI."""

    def __init__(self):
        self.ser = None
        self.lines = queue.Queue()

    @property
    def connected(self):
        return self.ser is not None

    def open(self, port):
        self.ser = serial.Serial(port, BAUD, timeout=0.2)
        threading.Thread(target=self._reader, args=(self.ser,), daemon=True).start()

    def close(self):
        if self.ser:
            self.ser.close()
        self.ser = None

    def send(self, message):
        if not self.ser:
            return
        try:
            self.ser.write((message + "\n").encode())
        except serial.SerialException:
            self.lines.put("__LOST__")

    def _reader(self, ser):
        while self.ser is ser:
            try:
                line = ser.readline().decode(errors="ignore").strip()
            except (serial.SerialException, OSError):
                self.lines.put("__LOST__")
                return
            if line:
                self.lines.put(line)


class App:
    def __init__(self, root):
        self.root = root
        self.link = PicoLink()

        self.speed = tk.IntVar(value=0)
        self.locked = tk.BooleanVar(value=False)
        self.low_water = tk.BooleanVar(value=False)
        self.knob_mode = tk.BooleanVar(value=True)
        self.port = tk.StringVar()

        root.title("HydroCool control")
        root.configure(bg=BG)
        root.resizable(False, False)
        self._build()
        self.refresh_ports()
        self.update_view()
        self.root.after(50, self.poll_serial)

    # --- layout ---------------------------------------------------------

    def _card(self, title):
        frame = tk.Frame(self.root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", padx=12, pady=4)
        tk.Label(frame, text=title, bg=CARD, fg=MUTED, font=("Helvetica", 9, "bold")).pack(
            anchor="w", padx=12, pady=(10, 2))
        return frame

    def _build(self):
        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(bar, text="Port:", bg=BG, fg=TEXT, font=("Helvetica", 11)).pack(side="left")
        self.port_menu = ttk.Combobox(bar, textvariable=self.port, width=12, state="readonly")
        self.port_menu.pack(side="left", padx=6)
        tk.Button(bar, text="Refresh", command=self.refresh_ports, bg=BG, fg=TEXT,
                  relief="solid", bd=1, font=("Helvetica", 10)).pack(side="left")
        self.conn_btn = tk.Button(bar, text="Connect", command=self.toggle_connect, bg=ACCENT,
                                  fg="white", relief="flat", font=("Helvetica", 10, "bold"), padx=10)
        self.conn_btn.pack(side="left", padx=8)
        self.status = tk.Label(bar, text="Not connected", bg=BG, fg=BAD, font=("Helvetica", 10))
        self.status.pack(side="left")

        card = self._card("PUMP SPEED")
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", padx=12)
        self.speed_label = tk.Label(top, text="0%", bg=CARD, fg=TEXT, font=("Helvetica", 32, "bold"))
        self.speed_label.pack(side="left")
        self.source_label = tk.Label(top, text="", bg=CARD, fg=MUTED, font=("Helvetica", 10))
        self.source_label.pack(side="right", anchor="s", pady=8)
        ttk.Scale(card, from_=0, to=100, orient="horizontal", variable=self.speed,
                  command=lambda v: self.set_speed(int(float(v)))).pack(fill="x", padx=12, pady=(0, 10))

        card = self._card("PRESETS")
        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", padx=12, pady=(0, 10))
        for label, value in PRESETS:
            tk.Button(row, text=label, command=lambda v=value: self.set_speed(v), bg=CARD, fg=TEXT,
                      relief="solid", bd=1, font=("Helvetica", 10), padx=8).pack(side="left", padx=(0, 6))
        tk.Button(row, text="Use knob", command=self.use_knob, bg=CARD, fg=ACCENT, relief="solid",
                  bd=1, font=("Helvetica", 10), padx=8).pack(side="right")

        card = self._card("CONTROLS")
        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", padx=12, pady=(0, 10))
        tk.Checkbutton(row, text="Lock pump", variable=self.locked, command=self.send_lock, bg=CARD,
                       fg=TEXT, font=("Helvetica", 11), activebackground=CARD).pack(side="left", padx=(0, 16))
        tk.Checkbutton(row, text="Low water LED", variable=self.low_water, command=self.send_low_water,
                       bg=CARD, fg=TEXT, font=("Helvetica", 11), activebackground=CARD).pack(side="left")

        card = self._card("LED STATUS")
        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", padx=12, pady=(0, 10))
        self.leds = {}
        for name in LED_COLOURS:
            cell = tk.Frame(row, bg=CARD)
            cell.pack(side="left", padx=(0, 22))
            dot = tk.Canvas(cell, width=18, height=18, bg=CARD, highlightthickness=0)
            dot.pack(side="left", padx=(0, 6))
            self.leds[name] = (dot, dot.create_oval(2, 2, 16, 16, fill=LED_OFF, outline=LED_OFF))
            tk.Label(cell, text=name, bg=CARD, fg=MUTED, font=("Helvetica", 10)).pack(side="left")
        tk.Frame(self.root, bg=BG, height=8).pack()

    # --- connection -----------------------------------------------------

    def refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_menu["values"] = ports
        self.port.set(find_pico_port() or (ports[0] if ports else ""))

    def toggle_connect(self):
        if self.link.connected:
            self.link.close()
            self.status.config(text="Not connected", fg=BAD)
            self.conn_btn.config(text="Connect")
            return
        try:
            self.link.open(self.port.get())
        except (serial.SerialException, ValueError) as e:
            messagebox.showerror("Connection failed", str(e))
            return
        self.status.config(text=f"Connected: {self.port.get()}", fg=OK)
        self.conn_btn.config(text="Disconnect")
        self.send_all()

    def send_all(self):
        self.link.send("POT_MODE" if self.knob_mode.get() else f"SPEED:{self.speed.get()}")
        self.send_lock()
        self.send_low_water()

    # --- user actions ---------------------------------------------------

    def set_speed(self, percent):
        self.knob_mode.set(False)
        self.speed.set(percent)
        self.link.send(f"SPEED:{percent}")
        self.update_view()

    def use_knob(self):
        self.knob_mode.set(True)
        self.link.send("POT_MODE")
        self.update_view()

    def send_lock(self):
        self.link.send(f"LOCK:{int(self.locked.get())}")
        self.update_view()

    def send_low_water(self):
        self.link.send(f"LED_LOW:{int(self.low_water.get())}")
        self.update_view()

    # --- messages from the Pico ----------------------------------------

    def poll_serial(self):
        while not self.link.lines.empty():
            self.handle(self.link.lines.get())
        self.root.after(50, self.poll_serial)

    def handle(self, line):
        if line == "__LOST__":
            self.link.close()
            self.status.config(text="Connection lost", fg=BAD)
            self.conn_btn.config(text="Connect")
        elif line.startswith("STATE:SPEED:"):
            if self.knob_mode.get():
                self.speed.set(int(line.split(":")[2]))
        elif line.startswith("STATE:LOCK:"):
            self.locked.set(line.endswith("1"))
        elif line == "STATE:POT_MODE":
            self.knob_mode.set(True)
        self.update_view()

    # --- display --------------------------------------------------------

    def update_view(self):
        speed = self.speed.get()
        locked = self.locked.get()
        self.speed_label.config(text=f"{speed}%")
        self.source_label.config(text="from the knob" if self.knob_mode.get() else "set in the app")
        lit = {"Power": True, "Pump": speed > 0 and not locked,
               "Locked": locked, "Low water": self.low_water.get()}
        for name, (canvas, dot) in self.leds.items():
            colour = LED_COLOURS[name] if lit[name] else LED_OFF
            canvas.itemconfig(dot, fill=colour, outline=colour)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
