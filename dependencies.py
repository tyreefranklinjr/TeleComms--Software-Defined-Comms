def str_to_bits(input: str):
    """
    Inputs a string then converts it to an
    8 bit binary string and returns the 
    entire phrase into a binary string
    """
    x = ""
    for char in input:
        x += f"{ord(char):08b}"
    return x

def modulate(input: str):
    """
    Grabs a binary string and converts it to relevant
    float value that is corresponding to its proper
    modulated value
    """
    x = []
    for bit in input:
        if bit == "0": x.append(-1.0)
        elif bit == "1": x.append(1.0)

    return x

def demodulate(input):
    """
    Grabs the modulated bit float types and converts 
    them back to a structured binary 8 bit string
    """
    bits = ""
    for x in input:
        if x == -1.0: bits += "0"
        elif x == 1.0: bits += "1"

    return bits

def bits_to_string(input: str):
    """
    Iterates through the 8 bit string and converts
    them back into character's, individually building
    the original input string
    """
    if not input: return ""
    x = ""

    for i in range(0, len(input), 8):
        byte = input[i:i+8]
        if len(byte) == 8:
            x += chr(int(byte, 2))

    return x

def calculate_crc8(data: bytes) -> int:
    """
    Computes an 8-bit CRC checksum for the given byte data 
    using the generator polynomial 0x07.
    """
    crc = 0x00
    polynomial = 0x07
    
    for byte in data:
        crc ^= byte
        
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ polynomial) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
                
    return crc