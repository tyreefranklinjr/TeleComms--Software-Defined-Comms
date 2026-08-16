# Roadmap

I'm building this as small versions that each actually work, rather than
disappearing for a few months and coming back with something enormous.
Every version below is something you could clone and run on its own.

| Version | Scope | New ideas introduced |
|---|---|---|
| **V0.1** | Generate bits, modulate/demodulate, recover, sanity check | bit-level encoding, plain Python |
| **V0.2** | Real frame structure: header, payload, length, sequence, CRC | bit manipulation, checksums, framing |
| **V0.3** | Controlled channel noise, measured failure rates | basic probability, BSC model |
| **V0.3.5** *(here)* | Refactored into layers, AWGN channel + closed-form BER added, Monte Carlo harness, full test suite | statistical validation, layered design, reproducibility |
| **V0.4** *(next)* | Forward error correction, probably Hamming(7,4) or something small | coding theory, coding gain vs. Eb/N0 |
| **V0.5** | ARQ, retry on CRC failure, starting with Stop-and-Wait, maybe Go-Back-N after | sliding windows, retry/timeout logic, throughput cost |
| **V0.6** | Multi-frame streams with bursty errors (Gilbert-Elliott model) | correlated errors vs. the i.i.d. assumption everything above relies on |
| **V0.7** | Basic contention, slotted ALOHA or CSMA | MAC-layer collisions, access probability |
| **V1.0** | Throughput/latency benchmarks across every channel model and coding scheme built so far | system-level performance comparison |

## Why this order, specifically

Each step adds exactly one new piece of complexity on top of something
that already works:

1. **V0.1 to V0.2** get correctness right with *no* noise at all. You
   can't reason sensibly about error rates until the clean path is trustworthy.
2. **V0.3** adds probability to a system that's already known-correct, so
   any error you measure can be attributed to the channel, not a bug.
3. **V0.3.5** treats the V0.3 numbers as a claim worth checking: run the
   Monte Carlo, compare against the closed-form math, and restructure the
   code so future versions are additions, not rewrites.
4. **V0.4 (FEC)** comes directly out of what the frame-error-rate and
   heatmap figures show in this version: detection alone falls apart fast
   under realistic error rates. That's not a hypothetical, it's what the
   data says.
5. **V0.5 (ARQ)** is the other half of the answer: instead of (or in
   addition to) correcting errors, just ask for the frame again.
6. **V0.6 to V0.7** move the error model and the access model closer to how
   actual wireless channels and shared-medium systems behave, since real
   traffic isn't independent bit flips and real channels aren't
   collision-free.
