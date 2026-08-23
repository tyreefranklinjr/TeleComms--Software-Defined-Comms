"""
Tests for src/fec.py: ConvolutionalEncoder, ViterbiDecoder,
SoftViterbiDecoder.
"""

import sys
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from src.fec import ConvolutionalEncoder, ViterbiDecoder, SoftViterbiDecoder
from src.modem import modulate, awgn_channel


# ---------- encoder ----------

def test_encoded_length_is_rate_half_plus_flush():
    enc = ConvolutionalEncoder()
    bits = "10110011"
    encoded = enc.encode_stream(bits)
    assert len(encoded) == 2 * (len(bits) + 6)

def test_encoder_output_is_binary_string():
    enc = ConvolutionalEncoder()
    encoded = enc.encode_stream("1010")
    assert set(encoded) <= {"0", "1"}

def test_encoder_deterministic():
    enc1 = ConvolutionalEncoder()
    enc2 = ConvolutionalEncoder()
    bits = "110010110"
    assert enc1.encode_stream(bits) == enc2.encode_stream(bits)

def test_encoder_all_zeros_produces_all_zeros():
    # zero state, zero input, forever -> zero output, useful sanity check
    enc = ConvolutionalEncoder()
    encoded = enc.encode_stream("0000")
    assert encoded == "0" * len(encoded)


# ---------- hard-decision round trip ----------

def test_hard_roundtrip_no_noise():
    enc = ConvolutionalEncoder()
    dec = ViterbiDecoder()
    bits = "1011001101001110"
    encoded = enc.encode_stream(bits)
    decoded = dec.decode(encoded)
    assert decoded == bits

def test_hard_roundtrip_various_lengths():
    enc = ConvolutionalEncoder()
    dec = ViterbiDecoder()
    for bits in ["0", "1", "1010", "111111", "0101010101010101"]:
        encoded = enc.encode_stream(bits)
        assert dec.decode(encoded) == bits

def test_hard_decode_corrects_scattered_bit_errors():
    # K=7 with this generator pair has free distance 10, comfortably
    # corrects a handful of scattered single-bit errors in a short frame.
    enc = ConvolutionalEncoder()
    dec = ViterbiDecoder()
    bits = "10110011010011101011001"
    encoded = enc.encode_stream(bits)

    rng = random.Random(3)
    corrupted = list(encoded)
    for p in rng.sample(range(len(corrupted)), 4):
        corrupted[p] = "1" if corrupted[p] == "0" else "0"
    corrupted = "".join(corrupted)

    assert dec.decode(corrupted) == bits

def test_hard_decode_history_matches_plain_decode():
    enc = ConvolutionalEncoder()
    dec = ViterbiDecoder()
    bits = "110100111010"
    encoded = enc.encode_stream(bits)
    plain = dec.decode(encoded)
    with_hist, history, state_path = dec.decode_with_history(encoded)
    assert plain == with_hist == bits
    assert state_path[0] == 0       # encoder always starts at state 0
    assert state_path[-1] == 0      # flush bits force it back to state 0
    assert len(state_path) == len(encoded) // 2 + 1


# ---------- soft-decision round trip ----------

def test_soft_roundtrip_no_noise():
    enc = ConvolutionalEncoder()
    dec = SoftViterbiDecoder()
    bits = "1011001101001110"
    encoded = enc.encode_stream(bits)
    symbols = np.array(modulate(encoded))  # bipolar +/-1, no noise
    decoded = dec.decode_soft(symbols)
    assert decoded == bits

def test_soft_decode_survives_light_noise():
    enc = ConvolutionalEncoder()
    dec = SoftViterbiDecoder()
    bits = "10110011010011101011001"
    encoded = enc.encode_stream(bits)
    symbols = modulate(encoded)

    rng = random.Random(5)
    noisy = np.array(awgn_channel(symbols, eb_n0_db=4.0, rng=rng))
    decoded = dec.decode_soft(noisy)
    assert decoded == bits

def test_soft_and_hard_agree_at_zero_noise():
    enc = ConvolutionalEncoder()
    hard_dec = ViterbiDecoder()
    soft_dec = SoftViterbiDecoder()
    bits = "0110100111"
    encoded = enc.encode_stream(bits)

    hard_out = hard_dec.decode(encoded)
    soft_out = soft_dec.decode_soft(np.array(modulate(encoded)))
    assert hard_out == soft_out == bits