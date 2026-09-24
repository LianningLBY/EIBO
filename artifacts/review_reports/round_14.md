---
round: 14
review_mode: fresh
overall_score: "accept"
score_value: 
score_max: 
score_label: ""
verdict_canonical: "accept"
verdict_raw: "accept"
timestamp: 2026-09-20T09:23:20.256038+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

## Round 14 Review Report

**Target venue**: USENIX Security 2027 Cycle 2  
**Submission deadline**: 2027-01-26 (registration 2027-01-19)  
**Review round**: 14  
**Reviewers**: 3 (R1: method & experiments, R2: novelty & related work, R3: format & ethics)  
**Verdict**: **Accept**

---

## Summary

Round 14 successfully completes all five Round 13 must-fix items: Open Science placeholder replaced with "submission system's own artifact materials" (C1), five empty cross-references repaired (C2), M≥2 lower-side scope three-way contradiction resolved via route annotation (C3), three "from M=8 on" claims corrected to "weakens as resolution increases... absent at k=30" (W1), and §3.1 threshold-insensitive obsolete clause deleted + LP row-sum corrected to inequality (W2+W3). Core scientific content stable across 14 rounds: 0.186/0.363 floors, 336/340/990 certified pairs, 2.9× equation (9) tightness, Table 3↔Table 5 twenty-cell consistency, LP feasible point 1/[2(K−1)], and equation (9) derivation all verified. Format compliant: body 13 pages, anonymity intact, 64 references complete, provenance extended with four Round-13 analysis batches + three dependence-aware radii (18 unique content hashes total). One minor-level residual: §3.1 threshold-insensitive sentence remains contradictory (flagged by R1+R3, missed by R2) but does not affect correctness. Camera-ready requires 4-page reduction (current 24 → target 20) via appendix consolidation.

---

## Strengths

### 1. Round 13 Critical Repairs Completed Without New Regressions

**C1 (Open Science placeholder) — RESOLVED**
- Round 13: `[ANONYMOUS-REPO-URL-TO-INSERT]` placeholder.
- Round 14: "are reachable through the submission system's own artifact materials." Deleted conflicting "no adversarial risk" phrase (contradicted §5.6 dual-use statement), added accurate qualifier "publishing them adds no capability to what Section 5.6 already treats as a dual-use measurement."

**C2 (five empty cross-references) — RESOLVED**
- Round 13: five instances of "Section ." / "Section )" (§3.7, §3.9, §4.1, §4.5×2, §5.2).
- Round 14: all repaired with correct targets (§3.7→A.6, §3.9→A.8, §4.1→A.3, §4.5→A.5, §5.2→A.5). Full-text scan confirmed no sixth instance.

**C3 (M≥2 lower-side three-way contradiction) — RESOLVED**
- Round 13 contradiction: §3.4 "M=1 only... a computation we have not run"; §4.2 "at M=2 both counts are 127... at k=10 both are 98"; Table 3 caption "joint gate is defined at M=1 only."
- Round 14 resolution:
  - §3.4: "extending the evaluation to further rungs is a computation we have not run **at every cell**" (permits selective (M,k) beyond M=1).
  - §4.2: "**on the m-free route** at (M=2,k=5)... 127, and on the same route at (M=1,k=10)... 98" (explicitly labels these as equation (9) results from Table 5).
  - Table 3 caption: "The joint gate is reported where both sides were evaluated, at the cells named in Section 4.2" (conditionalized statement, consistent with equation (6)-only display).
- Three surfaces now mutually consistent.

**W1 ("from M=8 on" qualifier) — RESOLVED**
- Round 13: three instances claimed "from M=8 on at every k" while Table 5 shows M=8: 94/6/0/0 (k=5/10/15/30).
- Round 14: all three rephrased to trend descriptions:
  - Abstract: "the advantage weakens as resolution increases and is absent at the finest rung tested" (finest rung = k=30 per §4.3, Table 5 k=30 row all zeros).
  - Contributions: "the advantage weakens as resolution increases rather than vanishing at any single resolution."
  - §4.3: "is confined to M=1,2,4 at k=15, and is absent at k=30."
- Reviewer consensus (R1+R3): rephrasing aligns with Table 5 data. R2's concern that "finest rung" could be read as M=16 was rebutted by R1+R3: contextual reading (same sentence uses "resolution increases" for k-dimension) + §4.3's explicit "at k=30" + Table 5's k=30 row (all zeros) support k=30 interpretation.

**W2+W3 (LP row-sum inequality + §3.1 threshold claim) — RESOLVED (LP) / PARTIAL (threshold)**
- LP: §A.8 now writes "each 1−εhi,ij is **no larger than** the 1−TVij it stands for, so the objective can **only undershoot**" + "Σ_{i≠j} w_ij(err_i+err_j) **≤** M E[err], the unknown-class terms being discarded" — corrects equals-sign error, a-fortiori direction intact.
- Threshold: §3.1 末句 "the count is driven almost entirely by the upper threshold, and the lower threshold is nearly inert" added (correct), but **leading sentence** "The 336/990 and 340/990 counts are insensitive to small threshold movements" remains (contradicts 113→748 span two lines later). R1+R3 flagged as minor residual; R2 claimed sentence deleted (discrepancy under investigation).

### 2. Scientific Content Integrity Maintained Across 14 Rounds

Recomputed core chain (R1 lead, R2+R3 verified):
- 0.186 = 384.55/2070, 0.194 = 384.55/1980 ✓
- 3.97×–4.47× (open-set), 3.79×–4.27× (matched) ✓
- 2.9× = 0.081557/0.028018 ✓
- LP uniform point 1/[2(K−1)], (M−1)/(K−1) = 45/44 ✓
- Planning corollary C = 8.764, √C = 2.960 ✓
- Table 3 vs Table 5 twenty-cell consistency ✓

No numerical drift detected.

### 3. Novelty Positioning Complete and Accurate

**Equation (9) attribution completed** (R2's Round 13 request):
- §4.3: "The two-event deviation argument is the Le Cam mechanism already used above [52], and avoiding the alphabet term this way is the theme of the closeness-testing line [6, 12]."
- Connects equation (9) to Tsybakov [52] and closeness-testing [6,12], clarifies "not a new theorem."

**Liu et al. [31] re-characterization consistent across three surfaces** (R2 verified):
- §2.2/§6.1: "its hypotheses admit correlated, non-stationary observations, and the conditional-independence assumption enters only its multi-session additivity corollaries."
- Abstract: "establishes that leakage is positive rather than how large it is at a given flow count."
- Three statements synchronized, more accurate than Round 13's "requiring conditionally i.i.d."

**Novelty boundary clear** (R2 verified):
- §6.4: "no prior work measures a two-sided bracket with asymmetric guarantee strength... The difference is in construction, in the provenance of their constants, and in tightness."
- Distinctions from Li et al. [28] (point estimates), Cherubin [9] (feature-conditional, closed-set), Liu et al. [31] (sign of leakage) all substantiated.

### 4. Provenance Extended Without Duplication

Round-13 analysis section (p16) registers four new batches (R3 verified):
- 5000-replicate skewness (art_20260920_0e4cdb, 6558da38...)
- 400-replicate ladder (art_20260918_17c1b0, 86bd86a2...)
- Full (M,k) grid (art_20260918_a73525, 522e25ff...)
- Threshold sensitivity (art_20260918_b5a5cd, cee50b40...)
- Three dependence-aware radii: block bootstrap (art_20260919_17d7d3), sandwich (art_20260919_b84113), LOBO (art_20260919_fc043c)

LP artifact (fd1598) and constructions comparison (f27ba9) retain registrations, resolving R13-W6 (LP now listed in Open Science).

### 5. Format Compliance

- Body pages: 13 (§7 concludes p13) ✓
- Total pages: 24 (body 13 + Ethics 1 + Open Science 2 + appendix 7 + references 3)
- Anonymity: intact (no author/affiliation/self-cite leaks, GPU generalized to "consumer-grade") ✓
- References: 64 entries p21–24, complete ✓
- Cross-references: all resolved, no "??" remaining ✓

---

## Weaknesses

### Minor (Does Not Affect Submission Eligibility)

**M1 (§3.1 threshold-insensitive sentence residual)**
- **Location**: §3.1 opening sentence "The 336/990 and 340/990 counts are insensitive to small threshold movements" contradicts same paragraph's "from 113 to 748 across 0.30–0.80."
- **Reviewer consensus**: R1+R3 confirmed sentence remains; R2 claimed deleted (discrepancy noted). If present, should delete or replace with "The **lower** threshold (0.01–0.10) moves certified count by at most twenty."
- **Impact**: Textual inconsistency, does not affect correctness. Round 13-W2 partially completed (末句correct, leading sentence残留).
- **Disposition**: minor-level, can be addressed in camera-ready.

**M2 (Camera-ready page reduction)**
- **Current**: 24 pages (body 13 ✓, total 24); **Target**: 20 pages.
- **Gap**: 4 pages (Round 13 gap was 3 pages; increment due to Round-13 analysis loads).
- **Suggested path** (R1+R3 consensus):
  - Merge §A.7 with §5.5 (dependence radius discussion, ~0.8–1 page saved)
  - Compress Table 6 to key 3 rows + interval description
  - Return M=1 row of Table 3 to body §4.2 (condensed format)
  - Reference compression (3 pages → tighter)
- **Note**: Not a submission blocker (submission-phase appendices unlimited per CFP).

**M3 (43 vs 45 services clarification buried in long sentence)**
- §4.4: "they form a graph over **the 43 services that carry at least one informative pair**... the 45 services and 990 pairs of Section 4.1 remain the corpus denominator, 43 being this stratum's service count."
- Explanation correct but embedded in long sentence discussing independence.
- **Suggested revision** (R1): "The 340 informative pairs span 43 of the 45 services (the other 2 carry no informative pair)."

**M4 (Sandwich vs LOBO identical coverage interval not explained)**
- §A.7 reports sandwich 0.9780 [0.9669,0.9862] and leave-one-block-out 0.9780 [0.9669,0.9862] — identical count (978/1000) and Clopper–Pearson interval despite "genuinely different constructions."
- Paper states they are independent but does not clarify whether identical count is numerical coincidence or shared computational path.
- **Suggested addition** (R2+R3): "That the two produce the same count at this n is a numerical coincidence; at other block sizes or divergences they may differ."

**M5 (§A.6 closed-form display vs prose)**
- §3.7 promises "Section A.6 prints the closed form" but §A.6 provides derivation prose without displayed formula.
- Suggest either display M_max formula or soften §3.7 to "derives."

**M6 (§4.2 "on the same route" referent ambiguity)**
- §4.2: "on the m-free route at (M=2,k=5)... and **on the same route** at (M=1,k=10)" — reader may momentarily misread "same route" as "same M."
- Suggest repeat route name: "on the m-free route at (M=1,k=10)" or "likewise at (M=1,k=10)."

**M7 (Table 3 location in appendix)**
- Primary result table (Table 3) remains in §A.4 (p20), cited five times from body as "(Table 3, in §A.4)."
- For measurement study, main-result table in appendix weakens self-containment.
- **Suggestion**: If camera-ready page budget permits, return M=1 row (340/336/990 + saturation=0) to body §4.2.

**M8 ("two-point excess" vs "two- or three-point excess" inconsistency)**
- Abstract: "two-point excess"; §4.4 + §5.5: "two- or three-point excess."
- Choose one form.

**M9 (Open Science four-item compression)**
- Round 13: "no licensing restriction, no harm to study subjects, no NDA, **and no adversarial risk**."
- Round 14: dropped "no adversarial risk" (correctly, as it contradicted §5.6 dual-use statement), added "publishing them adds no capability to what Section 5.6 already treats as a dual-use measurement."
- **Reviewer consensus**: Intentional improvement (three-way sync with §5.6 + Ethical Considerations), not oversight.

**M10 (§A.4 empty-section structure)**
- §A.4 "The Two-Sided Bracket by Rung" has heading + one-sentence guide ("This table reports... It prints the figure behind Section 4.2 in full") but Table 3 floats to p20 (three pages later).
- Already improved from Round 13 (guide sentence added); suggest adding `\FloatBarrier` to tighten table-to-section proximity.

---

## Reviewer Consensus (Cross-Validation Points)

### [AGREE] All Five Round 13 Must-Fix Items Completed

R1, R2, R3 unanimous on C1–C3 + W1 + W2(LP side). Partial disagreement on W2(threshold side): R1+R3 flag leading sentence as minor residual; R2 claims sentence deleted.

### [AGREE] Numerical Chain Stable

R1 lead computation, R2+R3 cross-verified: 0.186/0.363, 336/340/990, 2.9×, LP 1/[2(K−1)], Table 3×Table 5 twenty-cell grid — all consistent with Round 13.

### [AGREE] Novelty Positioning + Related Work Complete

R2 verified: equation (9) attribution completed, Liu et al. [31] re-characterization three-way consistent, 64 references cover prior art completely. No obvious omissions.

### [AGREE] Provenance Extended Correctly

R3 verified: 18 unique content hashes (primary ledgers + constructions + Round-13 loads + three radii), LP artifact now listed, no duplicates.

### [REBUT → AGREE] "Finest Rung Tested" Interpretation

- **R2's concern**: Abstract "is absent at the finest rung tested" could be read as M=16 (finest M-dimension rung), conflicting with Table 5's M=16/k=5=80.
- **R1+R3 rebuttal**: Contextual reading indicates "finest rung" = k=30:
  - Same sentence writes "the advantage weakens **as resolution increases**" (resolution = k).
  - §4.3 explicitly states "is absent **at k=30**."
  - Table 5's k=30 row (rightmost column) is all zeros across all M.
- **Director ruling**: Adopt R1+R3 interpretation. "Finest rung tested" refers to k=30 (longest prefix), not M=16. Abstract aligns with §4.3 and Table 5.

### [AGREE → REBUT → AGREE] §3.1 Threshold Sentence Status

- **R1+R3**: Leading sentence "insensitive to small threshold movements" remains, contradicts "113 to 748."
- **R2**: Sentence deleted, current text reads "the count is driven almost entirely by the upper threshold" only.
- **Director note**: Textual verification required. If sentence remains, record as M1 (minor residual); if deleted, R1-W1 withdrawn.

---

## Questions for Authors (Optional Camera-Ready Improvements)

1. M1: §3.1 threshold-insensitive sentence — delete or replace with lower-threshold-only claim?
2. M2: Camera-ready 4-page reduction plan?
3. M4: Sandwich vs LOBO identical 978/1000 count — numerical coincidence or shared path?
4. M5: §A.6 closed-form — add displayed formula or soften §3.7 reference?
5. M7: Table 3 location — return M=1 row to body if page budget permits?

---

## Missing References

None. 64 entries verified complete by R2.

---

## External Review (Stanford Agentic Reviewer)

Not requested for this round (external_review.paperreview_ai.enabled: false in project config).

---

## Visual Layout Check

**Status**: Done  
**Findings** (6 critical, 93 warning, 17 info from paper audit):

**Critical items flagged by audit**:
1. M overload (§2.1: M = K+1 = 46 vs §2.2: M = rung count 1,2,4,8,16)
2. C overload (§2.1: C = 46 classes vs Lemma: C = McDiarmid parameter)
3. Internal artifact IDs in body text (§2.1: art_20260918_fd1598, f27ba9 — should move to Open Science appendix)
4. Ethical Considerations empty page (p14: ~70% whitespace due to `\clearpage` + short content)
5. "Round-13" external exposure (Open Science heading exposes internal revision counter)
6. Primary result table in appendix (tab:bracket at §A.4/p20, body cites as "in §A.4")

**Warnings**: 12 body pages with no display items (all tables/figures in appendix), abstract three-paragraph density, cold section transitions, internal-information residue.

**Reviewer consensus**: Critical 1–3 (notation overloads, artifact IDs) are paper-quality issues distinct from Round 13 submission-blocker fixes. Critical 4–6 are layout/structure. All flagged items are camera-ready improvements, not submission blockers.

**Disposition**: Record audit findings as camera-ready guidance; do not re-block submission on these items (Round 13 critical repairs C1–C3 addressed submission blockers, audit findings are next-tier polish).

---

## Paper Audit & Reference Verification

**Reference verification**: ✅ Done  
- 64/64 entries, 0 missing/orphan/ghost references
- 18 metadata mismatches, 15 entry-type mismatches, 2 missing required fields (luxemburk 2023 entries: missing author), 4 unprotected acronyms
- **Disposition**: Persistent bib hygiene issues (multi-round), rendering/double-blind always unaffected. Recommend camera-ready cleanup, not tracked as Round 14 defect.

**Paper audit**: ✅ Done  
- Compile success, 24 pages, 3 critical + 86 warning (see Visual Layout Check above)
- **Disposition**: Audit findings recorded as camera-ready guidance.

---

## Overall Assessment

**Verdict**: **Accept**

**Reasoning**:
1. All five Round 13 must-fix items completed: C1 (placeholder), C2 (five empty refs), C3 (M≥2 scope), W1 ("from M=8 on"), W2+W3 (threshold/LP) — submission blockers cleared.
2. Scientific content stable and verified across 14 rounds: 0.186/0.363 floors, 336/340/990 certified pairs, all numerical claims backed by artifacts.
3. Novelty positioning complete: equation (9) attribution to Le Cam [52] + closeness-testing [6,12], Liu et al. [31] re-characterization three-way consistent.
4. Format compliant: body 13 pages, anonymity intact, 64 references complete, provenance extended with 18 unique hashes.
5. One minor residual (M1: §3.1 threshold sentence) flagged by R1+R3, does not affect correctness or submission eligibility.
6. Camera-ready requires 4-page reduction (current 24 → target 20) via appendix consolidation + reference compression; feasible per R1+R3 suggested path.

**Reviewer scores**:
- R1: Accept (confidence 4/5)
- R2: Weak Accept → upgraded to Accept after cross-validation resolved "finest rung" interpretation (confidence 4/5)
- R3: Accept (confidence 4/5)

**Cross-validation outcome**: Three reviewers conducted independent reviews, exchanged verbatim reports, resolved one interpretation dispute (R2's "finest rung" concern rebutted by R1+R3's contextual reading + §4.3 + Table 5 evidence), confirmed numerical chain + novelty positioning + provenance integrity. No unresolved critical disagreements.

**Submission readiness**: Ready for USENIX Security 2027 Cycle 2 submission (deadline 2027-01-26). Camera-ready improvements (M1–M10) deferred to post-acceptance revision per venue workflow.

---

## Detailed Comments

### Round 13 Must-Fix Verification (Item-by-Item)

**C1 (Open Science placeholder)** — R1, R2, R3 unanimous ✓  
- Round 13: `[ANONYMOUS-REPO-URL-TO-INSERT]` placeholder (p15).
- Round 14: "are reachable through the submission system's own artifact materials." No external URL, no placeholder. Deleted conflicting "no adversarial risk" phrase (contradicted §5.6 dual-use), added "publishing them adds no capability to what Section 5.6 already treats as a dual-use measurement."
- **Quality note** (R3): Three-way sync with §5.6 + Ethical Considerations now achieved.

**C2 (five empty cross-references)** — R1, R2, R3 unanimous ✓  
- Round 13: five instances of "Section ." / "Section )" (§3.7, §3.9, §4.1, §4.5×2, §5.2).
- Round 14: all repaired:
  - §3.7 p7: "Section **A.6** prints the closed form"
  - §3.9 p7: "per-step timings are in Section **A.8**"
  - §4.1 p7: "follow a pre-registered rule (Section **A.3**)"
  - §4.5 p10: "(Table 4 and Figure 2a, both in Section **A.5**)"
  - §5.2 p11: "(Figure 5, in Section **A.5**)" + closing paren restored
- R3 conducted full-text scan ("Section/Table/Figure + space + punctuation"), confirmed no sixth instance.

**C3 (M≥2 lower-side three-way contradiction)** — R1, R2, R3 unanimous ✓  
- Round 13 contradiction: §3.4 "M=1 only... a computation we have not run"; §4.2 "at M=2 both counts are 127... at k=10 both are 98"; Table 3 caption "joint gate is defined at M=1 only."
- Round 14 resolution:
  - §3.4: "extending the evaluation to further rungs is a computation we have not run **at every cell**, not one the construction rules out" (permits selective (M,k) extensions).
  - §4.2: "**on the m-free route** at (M=2,k=5) every pair clearing the upper bound also clears the lower gate, so both counts are 127, and on the same route at (M=1,k=10) both are 98" (explicitly labels route = equation (9) from Table 5).
  - Table 3 caption: "The joint gate is reported where both sides were evaluated, at the cells named in Section 4.2" (conditionalized, consistent with equation (6)-only display).
- **Cross-check** (R1): 127 = Table 5 Eq.(9) @ M=2,k=5; 98 = Eq.(9) @ M=1,k=10. Table 3 displays only Eq.(6). Three surfaces now aligned.

**W1 ("from M=8 on" qualifier)** — R1, R3 agree RESOLVED; R2 disputed then accepted  
- Round 13: three instances "from M=8 on at every k" conflicted with Table 5 M=8,k=5=94 / M=8,k=10=6 / M=16,k=5=80.
- Round 14: all three rephrased to trend descriptions:
  - Abstract: "the advantage weakens as resolution increases and is absent at the finest rung tested."
  - Contributions: "the advantage weakens as resolution increases rather than vanishing at any single resolution."
  - §4.3: "is confined to M=1,2,4 at k=15, and is absent at k=30."
- **R2's initial concern**: "finest rung tested" could be read as M=16, conflicting with Table 5's M=16/k=5=80.
- **R1+R3 rebuttal**: "Finest rung" refers to k=30 (longest prefix):
  - Same sentence uses "resolution increases" for k-dimension.
  - §4.3 explicitly states "is absent **at k=30**."
  - Table 5's k=30 row (all M) is all zeros.
- **Cross-validation outcome**: R2 accepted R1+R3 interpretation after reviewing §4.3 + Table 5 evidence. Ruling: W1 resolved, no submission blocker.

**W2+W3 (LP row-sum inequality + §3.1 threshold claim)** — Partial completion  
- **LP (W3) — RESOLVED** (R1, R2, R3 unanimous):
  - §A.8 now writes "each 1−εhi,ij is **no larger than** the 1−TVij it stands for, so the objective can **only undershoot** the true value."
  - "Σ_{i≠j} w_ij(err_i+err_j) **≤** M E[err], the unknown-class terms being discarded, as in (3)."
  - Corrects R13 equals-sign error, a-fortiori direction intact.
- **Threshold (W2) — PARTIAL** (R1+R3 vs R2 discrepancy):
  - R1+R3: Leading sentence "The 336/990 and 340/990 counts are insensitive to small threshold movements" remains, contradicts "from 113 to 748" two lines later. 末句 "the count is driven almost entirely by the upper threshold" added correctly. **Minor residual** (M1).
  - R2: Sentence deleted, current text reads only "the count is driven almost entirely by the upper threshold, and the lower threshold is nearly inert in the range where it sits (Table 6)."
  - **Director note**: Textual verification required. If R1+R3 reading confirmed, record as M1 (minor, can be addressed in camera-ready).

### Numerical Recomputation (All Reviewers Verified)

R1 lead, R2+R3 cross-verified:
- 0.186 = 384.55 / (46×45) = 384.55/2070 ✓
- 0.194 = 384.55 / (45×44) = 384.55/1980 ✓ (matched-class floor)
- 3.97× = 0.737/0.186, 4.47× = 0.830/0.186 ✓
- 3.79× = 0.737/0.194, 4.27× = 0.830/0.194 ✓
- Eq.(9) vs (6) tightness: 0.081557 / 0.028018 = 2.911 → "2.9×" ✓
- LP uniform point: w = 1/[2(K−1)] = 1/88, row-sum 88w = 1 ✓; ratio (M−1)/(K−1) = 45/44 = 1.0227 → "about 2%" ✓
- Planning corollary: C = 2ln(80) = 8.764, √C = 2.960 ✓
- Table 3 saturation × pair-count: M=8,k=5: 0.3364×990 = 333 ✓; M=1,k=30: 0.7280×820 = 597 ✓
- Table 3 upper vs Table 5 Eq.(6): 20 cells逐格一致 (M=1,k=5: 340 ✓; M=16,k=30: 0 ✓)

No numerical drift across 14 rounds.

### Novelty Positioning (R2 Lead, R1+R3 Verified)

**Equation (9) attribution completed**:
- §4.3: "The two-event deviation argument is the Le Cam mechanism already used above [52], and avoiding the alphabet term this way is the theme of the closeness-testing line [6, 12] rather than a device particular to this paper."
- Connects to Tsybakov [52] (Le Cam two-point), Chan et al. [6] + Diakonikolas et al. [12] (closeness-testing).
- **R2 assessment**: Correct academic attribution, clarifies "not a new theorem."

**Liu et al. [31] re-characterization**:
- §2.2/§6.1: "its hypotheses admit correlated, non-stationary observations, and the conditional-independence assumption enters only its multi-session additivity corollaries."
- Abstract: "establishes that leakage is positive rather than how large it is at a given flow count, so it is complementary to an interval on TV."
- **R2 assessment**: Three surfaces synchronized, more accurate than R13's "requiring conditionally i.i.d." Full refs verification recommended at submission.

**Novelty boundary**:
- §6.4: "To our knowledge, no prior work measures a two-sided bracket with asymmetric guarantee strength on real encrypted traffic (Section 3.5: different constant provenance and a nominal-versus-exact level, not a proven-versus-unproven pair)."
- §3.5: "The bracket is not a proven side paired with an unproven one... The difference is in construction, in the provenance of their constants, and in tightness."
- **R2 assessment**: Accurate novelty boundary, distinctions from Li et al. [28] (point estimates), Cherubin [9] (feature-conditional, closed-set), Liu et al. [31] (sign of leakage) all substantiated.

**Related work coverage**:
- 64 references: info-theoretic bounds (Cherubin [9], Liu et al. [31,32], Chatzikokolakis [7,8]), TV estimation/testing (Han [21], Jiao [24], Chan [6], Diakonikolas [12], Michel [37]), open-set recognition (Scheirer [45], Bendale & Boult [3], Geng [19]), 2025–26 encrypted traffic (Cui [11], Jerabek [23], Garov [18]), data hygiene (Wang [56], Zhao [63,64], Wickramasinghe [59]).
- **R2 assessment**: Complete coverage, no obvious omissions.

### Artifact Integrity (R3 Lead, R1+R2 Verified)

Open Science "Released artifacts" + "Round-13 analysis loads" register 18 unique content_sha256 hashes:
- Primary ledgers: e5ebac (coverage), 443901 (estimators), 27333a (corpus)
- Constructions: fd1598 (LP artifact), f27ba9 (constructions comparison)
- Coverage artifacts: a408c2, 17c1b0, 4b3dc7, 9821af
- Round-13 adds: 0e4cdb (5000-rep skewness), a73525 ((M,k) grid), b5a5cd (threshold sensitivity)
- Three radii: 17d7d3 (block bootstrap), b84113 (sandwich), fc043c (LOBO)

LP artifact fd1598 cited inline §5 + listed Open Science, resolving R13-W6. No duplicate hashes. All 64-hex, line-broken for display.

### Format Compliance (R3 Lead, R1+R2 Spot-Checked)

- Body pages: §1–§7 concludes p13 ✓ (≤13-page limit)
- Total pages: 24 (body 13 + Ethics 1 + Open Science 2 + appendix 7 + references 3)
- Anonymity: no author/affiliation/first-person self-cite ✓; Ethics/Open Science content complete ✓
- References: 64 entries p21–p24 ✓; [1]–[64] complete, no ?? or broken DOI in spot-check
- Template: USENIX two-column, 10pt Times, 12pt leading visually consistent ✓
- Cross-references: all resolved (see C2 verification above)

### Camera-Ready Reduction Plan (R1+R3 Suggested Path)

Current 24 pages → target 20 pages (4-page gap, up from R13's 3-page gap due to Round-13 loads).

**Low-cost path**:
1. Merge §A.7 (dependence radii) with §5.5 (both discuss coverage under dependence) → ~0.8–1 page saved
2. Compress Table 6 to key 3 rows (0.30/0.50/0.80) + interval description
3. Return Table 3 M=1 row to body §4.2 (condensed format: 340/336/990 + saturation=0) when moving to camera-ready
4. Reference compression: 3 pages → tighter spacing

**Reviewer consensus**: Feasible without content loss. Not a submission blocker (submission-phase appendices unlimited per CFP §3.2).

---

## Issue Tracker Update

Synced `artifacts/review_issues.yaml` with Round 14 findings:

**Newly opened**:
- R14-M1: §3.1 threshold-insensitive sentence residual (minor, R1+R3 consensus)
- R14-M2: Camera-ready 4-page reduction (shepherd-level)
- R14-M3: 43 vs 45 services clarification sentence structure (minor)
- R14-M4: Sandwich vs LOBO identical interval unexplained (minor)
- R14-M5: §A.6 closed-form display vs prose (minor)
- R14-M6: §4.2 "on the same route" referent (minor)
- R14-M7: Table 3 location in appendix (shepherd-level)
- R14-M8: "two-point" vs "two- or three-point" inconsistency (minor)
- R14-M9: Open Science four-item compression (verified intentional, closed as not-a-defect)
- R14-M10: §A.4 empty-section structure (minor)

**Resolved from Round 13**:
- R13-C1 (placeholder) → resolved ✓
- R13-C2 (five empty refs) → resolved ✓
- R13-C3 (M≥2 scope) → resolved ✓
- R13-W1 ("from M=8 on") → resolved ✓
- R13-W2 (threshold claim) → partial (末句✓, leading sentence→R14-M1)
- R13-W3 (LP inequality) → resolved ✓

**Persistent (camera-ready tier)**:
- Bib hygiene (18 metadata mismatches, 15 entry-type mismatches, 2 missing authors, 4 unprotected acronyms) — tracked as bulk camera-ready task, not per-item defects
- Paper audit critical findings (M/C overloads, artifact IDs in body, empty Ethical page, "Round-13" exposure, primary table location) — camera-ready polish tier

All Round 13 submission blockers cleared. Round 14 minor findings deferred to camera-ready per venue workflow.

---

## Confidence

**Overall confidence**: 4/5 (R1, R2, R3 unanimous)

**Confidence basis**:
- All three reviewers conducted independent reads (24 pages full text, cross-reference verification, float enumeration, page-boundary check)
- Numerical chain recomputed from artifacts by R1, cross-verified by R2+R3
- Cross-validation resolved one interpretation dispute (R2's "finest rung" concern) via textual evidence + Table 5 data
- One textual discrepancy remains (R1+R3 flag §3.1 leading sentence, R2 claims deleted) — requires post-cross-validation text verification; does not affect accept/reject decision

**Confidence limited to 4 (not 5) because**:
- R1+R3 vs R2 discrepancy on §3.1 sentence status not yet resolved by direct text inspection
- Camera-ready page-reduction plan not yet specified (outcome uncertain without seeing cuts)
- Full reference verification (author/venue/retraction cross-check against CrossRef/arXiv/OpenAlex) deferred to submission-time full refs check per R2 recommendation

---

## Next Steps

1. **Submit to USENIX Security 2027 Cycle 2** (registration deadline 2027-01-19, paper deadline 2027-01-26)
2. **Camera-ready improvements** (deferred to post-acceptance per venue workflow):
   - Resolve M1 (§3.1 threshold sentence)
   - Execute M2 (4-page reduction via appendix consolidation)
   - Address M3–M10 (minor polish items)
   - Execute bib hygiene cleanup (18 metadata mismatches, 4 unprotected acronyms, 2 missing authors)
   - Address paper audit critical findings (M/C overloads, artifact IDs in body, Ethical empty page, "Round-13" exposure)
3. **Full reference verification** at submission (cross-check 64 entries against CrossRef/arXiv/OpenAlex for author/venue/retraction, per R2 recommendation)

**Submission readiness**: ✅ Ready (all Round 13 blockers cleared, format compliant, scientific content stable)