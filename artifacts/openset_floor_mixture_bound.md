# A third construction: the mixture bound, and a metric short-cut that beats both

2026-09-17. Follow-up to `openset_floor_optimal_weighting.md`. The LP was the optimum *within* the
pairwise-summation family. This note leaves that family entirely and finds a strictly better bound,
then improves it again using the metric property of total variation.

## Construction A: the mixture bound

Let `Y` be uniform on `M`, `X ~ P_Y`, and `P̄ = (1/M) Σ_i P_i`. For any test `ψ` with decision regions
`A_i = {ψ = i}`:

```
err = 1 − (1/M) Σ_i P_i(A_i)
    ≥ 1 − (1/M) Σ_i [ P̄(A_i) + tv(P_i, P̄) ]
    ≥ 1 − 1/M − (1/M) Σ_i tv(P_i, P̄)          since Σ_i P̄(A_i) ≤ P̄(∪A_i) ≤ 1
    = (M−1)/M − (1/M) Σ_i tv(P_i, P̄)                                    (A)
```

`tv(P_i, P̄)` is not observable, but `tv` is **convex in its second argument**, so
`tv(P_i, P̄) ≤ (1/M) Σ_j tv(P_i, P_j)`, giving an assumption-free form:

```
E[err] ≥ (M−1)/M − (1/M²) Σ_{i,j} eps_hi_ij                              (A′)
```

At `M = 2` this reduces to `(1−tv)/2` — Le Cam again. **This construction contains no optimisation at
all**, and on the corpus it gives **0.3635**, agreeing with the LP's **0.3631** to three decimals.

## Construction B: the metric short-cut

The agreement above is worth attention, but the derivation has a slack step that can be tightened.
Since `tv` is a **metric**, `tv(P_i, P̄) ≤ tv(P_i, P_j) + tv(P_j, P̄)` for *every* `j`. Taking the
minimum over `j` and iterating is a **shortest-path problem** on the service graph, with edge weights
`eps_hi_ij` — all of which are upper bounds, so every path yields a valid upper bound and so does the
minimum over paths. Solving it by Bellman-Ford relaxation:

| construction | corpus floor | % of measured |
|---|---|---|
| uniform summation | 0.1858 | 25.2% |
| LP-optimal weighting | 0.3631 | 49.3% |
| mixture (A′) | 0.3635 | 49.3% |
| **mixture + metric short-cut (B)** | **0.3847** | **52.2%** |

## Verified

- **Mixture bound**: valid on 10 heterogeneous cases (true error 0.157–0.665), all below truth.
- **Shortest-path mixture**: **300 randomised configurations**, including near-identical clusters and
  inflated edge weights, **zero violations** against the exact Bayes error.
- **Mixture strictly beats the LP on 12/12** randomised cases where both were computed; on the corpus
  they coincide, which is itself informative — two structurally different arguments landing on the same
  number is evidence that `0.363` was a genuine ceiling of the pairwise-summation class, and the metric
  relaxation is what breaks through it.

## What is new here versus the earlier notes

The first two notes corrected inputs. The LP note optimised within the pairwise-summation family. **This
note changes the functional form twice**: (A) replaces pairwise distances with distances to the mixture,
removing the need for any weight optimisation; (B) adds the metric property to replace those distances
with shortest-path bounds. The two are independent — the agreement on the corpus, and the strict
improvement off it, are both informative about where the slack lives.

## Limits

1. **Still Le Cam-adjacent.** Each ingredient is standard (a union bound, convexity of tv, the triangle
   inequality). The contribution is the composition and the recognition that the metric property is
   available and unused.
2. **Uniform prior still required.**
3. **Still not tight** — 52.2% of the measured error, so a factor of 1.9 remains.
4. **No comparison from measurement for the improvement itself**: the measured error is one classifier's,
   and the floor is a lower bound over all classifiers, so the 2.0-point gain cannot be validated
   empirically, only shown to remain below truth.

## Status

Exploration line. Paper frozen at the weak-accept version.
