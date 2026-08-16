# Architecture

## Why it's split into layers

I split this along the same seams a real link stack uses: physical,
link, channel, mostly so I could test and reason about each piece on its
own without the whole thing being one tangled script. It also means
swapping a channel model or a modulation scheme later doesn't touch
anything else.

```
 ┌─────────────────────────────────────────────────────────────────┐
 │  Application layer                                               │
 │  scripts/run_demo.py, analysis/statistical_analysis.py           │
 └───────────────────────────┬─────────────────────────────────────┘
                              │  payload (str)
 ┌───────────────────────────▼─────────────────────────────────────┐
 │  Link layer: framing.py, crc.py                                  │
 │  build_frame()  : payload -> HEADER|LEN|SEQ|PAYLOAD|CRC bitstring│
 │  parse_frame()  : bitstring -> Frame + crc_ok                    │
 └───────────────────────────┬─────────────────────────────────────┘
                              │  bit string
 ┌───────────────────────────▼─────────────────────────────────────┐
 │  Physical layer: modem.py                                        │
 │  modulate()/demodulate()  : bits <-> BPSK symbols (±1.0)         │
 └───────────────────────────┬─────────────────────────────────────┘
                              │  symbol list
 ┌───────────────────────────▼─────────────────────────────────────┐
 │  Channel model: modem.py                                         │
 │  flip_channel()  : Binary Symmetric Channel, parameterized by p  │
 │  awgn_channel()  : Gaussian noise, parameterized by Eb/N0 (dB)   │
 └───────────────────────────┬─────────────────────────────────────┘
                              │  corrupted symbols
                              ▼
                (fed back through physical + link layer on receive)
```

`pipeline.run_trial()` glues all four layers into one transmit, channel,
receive call and hands back a `TrialResult` with both bit-level and
frame-level outcomes. Every script in the repo, the CLI demo and the
statistics, goes through this exact function, so there's one place that
defines what "a trial" means, instead of two slightly different
implementations drifting apart over time.

## Who does what

| Module | Job | Depends on |
|---|---|---|
| `bitops.py` | string <-> bit string <-> bytes | nothing, pure Python |
| `crc.py` | CRC-8 compute/verify | nothing |
| `modem.py` | BPSK modulation, both channel models, closed-form BER | `math`, `random` |
| `framing.py` | frame build/parse, wires CRC into the frame | `bitops`, `crc` |
| `pipeline.py` | end-to-end trial, scoring | `framing`, `modem` |
| `scripts/run_demo.py` | interactive CLI | `src/*` |
| `analysis/statistical_analysis.py` | Monte Carlo sweeps, plots, CSVs | `src/*`, matplotlib, numpy |

## A few decisions I made on purpose

- **The core has zero dependencies.** `bitops`, `crc`, and the frame
  format are plain Python, no NumPy needed to unit-test the parts that
  matter most for correctness. Numerical libraries only show up in the
  statistics layer, kept at the edges where they belong.
- **One interface, two channels.** `run_trial(channel="flip"|"awgn", ...)`
  means the same pipeline runs against an idealized BSC (fast, exact
  math) or a physically grounded AWGN model (maps to a real link budget)
  without any branching logic outside the modem module.
- **Randomness is seeded, on purpose.** Every sweep takes an explicit
  `random.Random` seeded once (`RNG_SEED = 42`) so the numbers in this
  repo are reproducible, rerun the script, get the same CSVs.
- **CRC coverage matches the wire exactly.** It's computed over
  `HEADER || LENGTH || SEQUENCE || PAYLOAD`, the actual transmitted
  bytes, nothing more, nothing less. `tests/test_framing.py` checks this
  directly rather than trusting it by inspection.
