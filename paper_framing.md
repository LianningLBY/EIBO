# Paper Framing — EIBO

> Written 2026-09-14, immediately after MVP PASS (see `docs/IDEA_BRIEF.md`).
> Gate/spec authority remains `memory.md`; the experiment list is `experiment_plan.yaml`.

## Target Venue
- **Primary**: USENIX Security 2027 Cycle 2 — paper deadline **2027-01-26**.
- Rationale: the contribution is **measured, auditable certification of an information limit** on real
  encrypted traffic, with an explicit hygiene regime (flow- and time-disjoint splits, packet-level splitting
  prohibited, no SNI/address side channels). That is a security-measurement paper, not an ML-architecture paper.
- **Do not silently downgrade the venue.** If the bar is not met, that is a discussion with the PI, not a
  unilateral fallback.

## Core Claims (3)

**C1 — A two-sided ε-indistinguishability bracket is computable on real encrypted traffic, with the two sides
carrying explicitly different certification strength.**
Falsifiable statement: *on the CESNET-QUICEXT-25 XS subset, at k=5 on a pre-registered coarse-grained
(direction, size) channel, **336/990 = 33.9%** of service pairs admit an interval whose **upper side is
finite-sample strict** (`eps_hi < 0.5`, given the a-priori alphabet) **and whose lower side is an asymptotic
lower bound** exceeding 0.05.* The upper side is **measured over all 990 pairs with zero assumed**.
- **The guarantee asymmetry IS the claim, not a caveat.** "Proven" is unavailable for the lower side at any
  stage; the upper side is the side an error-floor claim needs, and it is the side that **binds**.

**C2 — The certificate horizon is short, and the coarsest channel is the ONLY viable rung.**
Falsifiable statement: *the certifiable fraction shrinks monotonically in the alphabet resolution M
(**upper-only** `eps_hi < 0.5`: **0.3434 / 0.0475 / 0.0030 / 0 / 0** across M = 1/2/4/8/16), and the
saturation fraction rises monotonically (0 / 0.105 / 0.239 / 0.336 / 0.391), so the upper certificate is
lost as M grows.*
- **⚠ BASIS, CORRECTED — the series is UPPER-ONLY throughout.** The first version read *"gate 0.3394 /
  0.0475 / 0.0030 / 0 / 0"* and thereby **mixed two different quantities**: `0.3394 = 336/990` is the
  **joint gate** at M=1, while the M≥2 entries were **upper-only** counts. A per-rung **joint gate does not
  exist** for M≥2 (no per-rung lower side was computed), so a monotone claim can only be made on the
  upper-only basis, with M=1 stated as **340/990 = 0.3434**. The joint gate **336/990 = 33.9%** is C1's
  headline and is quoted **separately** — it is not an element of this series. Mixing the two made M=1 look
  *lower* than it is and put a quantity that does not exist per-rung into a monotone sequence.
- **THE MECHANISM, IN THE CORRECT DIRECTION (corrected — my first version had it backwards):** **a finer
  alphabet RESOLVES MORE, not less.** Measured `tv` medians at k=5 **rise** monotonically with M:
  **0.5805 → 0.8833 → 0.9248 → 0.9462 → 0.9673**. What fails is **CERTIFIABILITY, not resolution**: the
  certified floor is `(1 − eps_hi)/2`, so a pair that is *easily* distinguished has a *small* floor, and
  `eps_hi = tv + radius > 0.5` kills the certificate for high-`tv` pairs. **Finer M ⇒ higher channel TV ⇒
  the upper certificate is lost.** *This is a more interesting result than "finer resolves less", and the
  wrong version would be caught by any reviewer who plots `tv` against M.*
- **M=1 also has the HIGHEST `k_cert`** (17 / 8 / 5 / 4 / 3 at n=3.9e6, tv=0.30) — **not the lowest.** That
  is *why* it is the only rung retaining a certificate at k=10 (11/990 = 1.1%). The earlier parenthetical
  ("smallest alphabet, lowest `k_cert`") contradicted C2's own conclusion and is **retracted**.
- **Coarse-graining is necessary, not a concession** — and the honest reason is that the certificate is only
  available to pairs that are *close enough* on the coarsest channel, which is the opposite of a
  resolution story.

**C3 — The growth question is non-vacuous, and the standard estimator provably cannot answer it.**
**C3 has changed TYPE (D046): it is no longer a claimed sublinear-growth RATE. It is a methods/limits finding,
supported by an existence corroboration reported separately and at lower strength.** The pre-registered
statement it was *meant* to test was: *estimated over ALL 990 pairs across the full k range (5…30), the
chain-rule joint divergence `D_k` grows **sublinearly** in k, whereas the i.i.d. null predicts linear growth.*
- **⚠ THE GROWTH-RATE CLAIM IS NOT MADE. It is neither confirmed nor refuted** — see the reason below. What
  the paper reports instead is (i) a **methods/limits finding** about the estimator, which **is** the measured
  result, and (ii) an **existence corroboration** of dependence from a different route, which is
  **supporting, not the claim**.

**(i) THE METHODS/LIMITS FINDING — this is the novel content.**
- **The standard plug-in chain-rule divergence estimator CANNOT adjudicate the dependent-prefix growth
  question at these k and n, because its k-dependent sparse-context bias MANUFACTURES sublinearity.**
- **Evidence, from the estimator's own known-truth control:** on synthetic data whose analytic truth is
  **exactly LINEAR** (`p=0.30`, `q=0.70`, per-position truth `0.3389191441548814`, so
  `D_k = k × 0.3389191441548814`), it returned **SUBLINEAR** — in **both** arms, including a twin control
  built on the **REAL occupancy profile**. Its `est/true` ratio **FALLS** with k — **1.0002 at k=5 →
  0.6769 at k=30** (twin 0.9987 → 0.8824) — i.e. it **deflates large-k divergence**.
- **The mechanism is MEASURED, not asserted:** occupancy collapses with k (`frac_<5` **0.0154 → 0.9055**;
  effective n per context **64966 → 8.1**), so a per-position smoothing bias accumulates exactly where
  contexts are sparse. The fitted **SHAPE** is likewise unstable across smoothing settings (0.0 → a fit
  **outside the admissible region** at `p=1.25`; 0.5 → SUBLINEAR; 1.0 → SUBLINEAR).
- **★ IT IS ROBUST TO TWO INDEPENDENT REPAIR ATTEMPTS — which is what makes this a FINDING rather than a
  bug report:**
  - **Variant A (estimator FAMILY change; Laplace α=1 + two-sample delete-one jackknife bias correction,
    projected to the nonnegative half-line): the known-truth gate FAILED on BOTH arms.** Plain-iid exponent
    `0.552`, linear AIC advantage `−19.457`, increment ratio `5.305`; real-occupancy twin exponent `0.837`,
    linear AIC advantage `−38.649`, increment ratio `1.987`. **Real data was never touched.**
  - **Variant B (EXPOSURE conditioning; restrict to contexts with `n_P, n_Q >= T`): the gate FAILED — the
    plain-iid arm never passed at ANY `T ∈ {5,10,20,50,100}`.** And **the excluded mass needed to make
    contexts well-occupied grows to 0.608 (plain) at k=30** — **you cannot drop the sparse contexts without
    discarding most of the data.** *(Excluded mass reported explicitly at every k; no rows silently dropped.)*
    **⇒ That number is the finding's teeth: the failure is STRUCTURAL, not a tuning problem.**
- **A citable consequence, stated plainly:** replacing the estimator family, or conditioning the exposure,
  **does not** fix it; and the repair that would fix it costs **over half the data at k=30**. A practitioner
  who wants a growth-rate answer on this data needs a **different measurement design**, not a better
  hyperparameter — and this paper says so with numbers rather than asserting it.

**(ii) THE EXISTENCE CORROBORATION — supporting evidence, NOT the claim.**
- **Variant C** — a **nested-model comparison** (first-order Markov vs i.i.d., **BIC**) — is a **different
  route**: it does **not** estimate a growth rate, and it was pre-registered with its **own discriminating
  control** (an **i.i.d. synthetic case does NOT favour Markov** — IID 12/12, median `ΔBIC −21.771`; a
  **deliberately dependent synthetic case DOES** — Markov 12/12, median `ΔBIC 86689.854`;
  **control outcome: USABLE**).
- **On real data it favoured Markov for 45/45 services, at EVERY tested prefix length k=2..30, with 0 ties**
  (k=30 median `ΔBIC 110091.143`; BIC(IID) 911100.019 vs BIC(Markov) 801008.876). The two-parameter
  asymmetry is **inside** BIC; no raw likelihood advantage is reported.
- **⇒ What this establishes, stated at exactly the strength measured (D055 — SUPERSEDES D053's "the
  dependence is real"): THE VOTE IS NOT EVIDENCE.** The heterogeneous-i.i.d. arm — each flow draws its **own**
  rate from the pooled empirical per-flow rate distribution (5,058,007 flows) and then emits **30 i.i.d.
  bits**, so within-flow dependence is **ZERO by construction** — was pre-registered with the rule *"markov
  favoured for essentially all items (≥44/45) ⇒ the corroboration is DEAD"*. **It returned 45/45 Markov at
  k≥8, 98.2% overall: verdict `DEAD`.** ⇒ **C's "Markov 45/45 at every k" is fully reproduced by a
  zero-within-flow-dependence null and therefore carries NO evidence for within-flow dependence.**
  - **⚠ THIS REVERSES D053, AND D053 WAS MINE.** My original concern was right on the vote; my withdrawal of
    it was wrong. **Do not cite (ii) as evidence of dependence in any form.**
  - **⚠ BUT THE MAGNITUDE IS STILL NOT EXPLAINED BY HETEROGENEITY.** The arm's k=30 median `ΔBIC ≈ 1896`
    against the real data's **≈110,091** — **~58× larger** (the independent simulation's ~47× on the
    per-observation advantage measures the same phenomenon). So heterogeneity reproduces the **vote** but not
    the **size**. **⇒ NEITHER "the dependence is real and first-order" NOR "heterogeneity explains it" is
    correct. The honest statement: the vote is not diagnostic, and the magnitude exceeds the null without
    establishing a first-order structure** — because the i.i.d. null is a **single global `p`**, so any
    per-position marginal drift suffices. A **position-wise i.i.d. null** (or variable-order Markov
    selection) is **required** before "first-order" can be asserted at all; it is dispatched and unrun.
- **⚠⚠ MANDATORY CAVEAT:** **a Markov law beating a single global i.i.d. null on real packet data is EXPECTED
  — and worse, MEASURED here to be reproducible with zero within-flow dependence.** So (ii) is **NOT
  evidence**, not even a sanity corroboration. The content of C3 is **(i)** alone.
  growth-rate claim, and it must NEVER be read as a restored `SUBLINEAR` verdict.** **C027 remains in force:
  a route that has not cleared its own gate is not evidence for the growth claim, and a different route is
  not evidence for it either.**

- **⚠ RETRACTED, AND IT WAS LOAD-BEARING:** an earlier recorded justification held that this bias
  "**INFLATES** `D_k` as k grows … so the observed `SUBLINEAR` is **CONSERVATIVE** with respect to this
  bias." **The real control shows the OPPOSITE direction.** That note came from a *proxy construction*, never
  from the actual estimator. **It must not be reinstated in any form.**
- **★ PRE-REGISTRATION DISCIPLINE, EXTENDED (C027) — BINDING:** the null (linear) and the predicted direction
  (sublinear) are fixed before measurement, and **a candidate estimator may be applied to real data ONLY
  after it FIRST passes the known-truth control.** **A variant that has not cleared that gate is not evidence
  for C3, whatever it shows on real data.**
- **★ WINDOW, CORRECTED (retained for the record):** the first version confined adjudication to *"the set of k
  where two-sided brackets exist"* — per X1 that is **{5, 10}**, **two points**, one resting on **11 pairs
  (1.1%)**. A growth-**RATE** claim needs ≥3 points to have leverage; worse, that window was defined by **the
  object that dies first**, making "inconclusive" the **pre-determined** outcome. The corrected design
  computes `D_k` over **all 990 pairs across the full k range**, using the certified subset **only to
  validate the estimator** — separating the growth claim from the certification claim and leaving C1
  untouched. **That corrected design is what was run; its negative on the estimator is what (i) reports.**
- **STATUS: the growth question is OPEN, and the paper says so.** No further grinding for a pass. Whether the
  estimator can be replaced by a design that both clears a known-truth gate and retains the data is a
  question for future work, and the paper states it as such.

### Secondary component (reported, not a headline claim)
**Environment–content separability + the Step-0 occupancy gate.** `DST_ASN` is **demoted from an environment
axis to an audited confound** (32/53 services are single-ASN). Step-0 PASS is **provisional on the XS subset**
and is *not* closed until full-corpus month coverage confirms it. This is external-validity work; it does not
carry C1–C3.

## Story Spine

**Problem.** Open-set encrypted-traffic recognition is reported empirically — detectors publish AUROC/OSCR
with **no stated limits** — so a practitioner cannot say what error floor is *impossible* for a given
observation window, or whether a reported gain is near that floor.

**Existing approaches & their gaps.** The theory exists but in disconnected pieces: classifier-based TV lower
bounds (Michel et al.), discriminative TV estimation (Nguyen et al.), and side-channel leakage-inevitability
theory (Liu–Cheng–Liu) — the latter **single-letter**, with exponential decay only under an explicit **i.i.d.
repeated-observation** assumption, and its rate–distortion follow-up proved strictly **within the
stationary-memoryless class**. Nothing measures a two-sided, certification-graded bracket on real encrypted
traffic, and nothing tests the dependent-prefix divergence against the i.i.d. null.

**Our framing.** We treat the bracket as **two claims of different strength that may not borrow from each
other**, and we build the measurement so that each side is only ever asserted at the strength it can carry.
Two **coexisting certified objects** are reported and **may not be ranked or substituted**: a k-prefix symbol
law and a whole-flow rectified (PHIST) object. A dedicated section states why their near-equal informative
fractions are **cancellation, not corroboration**. **A third claim (C3) is reported at the strength it
reached: not as a measured growth rate, but as a methods/limits finding — the standard estimator provably
cannot adjudicate the growth question on this data — with a separately-reported existence corroboration that
the question is non-vacuous. Its negative result is reported as a finding, not hidden.**

**Headline result template.**
> *On the CESNET-QUICEXT-25 XS subset, at the coarsest pre-registered channel (k=5, M=1), **33.9% of 990
> service pairs** admit a two-sided ε-bracket whose **upper side is finite-sample strict** and whose **lower
> side is asymptotic**; a **finer alphabet strictly reduces the CERTIFIABLE fraction** — it resolves *more*, but
> the certificate is lost as `tv + radius` exceeds 0.5 — and the certificate is **lost entirely** beyond M=4.*

**Why it should matter to a security audience.** It converts "our detector got X" into "no detector can beat
Y on this window, and here is the certified interval" — and it is falsifiable at the pair level. **The C3
finding matters to the same audience in a different way: it says that a natural measurement of prefix
dependence is invalid on sparse-context traffic at these k and n, that the invalidity survives two
independent repairs, and that the repair which would work costs most of the data.**

## Anticipated Reviewer Concerns (each needs ≥1 plan entry that addresses it)
`framing_ref` in `experiment_plan.yaml` binds entries to these labels. Several were previously mitigated by
prose only, which is not a mitigation under the experiment-matrix discipline — a concern carried by a wording
rule alone is **uncovered**.

| id | concern | carried by |
|---|---|---|
| **RC1** | "This is one dataset's number, not a generalizable limit." | X4 (frontier as a function), X11 (QUIC22 replication) |
| **RC2** | "Your certificate covers only ~34% of pairs — what about the rest?" | X1 (stratum scoping), X4 (the certificate provably does not exist there) |
| **RC3** | "The lower side is asymptotic — what does it actually certify?" | **X12 — MEASURED, see §X12 below** (detector validation on the informative stratum), X6 (**the large-k side, ⚠ ASSUMPTION-LADEN / realizability-conditional — NOT distribution-free**) |
| **RC4** | "Single subset with unknown month coverage." | X10 (closes Step-0), X11 |
| **RC5** | "Side channels / the declared channel is a choice." | X9 (SNI/ECH price, measured), X7 (masking as a precondition) |
| **RC6** | "Do the brackets predict anything about real detectors?" | **X12 — MEASURED: the floor is NOT falsified on the informative stratum (9/9 cells as committed; ⚠ cell count is UNDER RE-MEASUREMENT — see the max_tpr fix below)** |
| **RC7** | "Open-set framing ignores the unknown-class mass." | **was absent ⇒ add X13 (Good-Toulmin missing-mass, deployment-site scoped)** |

**Two components of the original brief were missing from my first plan and are restored above:**
- **X12 — detector validation.** The brief's *falsifiable containment*: a pre-registered **one-sided coverage
  test** restricted to the **informative-pair stratum** (`eps_hat_k^hi < 0.5`), as a **binomial violation
  count** against the predicted floor `(1 − eps_hi)/2`, with **OSCR / FPR95 per held-out service** and the
  named baselines (LightGBM on k-packet features, SepSpace-style prototype-radius rejector, RoNeTC-style
  uncertainty-quantified rejector, frozen Pcap-Encoder probe). **Without it the paper reports brackets but
  never tests them against a detector** — which is precisely the practitioner-facing claim.
  **⚠⇒ THE PANEL IS THREE OF FOUR DETECTORS, NOT FOUR.** The frozen Pcap-Encoder probe is **`not_run`**
  (`ModuleNotFoundError`), **omitted BY DESIGN** because the authors report the pretraining model at ~800 GB —
  beyond this project's resource envelope **independently of any network reachability**. **⇒ Every artifact,
  every table, and every framing sentence must say THREE detectors; "four-detector panel" must never appear
  unqualified.**
  **⚠⇒ AND THE PRIMARY STATISTIC IS DEFINED ONLY WHERE THE INFORMATIVE STRATUM IS NON-EMPTY.** At M=1 the
  upper-side count is **340 at k=5** and **28 at k=10**, but **0 at k=15 (denominator 946)** and **0 at k=30
  (denominator 820)**. So **k=15 and k=30 yield NO validation evidence**, and the plan already pre-commits:
  *"if the informative stratum is empty at some k, that k contributes NO validation evidence and this is
  stated."* **⇒ The run must be at k=5** (the populated stratum, and C1's headline cell); k=10 is an optional
  secondary.
- **★ X12 — MEASURED (D078). THE FLOOR IS NOT FALSIFIED.** The pre-registered one-sided binomial test ran on
  the informative stratum at k=5 (the populated stratum and C1's headline cell): **3 detectors × 3 holdout
  levels, all nine cells `reject_null = false`.**
  **✅ RESOLVED — THE 9-CELL COUNT STANDS (D081).** The `max_tpr` fix ran and its acceptance gate PASSED: it
  reproduced the known-wrong values from the stored payloads before deriving the correction. Corrected values are
  **0.776–0.875 across all nine cells, far above the 0.01 guard, so the guard does not fire and no cell becomes
  `NO INFORMATION`.** **Keep two statements separate: "the guard cannot fire" (about the threshold) and "the
  quantity was miscomputed" (about the numerator population) are different claims.** The corrected
  `maximum_pair_tpr` values are **rates in [0,1] and quotable**; the old 170.5/192.9/2.10 are not. **⚠ Citable once the artifact is pulled locally — it is currently server-only.**
  (`(correct & positive).sum()`) REVIVES the `near_zero_tpr` guard at line 558, which the bug had
  disabled (the inflated numerator could never fall to <= 0.01). **Where the revived guard fires, that
  detector's rows become `NO INFORMATION` instead of `computed`, so the cell count may drop from 9 to 6.**
  **The direction is safe for the conclusion (cells can be lost, not gained), and the containment
  verdict does not consume `max_tpr` — but the NUMBER must be re-measured before it is written.**
  lightgbm 8/8/10 violations of 340 (rates 0.0235/0.0235/0.0294, p 0.9954/0.9954/0.9765);
  prototype 3/4/4 (0.0088/0.0118/0.0118, p ≈1.0); ronetc 3/3/2 (0.0088/0.0088/0.0059, p ≈1.0).
  Observed violation rates sit **below** the 0.05 null, so there is **no excess** and the pre-registered
  falsification condition (*"an excess of floor violations falsifies either the TV estimate or the declared
  channel model and MUST be reported"*) **does not fire**. Strata **340 / 540 / 110 = 990**, exactly X1's pair
  denominator. **This answers RC3 and RC6: the lower side does predict something about real detectors — no
  detector breaches the certificate at more than chance rate on the pairs where a certificate exists.**
  **⚠ THREE CAVEATS THAT MUST TRAVEL WITH IT — none may be dropped in drafting:**
  **(a) OBJECT SUBSTITUTION.** The compared quantity is a **pair-level MACRO-AVERAGE surrogate**, and it is
  **CLOSED-SET** classification error while the floor is an **OPEN-SET** error lower bound. **The citable
  sentence is "per-pair macro-average closed-set error stays above the floor on the informative stratum"** —
  never the stronger open-set reading.
  **(b) `max_tpr` / `maximum_pair_tpr` MUST NOT BE QUOTED (M115).** Those fields are computed **wrong**, not
  merely mis-named: the numerator counts correct predictions over **all flows** while the denominator counts
  only that service's positives, so values exceed 1 (up to 341; 22 of 53 services). Fix pending:
  `(correct & positive).sum()`. **The containment verdict does not consume these fields and is unaffected.**
  **(c) NO INFORMATION IS NOT A PASS.** `pcap_encoder` is `not_run` and reads `NO INFORMATION`; it contributes
  nothing and is **not** counted as a pass. Only the three executed detectors carry evidence.
  **⚠ And the `near_zero_tpr_threshold = 0.01` branch can never fire — it is dead code and must not be
  described as a guard.**
- **X13 — Good-Toulmin missing-service mass**, scoped as a **deployment-site quantity** (never a universal
  unknown prior), with Eriksson-type prediction intervals and a **mandatory 1:100-sampling sensitivity
  analysis**. Without it the open-set framing loses its unknown-class component.

## Venue Fit Risks (and how each is handled)

1. **"This is measurement, not a vulnerability."** USENIX Security does publish measurement/certification
   work, but it must land a *generalizable* limit, not one dataset's number. **Mitigation**: the bracket is a
   **function** (`M_max(k, n, tv)` is closed-form; the frontier is reported as a function of tv, never as an
   unpinned absolute), and the i.i.d.-vs-dependent question is a theory-level statement. **⚠ NOTE
   (2026-09-14, D046): the growth-rate form of that test is NOT reported as a result — the estimator provably
   cannot adjudicate it at these k and n (C3(i)). What the paper reports from that direction is the
   methods/limits finding itself; the dependence question is addressed only by the separate, lower-strength
   existence corroboration (C3(ii)), and the two must never be presented as one.**
2. **"Your certificate covers only ~34% of pairs."** **This is true and must be stated, not smoothed.**
   **Mitigation**: the claim is scoped to the stratum by construction — *"33.9% of pairs admit…"* — and the
   median pair falling **outside** the band is reported. A reviewer's natural follow-up ("so the other 66%?")
   is answered by C2: the binding constraint is the **existence** of a certificate, and it provably does not
   exist there at these k and n.
3. **"The lower side is asymptotic — so what does it certify?"** **Mitigation**: the asymmetry is stated in
   the abstract, every table, and the methods section. The lower side certifies **distinguishability**
   (it caps an error floor from above); it is never called a certificate, never called proven.
4. **"Single dataset / single subset."** **Mitigation**: Step-0's XS caveat travels with every number; the
   full-corpus confirmation is flagged as the closing condition; QUIC22 is the replication target.
5. **"Side channels."** **Mitigation**: the channel is declared as **(direction, size) only**; the exporter's
   third channel (inter-packet timing) is **deliberately excluded and said so**; no SNI/UA/TLS-extension data
   is consumed; an SNI/ECH sensitivity analysis reports the **price of ECH** as a measured delta.
6. **"Your estimator result is just a negative — why is it in the paper?"** **Mitigation**: the negative is
   **robust to two independent repairs** (estimator family; exposure conditioning), and the repair that would
   work costs **over half the data at k=30** — so it identifies a **structural** obstacle, not an
   implementation defect. It is reported with the numbers that make it checkable, and the accompanying
   existence corroboration (C3(ii)) shows the question it fails to answer is **non-vacuous**. **A negative
   that survives two repairs and is bounded by a quantified data cost is a finding, not an omission.**

## The one thing that must never be written

**The two certified objects must not be described as corroborating each other.** Their informative fractions
(340/990 and 342/990) agree only where **each uses its own radius convention**; holding the convention common
separates them by 260–600 pairs. The underlying statistics differ **2.7×** and the constants **7.34×** — two
large differences in opposite directions **cancelling**. Reporting that as a cross-check would be the single
most attractive way to overstate this work.
