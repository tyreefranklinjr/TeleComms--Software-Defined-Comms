"""
fec_viterbi_demo.py
--------------------
Two things for the V0.6 convolutional-coding addition (src/fec.py):

1. A trellis diagram that actually shows the Viterbi algorithm doing its
   job: a short message is encoded, corrupted with a couple of bit
   errors, and the winning survivor path the decoder traces back through
   is drawn over the full trellis structure. This uses a small
   illustrative K=3 (4-state) code, not the real K=7 (64-state) FEC in
   src/fec.py, a 64-state trellis is not something you can usefully look
   at in one figure. The mechanism (path metrics, branch metrics,
   survivor selection, traceback) is identical, just at a scale a human
   can actually read.

2. A coding-gain Monte Carlo sweep using the *real* K=7 code from
   src/fec.py (hard and soft decision both), compared against the
   uncoded closed-form BER curve, at matched Eb/N0. This is the number
   that actually justifies adding FEC: how many dB of margin the code
   buys you at a given target BER.

Produces, under figures/:
  1. viterbi_trellis_demo.png     -- illustrative 4-state trellis + winning path
  2. coding_gain_bpsk.png         -- coded (hard/soft) vs uncoded BER vs Eb/N0

Also writes results/coding_gain_sweep.csv.

Run:  python analysis/fec_viterbi_demo.py
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

from src.fec import ConvolutionalEncoder, ViterbiDecoder, SoftViterbiDecoder
from src.modem import modulate, awgn_channel, theoretical_ber_awgn

FIG_DIR = ROOT / "figures"
RES_DIR = ROOT / "results"
FIG_DIR.mkdir(exist_ok=True)
RES_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (8, 4.5),
    "figure.dpi": 140,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10,
})

CODE_RATE = 0.5  # rate 1/2, matches src/fec.py's 2-outputs-per-input-bit encoder
RNG_SEED = 21


# ---------------------------------------------------------------------
# 1. Illustrative small trellis (K=3, 4 states) with a real winning path
# ---------------------------------------------------------------------
# Same algorithmic shape as src/fec.py's ViterbiDecoder, just small
# enough to actually plot: 4 states instead of 64, generators 0b111
# (7 octal) and 0b101 (5 octal), the textbook minimal example.

class DemoTrellis:
    def __init__(self):
        self.k = 3
        self.num_states = 4
        self.g1 = 0b111
        self.g2 = 0b101
        self.next_state = np.zeros((4, 2), dtype=int)
        self.expected_output = np.zeros((4, 2, 2), dtype=int)
        for state in range(4):
            for bit in (0, 1):
                window = (bit << 2) | state
                out1 = bin(window & self.g1).count('1') % 2
                out2 = bin(window & self.g2).count('1') % 2
                next_st = ((state >> 1) | (bit << 1)) & 0x3
                self.next_state[state, bit] = next_st
                self.expected_output[state, bit] = [out1, out2]

    def encode(self, bits: str) -> str:
        state = 0
        out = []
        for ch in bits + "00":  # 2-bit flush for K=3
            b = int(ch)
            window = (b << 2) | state
            o1 = bin(window & self.g1).count('1') % 2
            o2 = bin(window & self.g2).count('1') % 2
            out.append(f"{o1}{o2}")
            state = self.next_state[state, b]
        return "".join(out)

    def decode(self, received_bits: str):
        pairs = [[int(received_bits[i]), int(received_bits[i + 1])]
                  for i in range(0, len(received_bits), 2)]
        INF = 10 ** 9
        path_metrics = np.full(4, INF, dtype=float)
        path_metrics[0] = 0.0
        history = []
        for rx_pair in pairs:
            new_metrics = np.full(4, INF, dtype=float)
            step_hist = np.zeros((4, 2), dtype=int)
            for state in range(4):
                if path_metrics[state] == INF:
                    continue
                for bit in (0, 1):
                    nxt = self.next_state[state, bit]
                    expected = self.expected_output[state, bit]
                    metric = path_metrics[state] + np.sum(expected != rx_pair)
                    if metric < new_metrics[nxt]:
                        new_metrics[nxt] = metric
                        step_hist[nxt] = [state, bit]
            path_metrics = new_metrics
            history.append(step_hist)

        state = 0
        bits_rev = []
        path_rev = [0]
        for step in range(len(pairs) - 1, -1, -1):
            prev, bit = history[step][state]
            bits_rev.append(str(bit))
            path_rev.append(prev)
            state = prev
        bits_rev.reverse()
        path = list(reversed(path_rev))
        return "".join(bits_rev[:-2]), path


def plot_trellis_demo():
    trellis = DemoTrellis()
    message = "1011"
    encoded = trellis.encode(message)

    # induce 1 bit error so the decoder actually has to work, not just
    # trace a trivial noiseless path
    corrupted = list(encoded)
    corrupted[3] = "1" if corrupted[3] == "0" else "0"
    corrupted = "".join(corrupted)

    decoded, winning_path = trellis.decode(corrupted)
    n_steps = len(encoded) // 2

    fig, ax = plt.subplots(figsize=(8, 4.5))

    # background: full generic trellis structure (same at every time step,
    # since transitions don't depend on which step we're at)
    for t in range(n_steps):
        for state in range(4):
            for bit in (0, 1):
                nxt = trellis.next_state[state, bit]
                ax.plot([t, t + 1], [state, nxt], color="lightgray",
                        linewidth=1.0, zorder=1)

    # winning survivor path, bold
    for t in range(n_steps):
        ax.plot([t, t + 1], [winning_path[t], winning_path[t + 1]],
                 color="#dc2626", linewidth=3.0, zorder=3)

    for t in range(n_steps + 1):
        for state in range(4):
            ax.plot(t, state, "o", color="black", markersize=5, zorder=2)

    ax.set_xlabel("Time step (received symbol pair)")
    ax.set_ylabel("Trellis state")
    ax.set_yticks(range(4))
    ax.set_title(
        f"Viterbi Decoding: Winning Survivor Path\n"
        f"illustrative K=3, 4-state code, message='{message}', 1 induced bit error\n"
        f"decoded='{decoded}', correct={decoded == message}",
        fontsize=10,
    )
    ax.set_xlim(-0.3, n_steps + 0.3)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "viterbi_trellis_demo.png")
    plt.close()

    print(f"trellis demo: message={message}  decoded={decoded}  "
          f"corrected={decoded == message}")


# ---------------------------------------------------------------------
# 2. Coding gain: real K=7 code (src/fec.py) vs uncoded, Monte Carlo
# ---------------------------------------------------------------------

N_TRIALS = 30
BITS_PER_TRIAL = 200


def coded_trial_hard(bits: str, eb_n0_db: float, rng: random.Random,
                      encoder: ConvolutionalEncoder, decoder: ViterbiDecoder) -> int:
    encoded = encoder.encode_stream(bits)
    symbols = modulate(encoded)
    # rate 1/2: coded symbols carry half the energy per symbol that an
    # uncoded bit would, at the same total transmit energy per info bit
    coded_ec_n0_db = eb_n0_db + 10 * np.log10(CODE_RATE)
    rx = awgn_channel(symbols, coded_ec_n0_db, rng=rng)
    rx_bits = "".join("1" if s > 0 else "0" for s in rx)
    decoded = decoder.decode(rx_bits)
    n = min(len(decoded), len(bits))
    return sum(a != b for a, b in zip(decoded[:n], bits[:n]))


def coded_trial_soft(bits: str, eb_n0_db: float, rng: random.Random,
                      encoder: ConvolutionalEncoder, decoder: SoftViterbiDecoder) -> int:
    encoded = encoder.encode_stream(bits)
    symbols = modulate(encoded)
    coded_ec_n0_db = eb_n0_db + 10 * np.log10(CODE_RATE)
    rx = np.array(awgn_channel(symbols, coded_ec_n0_db, rng=rng))
    decoded = decoder.decode_soft(rx)
    n = min(len(decoded), len(bits))
    return sum(a != b for a, b in zip(decoded[:n], bits[:n]))


def sweep_coding_gain(eb_n0_values, n_trials=N_TRIALS, bits_per_trial=BITS_PER_TRIAL):
    rng_hard = random.Random(RNG_SEED)
    rng_soft = random.Random(RNG_SEED + 1)
    enc = ConvolutionalEncoder()
    hard_dec = ViterbiDecoder()
    soft_dec = SoftViterbiDecoder()

    rows = []
    for ebn0 in eb_n0_values:
        hard_errors, soft_errors, total_bits = 0, 0, 0
        for _ in range(n_trials):
            bits = "".join(rng_hard.choice("01") for _ in range(bits_per_trial))
            hard_errors += coded_trial_hard(bits, ebn0, rng_hard, enc, hard_dec)
            soft_errors += coded_trial_soft(bits, ebn0, rng_soft, enc, soft_dec)
            total_bits += bits_per_trial

        hard_ber = hard_errors / total_bits
        soft_ber = soft_errors / total_bits
        theory_uncoded = theoretical_ber_awgn(ebn0)
        rows.append(dict(
            eb_n0_db=ebn0,
            hard_coded_ber=hard_ber,
            soft_coded_ber=soft_ber,
            uncoded_theoretical_ber=theory_uncoded,
            n_trials=n_trials,
            bits_per_trial=bits_per_trial,
        ))
        print(f"  Eb/N0={ebn0:4.1f} dB  hard={hard_ber:.5f}  soft={soft_ber:.5f}  "
              f"uncoded_theory={theory_uncoded:.5f}")
    return rows


def plot_coding_gain(rows):
    ebn0 = [r["eb_n0_db"] for r in rows]
    hard = [max(r["hard_coded_ber"], 1e-6) for r in rows]
    soft = [max(r["soft_coded_ber"], 1e-6) for r in rows]
    uncoded = [r["uncoded_theoretical_ber"] for r in rows]

    plt.figure(figsize=(7, 4.5))
    plt.semilogy(ebn0, uncoded, "k--", label="uncoded BPSK (theoretical)")
    plt.semilogy(ebn0, hard, "o-", color="#2563eb", label=f"rate-1/2 K=7, hard decision ({N_TRIALS} trials/pt)")
    plt.semilogy(ebn0, soft, "s-", color="#dc2626", label=f"rate-1/2 K=7, soft decision ({N_TRIALS} trials/pt)")
    plt.xlabel("$E_b/N_0$ (dB)")
    plt.ylabel("Bit Error Rate (log scale)")
    plt.title("Coding Gain: Convolutional FEC vs. Uncoded BPSK")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIG_DIR / "coding_gain_bpsk.png")
    plt.close()


def write_csv(rows):
    path = RES_DIR / "coding_gain_sweep.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path}")


def main():
    print("Building trellis demo...")
    plot_trellis_demo()

    print(f"\nRunning coding-gain sweep ({N_TRIALS} trials/point, "
          f"{BITS_PER_TRIAL} bits/trial, hard + soft)...")
    eb_n0_values = list(np.arange(0, 7, 1))
    rows = sweep_coding_gain(eb_n0_values)
    write_csv(rows)
    plot_coding_gain(rows)

    print(f"\nDone. Figures in {FIG_DIR}, data in {RES_DIR}")


if __name__ == "__main__":
    main()