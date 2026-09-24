# Track 5 skewness prefix provenance

## Pre-registered control

- SD control matches expected: `True`.
- Skewness control matches expected: `True`.

| Replicates | Generated SD | Expected SD | Generated skewness | Expected skewness |
|---:|---:|---:|---:|---:|
| 200 | 0.0169715358 | 0.0169715358 | -0.139556 | -0.139556 |
| 500 | 0.0167711400 | 0.0167711400 | -0.103819 | -0.103819 |
| 1000 | 0.0162722914 | 0.0162722914 | +0.055349 | +0.055349 |
| 2000 | 0.0161860482 | 0.0161860482 | +0.036285 | +0.036285 |
| 3000 | 0.0159308502 | 0.0159308502 | +0.025623 | +0.025623 |
| 5000 | 0.0160786624 | 0.0160786624 | -0.008893 | -0.008893 |

## Mismatches

- None.

## Stream

- One shared `numpy.random.Generator` seeded with `20260919` is used for all 5000 outer replicates.
- Each outer replicate consumes A, B, then 32 inner `rng.multinomial(lengths, theta)` pairs.
- `lengths` is derived from A block slices and the latent `theta` arrays are captured by `TracingRNG`.
- The TV estimate calls `eibo.statcore.tv_upper_bound(a, b, alphabet_size=32, alpha=0.025)`.

Boundary: this is the modelled block law at this design only, never real traffic.

content_sha256: 9247bd693ce7f93e073107e56788dece81e4832be9af1e059bac74c31f562162
