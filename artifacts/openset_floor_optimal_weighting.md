# Optimal weighting: the open-set floor nearly doubles under the same assumptions

2026-09-17. Follow-up to `openset_floor_tightened.md` and `openset_floor_looseness.md`. The looseness
note identified equal weighting as the reason the floor is slack. This note removes that restriction —
**and the floor on the corpus goes from 0.186 to 0.363.**

## The observation

The derivation sums `err_i + err_j >= 1 - tv_ij` over ordered pairs with **equal** weight. But the
argument never required equal weights. For any non-negative weights `w_ij`,

```
sum_{i!=j} w_ij (err_i + err_j)  >=  sum_{i!=j} w_ij (1 - tv_ij)
```

and the left side is a bound on the per-class errors only when the **row sums are uniform**:

```
r_i := sum_{j!=i} (w_ij + w_ji) = 1   for every i
   =>  sum_{i!=j} w_ij (err_i + err_j) = sum_i err_i = M * E[err]
```

So `E[err] >= [ max over feasible w of sum_{i!=j} w_ij (1 - tv_ij) ] / M`, and since every term is a
known quantity (`1 - eps_hi`), the maximisation is a **linear program** whose optimum we can compute.
Validity is then automatic: each `w_ij >= 0`, each `1 - eps_hi <= 1 - tv`, so the objective can only
be smaller than the truth would give.

**Equal weights are the feasible point `w_ij = 1/(2(M-1))`, which recovers the earlier bound exactly.**
So the LP is a strict generalisation — the previous result is its worst feasible point.

## Result on the corpus

| weighting | floor (M = 46) |
|---|---|
| uniform (previous) | 0.186 |
| **LP-optimal** | **0.363** |
| improvement | **+95.4%** |

## Verified

- **Validity, 200 randomised configurations** (3–8 classes, sparse and dense alphabets, near-identical
  clusters, upper bounds inflated by up to 0.4 of slack): **zero violations** against the exact Bayes
  error.
- **Validity on 8 heterogeneous cases** with certified bounds built as true `tv` plus slack: every LP
  value below the true error, with improvements of 9–67% over uniform.
- The equal-weight point reproduces the earlier bound exactly, confirming the LP strictly contains it.

## Why this matters more than the earlier tightenings

The two previous steps moved the number by correcting an input filter (0.118 → 0.186). **This one
changes the method**: the equal-weight averaging was not a requirement of the derivation but a choice,
and relaxing it is worth almost as much as everything before it combined. It also directly addresses
the diagnosis in the looseness note — that equal weighting cannot concentrate on the confusable
classes — by letting the LP find where the mass belongs.

## Limits, stated plainly

1. **Still Le Cam-based.** The core inequality is unchanged and standard; the contribution is the
   weighting optimisation, which is a genuine but incremental step, not a new bound.
2. **The weights are computed from `eps_hi`,** which are themselves data-dependent upper bounds. The
   validity argument does not care (it holds for any non-negative `w`), but it does mean the LP must
   be re-solved per configuration.
3. **The uniform prior is still required** for `E[err]` to be the per-class average.
4. **Not compared against measurement.** The project has no multi-class open-set run, so 0.363 cannot
   be checked against an observed multi-class error. Reporting such a comparison would repeat the
   category error behind the retracted impossibility claim.
5. **The LP is over the known classes only** (the unknown-class terms are still discarded, with
   `M = K+1` in the denominator), so the same assumption-free property is preserved.

## Status

Exploration line. Paper remains frozen at the weak-accept version per the user's direction.
