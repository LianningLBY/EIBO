# Finite-sample band: what adopting it would actually change

Prepared 2026-09-16, corrected after an independent recount. Companion to
`finite_sample_lower_bound_feasibility.md`.

## The mechanism, measured end to end

The constant `beta` enters the construction as an additive correction to the upper envelope:

```
upper(z) = q_m + z~ * m~/T + beta * sqrt( (m~/T)(n~/T)(T - z~) z~ / (T - 1) )
```

A **smaller** `beta` makes the constraint `V_m(z) <= upper(z)` easier to satisfy at every cutoff, so
the inferred adaptive `lambda` can only **increase**, and `eps_lo` rises with it.

Measured on the real implementation (`_michel_bound`, m = n = 1000, separating classifier):

| constant | `lambda_adapt` |
|---|---|
| asymptotic (current) | 0.106599 |
| finite-sample, 0.86x | **0.120175** |

**+12.7% on the bound.** Note this figure is a representative-instance measurement and is not
recoverable from the per-pair artifact; if it is ever quoted in the paper it needs its own provenance.

## The decisive argument: the band touches only the lower side

`beta` is a correction to the **lower**-side construction. The paper's headline is the **joint gate**,
and that is bounded by the **upper** side. Verified by independent recomputation over all 990 rows of
`q1_lower_side_full_n.json`:

| condition | count |
|---|---|
| `eps_lo > 0.05` | 986 |
| `eps_hi < 0.5` (upper) | **340** |
| both (joint gate) | **336** |

The artifact's own `joint_gate.gate_count` is also **336**. Since only 340 pairs pass the upper
condition, the joint gate can never exceed 340 no matter how far `eps_lo` rises:

| scaling of `eps_lo` | joint gate |
|---|---|
| 1.0 | 336 |
| 1.127 | 336 |
| 1.5 | 337 |
| 3.4 | 340 |

**So the band's influence on the headline is structurally excluded, not merely empirically small.**

## Correction: the flip boundary is +17.0%, not "no pair nearby"

An earlier version of this note said "the nearest is 0.0151, so there is no pair in the flip zone".
**That was wrong on both the value and the reasoning** — 0.0151 is the *smallest* `eps_lo` among the
four failures, whereas the pair *closest to the threshold* is a different one. The four failing pairs:

| pair | `eps_lo` | needed to cross 0.05 |
|---|---|---|
| **35–49** | **0.042725** | **×1.170 (+17.0%)** |
| 27–29 | 0.028705 | ×1.742 (+74.2%) |
| 11–51 | 0.022607 | ×2.212 (+121.2%) |
| 39–44 | 0.015071 | ×3.318 (+231.8%) |

At the measured +12.7% every one of them stays below the line (35–49 reaches 0.048151), so the count
remains 986 — but **the margin is +17.0%, not comfortable**. A band improvement of more than 17%
would flip pair 35–49 and take the lower-side count to 987. That changes nothing in the headline
(see above), but the earlier note's "no pair in the flip zone" was wrong and its scaling table
(×1.02, ×1.05, ×1.127 all showing 986) was misleading, since those three are one data point repeated;
the real critical point is ×1.170.

## Conclusion

The finite-sample band is **rigour-only**, and the reason is structural: it acts on the lower side,
which the joint gate does not bind on. It removes the "nominal" caveat and the undefined-region
fallback, and it should be presented as a correctness improvement on the derivation — never as a play
for a better verdict. Its own +12.7% magnitude is a representative-instance figure and needs
separate provenance if quoted.
