"""
modem.py
--------
BPSK modulation/demodulation, plus two channel models:

  * flip_channel  -- the original V0.3 model. Each modulated symbol
                     gets independently sign-flipped with probability
                     p. This is a Binary Symmetric Channel, parameterized
                     directly by bit-error rate.

  * awgn_channel   -- a step closer to a real RF link: Gaussian noise
                     added to the +/-1 BPSK symbols at a given Eb/N0
                     (energy-per-bit to noise-PSD ratio), recovered by
                     hard-decision (sign) detection. BER should follow
                     Q(sqrt(2*Eb/N0)) -- checked empirically in
                     analysis/statistical_analysis.py.

Kept both around deliberately: flip_channel is the noise model I
hand-rolled first, awgn_channel is the one an actual link obeys. Nice
to be able to point the same pipeline at either.
"""

from __future__ import annotations

import math
import random
from typing import List


def modulate(bits: str) -> List[float]:
    """BPSK: 0 -> -1.0, 1 -> +1.0"""
    return [1.0 if b == "1" else -1.0 for b in bits]


def demodulate(symbols: List[float]) -> str:
    """Hard-decision detection: sign(symbol) -> bit."""
    return "".join("1" if s > 0 else "0" for s in symbols)


def flip_channel(symbols: List[float], p_error: float, rng: random.Random | None = None) -> List[float]:
    """
    Binary Symmetric Channel: each symbol is independently negated
    (i.e. the corresponding bit is flipped) with probability p_error.
    """
    rng = rng or random
    return [-s if rng.random() < p_error else s for s in symbols]


def awgn_channel(symbols: List[float], eb_n0_db: float, rng: random.Random | None = None) -> List[float]:
    """
    Additive White Gaussian Noise channel at a given Eb/N0 (dB), unit
    energy per symbol (Eb = 1). Noise variance is derived from the
    standard BPSK relation N0/2 = 1 / (2 * 10^(Eb/N0_dB / 10)).
    """
    rng = rng or random
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    noise_std = math.sqrt(1.0 / (2 * eb_n0_linear))
    return [s + rng.gauss(0, noise_std) for s in symbols]


def theoretical_ber_awgn(eb_n0_db: float) -> float:
    """Closed-form BPSK bit-error rate over AWGN: Q(sqrt(2*Eb/N0))."""
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    return 0.5 * math.erfc(math.sqrt(eb_n0_linear))
