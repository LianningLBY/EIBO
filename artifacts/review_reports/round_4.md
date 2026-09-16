---
round: 4
review_mode: fresh
overall_score: "borderline accept (3.5/5) — reviewers converged on the same tier for the first time; acceptance contingent on closing the consistency and declaration items"
score_value: 3.5
score_max: 5.0
score_label: "borderline accept (3.5/5) — reviewers converged on the same tier for the first time; acceptance contingent on closing the consistency and declaration items"
verdict_canonical: "borderline accept"
verdict_raw: "borderline accept   — reviewers converged on the same tier for the first time; acceptance contingent on closing the consistency and declaration items"
timestamp: 2026-09-16T03:09:36.946849+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Consolidated Review Report — Round 4 (Revised Manuscript)

**Venue**: USENIX Security 2027 (Cycle 2) · **Review round**: 4 · **Reviewers**: 3

**Material fact governing this round:** unlike Rounds 2–3, the submitted PDF **has changed** (SHA-256 differs; 18 pages, ~86,116 characters, +2,257 from Round 3). The Round 3 consolidated report was delivered and converted into 22 action items (RT-W1…W22); this round verifies their execution.

---

## Summary

This is the first round to produce a genuinely revised manuscript, and the first in which all three reviewers land in the same tier. All three Round 3 desk-visible critical items are cleared: the reference-[4] machine residue and its appendix spread, the literal Markdown marker in §5.1, and the mandatory-appendix placement — the last of which now sits before the references and is split into two independent appendices. The title object's dimensional gap, which Reviewer 1 had called the paper's core reporting hole ("the bracket is nowhere characterised"), is closed by a new Table 5 giving the ε_lo and width quantiles. Citation integrity is materially repaired and externally verified: the Chan et al. entry now carries the correct DOI, author order, and pages, and the dataset reference has been rewritten as a canonical Zenodo entry. The novelty boundary was rewritten to declare *which* asymmetry is claimed, cites §3.5, and moved into the Introduction — which resolves Reviewer 2's Round 3 finding. §5.1's conservative-bias claim was corrected with a quantitative counterexample (capping *raises* ε_lo on 38 of 990 pairs, pair 35–49 named).

The remaining work is small in kind but not zero: two of the corrections were not propagated to where readers actually look (Figure 1 still says "joint 0.95" while the text now derives 0.975; Figure 5a's in-box annotation still says "can only weaken" while the text says "in aggregate"), one declaration is missing that determines whether the cross-corpus conservatism argument applies to the primary corpus at all, one undeclared object substitution remains between the detector-validation input channel and the certified channel, and the ethics/dual-use item has not been touched across two rounds.

**One dispute was litigated and settled this round** and is recorded so it is not re-opened: see Reviewer Divergence and R4-W1.

---

## Strengths

1. **The three desk-visible critical defects are gone.** [4]'s residue is cleared from both the bibliography and Appendix A.2b; the literal `**…**` is gone (render-confirmed); the mandatory appendices now precede the references. Reviewer 3 reports **no remaining desk-reject-level item**.
2. **The title object is now characterised.** New Table 5 reports ε_lo (min/p25/median/p75/max = 0.0151/0.3411/0.5548/0.6990/0.9729) and bracket width (0.0139/0.0428/0.0784/0.1119/0.2214), with the statement that no bracket has negative width. This directly answers Round 3's sharpest method objection.
3. **Citation integrity repaired and externally verified.** [4] Chan et al. now carries DOI `…3402.88`, the author order Chan → Diakonikolas → **Paul** Valiant → Gregory Valiant, and pages 1193–1203 — confirmed against CrossRef by Reviewer 2 and from the render by Reviewers 1 and 3. [29] is now the canonical Zenodo dataset entry, verified against its creators. The "cited by the record" residue is fully removed.
4. **The novelty boundary is honestly rewritten.** §1 now states the asymmetry is "one of constant provenance and confidence-level kind rather than provenness" and cites §6.4; §6.4 names "the one in Section 3.5". Reviewer 2's C-1 concern is formally withdrawn as resolved.
5. **The conservative-bias claim was fixed with numbers, not softened.** §5.1 now reads "the direction is aggregate rather than per-pair: capping raises ε_lo on 38 of the 990 pairs, one of them being pair 35–49 (full-n 0.042725 against capped 0.043732)". Reviewer 3 calls this "the rare case of an internal contradiction converted into a quantified, honest statement."
6. **Reproducibility moved from unverifiable to checkable.** All three hashes are now full 64-hex (independently counted by Reviewers 1 and 3) and pre-registration timestamps are given (2026-09-14T09:35:32Z vs 09:36:33Z).
7. **The reference-check divergence is diagnosed as tool-side.** Reviewer 3 walked the rendered bibliography page by page: [27], [28], [29] carry complete author lists, no uncited entry appears, and [31] is an arXiv preprint rather than a CRAN record.

---

## Weaknesses (core)

### Major — corrections not propagated to where readers look

**W1 — Figure 1's confidence label is stale, and §4.4's null rate was not revisited.** The authors adopted the relabel route: Lemma 1's proof now derives "a joint 1−α_law = 0.975 statement". But Figure 1's in-figure label still reads "finite-sample, joint 0.95" (render-confirmed at p3 by Reviewers 1 and 3), and §4.4's null rate is still 5%. **Severity: this is a definition-consistency defect, not a results-changing one** — see Reviewer Divergence for the settled arithmetic. Note also Reviewer 3's precision correction: the Lemma statement "with probability at least 1−α" is *true but not tight* (single-law failure is α′/2), not an inconsistency.

**W2 — Figure 5a's in-figure annotation contradicts its own caption and text.** The box still reads "Capping can only weaken ε_lo, so the bias is CONSERVATIVE" (render-confirmed at p13) while the same page's caption says the cap "lowers ε_lo **in aggregate**" and the text reports the 38-pair counterexample. Found independently by all three reviewers.

**W3 — Appendix A.1b "Endpoint Distributions" is an empty heading**, and its table (Table 5) floats to the top of p15 ahead of the "Appendix: Supplementary Material" heading, while §4.2 refers to it as "Table 5 in the appendix". Heading, table body, and cross-reference all need reconciling. Found independently by all three (R1-N3, R2-G-2, R3-N5).

### Critical — a missing declaration that bears on a load-bearing argument

**W4 — The construction convention behind the headline 336/990 is never declared, and the 20,000-flow cap's corpus attribution is inconsistent across four statements.** §5.1 reports "the cap binds on 2,145 of the 3,321 pairs" (replication corpus) and, in the next sentence without transition, "capping raises ε_lo on 38 of the 990 pairs" (primary corpus). Figure 5a's box presents the cap as a QUIC22 feature; Table 4's caption implies the primary corpus is capped by default; Appendix A.1 implies the headline uses full n. **This determines whether §5.1's "the reported figure is a floor / the bias runs in the conservative direction" applies to the primary corpus at all.** Reviewer 1 independently raises the adjacent question: is the "38 of 990" denominator all pairs or only the cap-bound subset? If the latter, a 38% reversal rate would materially weaken the "aggregate ⇒ conservative" argument. (R3's finding; R1's adjacent point.)

### Critical — an undeclared object substitution

**W5 — The validated detector sees a finer channel than the certified one.** §3.2 gives the alphabet as m = (2M)^k, so at M=1 each axis has one bin and the certified channel is **direction-only**; §4.4 states LightGBM is trained on the k=5 **(direction, size)** feature vector. Reviewer 1 raised this in Round 3; Reviewer 3 calls it "the sharpest of the remaining items" and asks for either an M=1-feature validation arm or an explicit declaration of this second substitution — the paper declares the closed-set/open-set one but not this. (R1, endorsed by R3.)

### Warning — residual overclaims and stale statements

**W6** — The abstract still says "on the 340 pairs where a certificate exists" (certificates exist for 336) and states "no detector breaches the certified floor" without §4.4's own power caveat ("reading 'not falsified' as evidence that the floor is tight would be a mistake").
**W7** — §4.3's new confound sentence ("do not by themselves separate genuine resolution from sparse inflation") is immediately followed by the paragraph that still asserts "A finer alphabet resolves more structure"; and the new sentence's pointer "(Figure 3b,c)" is a category error (the `sat.` column is an M-ladder quantity — Table 1 / Figure 2a — whereas Figure 3b,c varies with k).
**W8** — §4.2 states "no pair reaches TV ≥ 0.99", but the `sat.` column is defined on the plug-in estimate btv. With Table 5 available, ε_lo max = 0.9729 and width min = 0.0139 imply some pair may have ε_hi ≥ 0.9868, so the TV statement is not established by sat = 0.0000.
**W9** — The ethics/dual-use item (RT-W21) is untouched across two rounds: Appendix A.1 and §5.6 are verbatim unchanged, with no balanced statement for the §5.2 separability result and no IP-hash reversibility/salting discussion; A.1 also carries the unqualified "detection performance cannot be improved past" that §3.1 has now scoped.
**W10** — Two structural residuals: §6.4's self-reference still points at its own section, and "beyond the fourth rung" remains an off-by-one (M=8 *is* the fourth rung and is already zero — "at and beyond").
**W11** — Four reference additions remain missing (Bendale & Boult CVPR 2016; Geng/Huang/Chen TPAMI 2020; Sirinam CCS 2018; Rimmer NDSS 2018), confirmed by scanning all 54 entries.
**W12** — Three items carried from Round 3 but never entered the action list: the §3.3 coverage-calibration refusal (its stated reason covers only TV≈0; a truth scan and a dependent-data arm are both feasible), the detector-channel substitution (now W5), and the §4.3 paired-increment/marginal-median disagreement (+0.2931 vs +0.3028, estimator undefined).
**W13** — The Appendix's provenance section still carries no clickable URLs (access deferred to the submission-system channel) — the one unresolved sub-item of RT-W19.

---

## Reviewer Consensus

- **[AGREE] The three desk-visible critical defects are cleared**, including the appendix reordering — verified independently by all three reviewers, and Reviewer 2 formally withdrew its Round 1 rebuttal on that item.
- **[AGREE] Table 5 closes the "title object is not characterised" gap.**
- **[AGREE] The citation repairs are correct and externally verifiable** (CrossRef- and Zenodo-verified).
- **[AGREE] The novelty-boundary rewrite resolves C-1**; Reviewer 2 adds the honest bookkeeping that the fix *narrows* the original claim.
- **[AGREE] Figure 1's stale 0.95, Figure 5a's stale in-box annotation, and the empty A.1b heading are real and must be closed** — all three found each item independently.
- **[AGREE] No desk-reject-level item remains.** (The one open judgement call is whether each mandatory appendix must start its own page; Reviewer 3 flags it, Reviewers 1 and 2 do not treat it as a defect.)

## Reviewer Divergence

**Settled this round — whether the 0.975 relabel forces §4.4's null to 2.5% and changes any verdict.** Reviewer 3 initially argued that at a 2.5% null the strongest cell (10/340) would become significant and the "no cell rejects the null" conclusion would need recomputation. **Reviewer 1 rebutted with an explicit computation**: at null 2.5%, n=340, that cell gives μ=8.5, σ=2.879, continuity-corrected z=0.347, one-sided **p ≈ 0.36**; the 8-violation cells p ≈ 0.61; the rest p ≥ 0.97 — **no cell rejects at either null**. Reviewer 3 independently reproduced these values and **withdrew its claim**, further correcting its own direction error (lowering the null *lowers* p-values and improves, not worsens, power). **Panel position: the 5%/0.975 mismatch is a definition-consistency defect that changes no result.** Reviewer 3 also withdrew, on re-derivation, the suggestion that the Lemma statement's "≥1−α" is inconsistent — it is true-but-not-tight.

Other divergences are matters of scope, not conflict: Reviewer 1 reaches for Accept on closing five named items; Reviewers 2 and 3 sit at 3.5/5. **All three now fall in the borderline-accept band — the first agreement in four rounds.**

## Questions for the Authors

1. Which convention computes the headline 336/990 — capped or full-n ε_lo? Give the primary corpus's cap-bound pair count and separate the two corpora's statements.
2. Is the "38 of 990" denominator all pairs or the cap-bound subset?
3. Was the validation detector trained on the M=1 (direction-only) channel or on (direction, size)? If the latter, is this second substitution acknowledged?
4. Why was the 5% null pre-registered, and does it depend on the 0.95/0.975 question?
5. Will the ethics appendix be given the balanced dual-use and hash-reversibility statement?
6. Will each mandatory appendix start its own page?

## Missing References

No missing \cite keys (54 entries, 0 orphan, 0 duplicate). Still absent (Reviewer 2's finding, confirmed by Reviewer 3):
- **Bendale & Boult**, "Towards Open Set Deep Networks" (CVPR 2016) — the canonical deep-OSR reference.
- **Geng, Huang, Chen**, "Recent Advances in Open Set Recognition: A Survey" (TPAMI 2020).
- **Sirinam et al.**, "Deep Fingerprinting" (CCS 2018) and **Rimmer et al.**, "Automated Website Fingerprinting through Deep Learning" (NDSS 2018).
The two additions this round (Athanasiou QIF; Mücke "Waiting for QUIC") are correct and well-placed, and the Chan et al. and dataset entries are now externally verified.

## External Review

Not requested (paperreview.ai external review is not enabled for this project).

## Visual Layout Check (non-scoring)

Status: **done**. 0 critical, 5 warning, 7 info.
- **Figure 1, the paper's only architectural schematic, is under-scaled** (single narrow column, ~a quarter of column height, non-uniform box type sizes) and no display item appears before page 3 — promoting it to a full-width `figure*` near its first reference would fix both.
- **Figures 2 and 3 are first cited on p7 but float to p10** — a three-page drift across the section break.
- **Table 1 leaves a quarter-column blank block beneath its left half and carries a spurious empty column** (`probe` and `sup_flip` are printed as separate columns with no data path between them).
- Three short-column endings in the back half (p6, p11) driven by float clustering.
- Positives: no overflow, no clipped figures, no garbled equations or residual LaTeX; booktabs tables with consistent precision and best-value bolding; references [1]–[54] sequential with no `[?]`; Figure 5 survives grayscale.

## Paper Audit & Reference Verification (non-scoring)

- **Paper audit**: compile **PASS** (18 pages, exit 0; 4 critical, 80 warning, 12 info). The audit's criticals overlap W4/W6 and add: the Discussion's deep-matched stratification intervals (e.g. −15.5 [−28.4,−2.9]) are supported by a "stratification table" that appears nowhere in the paper or appendix; and the channel-sensitivity dose-response and the missing-service mass are quoted without any display item. The visual sub-agent exited abnormally again, so the layout layer rests on the dedicated visual check.
- **Reference verification**: 54 entries, 0 missing/orphan/duplicate; 13 metadata mismatches; 2 missing author fields and 4 brace issues that the rendered PDF contradicts (W20's diagnosis: a stale tool-side source).

---

## Overall Assessment

**Verdict: borderline accept (3.5/5).** For the first time the three reviewers agree on the tier. **Acceptance is contingent on closing the consistency and declaration items (W1–W5), not on new science.**

Round 1 was a reject on correctness; Rounds 2–3 fixed the correctness and then stalled on unclosed editorial work. Round 4 is the round in which that work was actually done: the desk-visible defects are gone, the title object is characterised, the citations are externally verifiable, the novelty boundary is honest, and the conservative-bias claim is now quantified rather than asserted. Every reviewer independently confirmed these.

The remaining items divide cleanly:
- **Propagation** (W1–W3): two figure annotations and one empty heading — minutes of work, but they sit exactly where a reviewer looks, and a figure that contradicts its own caption is worse than a caption that contradicts the text.
- **Declaration** (W4–W5): one sentence each, but they are load-bearing. W4 decides whether the cross-corpus conservatism argument applies to the primary corpus; W5 decides whether the detector validation tests the channel the paper certifies.
- **Substance** (W6–W13): the ethics/dual-use item, the four missing references, the coverage calibration, the §4.3 estimator definition, and the stratification table that the Discussion promises but does not deliver.

None of these is a design failure, and none requires new experiments except the optional coverage calibration. Closing W1–W5 would move this to a clear accept; the substance group does not block acceptance but should be closed before camera-ready.

**Confidence**: high. The panel's agreement is backed by three independent full reads, two rendering passes that counted the hashes character by character, external verification of the repaired citations, and a disputed statistical claim that was computed twice and settled by withdrawal rather than by seniority.

## Detailed Comments

**Abstract.** Detector sentence now carries the correct rates. *Fix:* "340 pairs where a certificate exists" → 336, and carry §4.4's power caveat (W6). Abstract remains ~330 words, above the venue norm.

**Introduction.** Contributions now number six, with the confound demo as Contribution 5 and the novelty boundary in place. *Fix:* move the "certification-grade" definition from the third paragraph to the first.

**Measurement Design.** Lemma 1 derives 0.975 correctly. *Fix:* align Figure 1's label (W1) and document the 5% null's provenance; add the coverage calibration (W12).

**Results.** Table 5 closes the ε_lo gap; §5.1's 38-pair counterexample is a model of honest correction. *Fix:* declare the headline's cap convention (W4); reconcile §4.3's confound sentence with its next paragraph (W7); fix the `sat.`/TV wording (W8); define the increment estimator (W12).

**Discussion.** The sensitivity and missing-mass results still lack any display item; the deep-matched intervals rest on an undisclosed stratification table.

**Related Work.** §6.2's three-way grouping is now correct. *Fix:* the §6.4 self-reference (W10); add the four missing references (W11).

**Conclusion.** Closes on the pairwise object. *Fix:* "beyond the fourth rung" → "at and beyond" (W10).

**Formatting / Anonymity.** Double-blind intact; body exactly 13 pages; mandatory appendices correctly placed. Two stale figure labels (W1–W2) and one empty heading (W3) are the remaining visible items.

**Ethics / Open Science.** Open Science is now substantially verifiable (full hashes, timestamps); the missing URLs are the last sub-item. Ethics remains untouched (W9).

*End of consolidated report — Round 4.*