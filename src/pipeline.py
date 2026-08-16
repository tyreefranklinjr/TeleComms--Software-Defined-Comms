"""
pipeline.py
-----------
Wires the physical layer (modem.py), link layer (framing.py, crc.py),
and channel model together into one transmit -> channel -> receive
call. This is the function the statistical analysis hammers thousands
of times per data point, so I wanted exactly one version of "what does
a trial mean" instead of two implementations drifting apart.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from .framing import build_frame, parse_frame, FrameParseError
from .modem import modulate, demodulate, flip_channel, awgn_channel


@dataclass
class TrialResult:
    success: bool               # CRC passed AND payload matches original
    crc_ok: bool                # CRC passed (may still be a false negative)
    payload_matches: bool       # recovered payload == original payload
    bit_errors: int             # Hamming distance between tx/rx bit streams
    frame_bits: int


def run_trial(
    payload: str,
    sequence: int = 0,
    channel: str = "flip",
    p_error: float = 0.0,
    eb_n0_db: float = 10.0,
    rng: Optional[random.Random] = None,
) -> TrialResult:
    """
    Run one full transmit -> channel -> receive cycle and score the outcome.
    channel: "flip" (BSC, parameterized by p_error) or "awgn" (parameterized
    by eb_n0_db).
    """
    tx_bits = build_frame(payload, sequence)
    symbols = modulate(tx_bits)

    if channel == "flip":
        rx_symbols = flip_channel(symbols, p_error, rng=rng)
    elif channel == "awgn":
        rx_symbols = awgn_channel(symbols, eb_n0_db, rng=rng)
    else:
        raise ValueError(f"unknown channel type: {channel}")

    rx_bits = demodulate(rx_symbols)
    bit_errors = sum(a != b for a, b in zip(tx_bits, rx_bits))

    try:
        frame, crc_ok = parse_frame(rx_bits)
        payload_matches = frame.payload == payload
    except FrameParseError:
        crc_ok = False
        payload_matches = False

    return TrialResult(
        success=crc_ok and payload_matches,
        crc_ok=crc_ok,
        payload_matches=payload_matches,
        bit_errors=bit_errors,
        frame_bits=len(tx_bits),
    )
