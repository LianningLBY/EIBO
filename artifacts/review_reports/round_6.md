---
round: 6
review_mode: fresh
overall_score: "weak accept (4/5). Panel unanimous: R1 4/5, R2 4/5, R3 4/5 (R3 withdrew its earlier 4.5 after cross-response, accepting that the Sec 3.3 coverage calibration is an unfilled substantive item even within its reproducibility remit)."
score_value: 4.0
score_max: 5.0
score_label: "weak accept (4/5). Panel unanimous: R1 4/5, R2 4/5, R3 4/5 (R3 withdrew its earlier 4.5 after cross-response, accepting that the Sec 3.3 coverage calibration is an unfilled substantive item even within its reproducibility remit)."
verdict_canonical: "weak accept"
verdict_raw: "weak accept  . Panel unanimous: R1 , R2 , R3 (R3 withdrew its earlier 4.5 after cross-response, accepting that the Sec 3.3 coverage calibration is an unfilled substantive item even within its reproducibility remit)."
timestamp: 2026-09-16T05:50:06.230256+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Consolidated Review Report — Round 6 (Revised Manuscript)

**Venue**: USENIX Security 2027 (Cycle 2) · **Review round**: 6 · **Reviewers**: 3

**Material facts.** The PDF has changed again (18 pages, SHA-256 `c57f6a0c…`; Round 5 was 19 pages). The hard gate set in Round 5 is cleared. The body remains exactly 13 pages. **The panel is unanimous at 4/5**: R3 raised to 4.5 in its independent review, then **withdrew that figure after cross-response**, accepting that the §3.3 coverage calibration is an unfilled substantive item even within its own reproducibility remit.

---

## Summary

This round closes every remaining *defect*. The one hard gate — a §4.4 footnote that referenced "the settled computation in the review record", an internal review-process artefact in the submitted PDF — is deleted outright (render-confirmed; "review record" has zero occurrences), and its content was promoted into the body in a better location. The p15 blank page is gone; the count fell back to 18 with the body still at exactly 13. The reversed direction claim in §4.4 was not merely corrected but replaced with a fuller argument that answers both the direction objection and a deeper falsifiability objection — prompting Reviewer 2 to withdraw its competing position in full and Reviewer 3 to call the fix "more concise than my own suggestion." The abstract's three-round 340/336 conflation is fixed, and the certification-grade definition moved into §1's first paragraph. The contentious "which null is stricter" question was resolved by *disclosing both nulls*; all three reviewers independently recomputed the p-values and agree.

What remains divides into three groups: a handful of propagation and wording residues (all one-line), one venue convention the panel cannot verify from the PDF, and the panel's standing **clear-accept threshold** — one substantive methodological addition plus the four-round-stale §3.3 coverage calibration. The novelty rating is "incremental" for the sixth consecutive round, and this round added no mathematics.

---

## Strengths

1. **The hard gate is cleared.** The §4.4 footnote is deleted and its content moved into the body's "Multiplicity and power." passage — a strictly better location. Verified by R1 and R3 from the render and by R2 from the text layer.
2. **The §4.4 rewrite exceeds what was asked.** Beyond the direction fix ("the validated object is *easier* to detect"), it adds: "A breach on the finer channel would not, however, falsify the coarser certificate; this validation is a consistency check, not a falsifiable test." That sentence answers R1's direction objection *and* the non-falsifiability concern R3 had raised, and caused R2 to withdraw H-2 in full — R2's own words: "my derivation broke down; the fault was mine."
3. **The null question was resolved by transparency, not adjudication.** §4.4 reports both nulls (5%: strongest cell p = 0.9765; 2.5%: p = 0.346). R1 recomputed 0.347, R2 independently 0.346–0.348, R3 0.346 — unanimous. R2 notes the method is now "better than the disputed wording it replaced."
4. **The blank page is gone** and appendix material is consolidated (Tables 4–5 moved up), with the body unchanged at 13 pages.
5. **The abstract's 340/336 conflation is fixed** ("the 340 pairs in the informative stratum"); §4.4 reads "the pairs with εhi < 0.5". Three concrete numbers — 336 certified / 335 capped variant / 340 informative stratum — now coexist coherently, each named.
6. **No regressions.** The ethics/dual-use material, hash-salting discussion, repaired citations, four added references, appendix ordering, and 64-hex provenance hashes with timestamps all remain intact.

---

## Weaknesses (core)

### The clear-accept threshold — the reason the score does not rise

**W1 — §3.3 still declines a coverage calibration, four rounds running.** The passage is verbatim unchanged since Round 3: "A coverage check on near-identical synthetic pairs would not test it … the derivation is what supports the bound." All three reviewers now name this the first item on the shared threshold, and all three stress it is **low cost**: the known-truth apparatus the authors already built for C3 (§3.5, §4.5) can carry a true-TV scan over (0, 0.5) plus a dependent-data arm without new method. R3, from the reproducibility remit, calls it "the one unfilled substantive item in this paper's reproducibility/verifiability dimension" and withdrew its 4.5 on that basis. It is the last unbacked support for the "certification-grade" label.

**W2 — no substantive methodological addition this round.** A section-by-section comparison against Round 5 finds zero methodological content added: Lemma 1 unchanged, no finite-sample lower bound, no pairwise-to-open-set reduction, the certificate still confined to (M=1, k=5) — the only rung where a joint gate exists. R2: "the distance to clear accept is not something editing can shorten; it needs an addition in the mathematics."

### Propagation residuals — corrections not carried to the framing surfaces

**W3 — the abstract's detector claim is stronger than the body supports.** The abstract says "no detector breaches the certified floor"; §4.4 states the tested quantity is "a pair-level macro-average surrogate" of *closed-set* error, not the open-set quantity the floor bounds, and that only the narrower statement is citable. (Paper audit; R1 and R2 concur on the underlying wording issue.)
**W4 — the abstract still asserts causality §4.3 retracted.** Abstract: raising alphabet resolution "resolves more structure". §4.3: "associated with higher median divergence, **but the confound named above leaves the causal claim open**." (R1.)
**W5 — the abstract omits three qualifiers the body carries**: the detector test's power caveat, the capped/full-n convention dependence, and — after this round's change — the double-null context (the abstract cites only the 5% null). (R1, R2, R3.)
**W6 — the Conclusion omits the estimator finding entirely**, though the abstract elevates it to a contribution and the Introduction gives it a full bullet. (Paper audit; missed by all three reviewers.)
**W7 — the §5.1 cross-corpus comparison mixes conventions** (primary full-n 33.9% vs replication capped 15.75%) and discloses it, yet the abstract reports 15.75% without the flag, and because both corpora were measured under both conventions a matched contrast (33.8% vs 15.75%) is one sentence away. (R2; paper audit.)

### One-line wording unifications

**W8 — §4.4's "Both substitutions run in the same direction" covers only the second.** The mechanism given applies to the resolution substitution; the closed-set/open-set substitution is described in the same section as producing "the **narrower** citable statement" — the opposite direction. R2 supplied the intra-paragraph evidence. Fix: drop "Both", or argue them separately. (R1, R2, R3.)
**W9 — "not falsified" vs "not a falsifiable test".** The body says the validation is "a consistency check, not a falsifiable test"; Table 2's caption says "the certified floor is not falsified"; Contributions entry 4 says "no detector breaches the certified floor". Fix: "not contradicted" / "no breach observed". (R1, R2, R3.)
**W10 — §2.3 still groups [11] Diakonikolas and [19, 22] under "Kolmogorov–Smirnov style refinements"**, while §6.2 now correctly separates "closeness testing" [5, 11] from "ℓ1 minimax" [19, 22]. The RT-W16 fix landed at one site and not the other. (R2.)
**W11 — Sec 4.2's closing sentence still reads "significant unmatched"** while the abstract and §4.2's opening read "significant before matching". (R3, confirmed by R1 and R2.)
**W12 — Sec 4.3 uses two names for one statistic** ("the median of the paired differences" vs "the per-replicate change in median TV"). (R1.)
**W13 — the two-null juxtaposition needs one connecting clause**: the implied 2.5% threshold is not the pre-registered one, and the paragraph reads "little power" before reporting p = 0.346, which a reader may misread as a contradiction. (R2 and R3, independently.) R2 and R3 both note this is the correct resolution of the earlier dispute, not a defect.

### Paper-audit findings not raised by any reviewer

**W14 — the reproducibility ledger claim is imprecise.** tab_boundary/main state that recomputing the upper-side condition row-by-row from the 990-row ledger reproduces "the 340-pair count and the 336-pair joint gate" — but the joint gate depends on the lower side, whose per-pair values live in a *different* artifact. A reader recomputing from the stated ledger alone gets 340, not 336. State which artifact carries each side.
**W15 — the fourth panel detector is unnamed** ("A fourth intended detector did not run (ModuleNotFoundError)"). Naming it costs nothing and makes the pre-registered panel auditable — exactly what the paper's own pre-registration section argues for.
**W16 — compute disclosure is incomplete**: no GPU model or memory, and the paper does not say the GPU path was attempted and failed before the CPU fallback. The venue's checklist expects the accelerator model.
**W17 — symbol overload.** `α` and the number 0.05 carry three distinct meanings (§3.3's per-law α = 0.025; §4.4's binomial-test α = 0.05; the gate's ε_lo > 0.05). Give the binomial test its own symbol.
**W18 — the preprocessing pipeline (flow segmentation, the 2,000-flow threshold's provenance, the discarded buffer month) is described only by pointer**, though the occupancy gate and the 45/53 service selection both depend on it.
**W19 — the Limitations block omits three limitations the body itself raises** (the mixed-convention comparison, the detector panel's power, the lower side's nominal status), and is not split by theme.
**W20 — Related Work sits after Discussion**, so the reader reaches Results without a positioning anchor; the paper audit suggests moving it between Background and Measurement Design. (Info-level; the panel takes no position.)

---

## Reviewer Consensus

- **[AGREE] Every substantive defect from Rounds 1–5 is closed.** The three longest-surviving — the internal-footnote gate, the blank page, and the reversed direction claim — all fell in this round, verified with render evidence.
- **[AGREE] The §4.4 rewrite is correct and exceeds what was requested**; R2's withdrawal of H-2 is recorded and accepted.
- **[AGREE] The double-null reporting is correct**; three independent recomputations agree.
- **[AGREE] No desk-reject-level item remains.** Body ≤13 pages, double-blind intact, mandatory appendices correctly placed and within their allowances, no internal artefact in the PDF, no ghost or mis-cited reference.
- **[AGREE, unanimously at 4/5] The novelty rating stays "incremental" and the clear-accept threshold is unchanged.** R3's withdrawal of its 4.5 makes the panel unanimous: the §3.3 coverage calibration is unfilled even within the reproducibility remit.
- **[AGREE] All remaining defects are editorial; the threshold is not.**

## Reviewer Divergence

**Resolved within the round — the panel is now unanimous.** R3's independent 4.5 was scoped to its format/ethics/reproducibility remit; after cross-response R3 **withdrew it**, judging that the §3.3 coverage calibration — although methodologically flavored — is the one unfilled substantive item in its own reproducibility/verifiability dimension, and noting the apparatus already exists at negligible cost. R1 and R2 had already converged at 4/5. **Final panel position: 4/5, unanimous.**

R3 also corrected the attribution record on two points, which this report adopts: the Round 5 "stricter direction" fix corresponds to **R3's own Round 5 finding (C2)**, not to R1's rebuttal; and the "Open Science exceeds one page" claim is settled in R3's favor (≈0.63 page, compliant — R1 did not re-raise it).

**Settled in earlier rounds and closed here:** the finer-channel direction dispute (R2 withdrew, R1/R3 upheld) and the appendix page-length dispute (R1 withdrew after R3's column count).

## Questions for the Authors

1. Will the §3.3 coverage calibration be added? (Lowest-cost item on the threshold; the apparatus already exists.)
2. Will the abstract be aligned with the body's narrower detector wording, its §4.3 association-not-causation language, and the power/convention/double-null qualifiers?
3. Will the Conclusion summarize the estimator finding the abstract advertises?
4. Will "Both substitutions run in the same direction" be fixed, and "not falsified" unified with the consistency-check framing?
5. Will §2.3's grouping be aligned with §6.2's?
6. Which artifact carries each side of the gate, for the ledger-recomputation claim?
7. Does the venue require each mandatory appendix to start a fresh page?

## Missing References

No missing \cite keys (58 entries, 0 orphan, 0 duplicate); no new references this round. The four long-standing gaps remain closed and CrossRef-verified. The Round 5 "possible ghost reference" flag does not recur — an index-availability artefact, not a ghost. Residual automated-check complaints (2 author fields, 4 brace issues) are contradicted by the rendered PDF and have been diagnosed across rounds as a tool-side stale source — **not manuscript defects** — and should be closed on the .bib side; this is the one item the panel has been unable to verify from its side across four rounds.

## External Review

Not requested (paperreview.ai external review is not enabled for this project).

## Visual Layout Check (non-scoring)

Status: **done**. 0 critical, 5 warning, 7 info (layout items unchanged and non-blocking): Figure 1 under-scaled and no display item before page 3; Figures 2–3 cited on p7 but floating to p10; Table 1's spurious empty column and a quarter-column gap; three short-column endings from float clustering. Positives: no overflow, no clipped figures, no residual LaTeX, references sequential with no unresolved `[?]`, and the body remains exactly 13 pages. R3's full 18-page render this round confirms p15 is a full page with no legend/table overlap.

## Paper Audit & Reference Verification (non-scoring)

- **Paper audit**: compile PASS (18 pages). **The content and visual sub-agents exited abnormally again**, so those layers are **not covered** rather than clean; the audit's five critical findings are folded in above as W3, W6, W7, and two claim-strength items that overlap W3/W9. R3's own full render is the substantive layout coverage.
- **Reference verification**: 58 entries, 0 missing/orphan/duplicate; the ghost flag does not recur; the metadata and author-field complaints remain tool-side.

---

## Overall Assessment

**Verdict: weak accept (4/5), unanimous.** Not acceptable as a clear accept this cycle; fully acceptable as a weak accept.

Six rounds in, the trajectory is clear. Round 1 was a reject on correctness. Rounds 2–5 repaired correctness, positioning, reference coverage, citation integrity, and the ethics gap. **Round 6 closes the last defects**: there is now no desk-reject-level item, no unreproducible claim, no figure contradicting its caption, no mis-cited reference, and no internal artefact in the PDF — each confirmed independently and with render evidence.

What holds the score at 4/5 is not a defect but an absence: the paper still declines the one check that would substantiate its own title term, and it still contains no methodological addition beyond Round 2. The panel has named the cheapest remedy three times — the known-truth apparatus already exists, so a true-TV coverage scan with a dependent-data arm is a bolt-on, not a new method. Absent that, "certification-grade" remains a claim about the upper side's derivation rather than a demonstrated property of the bracket, and the contribution's ceiling stays at the single (M=1, k=5) cell.

The paper the panel is judging is honest, reproducible, and complete about what it does and does not show. Its remaining distance is, as R2 put it, not one that editing can shorten.

**Confidence**: high. The unanimous tier rests on three independent full reads, R3's complete render plus R1's targeted renders, three independent recomputations of the disputed null arithmetic, and two disputes settled by computation and formally withdrawn rather than papered over.

## Detailed Comments

**Abstract.** 340/336 fixed. *Fix:* align the detector claim with §4.4's narrower wording; change "resolves more structure" to match §4.3's association; add the power, convention, and double-null qualifiers.

**Introduction.** The certification-grade definition is now in the first paragraph. *Fix:* six contribution bullets with three tiers of weight weaken the centre of gravity; consider consolidating.

**Measurement Design.** Lemma 1 correct; its statement is loose-but-true (independently verified). *Fix:* the §3.3 coverage calibration; give the binomial test its own symbol; define ε_lo and B at first use; describe the preprocessing pipeline.

**Results.** The §4.4 rewrite is the round's best work; the double-null disclosure is a model. *Fix:* "Both substitutions run in the same direction"; unify "not falsified"; unify the §4.3 statistic name; align §4.2's "significant unmatched"; state which artifact carries each side of the gate.

**Discussion.** §5.6 and the A.1 hash-salting discussion remain intact. *Fix:* give the convention-matched contrast; move the three unlisted limitations into the Limitations block.

**Related Work.** §6.2's three-way split is correct. *Fix:* §2.3 still carries the old grouping.

**Conclusion.** *Fix:* summarize the estimator finding the abstract advertises; carry the lower-side nominal qualifier and the divisibility bound's condition.

**Formatting / Anonymity.** Double-blind intact; body exactly 13 pages; mandatory appendices correctly placed and within their allowances. No remaining desk-visible artefact.

**Ethics / Open Science.** Substantive and balanced; hashes and timestamps verifiable; the explicit non-provision of URLs is venue-acceptable.

*End of consolidated report — Round 6.*