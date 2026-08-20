"""
pulse_shaping_analysis.py
--------------------------
Data-generation pass for the V0.4 pulse-shaping additions (upsample,
rrcosfilter, modulate_bpsk_rrc). Unlike the unit tests, which are
deterministic and give the same answer every run, this script pushes
randomized bit sequences through the real transmit -> AWGN -> matched
filter -> downsample -> decide chain, 100 trials per Eb/N0 point, and
compares the resulting BER against the same closed-form curve V0.3.5
already validated for the unshaped case.

The point isn't just "does the filter run", it's "does adding pulse
shaping cost anything in BER once a proper matched filter and correct
symbol-timing sampling are in place". Matched filter theory says it
shouldn't (a root-raised-cosine transmit filter paired with the same
filter on receive is still a Nyquist pulse with no ISI at the correct
sampling instant), so this is a real check of that claim, not a demo.

Produces, under figures/:
  1. rrc_filter_shapes.png        -- time-domain filter for several alpha
  2. rrc_frequency_response.png   -- frequency-domain rolloff for the same alphas
  3. eye_diagram.png              -- eye diagram of the shaped waveform
  4. ber_rrc_matched_filter.png   -- Monte Carlo BER (100 trials/point) vs theory

Also writes results/pulse_shaping_ber_sweep.csv.

Run:  python analysis/pulse_shaping_analysis.py
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.modem import upsample, rrcosfilter, modulate_bpsk_rrc, theoretical_ber_awgn

FIG_DIR = ROOT / "figures"
RES_DIR = ROOT / "results"
FIG_DIR.mkdir(exist_ok=True)
RES_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (7, 4.5),
    "figure.dpi": 140,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
})

SPS = 8
NUM_TAPS = 33
ALPHA = 0.35
N_TRIALS = 100          # per Eb/N0 point, as requested
BITS_PER_TRIAL = 2000
RNG_SEED = 7


# ---------------------------------------------------------------------
# 1. Filter shape across alpha (deterministic, one draw each)
# ---------------------------------------------------------------------

def plot_filter_shapes():
    alphas = [0.0, 0.2, 0.35, 0.5, 1.0]
    plt.figure()
    for a in alphas:
        h = rrcosfilter(NUM_TAPS, a, SPS)
        t = np.arange(-(NUM_TAPS // 2), NUM_TAPS // 2 + 1)
        plt.plot(t, h, marker="o", markersize=3, label=f"alpha={a}")
    plt.xlabel("Tap index (samples)")
    plt.ylabel("Filter coefficient")
    plt.title(f"RRC Filter Impulse Response vs. Rolloff (sps={SPS}, taps={NUM_TAPS})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "rrc_filter_shapes.png")
    plt.close()


def plot_frequency_response():
    alphas = [0.0, 0.2, 0.35, 0.5, 1.0]
    plt.figure()
    n_fft = 2048
    for a in alphas:
        h = rrcosfilter(NUM_TAPS, a, SPS)
        H = np.fft.fftshift(np.fft.fft(h, n_fft))
        freq = np.fft.fftshift(np.fft.fftfreq(n_fft, d=1.0)) * SPS  # normalized to symbol rate
        mag_db = 20 * np.log10(np.abs(H) / np.max(np.abs(H)) + 1e-12)
        plt.plot(freq, mag_db, label=f"alpha={a}")
    plt.xlim(-1.5, 1.5)
    plt.ylim(-60, 5)
    plt.xlabel("Frequency / symbol rate")
    plt.ylabel("Magnitude (dB)")
    plt.title("RRC Filter Frequency Response vs. Rolloff")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "rrc_frequency_response.png")
    plt.close()


# ---------------------------------------------------------------------
# 2. Eye diagram (classic pulse-shaping sanity check)
# ---------------------------------------------------------------------

def plot_eye_diagram():
    rng = np.random.default_rng(RNG_SEED)
    n_symbols = 400
    bits = rng.integers(0, 2, n_symbols)
    symbols = np.where(bits == 1, 1.0, -1.0)
    waveform = modulate_bpsk_rrc(symbols, sps=SPS, num_taps=NUM_TAPS, alpha=ALPHA).real

    group_delay = NUM_TAPS // 2
    trace_len = 2 * SPS  # show two symbol periods per trace
    plt.figure()
    for i in range(20, n_symbols - 20):
        start = group_delay + i * SPS - SPS // 2
        segment = waveform[start:start + trace_len]
        if len(segment) == trace_len:
            plt.plot(range(trace_len), segment, color="#2563eb", alpha=0.15, linewidth=0.8)
    plt.xlabel("Samples (2 symbol periods)")
    plt.ylabel("Amplitude")
    plt.title(f"Eye Diagram: RRC-Shaped BPSK (alpha={ALPHA}, sps={SPS}), 400 symbols")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "eye_diagram.png")
    plt.close()


# ---------------------------------------------------------------------
# 3. Monte Carlo BER through matched filter + noise, 100 trials/point
# ---------------------------------------------------------------------

def matched_filter_trial(bits: np.ndarray, eb_n0_db: float, rng: np.random.Generator) -> int:
    """
    One trial: bits -> BPSK symbols -> RRC transmit shaping -> AWGN ->
    RRC matched (receive) filtering -> downsample at symbol centers ->
    hard decision. Returns the number of bit errors.
    """
    symbols = np.where(bits == 1, 1.0, -1.0)
    tx_waveform = modulate_bpsk_rrc(symbols, sps=SPS, num_taps=NUM_TAPS, alpha=ALPHA)

    # Both rrcosfilter (transmit) and this same filter (receive, matched)
    # are unit-energy (sum(h^2) = 1), so the matched filter passes noise
    # variance straight through rather than averaging it down further.
    # Adding noise at the same per-sample std used in the unshaped model
    # (src.modem.awgn_channel) keeps the two comparable Eb/N0-for-Eb/N0.
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    noise_std = np.sqrt(1.0 / (2 * eb_n0_linear))
    noise = rng.normal(0, noise_std, size=tx_waveform.shape)
    rx_waveform = tx_waveform.real + noise

    h = rrcosfilter(NUM_TAPS, ALPHA, SPS)
    matched = np.convolve(rx_waveform, h, mode="full")

    # total group delay through tx + rx RRC filters
    group_delay = NUM_TAPS - 1
    sample_points = group_delay + np.arange(len(bits)) * SPS
    sample_points = sample_points[sample_points < len(matched)]

    decided_bits = (matched[sample_points] > 0).astype(int)
    n = min(len(decided_bits), len(bits))
    return int(np.sum(decided_bits[:n] != bits[:n]))


def sweep_matched_filter_ber(eb_n0_values, n_trials=N_TRIALS, bits_per_trial=BITS_PER_TRIAL):
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for ebn0 in eb_n0_values:
        total_errors, total_bits = 0, 0
        for _ in range(n_trials):
            bits = rng.integers(0, 2, bits_per_trial)
            errors = matched_filter_trial(bits, ebn0, rng)
            total_errors += errors
            total_bits += bits_per_trial
        empirical = total_errors / total_bits
        rows.append(dict(
            eb_n0_db=ebn0,
            empirical_ber=empirical,
            theoretical_ber=theoretical_ber_awgn(ebn0),
            n_trials=n_trials,
            bits_per_trial=bits_per_trial,
            total_bits=total_bits,
            total_errors=total_errors,
        ))
        print(f"  Eb/N0={ebn0:5.1f} dB  empirical={empirical:.5f}  "
              f"theory={theoretical_ber_awgn(ebn0):.5f}  "
              f"({total_errors} errors / {total_bits} bits)")
    return rows


def plot_ber_comparison(rows):
    ebn0 = [r["eb_n0_db"] for r in rows]
    emp = [max(r["empirical_ber"], 1e-6) for r in rows]  # floor for log scale
    theo = [r["theoretical_ber"] for r in rows]

    plt.figure()
    plt.semilogy(ebn0, theo, "k--", label=r"theoretical: $Q(\sqrt{2E_b/N_0})$ (unshaped)")
    plt.semilogy(ebn0, emp, "o-", color="#dc2626",
                 label=f"empirical: RRC + matched filter ({N_TRIALS} trials/pt)")
    plt.xlabel("$E_b/N_0$ (dB)")
    plt.ylabel("Bit Error Rate (log scale)")
    plt.title("Pulse-Shaped BPSK: Matched-Filter BER vs. Closed-Form Theory")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ber_rrc_matched_filter.png")
    plt.close()


def write_csv(rows, name):
    path = RES_DIR / name
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path}")


def main():
    print("Plotting filter shapes across rolloff...")
    plot_filter_shapes()
    plot_frequency_response()

    print("Building eye diagram...")
    plot_eye_diagram()

    print(f"Running Monte Carlo BER sweep ({N_TRIALS} trials/point, "
          f"{BITS_PER_TRIAL} bits/trial)...")
    ebn0_values = np.arange(0, 11, 1)
    rows = sweep_matched_filter_ber(ebn0_values)
    write_csv(rows, "pulse_shaping_ber_sweep.csv")
    plot_ber_comparison(rows)

    print(f"\nDone. Figures in {FIG_DIR}, data in {RES_DIR}")


if __name__ == "__main__":
    main()
