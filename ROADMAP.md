# EIBO — Research Dashboard

> Last updated: 2026-09-14 19:12 UTC | Update reason: Condense 1270-line accumulated narrative to a dashboard; incorporate X9_E verdict, X12 Stage 2 blocker, cross-tree audit, and current coverage

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is finite-sample strict** and **lower side is asymptotic** — the asymmetry *is* the contribution, not a caveat. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung (upper-only fraction falls monotonically in M). DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs. DONE (reframed from a growth-rate claim).

## Current progress

- **MVP passed**; the three claims are all supported by completed experiments. Coverage: C2 100%, C3 100%, **C1 58.3%** (7 done / 2 planned / 1 running / 2 failed — remaining C1 work is comparison/assembly, not new mechanism).
- **X9_E completed (negative→channel-sensitivity finding).** The dose-only hypothesis is falsified: at matched declared m, the SNI-dependent arm (DST_IP hash) yields systematically higher TV than the SNI-independent arm (random ID), median delta growing 0.03→0.36 before both saturate. **⚠ CLAIM BOUNDARY (D087, reviewer-flagged): the identifier effect is established at the `tv_hat` (radius-free estimate) level ONLY — `eps_hi` is `comparison_unavailable` at every rung (an arm saturates), and `eps_lo` is absent.** ⇒ The paper may write "identifier content changes radius-free separation, beyond a pure cardinality effect" — **must NOT write "SNI destroys the ε-certificate" or "degrades the bracket"** (object substitution, same class as X12/D064). Plus: `DST_IP ≠ f(QUIC_SNI)` (8,323 SNI values map to multiple DST_IPs).
- **X9's original +0.39 SNI delta is now fully attributed**: it was a declared-alphabet artifact (ARM B declared 32·256^10, radius ≈ 3.7e9, clipped 1406/1406). The dose-response design X9_E was built to separate cardinality from identifier effect — and did.
- **X12 k=5 containment holds** (9/9 cells, guard cannot fire at corrected rates); detector panel (lightgbm/prototype/ronetc) validated. **X12 Stage 2 (containment statistic) IS implemented and ran** — `build_containment_join` sources X1 upper bounds, calls `eibo.statcore`'s `error_floor_lower_bound`, computes informative/secondary/excluded strata (340/540/110), floor `(1−eps_hi)/2`, and a one-sided binomial α=0.05 unsplit; **all detectors × all holdouts `reject_null=false`**. Pair object: macro-average of the two per-service error rates (documented `PAIR_OBJECT_STATEMENT`).
- **Provenance discipline is now load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first). A cross-tree input audit (19 runners, 53 paths) found one snapshot-only defect (already fixed) and four silent-fallback sites (provenance-only, deferred).

## Near-term tasks

- [ ] **X11 feasibility + acquisition** — the strongest answer to "one dataset". Public corpus, same protocol/channel/split. Non-reproduction is a finding, not to be tuned away.
- [ ] **X2 / X7 / X8 / X10 / X13** — remaining C1 CPU comparisons and assembly (bound comparisons, vector-law, Step-0 closure, missing-service-mass).
- [ ] **Registry/plan linkage** — backfill `registry_id` for plan entries (X1–X13) so `compute_coverage_matrix` reads the real state, not "planned".
- [ ] **Paper: channel-sensitivity section** — the X9_E dose-response finding is quantitative, not auxiliary. **Scope it to `tv_hat` per D087; do not extend to the ε-certificate.**
- [ ] **x3_axis_validation / x3_parametric_growth** — pull the re-run server bytes and re-register (D070); do not hand-edit the parametric growth artifact (sha quoted in registry).

## BLOCKED_ON

| gate | trigger | state |
|---|---|---|
| ~~X12 Stage 2 containment statistic~~ | n/a | **CLOSED** — implemented and ran at k=5; containment holds, all detectors `reject_null=false` |
| x3_parametric_growth stored artifact carries D057-withdrawn sentence | fixed runner re-run + pull | **OPEN** — do not hand-edit (sha quoted) |
| x3_axis_validation stored artifact predates synced fix | re-run + pull | **RE-RUN DONE, PULL OUTSTANDING** — server 123,295 B / 4061258e…; local still stale |
| git push | platform sync route | **CLOSING** — instructed to push; confirm origin/main sha |

## GPU budget

1× RTX 5090 D bound. **X12 is the only GPU-eligible entry and its next run (k=5) must NOT pass `--cpu-only`** so ronetc trains on CUDA. All other remaining work (X1/X2/X7/X8/X10/X11/X13, X9_E) is CPU-only by design — the card idle is a property of the plan, not an omission. Do not invent GPU work to fill it.

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D087 | 2026-09-14 | D087: X9_E claim boundary — identifier effect is t | X9_E |
| D086 | 2026-09-14 | D086: X9_E verdict — negative on dose-only hypothe | X9_E, X9 |
| D085 | 2026-09-14 | D099: Fix C3(ii) title–body contradiction and X3 r | X3 |
| D084 | 2026-09-14 | Retracted my own D119 §3 instruction to take the b | X9, X9_E |
| D083 | 2026-09-14 | Ruled the X9 SNI arm: keep DST_IP as primary per s | X9 |
| D082 | 2026-09-14 | X9 measured a +0.38 SNI-inclusion delta, but the t | X9, X4 |
| D081 | 2026-09-14 | The max_tpr re-measurement produced its answer and | X12_k5, X12 |
| D080 | 2026-09-14 | M108 repeated on a second runner: the parametric r | X3, X6 |
| D079 | 2026-09-14 | Three instances of "the change was made but not pr | X3 |
| D078 | 2026-09-14 | k=5 containment completed and the floor is NOT fal | X12_k5, X1 |

