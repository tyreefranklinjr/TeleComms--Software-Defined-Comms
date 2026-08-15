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

# --- TRANSMITTER PIPELINE ---
payload = "Hello World, my name is Tyree!"
header = 255
length = len(payload)
sequence = 0

header_bits = f"{header:08b}"
length_bits = f"{length:08b}"
sequence_bits = f"{sequence:08b}"
payload_bits = str_to_bits(payload)

file_content_bits = header_bits + length_bits + sequence_bits + payload_bits

frame_bytes = bytes([header, length, sequence]) + payload.encode('utf-8')
crc_val = calculate_crc8(frame_bytes)
crc_bits = f"{crc_val:08b}"

modulated_file = modulate(file_content_bits + crc_bits)

# Receiver pipline
received_bits = demodulate(modulated_file)

rx_header = int(received_bits[0:8], 2)
rx_length = int(received_bits[8:16], 2)
rx_sequence = int(received_bits[16:24], 2)

payload_start = 24
payload_end = 24 + (rx_length * 8)
rx_payload_bits = received_bits[payload_start:payload_end]
rx_crc_bits = received_bits[payload_end:payload_end+8]

rx_payload_str = bits_to_string(rx_payload_bits)
rx_frame_bytes = bytes([rx_header, rx_length, rx_sequence]) + rx_payload_str.encode('utf-8')
calculated_rx_crc = calculate_crc8(rx_frame_bytes)

if f"{calculated_rx_crc:08b}" == rx_crc_bits:
    print("CRC Verified Successfully!")
    print("Recovered String:", rx_payload_str)
else:
    print("CRC Error: Packet corrupted!")