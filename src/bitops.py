"""
bitops.py
---------
The boring-but-necessary conversions everything else builds on: string
<-> bit string <-> bytes. Kept pure Python on purpose, no NumPy here,
so these can be unit tested without pulling in anything heavier.
"""

from __future__ import annotations


def str_to_bits(text: str) -> str:
    """Encode a string as an 8-bit-per-character binary string (MSB first)."""
    return "".join(f"{ord(ch):08b}" for ch in text)


def bits_to_string(bits: str) -> str:
    """Inverse of str_to_bits. Silently drops a trailing partial byte."""
    if not bits:
        return ""
    chars = []
    for i in range(0, len(bits) - (len(bits) % 8), 8):
        byte = bits[i:i + 8]
        chars.append(chr(int(byte, 2)))
    return "".join(chars)


def bits_to_bytes(bits: str) -> bytes:
    """Pack a bit string into a bytes object (zero-padded on the right)."""
    pad = (-len(bits)) % 8
    bits = bits + "0" * pad
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def hamming_distance(a: str, b: str) -> int:
    """Number of differing bit positions between two equal-length bit strings."""
    if len(a) != len(b):
        raise ValueError("bit strings must be the same length")
    return sum(x != y for x, y in zip(a, b))
