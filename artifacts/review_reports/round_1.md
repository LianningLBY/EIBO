---
round: 1
review_mode: fresh
overall_score: "reject（resubmit-worthy：正确性三件套须实质修复，仅修格式与表述不足以录用）"
score_value: 
score_max: 
score_label: ""
verdict_canonical: "reject"
verdict_raw: "reject（resubmit-worthy：正确性三件套须实质修复，仅修格式与表述不足以录用）"
timestamp: 2026-09-15T06:11:16.301123+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Consolidated Review Report — Round 1

**Venue**: USENIX Security 2027 (Cycle 2) · **Review round**: 1 · **Reviewers**: 3 (method/experiment · novelty/related-work · format/ethics/reproducibility)

---

## Summary

The paper proposes to compute, on real encrypted (QUIC) traffic, a *two-sided ε-indistinguishability bracket* per service pair — a finite-sample-strict upper bound on total-variation distance (plug-in estimate plus a confidence radius) and an asymptotic lower bound (Michel-style) — and to make the *guarantee asymmetry* between the two sides the explicit object of study. On the coarsest pre-registered channel (k=5, M=1) it reports 336/990 (33.9%) of service pairs admit a joint bracket, that the certifiable fraction collapses monotonically as alphabet resolution M grows and vanishes beyond M=4, and that a standard chain-rule divergence estimator provably cannot adjudicate the dependent-prefix growth question — a negative result robust to two repair attempts, plus a vacated BIC-vote result correctly labeled non-evidence.

The submission's reporting discipline is genuinely exceptional — negative results are reported rather than hidden, the two certified objects are explicitly refused mutual corroboration, and a heterogeneous-i.i.d. null is used to *kill* its own BIC-vote corroboration. However, the three reviewers converged on a cluster of correctness and positioning defects that strike at the paper's central claims: the sole carrier of the "finite-sample strict, zero-assumption" guarantee is an unproven and mis-attributed radius, the "asymmetry is the problem's shape" framing is a method choice elevated to necessity, and the promised open-set error floor is never reduced from the pairwise object that is actually measured. These are fixable, but they are substantive, and the manuscript is not acceptable in current form.

---

## Strengths

1. **Exceptional reporting discipline.** The paper refuses to average away the upper/lower guarantee asymmetry, refuses to mix the 340 (upper-only) and 336 (joint gate) counts (everywhere except the abstract), refuses to let the k-prefix and whole-flow certified objects corroborate each other (§5.4 "cancellation rather than corroboration"), and refuses to present the BIC-vote as evidence for dependence. This is rare and valuable.
2. **A negative result with quantified teeth (C3).** The claim is not "divergence grows sublinearly" but: the standard plug-in chain-rule estimator returns sublinear on exactly-linear known truth (est/true 1.0002→0.6769), the failure survives two independent repairs, and the repair that would work costs 0.608 of the data at k=30. That is a methods/limits finding, not a bug report.
3. **A genuinely non-trivial confound demonstration.** "A heterogeneous-i.i.d. null (zero within-flow dependence by construction) reproduces the Markov vote 45/45" — thereby showing the vote is not diagnostic — is the paper's single best negative result and deserves promotion, not burial at the end of §4.5.
4. **The certificate horizon as a function, not a number.** The closed-form frontier M_max(k, n, tv) is the most reusable contribution for a USENIX Security audience, and is the part that survives the corpus-instability critique.
5. **Hygiene regime verified, not assumed.** Flow/time-disjoint splits, no packet-level splitting, address randomization with an audited masking histogram, and explicit exclusion of SNI/UA/TLS-extension side channels — directly responsive to the shortcut-learning literature.
6. **Numerical self-consistency.** 45→C(45,2)=990; 340−336=4=990−986; 336/990=0.3394, 534/3321=0.1608, 523/3321=0.1575, 3310/3321=0.9967 all reconcile; Table 3's 0.6769/0.8820 and occupancy 0.000→0.998 match the text.

---

## Weaknesses (core)

### Critical — correctness

**W1 — The upper-bound radius Eq.(4) is unproven, mis-attributed, and its sampling assumption is undeclared.** This is the highest-priority, three-reviewer consensus issue (R1-1 = R2-N3 = R3-M2). Eq.(4), ε_hi = btv + r_a + r_b with r_i = ½√(m/n_i) + ½√(2 ln(2/α_law)/n_i), is the *sole* carrier of the title's "certification-grade" and of the "finite-sample strict, zero assumptions" claim. Yet: (a) it is labeled "Dvoretzky–Kiefer–Wolfowitz type," but DKW is a sup-norm bound while Eq.(4) is an ℓ1 bound whose ½√(m/n) term is closer to the Han–Jiao–Weissman [14] minimax ℓ1-deviation form (that reference sits in the bibliography but is not invoked in §3.3 to fix constants); (b) no lemma, theorem, or proof is given, and the "α_law=0.025 + union bound over two laws → joint 0.95" derivation is one sentence; (c) the bound requires i.i.d. flow samples, but Monday-to-Friday backbone flows have time-correlation (same-service bursts, time clustering), and the i.i.d. assumption is never stated — §3.3's "no smoothness" is a *different* assumption. **This is the correctness linchpin of the whole paper; without it the "finite-sample strict" results are unsupported.**

**W2 — The guarantee asymmetry is elevated to a property of the problem when it is a method choice (R2-N1, endorsed by R3).** The paper repeatedly asserts the lower side is "asymptotic … the asymmetry is the result, not a caveat" and that "proven is unavailable for the lower side at any sample size." This is factually wrong: finite-sample high-probability TV lower bounds exist and are *already cited in the paper's own bibliography* — Chan et al. 2013 and Diakonikolas et al. 2020 (optimal closeness testing), and Michel et al. [26] whose own title is "**High probability** lower bounds for the total variation distance." The paper chose the asymptotic construction; it did not discover an impossibility. Either add a finite-sample lower bound via the already-cited closeness-testing route (making the bracket genuinely two-sided finite-sample), or rewrite the claim as "under affordable constants we use an asymptotic lower bound."

**W3 — Pairwise TV bracket → open-set error floor has no reduction anywhere (R2-N2).** The abstract/introduction promise "what error floor is impossible" for *open-set* recognition, but the bracket is per-pair TV(P,Q) while open-set error is a known-vs-unknown multi-class aggregate (OSCR/AUROC). No reduction — not even a union-bound weak form — connects the two. §4.4 itself concedes the compared quantity is closed-set. The promised open-set floor does not exist in the paper; only a pairwise indistinguishability certificate exists. Reposition the contribution or supply the reduction.

**W4 — "each side of the bracket is a joint 0.95 statement" contradicts the paper's own discipline (R3-M4).** The lower side is asymptotic with no finite-sample confidence level; the 0.95 belongs only to the upper side. This self-contradiction sits at the heart of the one discipline the paper makes its main contribution, and all three reviewers flagged it (R2 called it the sharpest self-contradiction across all reviews).

**W5 — "The upper side binds on every rung / 100% of the ladder (Table 1, rightmost column)" overreaches and cites a nonexistent column (R3-M5, R1, R2-W1).** On rungs M≥2 no per-rung lower side was computed (Table 1's own caption concedes the joint gate is defined at M=1 only), so "binding" — a comparison against the lower side — is undefined there. The rightmost column is "joint," not a binding-fraction column. Scope the claim to M=1 (340 vs 986).

**W6 — Detector validation is unreproducible and its "no detector breaches" claim is not matched by evidence (R1-6, R2-W3, R3).** No architecture, feature set, training protocol, hyperparameters, or citation for LightGBM/Prototype/RoNeTC; the compared quantity is a pair-level macro-average *closed-set* error, not the open-set floor; and the nine one-sided binomial cells show 2–10 violations, all p ≥ 0.9765 — power near zero, so "not falsified" carries almost no information. *(Cross-note: R2 correctly rebuts one sub-point — the null rate 0.05 is the correct null, not a misuse of α, since ε_hi is a 95% upper bound; the defect is power and the closed/open object mismatch, not the null construction.)*

### Critical — framing / integrity

**W7 — References [2][30][32][38][44] carry internal workflow annotations (R3-M1).** "[2] CESNET and associated paper cited by the record: Jan Mücke et al.", "[30] metadata-level; full text not yet fetched", "[32] …Closest protocol/privacy positioning comparator", "[38] RoNeTC is the method name; the DOI title is as given…". Author review notes left in the bibliography — visible at desk check and corrosive to the confidence the paper's discipline otherwise earns.

**W8 — The reproducibility chain and pre-registration are unverifiable in the submission (R3-M3, R2, R1).** Zero exp_id, zero content_sha256, zero manifest hash appear in the text; no anonymous URLs in the Open Science appendix (only "provided through the submission system's artifact channel"); "pre-registered" appears multiple times with no record/hash/timestamp; §3.7 claims "the appendix and the released artifacts carry the per-pair ledgers, the full 20-cell resolution table, the sample-size stratification table" but the appendix contains prose only.

**W9 — Orphan result-bearing blocks in Discussion (R1-8, R3-W4, R2).** The whole-flow rectified object (2.7×/7.3× cancellation), the missing-service mass (0.00202), and the promised DST_ASN audit ("the DST_ASN audit we report" at §6.4, with no report in Results) are unpaired with the contribution list and have no experiment/table/setup in Results. They belong to a different paper than the one the Introduction describes.

**W10 — The abstract is inverted and conflates two counts.** It gives the C3 estimator negative its own 9-line co-headline while compressing detector validation to one clause and dropping the divisibility bound entirely; and "the certifiable set falls from 340 pairs to none four rungs finer" uses the upper-only 340 as the "certifiable set" — the two-sided bracket actually exists only at the single cell (M=1, k=5). A reviewer of the abstract alone would not know the paper validates its instrument against real detectors.

### Major

**W11 — No compute/hardware/hyperparameter disclosure** anywhere in body or appendices (GPU-hours, runtime, epochs, learning rate, split boundaries), contradicting §3.7's reproducibility promise.

**W12 — Primary corpus not named in the body.** §4.1 says only "a paired QUIC corpus of Monday-to-Friday backbone captures"; the XS-subset selection (service-label source, 53→45 threshold, flow-retention rules) is undisclosed. *(Cross-note: R3 partially rebuts R2-N4 — refs [2] does name CESNET-QUICEXT-25, Zenodo 17249078 — but the in-line body and the Open Science appendix do not, and the "minimum flow threshold" value that yields 990 pairs is never stated.)*

**W13 — Cross-corpus comparison uses an argument from precision, not a test.** "Agrees to three decimal places … would not be expected by accident" (0.9967 vs 0.9960) is a floor effect on near-saturated pass rates, and the 18.2→9.7-pt gap narrowing is reported as bare point values — the one place where wording strength exceeds what is computed, against the paper's own discipline.

**W14 — The median-TV monotone series (0.58→0.97) is asserted without display and confounded with sparse-context bias.** It is quoted in prose only (no distribution, no CI), and its "finer alphabet resolves more structure" reading is entangled with the plug-in sparse bias the paper itself demonstrates in §4.5 — the rise may be partly bias, not separability.

**W15 — Missing related-work cluster.** (i) The title says "ε-Indistinguishability" but there is zero differential-privacy citation (Dwork TCC 2006; Andrés geo-indistinguishability CCS 2013); (ii) statistical-distance traffic-indistinguishability defenses are absent (Traffic Morphing NDSS 2009; Tamaraw CCS 2014; Juarez et al. CCS 2014 — the latter directly speaks to the 33.9%→15.75% instability); (iii) the sparse plug-in bias of C3 is a textbook result (Paninski 2003; Nemenman et al. 2002; Valiant & Valiant STOC 2011) not delimited as prior art; (iv) "certified" is not delimited from randomized-smoothing certified robustness (Cohen et al. ICML 2019).

**W16 — C3's causal language overreaches.** "Bias accumulates exactly where sparse" is correlational (no occupancy-controlled ablation), and "structural" is an overgeneralization from two failed repairs. The genuinely novel parts — the quantified 0.608@k=30 data cost and the heterogeneous-i.i.d.-reproduces-Markov-vote confound — should be foregrounded.

**W17 — Reference metadata defects.** 12 metadata mismatches, 2 missing author fields (luxemburk2023cesnet, luxemburk2023encryptedquic), 4 brace-protection issues; michel2020high resolves to a CRAN R-package rather than the paper; jiao2018l1distance matched at title similarity 0.43 (possible wrong DOI); chan2013closeness year mismatch (2013 vs 2014).

### Minor

**W18 — Discussion is not a discussion** — four result-bearing subsections first report load-bearing numbers there; the Limitations subsection re-derives the horizon mechanism §4.3 already derives.

**W19 — Section order (Results → Discussion → Related Work) buries the positioning claim**; the "why a bracket is needed" argument is only substantively answered in related work after all results, and the "to our knowledge, no prior work" sentence sits at the end of Related Work.

**W20 — "EIBO" is used as a proper noun in a figure caption but never defined** in body, title, or abstract.

**W21 — X11's 20,000-flow cap on the replication lower side is never justified** (the primary corpus computes full-n on 990 pairs); the conservative direction is stated but the necessity is unexplained.

**W22 — §5.2 is a dual-use result** (quantifies target-address separability gain, Δtv̂=0.3136 at B=256) with a purely defensive ethics statement; IP-hash reversibility (low-entropy, dictionary-reversible if unsalted) is not discussed.

**W23 — Title "Certification-Grade" overstates a mixed-strength gate** (finite-sample upper AND asymptotic lower); needs a first-paragraph definition or softer wording.

---

## Reviewer Consensus

Tagged [AGREE] — all three Reviewers converged, with no substantive [REBUT] remaining:

- **[AGREE] W1 (Eq.(4) unproven + mis-attributed + i.i.d. undeclared)** is the dominant, correctness-level problem. R1 notes AD1 (i.i.d. undeclared, distinct from "no smoothness") and AD2 (lower-bound source [26] Michel's title is "High probability lower bounds," rewritten as "asymptotic" without explanation).
- **[AGREE] W2 (asymmetry is method choice, not necessity)** — the paper's own cited works (Chan 2013, Diakonikolas 2020) are finite-sample two-sided TV testers.
- **[AGREE] W3 (no pairwise→open-set reduction)** — the core open-set error-floor promise is unfulfilled.
- **[AGREE] W4 + W5 (two self-contradictions)** — "each side joint 0.95" and "binds on 100% of the ladder" both contradict the paper's own asymmetry discipline.
- **[AGREE] W7 (reference annotations)** — desk-reject-visible.
- **[AGREE] W8 (reproducibility chain unverifiable)** — zero exp_id/hash/URL/pre-registration in the submission.
- **[AGREE] The measurement itself (C1/C2) is sound and the reporting discipline is a genuine strength**; the defects are in what is *claimed over* the measurement, not in the measurement.

## Reviewer Divergence

Two bounded divergences, recorded for completeness:

1. **Originality rating.** R3 rated Originality "high" (four-in-one contribution + asymmetry-as-result + horizon function); R2 rated it "incremental, marginal-leaning" (two off-the-shelf tools combined; the novelty is the reporting discipline and the confound demo); R1's Reject leans on correctness rather than novelty. Consensus reading: the *combination and its honest framing* are novel, the *mathematics* is not new — "incremental contribution with exceptional reporting discipline" is the accurate characterization.
2. **Verdict threshold.** R1: reject (correctness directly strikes the correctness dimension); R2: weak reject / borderline (novelty incremental); R3: reject, resubmit-worthy (M1/M3 stacked on the correctness cluster push it below a direct Major Revision). This is a severity weighting, not a factual disagreement. **Common bottom line (all three): correctness defects must be substantively resolved — formatting and wording fixes alone are not sufficient for acceptance.**

## Questions for the Authors

1. Provide the theorem statement and proof (or the exact citation with constants) for Eq.(4), state the i.i.d. flow-sampling assumption explicitly, and discuss how time-correlation of Monday-to-Friday flows affects the "finite-sample strict" claim.
2. Given that Chan et al. 2013, Diakonikolas et al. 2020, and Michel et al. [26] (whose title says "high probability") are already cited, why is "proven unavailable for the lower side at any sample size" asserted? Will you add a finite-sample lower bound, or rescope the claim?
3. Where is the reduction from the pairwise TV bracket to the open-set error floor? If none exists, will you retitle the contribution as a pairwise indistinguishability certificate?
4. What are the architectures/features/hyperparameters of the LightGBM/Prototype/RoNeTC panel, and what is the power of the nine-cell binomial test against a meaningful effect size?
5. Which corpus and which exact subset/split produce the 336/990 headline, and what is the minimum flow threshold?
6. Where are the anonymous artifact links and the pre-registration record (doc hash + timestamp)?
7. Please reconcile the abstract's contribution emphasis and the 340-vs-336 usage with the body's two-number discipline.

## Missing References

No missing \cite keys (44/44 resolve; 0 orphan, 0 duplicate). But these de facto missing references must be added:

- **Differential privacy**: Dwork, McSherry, Nissim, Smith — "Calibrating Noise to Sensitivity" (TCC 2006); Andrés, Bordenabe, Chatzikokolakis, Palamidessi — "Geo-indistinguishability" (CCS 2013). The title claims "ε-Indistinguishability" with zero DP citation.
- **Traffic indistinguishability defenses**: Wright, Coull, Monrose — "Traffic Morphing" (NDSS 2009); Cai et al. — Tamaraw (CCS 2014); Juarez et al. — "A Critical Evaluation of Website Fingerprinting Attacks" (CCS 2014).
- **Sparse plug-in bias (for C3 delimitation)**: Paninski (Neural Computation 2003); Nemenman, Shafee, Bialek (NeurIPS 2002); Valiant & Valiant — "Estimating the Unseen" (STOC 2011).
- **Certified-robustness semantics**: Cohen, Rosenfeld, Kolter — "Certified Adversarial Robustness via Randomized Smoothing" (ICML 2019).
- **Fix the mis-resolved objects**: michel2020high (→ the paper, not the CRAN package), jiao2018l1distance (verify DOI), chan2013closeness (verify year/authors).

## External Review

Not requested (paperreview.ai external review is not enabled for this project). No external findings to fold in.

## Visual Layout Check (non-scoring)

Status: **done** (independent visual-check agent). 0 critical, 4 warning, 9 info.

- **Page 15** ("Ethical Considerations") fills ~22% of the page; **page 16** ("Open Science") ~15–20% — together they waste over a full page.
- **No visual anchor on pages 1–4**: the first figure lands on page 5, so a reviewer's first three pages are text-only.
- Figure 1's panels are tight at print size; Figure 3's in-plot legends shrink the data region; Table 1's mixed integer/decimal "and" column reads unevenly.
- Positives: no content overflows margins; zero Overfull \hbox in the compile log; booktabs-ruled tables; colorblind-safe point/interval encoding with hatch redundancy.

## Paper Audit & Reference Verification (non-scoring)

Both completed (status: **done**).

- **Paper audit**: compile PASS (16 pages, exit 0); 4 critical, 61 warning, 10 info. The four critical findings map to W1/W5/W10/W9 above; the 28 `\label`-without-`\ref` warnings and "the `cite` package should not be used" are noted for the venue kit.
- **Reference verification**: 44 entries, 44 unique cited keys, 73 citations, 0 missing/orphan/duplicate; 25 online-verified, 12 metadata mismatches, 2 missing author fields, 4 brace issues, 7 API-unresolvable. Detail in W17 / Missing References.

---

## Overall Assessment

**Verdict: reject** (resubmit-worthy — a major revision that substantively resolves the correctness cluster, not merely format and wording).

This is an unusually honest and well-disciplined measurement paper whose negative results and guarantee-asymmetry framing are genuinely valuable, and whose certificate-horizon-as-a-function and confound-demonstration contributions are worth publishing. **However**, the three reviewers independently converged on a correctness cluster that the current manuscript does not survive: the sole finite-sample-strictness guarantee rests on an unproven, mis-attributed radius with an undeclared i.i.d. assumption (W1); the "asymmetry is the problem's shape" framing is a method choice presented as necessity (W2); and the promised open-set error floor is never reduced from the pairwise object that is actually measured (W3). These are compounded by two self-contradictions in the very discipline the paper makes its centerpiece (W4, W5), internal annotations left in the bibliography (W7), and a reproducibility chain that is unverifiable in the submission (W8). The defects are fixable — supply the proof and assumption, add a finite-sample lower bound or rescope, provide the reduction or reposition, strip the annotations, and ship the anonymous artifact links — but the common bottom line across all three reviewers is that the correctness issues must be substantively resolved before the paper can be considered for acceptance.

**Confidence**: high. Every critical finding is corroborated by the paper's own internal concessions (Table 1 caption, §4.4 closed-set concession), by the independent paper audit, and by three-way reviewer convergence with no remaining substantive rebuttal.

## Detailed Comments

**Abstract.** Inverted emphasis (W10) and the 340-vs-336 conflation; the "upper side binds" phrasing imports W5. Lead with the bracket + asymmetry, name the detector validation, state the two-sided bracket's single cell (M=1,k=5), and demote C3 to a supporting finding.

**Introduction.** Correct "binds on every rung" (W5); reconcile the divisibility-bound listing with the abstract; the "proven unavailable at any sample size" claim must be removed or rescoped per W2.

**Background / Measurement Design.** The channel hygiene is a strength. Eq.(4) needs a theorem statement, exact constants, the i.i.d. declaration, and correct ℓ1-vs-DKW attribution (W1); fix "each side joint 0.95" (W4); deliver the promised per-pair ledgers (W8/W11).

**Results.** Two-number discipline (28–36) is good; but the median-TV series needs display and an occupancy-controlled ablation to separate bias from separability (W14); the detector panel needs architecture/features/protocol/citations and a power analysis (W6); the corpus and flow threshold must be named (W12).

**Discussion.** Four first-reported result blocks must move into Results or be promoted into the contribution list (W9); the "three decimal places" argument needs a statistical test or softer wording (W13); §5.2 needs a balanced dual-use ethics statement and salt disclosure (W22).

**Related Work.** Add the DP / traffic-morphing / sparse-bias / certified-robustness clusters (W15); move the novelty boundary to the Introduction; fix the dangling DST_ASN reference (W9).

**Conclusion.** Consistent with the Introduction — which makes the abstract's divergence (W10) more visible; reconcile all three framing surfaces.

**Formatting / Anonymity.** Double-blind appears intact (no author/funding/self-reference leakage; internal-leak check 0 findings). Strip the reference annotations (W7); fix author fields/braces (W17); replace the `cite` package per the venue kit. The two appendices' page-15/16 whitespace waste should be consolidated (W23 / visual check).

**Ethics / Open Science.** Both sections present; content appropriate; Open Science must add the anonymous URLs and a representative exp_id→content_sha256 example (W8).

---

*End of consolidated report — Round 1.*