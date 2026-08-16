"""
statistical_analysis.py
------------------------
The Monte Carlo harness that turns "I think this works" into numbers.

Produces, under figures/:
  1. ber_vs_p_flip.png        -- empirical BER vs theoretical BER, BSC model
  2. ber_vs_ebn0_awgn.png     -- empirical BER vs closed-form Q-function BER, AWGN model
  3. frame_error_rate.png     -- FER vs p_error, empirical vs 1-(1-BER)^N
  4. crc_miss_detection.png   -- fraction of corrupted-but-CRC-passed frames vs p_error
  5. summary_heatmap.png      -- payload length x p_error -> frame success rate

Raw swept data lands in results/*.csv so the numbers behind each plot
are checkable, not just trusted.

Run:  python analysis/statistical_analysis.py
"""

import csv
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.pipeline import run_trial
from src.modem import theoretical_ber_awgn

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

TEST_PAYLOAD = "The quick brown fox jumps over the lazy dog 1234567890"
N_TRIALS = 4000
RNG_SEED = 42


def sweep_flip_channel(p_values, payload=TEST_PAYLOAD, n_trials=N_TRIALS):
    rng = random.Random(RNG_SEED)
    rows = []
    for p in p_values:
        bit_err_total, bits_total = 0, 0
        crc_pass, success, undetected = 0, 0, 0
        for i in range(n_trials):
            r = run_trial(payload, sequence=i % 256, channel="flip", p_error=p, rng=rng)
            bit_err_total += r.bit_errors
            bits_total += r.frame_bits
            crc_pass += int(r.crc_ok)
            success += int(r.success)
            # undetected error: CRC said OK but payload is actually wrong
            if r.crc_ok and not r.payload_matches:
                undetected += 1
        rows.append(dict(
            p_error=p,
            empirical_ber=bit_err_total / bits_total,
            frame_success_rate=success / n_trials,
            crc_pass_rate=crc_pass / n_trials,
            undetected_error_rate=undetected / n_trials,
            n_trials=n_trials,
        ))
    return rows


def sweep_awgn_channel(ebn0_values, payload=TEST_PAYLOAD, n_trials=N_TRIALS):
    rng = random.Random(RNG_SEED)
    rows = []
    for ebn0 in ebn0_values:
        bit_err_total, bits_total, success = 0, 0, 0
        for i in range(n_trials):
            r = run_trial(payload, sequence=i % 256, channel="awgn", eb_n0_db=ebn0, rng=rng)
            bit_err_total += r.bit_errors
            bits_total += r.frame_bits
            success += int(r.success)
        rows.append(dict(
            eb_n0_db=ebn0,
            empirical_ber=bit_err_total / bits_total,
            theoretical_ber=theoretical_ber_awgn(ebn0),
            frame_success_rate=success / n_trials,
            n_trials=n_trials,
        ))
    return rows


def write_csv(rows, name):
    path = RES_DIR / name
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path}")


def plot_ber_vs_p_flip(rows):
    p = [r["p_error"] for r in rows]
    ber = [r["empirical_ber"] for r in rows]
    plt.figure()
    plt.plot(p, p, "k--", label="theoretical BER = p (BSC)")
    plt.plot(p, ber, "o-", color="#2563eb", label="empirical BER")
    plt.xlabel("Channel flip probability, p")
    plt.ylabel("Bit Error Rate")
    plt.title("BSC Model: Empirical vs Theoretical BER")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ber_vs_p_flip.png")
    plt.close()


def plot_ber_vs_ebn0(rows):
    ebn0 = [r["eb_n0_db"] for r in rows]
    emp = [r["empirical_ber"] for r in rows]
    theo = [r["theoretical_ber"] for r in rows]
    plt.figure()
    plt.semilogy(ebn0, theo, "k--", label=r"theoretical: $Q(\sqrt{2E_b/N_0})$")
    plt.semilogy(ebn0, emp, "o-", color="#dc2626", label="empirical (Monte Carlo)")
    plt.xlabel("$E_b/N_0$ (dB)")
    plt.ylabel("Bit Error Rate (log scale)")
    plt.title("AWGN BPSK: Empirical vs Closed-Form BER")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ber_vs_ebn0_awgn.png")
    plt.close()


def plot_frame_error_rate(rows, frame_bits):
    p = np.array([r["p_error"] for r in rows])
    emp_fer = 1 - np.array([r["frame_success_rate"] for r in rows])
    theo_fer = 1 - (1 - p) ** frame_bits
    plt.figure()
    plt.plot(p, theo_fer, "k--", label=r"theoretical: $1-(1-p)^N$")
    plt.plot(p, emp_fer, "o-", color="#16a34a", label="empirical FER")
    plt.xlabel("Channel flip probability, p")
    plt.ylabel("Frame Error Rate")
    plt.title(f"Frame Error Rate vs Bit Error Probability (N={frame_bits} bits/frame)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "frame_error_rate.png")
    plt.close()


def plot_crc_miss_detection(rows):
    p = [r["p_error"] for r in rows]
    undetected = [r["undetected_error_rate"] for r in rows]
    plt.figure()
    plt.plot(p, undetected, "o-", color="#9333ea", label="empirical undetected-error rate")
    plt.axhline(1 / 256, color="k", linestyle="--", label=r"asymptotic bound $\approx 2^{-8}$")
    plt.xlabel("Channel flip probability, p")
    plt.ylabel("P(CRC passes | payload corrupted)")
    plt.title("CRC-8 Miss-Detection Probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "crc_miss_detection.png")
    plt.close()


def plot_summary_heatmap():
    payload_lengths = [4, 16, 32, 64, 96]
    p_values = np.linspace(0.0, 0.08, 9)
    rng = random.Random(RNG_SEED)
    grid = np.zeros((len(payload_lengths), len(p_values)))

    for i, length in enumerate(payload_lengths):
        payload = ("A" * length)
        for j, p in enumerate(p_values):
            success = 0
            trials = 800
            for k in range(trials):
                r = run_trial(payload, sequence=k % 256, channel="flip", p_error=p, rng=rng)
                success += int(r.success)
            grid[i, j] = success / trials

    plt.figure(figsize=(7.5, 4.5))
    im = plt.imshow(grid, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1, origin="lower")
    plt.colorbar(im, label="Frame success rate")
    plt.xticks(range(len(p_values)), [f"{p:.3f}" for p in p_values], rotation=45)
    plt.yticks(range(len(payload_lengths)), payload_lengths)
    plt.xlabel("Channel flip probability, p")
    plt.ylabel("Payload length (bytes)")
    plt.title("Frame Success Rate: Payload Length x Channel Error Rate")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "summary_heatmap.png")
    plt.close()


def main():
    print("Sweeping BSC (flip) channel...")
    flip_rows = sweep_flip_channel(np.linspace(0.0, 0.05, 11))
    write_csv(flip_rows, "flip_channel_sweep.csv")
    plot_ber_vs_p_flip(flip_rows)
    plot_crc_miss_detection(flip_rows)

    from src.framing import build_frame
    frame_bits = len(build_frame(TEST_PAYLOAD, 0))
    plot_frame_error_rate(flip_rows, frame_bits)

    print("Sweeping AWGN channel...")
    awgn_rows = sweep_awgn_channel(np.linspace(-2, 10, 13))
    write_csv(awgn_rows, "awgn_channel_sweep.csv")
    plot_ber_vs_ebn0(awgn_rows)

    print("Building payload-length x error-rate heatmap...")
    plot_summary_heatmap()

    print(f"\nDone. Figures written to {FIG_DIR}, data to {RES_DIR}")


if __name__ == "__main__":
    main()
