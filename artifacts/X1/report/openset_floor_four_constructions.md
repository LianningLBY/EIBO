# Four constructions, one with a bug caught in the act

2026-09-17. Follow-up to `openset_floor_mixture_bound.md`. This note adds a fourth construction and
records a **normalisation error I made and caught** during the comparison — which matters more than the
small gain it produces.

## The comparison, corrected

| construction | corpus floor | % of measured |
|---|---|---|
| uniform summation | 0.18577 | 25.2% |
| LP-optimal weighting | 0.36307 | 49.3% |
| mixture + metric short-cut | 0.36347 | 49.3% |
| **exclude-U (new)** | **0.37155** | **50.4%** |
| measured (LightGBM, macro) | 0.7366 | — |

## The new construction: exclude the unknown class from the mixture

The earlier mixture form folded the unknown class into `P̄` using the trivial bound `tv(P_i, U) ≤ 1`,
which silently inflates the average and weakens the bound. Excluding it is strictly better:

```
E[err] = (1/M)[ Σ_{i∈S} err_i + err_U ] ≥ (K/M) · err_known          with M = K+1
err_known = (1/K) Σ_{i∈S} err_i ≥ (K−1)/K − (1/K) Σ_{i∈S} tv(P_i, P̄_S)
```

using the same mixing argument but over the `K` known classes only, since
`Σ_{i∈S} P̄_S(A_i) ≤ P̄_S(∪ A_i) ≤ 1`. The unknown class then enters **only through the prior factor
`K/M`**, not through any distance. Combining with the metric short-cut on `tv(P_i, P̄_S)` gives
**0.37155**, a further +2.2% over the LP.

**Verified: 400 randomised configurations, zero violations.**

## The bug I caught, and why it matters more than the gain

During this comparison my first attempt produced **0.3715 for the *uniform* bound** — double the
correct 0.1858. The cause: I computed `Σ_{i≠j} (1 − eps_hi_ij)` over **ordered** pairs, which counts
every unordered pair twice, but divided by the **unordered** normaliser `M(M−1)`. The correct
denominator for an ordered sum is `2M(M−1)`.

The general rule, now written into the check: an ordered-pair sum
`Σ_{i≠j} w_ij (err_i + err_j)` equals `Σ_i err_i · r_i` with
`r_i = Σ_{j≠i}(w_ij + w_ji)`, so the bound on `E[err]` is the objective divided by **`r · M`**, where
`r` is the common row sum. For uniform `w = 1/2`, `r = M−1`, giving `S_unordered/(M(M−1))`.

**This is the same defect class as the earlier `1/(2K(K−1))` slip and the `0.118` input-filter error: a
factor-of-two placed in the normalisation rather than the sum.** Three instances in one project is a
pattern, not an accident — every construction here should be sanity-checked at `M = 2` against Le Cam
before being trusted, which is exactly how the double count was caught this time.

## Interpreting the near-agreement

Uniform (0.1858) sits well below the other three (0.363–0.372), and the LP, mixture and exclude-U forms
cluster within 2.3% of each other. That clustering across structurally different arguments — an LP
dual, a union bound through the mixture, and a prior-factor argument — is evidence that **~0.37 is the
ceiling of this family of pairwise-certificate arguments**, and that the residual factor of 2 to the
measured error is not reachable by re-weighting or re-arranging the same ingredients.

## Limits, unchanged

Still Le Cam-adjacent; every ingredient standard; composition is the contribution. Uniform prior
required. Not tight: 50.4% of measured, factor 1.98 remains. Not comparable as a certificate on the
measured classifier, and not an open-set rejection evaluation.

## Status

Exploration line; paper frozen at the weak-accept version.
