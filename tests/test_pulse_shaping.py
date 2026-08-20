"""
Tests for the V0.4 pulse-shaping additions to modem.py: upsample,
rrcosfilter, modulate_bpsk_rrc.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest

from src.modem import upsample, rrcosfilter, modulate_bpsk_rrc


# ---------- upsample ----------

def test_upsample_length():
    symbols = np.array([1.0, -1.0, 1.0, 1.0])
    sps = 8
    out = upsample(symbols, sps)
    assert len(out) == len(symbols) * sps

def test_upsample_places_symbols_correctly():
    symbols = np.array([1.0, -1.0, 1.0])
    sps = 4
    out = upsample(symbols, sps)
    # symbols should land at indices 0, 4, 8
    assert out[0] == 1.0
    assert out[4] == -1.0
    assert out[8] == 1.0

def test_upsample_zero_stuffing():
    symbols = np.array([1.0, -1.0])
    sps = 4
    out = upsample(symbols, sps)
    # everything between symbol positions should be zero
    assert np.all(out[1:4] == 0)
    assert np.all(out[5:8] == 0)

def test_upsample_sps_one_is_identity():
    symbols = np.array([1.0, -1.0, 1.0])
    out = upsample(symbols, 1)
    assert np.array_equal(out.real, symbols)


# ---------- rrcosfilter ----------

def test_rrcosfilter_rejects_even_taps():
    with pytest.raises(ValueError):
        rrcosfilter(num_taps=32, alpha=0.35, sps=8)

def test_rrcosfilter_output_length():
    h = rrcosfilter(num_taps=33, alpha=0.35, sps=8)
    assert len(h) == 33

def test_rrcosfilter_is_symmetric():
    h = rrcosfilter(num_taps=33, alpha=0.35, sps=8)
    assert np.allclose(h, h[::-1], atol=1e-10)

def test_rrcosfilter_energy_normalized():
    h = rrcosfilter(num_taps=33, alpha=0.35, sps=8)
    energy = np.sum(h ** 2)
    assert np.isclose(energy, 1.0, atol=1e-8)

def test_rrcosfilter_peak_at_center():
    h = rrcosfilter(num_taps=33, alpha=0.35, sps=8)
    center = len(h) // 2
    assert np.argmax(np.abs(h)) == center

def test_rrcosfilter_no_nans_across_alpha_range():
    for alpha in [0.0, 0.1, 0.35, 0.5, 0.99]:
        h = rrcosfilter(num_taps=33, alpha=alpha, sps=8)
        assert not np.any(np.isnan(h)), f"NaN in filter at alpha={alpha}"

def test_rrcosfilter_different_sps_still_valid():
    for sps in [2, 4, 8, 16]:
        h = rrcosfilter(num_taps=33, alpha=0.35, sps=sps)
        assert len(h) == 33
        assert np.isclose(np.sum(h ** 2), 1.0, atol=1e-8)


# ---------- modulate_bpsk_rrc ----------

def test_modulate_bpsk_rrc_output_length():
    symbols = np.array([1.0, -1.0, 1.0, 1.0, -1.0])
    sps, num_taps = 8, 33
    waveform = modulate_bpsk_rrc(symbols, sps=sps, num_taps=num_taps, alpha=0.35)
    # full convolution length: len(upsampled) + len(filter) - 1
    expected_len = len(symbols) * sps + num_taps - 1
    assert len(waveform) == expected_len

def test_modulate_bpsk_rrc_no_nans():
    symbols = np.array([1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0])
    waveform = modulate_bpsk_rrc(symbols, sps=8, num_taps=33, alpha=0.35)
    assert not np.any(np.isnan(waveform))

def test_modulate_bpsk_rrc_default_args_run():
    symbols = np.array([1.0, -1.0, 1.0])
    waveform = modulate_bpsk_rrc(symbols)  # uses sps=8, num_taps=33, alpha=0.35
    assert len(waveform) > 0

def test_modulate_bpsk_rrc_sign_pattern_survives():
    # matched-filtering isn't implemented yet (that's V0.7 receiver work),
    # but the waveform's real part should still peak near the expected
    # symbol centers with the correct sign, since RRC filtering doesn't
    # invert polarity.
    symbols = np.array([1.0, -1.0])
    sps, num_taps = 8, 33
    waveform = modulate_bpsk_rrc(symbols, sps=sps, num_taps=num_taps, alpha=0.35)
    group_delay = num_taps // 2
    first_symbol_center = group_delay + 0 * sps
    second_symbol_center = group_delay + 1 * sps
    assert waveform.real[first_symbol_center] > 0
    assert waveform.real[second_symbol_center] < 0