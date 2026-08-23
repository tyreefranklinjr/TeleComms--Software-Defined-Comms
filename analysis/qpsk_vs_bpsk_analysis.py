"""
qpsk_vs_bpsk_analysis.py
--------------------------
Monte Carlo comparison of BPSK vs. Gray-coded QPSK. Both modulate the
same random bit stream and both go through an AWGN channel matched to
the same Eb/N0 (see modem.awgn_channel_complex's docstring for why
bits_per_symbol changes the noise scaling, not the channel itself).

Two things this is actually checking, not just plotting:

1. Textbook claim: Gray-coded QPSK has the *same* per-bit BER as BPSK at
   equal Eb/N0, despite carrying twice the bits per symbol. That's a
   real, checkable claim (Gray coding makes every likely symbol error a
   single-bit error), not just "QPSK is better because it's fancier".
2. The practical tradeoff: QPSK gets that same BER while using half the
   symbol rate (half the bandwidth) for the same bit rate. That's the
   actual reason QPSK exists, not free performance, a bandwidth/bit-rate
   trade at equal energy efficiency.

Produces, under figures/:
  1. ber_bpsk_vs_qpsk.png       -- empirical BER, both schemes, vs shared theory curve
  2. qpsk_constellation.png     -- ideal points vs. noisy received points at one Eb/N0

Also writes results/bpsk_vs_qpsk_sweep.csv.

Run:  python analysis/qpsk_vs_bpsk_analysis.py
"""

import csv
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.modem import (
    modulate, demodulate, awgn_channel,
    modulate_qpsk, demodulate_qpsk, awgn_channel_complex,
    theoretical_ber_awgn, theoretical_ber_qpsk,
)

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

N_TRIALS = 100
BITS_PER_TRIAL = 2000
RNG_SEED = 11


def random_bitstring(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("01") for _ in range(n))


def sweep_bpsk(eb_n0_values, n_trials=N_TRIALS, bits_per_trial=BITS_PER_TRIAL):
    rng = random.Random(RNG_SEED)
    rows = []
    for ebn0 in eb_n0_values:
        total_errors, total_bits = 0, 0
        for _ in range(n_trials):
            bits = random_bitstring(rng, bits_per_trial)
            symbols = modulate(bits)
            rx = awgn_channel(symbols, ebn0, rng=rng)
            rx_bits = demodulate(rx)
            errors = sum(a != b for a, b in zip(bits, rx_bits))
            total_errors += errors
            total_bits += bits_per_trial
        rows.append((ebn0, total_errors / total_bits))
    return rows


def sweep_qpsk(eb_n0_values, n_trials=N_TRIALS, bits_per_trial=BITS_PER_TRIAL):
    rng = random.Random(RNG_SEED + 1)
    rows = []
    for ebn0 in eb_n0_values:
        total_errors, total_bits = 0, 0
        for _ in range(n_trials):
            bits = random_bitstring(rng, bits_per_trial)
            symbols = modulate_qpsk(bits)
            rx = awgn_channel_complex(symbols, ebn0, bits_per_symbol=2, rng=rng)
            rx_bits = demodulate_qpsk(rx)
            n = min(len(bits), len(rx_bits))
            errors = sum(a != b for a, b in zip(bits[:n], rx_bits[:n]))
            total_errors += errors
            total_bits += n
        rows.append((ebn0, total_errors / total_bits))
    return rows


def plot_ber_comparison(bpsk_rows, qpsk_rows, eb_n0_values):
    theory = [theoretical_ber_awgn(e) for e in eb_n0_values]
    bpsk_ber = [r[1] for r in bpsk_rows]
    qpsk_ber = [r[1] for r in qpsk_rows]

    plt.figure()
    plt.semilogy(eb_n0_values, theory, "k--",
                 label=r"theoretical: $Q(\sqrt{2E_b/N_0})$ (shared by both)")
    plt.semilogy(eb_n0_values, bpsk_ber, "o-", color="#2563eb",
                 label=f"empirical BPSK ({N_TRIALS} trials/pt)")
    plt.semilogy(eb_n0_values, qpsk_ber, "s-", color="#dc2626",
                 label=f"empirical QPSK, Gray-coded ({N_TRIALS} trials/pt)")
    plt.xlabel("$E_b/N_0$ (dB)")
    plt.ylabel("Bit Error Rate (log scale)")
    plt.title("BPSK vs. Gray-Coded QPSK: Same BER at Equal Eb/N0")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ber_bpsk_vs_qpsk.png")
    plt.close()


def plot_constellation(eb_n0_db=8, n_symbols=500):
    rng = random.Random(RNG_SEED + 2)
    bits = random_bitstring(rng, n_symbols * 2)
    ideal = modulate_qpsk(bits)
    noisy = awgn_channel_complex(ideal, eb_n0_db, bits_per_symbol=2, rng=rng)

    plt.figure(figsize=(6, 6))
    plt.scatter(noisy.real, noisy.imag, s=8, alpha=0.35, color="#dc2626",
                label=f"received symbols (Eb/N0={eb_n0_db} dB)")
    ideal_points = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
    plt.scatter(ideal_points.real, ideal_points.imag, s=150, color="black",
                marker="x", linewidths=2.5, label="ideal constellation points", zorder=5)
    plt.axhline(0, color="gray", linewidth=0.8)
    plt.axvline(0, color="gray", linewidth=0.8)
    plt.xlabel("In-phase (I)")
    plt.ylabel("Quadrature (Q)")
    plt.title(f"QPSK Constellation Under AWGN (Eb/N0 = {eb_n0_db} dB)")
    plt.legend(loc="upper right", fontsize=8)
    plt.axis("equal")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "qpsk_constellation.png")
    plt.close()


def write_csv(eb_n0_values, bpsk_rows, qpsk_rows):
    path = RES_DIR / "bpsk_vs_qpsk_sweep.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["eb_n0_db", "bpsk_empirical_ber", "qpsk_empirical_ber", "theoretical_ber"])
        for i, ebn0 in enumerate(eb_n0_values):
            writer.writerow([ebn0, bpsk_rows[i][1], qpsk_rows[i][1], theoretical_ber_awgn(ebn0)])
    print(f"wrote {path}")


def main():
    eb_n0_values = list(range(0, 11))

    print(f"Sweeping BPSK ({N_TRIALS} trials/point, {BITS_PER_TRIAL} bits/trial)...")
    bpsk_rows = sweep_bpsk(eb_n0_values)
    for ebn0, ber in bpsk_rows:
        print(f"  BPSK  Eb/N0={ebn0:5.1f} dB  empirical={ber:.5f}  theory={theoretical_ber_awgn(ebn0):.5f}")

    print(f"Sweeping QPSK ({N_TRIALS} trials/point, {BITS_PER_TRIAL} bits/trial)...")
    qpsk_rows = sweep_qpsk(eb_n0_values)
    for ebn0, ber in qpsk_rows:
        print(f"  QPSK  Eb/N0={ebn0:5.1f} dB  empirical={ber:.5f}  theory={theoretical_ber_qpsk(ebn0):.5f}")

    write_csv(eb_n0_values, bpsk_rows, qpsk_rows)
    plot_ber_comparison(bpsk_rows, qpsk_rows, eb_n0_values)
    plot_constellation()

    print(f"\nDone. Figures in {FIG_DIR}, data in {RES_DIR}")


if __name__ == "__main__":
    main()