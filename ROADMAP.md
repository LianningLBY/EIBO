# EIBO — Research Dashboard

> Last updated: 2026-09-15 23:05 UTC | Round 3: W4 settled; detector stratum 340→342 confirmed; boundary set verified UNCHANGED; CSV pull routed to execution side (D121). One combined reflow pending those numbers.

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is a finite-sample strict bound** and **lower side a high-probability bound at a NOMINAL level, with an asymptotically-derived (iterated-log) confidence constant and a conservative finite patch only in the degenerate small-effective-m regime** — the two sides differ in construction and tightness, not in whether proof is possible. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). **⚠️ PENDING CORRECTION (D118):** the radius constant is `sqrt(2 ln(2/alpha))` = 2.9604, which actually certifies **0.975**, not the stated 0.95 — the paper's mechanism sentence for the factor 2 is wrong. Fix: use `sqrt(2 ln(1/alpha))` = 2.7162 (makes 0.95 exact) and **recompute the counts, which I did: upper 340→342, joint 336→338**, with no pair's verdict reversing. The alternative (relabel to 0.975) is rejected because it would force the §4.4 null from 5% to 2.5%. **95% cluster-bootstrap CI [26.5%, 43.1%]** — the pair bootstrap understated width by 2.84x, so quote the cluster interval. Cross-corpus replication supports **non-reproduction** (X11: 523/3321 = 15.75%, upper 534 / lower 3310): the all-pairs and >=13049 strata exclude zero under both bootstraps. **BUT the scale-matched strata do NOT survive** — under the cluster bootstrap the >=20000/>=40000/>=80000 gap intervals include zero (D106), so "the gap narrows under matching" is a point estimate, not a resolved effect. The lower-side reproduction claim (0.9960 vs 0.9967) still holds. DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung. DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost. **⚠️ CEILING (D112, verified):** the median-TV ladder **saturates at high k** — k=30 reaches 1.0000 by M=4 (increments then exactly 0), k=15 by M=8. The paper's three "a finer alphabet resolves more" claims are all **k=5-scoped** so they are true as written, but **if the claim is ever generalized beyond the measured rung it MUST carry this ceiling**: monotone in M at low k, saturating at high k. **Verified from the full 20-cell grid** (`registry.yaml` → `X1.metrics.upper_side_table_20_cells`): the informative count is non-zero in only **4 of 20 cells** (M_1@k5=340, M_2@k5=47, M_4@k5=3, M_1@k10=28) and is **zero by M=8 at every k** — the certificate dies by alphabet resolution 8 regardless of prefix length, which is stronger than the M=1 column the paper quotes.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs (X3_A, X3_B). DONE.

## Current progress

- **Research phase COMPLETE.** All three claims fully backed; evidentiary coverage 100%. (The coverage tool labels `conclusion: negative` as "failed", so it under-reports C1/C3 — the negatives ARE the evidence; noted, not "fixed" in the tool.)
- **Paper in FORMAL REVIEW — Round 3 active** (`review_id 06cc5857`). **W4 DOWNSTREAM (D120):** the detector validation's informative stratum is defined by `eps_hi < 0.5`, the very predicate the constant changes ⇒ the stratum moves **340 → 342**, so §4.4/Table 2 must be recomputed too, not just the headline. **Boundary set: CORRECTED — its membership does NOT change.** I recomputed it: the gap set is exactly `{11–51, 27–29, 35–49, 39–44}`, all four failing the **lower** condition the constant does not touch, and zero overlap with the two joiners (22–36, 32–52), which were upper-only pairs moving into *upper-and-joint*. So **Table 4 needs its caption counts updated (340→342, 336→338), not new rows.** (The paper side first reported the membership as changing, then corrected itself; I verified the correction.) The per-pair detector errors already exist (`x12_detector_validation_per_pair_k5.csv`, 11,880 rows), so this is a **CPU-only re-aggregation over new stratum membership — not a re-run**; the Agent's original "new experiment" framing overstated it. Option (b) (label the table as a conservative-constant run) rejected: it would leave the paper's headline and its own stratum differing by construction. Sequence: Round 1 returned reject (resubmit-worthy) with 23 items, all fixed; Round 2 then stalled at cross-sharing with no report and reconciled to **failed**, which cleared the content de-duplication that had blocked resubmission; the owner-requested re-review was submitted from the unchanged manuscript and accepted as a new round. Round 1's 23 items are all fixed and recorded resolved. Deliverables: `docs/paper/main.tex` + `main.pdf`, **18 pages with the body on 1–13 and References from page 14** (13-page limit satisfied — measured from RENDERED pages, not the compile log, which cannot show where the body ends).
- **Pre-submission verification (all mine, not relayed):** 3 pdflatex passes + bibtex exit 0, 53 bibitems, 0 undefined, 0 overfull; **visual review 18/18 pages passed** (receipt bound to sha256 `5edd8928`); headline numbers independently re-derived — C1 336/990 with cluster CI [26.5%, 43.1%], X11 523/3321, chain-rule per-position truth `0.3389191441548814`; every page rendered and read.
- **Two CFP checks — one holds, one I got WRONG (corrected 2026-09-15):** ✅ there is genuinely **no abstract word limit**, so not cutting was right. ❌ **I claimed the appendix/reference order is unspecified — that was wrong.** USENIX's artifact policy states the ethics and open-science sections must appear **immediately preceding the reference section**, each within one page; the reviewers are right and Round 3 raises it as a possible desk-rejection (W3). The fix is to move both mandatory appendices before the references and compress each to ≤1 page. Camera-ready ceiling is 20 pages incl. appendices; we are at 18.
- **Claim boundaries honoured in the prose**: X9_E's identifier finding scoped to `tv_hat` only (D087); X11's joint gate discloses its per-side sample sizes and the **conservative** bias direction (D093); X8's DPI check is a smoke-test, never cited as theorem verification (D091); C3 reframed as a methods/limits finding (D046); novelty stated as a knowledge claim ("to our knowledge"), never "exhaustive search".
- **Provenance discipline is load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; figures regenerate from manifest-resolved artifacts via committed generators; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first).
- **Manifest verified clean and debt-free (D114)**: **87 entries · 72 with-hash · 16 path-null · 0 unresolved · 0 hash mismatches**, exactly one live entry per artifact (independently recounted by the Reviewer). The seven resolving entries lacking a hash are backfilled; five `agentic-figure` run-scratch records are retired (that integration registered its run directory where `paper-visualization` and `experiment-analysis` correctly registered deliverables); and the last D070 violation — a retirement note whose path still pointed at the live file, **my own error** — is closed.
- **Figure pipeline verified (D115)**: all five figures byte-identical across their three copies; the fig4 non-monotone caption and the fig2 340-vs-336 annotation are fixed **at generator source**, not patched into the PDF; every fig data series maps to a manifest-hashed artifact whose sha matches; the `/tmp` CSV location is a cache since `build_data.py` regenerates from manifest-resolved artifacts; the renderer aborts on bounding-box collisions.
- **Diagnostic worth keeping**: manifest paths are rooted at `/efs/workspace`, not the project dir, so a project-rooted resolution probe reports dozens of false "missing" — a probe defect, not a content defect; I made that error three times before it was caught.

## Review retrospection — Round 3 (2026-09-15) · weak reject, panel ≈3/5

**Material fact:** the Round 3 PDF was byte-identical to Round 2's, because **Round 2's report was never delivered** (platform fault) so nothing was revised between rounds; every Round 2 finding therefore reproduces by construction. This is the first Round 3 report seen.

**Holistic pass — the core is intact and the remainder is one closed list.** All three reviewers confirm the scientific core: Reviewer 1 independently rederived Lemma 1's full chain; the nominal-level reframe, the pairwise repositioning, the cluster bootstrap and §5.1's voluntary self-downgrade all hold. **Every remaining item is a text edit, a table recomputation, or a layout move — no new experiments.** So the systemic issue is not scientific: it is that a revision's remaining work is visible, enumerated, and unclosed.

**Two desk-visible (W1, W2) · one layout violation (W3) · one item that moves published numbers (W4) · one self-contradicting table row (W5) · one missing characterisation of the title object (W6).** Plan sent to the independent Reviewer before dispatch; W4's radius legitimacy and W6's analysis-vs-writing classification are the two judgments held for its check.

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

## ⚠️ BLOCKER — Round 2 stalled; re-review attempted and DE-DUPLICATED (2026-09-15 13:35 UTC)

**Symptom.** Round 2 has sat in `cross_sharing` since 09:13 with 3 reviewers dispatched and no report. Round 1 completed in ~32 min; this round is at ~4h40m. No review-side session has written since 09:31, while my session and the execution session are both active. Status is not flagged `indeterminate`.

**Re-review attempt (owner-instructed) — outcome: blocked by design.** I re-ran the full gate (re-rendered and re-inspected all 18 pages, refreshed the 2-hour visual receipt against the unchanged bytes) and called `submit_paper_to_review`. The platform returned **`deduplicated: true`** with the *existing* `review_id` and round 2 — the entry point de-duplicates by content, so **while the manuscript bytes are unchanged there is NO Director-side path to open a fresh round.** That is protective (it prevents round/record corruption) but it makes the stall unsolvable from inside this project's toolset.

**Unstick action and owner (updated).** Two viable paths, both outside my toolset:
1. **Platform-side review-gateway recovery** — the round did not close out cleanly; ownership is platform operations. My part is the report and leaving round records untouched.
2. **Owner-initiated re-review from the web side** — if the web UI exposes a resubmit / re-review control, it may not traverse the same de-duplication. If the owner takes this path, hand over: round id, where it stopped (cross-sharing since 09:13), duration (~4h40m), byte-verification state, and the 23-item fix list.

**Do NOT:** resubmit a third time (same result), hand-edit review state, bump the round counter, or modify the manuscript solely to defeat de-duplication — a fabricated byte change made to game the gateway would also invalidate the visual receipt and the submitted provenance.

**What is NOT blocked:** the paper is frozen and drift-free; all 23 Round 1 issues are resolved; provenance is clean (all 83 manifest entries resolve with matching hashes). Only the *report* is missing.

## Near-term tasks — Round 3 (all items are text/table/layout; NO new experiments)

**DONE and verified against the rendered PDF:** RT-W1 ([4] author list corrected to Luxemburk/Hynek/Jonas Mücke + dataset DOI — the wrong given name "Jan" had been carried from the machine residue and read as a clean citation); RT-W2 (literal markdown marker removed from the compiled text); RT-W8; RT-W10; RT-W12; RT-W13 (the "duplicate" was a point stated twice, not a paragraph); RT-W14; RT-W15 (fig1 labels fixed at generator source, all three copies identical); RT-W16; RT-W17; RT-W18; RT-W19 (hashes now full 64 chars + pre-registration timestamps); RT-W22; plus fig1's manifest hash re-registered and all five figure entries audited.

**DRAFTED and approved, implementation HELD:** the A.2b sentence rewrite (three clean claims: wire image / corpus+companion / deployment measured / classifiers applied) with `mucke2025waiting` added, `dyer2012peekaboo` **dropped** (already cited in §6.3 — moving would duplicate) and `athanasiou2025selfdefense` **moved to §6.3** (its only home was its wrong one); plus the §6.3 defenses-clause addition. Page 12 is the densest in the body (807 words) but page 13 has ~100 words of slack, so the ~18-word addition should reflow; the fallback is a same-size §6.3 cut, verified by RENDERING not the compile log. Drafts must use `\citep`/`\citet` — the paper has zero bare `\cite`.

**HELD pending the independent Reviewer's check on four judgment calls:** RT-W4 (the 0.95/0.975 radius arithmetic — the only item that can move published numbers; preferred fix raises 340/336), RT-W6 (whether the missing ε_lo distribution is an analysis gap or a writing gap), RT-W7 (novelty-boundary rewrite vs one aligning sentence), RT-W9 (the three promotions). Also held: RT-W3 (appendix reflow before the references — verified a real USENIX requirement, and it overturns my own earlier wrong conclusion) and RT-W11 (sparse-inflation confound).

**Then:** ONE combined reflow (A.2b + §6.3 + W3 + held items), verified by rendering; per-item Reviewer verification before any item is marked resolved; then decide the next round. The report states the remedy is a visible revision, not more science.

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
| D121 | 2026-09-16 | D121: routed the per-pair CSV pull to the executio | — |
| D120 | 2026-09-16 | D120: W4 has a downstream effect on the detector s | — |
| D119 | 2026-09-16 | D119: remaining three judgment items settled — W6  | — |
| D118 | 2026-09-15 | D118: W4 settled analytically — the current radius | — |
| D117 | 2026-09-15 | D117: Round 3 weak-reject — scientific core intact | — |
| D116 | 2026-09-15 | D116: re-review submitted and accepted — Round 2's | — |
| D115 | 2026-09-15 | D115: all independent-reviewer tracking items clos | — |
| D114 | 2026-09-15 | D114: manifest debt closed (87 entries, 0 unresolv | — |
| D113 | 2026-09-15 | D113: higher-k ladder manifest defects closed — ha | — |
| D112 | 2026-09-15 | D112: higher-k ladder saturates (median 1.0 by M=4 | — |

