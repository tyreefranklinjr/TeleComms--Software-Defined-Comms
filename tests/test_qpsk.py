"""
Tests for the QPSK additions to modem.py: modulate_qpsk, demodulate_qpsk,
awgn_channel_complex, theoretical_ber_qpsk.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from src.modem import (
    modulate_qpsk, demodulate_qpsk, awgn_channel_complex,
    theoretical_ber_qpsk, theoretical_ber_awgn,
)


def test_roundtrip_no_noise():
    bits = "0011011000"
    assert demodulate_qpsk(modulate_qpsk(bits)) == bits

def test_odd_length_gets_padded():
    bits = "101"
    syms = modulate_qpsk(bits)
    assert len(syms) == 2  # padded to 4 bits -> 2 symbols

def test_unit_average_energy():
    bits = "00011011"  # all four constellation points
    syms = modulate_qpsk(bits)
    energies = np.abs(syms) ** 2
    assert np.allclose(energies, 1.0, atol=1e-10)

def test_all_four_constellation_points_reachable():
    syms = modulate_qpsk("00011110")
    unique_points = set(np.round(s, 5) for s in syms)
    assert len(unique_points) == 4

def test_gray_coding_adjacent_quadrants_differ_by_one_bit():
    # Gray coding property: 00 <-> 01 (adjacent quadrants) should differ
    # in exactly one bit position, same for 00 <-> 10.
    def hamming(a, b):
        return sum(x != y for x, y in zip(a, b))
    assert hamming('00', '01') == 1
    assert hamming('00', '10') == 1
    assert hamming('01', '11') == 1
    assert hamming('10', '11') == 1

def test_awgn_complex_zero_noise_floor_at_high_ebn0():
    bits = "00" * 50
    syms = modulate_qpsk(bits)
    rx = awgn_channel_complex(syms, eb_n0_db=30, bits_per_symbol=2)
    recovered = demodulate_qpsk(rx)
    assert recovered == bits  # should be essentially error-free at 30 dB

def test_awgn_complex_matches_bpsk_noise_std_at_k1():
    # bits_per_symbol=1 should reduce to the same per-dimension noise
    # variance as the existing real-valued awgn_channel for BPSK.
    import random
    import math
    rng = random.Random(0)
    eb_n0_db = 5
    symbols = np.array([1.0 + 0j] * 20000)
    rx = awgn_channel_complex(symbols, eb_n0_db, bits_per_symbol=1, rng=rng)
    empirical_std = np.std(rx.real - 1.0)
    eb_n0_linear = 10 ** (eb_n0_db / 10)
    expected_std = math.sqrt(1.0 / (2 * eb_n0_linear))
    assert abs(empirical_std - expected_std) / expected_std < 0.05

def test_theoretical_ber_qpsk_equals_bpsk():
    # Gray-coded QPSK BER should equal BPSK BER at the same Eb/N0.
    for ebn0 in [0, 3, 6, 9]:
        assert theoretical_ber_qpsk(ebn0) == theoretical_ber_awgn(ebn0)