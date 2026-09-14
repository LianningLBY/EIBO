# EIBO — Idea Brief (pointer + MVP record)

<!-- Origin
Source: idea (IDEA Generator)
Idea ID: d15c2c2b-41f4-4d28-87ff-d5fbe7e00fa8
Created: 2026-09-12
-->

> **The full idea text lives in `docs/PROJECT_BRIEF.md`** (Summary / Core Problem / Opportunity /
> Approach / Key References). This file records the MVP outcome against it and is the append target for
> the MVP validation results.

## MVP outcome — 2026-09-14

**Hypothesis: SUPPORTED.** A two-sided epsilon-indistinguishability bracket with explicitly graded
certification is **computable on real encrypted QUIC wire data**, on both of the project's two questions.

### The two answers
| object | result |
|---|---|
| **Q1 — k-prefix chain** (k=5, M=1, coarsest rung) | **gate 336/990 = 33.94%** — upper side `eps_hi < 0.5` = **340/990** (finite-sample strict, given the a-priori `m`); lower side `eps_lo > 0.05` = **986/990** (asymptotic) |
| **Q2 — PHIST whole-flow** (packet-cell law, m=32) | **informative 342/990 = 34.55%** under the sharp sum-to-zero bound (16r) |

**Both are FULLY MEASURED.** The Q1 gate's own artifact reports **measured 990 pairs / assumed 0**, from a
full-n run with the sample cap removed and no fallback.

### What the MVP settled structurally
1. **The upper side binds at every rung** (it removes 650 pairs; the lower side removes only 4 within the
   upper set). The tension is *"can a certificate exist at all"*, not *"can the services be told apart"*.
2. **M=1 is the ONLY viable rung** — despite having the smallest alphabet and the lowest `k_cert`. The feasible
   set shrinks monotonically in M and saturation rises monotonically (0 / 0.105 / 0.239 / 0.336 / 0.391), so
   **a finer alphabet has LESS resolving power**: coarse-graining is necessary, not a concession.
3. **k=10 leaves only M=1** with any certificate (0.0111). The certificate horizon is short and steep.
4. **The guarantee asymmetry is intact and is the thesis:** the upper side is finite-sample strict given the
   a-priori `m`; the lower side is **asymptotic**. **"Proven" is unavailable for the lower side at any stage.**
5. **Q1's 340/990 and Q2's 342/990 do NOT corroborate each other.** A 2×2 decomposition: using each object's
   own radius, 340 vs 342 (difference 2); holding the radius common, 340 vs 935 and 81 vs 342 (differences
   260–600). The underlying statistics differ **2.7×** while the radius constants differ **7.34×** — two large
   differences in opposite directions **cancelling**. Numerical coincidence, zero corroborative weight.

### Corrections that materially changed the numbers (each recorded with its cause)
- **2× radius error** — the runner dropped the `0.5` coefficients that the repo's own `statcore.tv_upper_bound`
  applies. It understated Q1's headline by **5.2 points** (0.2919 → 0.3434). Direction: conservative.
- **2×-loose multiplier in Q2** (`31` instead of `16`, from ignoring `sum(delta)=0`) understated Q2 by ~19
  points (152 → 342).
- **The first Q2 attempt was VOID** — its two sides bounded different objects, giving `eps_lo > eps_hi` on
  **988/990** pairs. The one-hot symbol-map repair took that to **0/990**.

### Limitations that must travel with every citation
- The corpus is a **10M-flow budget subset with unknown month coverage** ⇒ **Step-0 PASS is provisional**;
  full-corpus confirmation is the condition for closing it.
- **The certificate exists on a MINORITY stratum (~34%), not corpus-wide** — the median pair falls outside the
  band. The correct sentence is *"34% of service pairs admit a two-sided interval whose upper side is
  finite-sample strict and whose lower side is an asymptotic lower bound exceeding 0.05"*, **not** "the bracket
  is provable".
- **The lower side is asymptotic** ⇒ the word "proven" must not be used anywhere.
- Nearest margins to the 0.05 line at full n: **+0.0088** (nearest pass) and **−0.0073** (nearest fail) ⇒ the
  gate is stable at the ~0.007–0.009 level; it is **not** knife-edge. (An earlier claim that it rested on a
  margin of 0.0002 was wrong — that was the *capped* value's margin, a quantity the gate does not use.)

### Environment gate (Q2's identifiability precondition)
**Step-0 PASS (XS subset):** 53 services, 45 at the 2,000-flow threshold; two-axis 43/39, full-crossing 39/36
— comfortably clearing the ≥15 criterion. `TIME_FIRST` spans 13 calendar months (12 full + a 69-flow boundary
fragment). **32/53 services are single-ASN** ⇒ `DST_ASN` is an audit confound, not an environment axis.
**NOT closed** pending full-corpus confirmation.


## MVP Validation Results

- **Date**: 2026-09-13
- **Hypothesis Supported**: Yes

### Key Metrics

Q1 (k-prefix, k=5, M=1, coarsest rung): gate 336/990 = 0.3394 (upper side eps_hi<0.5 = 340/990, finite-sample strict given the a-priori m; lower side eps_lo>0.05 = 986/990, asymptotic). FULLY MEASURED: the artifact reports measured 990 / assumed 0, from a full-n run over all 990 pairs with no cap and no fallback. The upper side binds (removes 650 pairs; the lower removes only 4 within the upper set). Per-rung: M=1 is the ONLY viable rung; the feasible set shrinks monotonically and saturation rises monotonically 0/0.105/0.239/0.336/0.391, so finer alphabets have LESS resolving power. k=10: only M=1 has any certificate (0.0111). Nearest margins at full n: +0.0088 (nearest pass), -0.0073 (nearest fail). Q2 (PHIST packet-cell law, m=32): informative 342/990 = 0.3455 under the sharp sum-to-zero bound (16r); 152/990 under the superseded 2x-loose 31r. Q1/Q2 near-equality is CANCELLATION, not corroboration (2x2: own radii 340/342; common radii 340 vs 935 and 81 vs 342; statistics differ 2.7x, constants 7.34x). The first Q2 attempt's object mismatch is FIXED: invariant violations 988/990 -> 0/990. Step-0 environment gate PASS on the XS subset (53 services, 45 at threshold, 39 two-axis / 36 full-crossing), provisional.

### Summary

The MVP hypothesis — that a two-sided epsilon-indistinguishability bracket with explicitly graded certification is COMPUTABLE on real encrypted QUIC wire data — is SUPPORTED on both of the project's questions. Two independent certified objects were measured on the CESNET-QUICEXT-25 XS subset (10M flows, 45 services at a 2000-flow threshold, 990 pairs, k=5). (a) k-prefix chain: the joint gate (eps_lo>0.05 AND eps_hi<0.5) holds for 336/990 pairs = 33.94%, FULLY MEASURED across all 990 pairs with zero assumed, from a full-n run with the sample cap removed. The upper side is the binding constraint at every rung, and M=1 (the coarsest rung, smallest alphabet, lowest k_cert) is the ONLY viable rung — so a finer alphabet has LESS resolving power, which is the sharpest available evidence that coarse-graining is necessary rather than a concession. (b) PHIST whole-flow object: 342/990 = 34.55% informative under the sharp sum-to-zero bound. Several corrections materially changed the numbers and each is recorded with its cause: a 2x radius error (the runner dropped the 0.5 coefficients that the repo's own tv_upper_bound applies) understated Q1's headline by 5.2 points; a 2x-loose multiplier (31 instead of 16, from ignoring sum(delta)=0) understated Q2's by ~19 points; and the first Q2 attempt was VOID because its two sides bounded different objects (eps_lo>eps_hi on 988/990 pairs), which the one-hot symbol-map repair fixed to 0 violations. The single most important negative result is that Q1's 340/990 and Q2's 342/990 do NOT corroborate each other: a 2x2 decomposition shows agreement only where each object uses its own radius convention, while holding the convention common separates them by 260-600 pairs — two large differences in opposite directions cancelling to the same fraction. Limitations that must travel with every citation: the corpus is a 10M-flow budget subset with unknown month coverage (Step-0 PASS is provisional); the certificate exists on a MINORITY stratum (~34%), not corpus-wide, with the median pair falling outside the band; and the lower side is asymptotic, so "proven" is unavailable at any stage.

### Recommendation

GO. Both MVP questions are answered on real wire data with fully measured quantities. Q1's two-sided bracket exists at the coarsest rung for 336/990 (33.94%) of pairs, with the guarantee asymmetry intact (upper side finite-sample strict given the a-priori m; lower side asymptotic — "proven" is unavailable at any stage, and that asymmetry is the paper's thesis rather than a defect). Q2 yields 342/990 under a valid sharp bound. The claim that must NOT be made is that the two objects corroborate each other: their agreement is cancellation. Research-phase priorities in order: (1) vector-level distinguishability as a one-sided result (a real paper number, currently unreported, CPU-only); (2) the masking two-arm design with genuinely different flow sets, with the requirement written INTO the script rather than re-derived per run; (3) closing Step-0 by confirming corpus representativeness on the Parquet months (off the MVP critical path but the condition for closing); (4) the month-level split, which is feasible in aggregate but certifiable per month only for high-volume services — marginal-threshold services support a point estimate but not a certified upper side. The frontier is layer-specific (33.94% / 4.7% / 0.3% / 0% across M=1/2/4/8+), so the paper's claim must be scoped to a minority stratum, not the corpus.
