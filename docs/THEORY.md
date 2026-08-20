# Theory & Statistical Models

This is the math behind the figures: what I expected going in, and what
the simulation actually gave back.

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

I ran 4000 frames at each of 11 values of `p` from 0 to 0.05 and compared
the fraction of bits that actually flipped. It matched almost exactly
(p=0.03 in, BER=0.03005 out, off by fifth-decimal noise). That's expected
with a few thousand trials per point, but it's still worth checking: if the
modem or the RNG wiring were broken, this is exactly where it'd show up.

### 1.2 AWGN + BPSK, the model that actually looks like a radio link

`awgn_channel` adds Gaussian noise to the ±1 symbols at a given **Eb/N0**
(energy per bit over noise spectral density, in dB), then a hard-decision
receiver just checks the sign. This is the standard model for coherent
BPSK over an additive-noise channel, the one you'd actually find in a
communications textbook or a link budget spreadsheet.

```
BER_theoretical(Eb/N0) = Q(√(2·Eb/N0)) = 0.5 · erfc(√(Eb/N0))
```

implemented in `modem.theoretical_ber_awgn`. Sweeping Eb/N0 from -2 dB to
10 dB and comparing empirical vs. theoretical gives the classic waterfall
shape: BER dropping roughly an order of magnitude every couple of dB.
At 10 dB the empirical BER is estimated from a literal handful of bit
errors out of ~900,000 simulated bits, so the last couple of points are
noisier than they look (small-sample effects, not a bug).

**Why bother with both.** `flip` is convenient, you dial in the bit error
rate directly, which is nice for controlled experiments. `awgn` is closer
to how a real link is actually specified: nobody hands you a target BER,
they hand you an SNR or Eb/N0 and you work out what that implies. Having
both means the same pipeline can be exercised either way.

## 2. Frame Error Rate

A frame of `N` bits only survives if none of its `N` bits flip. Under the
independent-error assumption of the BSC:

```
FER_theoretical = 1 - (1 - p)^N
```

For a ~224-bit frame (short payload, standard header), this gets ugly
fast. A 1% per-bit error rate already pushes frame error rate close to
90%. That's not a fluke of my numbers, it's just what happens when you
multiply a lot of "mostly fine" probabilities together. Two things fall
out of this directly:

- Frame size matters a lot. Doubling the payload roughly doubles the
  exponent, and the FER curve gets steeper, not just shifted.
- Detection-only protocols (what this version is) don't fix anything,
  they just tell you the frame failed. Actually recovering from a failed
  frame is V0.4/V0.5 territory (see the roadmap).

## 3. How good is an 8-bit CRC, really

CRC-8 (poly `0x07`) can't catch every possible corruption. It has 256
possible output values, so for genuinely random, independent bit errors
the odds a corrupted frame still produces the "right" CRC by accident are
roughly:

```
P(undetected error | frame corrupted) ≈ 2^-8 ≈ 1/256 ≈ 0.39%
```

This is an approximation, not an exact result. Real CRC polynomials have
structure that makes them better or worse at specific error patterns
(especially burst errors, which is what CRCs are actually designed to
catch well). Random independent bit flips are close to the worst case for
a CRC's "designed" strengths, so treating this number as a rough
upper-bound estimate is fair. My empirical numbers bounced between about
0.27% and 0.48% across the sweep, sitting close to the 1/256 line without
being pinned to it, which is what you'd expect measuring a rare event
over a few thousand trials.

The number that matters here isn't the plot, it's the takeaway: even after
CRC passes, there's a small but nonzero chance the frame you accepted is
wrong. That residual risk is exactly what forward error correction and
retransmission exist to close.

## 4. Why simulate instead of just trusting the formulas

Closed-form BER/FER/CRC numbers all assume clean, independent bit errors.
Real channels don't cooperate: fading, burst errors, interference,
hardware quirks. Running the Monte Carlo harness through the *exact* same
`pipeline.run_trial` code path the interactive demo uses means two things:

1. If there's a bug anywhere in the framing, CRC, or modem code, it shows
   up as the empirical curve drifting off the theoretical one, so the theory
   check doubles as a regression test.
2. Swapping in a more realistic channel later (fading, bursts, whatever
   V0.6 ends up being) doesn't require touching how results get collected
   or plotted, just the channel function itself.

## 5. Pulse shaping (V0.4): does band-limiting cost anything

Up to this point, BPSK symbols were treated as instantaneous ±1 values,
one sample per symbol. Real transmitters can't do that: a signal that
jumps instantly between two levels has infinite bandwidth, which no
antenna or channel actually supports. `modulate_bpsk_rrc` fixes this by
upsampling each symbol and convolving it with a root-raised-cosine (RRC)
filter, producing a smooth, band-limited waveform instead of a sequence
of instant jumps.

### 5.1 Why root-raised-cosine specifically

An RRC filter is built so that when the *same* filter is applied a second
time on receive (the matched filter), the cascade of the two forms a
raised-cosine pulse: a waveform that is exactly zero at every symbol
period except its own center. That property, zero inter-symbol
interference (ISI) at the correct sampling instant, is the entire point.
Splitting the raised-cosine response evenly between transmitter and
receiver (hence "root" raised-cosine, each half is the square root of
the full response in the frequency domain) also means each side of the
link only needs half the filtering, and the receive-side matched filter
gives the best possible noise rejection for that pulse shape.

`rrcosfilter(num_taps, alpha, sps)` builds that impulse response directly
from the standard closed-form RRC equation. `alpha` (the rolloff factor,
0 to 1) trades bandwidth for how gently the filter's frequency response
rolls off:

```
figures/rrc_filter_shapes.png       -- time domain, alpha = 0.0 .. 1.0
figures/rrc_frequency_response.png  -- same sweep, frequency domain
```

Low alpha (0.0) is the narrowest possible bandwidth (matches the ideal
sinc/Nyquist filter) but rings for a long time in the time domain, wide
side-lobes that take many symbol periods to die out. High alpha (1.0)
occupies close to double the bandwidth but decays fast and cleanly. 0.35,
the default used everywhere else in this repo, is a standard middle
ground used in a lot of real systems for exactly that reason.

### 5.2 Eye diagram: what "no ISI at the sampling instant" looks like

`figures/eye_diagram.png` overlays many two-symbol-period windows of the
shaped waveform on top of each other. This is the transmit-side waveform
only, one RRC filter, not the matched pair, so the eye is partially
closed by design: a single RRC stage still has ISI on its own, that's
expected and correct, not a bug. The eye only fully opens once the
receive-side matched filter is added back in (section 5.3), which is
exactly the mechanism the BER sweep exercises.

### 5.3 Matched filtering: proving pulse shaping doesn't cost BER

The real question pulse shaping raises: does band-limiting the waveform
make the link worse? Matched-filter theory says no, a transmit RRC
paired with an identical receive RRC should reproduce the *same* BER as
the ideal, unshaped model, because the matched filter recombines all the
signal energy the pulse spread out across multiple samples while only
passing through as much noise as an unshaped one-sample-per-symbol system
would.

`analysis/pulse_shaping_analysis.py` checks this directly instead of
assuming it. Each trial: bits -> BPSK symbols -> `modulate_bpsk_rrc`
(transmit shaping) -> AWGN added on the oversampled waveform -> a second
RRC convolution acting as the receive-side matched filter -> downsample
at the correct symbol centers (accounting for the combined group delay
of both filters) -> hard decision. Run 100 times per Eb/N0 point, 2000
random bits per trial, 200,000 bits per point:

```
figures/ber_rrc_matched_filter.png
```

The result tracks the closed-form `Q(√(2·Eb/N0))` curve closely across
the full 0-10 dB sweep, which is the expected outcome and a real check
that the transmit/receive filter pair and the symbol-timing math are
correct, not just that the code runs without crashing.

**Where it doesn't line up exactly, and why that's honest, not a bug.**
At the high end of the sweep (8-10 dB) the empirical BER runs
consistently a little above theory, for example about 6e-5 measured
against a theoretical 5e-6 at 10 dB. This isn't noise in the estimate,
it's a real, explainable cost: `rrcosfilter` uses a finite number of taps
(33 by default) to approximate a filter whose ideal impulse response is
infinitely long. Truncating it clips off a small amount of pulse energy,
which costs a small, consistent amount of SNR, more taps would close that
gap further, at the cost of more compute per sample. Reporting that gap
instead of picking parameters that hide it is the same standard the rest
of this repo holds itself to (see section 1.2 for the same kind of
small-sample honesty on the unshaped AWGN sweep).
