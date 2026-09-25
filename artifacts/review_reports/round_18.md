---
round: 18
review_mode: fresh
overall_score: "weak reject (borderline). USENIX Security qualitative criteria: originality moderate; relevance moderate-low; correctness high in execution but the headline guarantee's statistical status is ambiguous; clarity high in prose, low in guarantee semantics. No numeric scale at this venue."
score_value: 
score_max: 
score_label: ""
verdict_canonical: "weak reject"
verdict_raw: "weak reject (borderline). USENIX Security qualitative criteria: originality moderate; relevance moderate-low; correctness high in execution but the headline guarantee's statistical status is ambiguous; clarity high in prose, low in guarantee semantics. No numeric scale at this venue."
timestamp: 2026-09-24T16:59:34.808254+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 18 — Consolidated Review Report

**Paper:** Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition
**Target venue:** USENIX Security 2027, Cycle 2 (registration 2027-01-19, submission 2027-01-26; both future — deadline NOT expired). Double-blind; body ≤13pp in the unaltered USENIX template; two mandatory one-page appendices ("Ethical Considerations", "Open Science") after the body and before references; references/optional appendices uncapped. USENIX reviews on qualitative criteria (originality, relevance, correctness, clarity) with no numeric grid.
**Submission:** PDF only, 24pp (body ends p.13; Ethics p.14; Open Science pp.15–16; Appendix pp.17–21; References pp.22–24). No LaTeX sources, so reference verification was not applicable this round.
**Roundtable:** 3 reviewers, all delivered independent reviews and point-by-point cross-responses. R1 = method soundness + experimental rigor; R2 = novelty + related-work; R3 = format + ethics + reproducibility + anonymisation.

---

## Summary

The paper measures, on real QUIC wire data at per-service-pair granularity, a two-sided interval on total variation between service traffic distributions — a finite-sample strict upper side and a classifier-based high-probability lower side — and aggregates the per-pair bounds into an open-set error floor. It is an unusually honest measurement/rigour paper: it reports its own negative results in quantified detail (the chain-rule estimator failing a known-truth gate; the certificate horizon; the estimator-coverage shortfall) and repeatedly states facts that undercut its own headline. The reviewers converge that the work is careful and sound in execution but does not, in its current form, clear the USENIX Security bar — primarily because the certified object is narrow (it exists as a true two-sided joint gate at one (M,k) cell), the headline number is dominated both by a no-data combinatorial bound and by the paper's own uncited-in-comparison LP floor, the nearest prior-art line is not cited, and the headline guarantee's statistical status is stated three incompatible ways.

## Reviewer verdicts

- **Reviewer 1 (soundness):** borderline. Arithmetic and constructions re-derived and largely stand; the defects are fixable statement/positioning problems plus one genuine numerical error, not a broken result.
- **Reviewer 2 (novelty):** Reject (weak reject / borderline). Recommends PoPETs as the natural venue (IMC second); USENIX Security judged the weakest fit.
- **Reviewer 3 (format/ethics/repro):** Do not reject on substance, but three compliance defects must be fixed before submission (appendix over-length, internal-vocabulary leak, unlocatable artifact chain).

**Consolidated: weak reject (borderline).** No unresolved reviewer contradictions remain; the cross-stage rebuttals were refinements, not disagreements.

---

## Strengths (reviewer consensus)

1. **The negative results are genuine contributions, not diary entries.** §4.5: the chain-rule estimator is admitted only after a known-truth gate (0.3389191441548814), fails it, and the failure is mechanised with numbers (occupancy collapse; both repairs fail with a quantified data cost of 0.608 excluded mass at k=30). (R2-S1, R1 concur.)
2. **The paper corrects its own prior attribution.** §4.3 states the certificate horizon was first attributed to the radius and that "that attribution was wrong," then re-attributes it to estimator saturation with numbers (median btv 0.9979 at k=30). (R2-S2.)
3. **Scope discipline is unusually good.** Stratum statements travel with every quoted fraction (the 33.9% is explicitly "a stratum statement, not a property of traffic in general"); the 990 pairs are treated as a complete graph over 45 services and resampled by service, not by pair; §5.4 refuses to rank two certified objects whose agreement is cancellation. (R2-S4, R1 concur.)
4. **The shortcut / data-hygiene literature IS engaged** — this was checked specifically. [56] "Bias in the Shadows", [59] SoK "Decoding the Enigma", [63] "Sweet Danger of Sugar", [64] ShortcutCatcher, tied to the split policy (flow- and time-disjoint, packet-level splitting prohibited, discarded buffer month; masking verified by a padding sweep). (R2-S5.)
5. **The paper states the fact that undercuts its own headline** (§3.1: the uniform floor "is not competitive at the coarsest rung even against a one-line combinatorial argument"). R2 verified the dominating bound independently (max(0, 1−m/C): 1−32/45=0.289, 1−32/46=0.304, both > 0.197). (R2-S7.)
6. **Ethics appendix is substantive, not boilerplate.** It discloses "Hashing is not anonymization where the address space is enumerable" — an honest limitation of the corpus's own protection mechanism. (R3.)
7. **Reproducibility detail is above average**: seeds (random_state 0; calibration seed 20260917; split seed 12), hyperparameters (LightGBM 100 rounds/lr 0.1/31 leaves; RoNeTC MLP width, dropout 0.20, Adam 1e-3, 64 MC passes), compute budget, corpus name + DOI. (R3-S7, R1 concur.)

---

## Weaknesses

### Reviewer Consensus (independently confirmed by ≥2 reviewers)

**C1 [critical] — The headline guarantee's statistical status is stated three incompatible ways.** *All three reviewers verified the text.*
- Abstract: floor "held simultaneously over all 990 pairs with probability ≥0.95 under the upper side's within-service i.i.d. assumption".
- §7: "held simultaneously … ≥0.95 (Bonferroni)".
- §3.1, same paragraph: "at the simultaneous level 0.95 (Bonferroni over the 990 pairs)" AND "because the S terms are interval-valued, the aggregate is stated in expectation rather than as a joint high-probability claim".
Four sentences, three states, one PDF. A reader cannot determine what ≥0.95 attaches to — the single most load-bearing claim in the paper is unassessable as written. R2's arithmetic (990×0.025/2070 = 0.01196; 0.05/2070 = 2.42×10⁻⁵) was reproduced by R1 and R3. **R1's refinement (adopted):** R2's inference that a genuine Bonferroni route would require ε_hi recomputed at α≈0.05/990 while the ledger sits at α_law=0.025 is only partly right — the Open Science D181 entry records an operative budget α_pair=0.05/990 with 984/990 pairs non-vacuous and 6 vacuous (caps at 1), which is consistent with radii recomputed at the inflated α. So the Bonferroni-simultaneous claim *may* have artifact support; the more likely root defect is that the "in expectation" per-pair-envelope paragraph is a superseded generation left undeleted. **Fix:** state once which α produced the ledger's ε_hi, what carries ≥0.95, and that the floor is an expectation under a uniform class prior; delete or demote the stale expectation clause. (R2-N4 = R1 = R3-confirmed.)

**C2 [critical] — The certified two-sided object is narrow, and the lower-side evaluation scope is stated inconsistently across three surfaces.** *Confirmed by all three; R1 and R3 corrected the exact count.*
The (6)-route two-sided joint gate exists at one (M,k) cell only: 336 at (k=5, M=1); upper-side counts fall 340→47→3→0→0 across M and are 0 at every k≥15. R2 framed this as "one of 20 cells." **R1 and R3 both corrected the absolute count:** §4.2 additionally reports joint counts on the m-free (Eq 9) route at (M=2,k=5)=127 and (M=1,k=10)=98, so the lower gate was evaluated at more than M=1. This exposes a **new internal contradiction not present in the Round-13 tracker:** §3.4 says the lower side "is evaluated at M=1 only, deliberately," §4.2 reports an (M=2,k=5) joint count (requiring an M=2 lower side), and Table 3 prints "–" in those cells. At most one is true. This is adjacent to the Round-13 L13-CR3 route-mix item, which was marked resolved on the earlier bytes — it has recurred in a different form. **Fix:** decide which (M,k) lower sides were computed; realign §3.4, the §4.2 passage (label the route per sentence), and the Table 3 caption; carry the single-cell status of the (6)-route bracket into the abstract/title framing. (R2-N2 + R1 + R3.)

**C3 [critical] — Internal identifier "D181" leaks into the rendered submission (double-blind).** *Probe reproduced by R3, confirmed by R1 and R2.*
- p.4 §3.1: "The floors are produced by the **D181** joint-coverage reaggregation, art_20260922_f7853e (c0573590…)".
- p.15 Open Science: "**D181** headline floors: …".
"D181" is this project's internal decision-registry identifier, undefined anywhere in the paper and unresolvable to a reader. The same appendix/caption region also prints revision residue: **Figure 1 caption (p.17) "relocated here from the Introduction."** This is the same defect class as a previously-shipped internal-process-vocabulary leak. **Scope note (R1/R2 refinement):** listing artifact filenames and module names (e.g. `q1_lower_side_full_n.json`, the `statcore` module) inside a reproducibility appendix is standard practice and is NOT required to be removed; and R2 notes USENIX has no standalone "no process vocabulary" rule, so this is best classified as a **clarity/anonymity-adjacent defect**, not a hard anonymity violation. But "D181" and the "relocated here from the Introduction" caption should be removed. (R3 Probe B + R1 + R2.)

**C4 [critical] — Open Science appendix exceeds the one-page limit.** *R3 finding; R2 and R1 confirm; R1's own initial "✓ compliant" was rebutted by R3 and is withdrawn.*
"Open Science" starts p.15 and runs a full second page to p.16 ("…produce the flow-level tables used here."); "Appendix: Supplementary Material" only begins p.17. Ethics is correctly one page (p.14). USENIX '27 allows each mandatory appendix up to one page; two pages is a compliance defect and a desk-reject risk. R1 initially recorded this as compliant — R3 and R2 both corrected that from the render. **Fix before submission:** compress Open Science to one page or move non-mandatory content into the optional appendix. (R3-W1 = R2-I1; R1 corrected.)

**C5 [warning] — The artifact chain is not locatable from the submission.** *R3 finding, R2 confirms as two sides of one defect.*
Open Science (p.15) states artifacts are "carried in the supplementary-material archive … reachable through the submission system's own artifact materials" — no anonymised link, no host, no manifest filename — so the ~20 content_sha256 hashes cannot be traced to bytes from the PDF alone; the corpus is given as name + DOI with no checksum. The adjacent claim "Every claim … can be checked from the submitted bytes, without tooling" (p.16) contradicts the fact that reproducing the bounds requires parsing ledgers and recomputing (6)/(3). **Fix:** supply an anonymous artifact link (USENIX recommends anonymous.4open.science, conference ID SEC27) and a manifest filename, or state honestly that artifacts travel only within the submission system; scope the "without tooling" claim. (R3-W3 = R2-I2/I3.)

**C6 [warning] — Figure 1 caption points at the wrong section (resolves but wrong).** *Probe C reproduced by R3, confirmed by R1.*
Figure 1 caption (p.17): "Cited from Section 1 and **Section 3.7**." §3.7 (p.6) does not reference Figure 1; the sections that do are §1 and §3.1 (p.5, "Figure 1 (in §A.1) shows the pipeline"). The number resolves but is wrong — the exact defect class flagged in the assignment. A companion navigation defect: §5.2 cites "Figure 5, in Section A.5" but Figure 5 renders on p.21 (the A.7–A.9 region). (R3-W5/W6 + R1; R2 notes W6 should be minor since the figure number itself resolves.)

**C7 [critical] — The nearest prior-art line (black-box leakage / Bayes-risk estimation) is uncited, and the novelty sentence depends on that omission.** *R2 finding; R1 confirmed against §2.3/§6.1–6.4; R3 confirmed the four works are absent from the reference list but declined to rule on novelty strength (out of remit).*
§6.1 names Cherubin [9] as "the closest precedent for our upper side" and §6.2 names Michel et al. [37] as the direct source of the lower side; §6.4 claims "no prior work measures a two-sided bracket with asymmetric guarantee strength on real encrypted traffic." Absent: F-BLEAU (Cherubin et al., S&P 2019 — same first author as [9]), leakiEst (Chothia et al., CAV 2013), Bayes Security (Chatzikokolakis et al., CSF 2023), DeepSE-WF (Veicht et al., PoPETs 2023). Since the paper itself says the lower side is Michel et al. applied to this data, the delta must be drawn against this estimation line. **Fix:** add a subsection under §6.2 and state the delta precisely (fixed-n finite-sample upper side with stated α vs asymptotically-consistent estimators; per-service-pair; TV rather than a leakage functional; open-set aggregation). (R2-N3/W5 + R1; R3 confirmed absence.)

### Additional confirmed weaknesses

**C8 [critical] — Headline-number inconsistency: "the uniform floor of (3)" is printed as both 0.197 and 0.1858, and §A.8's own reconciliation does not close it.** *R3 finding; R1 supplied the missing derivation; R2 exhausted the alternatives.*
Everywhere but one place the floor of (3) is **0.197** (Abstract, §3.1, §4.2, §7, Open Science). §A.8 (p.21) calls "the uniform floor of (3)" **0.1858** and says the two differ by (M−1)/(K−1) = 45/44 ≈ 2%. But 0.197/0.1858 = 1.060, not 1.023. **R1's independent re-derivation:** with the LP uniform point w_ij = 1/[2(K−1)], the floor = S_known/((K+1)(K−1)) = 407.75/(46×44) = **0.2015** = 0.197×(45/44) ✓ — so the 45/44 reconciliation is correct, but it connects 0.197 and 0.2015, and the printed **0.1858 matches neither** (it corresponds to S≈384.6, most likely a superseded S-vector residual). R2 confirmed by exhausting both normalisation directions (0.1858×45/44=0.19003; 0.197×44/45=0.19258). Because 0.197 is the abstract's headline, this must be corrected or fully derived. This and C1 are two faces of one **generation-residue family** — the PDF cannot tell whether printed ε_hi/floor/quantile values come from the α=0.05/pair ledger or the α_pair=0.05/990 reaggregation. (R3-W8 + R1 + R2.)

**C9 [critical] — The headline floor is dominated twice, and the paper never writes the one comparison that rescues its contribution.** *R2 finding; R1 and R3 confirmed the text.*
0.197 is beaten by the no-data bound (0.304 at C=46). The paper's own **LP-weighted certified floor is 0.375** — which exceeds 0.304 — but the inequality 0.375 > 0.304 appears nowhere. This is simultaneously an over-claim (0.197 presented as the headline) and an under-claim (the LP result that dominates is never compared). R1 confirmed the LP is certified (§A.8 a-fortiori argument) so "make the LP floor the headline" is technically available, not merely rhetorical. **R3 correction to R2:** 0.375 is not "buried" — it appears in five places incl. the abstract — but the explicit dominance sentence is what is missing. (R2-N1 + R1 + R3.)

**C10 [critical] — The finite-sample guarantee is calibrated only on a synthetic model of its own violation.** *R2 finding; R1 and R3 confirmed the concession.*
The upper side is finite-sample "only under i.i.d. flow sampling." Calibration (§5.5, Table 7, §A.7) is synthetic block-law draws at one block size and one divergence; §A.7 concedes "we did not test coverage on real traffic, and nothing here says coverage holds on the corpus." For a paper whose whole value is a finite-sample guarantee, coverage on the reported corpus is the result, not a caveat. **R1's feasibility nuance:** true corpus coverage needs the true TV, which is unavailable on real traffic; the honest achievable check is a service-clustered re-split stability check, and if that cannot be produced the correct fix is to weaken the wording rather than add a mislabelled "coverage" test. (R2-N5 + R1 + R3.)

**C11 [warning] — §3.1 and §A.8 contradict each other on the sole stated reason for the weaker headline.** §3.1: the uniform form "alone preserves both the per-pair confidence semantics of (2) and the open-set discarded-term property." §A.8 (on the LP): "the same assumption-free property is therefore preserved." Both cannot hold; combined with C9 the stated justification for the uniform headline collapses to per-pair semantics alone. (R2-W1 + R1 + R3.)

**C12 [warning] — "Certification-grade" / "ε-indistinguishability" are self-applied and undefined.** §5.5 concedes the two-sided interval "is only as strong as its weaker endpoint" (the lower side's level is nominal, not exact), which sits badly with "Certification-Grade" in the title. Separately, "ε-indistinguishability" is used in title/abstract/Contribution 1 but only ε_lo ≤ TV ≤ ε_hi is defined (§3.1); the term carries a differential-privacy connotation (the paper itself invokes geo-indistinguishability [1] in §6.3), inviting a security reviewer to read in an ε-DP guarantee. Define at first use or rename. (R2-W2/W3 + R1 + R3.)

**C13 [warning] — Contribution 4 (detector validation) is listed although the paper says it cannot fail.** §4.4: "this validation is a consistency check, not a falsifiable test"; the surrogate is a closed-set pair-level macro-average compared against the open-set floor, and the binomial "treats the 340 pairs as independent draws, which they are not." Either demote to a limitation or state what would have falsified it. Compounded by two missing hyperparameter values that drive the panel's violation rate — the prototype detector's "fixed distance quantile" and RoNeTC's "fixed epoch budget" are never given numerically (§4.4), so the panel is not reproducible. (R2-W4 + R3-W4 + R1.)

**C14 [warning] — Convention labels are missing where the number depends on the convention.** Table 2 caption ("Both endpoints across all 990 pairs at k=5, M=1") does not state whether ε_lo uses full-n or the 20,000-flow cap, though ε_lo is exactly the column that moves with that convention — violating the paper's own §3.1 rule "we name both conditions wherever a count is reported" (Table 1 does state it). Same root cause as the "median certified lower bound" appearing as both 0.535 (§4.4) and 0.5548 (Table 2) for what should be the same 990-pair median. (R3-W7/W9 + R2 + R1.)

### Minor (confirmed)
- §7 "an alphabet-free bound **buy** headroom" → "buys". (all three)
- §1 attributes "597 of 820 pairs" to Figure 4, but that figure is the k=30 statistic (Table 5 / §4.3) while Figure 4a is computed only at k=5 — imprecise attribution. (R3 + R1)
- Figure 1 caption first line "The **EIBO** measurement" — "EIBO" appears only there, defined nowhere in the submission. (R2 cross-stage new find)
- Reference [50] links an institution-hosted PDF rather than a DOI (style inconsistency, not an anonymity issue). (R3 + R1)
- §A.7 revision residue "A follow-up asked whether…" reads as prior-round narrative; rephrase reader-facing. (R3)

---

## Reviewer Divergence

No unresolved `[REBUT]` conflicts. The cross-stage disagreements were all refinements that the raising reviewer's evidence settled:
1. **Count of certified cells (C2):** R2 said "1 of 20"; R1 and R3 corrected to "one cell on the (6) route, plus (M=2,k=5) and (M=1,k=10) on the m-free route," which strengthens the finding by exposing the §3.4/§4.2/Table 3 contradiction. No dispute on the substance.
2. **Severity of the Figure 5 drift (C6):** R2 argued minor (the figure number resolves); R3 raised it as warning. Recorded as minor navigation defect. Not load-bearing.
3. **Classification of the "D181"/filenames leak (C3):** R3 filed it under anonymity; R1/R2 narrowed it to clarity/anonymity-adjacent and defended keeping artifact filenames in the reproducibility appendix. Resolved as: remove "D181" and the revision-residue caption; keep the filenames.
4. **R1's initial format "✓" (C4):** rebutted by R3 and R2 from the render; withdrawn.

---

## ⚠️ Independent-verification gap (process note to the Research Director)

Reviewer 1 held the sole method-soundness remit. Its **independent first-review deliverable never arrived** (only a session-start check plus a 7-point plan; the deep pass timed out of the delivery channel). R1 subsequently delivered substantive soundness content **in its cross-response**, which is folded into C1, C2, C8, C10 above and is genuine independent re-derivation (notably the C8 0.2015 derivation and the C2 count correction). However, three of R1's original seven points received **no full independent write-up from any reviewer**:
- **Lemma 1 / the upper side:** whether the McDiarmid radius constant follows from its stated conditions and is genuinely tighter than the disclaimed DKW radius — **not independently re-derived this round.**
- **Eq (3) aggregation:** the 0.197 floor arithmetic was checked (407.75/2070 ✓ by R2, and R1's 0.2015 sibling), but the full aggregation derivation was not audited end to end.
- **Eq (9) m-free route:** whether the two fluctuation terms genuinely coincide at δ=α_law=0.025 with no hidden m-dependence — **not independently verified.**
These should be recorded as **not independently verified**, not as "no objection." R2 explicitly flagged the same gap.

---

## Questions for the authors

1. Which α produced the ε_hi values in the 990-row ledger — 0.05 per pair, or 0.05/990? State it once and reconcile the abstract's "≥0.95 (Bonferroni)" with §3.1's "in expectation." (C1)
2. Which (M,k) lower sides were actually computed? Reconcile §3.4 ("M=1 only"), the §4.2 (M=2,k=5)=127 count, and Table 3's "–". (C2)
3. What is 0.1858 in §A.8, and how does it relate to the 0.197 headline and the 0.2015 the 45/44 factor actually produces? (C8)
4. Does the LP-weighted certified floor (0.375) exceed max(0, 1−m/C) at every cell where both exist? If so, why is it not the headline? (C9)
5. Can a corpus-internal coverage (or re-split stability) check for ε_hi be produced, rather than the synthetic block-law model? (C10)
6. Does §A.8's "the same assumption-free property is preserved" (for the LP) contradict §3.1's "the uniform form alone preserves it"? (C11)
7. What would falsify the detector validation, and what are the prototype quantile and RoNeTC epoch-budget values? (C13)
8. Is the lower side anything other than Michel et al. [37] applied to this data, stated as a delta against the black-box leakage-estimation line? (C7)
9. Does the Open Science appendix as submitted satisfy the '27 anonymous-artifact-link requirement, and does it fit one page? (C4, C5)

---

## Missing References (from Reviewer 2, absence confirmed by Reviewer 3 against the render)

**Closest prior art — black-box leakage / Bayes-risk estimation (highest priority):**
- G. Cherubin, K. Chatzikokolakis, C. Palamidessi. "F-BLEAU: Fast Black-Box Leakage Estimation." IEEE S&P 2019, 835–852.
- K. Chatzikokolakis, G. Cherubin, C. Palamidessi, C. Troncoso. "Bayes Security: A Not So Average Metric." IEEE CSF 2023, 388–406.
- A. Veicht, C. Renggli, D. Barradas. "DeepSE-WF: Unified Security Estimation for Website Fingerprinting Defenses." PoPETs 2023(2):188–205.
- T. Chothia, Y. Kawamoto, C. Novakovic. "A Tool for Estimating Information Leakage (leakiEst)." CAV 2013, LNCS 8044, 690–695.

**Anytime-valid / confidence sequences:** S. R. Howard, A. Ramdas, J. McAuliffe, J. Sekhon. "Time-uniform, nonparametric, nonasymptotic confidence sequences." Ann. Stat. 49(2):1055–1080, 2021.
**Data-hygiene framing:** Jacobs et al., ACM CCR 55(1):6–20, 2025; Geirhos et al., Nature Machine Intelligence 2:665–673, 2020.
**Open-set, security-native:** Yang et al., "CADE," USENIX Security 2021 (relevant to §5.3's unknown-class-mass discussion; also strengthens venue fit).
**Traffic-classification architecture:** Wang et al., "NetMamba," IMC 2024.

Lines confirmed adequately covered: the shortcut/spurious-correlation critique; the open-set recognition line (Scheirer, OpenMax, Geng, Fang, Garov & Chaudhuri, RoNeTC, SepSpace, OpenCBD); the QUIC measurement line; leakage-inevitability/rate-distortion; TV estimation and closeness testing.

---

## External Review

Not requested (external review not configured for this project this round).

## Visual Layout Check (non-scoring)

The independent visual-check agent **timed out after 600s (retryable)** and produced no page-by-page findings this round. Layout observations therefore come only from the reviewers' own render inspection: the body (pp.1–13) contains no table and only Figure 1, with the primary results table (Table 3, the two-sided bracket) in Appendix A.4; the Ethics page (p.14) is ~2/3 whitespace; appendix table numbering is non-monotone in order of appearance. These are presentation weaknesses (self-containment), previously tracked as shepherd-level and non-blocking. The user may re-trigger the visual check.

## Paper Audit & Reference Verification (non-scoring)

Not dispatched this round — the submission is PDF-only with no LaTeX/BibTeX sources, so both the automated paper-quality audit and reference verification are not applicable. (A prior run on the source tree exists in the project record; its findings on internal-ID leakage and the abstract's 0.375 informed the targeted probes above, which the reviewers then verified or refuted against the render — see the Detailed Comments.)

## Issue Tracker (sync limitation — disclosed)

The cross-round issue tracker (`artifacts/review_issues.yaml`, ~75KB) could not be safely re-synced this round: it exceeds the length this session can load into context intact, and the update tool overwrites the whole file, so a reconstruction from the visible portion would silently drop unseen L14+ history. The sync was therefore **not performed** rather than performed destructively. Round-18 findings that are new or recurred on the current bytes and should be entered when the file can be loaded fully: the §3.4/§4.2/Table 3 lower-side-scope contradiction (recurrence of the L13-CR3 class in a new form); the "D181" internal-ID leak and the "relocated here from the Introduction" caption (recurrence of the internal-vocabulary class); the Open Science two-page over-length; the 0.197-vs-0.1858 headline-number inconsistency; the Figure 1 wrong-target caption; and the reviewer-delivery process gap on the soundness lane.

---

## Overall Assessment

**Verdict: weak reject (borderline).** USENIX Security qualitative reading:
- **Originality — moderate.** The per-pair two-sided TV interval on real encrypted traffic and the open-set aggregation appear new; the ingredients (ℓ1 plug-in + McDiarmid radius; Michel et al. for the lower side; Le Cam for the consequence) are not, and the paper says so. The delta against the uncited black-box leakage-estimation line (C7) is narrower than §6.4 implies.
- **Relevance — moderate-low.** No attack, defense, vulnerability, or deployment; the paper positions itself as "a measurement instrument, not a vulnerability." The auditing use is real, but the headline number is dominated by a bound requiring no measurement. Two reviewers judge the centre of gravity to be PoPETs (IMC second); USENIX Security is the weakest of the plausible venues.
- **Correctness — high in execution, ambiguous at the headline.** Re-derived arithmetic stands (the 0.197 floor, the m/C dominating bound, the overstatement figures, the radius ratio 2.91). Against that: the headline guarantee is stated three incompatible ways (C1), §3.1 and §A.8 contradict each other (C11), one headline-adjacent number is simply wrong (C8, 0.1858), and the binding assumption is validated only on a synthetic model (C10). Three core derivations (Lemma 1, the (3) aggregation, the (9) route) received no full independent verification this round.
- **Clarity — prose excellent and honest; guarantee semantics not.** The writing is disciplined and repeatedly self-critical, but the reader cannot determine what the ≥0.95 attaches to.

**Confidence — high for format/positioning, moderate for deep soundness.** All format, anonymity, and reference-presence findings were verified page-by-page in the render; the novelty gap rests on four confirmed-absent nearest antecedents; the soundness lane's three core derivations remain not-independently-verified and are flagged as such rather than cleared.

The paper is unusually careful and its honesty is above the field average — but at this venue the certified object is a single-cell measurement, the headline floor is stated to lose to a certificate-free bound while the paper's own dominating construction goes uncompared, the nearest prior art is uncited, and the central guarantee is not stated in a single unambiguous form. The two highest-leverage changes are C9 (make the LP dominance explicit or headline it) and C7 (cite and differentiate the black-box leakage-estimation line); C1/C8 (fix the headline-number semantics and the 0.1858 error) and C4/C5/C3 (the pre-submission compliance defects) are mandatory regardless of venue.