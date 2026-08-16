"""
run_demo.py
-----------
Interactive single-frame demo: type a payload, watch it get framed,
modulated, optionally corrupted by a noisy channel, and recovered
(or rejected) on the receive side. This is the direct descendant of
the original V0.1-V0.3 script, refactored on top of src/.

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --p-error 0.02
    python scripts/run_demo.py --channel awgn --eb-n0-db 4
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.framing import build_frame, parse_frame, FrameParseError
from src.modem import modulate, demodulate, flip_channel, awgn_channel


def main():
    parser = argparse.ArgumentParser(description="Single-frame transmit/receive demo")
    parser.add_argument("--payload", type=str, default=None, help="payload text (prompts if omitted)")
    parser.add_argument("--sequence", type=int, default=0)
    parser.add_argument("--channel", choices=["flip", "awgn", "none"], default="none")
    parser.add_argument("--p-error", type=float, default=0.01, help="bit-flip probability for --channel flip")
    parser.add_argument("--eb-n0-db", type=float, default=6.0, help="Eb/N0 in dB for --channel awgn")
    args = parser.parse_args()

    payload = args.payload if args.payload is not None else input("Input your payload data: ")

    # --- Transmitter ---
    tx_bits = build_frame(payload, args.sequence)
    symbols = modulate(tx_bits)
    print(f"\n[TX] frame length: {len(tx_bits)} bits ({len(tx_bits)//8} bytes)")

    # --- Channel ---
    if args.channel == "flip":
        symbols = flip_channel(symbols, args.p_error)
        print(f"[CH] flip channel, p_error={args.p_error}")
    elif args.channel == "awgn":
        symbols = awgn_channel(symbols, args.eb_n0_db)
        print(f"[CH] AWGN channel, Eb/N0={args.eb_n0_db} dB")
    else:
        print("[CH] ideal channel (no noise)")

    # --- Receiver ---
    rx_bits = demodulate(symbols)
    try:
        frame, crc_ok = parse_frame(rx_bits)
        if crc_ok:
            print("[RX] CRC verified successfully!")
            print("[RX] Recovered string:", repr(frame.payload))
        else:
            print("[RX] CRC error: packet corrupted!")
            print("[RX] Best-effort decode:", repr(frame.payload))
    except FrameParseError as e:
        print(f"[RX] Frame parse failed: {e}")


if __name__ == "__main__":
    main()
