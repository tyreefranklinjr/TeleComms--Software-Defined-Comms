"""
framing.py
----------
The frame format I designed, and the code to build/parse it.

Layout (everything but the payload is a fixed 1 byte / 8 bits):

    +----------+----------+------------+-----------------+---------+
    | HEADER   | LENGTH   | SEQUENCE   | PAYLOAD (N*8 b)  | CRC-8   |
    | 8 bits   | 8 bits   | 8 bits     | LENGTH*8 bits    | 8 bits  |
    +----------+----------+------------+-----------------+---------+

    HEADER   : fixed sync/marker byte (0xFF) identifying frame start
    LENGTH   : payload length in bytes (0-255)
    SEQUENCE : monotonically increasing frame counter (mod 256)
    PAYLOAD  : UTF-8 encoded application data
    CRC-8    : checksum over HEADER || LENGTH || SEQUENCE || PAYLOAD
"""

from __future__ import annotations

from dataclasses import dataclass

from .bitops import str_to_bits, bits_to_string
from .crc import calculate_crc8

HEADER_BYTE = 0xFF


@dataclass
class Frame:
    header: int
    length: int
    sequence: int
    payload: str
    crc: int

    @property
    def total_bits(self) -> int:
        return 8 + 8 + 8 + self.length * 8 + 8


def build_frame(payload: str, sequence: int, header: int = HEADER_BYTE) -> str:
    """Serialize an application payload into a bit string ready for modulation."""
    length = len(payload)
    header_bits = f"{header:08b}"
    length_bits = f"{length:08b}"
    sequence_bits = f"{sequence:08b}"
    payload_bits = str_to_bits(payload)

    frame_bytes = bytes([header, length, sequence]) + payload.encode("utf-8")
    crc_val = calculate_crc8(frame_bytes)
    crc_bits = f"{crc_val:08b}"

    return header_bits + length_bits + sequence_bits + payload_bits + crc_bits


class FrameParseError(Exception):
    pass


def parse_frame(bits: str) -> tuple[Frame, bool]:
    """
    Parse a received bit string into a Frame and report whether the
    CRC matched. Raises FrameParseError if the bit string is too short
    to even contain a valid header/length/sequence/CRC skeleton, or if
    the declared length would run past the end of the buffer.
    """
    if len(bits) < 32:
        raise FrameParseError("bit stream shorter than minimum frame size (32 bits)")

    header = int(bits[0:8], 2)
    length = int(bits[8:16], 2)
    sequence = int(bits[16:24], 2)

    payload_start = 24
    payload_end = payload_start + length * 8
    crc_end = payload_end + 8

    if crc_end > len(bits):
        raise FrameParseError("declared LENGTH exceeds available bits (corrupted length field)")

    payload_bits = bits[payload_start:payload_end]
    crc_bits = bits[payload_end:crc_end]

    payload_str = bits_to_string(payload_bits)
    rx_crc = int(crc_bits, 2)

    frame_bytes = bytes([header, length, sequence]) + payload_str.encode("utf-8", errors="replace")
    calculated_crc = calculate_crc8(frame_bytes)

    frame = Frame(header=header, length=length, sequence=sequence, payload=payload_str, crc=rx_crc)
    return frame, calculated_crc == rx_crc
