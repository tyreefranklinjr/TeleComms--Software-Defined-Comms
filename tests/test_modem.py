import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.modem import modulate, demodulate, flip_channel, theoretical_ber_awgn

def test_modulate_demodulate_roundtrip():
    bits = "1010110001"
    assert demodulate(modulate(bits)) == bits

def test_flip_channel_zero_prob_no_change():
    symbols = modulate("110010")
    rng = random.Random(0)
    result = flip_channel(symbols, 0.0, rng=rng)
    assert result == symbols

def test_flip_channel_full_prob_flips_all():
    symbols = modulate("110010")
    rng = random.Random(0)
    result = flip_channel(symbols, 1.0, rng=rng)
    assert result == [-s for s in symbols]

def test_theoretical_ber_decreasing_in_snr():
    assert theoretical_ber_awgn(0) > theoretical_ber_awgn(10)
