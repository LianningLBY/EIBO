# EIBO — Research Dashboard

> Last updated: 2026-09-15 09:15 UTC | Round 2 in review (cross-sharing phase); awaiting the report.

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is a finite-sample strict bound** and **lower side a high-probability bound at a NOMINAL level, with an asymptotically-derived (iterated-log) confidence constant and a conservative finite patch only in the degenerate small-effective-m regime** — the two sides differ in construction and tightness, not in whether proof is possible. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). **95% cluster-bootstrap CI [26.5%, 43.1%]** — the pair bootstrap understated width by 2.84x, so quote the cluster interval. Cross-corpus replication supports **non-reproduction** (X11: 523/3321 = 15.75%, upper 534 / lower 3310): the all-pairs and >=13049 strata exclude zero under both bootstraps. **BUT the scale-matched strata do NOT survive** — under the cluster bootstrap the >=20000/>=40000/>=80000 gap intervals include zero (D106), so "the gap narrows under matching" is a point estimate, not a resolved effect. The lower-side reproduction claim (0.9960 vs 0.9967) still holds. DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung. DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs (X3_A, X3_B). DONE.

## Current progress

- **Research phase COMPLETE.** All three claims fully backed; evidentiary coverage 100%. (The coverage tool labels `conclusion: negative` as "failed", so it under-reports C1/C3 — the negatives ARE the evidence; noted, not "fixed" in the tool.)
- **Paper in FORMAL REVIEW — Round 2 active** (`review_id a1a8ea1e`). Round 1 returned reject (resubmit-worthy) with 23 items; all are fixed and recorded resolved. Deliverables: `docs/paper/main.tex` + `main.pdf`, **18 pages with the body on 1–13 and References from page 14** (13-page limit satisfied — measured from RENDERED pages, not the compile log, which cannot show where the body ends).
- **Round-2 pre-submission verification (all done by me, not relayed):** 3 pdflatex passes + bibtex exit 0, 53 bibitems, 0 undefined, 0 overfull; **visual review 18/18 pages passed** (receipt bound to sha256 `5edd8928`); headline numbers independently re-derived — C1 336/990 with cluster CI [26.5%, 43.1%], X11 523/3321, chain-rule per-position truth `0.3389191441548814`; every page rendered and read.
- **Two FALSE constraints rejected after checking the official CFP**: there is **no abstract word limit** (so the divisibility clause and detector paragraph were NOT cut), and the **appendices' placement vs references is unspecified** (so the order was NOT changed, which would have re-broken the page limit). Camera-ready ceiling is 20 pages incl. appendices; we are at 18.
- **Claim boundaries honoured in the prose**: X9_E's identifier finding scoped to `tv_hat` only (D087); X11's joint gate discloses its per-side sample sizes and the **conservative** bias direction (D093); X8's DPI check is a smoke-test, never cited as theorem verification (D091); C3 reframed as a methods/limits finding (D046); novelty stated as a knowledge claim ("to our knowledge"), never "exhaustive search".
- **Provenance discipline is load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; figures regenerate from manifest-resolved artifacts via committed generators; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first).

## Review retrospection — Round 1 (2026-09-15)

**Holistic pass.** Twelve issues (4 critical, 8 warning). Clustering by theme rather than treating them independently:

### ★ SYSTEMIC ISSUE 1 — the abstract over-states relative to the body's own measured scope
**Cluster (3 items): R1-W1, R1-W2, R1-W5.** W1 asserts "the upper side binds on every rung" — an extrapolation of the M=1 joint gate to the whole ladder, where no per-rung lower side exists, and `results.tex`'s own caption concedes exactly that. W5 makes the same error in miniature: the abstract says the certifiable set "falls from **340** pairs", mixing the upper-only count (340) with the joint gate (336) — the one place the paper's otherwise-tight two-number discipline breaks. W2 is the same family one level up: the abstract is inverted against the Introduction's contribution list, giving the estimator negative its own paragraph while omitting the detector validation and the divisibility bound. **⇒ Root cause: the abstract was written to read well rather than to state exactly what was measured.** This is the same defect class the session spent the day removing from the figures — a name pointing at the wrong object. **⇒ It does NOT invalidate any claim; it means the headline prose must be cut back to the measured scope.**
**Global impact: high but bounded — framing-only.** No experiment changes; the body is already correct. Mandatory before the action matrix: a `red-section` framing pass on the abstract.

### ★ SYSTEMIC ISSUE 2 — the experiment is under-reported for a measurement paper
**Cluster (4 items): R1-W3, R1-W6, R1-W7, R1-W8.** The primary corpus is never named (W7) — a reader cannot tell where the headline 336/990 comes from or reproduce the split; the flow threshold that yields the 990-pair set is never stated (W8) even though 990 is the most-quoted denominator; the detector panel has no architecture/features/training protocol/citations (W3); and there is no compute/hardware disclosure and the promised per-pair ledger tables are absent from the appendix (W6). **⇒ Root cause: the paper reports results with rigor but omits the provenance a replicator needs** — ironically the one thing this project's artifact discipline does best internally. **⇒ W3 carries an extra edge: the paper's own text concedes the closed-set/open-set mismatch, so the claim must be scoped to the surrogate it actually measures, plus multiplicity handling.**

### Secondary cluster (2 items): absent uncertainty on cross-corpus and ladder numbers
**R1-W9, R1-W10** — the cross-corpus comparison argues from precision ("agree to three decimals") rather than a statistical test, and the main table plus the median-TV series carry no interval. **⇒ A real gap, but not systemic: both are computable from existing artifacts** (bootstrap CIs), so they are computations, not new experiments.

### Not systemic
**R1-W4** (three Discussion blocks unpaired with the contribution list) is structural-editorial. Decided here: **all three have artifacts or are genuinely absent — promote the two that exist, cut the one that does not.** X13's missing-service-mass has an artifact (`artifacts/X13/data/x13_missing_service_mass.json`); the whole-flow rectified object has one (`q1_absolute_*`). **The DST_ASN audit does NOT exist and is promised at `related_work.tex:102` — that promise must be removed or the audit produced.**
**R3-W1/R3-W2** are reference metadata and page economy — cosmetic, addressed in passing.

### Action Matrix

| ID | Summary | Category | Action | Owner | ETA |
|---|---|---|---|---|---|
| R1-W1 | binding-side claim extrapolated | edit paper (framing) | `red-section`: delete "on every rung"/"100% of the ladder"; state the upper side is the scarce object at M=1 where the joint gate is defined | Paper Agent | now |
| R1-W2 | abstract inverted vs contributions | edit paper (framing) | rebalance: surface detector validation + divisibility bound, compress the C3 negative to one clause | Paper Agent | now |
| R1-W5 | 340/336 conflation in abstract | edit paper | quote 336 (joint) or label 340 as upper-only | Paper Agent | now |
| R1-W3 | detector panel not reproducible | edit paper + clarify scope | add architectures/features/training/citations; state the closed-set surrogate explicitly; report multiplicity handling | Paper Agent | now |
| R1-W6 | no compute disclosure; ledgers absent | edit paper + add appendix tables | add compute budget and split boundaries; add the promised per-pair ledger tables | Paper Agent | now |
| R1-W7 | primary corpus unnamed | edit paper | name CESNET-QUICEXT-25 XS with an artifact reference | Paper Agent | now |
| R1-W8 | flow threshold unstated | edit paper | state the floor and how it yields 990 pairs | Paper Agent | now |
| R1-W4 | orphan discussion blocks | edit paper (structural) | promote the two blocks that have artifacts (X13 mass, whole-flow object) into the contribution list + Results; **remove the DST_ASN promise at `related_work.tex:102`** since no audit exists | Paper Agent | now |
| R1-W9 | no uncertainty on cross-corpus numbers | add computation | bootstrap CI on the 0.9967/0.9960 and the gap series; **note the gap is NOT monotone** (18.3→15.5→9.3→13.0→15.4: minimised at ≥20000, then widens) so "narrows to 9.7" was threshold-shopping; all five intervals exclude zero (pair bootstrap — cluster version pending, ≥20000 has the thinnest margin) | Agent (compute) → Paper Agent | 1d |
| R1-W10 | no uncertainty in main table / tv series | add computation | CI or distribution for the median-tv series, or justify the threshold collapse | Agent (compute) → Paper Agent | 1d |
| R3-W1 | reference metadata/brace items | edit paper | fix author fields and braces; re-verify `michel2020high`, `jiao2018l1distance`, `chan2013closeness` | Paper Agent | now |
| R3-W2 | page economy, no early visual anchor | edit paper | consolidate the two appendices; front-load the bracket schematic | Paper Agent | now |

**No framing PIVOT and no new experiment is required by any item.** W1/W2/W5 are wording cuts back to the measured scope; W3/W6/W7/W8 are disclosure additions from existing artifacts; W9/W10 are computations over existing data; W4 is structural. The three claims stand.

## Formal Round 1 review (23 items) — verdict: reject (resubmit-worthy)

The **formal** review (3 reviewers) returned 23 items, 10 critical. **ROUTING WARNING to future-me: this set shares identifiers with the earlier pre-review list but has DIFFERENT content — the earlier list's R1-W1..W8 are NOT this list's W1..W8.** The Paper Agent completed the earlier list (detector panel, compute disclosure, corpus naming, 990 provenance, appendix consolidation, fig1 front-load — all good and all retained), but the formal criticals below were untouched by it. Re-dispatched under non-colliding tags FR-1..FR-23.

### The four reject causes (correctness / framing)
- **FR-1 (W1)** — Eq.(4)'s radius is **unproven, mis-attributed, i.i.d. undeclared**. `measurement_design.tex:83` calls it "Dvoretzky-Kiefer-Wolfowitz type"; **DKW is sup-norm, Eq.(4) is l1** (closer to Han-Jiao-Weissman [14]). Fix: theorem statement + derivation (the `0.5*sqrt(m/n)` term is an l1-deviation term; the `0.5*sqrt(2ln(2/alpha)/n)` a McDiarmid bounded-differences fluctuation, `2/alpha` from the union over two laws), declare i.i.d. flow sampling, add a time-correlation limitation. **My empirical coverage test (100% at m in {4,16,64,256}) is a sanity check only — `tv_hat` is upward-biased there, so coverage is NOT evidence for the bound. The derivation is.**
- **FR-2 (W2)** — the paper asserts an impossibility **our own code and brief contradict**. `introduction.tex:30`: "'Proven' is unavailable for the lower side at any sample size." But `statcore.py::tv_lower_bound` implements Michel's construction **with a per-sample-size finite-sample confidence constant** (`_michel_beta`), self-labelling "a nominal 1-alpha lower bound"; and PROJECT_BRIEF Step 5 calls the lower side "a **certified, distribution-free** LOWER bound" from "**high-probability**" bounds (Michel's own title). Fix: describe the lower side as what it is and delete the impossibility claim. **The asymmetry selling point survives as construction/tightness, not impossibility.**
- **FR-3 (W3)** — the promised **open-set** error floor has no reduction from the certified per-pair object. Fix by **repositioning** as a pairwise indistinguishability certificate; state the per-pair Le Cam consequence and that the multi-class aggregation is not reduced. Do not invent a reduction we lack.
- **FR-4 (W4)** — "each side of the bracket ... joint 0.95" contradicts the paper's own discipline; the 0.95 belongs to the upper side. **Same error as FR-2 seen from another angle.**

### Other formal items
FR-5 (W5) scope the binding claim to M=1 and fix the column citation · FR-6/7 (W6) panel + **state the near-zero power** (X12 ran binomtest, p=0.9954) · **FR-8 (W7) strip internal workflow annotations from refs [2][30][32][38][44] — desk-reject-visible** · FR-9 (W8) anonymous artifact pointer + exp_id->sha256 + pre-registration record · FR-10 (W10) abstract rebalance · FR-11/12 (W11/12) compute + corpus disclosure (already done) · FR-13/14 (W13/14) uncertainty · FR-15 (W15) four missing related-work clusters (DP, traffic morphing, sparse bias, certified robustness) · FR-16 (W16) soften C3 causality · FR-17 (W17) reference metadata incl. the unchecked `chan2013closeness` year · FR-18..23 formatting/ethics/title.

### Uncertainty — CORRECTED (D102)
The first bootstrap resampled **pairs**, but the 990 pairs are the **complete graph C(45,2)**: 45 services, every service in exactly 44 pairs (verified from the artifact). Pairs sharing a service are correlated, so the pair bootstrap understates width. **Cluster bootstrap over services is the defensible construction.** My own replication:

| quantity | pair bootstrap | cluster bootstrap (authoritative) | ratio |
|---|---|---|---|
| joint gate 33.9% | [0.3091, 0.3677] | **[0.2645, 0.4310]** | 2.84x |
| upper 34.3% | [0.3141, 0.3727] | [0.2685, 0.4338] | 2.82x |
| lower 99.6% | [0.9919, 0.9990] | [0.9914, 1.0000] | 1.22x |
| median tv (M=1) | [0.5601, 0.6064] | [0.5205, 0.6435] | 2.65x |

**Construction (pinned, D104):** draw the 45 services with replacement, **deduplicate to a set**, rebuild the complete graph on the set. Verified by a 50,000-trial simulation reproducing the artifact's replicate pair-count distribution exactly (median 406, p5 300, p95 496). My earlier replication endpoints (3.00x) were from a faulty script and are retracted. Sanity: the naive sqrt(990/45)=4.7x expectation exceeds the observed 2.8x, consistent with only part of the per-pair TV variance being service-level.

**Report the pair AND cluster intervals side by side with the ratio — the comparison is itself the evidence for W10.** Median-TV intervals are **not estimable for M in {2,4,8,16}** (no per-pair rows persisted; X1 stores aggregates) — a future-me must NOT present those without first re-running those cells; cost estimate requested before authorizing.

## Near-term tasks

- [ ] **Await the Round 2 report** — on arrival run the holistic pass then the per-comment Action Matrix (`review-report-action`); no blanket acknowledgement.
- [ ] **Paper edits are FROZEN** until that report lands; any change now would invalidate the submitted version.
- [ ] **x6 input-path resolver** — standing: give x6's four hardcoded inputs the flat-first resolver **when x6 is next edited**.
- [ ] **Four silent-fallback sites** (E7 ×2, Q2 v3, X3 controls) — provenance-only; fix when those files are next touched.
- [ ] Two FROZEN SNAPSHOT manifest entries carry an audit snapshot's hash while their path points at the live runner (path/hash inconsistent by design) — leave unless the runner changes again.

## BLOCKED_ON

| gate | trigger | state |
|---|---|---|
| ~~X12 Stage 2 containment statistic~~ | n/a | **CLOSED** — implemented and ran at k=5; containment holds |
| ~~x3_parametric_growth D057 sentence~~ | n/a | **CLOSED** — withdrawn sentence gone; sha matches manifest |
| ~~x3_axis_validation pull~~ | n/a | **CLOSED** — local sha matches manifest |
| `X9_C` non-terminal status | a registry status vocabulary admitting `cancelled`/`withdrawn` | **OPEN — tool gap (C034), not work.** A withdrawn-never-run design cannot reach a terminal status without fabricating a managed-run history (M131). Annotated per D096. Costs no integrity. |

## GPU budget

1× RTX 5090 D bound. **X12 (the only GPU-eligible entry) is DONE**; all remaining work is CPU-only (paper, review response) by design. The card idle is a property of the plan, not an omission — do not invent GPU work to fill it.

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D107 | 2026-09-15 | D107: Round 2 submitted and active — the four reje | — |
| D106 | 2026-09-15 | D106: W9 cluster bootstrap flips the scale-matched | — |
| D105 | 2026-09-15 | D105: retract my "lower side is finite-sample" ins | — |
| D104 | 2026-09-15 | D104: W10 cluster bootstrap confirmed correct — re | — |
| D103 | 2026-09-15 | D103: cross-corpus gap is non-monotone (correct th | — |
| D102 | 2026-09-15 | D102: bootstrap must resample services, not pairs  | — |
| D101 | 2026-09-15 | D101: Round 1 review verdict reject (resubmit-wort | — |
| D100 | 2026-09-15 | D100: Round 1 review action matrix — two systemic  | X11, X13 |
| D099 | 2026-09-15 | D099: C3's control citation pointed at the BIC rou | X3 |
| D098 | 2026-09-15 | D098: do not reshape registry keys to satisfy a va | X1, X11 |

