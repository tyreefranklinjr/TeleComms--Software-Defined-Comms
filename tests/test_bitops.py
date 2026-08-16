import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.bitops import str_to_bits, bits_to_string, hamming_distance

def test_roundtrip():
    s = "Hello, World! 123"
    assert bits_to_string(str_to_bits(s)) == s

def test_empty():
    assert str_to_bits("") == ""
    assert bits_to_string("") == ""

def test_hamming_distance():
    assert hamming_distance("0000", "0000") == 0
    assert hamming_distance("0000", "1111") == 4
    assert hamming_distance("1010", "1001") == 2
