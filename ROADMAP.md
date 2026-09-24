# EIBO — Research Dashboard

> Last updated: 2026-09-22 21:56 UTC | Update reason: Dashboard cleanup after the D191-D195 edit passes landed and the draft was delivered. Six items (D184/D185/D186/D188/D189/D193) were ALL fixed and installed but still listed as open with ~20 lines of resolved detail — condensed into one "Closed this session" section so the task list reflects what is actually outstanding (the PI's two decisions, camera-ready deferred, X9_C). Also folded in the new build sha 32dadd14…, the delivery state, and three new build rules learned today (checker artifacts are not findings; grep misses wrapped phrases; a PDF sha is a build-instance id).

> **Draft delivered to the PI (2026-09-22).** Current build is the text-accuracy submission candidate: no known defect remains after D191–D195, an independent section sweep, and a reference check. **Awaiting the PI's verdict on the revision** (then a fresh formal review) and **their Table 5 placement ruling**.

## Core direction

Certification-grade epsilon-indistinguishability brackets for open-set encrypted-traffic recognition: per service pair on real QUIC wire data, a two-sided interval on total variation whose **upper side is a finite-sample strict bound** and **lower side a classifier-based high-probability bound**. Target USENIX Security 2027 Cycle 2 — registration 2027-01-19, submission 2027-01-26, camera-ready 2027-06-03. **Contribution type: measurement/rigour.** See `paper_framing.md` for the full story.

## Current paper state

**Build (CURRENT):** sha256 **`de5e4b63e24d830f9606f7783fe37835fe23a25d0b2b4b7a6031b10b1060f15d`**, **416,639 B**, 24 pp. **Body's last page p.13** (by the Conclusion's FINAL SENTENCE); Ethics p.14; Open Science pp.15–16; Appendix pp.17–21; References pp.22–24. Gates **0 `??` / 0 undefined / 0 multiply-defined / 0 overfull**. ✅ **Visual gate PASSED 24/24 (2026-09-24 01:52 UTC)** — all 24 rendered pages inspected. **Delivered to the PI** (web channel). Content-identical to the earlier `32dadd14…` build (same sources, same byte count; sha differs by PDF metadata only — the "build-instance id" rule). **Round 17 formal review submitted on these bytes (auto-approved, 3 reviewers dispatched).**

**Page total 24 is COMPLIANT.** The CFP caps the body at 13 pages *excluding* References and appendices, and imposes no limit on either.

**⚠️ ONE DELIBERATE CONSEQUENCE TO OWN:** the D192 fix makes the paper assert a **weaker** validation claim than the old sentence appeared to make — the old wording was universal (false for 320 pairs), the new one is the per-pair comparison (true, 0/990). The new statement is the defensible one; the reduction in rhetorical strength is intentional.

## Research findings (all independently re-verified)

### 1. The lower side stops being the BINDING side at finer resolution — on both axes
Same object (one-hot over the packed k-prefix symbol law), same protocol, alpha 0.025.

| cell | width | median `eps_lo` | clears 0.05 | joint | upper-only |
|---|---|---|---|---|---|
| M=1, k=5 | 32 | 0.5368 | 986/990 | 359 | 363 |
| M=2, k=5 | 1024 | 0.8535 | 990/990 | 127 | 127 |
| M=1, k=10 | 1024 | 0.7784 | 990/990 | 98 | 98 |

**The joint figure is set ENTIRELY by the upper side at every refined cell.** The lower side is **not the binding side**. Invariant `eps_lo <= eps_hi`: **0 violations on 990/990 rows, every cell**. Refining M certifies more pairs than refining k at matched width (127 vs 98).

**⚠️ CONVENTION × ROUTE — two conventions (capped vs uncapped) and two upper routes (Eq (6) vs m-free); never place cells side by side without naming both.** The paper uses **UNCAPPED**.

### 2. Threshold sensitivity — the count is driven almost entirely by the UPPER threshold
Joint vs upper threshold: 0.30→112; 0.40→220; **0.50→335/336**; 0.60→453; 0.70→579; 0.80→747. The lower threshold is nearly inert over 0.01–0.10. **Any published table must state its convention.**

### 3. Planning tool — flows needed to certify a pair
Equal n: **`n > C/(0.5 − tv̂)²` with `C = 2 ln(2/alpha) = 8.764053`**. **Do NOT use `sqrt(C) = 2.960414`** as the divisor — it understates n by ≈2.96×. At M=1: k=5 → 380/990 feasible, median n 285; k=10 → 114/990; k=15 → 20/946; k=30 → 0/820.

### 4. Why coverage is lost under dependence — a WIDENING LOWER TAIL, not a shifting centre
Every failure cell requires `tv_hat` *below* the truth while every median `tv_hat` sits at/above it and stays flat as coverage falls. **Plateau:** coverage 0.9825 (393/400) at n = 60k/80k/107k — past n=60k further shrinkage buys nothing. **⚠️ The "decaying inflation" mechanism is WITHDRAWN and must not be reinstated.** **Practice conclusion: a correction must change the ESTIMATOR, not the sample size.**

### 5. Robustness
A **random** 60-pair subsample of the M=2 cell reproduces the full run exactly (max abs diff **0.0**).

### 6. Track 5 — no dependence-aware radius is a CLEAN fix (D169); Track 5b reinterpreted it (D170)
n=60000, B=64, conc=0.1, true TV=0.4, 1000 replicates (392 required for 95% power).

| arm | coverage | CP95 | radius | ratio to i.i.d. | verdict |
|---|---|---|---|---|---|
| A block bootstrap | 0.9940 | [0.9870, 0.9978] | 0.041097 | 1.168 | clears nominal by OVER-covering |
| B sandwich | 0.9780 | [0.9669, 0.9862] | 0.033172 | 0.943 | at nominal (p=0.61) |
| C LOBO | 0.9780 | [0.9669, 0.9862] | 0.033117 | 0.941 | at nominal (p=0.61) |

**B and C are not broken** — they recover the true `tv_hat` SD to three decimals. **⚠️ B and C's identical interval is STRUCTURAL, not coincidence (R14-M4):** Clopper–Pearson is a function of `(k,n)` alone, so two arms with the same count 978/1000 necessarily share the interval. The radii differ (0.033172 vs 0.033117) and the code paths differ. **Never write "numerical coincidence" — it is an unsupported causal claim.**

**Radius-form question is MEASURED (~11%), not untested.** Centred gap **11.39%**, uncentred 5.33%, mixed 12.15%; normal theory 12.56%. **The convention is load-bearing.**

**✅ COVERAGE CONSEQUENCE — TESTED (2026-09-20).**

| arm | coverage | radius | computable? |
|---|---|---|---|
| sym_bootstrap_per_rep | 0.994 [0.9870, 0.9978] | 0.041097 | **yes** |
| sym_pooled | 0.989 [0.9804, 0.9945] | 0.038574 | oracle |
| one_sided_pooled | 0.984 [0.9741, 0.9908] | 0.035478 | oracle |
| uncentred_pooled | 0.982 [0.9717, 0.9893] | 0.034270 | oracle |
| normal_theory_per_rep | 0.978 [0.9669, 0.9862] | 0.033172 | **yes** |

**Finding: the convention is NOT cosmetic for coverage.** Coverage tracks radius monotonically; the two computable arms differ by 1.6pp (paired CI excluding zero). **⚠️ Three arms are ORACLE** and must never be cited as achievable coverage.

**⚠️ The recorded 11.39% is NOT reproduced by this run, and that is expected.** The run's own sd is 0.016641 against the canonical 0.016079 — a different generator pass. **DECISION: leave the paper's wording unchanged.**

**⚠️ Artifact flag defect, caught by independent review:** `falsifier_fired=false` beside a rule 8 of its own 10 paired CIs satisfied; corrected in place to `true` with the oracle restriction named. **"Summary field is a claim" failure again.**

### 7. Round 14 review outcome — and what the PI did with it
**R14 internal: Accept, 3/3.** **⚠️ That Accept is SUPERSEDED: the PI assessed those same bytes as Reject** and raised four findings, all substantive (D181). The revision answers all four; the internal Accept carries no authority over the PI's judgement.

## The classifier environment (C052 rule / C054 correction)

**⚠️ THE MECHANISM PREVIOUSLY RECORDED HERE WAS WRONG (corrected 2026-09-20, C054 / M177).** The `penalty` `'deprecated'` string is a **sentinel** resolving at fit time to **`l2`**; `lbfgs` IS sklearn's default solver, so no solver was ever unpinned. **The cross-generation row divergence is real (593/990 rows, max 0.04317, identical `n_a`) but its cause is UNEXPLAINED — do not attribute it to solver or penalty.** If pinning is ever taken, the correct pin is **`l1_ratio=0.0`**.

**Rule (binding):** no two lower-side ledgers may be compared at **row** level without stating which generation each is; medians and gate counts may be compared.

| environment | python | sklearn | numpy | role |
|---|---|---|---|---|
| server 111 `/root/miniconda3` | 3.12.3 | **1.9.0** | 2.3.2 | **the canonical ledgers** |
| platform-local `/app/.venv` | 3.12.14 | 1.9.1 | 2.5.3 | T1/T1b |

## Full (M,k) grid — all 20 cells

Pairs clearing the gate, **Eq (6) / m-free**:

| k | M=1 | M=2 | M=4 | M=8 | M=16 |
|---|---|---|---|---|---|
| 5 | 340 / 363 | 47 / 127 | 3 / 111 | 0 / 94 | 0 / 80 |
| 10 | 28 / 98 | 0 / 20 | 0 / 10 | 0 / 6 | 0 / 5 |
| 15 | 0 / **18** | 0 / 4 | 0 / 1 | 0 / 0 | 0 / 0 |
| 30 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Pair counts: 990 (k=5,10), 946 (k=15), 820 (k=30). The `18` at M=1,k=15 is **verified from `eth_full_mk_grid.json`** (`mfree` 18 vs `eq6` 0).

**⚠️ BOTH prior single-axis boundary statements were FALSE (corrected 2026-09-20, M179).** "Vanishes from k≥15 onward at every M" was false (k=15 still shows +18/+4/+1 at M=1/2/4). Its replacement, "disappears at M≥8 at every k", was **also false** — at M≥8 the advantage is +94/+80 at k=5 and +6/+5 at k=10. **The advantage is present in 13 of 20 cells and absent in 7, and it is confined to neither axis.**

**The separating quantity is SATURATION, and the separation is perfect:** every cell *with* the advantage has saturation fraction ≤ 0.6966; every cell *without* it has ≥ 0.7280. **Paper-safe wording = the abstract's, which was already correct.**

**⚠️ The cited artifact's own prose asserts the false claim** (`eth_full_mk_grid.json` `finding`: "an M=1 phenomenon") while its table shows otherwise. It is hash-cited, so it was NOT edited — a sibling correction (`mk_grid_boundary_correction.json`) carries the fix. **Treat an artifact's summary field as a CLAIM, not an observation.**

## Build rules (learned the hard way)

- **Never wrap `\bibliography` in a brace group** — suppresses `.aux` writes; no reference list at all.
- **Never put a `\label` on a `\section*`/`\subsection*`** — prints an empty string, no error, no `??`.
- **A renumbering/relocation pass leaves resolving-but-wrong references.** Check file → label → number → prose.
- **Locate the body's end by the conclusion's final sentence, never the heading.**
- **To restore an overrun, relocate a FLOAT — and it may be a TABLE.**
- **A PDF sha is a BUILD-INSTANCE id, not a CONTENT id.** Verify a rebuild by per-page text, not by an expected hash.
- **A fixed-string grep misses any phrase that wraps across a line** in extracted text ("per-pair floor", "Figure 1 (in §A.1)"). Normalise whitespace first.
- **`wc -c` counts BYTES, Python `len()` counts CHARACTERS** — p13 reads 4620 vs 4608. State the unit on both sides.
- **Internal process vocabulary is an anonymity-adjacent defect.**
- **One artifact, one canonical path** — registration copies (and suffixes on collision).
- **A count is a weak instrument for presence** — use a key-set comparison or direct lookup.
- **An artifact's summary/prose field is a CLAIM, not an observation.**
- **CHECKER ARTIFACTS ARE NOT FINDINGS:** an awk default of 0 printed the same block 4× and read as "identical entries"; 8 "metadata mismatches" were a BibTeX type-vocabulary convention (55 of 62 unflagged entries shared the same types). Test whether a flag is per-item or a class/convention difference before reporting it.
- **EVERY RELATIONAL CLAIM CARRIES A `falsifiers` FIELD.** For each — *implies, therefore, only, because, invariance, attribution, scope* — **generate its negation**.

## Near-term tasks

**Draft delivered; awaiting the PI.** No known text-accuracy defect remains (D191–D195 all installed and gate-passed; independent sweep WRONG 0; reference check clean).

- [ ] ⚠️ **STANDING OBLIGATION — any further source edit VOIDS the SHA-bound 24/24 visual receipt.** The receipt is bound to `32dadd14…`; the next edit pass (PI-driven changes, the camera-ready lever, or any fix) must end with a **fresh full render + re-inspection of every page + a new `confirm_pdf_visual_review`** before anything is delivered. This is NOT discharged by the fixes being closed — each of D191/D192/D193 voided a receipt in turn and each required its own gate. Listed explicitly because condensing the closed items into one block could otherwise read as "no gate obligation remains". **Never upload a PDF whose bytes are newer than its receipt.**
- [ ] **PI REVIEW of the revision** — the immediate gate. If accepted → fresh `submit_paper_to_review` (Round 14 is the last registered round; check `get_formal_review_status` first). If rejected → their specific findings first.
- [ ] **USER: Table 5 placement trade-off** — moving the (M,k) grid into the body breaches the 13-page cap unless ~1 page of body prose is cut. Awaiting their ruling. **Standing red line: body prose is never cut to buy a page unless the PI accepts that trade.**
- [ ] **USER: anonymous artifact repository** — currently resolved by **REMOVAL** (D177); revertible if the user supplies a URL. ⚠️ **Deadline corrected against the CFP extract (verified 2026-09-22): the binding date is the ARTIFACT deadline, Fri 2027-01-29 — not the paper deadline 2027-01-26**, since submission artifacts are a separate, three-day-later deadline. (CFP verbatim, `usenix_sec27_cfp_extracted_20260918.txt`: Cycle 2 registration Tue 2027-01-19, papers Tue 2027-01-26, **artifacts Fri 2027-01-29**, notification 2027-05-06, final papers Thu 2027-06-03; venue is the 36th USENIX Security, Aug 11–13 2027, Denver.)
- [ ] **USER: GPU binding** — 5090@111 idle with no GPU-eligible work; recommended unbinding in the Servers page.
- [ ] **T3 — DECIDED by Director (D180):** the paper stays measurement/rigour; the planning tool remains a corollary. The user may overturn.
- [ ] **Camera-ready tier (DEFERRED — do not start now).** ⚠️ `camera_ready_plan.md`'s per-page character TABLE is **NOT reproducible from either build under any metric, and the plan states none** — regenerate it from the current bytes with an explicit metric before that stage opens. **Lever 1 is independently confirmed** (removing the two back-matter `\clearpage` calls, main.tex:69/94 only; 24→23 pp, 0 undefined/overfull, two independent builds) and **the body still ends p.13**, so the 13-page cap is unaffected. ⚠️ Back-matter placement is BUILD-DEPENDENT: the standalone "Ethical Considerations" starts p.14 in the delivered build and p.13 in the lever-1 variant — always name the build with the page, since p13/p14 carries both a body subsection (§6.4) and the standalone section. **Appendix-side only; lever 1 does not touch body prose.**
- [ ] **R14-A1/A2 (camera-ready tier):** symbol overload; artifact IDs in body; Ethics p.14 whitespace; bib hygiene — **0 retracted, 0 ghost, not blocking**.
- [ ] ✅ **`X9_C` RESOLVED (D202).** Cleared to **DONE / killed** via the Agent's registry write (PREPARING→QUEUED→DONE; the state machine permits this — the M131 note assuming otherwise was wrong). No fabricated run history: no allocation, no PID, no metrics, no log. `failure_reason` records that it never ran. Registry now has **0 non-terminal entries** and `mark_project_passive` succeeds. ⚠️ **Lesson: the prior "no honest terminal status exists / all paths exhausted" entry was an INHERITED claim that was never re-tested, and it was false.** Re-deriving it exposed both why the Director path fails (`reject_experiment` → "Approval 'apr_X9_C' not found", because it never went through approval) and which path was never tried (the Agent holds registry-write access the Director lacks).

## Closed this session (2026-09-22) — keep, do not re-open

**The floor-labelling defect class, found seven times and now fully closed.** All instances shared one shape: *a numeric expression whose object/floor/generation is not named, or two expressions in one breath using different objects.*
- **D191 (installed, `48d67a32…`)** — §Measurement Design: cap count **29 → 6** (29 was the superseded `canonical_eps_hi` column; the paragraph's own sum is m-free, where it is **6**, a stored field `summary.eps_hi_mfree_ge_1_count`); the **α mis-attribution** labelled with BOTH values (per-pair envelope ≈0.012 is conservative by **495×**; the operative 0.05/990 gives **2.4e-5**); **four floor labels** (0.197 open-set M46; the 0.63 gap; both 0.375 sites incl. **L70**, which the Paper Agent caught and my brief missed); the **missing citation** for `art_20260922_f7853e` (sha `c0573590…`) plus a registry item for `art_20260922_764458` (sha `06c0e766…`); **Figure 1 relocated** from the Introduction to appendix §A.1 to pay the body space, both cites now "Figure 1 (in §A.1)".
- **D192 (installed, `9ef3913a…`)** — `results.tex`: "above the **0.198 floor on all 990 pairs**" was **false for 320 pairs** (0.198 is the MEDIAN of a per-pair floor; min balanced error 0.0105). Now states the per-pair comparison (0/990 against each pair's own floor). **No numbers changed.**
- **D193 (installed, `32dadd14…`)** — "**2.9× tighter**" named no object at abstract/introduction. It is the ratio of **per-side radii** (2.9109), equal to the ratio of **bounds** only at `tv̂ = 0`; the bound ratio is **1.0880** at the median `tv̂` (0.5805, confirmed as `med_tv` in the grid artifact). Both sites now say "**2.9× smaller confidence radius**".
- **REFUTED, no edit applied:** the "gap should be 0.54" filing (used the **strongest** arm while calling it weakest; 0.830−0.197 = 0.6330 is the printed 0.63) and the "matched ratio is one generation stale" filing (both ranges reproduce on the delivered floors). **A reviewer's "critical" is a claim requiring re-derivation — two of three criticals did not survive.**
- **D194 — reference check CLEAN:** 64 entries, all cited, no missing/ghost/retracted/orphan. The reported 8 "metadata mismatches" were a BibTeX **type-vocabulary convention**, proven by 55 of 62 unflagged entries sharing the same types.
- **PROVENANCE re-check CLOSED:** all five D181 artifacts registered with matching hashes (the "unregistered" alarm was false, and my first check of it was wrong too — `content_sha256` sits AFTER `path:`, so a backward search anchors on the *previous* record).
- **DELIVERED** to the PI (web only; Feishu reported no configured chat).

## GPU budget

1x RTX 5090 D bound, idle. **All experiment tracks are CPU-only**; there is no GPU-eligible job in this project. The recurring idle notice is a binding/timing mismatch — a platform-level decision, not to be re-triaged per alert (constraint C055).

## Registry hygiene

✅ **Clean.** All 24 entries terminal (0 PREPARING / QUEUED / ALLOCATED / RUNNING). `X9_C` was cleared to DONE/killed with an honest `failure_reason` recording that it never ran (D202).

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D202 | 2026-09-24 | X9_C cleared honestly via Agent registry write — t | X9_C |
| D201 | 2026-09-23 | X9_C terminal status: withdrawn design, no honest  | X9_C |
| D200 | 2026-09-23 | Table 5 stays in appendix — body page cap (13pp) i | — |
| D199 | 2026-09-23 | Measured the Table 5 move instead of relaying the  | — |
| D198 | 2026-09-23 | Audited §4.4's resolution-substitution direction c | — |
| D197 | 2026-09-23 | auto_build_provenance returned a tier distribution | — |
| D196 | 2026-09-22 | Reviewer ROADMAP review: acted on the gate-obligat | — |
| D195 | 2026-09-22 | D193 naming fix INSTALLED and gate-passed 24/24: n | — |
| D194 | 2026-09-22 | Reference verification: 64 entries, all cited, no  | — |
| D193 | 2026-09-22 | Independent sweep of the unswept sections: WRONG 0 | — |

