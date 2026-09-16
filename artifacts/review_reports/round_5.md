---
round: 5
review_mode: fresh
overall_score: "weak accept (4/5, conditional) — panel converged; one hard pre-submission gate plus editorial and optional substantive items"
score_value: 4.0
score_max: 5.0
score_label: "weak accept (4/5, conditional) — panel converged; one hard pre-submission gate plus editorial and optional substantive items"
verdict_canonical: "weak accept"
verdict_raw: "weak accept  , conditional) — panel converged; one hard pre-submission gate plus editorial and optional substantive items"
timestamp: 2026-09-16T04:49:52.121943+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Consolidated Review Report — Round 5 (Revised Manuscript)

**Venue**: USENIX Security 2027 (Cycle 2) · **Review round**: 5 · **Reviewers**: 3

**Material facts.** The PDF has changed again (19 pages, SHA-256 `5129416e…`; Round 4 was 18 pages). The Round 4 report was delivered and its residuals became action items. **The body is still exactly 13 pages — the extra page is entirely in the appendix area, and it is a blank one (W3).** Reviewer 2's cross-response lane did not return text this round; its **independent** review and its CrossRef citation addendum are fully incorporated, and the two content questions it raised are adjudicated below. The panel is unanimous on the tier: **4/5**.

---

## Summary

This is the round in which the paper's editorial debt was paid and the panel converges. Every Round 4 item that was a *defect* is closed: Figure 1's label now reads 0.975 and matches Lemma 1; Figure 5a's in-box annotation says "in aggregate"; the empty A.1b heading is gone with Table 5 cited; §4.1 declares which construction convention produces the headline 336/990 and separates the two corpora; §4.3 defines the increment estimator; §6.4's self-reference and the "fourth rung" off-by-one are fixed. After three rounds untouched, the ethics gap is closed: §5.6 is now "Dual-use considerations" and Appendix A.1 discusses hash reversibility and salting. The four references Reviewer 2 had requested across two rounds are in, woven into the argument, and CrossRef-verified.

The round also introduced **two desk-visible defects** — one of which the panel treats as the single hard gate — and two substantive disputes were litigated and settled by explicit computation. The scientific core is unchanged and remains sound; the novelty rating remains "incremental" for the fifth round.

---

## Strengths

1. **The Round 4 defect list is closed.** Verified across three reviewers with render evidence where visual: Figure 1 → 0.975, Figure 5a → "in aggregate", A.1b heading deleted, §4.3's confound pointer fixed to "Table 1 / Figure 2a", §4.2's `sat.`/`btv` wording, §6.4 self-reference, "at and beyond the fourth rung", and the §4.3 estimator definition.
2. **The construction declaration is complete and arithmetically verified.** §4.1: the headline uses the full-n convention; the capped variant gives 335/990 with pair (21,23) the sole difference; the primary corpus's cap binds on 814/990; capping raises ε_lo on 38 pairs (4.7% of the bound subset, 3.8% of all 990) and lowers it on 776. Reviewers 1 and 3 independently verified 776 + 38 = 814.
3. **The ethics gap is closed after three rounds untouched.** §5.6 "Dual-use considerations" ("The bracket is simultaneously an auditing instrument and a map; it shows an operator which pairs are near the detection limit and an adversary which are cheap to distinguish"), and A.1's salting discussion ("Hashing is not anonymization where the address space is enumerable…"), plus the "pairwise" qualifier in A.1.
4. **The four long-missing references are in and integrated.** Bendale & Boult [3], Geng et al. [17], Sirinam et al. [44], Rimmer et al. [40] — woven into the argument ("both report accuracy-style metrics, so neither bounds what the channel permits") and CrossRef-verified by Reviewer 2.
5. **Two prior criticisms became empirically checkable** through this round's disclosures (the convention accounting; the estimator definition), and both check out.
6. **The reference-integrity picture is clear.** Reviewer 3's page-by-page walk of the rendered bibliography shows complete author lists, no orphans, and michel2020high as an arXiv preprint rather than a CRAN record — confirming the automated check's residual complaints as a tool-side stale source, not a manuscript defect.

---

## Weaknesses (core)

### Critical — the single hard pre-submission gate

**W1 — Table 2's footnote contains an internal review-process reference.** p9, footnote 1 closes: "No cell rejects at either rate (**see the settled computation in the review record**)." This is the same class as the Round 1 critical bibliography residue: an internal-workflow artefact inside the submitted PDF. It does not break anonymity (no identifying information) and does not falsify any claim, but it exposes that the paper has been through review and is meaningless to a reader. Found independently by Reviewers 1 and 3 (render-confirmed, single occurrence; Reviewer 2 did not report it). Both call it a pre-submission must-delete; Reviewer 3 proposes it as the panel's one hard gate.

### Major — a reversed direction claim that must be rewritten

**W2 — §4.4's parenthesis on the finer-channel validation is written backwards.** The new paragraph correctly *declares* the second object substitution (detector features are k=5 raw direction bits plus log packet sizes, 10 dimensions, strictly finer than the m = 32 single-cell alphabet). It then says "both run in the same direction (**the validated object is harder to detect on than the certified one**)." By the data-processing inequality TV_coarse ≤ TV_fine, the finer object's floor is lower, so it is **easier** to breach, and a non-breach there is the **stronger** statement. Reviewers 1 and 3 independently call it backwards; Reviewer 3 supplies a minimal counterexample (coarse alphabet TV = 0 against a refinement with TV = 1: the coarse channel's minimum error clears the floor while the fine one's does not). See Reviewer Divergence, Dispute 1, which also settles Reviewer 2's competing claim.

### Major — a layout regression

**W3 — p15 is ≈90% blank** (8 lines of "Data." only). Found by Reviewer 1 (render-confirmed) and inferred independently by Reviewer 2 from the text layer. New this round, and the entire source of the 18→19 page growth. **Settled sub-dispute:** Reviewer 1 initially paired this with an "Open Science exceeds 1 page" claim; Reviewer 3 rebutted with a column-by-column count (Ethics ≈0.43 page, Open Science ≈0.63 page) and **Reviewer 1 withdrew the page-limit claim**. The allowance is compliant; the defect is wasted space, caused by Tables 4/5 floating late. Fix by moving the tables, not by cutting Open Science.

### Major — still open from Round 3/4

**W4 — The abstract still says "on the 340 pairs where a certificate exists."** Three reviewers flag it independently, and the error is now *more* visible because §4.1 discloses the capped variant at 335 — so three numbers coexist (336 full-n headline / 335 capped / 340 upper-side-only). It also omits §4.4's own power caveat. Fix: "the 340 pairs whose upper side certifies", plus the caveat.

**W5 — The new §4.4 footnote's "the 5% null is therefore the stricter direction" is ambiguous or reversed.** At a 0.975 joint level the corresponding expected violation rate is 2.5%, under which the bar is higher, so 5% is the more **lenient** side. With the strongest cell observed at 10/340 = 2.94%, the margin against a 2.5% null is much smaller than against 5%. (Reviewer 3, within its significance-disclosure remit.) The panel agrees no cell rejects at either null (strongest cell p ≈ 0.3–0.36). Fix: give the p-values under both nulls, or state the convention plainly.

**W6 — §3.3 still declines a coverage calibration** with a reason covering only the TV ≈ 0 degenerate case. A truth-scan over TV ∈ (0, 0.5) and a dependent-data arm are both feasible and would directly test the paper's own declared i.i.d. threat. (Reviewer 1, carried since Round 3.)

### Minor

**W7** — The "certification-grade" definition still sits in §1's third paragraph rather than the first; the cross-corpus comparison pairs the primary's full-n 33.9% against QUIC22's capped 15.75% without a convention-match rationale; the abstract does not mention the convention dependence.
**W8** — Three optional strengthening notes (Reviewer 1): the cap never admits a pair the full-n bound rejects (a monotone set-level statement, 340 → 335, stronger than the per-pair "38 rise"); pair (21,23) — the sole convention difference — is absent from Table 4; §4.3 calls one statistic two names.
**W9** — "significant unmatched" phrasing persists; the Table 2 null and the 2.9604 constant are explained only in the footnote.

---

## Reviewer Consensus

- **[AGREE] Every Round 4 defect is closed**, verified independently by all three with render evidence where visual.
- **[AGREE] The four reference additions are correct, complete, integrated, and CrossRef-verified.**
- **[AGREE] The ethics/dual-use gap is closed.**
- **[AGREE] W1 (the footnote's internal reference) and W3 (the blank page) are real and were found independently; W1 is a pre-submission must-delete.**
- **[AGREE] W2 (the reversed direction parenthesis) must be rewritten.**
- **[AGREE] W4 (abstract 340/336) is still open after three rounds.**
- **[AGREE] The novelty rating remains "incremental"; editorial cleanup cannot reach clear accept.**

## Reviewer Divergence

**Dispute 1 — settled: the finer-channel validation direction.** Reviewer 2 argued that because a finer observable has a lower information-theoretic floor, "no breach" on it does not strengthen the coarse-channel certificate, so the validation's evidence power is *weakened*. **Reviewers 1 and 3 both rebut; Reviewer 2's conclusion does not survive.** TV_coarse ≤ TV_fine means the finer channel's floor is lower, so it is *easier* to breach, and a non-breach there is the *stronger* statement — an easier test passed. Reviewer 3 adds the minimal counterexample and identifies the real issue: a breach on the finer channel does **not** falsify the coarse-channel certificate, so the validation is a **consistency check, not a falsifiable test** — the framing that answers both Reviewer 1's objection and Reviewer 2's underlying concern.

**Dispute 2 — settled: Open Science page length.** Reviewer 1 read ≈1.05 pages (over the allowance); Reviewer 3's column count gives ≈0.63 page, and **Reviewer 1 withdrew**. The allowance is compliant; only the blank page remains.

**Score convergence.** Reviewer 1 moved 3.5 → **4/5** ("my 3.5 anchor was the hygiene signal of a recurring critical-class defect; I now record it as a must-clear list rather than a deduction"); Reviewer 2 **4/5**; Reviewer 3 **4/5**, all conditional. **Panel position: 4/5 (weak accept, conditional). No reviewer holds a different tier.** Reviewer 2's H-2 was withdrawn in substance; its residual concern survives as the non-falsifiability framing above.

## Questions for the Authors

1. Will the "see the settled computation in the review record" clause be deleted? (Hard gate.)
2. Will the §4.4 parenthesis be rewritten to "easier to detect, so a non-breach is the stronger statement", with the non-falsifiability caveat?
3. Will Tables 4/5 be moved so p15 consolidates?
4. Will the abstract's "340 pairs where a certificate exists" become 336, with the power caveat?
5. Which null convention is used, and what are the p-values under both?
6. Will the coverage calibration be added?

## Missing References

No missing \cite keys (58 entries, 0 orphan, 0 duplicate). **The four long-standing gaps are closed**, and all additions are CrossRef-verified: Bendale & Boult (CVPR 2016, pp. 1563–1572), Geng/Huang/Chen (TPAMI 43(10):3614–3631), Sirinam et al. (CCS 2018, pp. 1928–1943), Rimmer et al. (NDSS 2018).

## External Review

Not requested (paperreview.ai external review is not enabled for this project).

## Visual Layout Check (non-scoring)

Status: **done**. 0 critical, 5 warning, 7 info.
- **Figure 1, the paper's only architectural schematic, is under-scaled** (single narrow column, ≈a quarter of column height, non-uniform box type sizes); no display item appears before page 3. Promoting it to a full-width `figure*` would fix both.
- **Figures 2 and 3 are first cited on p7 but float to p10** — a three-page drift across the section break.
- **Table 1 leaves a quarter-column blank beneath its left half and carries a spurious empty column** (`probe` and `sup_flip` printed as separate columns with no data path between them).
- Three short-column endings in the back half, driven by float clustering.
- **Positives:** no overflow, no clipped figures, no garbled equations, no residual LaTeX markup; booktabs tables with consistent precision and best-value bolding; references sequential with no unresolved `[?]`; Figure 5 survives grayscale; **the body remains exactly 13 pages**.

## Paper Audit & Reference Verification (non-scoring)

- **Paper audit**: compile **PASS** (19 pages). **Both the content and visual sub-agents exited abnormally this round**, so no content-level or layout-level audit findings were produced — treat those layers as **not covered**, not clean. The deterministic check reports 1 source-level critical (an Overfull `\hbox` 8.5 pt too wide at lines 201–209) and 10 uncited bibliography keys.
- **Reference verification**: 58 entries (up from 54 — the four additions), 0 missing/orphan/duplicate; 13–14 metadata mismatches; 2 missing author fields and 4 brace issues **contradicted by the rendered PDF** (tool-side stale source, per Reviewer 3's page-by-page walk). One entry (garov2025closer) is flagged "not found online" — consistent with an unindexed preprint rather than a ghost reference; no reviewer surfaced a ghost-reference finding on inspection.

---

## Overall Assessment

**Verdict: weak accept (4/5) — conditional.** All three reviewers converged on this tier (Round 4's 3.5 was also unanimous; this round moves all three to 4/5).

This is the round in which the editorial debt was paid. The Round 4 defect list is closed; the ethics gap that survived three rounds is closed; and the reference coverage — the one place the paper had a genuine *gap* rather than a wording problem — is now complete and externally verified. Two disclosures added this round made two earlier criticisms checkable, and both check out.

What remains divides cleanly. One item is a **hard gate**: an internal review-process reference inside the submitted PDF, the same class of artefact that was a Round 1 critical; removing it is a one-line edit and is the difference between a paper that reads as submission-ready and one that reads as a working document. Two items are **rewrites**: the reversed direction parenthesis (with the consistency-check framing that also answers Reviewer 2's concern) and the abstract's 340/336 with the power caveat. One is a **layout** fix (move the tables; do not cut Open Science). One is a **long-standing method gap** the panel has carried since Round 3: no coverage calibration against known-truth TV, which would directly test the i.i.d. threat the paper itself declares.

The clear-accept threshold, stated by all three reviewers, is unchanged and is **not editorial**: one substantive methodological addition — most cost-effectively a finite-sample two-sided lower bound built from the closeness-testing references the paper already cites (Chan, Diakonikolas), which would simultaneously dissolve the entire "certificate" versus mixed-strength tension. Absent that, the contribution is honestly scoped and its ceiling is the single (M=1, k=5) cell. That is a respectable weak accept at this venue; it is not a clear accept.

**Confidence**: high. The tier convergence rests on three independent full reads, two render passes, CrossRef verification of both the repaired and the added citations, and two disputes settled by explicit computation (one with a counterexample) rather than by assertion.

## Detailed Comments

**Abstract.** Detector sentence carries correct violation and null rates. *Fix:* "340 pairs where a certificate exists" → 336, plus the power caveat (W4); add a clause on the convention dependence (W7).

**Introduction.** Contributions number six, with the confound demo as Contribution 5 and the novelty boundary in place. *Fix:* move the certification-grade definition to the first paragraph (W7).

**Measurement Design.** Lemma 1 and Figure 1 now agree at 0.975. *Fix:* the footnote's "stricter direction" wording (W5); the coverage calibration (W6); the two names for one statistic (W8).

**Results.** The convention accounting and the estimator definition are model disclosures. *Fix:* rewrite the §4.4 direction parenthesis (W2); align the abstract (W4).

**Discussion.** §5.6 "Dual-use considerations" and the hash-salting discussion close a three-round gap.

**Related Work.** The four additions are well integrated; §6.4's self-reference is fixed.

**Conclusion.** Consistent with the body.

**Formatting / Anonymity.** Double-blind intact; body exactly 13 pages; mandatory appendices correctly placed and within their allowances. **The footnote's internal reference (W1) is the one blocker**; the blank p15 (W3) is next.

**Ethics / Open Science.** Now substantive and balanced. The explicit "no URLs to preserve double-blind integrity" statement is venue-acceptable, with one low-severity note for the Director about the Round 1 brief's phrasing.

*End of consolidated report — Round 5.*