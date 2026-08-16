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
