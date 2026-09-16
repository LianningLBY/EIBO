---
round: 3
review_mode: fresh
overall_score: "weak reject (borderline; reviewers converge on 3/5, with one dissent at 2.5/5 — not acceptable in current form)"
score_value: 3.0
score_max: 5.0
score_label: "weak reject (borderline; reviewers converge on 3/5, with one dissent at 2.5/5 — not acceptable in current form)"
verdict_canonical: "weak reject"
verdict_raw: "weak reject (borderline; reviewers converge on , with one dissent at — not acceptable in current form)"
timestamp: 2026-09-15T20:12:46.954306+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Consolidated Review Report — Round 3

**Venue**: USENIX Security 2027 (Cycle 2) · **Review round**: 3 · **Reviewers**: 3 (method/experiment · novelty/related-work · format/ethics/reproducibility)

**Material fact governing this round:** the submitted PDF is **byte-identical to the Round 2 submission** (same SHA-256, same 18 pages). Nothing was revised between rounds. Every Round 2 finding therefore reproduces by construction, and the Round 2 consolidated report was not delivered to the Research Director (platform fault), so the authors had no round's report to act on. Both facts are stated up front because they frame how the disposition below should be read.

---

## Summary

The paper computes a two-sided ε-indistinguishability bracket per service pair on real QUIC traffic, makes the guarantee asymmetry its object of study, and reports a negative estimator result. Round 1's correctness cluster was substantively repaired in the Round 2 revision (Lemma 1 with proof, the asymmetry reframed at a nominal level, the open-set claim rescoped to pairwise, a service-cluster bootstrap for the headline). Round 3 is a **zero-change re-submission**: the same bytes, so the same state.

All three reviewers independently re-read the full manuscript and reconfirmed both halves of the picture. The **scientific core still stands**: Lemma 1's derivation is correct on independent re-derivation, the nominal-level reframe is honest, the pairwise repositioning is thorough, the cluster bootstrap is right, and §5.1's voluntary downgrade of its own favourable claim remains the revision's best feature. And the **defect list reproduces intact**: two desk-visible artifacts, one arithmetic label mismatch that determines whether the headline moves, one table row that contradicts the claim it supports, three unexecuted positional fixes, and — newly confirmed this round — a mandatory-appendix placement violation.

The net disposition is unchanged from Round 2 and the paper is **not acceptable in its current form**, but for a reason worth stating precisely: not because the science regressed (it did not), but because the revision's remaining work is visible, enumerated, and unclosed, and a third submission carrying the same two desk-visible defects cannot advance.

---

## Strengths

1. **Lemma 1 is correct.** Reviewer 1 rederived the full chain independently (triangle inequality → Jensen/Cauchy–Schwarz → E‖P−P̂‖₁ ≤ √(m/n) → McDiarmid); all three reviewers reconfirmed it in Round 3. The DKW→ℓ1 self-correction is precise, and the i.i.d. assumption is declared as a *threat* with the error direction stated correctly.
2. **The asymmetry reframe is honest.** §3.4 ("high probability at a nominal level"), §3.5 ("Where the two sides differ"), and §1 ("a statement about this construction rather than about what is provable") retract the impossibility claim cleanly.
3. **A voluntary self-correction of a favourable result.** §5.1 *withdraws* the Round 1 "narrows to 9.7 points" and replaces it with "not statistically resolved at matched evidence." Reviewer 2 calls this the revision's most confidence-building change; it survives into Round 3.
4. **The headline carries a correct uncertainty interval.** The service-cluster bootstrap (33.9% → [26.5%, 43.1%]) resamples at the *service* level, correctly treating the 990 pairs as the complete graph on 45 services.
5. **Citation coverage is now a strength.** The four added clusters (DP/geo-indistinguishability, traffic morphing/Tamaraw/Juarez, sparse-bias, randomized smoothing) are present and well placed; the Paninski/Nemenman delimitation ("a limits result rather than a remedy") is the right self-positioning for C3.
6. **The negative result has real content.** The heterogeneous-i.i.d. confound demonstration (a zero-within-flow-dependence null reproduces the Markov vote 45/45, so the vote is not diagnostic) and the quantified data cost (0.608 at k=30) are non-trivial and checkable.

---

## Weaknesses (core)

### Critical — desk-visible, found independently by all three reviewers

**W1 — Reference [4]'s machine-residue author field remains and has spread into the appendix.** [4] still reads `CESNET and associated paper cited by the record: Jan Mücke et al.`, and Appendix A.2b replicates the same broken phrase in body text (render-confirmed at p14 and p17). This is the citation carrying the headline 33.9% corpus. The sibling annotations in [30][32][38][44] were cleared, so the cleanup was partial. **Reviewer 1 found the canonical replacement** the authors can drop in: Mücke et al., "Waiting for QUIC…", Proc. ACM Netw. 3, CoNEXT4, Art. 41, 2025, DOI 10.1145/3768988.

**W2 — A literal unrendered Markdown bold marker appears in the compiled PDF.** §5.1 contains `**all of which include zero**` (render-confirmed at p10 by Reviewers 1 and 3). Note the evidence conflict: the automated visual check reported "no leftover LaTeX markup," while the two direct render inspections see it. Weight the direct inspections. This is a newly written sentence from the revision — an editing accident introduced *by* the fix.

**W3 — The mandatory appendices are positioned after the references, and Open Science exceeds its page allowance.** The verified requirement is that Ethical Considerations (mandatory) and Open Science each occupy ≤1 page immediately after the body and **before** the references. The paper places both at p17–18, after references at p14–16; merges them with optional material into a single block; and A.3 Open Science runs ~1.1–1.2 pages. Reviewers 1 and 3 confirmed the placement violation independently; **Reviewer 2 confirmed it and formally corrected its own Round 1 rebuttal** (it had called post-reference placement conventional — that rebuttal is withdrawn and should not be credited). Reviewer 3 judges this the one item that could trigger a desk rejection; Reviewer 1 holds that severity depends on whether pre-check treats it as binding.

### Critical — the arithmetic that determines whether the headline moves

**W4 — The upper side's stated joint level and its radius constant are not reconciled.** With α_law declared per-law and radius √(2 ln(2/α_law)/n), the two-law union gives 1 − α_law = **0.975**, not the stated 0.95. The radius is correctly calibrated to 0.975, so 0.95 is a *conservative understatement* — Reviewer 2 originally graded this critical, then retracted after deriving Σcᵢ² = 4/n, and that retraction stands. **But Reviewer 1 and Reviewer 3 both stress it is not merely a label problem:** the preferred fix (radius → ln(1/α_law)) *shrinks* the radius, lowers ε_hi, and would **raise 340/336** — so Table 1 must be recomputed, not relabelled. Reviewer 3 adds the decisive constraint: the alternative (relabel to 0.975) would force §4.4's null from 5% to 2.5%, worsening an already near-zero-power detector test. **The ln(1/α_law) route is the only one with no knock-on changes, and it moves the headline upward in the authors' favour.**

**W5 — Table 4's row 35–49 contradicts the conservative-bias monotonicity claim.** Capped ε_lo = 0.043732 exceeds the full-n value 0.042725, while §5.1 and Figure 5a assert the cap "can only shrink ε_lo / the bias is CONSERVATIVE" — the claim the cross-corpus argument rests on. Found independently by Reviewers 1 and 3; render-confirmed. The paper audits suggests the two columns may simply be swapped for that row — a useful repair lead. Magnitude ~0.001; it does not change that pair's gate verdict.

**W6 — The paper never reports the distribution of ε_lo or the width of the certified bracket.** Reviewer 1's finding, endorsed by Reviewer 3: only pass rates (986/990, 0.9960/0.9967) and the four near-threshold values in Table 4 (0.015–0.044) are given; the other 982 pairs' ε_lo margins are never shown. **The content of the paper's title object — the bracket — is nowhere characterised.** Reviewer 3 notes this is the same class of gap as the truncated hashes: the artifact of record, with its ε_lo column, is never exhibited.

**W7 — The novelty boundary's own support is in tension with the revised body (reviewer divergence).** §6.4 claims priority on "asymmetric guarantee strength." §1 now says the two sides "differ in construction and in tightness, not in whether a guarantee is available." Reviewer 2 (Round 3's top finding, joined by Reviewer 1) reads this as the novelty argument's load-bearing property having been abandoned by the paper's own revision, and says a relocation cannot fix it — the paragraph must be rewritten. **Reviewer 3 rebuts this reading:** the withdrawn claim was *existence* of a guarantee (proven vs unproven), whereas §3.5 retains a *kind* asymmetry (finite-sample-exact vs asymptotically-derived-nominal), and §6.4's phrasing maps onto the latter. Reviewer 3 agrees the wording is tense across the two senses and asks for one aligning sentence, but calls "the novel claim cannot stand" too heavy. **The panel's reading: a real wording defect that must be aligned; whether it is a rewrite or a one-sentence fix depends on which asymmetry the authors intended to claim.** See Reviewer Divergence.

**W8 — Intro contribution 4 overstates the cross-corpus result against §5.1.** It says the upper side's difference is "explained, and disclosed, by sample-size stratification," while §5.1 concludes the residual gap "is not statistically resolved." Found independently by Reviewer 1 and the paper audit; same class as W7 (a claim sentence not synchronized with the revised body).

### Major — unexecuted positional fixes

**W9 — Three promised fixes were not executed** (flagged in Round 2, still absent): the heterogeneous-i.i.d. confound demonstration was not promoted into Contributions (it appears in none of the five); "certification-grade" is not defined in the first paragraph; the novelty boundary was not moved into the Introduction.

### Major — assertion strength and confounds

**W10 — §5.1 still contradicts itself.** It retains "a construction agreeing only by accident would not hold to three decimal places" while a newly added sentence in the same subsection concedes "the lower side is saturated, so it reproduces across corpora under either construction." The second is correct.

**W11 — §4.3's "a finer alphabet resolves more structure" remains confounded.** The paired-increment test settles significance but not the sparse-inflation confound (btv on an exponentially growing alphabet at fixed n; the `sat.` column rising 0.000→0.391 is the tell). Reviewer 1 and Reviewer 2 both flag it.

**W12 — §4.2's closing direction word is inverted.** "Falls to zero as the alphabet **coarsens**" describes the column falling as the alphabet is *refined* — contradicting the mechanism paragraph directly below it. Found by the paper audit; **missed by all three reviewers across three rounds.**

### Should-fix

- **W13** — §4.4's closing detector paragraph is duplicated verbatim (all three reviewers, render-confirmed at p8).
- **W14** — The abstract/Intro detector sentence ("no detector … breaches the certified floor above the null rate") is ambiguous or inverted against Results (violation rates 0.6–2.9% sit *below* the 5% null). Found by the paper audit; needs a rewrite.
- **W15** — Figure 1's in-figure labels ("finite-sample strictly valid"/"asymptotic") contradict the revised caption and §3.5.
- **W16** — §6.2's "Kolmogorov–Smirnov family" grouping wrongly includes closeness-testing refs [5] and [11], contradicting §3.3's own careful wording.
- **W17** — [5]'s citation has a wrong DOI (.86 → an unrelated chapter; correct .88), reversed author order (should be Chan, Diakonikolas, **Paul** Valiant, Gregory Valiant), and missing pages (1193–1203). Independently confirmed by Reviewers 2 and 3 via web verification and by Reviewer 1.
- **W18** — §6.4's self-reference is broken; Contributions entry 2 still says "certifiable set … beyond the fourth rung"; §5.2's text stops at B=256 while Figure 4's axis runs to 65536.
- **W19** — Reproducibility remains unverifiable as written: the provenance hashes are truncated to 16 hex characters while the field is `content_sha256`; the pre-registration timestamps are not given; the appendix carries no URLs.
- **W20** — A reference-check divergence is unresolved: the automated check reports 2 missing author fields, 10 orphan entries, and a CRAN resolution for [31], none of which reproduce in the rendered PDF. This must be diagnosed (working-tree .bib vs. the one that built the PDF, or a stale build) before reference verification can converge.
- **W21** — §5.2's dual-use result still has a purely defensive ethics statement, with no IP-hash reversibility/salting discussion.
- **W22** — p17's provenance bullets stretch word spacing badly (long unbreakable tokens), degrading that column.

---

## Reviewer Consensus

- **[AGREE] The scientific core (Lemma 1, nominal-level reframe, pairwise repositioning, cluster bootstrap, §5.1's self-downgrade) survives Round 3 intact.**
- **[AGREE] W1, W2, W5, W13 are genuine and were found independently by two or three reviewers**; W1 and W2 are desk-visible.
- **[AGREE] W3 (appendix placement) is a real violation** — confirmed by all three, with Reviewer 2 formally withdrawing its earlier contrary position.
- **[AGREE] W4's arithmetic is settled** (radius ↔ 0.975; the 0.95 label is conservative), and the preferred repair is the ln(1/α_law) radius, which raises the headline.
- **[AGREE] Round 3 changed nothing, and the paper is not acceptable in its current form** — with the caveat that the zero-change is not the authors' fault (the Round 2 report was never delivered to them).

## Reviewer Divergence

1. **W7 (novelty boundary).** Reviewer 2 (joined by Reviewer 1) reads the boundary's support as removed by the authors' own reframe and requires a rewrite. Reviewer 3 rebuts: a *kind* asymmetry (exact vs nominal) survives, so the claim is not self-refuting — the wording merely spans two senses of "guarantee strength" and needs one aligning sentence. **Unresolved; both positions recorded.** The practical resolution for the authors is the same either way: state which asymmetry is being claimed, and cite §3.5.
2. **Severity of W3, and the score.** Reviewer 1 demurs on desk-reject severity (pre-check dependent). Reviewer 3 holds it may be the single desk-triggering item. Reviewer 3 also weights the zero-change more heavily in its score, but **explicitly accepts 3/5 as the consensus number** if the appendix items are treated as reflow-only.
3. **Scores**: Reviewer 1 — weak reject (≈3/5), downgraded from its Round 2 conditional-accept; Reviewer 2 — 3/5 borderline, unchanged; Reviewer 3 — 2.5/5, accepting 3/5 as the panel number. **Converged range: weak reject / borderline.**

## Questions for the Authors

1. Which reading do you intend in §6.4 — the withdrawn proven/unproven asymmetry, or the retained exact/nominal one? State it and cite §3.5.
2. Will you recompute Table 1 under the ln(1/α_law) radius (the counts can only rise), or relabel to 0.975 and correspondingly change §4.4's null?
3. Is Table 4's row 35–49 a column swap, or does the monotonicity claim need demoting?
4. Where is the ε_lo distribution / bracket-width summary?
5. Why does the reference check disagree with the rendered PDF on three items — which .bib built the PDF?
6. Will the mandatory appendices be moved before the references and compressed to ≤1 page each?

## Missing References

No missing \cite keys (53 entries, 53 cited, 0 orphan, 0 duplicate). Remaining items are integrity, not coverage:
- **[5] fix**: wrong DOI, reversed author order, missing pages (W17) — independently web-verified.
- **Open-set recognition cluster still thin**: Bendale & Boult (CVPR 2016) and Geng, Huang, Chen (TPAMI 2020) are absent (Reviewer 2's C-2).
- **Encrypted-traffic deep models**: Sirinam et al. (CCS 2018) and Rimmer et al. (NDSS 2018) absent from the "analyzers are now numerous" list (Reviewer 2's C-3).
- **Brace-protection** (4 entries) and **2 author fields** — unresolved and explicitly contradicted by the rendered PDF; diagnose W20 first.

## External Review

Not requested (paperreview.ai external review is not enabled for this project).

## Visual Layout Check (non-scoring)

Status: **done** (18 pages covered). 0 critical, 2 warning, 14 info.
- Density: pages 3–7 are near-consecutive text with no display item; pages 6–7 are the densest unbroken block. One display item in §3.4–3.8 would restore rhythm.
- Appendix headings are visibly unbalanced (two subsections numbered A.2, one suffixed "b"; inconsistent heading levels) — reads as an un-proofread appendix.
- Figure 1's caption (~8 lines, small type) outweighs its graphic.
- Positives: no content overflows the margins; no clipped figures or garbled equations; tables booktabs-ruled; colour scheme colourblind-safe.
- **Evidence conflict to note:** the automated check reported no leftover LaTeX markup; Reviewers 1 and 3 both see the literal `**…**` at p10. Weight the direct inspections (W2).

## Paper Audit & Reference Verification (non-scoring)

- **Paper audit**: compile **PASS** (18 pages, exit 0; 2 critical, 82 warning, 9 info). The two critical findings are W8 and W14; the audit also produced W12, which all three reviewers missed. The visual sub-agent exited abnormally again, so the layout layer rests on the dedicated visual check above.
- **Reference verification**: 53 entries, 0 missing/orphan/duplicate; 13 metadata mismatches; 2 missing author fields and 4 brace issues (both contested by the rendered PDF — see W20). [5]'s DOI error was independently web-verified by two reviewers.

---

## Overall Assessment

**Verdict: weak reject (borderline).** Panel converged at ≈3/5 (one reviewer at 2.5/5). **Not acceptable in current form.**

Round 1 was *reject* on correctness. Round 2's revision genuinely fixed the correctness cluster, and all three reviewers confirmed that fix holds. Round 3 changes nothing, so the disposition reverts to the unresolved remainder — and the remainder is now not "unknown defects" but a **closed, enumerated list**: two desk-visible artifacts (W1, W2), one arithmetic mismatch that, when fixed the preferred way, *raises* the headline (W4), one table row contradicting its own claim (W5), one missing characterization of the title object (W6), one wording/claim divergence (W7/W8), three unexecuted promotions (W9), and a mandatory-appendix placement violation (W3).

The one thing that would change this assessment is not more science — it is the **next revision being visible**. Every item on the list is a text edit, a table recomputation, or a layout move. None requires new experiments. Two of them (W1, W2) would be caught by a desk check; the rest by one careful pass. If the authors close W1–W6 and W9 and move the mandatory appendices (W3), the paper returns to the borderline-accept territory Round 2 had reached, and the honest caveat about the missing Round 2 report means that outcome should be expected, not treated as a failure of the work.

**Confidence**: high. The scientific-core assessment and the defect list are both corroborated by three independent re-reads, one full render inspection, the paper audit, and independent reference verification — with the two evidence conflicts (W2, W20) disclosed rather than smoothed.

## Detailed Comments

**Abstract.** Pairwise framing correct; "upper-side set falls from 340 to none" fixed. *Residual:* the detector sentence (W14); the title-vs-claim mapping still unstated.

**Introduction.** Carries the self-limitation that resolved Round 1. *Missing:* first-paragraph term definition; novelty boundary; contribution 4 overstatement (W8).

**Measurement Design.** Lemma 1 correct. *Fix:* reconcile 0.95/0.975 via the ln(1/α_law) radius and recompute Table 1 (W4); add the coverage calibration the Section currently declines (Reviewer 1's N-3).

**Results.** Bootstrap and paired-increment test are strong. *Fix:* report the ε_lo distribution (W6); name the sparse-inflation confound (W11); fix the inverted direction word (W12); delete the duplicated paragraph (W13).

**Discussion.** §5.1's self-reversal is the revision's best moment; the "three decimal places" sentence it contradicts (W10) must go. §5.2 needs the balanced dual-use statement (W21).

**Related Work.** Added clusters well-placed; §6.2's KS grouping (W16) and the §6.4 self-reference (W18) need fixing; the novelty boundary belongs in the Introduction (W7/W9).

**Conclusion.** Closing sentence needs the pairwise qualifier moved forward (W12's class).

**Formatting / Anonymity.** Double-blind intact; body exactly 13 pages. **Two desk-visible defects (W1, W2) and the appendix placement (W3)** are the priority; then the reference-field items (W17) once W20 is diagnosed.

**Ethics / Open Science.** Open Science carries a provenance example and a pre-registration statement — but with truncated hashes, no timestamps, and no URLs (W19). Ethics remains purely defensive (W21).

*End of consolidated report — Round 3.*