> ARCHIVED — superseded by artifacts/pairwise_to_openset_impossibility.md (corrected 2026-09-16).
> This file contains the RETRACTED impossibility claim with its errors intact, kept only as a
> record of what was asserted and why it was wrong. Do not cite anything below this line.

> ## ⛔ DO NOT CITE — RETRACTED 2026-09-16 (independent check, severity critical)
>
> **The claims in this note are WRONG.** An independent scrutiny found two errors and I reproduced both:
>
> 1. **The summation step is valid for ALL K, not just K=2.** The bound `err_i + err_j >= 1 - tv(P_i,P_j)`
>    holds for every ordered pair at any K, by constructing the binary test from the classifier itself
>    (`psi_ij(X) = 1{phi(X)=i}`): under `Y=j` we have `{phi=i} ⊆ {phi≠j}` so its error is at most `err_j`.
>    Le Cam then applies unconditionally. So formula (2) is a **correct generalisation**, and it is a
>    **standard textbook result**, not a discovery.
> 2. **The "counterexample" is not one.** Its true Bayes error is **0.075269**, not 0, against a floor of
>    **0.045161** — the formula holds with slack 0.030. The construction makes every non-private symbol
>    carry equal mass for 5 classes, so `argmax` must misassign 5 × 0.002823 = 0.014113 per class.
>    Separability (error 0) would require `rest = 0`, i.e. `priv = 1`, i.e. `tv = 1` and a floor of 0 —
>    still consistent. The two conditions I claimed to co-occur cannot.
>
> **Root cause of the error:** my verification script scored `argmax(P,axis=1) == arange(K)`, which
> assumes class `i`'s modal symbol is the `i`-th column. That holds only for index-aligned one-hot
> supports; the duplicated-support mode broke it, yielding the error of a *mislabelled* classifier.
> Re-running with the correct Bayes error against a uniform prior gives **0 violations in 400 cases**
> (vs 100 with the broken scorer). The "100 of 400" figure was a harness bug.
>
> **What survives:** the weaker, correct observation that the floor degenerates to zero in the
> near-separated regime — but that is a direct corollary of Le Cam, hence also not new.
>
> **See instead:** the Reviewer's conditional open-set corollary, which IS actionable, and the
> correction recorded in the decisions/constraints store.

# Feasibility: pairwise→open-set reduction (the reviewers' named gap)

Prepared 2026-09-16. Question: can the per-pair certificates be aggregated into an open-set
(K-class) error floor — the second item Round 6 names as a clear-accept requirement?

**Answer: no — and the impossibility is provable, not merely unattempted.** This is a *positive*
finding for the paper, because it converts "an argument we do not give" into "an argument that cannot
be given from this object", with a counterexample.

## The natural aggregation, and why it fails

The obvious route is to generalise Le Cam. For a classifier `phi` over K classes with uniform prior,
write `err_i = P(phi errs | Y=i)`. For each pair, the two-point bound gives

```
err_i + err_j >= 1 - tv(P_i, P_j)                                        (1)
```

Summing (1) over all ordered pairs yields `2(K-1)K * E[err] >= sum_{i≠j}(1 - tv_ij)`, hence the
candidate floor

```
E[err] >= (1/(2K(K-1))) * sum_{i≠j} (1 - tv_ij)                          (2)
```

which for K=2 correctly reduces to `(1-tv)/2`. **But (2) is false for K>2**, and it was refuted by
direct test: 100 violations in 400 randomised cases, plus a minimal analytic counterexample.

### The counterexample

Take K=6 classes on a 32-symbol alphabet, each with 0.9125 mass on its own private symbol and the
remaining mass spread uniformly:

- every pairwise `tv` ≈ **0.9** (so (1) holds for every pair, with large slack);
- the Bayes-optimal classifier has error **exactly 0**;
- formula (2) predicts a floor of **0.05**.

The estimator is fully separable, so its error vanishes — while every pairwise certificate reports
near-maximum distinguishability. Formula (2) is therefore wrong, and the error is not a small
constant: it scales with K.

### Why the summation argument fails

Step (1) is a statement about the **pair-restricted** problem: conditional on `Y ∈ {i,j}`, the best
possible test errs at least `(1-tv_ij)/2`. That does not transfer to the full K-class problem,
because with more classes available the estimator has *more* information, and in the separable case
it has enough to be right always. A sum of lower bounds on overlapping sub-problems is not a lower
bound on the whole problem.

## The wider impossibility

The counterexample generalises: **no function of the pairwise `tv` values alone can lower-bound the
K-class error positively.** Whenever the classes are (near-)separated, `tv_ij` is near 1 for every
pair while the achievable error is near 0. Any formula `f({tv_ij}) > 0` is falsified by that
configuration. The pairwise object simply does not see the structure that determines multi-class
error — and separability, which it *does* see, drives the error to zero rather than up.

This is why the honest version of the claim is per pair: the pair-restricted problem is the only one
for which Le Cam's consequence is unconditional.

## Does the unknown class rescue it?

The open-set problem adds an "unknown" class U. If U's law sits within `tv <= eps` of some known
`P_i`, the problem is at least as hard as distinguishing that pair, so

```
open-set error >= (1/2) * (1 - min_i tv(P_i, U))
```

**but this is still a single-pair statement**, about U and its nearest known service. Converting it
to a K-class floor requires a **covering/packing assumption** relating U to the whole known set —
e.g. that U is at distance ≥ δ from *every* known law, together with a bound on how many known
classes are mutually close. The paper does not state such an assumption, and its existing artifacts
do not supply one: the missing-mass estimate (X13) measures **mass**, not distance from U to the
known laws.

## Consequence for the paper

Two things follow, and both are improvements:

1. **The current position is not a shy omission — it is the correct scope.** The paper says
   aggregating pairwise certificates "would require an argument we do not give". That can be
   strengthened to: *no aggregation of this object alone can give a positive open-set floor*, with the
   separation counterexample as proof. A reviewer asking for the reduction is asking for something
   the certified object cannot provide; showing that is a substantive contribution to the paper's
   framing and closes the item honestly.
2. **A conditioned version is available.** If we are willing to *state* a separation/coverage
   assumption on the unknown class, a genuine open-set floor follows trivially and is worth stating
   as a conditional corollary — with the assumption named on the face of it, and its empirical
   plausibility (or lack of it) reported from the corpus. That is a real, bounded addition: one
   assumption, one corollary, plus a measurement of whether the corpus supports the assumption.

## Recommendation

**Do not chase the unconditional reduction — it does not exist.** Instead:

- add a short passage in §3 or the Discussion stating the impossibility with the counterexample, and
  cite the pair-restricted scope as *forced* rather than *chosen*;
- add the conditional corollary under a stated separation assumption, and report from the corpus how
  many service pairs would satisfy it.

That is cheap, honest, and directly answers the reviewer's item — not with the reduction they asked
for, but with a proof that it cannot exist, which is the stronger reply. It also pairs naturally with
the finite-sample lower-bound tightening from the companion note, so one round carries both.
