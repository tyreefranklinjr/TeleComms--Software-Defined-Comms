"""
crc.py
------
CRC-8 (polynomial 0x07 -- the CRC-8/SMBUS variant), tacked onto every
frame as the integrity check. Same algorithm from the original V0.2
script, just pulled out into its own module.
"""

from __future__ import annotations

POLY = 0x07


def calculate_crc8(data: bytes, poly: int = POLY) -> int:
    """Compute an 8-bit CRC over `data` using generator polynomial `poly`."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def verify_crc8(data: bytes, received_crc: int, poly: int = POLY) -> bool:
    return calculate_crc8(data, poly) == received_crc
