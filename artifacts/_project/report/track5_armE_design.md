# Track 5 Arm E design diagnostic

## Symmetric versus one-sided decision

**r_one_975 differs from r_sym beyond Monte Carlo error: YES.**
The observed difference is `-0.00463417` with paired-bootstrap Monte Carlo SE
`0.00293868` and 95% bootstrap interval
`[-0.01228333, -0.00079458]`. This is the primary gate for
whether a one-sided follow-up can address the symmetric-radius design.

## Design

| n | B | concentration | true TV | seed | outer draws |
|---:|---:|---:|---:|---:|---:|
| 60000 | 64 | 0.1 | 0.4 | 20260919 | 200 |

## Signed deviation and radii

`D = tv_hat - TRUE_TV`. The standard deviation below is the sample SD (`ddof=1`).
Skewness is the requested Fisher-Pearson standardized moment coefficient
`g1 = m3 / m2**1.5`, with `m2` and `m3` computed using `1/n` central moments.

| quantity | value |
|---|---:|
| mean(D) | 0.004256166667 |
| sd(D) | 0.015101771106 |
| skewness(D), g1 | -0.369630928675 |
| r_sym = quantile(abs(D), 0.975) | 0.030840416667 |
| r_one_975 = -quantile(D, 0.025) | 0.026206250000 |
| r_one_95 = -quantile(D, 0.05) | 0.023120833333 |
| r_dir_095 = quantile(D, 0.95) | 0.026344166667 |
| iid_radius | 0.035179851843 |
| iid_radius / sd(D) | 2.329518279397 |

## Implied one-sided coverage

Coverage is the fraction of outer draws satisfying `D >= -r`; SE is the binomial
standard error `sqrt(p(1-p)/n)`.

| candidate radius | coverage | SE | n |
|---|---:|---:|---:|
| r_sym | 0.990000 | 0.007036 | 200 |
| r_one_975 | 0.975000 | 0.011040 | 200 |
| r_one_95 | 0.950000 | 0.015411 | 200 |
| r_dir_095 | 0.975000 | 0.011040 | 200 |

## Required answers

1. **Skewness:** `g1 = -0.369630928675`. The paired-bootstrap 95% interval is
   `[-0.63144292, -0.10648513]`; therefore it is **distinguishable from 0** at this sample size under this diagnostic.
2. **Symmetric versus one-sided:** `r_one_975 - r_sym = -0.004634166667`.
   It **does** differ beyond Monte Carlo error under the paired-bootstrap check.
3. **Oracle design issue:** These pooled outer-draw quantile radii use `TRUE_TV`,
   which a real estimator does not know. Their implied coverage is close to the target
   by construction and is a diagnostic of distribution shape only, not an implementable
   result and not comparable to existing per-replicate sample-only radii.
4. **Level issue:** Track 5 nominal is one-sided `0.975`. Only `r_one_975` is
   level-matched. `r_one_95` and `r_dir_095` target `0.95`, so their coverage and
   comparison with `0.975` are not like-for-like. `r_dir_095` also uses the literal
   signed-distribution 0.95 quantile rather than the lower-tail one-sided direction.

## Quantile method and uncertainty

NumPy default and explicit `method="linear"` were used; they agree exactly here:
`r_sym=0.030840416667`, `r_one_975=0.026206250000`,
`r_one_95=0.023120833333`, and `r_dir_095=0.026344166667`.
The reported difference SE comes from 20,000 paired bootstrap resamples of the 200
outer-draw D values; the skewness interval uses the same bootstrap resamples.
