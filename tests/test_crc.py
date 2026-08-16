import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.crc import calculate_crc8, verify_crc8

def test_deterministic():
    data = b"hello world"
    assert calculate_crc8(data) == calculate_crc8(data)

def test_verify_true():
    data = b"frame payload"
    crc = calculate_crc8(data)
    assert verify_crc8(data, crc) is True

def test_verify_false_on_corruption():
    data = b"frame payload"
    crc = calculate_crc8(data)
    corrupted = b"frame payloae"
    assert verify_crc8(corrupted, crc) is False

def test_sensitivity_single_bit_flip():
    data = bytearray(b"sensitive")
    crc1 = calculate_crc8(bytes(data))
    data[0] ^= 0x01
    crc2 = calculate_crc8(bytes(data))
    assert crc1 != crc2
