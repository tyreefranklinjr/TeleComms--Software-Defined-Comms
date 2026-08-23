"""
fec.py
------
Rate-1/2, K=7 convolutional forward error correction: the standard
(133, 171) octal generator pair used all over real wireless systems
(this exact code shows up in 802.11, GPS, and voyager-era deep space
links). Encoder is a straightforward shift-register/XOR implementation.
Two decoders are provided:

  * ViterbiDecoder      -- hard-decision: takes a demodulated bit string
                            (post hard-decision), Hamming distance as the
                            branch metric.
  * SoftViterbiDecoder  -- soft-decision: takes the raw bipolar (+/-1)
                            channel output directly, squared Euclidean
                            distance as the branch metric. Skipping the
                            hard-decision step before decoding is exactly
                            what gives soft decoding its ~2 dB advantage
                            over hard decoding at the same Eb/N0, since
                            it keeps the "how confident was this bit"
                            information the hard slicer throws away.

Both decoders build the same 64-state trellis the encoder's shift
register defines, so encode -> decode round-trips exactly with no
channel noise, and the tests check exactly that.
"""

import numpy as np


class ConvolutionalEncoder:
    def __init__(self):
        self.g1 = 0b1011011  # 133 octal
        self.g2 = 0b1111001  # 171 octal
        self.register = 0

    def encode_bit(self, bit: int) -> tuple[int, int]:
        current_window = (bit << 6) | self.register
        out1 = bin(current_window & self.g1).count('1') % 2
        out2 = bin(current_window & self.g2).count('1') % 2
        self.register = ((bit << 5) | (self.register >> 1)) & 0x3F
        return out1, out2

    def encode_stream(self, bits: str) -> str:
        self.register = 0
        encoded_bits = []
        padded_bits = bits + "000000"  # flush tail

        for char in padded_bits:
            b = int(char)
            o1, o2 = self.encode_bit(b)
            encoded_bits.append(str(o1))
            encoded_bits.append(str(o2))

        return "".join(encoded_bits)


class ViterbiDecoder:
    def __init__(self, k: int = 7):
        self.k = k
        self.num_states = 2 ** (k - 1)  # 64 states for K=7
        self.g1 = 0b1011011
        self.g2 = 0b1111001

        # precomputed trellis lookup tables
        # next_state[state][input_bit] -> resulting_state
        # expected_output[state][input_bit] -> (out1, out2)
        self.next_state = np.zeros((self.num_states, 2), dtype=int)
        self.expected_output = np.zeros((self.num_states, 2, 2), dtype=int)

        self._build_trellis()

    def _build_trellis(self):
        for state in range(self.num_states):
            for bit in (0, 1):
                # shift register layout: lower (k-1) bits of state + input bit at top
                current_window = (bit << (self.k - 1)) | state

                out1 = bin(current_window & self.g1).count('1') % 2
                out2 = bin(current_window & self.g2).count('1') % 2

                # next state shifts out the oldest bit, shifts in the new one
                next_st = ((state >> 1) | (bit << (self.k - 2))) & (self.num_states - 1)

                self.next_state[state, bit] = next_st
                self.expected_output[state, bit] = [out1, out2]

    def decode(self, received_bits: str) -> str:
        """
        Decodes a hard-decision binary string using the Viterbi algorithm.
        """
        num_steps = len(received_bits) // 2
        pairs = []
        for i in range(0, len(received_bits), 2):
            pairs.append([int(received_bits[i]), int(received_bits[i + 1])])

        INF = 10 ** 9
        path_metrics = np.full(self.num_states, INF, dtype=float)
        path_metrics[0] = 0.0

        history = []

        for step, rx_pair in enumerate(pairs):
            new_path_metrics = np.full(self.num_states, INF, dtype=float)
            step_history = np.zeros((self.num_states, 2), dtype=int)

            for state in range(self.num_states):
                if path_metrics[state] == INF:
                    continue

                for bit in (0, 1):
                    nxt_st = self.next_state[state, bit]
                    expected = self.expected_output[state, bit]

                    metric_diff = np.sum(expected != rx_pair)
                    total_metric = path_metrics[state] + metric_diff

                    if total_metric < new_path_metrics[nxt_st]:
                        new_path_metrics[nxt_st] = total_metric
                        step_history[nxt_st] = [state, bit]

            path_metrics = new_path_metrics
            history.append(step_history)

        current_state = 0
        decoded_bits_rev = []

        for step in range(len(pairs) - 1, -1, -1):
            prev_state, input_bit = history[step][current_state]
            decoded_bits_rev.append(str(input_bit))
            current_state = prev_state

        decoded_bits_rev.reverse()

        return "".join(decoded_bits_rev[:-6])

    def decode_with_history(self, received_bits: str):
        """
        Same as decode(), but also returns the per-step history array and
        the winning survivor path (state sequence), for visualization.
        """
        num_steps = len(received_bits) // 2
        pairs = []
        for i in range(0, len(received_bits), 2):
            pairs.append([int(received_bits[i]), int(received_bits[i + 1])])

        INF = 10 ** 9
        path_metrics = np.full(self.num_states, INF, dtype=float)
        path_metrics[0] = 0.0

        history = []

        for step, rx_pair in enumerate(pairs):
            new_path_metrics = np.full(self.num_states, INF, dtype=float)
            step_history = np.zeros((self.num_states, 2), dtype=int)

            for state in range(self.num_states):
                if path_metrics[state] == INF:
                    continue

                for bit in (0, 1):
                    nxt_st = self.next_state[state, bit]
                    expected = self.expected_output[state, bit]

                    metric_diff = np.sum(expected != rx_pair)
                    total_metric = path_metrics[state] + metric_diff

                    if total_metric < new_path_metrics[nxt_st]:
                        new_path_metrics[nxt_st] = total_metric
                        step_history[nxt_st] = [state, bit]

            path_metrics = new_path_metrics
            history.append(step_history)

        current_state = 0
        decoded_bits_rev = []
        state_path_rev = [0]

        for step in range(len(pairs) - 1, -1, -1):
            prev_state, input_bit = history[step][current_state]
            decoded_bits_rev.append(str(input_bit))
            state_path_rev.append(prev_state)
            current_state = prev_state

        decoded_bits_rev.reverse()
        state_path = list(reversed(state_path_rev))  # states s0, s1, ..., sN

        decoded = "".join(decoded_bits_rev[:-6])
        return decoded, history, state_path


class SoftViterbiDecoder:
    def __init__(self, k: int = 7):
        self.k = k
        self.num_states = 2 ** (k - 1)  # 64 states for K=7
        self.g1 = 0b1011011
        self.g2 = 0b1111001

        self.next_state = np.zeros((self.num_states, 2), dtype=int)
        # expected outputs mapped to float coordinates (-1.0 and 1.0) for soft matching
        self.expected_output_float = np.zeros((self.num_states, 2, 2), dtype=float)

        self._build_trellis()

    def _build_trellis(self):
        for state in range(self.num_states):
            for bit in (0, 1):
                current_window = (bit << (self.k - 1)) | state

                out1 = bin(current_window & self.g1).count('1') % 2
                out2 = bin(current_window & self.g2).count('1') % 2

                next_st = ((state >> 1) | (bit << (self.k - 2))) & (self.num_states - 1)

                self.next_state[state, bit] = next_st
                self.expected_output_float[state, bit] = [
                    -1.0 if out1 == 0 else 1.0,
                    -1.0 if out2 == 0 else 1.0,
                ]

    def decode_soft(self, received_soft_symbols: np.ndarray) -> str:
        """
        Decodes a stream of soft-decision values (e.g., real floats from an
        AWGN channel) using squared Euclidean distance branch metrics.
        """
        num_steps = len(received_soft_symbols) // 2
        pairs = received_soft_symbols.reshape((num_steps, 2))

        INF = 10.0 ** 9
        path_metrics = np.full(self.num_states, INF, dtype=float)
        path_metrics[0] = 0.0

        history = []

        for step, rx_pair in enumerate(pairs):
            new_path_metrics = np.full(self.num_states, INF, dtype=float)
            step_history = np.zeros((self.num_states, 2), dtype=int)

            for state in range(self.num_states):
                if path_metrics[state] == INF:
                    continue

                for bit in (0, 1):
                    nxt_st = self.next_state[state, bit]
                    expected = self.expected_output_float[state, bit]

                    branch_metric = np.sum((expected - rx_pair) ** 2)
                    total_metric = path_metrics[state] + branch_metric

                    if total_metric < new_path_metrics[nxt_st]:
                        new_path_metrics[nxt_st] = total_metric
                        step_history[nxt_st] = [state, bit]

            path_metrics = new_path_metrics
            history.append(step_history)

        current_state = 0
        decoded_bits_rev = []

        for step in range(num_steps - 1, -1, -1):
            prev_state, input_bit = history[step][current_state]
            decoded_bits_rev.append(str(input_bit))
            current_state = prev_state

        decoded_bits_rev.reverse()

        return "".join(decoded_bits_rev[:-6])