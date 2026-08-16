import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.framing import build_frame, parse_frame, FrameParseError

def test_build_parse_roundtrip():
    bits = build_frame("test payload", sequence=5)
    frame, crc_ok = parse_frame(bits)
    assert crc_ok is True
    assert frame.payload == "test payload"
    assert frame.sequence == 5

def test_corruption_detected():
    bits = build_frame("integrity check", sequence=1)
    corrupted = bits[:40] + ("1" if bits[40] == "0" else "0") + bits[41:]
    frame, crc_ok = parse_frame(corrupted)
    assert crc_ok is False

def test_too_short_raises():
    try:
        parse_frame("0101")
        assert False, "expected FrameParseError"
    except FrameParseError:
        pass

def test_empty_payload():
    bits = build_frame("", sequence=0)
    frame, crc_ok = parse_frame(bits)
    assert crc_ok is True
    assert frame.payload == ""
