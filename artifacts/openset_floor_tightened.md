# Open-set floor: two tightenings, one of which corrects my earlier number

2026-09-17. Follow-up to `openset_floor_assumption_free.md`. Both changes were verified by
stress test; one of them means **the number I reported earlier was too small**.

## Correction: every certified pair counts, not just the informative ones

The floor is

```
E[err] >= S / (M(M-1)),      S = sum_{i<j} (1 - tv_ij)
```

and we only ever have an **upper** bound `eps_hi_ij >= tv_ij`. Substituting gives
`1 - eps_hi_ij <= 1 - tv_ij`, so replacing each term by its *smaller* certified value **preserves the
inequality** — and this holds for **every** pair, whatever `eps_hi` is, including `eps_hi = 1.0`
(whose term is 0 and simply adds nothing).

My earlier computation filtered to `eps_hi <= 0.5`, which is the **certification gate**, not a
requirement of the bound. That filter silently discarded 650 of the 990 pairs and a large amount of
legitimate mass. Corrected values on the corpus, over the complete 45-service graph:

| variant | S | floor, M = K | floor, M = K+1 |
|---|---|---|---|
| filtered at `eps_hi <= 0.5` (what I reported) | 222.5 | — | **0.1176** |
| **every pair** (correct) | **384.6** | 0.1942 | **0.1858** |

**The open-set floor is 0.186, not 0.118** — 58% higher than I reported. Same derivation, same
objects; I had narrowed the input without cause.

## Verified

- **Validity of the unfiltered form:** 1200 randomised configurations (2–7 known classes plus an
  unknown, four generator families including `U` placed within a small ball of one known class, and
  `U` as a point mass far from everything), with `eps_hi` taken at its tightest legitimate value.
  **Zero violations.** Using every pair cannot break the inequality, since each substituted term is
  no larger than the true one.
- **Subset refinement — no gain:** restricting to subsets and reweighting by prior mass gives
  `S_S/(M(s-1))`, which on a constructed case (two near-identical classes among four easy ones,
  true error 0.534) returned exactly the full-set value, 0.1999. The full-set averaging is already
  optimal among subset arguments, so this axis is closed.

## What this does and does not change

- **It changes the number**: the statement should be 0.186. Any use of 0.118 is superseded.
- **It does not change the structural point**: an assumption-free open-set floor exists, because the
  discarded unknown-class terms carry positive sign. That remains the substantive claim.
- **Recovering the unknown-class mass adds little**: under an anchoring assumption the floor moves
  by at most +0.023 (at `tv(P_i,U) >= 0` for all `i`, which is the vacuous extreme), down to +0.000
  at full separation. So the floor is robust: the interesting content is in the certified pairs, not
  in the discarded ones.

## Status

Exploration line only. Per the user's direction the paper stays frozen at the weak-accept version;
this and the companion note sit outside it, to be folded in only on request.
