# Finite-sample band: what adopting it would actually change

Prepared 2026-09-16. Companion to `finite_sample_lower_bound_feasibility.md`. This note answers the
actionable question the feasibility note left open: **if we replaced the asymptotic confidence
constant with a finite-sample one, would any published number move?**

## The mechanism, measured end to end

The constant `beta` enters the construction as an additive correction to the upper envelope:

```
upper(z) = q_m + z~ * m~/T + beta * sqrt( (m~/T)(n~/T)(T - z~) z~ / (T - 1) )
```

A **smaller** `beta` makes the constraint `V_m(z) <= upper(z)` easier to satisfy at every cutoff, so
the inferred adaptive `lambda` can only **increase**, and `eps_lo` rises with it — a tighter
(better) lower bound.

Measured on the real implementation (`_michel_bound`, m = n = 1000, separating classifier):

| constant | `lambda_adapt` |
|---|---|
| asymptotic (current) | 0.106599 |
| finite-sample, 0.86x | **0.120175** |

**That is +12.7% on the bound** — far larger than the ~2% the raw constant ratio (0.86) suggests,
because `beta` multiplies a term comparable in size to the rest of the envelope at these scales.

## But it moves nothing at the gate

The gate is `eps_lo > 0.05 AND eps_hi < 0.5`. Per-pair `eps_lo` for all 990 pairs is available in
`q1_lower_side_full_n.json` (min 0.0151, median 0.5548, max 0.9729). Applying the measured scaling:

| scaling of `eps_lo` | pairs above 0.05 |
|---|---|
| 1.0 (current) | **986** |
| 1.02 (+2%) | **986** |
| 1.05 (+5%) | **986** |
| 1.127 (+12.7%) | **986** |

**Identical at every level.** The reason is that only **4 of 990** pairs fail the `eps_lo > 0.05`
condition, and their `eps_lo` values are nowhere near the line — the nearest is 0.0151, so a 12.7%
raise leaves it at 0.017, still far below. There is no pair in the flip zone.

So: **adopting the finite-sample band is a strict improvement in rigour (it removes the "nominal"
caveat and the undefined-region fallback) and a strict no-op on every reported count.** It cannot
change 336/990, 340/990, the cluster CI, or any gate count.

## Consequence

This closes the second of the two rigour items the nudge flagged:

- **Do it** — it is cheap, needs no experiments, and removes a live caveat from the paper's weakest
  side. The comparison tables above are the evidence to cite.
- **Do not justify it as a score play.** It moves no number the reviewers saw. It is a correctness
  improvement on the derivation, and should be presented as exactly that.

Combined with `pairwise_to_openset_aggregation.md` (no new content available there either), the
picture is now consistent: **every remaining computable improvement to this paper is a rigour
improvement, not a claim change.** That is the honest basis on which to decide between submitting as
is and investing in genuinely new mathematics.
