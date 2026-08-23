# Theory & Statistical Models

This is the math behind the figures: what I expected going in, and what
the simulation actually gave back. Every section follows the same
structure on purpose: state the theoretical prediction, describe exactly
how it was measured (trial count, bits per trial, seed), then report the
actual numbers, agreement and disagreement both, because a validation
that only reports agreement isn't a validation.

## 1. Two channel models, two ways of thinking about noise

### 1.1 Binary Symmetric Channel (the `flip` model)

`flip_channel` independently negates each transmitted symbol with
probability `p`. That's a textbook Binary Symmetric Channel: a 0 arrives
as a 1 with probability `p`, a 1 arrives as a 0 with probability `p`,
independent across bits. Nothing fancy, and that's the point. It's the
simplest channel you can write down, and the theoretical BER falls right
out of the definition:

```
BER_theoretical = p
```

**Evidence.** 4000 frames simulated at each of 11 values of `p` from 0
to 0.05 (`results/flip_channel_sweep.csv`), fraction of bits actually
flipped compared against `p` directly:

| p (in) | BER (measured) | agreement |
|---|---|---|
| 0.01 | 0.00994 | within 0.6% |
| 0.03 | 0.03005 | within 0.2% |
| 0.05 | 0.05009 | within 0.2% |

That's expected with a few thousand trials per point, but it's still
worth checking: if the modem or the RNG wiring were broken, this is
exactly where it'd show up.

### 1.2 AWGN + BPSK, the model that actually looks like a radio link

`awgn_channel` adds Gaussian noise to the ±1 symbols at a given **Eb/N0**
(energy per bit over noise spectral density, in dB), then a hard-decision
receiver just checks the sign. This is the standard model for coherent
BPSK over an additive-noise channel.

```
BER_theoretical(Eb/N0) = Q(√(2·Eb/N0)) = 0.5 · erfc(√(Eb/N0))
```

implemented in `modem.theoretical_ber_awgn`.

**Evidence.** Swept -2 dB to 10 dB (`results/awgn_channel_sweep.csv`),
compared empirical vs. theoretical:

| Eb/N0 | measured BER | theoretical BER |
|---|---|---|
| 0 dB | 0.0790 | 0.0786 |
| 4 dB | 0.01247 | 0.01250 |
| 8 dB | 0.000186 | 0.000191 |
| 10 dB | 0.0000054 | 0.0000039 |

The 10 dB point is estimated from a literal handful of bit errors out of
~900,000 simulated bits, small-sample noise, not a modeling error, and
called out here rather than left for someone else to notice.

**Why bother with both channel models.** `flip` is convenient, you dial
in the bit error rate directly. `awgn` is closer to how a real link is
actually specified: nobody hands you a target BER, they hand you an SNR
or Eb/N0. Having both means the same pipeline can be exercised either
way, and the FEC coding-gain sweep in section 7 depends specifically on
the AWGN model being trustworthy.

## 2. Frame Error Rate

A frame of `N` bits only survives if none of its `N` bits flip:

```
FER_theoretical = 1 - (1 - p)^N
```

**Evidence.** For a ~224-bit frame, measured against the theoretical
curve across the same `p` sweep as section 1.1: at `p=0.005`, FER≈0.90;
at `p=0.01`, FER≈0.99; at `p=0.02`, FER≈1.00 (`figures/frame_error_rate.png`,
underlying data in `results/flip_channel_sweep.csv`). A 1% per-bit error
rate pushes frame error rate above 90%, purely from multiplying "mostly
fine" probabilities together at frame scale, which is the concrete
motivation behind adding FEC in section 7.

## 3. How good is an 8-bit CRC, really

CRC-8 (poly `0x07`) has 256 possible output values, so for genuinely
random, independent bit errors the odds a corrupted frame still produces
the "right" CRC by accident are roughly:

```
P(undetected error | frame corrupted) ≈ 2^-8 ≈ 1/256 ≈ 0.39%
```

This is an approximation, not exact, real CRC polynomials have structure
that changes the odds for specific error patterns, especially burst
errors (what CRCs are actually designed against). Random independent
flips are close to the worst case for a CRC's designed strengths, so
treating 1/256 as a rough upper bound is fair.

**Evidence.** Measured across the same flip-channel sweep
(`figures/crc_miss_detection.png`, `results/flip_channel_sweep.csv`):
empirical undetected-error rate bounced between about 0.27% and 0.48%
across the `p` sweep, straddling the 1/256≈0.39% line without being
pinned to it, consistent with measuring a rare event over a few thousand
trials per point.

## 4. Why simulate instead of just trusting the formulas

Closed-form BER/FER/CRC numbers all assume clean, independent bit
errors. Real channels don't cooperate. Running every Monte Carlo harness
through the exact code path the interactive demo uses (`pipeline.run_trial`
for framing/CRC/channel, the actual `src/modem.py` and `src/fec.py`
functions for pulse shaping, QPSK, and coding) means two things:

1. A bug anywhere in that code shows up as the empirical curve drifting
   off the theoretical one. The validation doubles as a regression test.
2. Swapping in a more realistic model later doesn't require touching how
   results get collected or plotted, just the model function itself.

## 5. Pulse shaping (V0.4): does band-limiting cost anything

`modulate_bpsk_rrc` upsamples each BPSK symbol and convolves it with a
root-raised-cosine (RRC) filter, producing a band-limited waveform
instead of instantaneous jumps between ±1.

### 5.1 Why root-raised-cosine specifically

An RRC filter is built so that pairing it with an identical filter on
receive (the matched filter) forms a raised-cosine pulse: exactly zero
at every symbol period except its own center, zero inter-symbol
interference (ISI) at the correct sampling instant.

**Evidence.** `rrcosfilter(num_taps, alpha, sps)` swept across
`alpha ∈ {0.0, 0.2, 0.35, 0.5, 1.0}` (`figures/rrc_filter_shapes.png`,
`figures/rrc_frequency_response.png`, raw coefficients in
`results/rrc_filter_shapes.csv` and `results/rrc_frequency_response.csv`).
Low alpha keeps bandwidth narrowest but rings longest in time; high alpha
occupies close to double the bandwidth but decays fast. 0.35, used
everywhere else in this repo, is the standard middle ground.

### 5.2 Eye diagram: what "no ISI" looks like, and what it doesn't yet

`figures/eye_diagram.png` (raw samples in `results/eye_diagram_traces.csv`,
360 overlaid two-symbol traces) shows the transmit-side waveform only,
one RRC stage, not the matched pair, so the eye is partially closed by
design. That's expected, a single RRC stage still has ISI on its own.
The eye only fully opens once the receive-side matched filter is added
(section 5.3).

### 5.3 Matched filtering: proving pulse shaping doesn't cost BER

**Evidence.** `analysis/pulse_shaping_analysis.py`: bits → BPSK → RRC
transmit shaping → AWGN on the oversampled waveform → RRC matched filter
→ symbol-center downsampling → hard decision. 100 trials per Eb/N0
point, 2000 bits per trial, 200,000 bits per point
(`results/pulse_shaping_ber_sweep.csv`):

| Eb/N0 | measured BER | theoretical BER |
|---|---|---|
| 0 dB | 0.0787 | 0.0786 |
| 4 dB | 0.0130 | 0.0125 |
| 7 dB | 0.00091 | 0.00019 |
| 10 dB | 0.000065 | 0.0000049 |

**The gap at high Eb/N0 is real, not noise in the estimate.** `rrcosfilter`
uses 33 taps to approximate a filter whose ideal impulse response is
infinite. Truncation clips a small amount of pulse energy, costing a
small, consistent amount of SNR, worse at high Eb/N0 where the noise
floor is low enough for that fixed cost to matter proportionally more.
More taps would close the gap at the cost of more compute per sample.
Reporting it instead of picking parameters that hide it matches the
standard the rest of this repo holds itself to.

## 6. QPSK vs. BPSK: same BER, half the bandwidth

`modulate_qpsk` maps 2-bit pairs to one of four constellation points
using Gray coding: `00, 01, 11, 10` assigned so every pair of *adjacent*
quadrants differs in exactly one bit. Under noise, the most likely
mistake is landing in a neighboring quadrant, not the opposite one, and
Gray coding makes that most-likely mistake cost exactly one bit.

```
BER_theoretical_QPSK(Eb/N0) = BER_theoretical_BPSK(Eb/N0) = Q(√(2·Eb/N0))
```

**Making the comparison fair.** `awgn_channel_complex(symbols, eb_n0_db,
bits_per_symbol)` scales per-dimension noise variance as
`1/(2·bits_per_symbol·Eb/N0_linear)`, which collapses to the exact same
formula the original real-valued `awgn_channel` uses at
`bits_per_symbol=1` (checked directly in `tests/test_qpsk.py`), so BPSK
and QPSK are compared at genuinely equal energy-per-bit, not just an
equal label.

**Evidence.** `analysis/qpsk_vs_bpsk_analysis.py`: 100 trials per Eb/N0
point, 2000 bits per trial, 0-10 dB, both schemes
(`results/bpsk_vs_qpsk_sweep.csv`):

| Eb/N0 | BPSK measured | QPSK measured | theory |
|---|---|---|---|
| 0 dB | 0.07961 | 0.08002 | 0.07865 |
| 4 dB | 0.01249 | 0.01297 | 0.01250 |
| 8 dB | 0.00018 | 0.00024 | 0.00019 |

Both curves land on the same theoretical line, no systematic gap between
BPSK and QPSK the way there was for the truncated RRC filter in 5.3,
confirming the Gray-coding argument empirically rather than leaving it
asserted. `figures/qpsk_constellation.png` shows 500 symbols at 8 dB,
four visibly separated noise clouds around the ideal points, a visual
check that the constellation mapping and quadrant decision boundaries
are wired correctly, independent of the BER numbers.

**What QPSK actually buys you.** Not free performance, the BER is
identical. QPSK carries 2 bits/symbol instead of 1, so for a fixed bit
rate it needs half the symbol rate, roughly half the bandwidth, at the
same energy efficiency. That's the real tradeoff, and why higher-order
schemes exist at all: trading a widening BER penalty for progressively
less bandwidth per bit.

## 7. Convolutional coding (V0.6): does FEC actually earn its complexity

Up to this point, error handling in this repo has been detect-only (CRC:
know a frame failed, discard it). V0.6 adds rate-1/2, K=7 convolutional
coding, the standard (133, 171) octal generator pair used in real
systems (802.11, GPS, deep-space links), with two decoders: hard-decision
Viterbi (works on already-sliced bits) and soft-decision Viterbi (works
directly on the raw channel output, keeping the "how confident was this
bit" information a hard slicer throws away).

### 7.1 Verifying the trellis is actually self-consistent

Before trusting any BER numbers, the encoder's shift-register update and
the decoder's trellis construction have to define the *same* state
machine, or the decoder is solving the wrong problem. Encoder:
`register' = (bit<<5) | (register>>1)`. Decoder's `next_state`:
`(state>>1) | (bit<<5)`. Same formula. `tests/test_fec.py::
test_hard_roundtrip_various_lengths` and `test_soft_roundtrip_no_noise`
confirm this empirically: encode → decode with zero channel noise
recovers the exact original bits at every length tested (`"0"`, `"1"`,
`"1010"`, `"111111"`, `"0101010101010101"`).

### 7.2 Verifying it actually corrects errors, not just round-trips clean data

A round-trip with no noise proves the trellis is self-consistent, it
doesn't prove the decoder can recover from a bad channel, which is the
entire point of FEC. `tests/test_fec.py::
test_hard_decode_corrects_scattered_bit_errors` encodes a 24-bit message
(58 coded bits), flips 4 scattered bits at random positions, and
confirms exact recovery. `test_soft_decode_survives_light_noise` runs
the same message through actual AWGN at 4 dB and confirms the same.

### 7.3 The Viterbi mechanism itself, not just its output

`figures/viterbi_trellis_demo.png` uses a small illustrative 4-state
code (K=3, the real K=7 code is 64 states and not usefully plottable in
one figure, same generator-tap mechanism at smaller scale) to show the
actual winning survivor path a decoder traces back through, for a
message with one deliberately induced bit error, correctly recovered.
This is the mechanism (path metrics accumulated at every state, best
predecessor recorded at every step, traceback from the final state)
underneath every BER number in this section, not a separate demo.

### 7.4 Coding gain: the number that justifies adding this complexity

**Evidence.** `analysis/fec_viterbi_demo.py`: 30 Monte Carlo trials per
Eb/N0 point, 200 info bits per trial, both decoders, against the
closed-form uncoded curve (`results/coding_gain_sweep.csv`):

| Eb/N0 | uncoded (theory) | hard-decision coded | soft-decision coded |
|---|---|---|---|
| 0 dB | 0.07865 | 0.34350 | 0.13233 |
| 1 dB | 0.05628 | 0.19233 | 0.02717 |
| 2 dB | 0.03751 | 0.10167 | 0.00833 |
| 3 dB | 0.02288 | 0.03100 | 0.00050 |
| 4 dB | 0.01250 | 0.00167 | 0.00000 (0/6000 bit errors) |
| 5 dB | 0.00595 | 0.00217 | 0.00000 (0/6000 bit errors) |
| 6 dB | 0.00239 | 0.00000 | 0.00000 (0/6000 bit errors) |

Two things this table shows plainly, including the part that doesn't
flatter the code:

**Below about 2-3 dB, coding is measurably worse than uncoded.** At 0 dB,
hard-decision coded BER (0.344) is over 4x *worse* than uncoded (0.079).
This is real and expected, not a bug: a rate-1/2 code spends half its
transmitted symbols on redundancy rather than new information, so at
fixed total transmit energy per info bit, each *coded symbol* carries
half the energy an uncoded symbol would (`coded_ec_n0_db = eb_n0_db +
10·log10(0.5)`, a 3.01 dB penalty applied before the AWGN channel call in
`analysis/fec_viterbi_demo.py`). Below the code's effective working
region, that energy penalty costs more than the error-correction gains
back.

**Above the crossover point, the code wins decisively.** By 3 dB,
soft-decision coded BER (0.00050) is already ~46x better than uncoded
(0.02288). By 4 dB, soft-decision measures zero errors across 6000
simulated bits, consistent with a BER below roughly 1.7×10⁻⁴ at that
sample size (can't claim a tighter bound than "no errors observed in
this many trials" without more bits, which is itself an honest
limitation of a 30-trial sweep, more trials would sharpen this number).

**Soft decision consistently and substantially outperforms hard
decision** at every measured point, exactly as coding theory predicts
(hard decision throws away amplitude/confidence information before
decoding; soft decision doesn't), quantified directly instead of taken
on faith: at 2 dB, soft measures 12x fewer errors than hard (0.00833 vs.
0.10167) at the identical channel realization budget.

**Why report the crossover instead of only showing the flattering part
of the curve.** A plot that starts at 4 dB would show FEC looking
strictly better and nothing else, a shorter, more instagram-friendly
answer. It would also hide a genuinely important system-design fact:
convolutional coding isn't a free win at any SNR, it has a working
region, and knowing where the crossover sits (here, roughly 2-3 dB for
this code and this Eb/N0 convention) is exactly the kind of number an
actual link-budget decision needs. This is the same reporting standard
sections 1.2, 5.3, and 6.3 already hold themselves to.