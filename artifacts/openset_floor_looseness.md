# How loose is the open-set floor? An honest characterisation

2026-09-17. Follow-up to `openset_floor_tightened.md`. This answers the question that note left
open — how far the floor sits from what a classifier actually achieves — and it found a structural
limit worth stating plainly.

## What could and could not be measured

**A correction to my own first attempt.** My initial sweep varied `M` while holding `S` fixed, which
is invalid: `S` is a sum over the pairs *among the M classes*, so both must move together. Redone
with `M` and `S` matched, over services ordered by mean `eps_hi` (most separable first):

| M | S_M | floor |
|---|---|---|
| 2 | 0.87 | 0.433 |
| 5 | 7.67 | 0.383 |
| 10 | 33.74 | 0.375 |
| 20 | 126.44 | 0.333 |
| 44 | 381.20 | 0.201 |
| **46** (45 services + unknown) | 384.55 | **0.186** |

So on the corpus the floor *rises* as the class set shrinks, which is the useful direction: **the
statement is strongest, in absolute terms, for small `K`.**

## Where the bound actually sits — measured against ground truth

Constructed problems with known total variation, comparing the floor to the exact Bayes error:

| M | true Bayes error | floor | floor / true |
|---|---|---|---|
| 2 | 0.0623 | 0.0623 | **1.00** |
| 3 | 0.2249 | 0.1320 | 0.59 |
| 5 | 0.4031 | 0.1734 | 0.43 |
| 10 | 0.5663 | 0.1484 | 0.26 |
| 20 | 0.7201 | 0.1473 | 0.20 |

**At M = 2 the bound is exactly tight** — it reproduces Le Cam. **It then degrades steadily with the
class count**, recovering only about a fifth of the true error at M = 20. That is not an artefact of
the data; it is intrinsic to the construction. The derivation is forced to average over all `M(M−1)`
ordered pairs with equal weight, so it cannot concentrate on the handful of genuinely confusable
classes that dominate multi-class error. The `1/(M(M−1))` normalisation is what buys the
assumption-free property, and it is also what caps the bound's sharpness.

**Practical reading:** the floor is meaningful for pairwise and low-multiclass statements (`K` up to
roughly 5–10, where it recovers 30–60% of the truth) and increasingly conservative beyond that. For
`K = 45` it is a valid lower bound with content, but it is a floor and not an estimate — the true
error is expected to be materially larger.

## What cannot be measured here

There is **no measured multi-class or open-set run in this project** — the detector artifact carries
per-pair closed-set surrogates, which are a different object. So the corpus value of 0.186 cannot be
compared against an observed multi-class error, and I am not reporting any such comparison. Doing so
would substitute a per-pair quantity for a multi-class one, which is the exact category error that
produced the false "impossibility" claim on 2026-09-16.

## Status

Exploration line. The paper remains frozen at the weak-accept version, per the user's direction; this
and the two companion notes sit outside it.
