# EIBO — Research Dashboard

> Last updated: 2026-09-14 19:12 UTC | Update reason: Condense 1270-line accumulated narrative to a dashboard; incorporate X9_E verdict, X12 Stage 2 blocker, cross-tree audit, and current coverage

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is finite-sample strict** and **lower side is asymptotic** — the asymmetry *is* the contribution, not a caveat. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung (upper-only fraction falls monotonically in M). DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs. DONE (reframed from a growth-rate claim).

## Current progress

- **MVP passed**; the three claims are all supported by completed experiments. **Coverage: C1 12/12, C2 2/2, C3 1/1 — all claims fully backed.** *(The coverage tool labels X9/X9_E's negative conclusions as "failed"; a negative result is a completed finding, not a failure — noted, not fixed in the tool.)*
- **X9_E completed (negative→channel-sensitivity finding).** The dose-only hypothesis is falsified: at matched declared m, the SNI-dependent arm (DST_IP hash) yields systematically higher TV than the SNI-independent arm (random ID), median delta growing 0.03→0.36 before both saturate. **⚠ CLAIM BOUNDARY (D087, reviewer-flagged): the identifier effect is established at the `tv_hat` (radius-free estimate) level ONLY — `eps_hi` is `comparison_unavailable` at every rung (an arm saturates), and `eps_lo` is absent.** ⇒ The paper may write "identifier content changes radius-free separation, beyond a pure cardinality effect" — **must NOT write "SNI destroys the ε-certificate" or "degrades the bracket"** (object substitution, same class as X12/D064). Plus: `DST_IP ≠ f(QUIC_SNI)` (8,323 SNI values map to multiple DST_IPs).
- **X9's original +0.39 SNI delta was a clipping artifact of the `eps_hi` measurement, and X9_E separated the confound — the identifier effect is REAL, not the cardinality.** Specifically: X9's +0.39 was `eps_hi` at m=256^10 where radius≈3.7e9 clips all 1406 pairs (that number is a clipping artifact); X9_E then measured at sane m and found the identifier contributes ~0.34 of `tv_hat` separation while the cardinality-only arm contributes ~0.04 at B=256. **The identifier is the dominant contributor, not the cardinality.**
- **X12 k=5 containment holds** (9/9 cells, guard cannot fire at corrected rates); detector panel (lightgbm/prototype/ronetc) validated. **X12 Stage 2 (containment statistic) IS implemented and ran** — `build_containment_join` sources X1 upper bounds, calls `eibo.statcore`'s `error_floor_lower_bound`, computes informative/secondary/excluded strata (340/540/110), floor `(1−eps_hi)/2`, and a one-sided binomial α=0.05 unsplit; **all detectors × all holdouts `reject_null=false`**. Pair object: macro-average of the two per-service error rates (documented `PAIR_OBJECT_STATEMENT`).
- **Provenance discipline is now load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first). A cross-tree input audit (19 runners, 53 paths) found one snapshot-only defect (already fixed) and four silent-fallback sites (provenance-only, deferred).

## Near-term tasks

- [ ] **x3_parametric_growth re-run + pull** — the stored artifact still carries the D057-withdrawn sentence; the fixed runner must be re-run on the server and the result pulled. Do NOT hand-edit (sha quoted in registry as the defect fingerprint).
- [ ] **x3_axis_validation pull + re-register** — server holds 123,295 B / 4061258e… with the fix; local is stale.
- [ ] **X13 manifest consolidation** — one live entry, canonical path clean, sha computed; retire the duplicate suffixed entries. (In flight.)
- [ ] **X8 DPI relabel** — D091: relabel the DPI check as a smoke-test, drop "holds per pair"/"990/990" wording; do not cite dpi_violations:0 as theorem verification.
- [ ] **X12 k=5 violations/trials backfill** — the artifact's binomial p-values are real (9/9 reject_null=false) but the per-holdout violations/trials fields are None; persist them.
- [ ] **Paper: channel-sensitivity section** — X9_E dose-response finding, scoped to `tv_hat` per D087 (Paper Agent territory, later).

## BLOCKED_ON

| gate | trigger | state |
|---|---|---|
| ~~X12 Stage 2 containment statistic~~ | n/a | **CLOSED** — implemented and ran at k=5; containment holds, all detectors `reject_null=false` |
| x3_parametric_growth stored artifact carries D057-withdrawn sentence | fixed runner re-run + pull | **OPEN** — do not hand-edit (sha quoted) |
| x3_axis_validation stored artifact predates synced fix | re-run + pull | **RE-RUN DONE, PULL OUTSTANDING** — server 123,295 B / 4061258e…; local still stale |
| git push | platform sync route | **CLOSING** — instructed to push; confirm origin/main sha |

## GPU budget

1× RTX 5090 D bound. **X12 (the only GPU-eligible entry) is DONE; its k=5 containment run already completed.** All remaining work (X1/X2/X7/X8/X10/X11/X13) is CPU-only by design — the card idle is a property of the plan, not an omission. Do not invent GPU work to fill it.

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D091 | 2026-09-14 | D091: X8 DPI check is vacuous (0/990 testable); re | X8 |
| D090 | 2026-09-14 | D090: X12 containment WAS executed at k=5 (9/9 rej | X12_k5 |
| D089 | 2026-09-14 | D089: X13 bootstrap interval is invalid — multinom | X13 |
| D088 | 2026-09-14 | D088: Correct ROADMAP X9/X9_E wording — identifier | X9, X9_E |
| D087 | 2026-09-14 | D087: X9_E claim boundary — identifier effect is t | X9_E |
| D086 | 2026-09-14 | D086: X9_E verdict — negative on dose-only hypothe | X9_E, X9 |
| D085 | 2026-09-14 | D099: Fix C3(ii) title–body contradiction and X3 r | X3 |
| D084 | 2026-09-14 | Retracted my own D119 §3 instruction to take the b | X9, X9_E |
| D083 | 2026-09-14 | Ruled the X9 SNI arm: keep DST_IP as primary per s | X9 |
| D082 | 2026-09-14 | X9 measured a +0.38 SNI-inclusion delta, but the t | X9, X4 |

