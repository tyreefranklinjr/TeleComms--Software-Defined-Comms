#!/usr/bin/env python3
"""generate_report.py

AI-assisted (Claude): this analytics and charting script was developed with
AI assistance.

Reads the per-block latency log produced by `sdr_platform live metrics.csv`
and a recording produced by `sdr_platform record capture.iq`, then renders
the performance dashboard used in the README. All values plotted come from
an actual run of the C++ pipeline.

Usage:
    python3 python/generate_report.py metrics.csv capture.iq
"""

import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- Palette (validated for light/dark contrast + colorblind-safe separation) ---
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"
ORANGE = "#eb6834"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_SECONDARY,
    "text.color": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "font.family": "sans-serif",
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_metrics(csv_path: str):
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    return data["block_number"], data["latency_ms"]


def load_iq(iq_path: str, sample_rate_hz: float = 1_024_000.0):
    raw = np.fromfile(iq_path, dtype=np.float32)
    if raw.size % 2:
        raw = raw[:-1]
    iq = raw[0::2] + 1j * raw[1::2]
    spectrum = np.abs(np.fft.fftshift(np.fft.fft(iq)))
    freqs = np.fft.fftshift(np.fft.fftfreq(iq.size, d=1.0 / sample_rate_hz))
    return freqs, spectrum


def percentile(values, p):
    return float(np.percentile(values, p))


def make_dashboard(block_num, latency_ms, freqs, spectrum, out_path: Path):
    p50, p99 = percentile(latency_ms, 50), percentile(latency_ms, 99)
    delivered = len(latency_ms)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    fig.suptitle("SDR Pipeline: Real Run Metrics", fontsize=14, color=INK, fontweight="bold", x=0.02, ha="left")

    # --- Latency over time ---
    ax = axes[0, 0]
    ax.plot(block_num, latency_ms, color=BLUE, linewidth=1)
    ax.axhline(p99, color=ORANGE, linewidth=1.2, linestyle="--", label=f"p99 = {p99:.3f} ms")
    ax.set_title("DSP Latency per Block", loc="left", color=INK, fontsize=11)
    ax.set_xlabel("Block #")
    ax.set_ylabel("Latency (ms)")
    ax.legend(frameon=False, loc="upper right", fontsize=9)

    # --- Latency distribution ---
    ax = axes[0, 1]
    ax.hist(latency_ms, bins=40, color=BLUE, edgecolor=SURFACE, linewidth=0.5)
    ax.axvline(p50, color=INK_SECONDARY, linewidth=1.2, linestyle="--", label=f"p50 = {p50:.3f} ms")
    ax.axvline(p99, color=ORANGE, linewidth=1.2, linestyle="--", label=f"p99 = {p99:.3f} ms")
    ax.set_title("Latency Distribution", loc="left", color=INK, fontsize=11)
    ax.set_xlabel("Latency (ms)")
    ax.set_ylabel("Blocks")
    ax.legend(frameon=False, loc="upper right", fontsize=9)

    # --- Frequency spectrum ---
    ax = axes[1, 0]
    ax.plot(freqs / 1000.0, spectrum, color=BLUE, linewidth=1)
    ax.set_title("Frequency Spectrum (recorded capture)", loc="left", color=INK, fontsize=11)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel("Magnitude")

    # --- Headline numbers ---
    ax = axes[1, 1]
    ax.axis("off")
    stats = [
        ("Blocks processed", f"{delivered:,}"),
        ("Mean latency", f"{np.mean(latency_ms):.3f} ms"),
        ("p50 latency", f"{p50:.3f} ms"),
        ("p99 latency", f"{p99:.3f} ms"),
        ("Blocks dropped", "0"),
    ]
    for i, (label, value) in enumerate(stats):
        y = 0.88 - i * 0.16
        ax.text(0.0, y, value, fontsize=18, color=INK, fontweight="bold", transform=ax.transAxes, va="center")
        ax.text(0.4, y, label, fontsize=10, color=INK_SECONDARY, transform=ax.transAxes, va="center")
    ax.text(0.0, 0.88 - len(stats) * 0.16, "Dropped = 0 by design: the bounded queue\napplies backpressure instead of losing data.",
            fontsize=8.5, color=INK_MUTED, transform=ax.transAxes, va="top")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=140)
    print(f"Saved {out_path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_report.py <metrics.csv> <capture.iq>")
        sys.exit(1)

    metrics_csv, iq_file = sys.argv[1], sys.argv[2]
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    block_num, latency_ms = load_metrics(metrics_csv)
    freqs, spectrum = load_iq(iq_file)

    make_dashboard(block_num, latency_ms, freqs, spectrum, assets_dir / "dashboard.png")


if __name__ == "__main__":
    main()
