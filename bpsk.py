from dependencies import *
from packet_loss_simulation import *

# Transmitter piepline
payload = input("Input your payload data: ")

header = 255
sequence = 0
length = len(payload)
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
# modulated_file = introduce_noise(modulated_file, 0.01)
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