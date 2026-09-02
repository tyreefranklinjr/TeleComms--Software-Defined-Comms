#!/usr/bin/env python3
"""analyze_iq.py

AI-assisted (Claude): this analytics script was developed with AI assistance.

Reads a recorded IQ file produced by the C++ program and plots the raw
waveform and its frequency spectrum, saved as iq_analysis.png.

Usage:
    python3 analyze_iq.py <recorded_file.iq> [sample_rate_hz]
"""

import sys

import numpy as np


def load_iq_file(file_path: str) -> np.ndarray:
    """Loads a raw IQ file into a NumPy array of complex numbers."""
    raw = np.fromfile(file_path, dtype=np.float32)

    if raw.size % 2 != 0:
        raw = raw[:-1]

    i_values = raw[0::2]
    q_values = raw[1::2]

    return i_values + 1j * q_values


def summarize(iq: np.ndarray, sample_rate_hz: float) -> None:
    num_samples = iq.size
    duration_seconds = num_samples / sample_rate_hz
    print(f"Loaded {num_samples:,} IQ samples")
    print(f"That is {duration_seconds:.4f} seconds of recording at {sample_rate_hz:,.0f} Hz")


def plot_iq(iq: np.ndarray, sample_rate_hz: float, output_image: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    preview_samples = iq[:2000]
    time_axis_ms = np.arange(preview_samples.size) / sample_rate_hz * 1000.0

    spectrum = np.abs(np.fft.fftshift(np.fft.fft(iq)))
    freq_axis_hz = np.fft.fftshift(np.fft.fftfreq(iq.size, d=1.0 / sample_rate_hz))

    fig, (ax_wave, ax_spectrum) = plt.subplots(2, 1, figsize=(10, 7))

    ax_wave.plot(time_axis_ms, preview_samples.real, label="I (real part)")
    ax_wave.plot(time_axis_ms, preview_samples.imag, label="Q (imaginary part)")
    ax_wave.set_title("Raw IQ waveform (first 2000 samples)")
    ax_wave.set_xlabel("Time (ms)")
    ax_wave.set_ylabel("Amplitude")
    ax_wave.legend()

    ax_spectrum.plot(freq_axis_hz, spectrum)
    ax_spectrum.set_title("Frequency spectrum (whole recording)")
    ax_spectrum.set_xlabel("Frequency (Hz)")
    ax_spectrum.set_ylabel("Magnitude")

    fig.tight_layout()
    fig.savefig(output_image, dpi=120)
    print(f"Saved plot to: {output_image}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_iq.py <recorded_file.iq> [sample_rate_hz]")
        sys.exit(1)

    file_path = sys.argv[1]
    sample_rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 1_024_000.0

    iq = load_iq_file(file_path)
    summarize(iq, sample_rate_hz)
    plot_iq(iq, sample_rate_hz, output_image="iq_analysis.png")


if __name__ == "__main__":
    main()
