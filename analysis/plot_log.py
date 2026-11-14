"""
Plot a HydroCool log file.

    python plot_log.py                      plots ../data/example_log.csv
    python plot_log.py path/to/log.csv      plots a file copied off the Pico

Produces docs/temperatures.png and docs/fan_and_humidity.png and prints a
short summary: average temperature drop, how close the store got to the
wet-bulb limit, and the fan's duty cycle over the run.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware"))
from wetbulb import cooling_efficiency  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LOG = os.path.join(HERE, "..", "data", "example_log.csv")
DOCS = os.path.join(HERE, "..", "docs")


def load(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "session": int(r["session"]),
                "t": int(r["uptime_s"]) / 3600.0,
                "t_in": float(r["t_in_c"]),
                "rh_in": float(r["rh_in"]),
                "t_out": float(r["t_out_c"]),
                "rh_out": float(r["rh_out"]),
                "wb": float(r["wet_bulb_out_c"]),
                "fan": float(r["fan_duty"]),
                "water_low": r["water_low"] == "1",
                "reason": r["reason"],
            })
    return rows


def plot(rows, title_note):
    os.makedirs(DOCS, exist_ok=True)
    t = [r["t"] for r in rows]

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(t, [r["t_out"] for r in rows], color="#d62728", label="outside air")
    ax.plot(t, [r["t_in"] for r in rows], color="#1f77b4", linewidth=2, label="inside store")
    ax.plot(t, [r["wb"] for r in rows], color="#2ca02c", linestyle="--", label="wet-bulb limit of outside air")
    ax.fill_between(t, [r["wb"] for r in rows], [r["t_out"] for r in rows], color="#2ca02c", alpha=0.06)
    ax.set_xlabel("time (hours)")
    ax.set_ylabel("temperature (°C)")
    ax.set_title("Store temperature against the outside air and the evaporative limit" + title_note, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "temperatures.png"), dpi=130)
    plt.close(fig)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True)
    ax1.plot(t, [r["rh_in"] for r in rows], color="#1f77b4", label="inside RH")
    ax1.plot(t, [r["rh_out"] for r in rows], color="#d62728", label="outside RH")
    ax1.set_ylabel("relative humidity (%)")
    ax1.grid(alpha=0.3)
    ax1.legend(fontsize=8)
    ax2.step(t, [100 * r["fan"] for r in rows], where="post", color="#555555")
    ax2.fill_between(t, 0, [100 * r["fan"] for r in rows], step="post", color="#555555", alpha=0.25)
    ax2.set_ylabel("fan duty (%)")
    ax2.set_xlabel("time (hours)")
    ax2.set_ylim(0, 105)
    ax2.grid(alpha=0.3)
    fig.suptitle("Humidity and fan duty" + title_note, fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "fan_and_humidity.png"), dpi=130)
    plt.close(fig)


def summarise(rows):
    # Ignore the first hour so the pull-down from room temperature is not counted.
    settled = [r for r in rows if r["t"] >= 1.0] or rows
    drop = sum(r["t_out"] - r["t_in"] for r in settled) / len(settled)
    eff = sum(cooling_efficiency(r["t_out"], r["rh_out"], r["t_in"]) for r in settled) / len(settled)
    duty = sum(r["fan"] for r in rows) / len(rows)
    on_fraction = sum(1 for r in rows if r["fan"] > 0) / len(rows)
    min_in = min(r["t_in"] for r in rows)
    print("rows: %d over %.1f h" % (len(rows), rows[-1]["t"] - rows[0]["t"]))
    print("average temperature drop (after 1 h): %.1f C" % drop)
    print("average saturation efficiency:         %.0f %%" % (100 * eff))
    print("lowest inside temperature:             %.1f C" % min_in)
    print("fan on %.0f %% of the time, mean duty %.0f %%" % (100 * on_fraction, 100 * duty))
    print("estimated fan energy at 2.4 W full duty: %.1f Wh" % (2.4 * duty * (rows[-1]["t"] - rows[0]["t"])))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG
    rows = load(path)
    if not rows:
        print("no rows in", path)
        return
    note = "  (example data from analysis/example_model.py)" if os.path.abspath(path) == os.path.abspath(DEFAULT_LOG) else ""
    plot(rows, note)
    summarise(rows)
    print("plots written to", os.path.normpath(DOCS))


if __name__ == "__main__":
    main()
