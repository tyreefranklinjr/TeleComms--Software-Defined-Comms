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
import numpy as np


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

def upsample(symbols: np.ndarray, sps: int) -> np.ndarray:
    """
    Inserts (sps - 1) zeros between each symbol for pulse shaping.
    """
    out = np.zeros(len(symbols) * sps, dtype=complex)
    out[::sps] = symbols
    return out

def rrcosfilter(num_taps: int, alpha: float, sps: int) -> np.ndarray:
    """
    Generates a Root-Raised-Cosine (RRC) filter impulse response.
    num_taps must be an odd integer to maintain symmetry.
    """
    if num_taps % 2 == 0:
        raise ValueError("num_taps must be an odd integer for symmetry.")
        
    half_taps = num_taps // 2
    t = np.arange(-half_taps, half_taps + 1, dtype=float)
    h = np.zeros(num_taps, dtype=float)
    
    idx_zero = np.where(t == 0.0)
    h[idx_zero] = (1.0 - alpha + (4.0 * alpha / np.pi)) / np.sqrt(sps)
    
    if alpha != 0:
        threshold = np.abs(t) == (sps / (4.0 * alpha))
        if np.any(threshold):
            term = (alpha / np.sqrt(2.0 * sps))
            val = (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * alpha)) + \
                  (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * alpha))
            h[threshold] = term * val
            
    normal_indices = np.where((t != 0.0) & (np.abs(t) != (sps / (4.0 * alpha) if alpha != 0 else -1)))
    if alpha == 0:
        tn = t[normal_indices] / sps
        h[normal_indices] = np.sin(np.pi * tn) / (np.pi * tn) / np.sqrt(sps)
    else:
        tn = t[normal_indices] / sps
        numerator = np.sin(np.pi * tn * (1.0 - alpha)) + \
                    4.0 * alpha * tn * np.cos(np.pi * tn * (1.0 + alpha))
        denominator = np.pi * tn * (1.0 - (4.0 * alpha * tn)**2)
        h[normal_indices] = numerator / denominator / np.sqrt(sps)
        
    # Normalize filter energy
    h = h / np.sqrt(np.sum(h**2))
    return h

def modulate_bpsk_rrc(symbols: np.ndarray, sps: int = 8, num_taps: int = 33, alpha: float = 0.35) -> np.ndarray:
    """
    Full V0.4 BPSK modulation pipeline:
    1. Converts complex/real symbols via upsampling (zero-stuffing).
    2. Generates RRC filter coefficients.
    3. Convolves the upsampled stream with the filter to produce a band-limited waveform.
    """
    upsampled = upsample(symbols, sps)
    h = rrcosfilter(num_taps, alpha, sps)
    waveform = np.convolve(upsampled, h, mode='full')
    return waveform


# ---------------------------------------------------------------------
# QPSK: 2 bits/symbol, Gray-coded, unit average symbol energy
# ---------------------------------------------------------------------

_QPSK_MAP = {
    '00':  1.0 + 1.0j,
    '01': -1.0 + 1.0j,
    '11': -1.0 - 1.0j,
    '10':  1.0 - 1.0j,
}
_QPSK_DEMAP = {v: k for k, v in _QPSK_MAP.items()}


def modulate_qpsk(bits: str) -> np.ndarray:
    """
    Packs bits into pairs (2 bits/symbol) and maps them to Gray-coded
    QPSK constellation points, normalized to unit average symbol energy
    (each point has magnitude 1, matching the BPSK convention of Eb=1
    per bit so the two schemes are directly comparable at the same
    Eb/N0).
    """
    if len(bits) % 2 != 0:
        bits += '0'  # pad if odd number of bits

    norm = 1.0 / np.sqrt(2.0)  # unit-energy normalization
    symbols = []
    for i in range(0, len(bits), 2):
        pair = bits[i:i + 2]
        symbols.append(_QPSK_MAP[pair] * norm)
    return np.array(symbols, dtype=complex)


def demodulate_qpsk(received_symbols: np.ndarray) -> str:
    """
    Hard-decision quadrant slicing: recovers the Gray-coded bit pair
    for each received (possibly noisy) complex symbol based on the
    sign of its real and imaginary parts.
    """
    bits = []
    for sym in received_symbols:
        r_pos = sym.real >= 0
        i_pos = sym.imag >= 0
        if r_pos and i_pos:
            bits.append('00')
        elif not r_pos and i_pos:
            bits.append('01')
        elif not r_pos and not i_pos:
            bits.append('11')
        else:
            bits.append('10')
    return "".join(bits)


def awgn_channel_complex(symbols: np.ndarray, eb_n0_db: float, bits_per_symbol: int,
                          rng: random.Random | None = None) -> np.ndarray:
    """
    Complex AWGN channel for M-ary schemes with `bits_per_symbol` bits
    per constellation point and unit average symbol energy (Es=1).

    Given Es = bits_per_symbol * Eb and Es/N0 = bits_per_symbol * (Eb/N0),
    the per-dimension (I and Q) noise variance is N0/2 =
    1 / (2 * bits_per_symbol * Eb/N0_linear). With bits_per_symbol=1 this
    collapses to the same formula awgn_channel() already uses for BPSK,
    so the two are on equal footing at the same Eb/N0.
    """
    rng = rng or random
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    noise_std = math.sqrt(1.0 / (2 * bits_per_symbol * eb_n0_linear))
    noise = np.array([
        complex(rng.gauss(0, noise_std), rng.gauss(0, noise_std))
        for _ in range(len(symbols))
    ])
    return symbols + noise


def theoretical_ber_qpsk(eb_n0_db: float) -> float:
    """
    Closed-form per-bit BER for Gray-coded QPSK: identical to BPSK's
    Q(sqrt(2*Eb/N0)). Gray coding means every symbol error, wrong
    quadrant, differs from the correct one in exactly one bit, so the
    bit error rate doesn't inherit the (worse) symbol error rate; it
    matches BPSK bit-for-bit at the same Eb/N0 despite carrying twice
    the bits per symbol.
    """
    return theoretical_ber_awgn(eb_n0_db)


def modulate_qpsk(bits: str) -> np.ndarray:
    """
    Takes a binary string, packs bits into pairs (2 bits per symbol),
    and maps them to QPSK constellation points using Gray coding,
    normalized for unit average energy.
    """
    if len(bits) % 2 != 0:
        bits += '0'  # Pad if odd number of bits

    # Gray-coded QPSK mapping table
    # Format: 'bits': complex_coordinate
    mapping = {
        '00':  1.0 + 1.0j,
        '01': -1.0 + 1.0j,
        '11': -1.0 - 1.0j,
        '10':  1.0 - 1.0j,
    }
    norm = 1.0 / np.sqrt(2.0)  # Energy normalization factor

    symbols = []
    for i in range(0, len(bits), 2):
        pair = bits[i:i + 2]
        symbols.append(mapping[pair] * norm)

    return np.array(symbols, dtype=complex)


def demodulate_qpsk(received_symbols: np.ndarray) -> str:
    """
    Takes noisy complex symbols, performs hard-decision slicing based
    on the quadrants, and recovers the original bit string.
    """
    bits = []
    for sym in received_symbols:
        real_part = sym.real
        imag_part = sym.imag
        # Determine quadrant, mapping back to Gray-coded bits
        r_pos = real_part >= 0
        i_pos = imag_part >= 0
        if r_pos and i_pos:
            bits.append('00')
        elif not r_pos and i_pos:
            bits.append('01')
        elif not r_pos and not i_pos:
            bits.append('11')
        else:
            bits.append('10')
    return "".join(bits)


def awgn_channel_qpsk(symbols: np.ndarray, eb_n0_db: float, rng: np.random.Generator | None = None) -> np.ndarray:
    """
    Complex AWGN channel for QPSK. Noise is added independently to the I
    and Q rails. QPSK carries 2 bits/symbol at unit average symbol energy
    (Es=1, so Eb=Es/2=0.5), which is why the per-dimension noise variance
    here is half of the BPSK case for the same Eb/N0: N0/2 = 1/(4*Eb/N0),
    not 1/(2*Eb/N0). This is what makes theoretical_ber_qpsk work out to
    the same curve as BPSK per bit, not a worse one.
    """
    rng = rng or np.random.default_rng()
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    noise_std = np.sqrt(1.0 / (4 * eb_n0_linear))
    noise = rng.normal(0, noise_std, size=symbols.shape) + 1j * rng.normal(0, noise_std, size=symbols.shape)
    return symbols + noise


def theoretical_ber_qpsk(eb_n0_db: float) -> float:
    """
    Closed-form QPSK bit error rate over AWGN: same as BPSK per bit,
    Q(sqrt(2*Eb/N0)), because Gray-coded QPSK is two independent BPSK
    channels (in-phase and quadrature) sharing the symbol energy, and
    the Gray mapping means a symbol error at high SNR almost always
    flips exactly one of the two bits, not both.
    """
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    return 0.5 * math.erfc(math.sqrt(eb_n0_linear))