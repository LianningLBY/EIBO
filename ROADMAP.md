# EIBO — Research Dashboard

> Last updated: 2026-09-14 18:20 UTC | Update reason: **D070 — MY D061 LAYER FRAMING IS OVERTURNED; RULING:
> "THE MANIFEST IS THE AUTHORITY, NOT A DIRECTORY".** Confirmed on disk: **`artifacts/<EXPID>/` is produced BY
> `register_artifact` itself** — `artifacts/X3/` is back with 4 files, the manifest carries 4 entries into it vs
> 31 into `_project/data/`, and **my layer-convention comment was overwritten**. **⇒ A one-shot merge CANNOT
> hold; `_project/` has no canonical claim.** **The invariant is EXACTLY ONE LIVE MANIFEST ENTRY PER ARTIFACT
> whose `path` RESOLVES TO BYTES** (broken resolver = defect; second live entry = defect). **Do NOT re-merge;
> both layouts coexist.** *(No per-registration consolidation: this project has shown four times today that
> per-incident discipline is what fails.)*
> **★ D069 — AXIS VALIDATION: content good, label fixed at SOURCE.** Vote construction **re-derived with
> separately written BIC logic, 0 mismatches**, incl. **S3 heterogeneous-iid → Markov 8/0/0** ⇒ **independently
> corroborates D055's `DEAD` at the vote level**. Axis test is **SENSITIVE** (dependence from `0→1,1→2,2→3` only
> ⇒ switch at k=5; observed **IID k=2,3 → MARKOV k=4 → IID k≥5** — a **single-point flip**). Parametric residuals
> **max 1.07e-14**, **k=1 boundary residual disclosed**; **`route_repaired: false`**. **⚠ The script HARD-CODED a
> bare `"parametric_artifact": "verified-correct"`** — which would read as **D057 overturned**. **Fixed at the
> SOURCE** to *"axis-verified; conclusion remains NON-DIAGNOSTIC per D057"* + notes. **A prose-only fix would let
> it re-mint on the next run.**
> **★ D065 — X6 COMPLETED AND DELIVERS C2's MEASUREMENT:** non-empty exactly where the plug-in certificate is
> lost (**100% nontrivial at k=15/20/25/30**, informative **0.9989/1.0/1.0/1.0**).
> **⚠⚠ ITS VALIDITY GATE CANNOT FAIL FOR ~75/120 ROWS (D071).** `violation = bound > truth + 1e-12`, and at
> `VALIDITY_SAMPLE_SIZE = 400` the bound **clips to 0** (classifier errors ≈ chance ⇒ raw bound negative);
> **a 0 bound can never exceed a non-negative truth**, and **all 24 truth-0 rows are incapable by
> construction**. **⇒ the honest form is "96/96 TESTABLE rows comply" (n raised 400→20,000), NOT "0/120 violations"; 24 rows remain vacuous, all at `requested_tv = 0.00`.**
> **The artifact recorded `vacuous`/`raw_bound_went_negative` per row — it did not conceal; what it omits is a
> testable/vacuous COUNT.** Fix: add `testable_replications`/`vacuous_replications`, raise the sample size to
> the real-data order (20,000) and re-run, plus a precondition asserting a minimum fraction of strictly
> positive bounds. **⚠ THE REAL-DATA LEG IS UNAFFECTED** (20,000/service; vacuous_count 0 at k≥10) —
> that is where C2's measurement lives. **4th instance today of a check that cannot fail.**
> **⚠ Paper caveat: 20,000-flow/service subsample vs C1's full-n upper.** **⚠ I fixed the framing's banned
> "assumption-free" wording myself — the claim-binding source was the one surface that was wrong.**
> **⚠ M115 — `max_tpr` IS A FORMULA BUG, NOT MERELY A MIS-NAME (I proved it arithmetically).**
> For **all 53 services**, `max_tpr × n_positive` is an **exact integer** ⇒ the numerator is a **COUNT** and the
> denominator is **that service's `n_positive`** — **but the numerator ranges over ALL flows, not that service's**:
> svc 0 `1.0673 × 53,116 = 56,692` against **53,116** positives; svc 1 `1.2483 × 6,009 = 7,501` against **6,009**;
> svc 13 `1.4121 × 182 = 257` against **182**. **⇒ A recall denominator with an all-flows numerator.**
> **⇒ The fix is `(correct & positive).sum()` instead of `correct.sum()`**, after which every value lies in [0,1]
> and the name becomes true. **⇒ UNTIL THAT LANDS, `max_tpr` AND `maximum_pair_tpr` MUST NOT BE QUOTED** —
> **stronger than "mis-named": a wrong value travels under a right-sounding name.**
> **⚠ Secondary: `near_zero_tpr_threshold = 0.01` CAN NEVER FIRE** (every value is far above it) ⇒ that
> NO-INFORMATION branch is **dead code — the sixth unfalsifiable check**. Not load-bearing (pcap_encoder is
> separately and correctly `not_run`), but **it must not be described as a guard.**
> **⇒ Required: a range assertion — anything named as a rate asserts `0 <= value <= 1` at production.** One line;
> it is the check that would have caught this at the source rather than at a reviewer's anomaly.
> **⇒ The containment verdict is UNAFFECTED** (it comes from `binomial_test`, which does not consume either field).
> **⚠ M127 — X9 RAN AND ITS DELTA IS CONFOUNDED; IT MUST NOT BE REPORTED AS THE PRICE OF SNI.**
> `x9_sni_channel_delta.json` (1,928,205 B) reports **`MEASURED_SNI_CHANNEL_INCLUSION_DELTA`** over **703 pairs**:
> `delta_tv_hat` **median +0.3769** / mean +0.3923 · `delta_eps_hi` **median +0.3879** / mean +0.3897.
> **Design is correct in every respect specified:** `same_flow_set_across_arms: true`, flow- and time-disjoint
> verified, k=5/M=1, service threshold 2000, buffer month 202412 unused, `cpu_only: True`, no packet-level split.
> **⇒ BUT THE TWO ARMS DIFFER IN A SECOND WAY (the artifact's own `alphabet` block):**
> **ARM A alphabet = 32** (the declared (direction,size) k=5 prefix) · **ARM B = 256^10 = 3.87e25** (the full
> fixed-width `DST_IP` storage domain) ⇒ **ratio ~10^24.**
> **⚠ AND C2 ALREADY MEASURED THAT A FINER ALPHABET INFLATES TV** (*"a finer alphabet RESOLVES MORE, not less":
> tv medians at k=5 rise 0.5805 → 0.8833 → 0.9248 → 0.9462 → 0.9673*). **⇒ So +0.38 has TWO available
> explanations — SNI separating services, or a 10^24-finer partition separating flows — and this artifact
> cannot separate them, because the SNI treatment and the cardinality treatment are the SAME treatment.**
> **⇒ The artifact carries NO control or caveat: `cardinalit` 0 hits · `control` 0 · `matched` 0 · `confound` 0
> · `caveat` 0 · `limitation` 0. Nothing warns a reader the arms differ in alphabet size by 24 orders.**
> **⇒ REQUIRED: either (a) a MATCHED-CARDINALITY CONTROL** — re-run ARM B with a random identifier drawn from the
> same fixed-width storage domain but INDEPENDENT of the SNI, holding alphabet size fixed and breaking only the
> SNI dependence (**if the delta collapses it was cardinality; if it survives it is SNI**) — **or (b) state the
> confound explicitly and refuse the "price of SNI" reading.** **UNTIL THEN the +0.39 may be reported only as
> "a partition augmented with the destination-host identifier raises measured TV by ~0.39, attribution OPEN".**
> **★ D083 — SNI ARM RULED, AND THE SPEC'S FOUNDING CLAIM IS NOW TESTABLE RATHER THAN ASSUMED.**
> The artifact's own source block **DECLARES both** fields:
> `sni_derived_destination_host_identifier_field: DST_IP` **and** `sni_field: QUIC_SNI`.
> **⇒ PRECISION (do not repeat my own slip): that is a DECLARATION by the runner, not a measurement of the H5.**
> The only location that block says was *verified* is the identifier's column. **So the premise test's first
> duty is to CONFIRM `QUIC_SNI` is actually readable from `/flows`; if it is not, report THAT and stop** —
> a declaration naming a field is not evidence the field exists. **Same defect class as everything else logged today.**
> **⇒ So the claim that the anonymised identifier is a DETERMINISTIC FUNCTION of the SNI — the claim the whole
> exclusion rests on — can be MEASURED on the shared flows in the same pass, and had NEVER been checked.**
> **(a) PRIMARY ARM stays `DST_IP`** (do NOT substitute the raw hostname — the declared channel excludes the
> identifier, and RC5 justifies THAT exclusion; a hostname arm would change the claim, not control it).
> **(b) ADD THE PREMISE TEST:** is `DST_IP` a deterministic function of `QUIC_SNI` on the shared flows? **Report yes
> or no.** **YES** ⇒ the exclusion is justified as claimed and the artifact should SAY so rather than ask a reader
> to trust it. **NO** ⇒ the object declaration's central phrase is unproven and the anonymisation destroyed
> information, which is itself a finding.
> **(c) A `QUIC_SNI` arm is DEFERRED**, triggered only by a **NO** from (b) or by wanting an explicit leak bound.
> **⇒ Same discipline as the rest of the session: turn a load-bearing assumption into a measurement.**
> **⇒ Same class as M055, where a word silently named two objects.**
>
> **★ D084 — I RETRACT MY OWN D119 §3, AND THE CAUSE OF THE X9 HEADLINE IS NOW NAMED.**
> **My instruction was to take `m` from each arm's REALIZED SUPPORT. That VIOLATES the project's own C005:**
> *"m must come from a provable a-priori reachable set, never from realized support or any data-derived quantity;
> a certificate built on a data-dependent m is invalid, **not merely loose**."* **⇒ The Worker stopped at preflight
> and read `statcore.tv_upper_bound` first — the guard at line 404 (`alphabet_size is smaller than the observed
> support`) is exactly C005 in code. **A stopped run is the correct outcome here, not a failure.** **⇒ Credited.**
>
> **★ AND THE REAL FINDING, which neither the spec nor I had: the X9 headline is an ALPHABET-CHOICE artefact.**
> ARM B declared an a-priori alphabet of `32 × 256^10 ≈ 3.87e25`. In `tv_upper_bound` the radius carries
> `0.5·sqrt(m/n)`, so with that m the term is `≈ 3.1e12` — **astronomically past 1, hence clipped to 1.0 on
> 1406/1406 observations.** That is *why* `delta_eps_hi` collapses to the identity `1 − mean(ARM A)` (M128).
> **⇒ So the +0.39 was never "SNI makes pairs uncertifiable". It was "this declared alphabet is too fine to
> certify at this n" — a property of the DECLARATION, not of the channel.**
>
> **★ THE CORRECT ARM IS C005-COMPLIANT AND IS A FAMILY, NOT A SINGLE CONTROL.**
> A **fixed, publicly declared hash of `DST_IP` into B buckets** is a provable a-priori reachable set —
> `m = 32·B` fixed BEFORE any data is seen. So run a **dose–response curve in the declared alphabet size**, and at
> **each** declared `m` run the pair that isolates the two explanations:
> **(i) `ARM B_B` = (k=5 prefix, `hash_B(DST_IP)`)** — SNI-DEPENDENT, coarse; **(ii) `ARM C_B` = (k=5 prefix,
> `hash_B(random)`)** — SNI-INDEPENDENT, SAME a-priori m. **⇒ Comparing B_B against C_B at matched m is what
> separates "SNI separates services" from "any finer partition separates flows".** Then face ARM A.
> **⇒ The X9 256^10 point becomes the EXTREME of the family, not the headline.**
>
> **★ TWO DELTAS, NEVER ONE:** `delta_eps_hi` = arithmetic residue, **zero SNI information, never quotable** (M128);
> `delta_tv_hat` median **0.377 = a real measurement**, radius-free, but it says nothing about certificates.
> **⇒ LIKELY OUTCOME, stated in advance so it cannot be spun later: at a sane declared m the inclusion arm probably
> STOPS clipping ⇒ the "SNI destroys certification" reading dissolves, leaving the true statement
> "including the host identifier raises measured TV by ~0.39".** **⇒ If that happens it is the SECOND headline
> today to dissolve on inspection — and that pattern is itself the finding.**
>
> **★ D085 — THE FOUR-RUNNER REGISTRATION WAS REFUSED FOR A FALSE REASON, AND UNDER IT IS A REAL GAP.**
> **FALSE BLOCKER:** registration was rejected for `type: code`. **The manifest ALREADY registers runners** —
> seven `.py` entries, **every one typed `intermediate`.** The allowed type was never in question; the refusal
> came from choosing a type the vocabulary does not use. **⇒ Fix: register as `intermediate`.**
> **⇒ Same shape as everything else today: a rejection whose stated reason is not its actual reason.**
>
> **★ THE REAL GAP, measured this turn:** `x6_divisibility_lower_bound.json` **self-reports**
> `runner_sha256 = 7810326c33e0d0ad…`, and the top-level `x6_divisibility_lower_bound.py` on disk **is** that
> sha — **but HEAD holds `9b5c2d4de2d6ddfe…`. ⇒ THE RUNNER THAT PRODUCED THE FINAL VERIFIED X6 ARTIFACT IS IN
> NO COMMIT.** A reader who checks out the repository gets a runner that **cannot** reproduce the artifact whose
> binding is recorded. **⇒ M124's defect surviving under a new name — and the one item here that actually
> threatens the byte-traceability claim.**
>
> **★ A second, quieter defect: two manifest runner entries bind STALE SNAPSHOTS.** Entries `c13fe7`
> (`x3_variant_b_support_conditioning.py`) and `646bc6` (`x3_control_occupancy_dose_response.py`) point at copies
> under `artifacts/_project/intermediate/` that **DIFFER from the top-level runners that execute**
> (`c2de06e0…` vs `59015898…`; `da81dabb…` vs `e741a0c2…`). **⇒ Both snapshots are legitimate frozen records and
> both carry the D056 assertion — but neither is the executor, and `646bc6` is NAMED as though it were. ⇒ An entry
> that binds a snapshot must say so, or a reader will cite the wrong bytes.**
>
> **⇒ Same discipline as the rest of the session: a binding that RESOLVES is not the same as a binding that is RIGHT.**
>
> **★ D086 — REGISTRATION IS NOT PROVENANCE: AN ENTRY THAT RESOLVES ONLY IN THE WORKING TREE.**
> The four runners are now **registered correctly** (type `intermediate`, sha matching the file on disk,
> including the two that matter: `x6_divisibility_lower_bound.py` at **7810326c…** — **the exact sha the X6 artifact
> self-reports** — and `x9_sni_channel_delta.py` at **63f2a356…**, the sha X9's run logged). **The content is right.**
> **⇒ BUT ALL FOUR ARE UNTRACKED.** Measured: every one resolves on disk, sha OK, **`tracked=False`.** So a fresh
> checkout still cannot reproduce the artifacts whose bindings we just recorded. **⇒ The entry proves the bytes
> exist on THIS disk, not that they are in the repository.**
> **⇒ ⇒ RULE: a manifest entry for a runner is complete only when the file is TRACKED. `exists + sha OK` is
> necessary and NOT sufficient — the check must name `tracked` explicitly, or it will pass on a file we could lose.**
> **⇒ Same family as everything else today: a green check that verifies the wrong thing.**
>
> **★ ALSO OPEN, and it is the same defect one level down:** the four MODIFIED top-level runners
> (`x11_feasibility_probe`, `x3_control_occupancy_dose_response`, `x3_variant_b_support_conditioning`,
> `x6_divisibility_lower_bound`) carry fixes that exist only in the working tree — `x6`'s artifact says
> `7810326c…` while **HEAD holds `9b5c2d4d…`.** **⇒ Both halves must land in the same commit, or the bindings stay
> half-true: registered but unpushed, or pushed but stale.**
> **⇒ Same discipline as the rest of the session: a binding that RESOLVES is not the same as a binding that is RIGHT —
> and neither is the same as a binding that SURVIVES.**
> **⇒ Same discipline as the rest of the session: turn a load-bearing assumption into a measurement.**
> **⚠⚠ AND M128 SHARPENS THIS FROM A CONFOUND INTO AN ARITHMETIC PROOF — `delta_eps_hi` IS NOT A MEASUREMENT.**
> From the artifact's own `sensitivity_to_channel_inclusion`: `inclusive_arm_clipped_fraction = 1.0`,
> `excluded_arm_mean_eps_hi = 0.6102972071320967`, `aggregate_delta_eps_hi = 0.3897027928679033`, and
> **`1.0 − 0.6102972071320967 = 0.3897027928679033` — IDENTICAL to the last digit.** ⇒ **the delta is the CEILING
> minus ARM A's mean, carrying ZERO information about SNI.**
> **Per-pair (1406 observations = 703 pairs × 2 splits): ARM A `eps_hi ≥ 1.0` in 67 (4.77%); ARM B in 1406 (100.00%).**
> **Mechanism, from `src/eibo/statcore.py`: `radius_1 = 0.5·sqrt(m/n)`.** ARM B's **`m = 32·256^10 = 3.87e25`**
> ⇒ at n≈700k, **`radius_1 ≈ 3.7e9 ≫ 1`**, so **the bound cannot do anything but clip.** **The artifact even flags
> the cause without drawing it: `realized_support_not_used_for_m: True`.**
> **⇒ AND MY ARM C SPEC WAS WRONG: matching `m` to ARM B's (256^10) would reproduce the saturation exactly and make
> the control VACUOUS.** **⇒ The correct control holds the REALIZED SUPPORT equal and varies only the SNI dependence:**
> ARM A as-is · **ARM B′** (SNI-inclusive, `m` from the realized distinct (prefix, DST_IP) count) · **ARM C** (random
> 10-byte per-flow identifier, SNI-independent, `m` from its own realized support). **Each arm reports its realized
> support and an explicit clipping flag; a saturated arm must be reported AS saturated, never averaged into a delta.**
> **⇒ FRAMING: X9 cannot price the exclusion at this n — a 256^10-symbol alphabet is not estimable from ~10^6 flows.**
> **That is a C3-shaped ESTIMATOR LIMITATION, not a defect in the exclusion**, whose channel-declaration argument
> stands independently.
> **★★★ D078 — k=5 CONTAINMENT RESULT: THE FLOOR IS NOT FALSIFIED. C1's MISSING PIECE HAS LANDED.**
> `X12_k5` COMPLETED 18:12; artifact 191,867 B (sha `14f0f581…`), GPU released. **I read all 9 cells myself.**
> **Design:** 3 detectors × 3 holdout levels on the **informative stratum (340 pairs)** — a pre-registered,
> ONE-SIDED binomial test (`scipy.stats.binomtest`, α=0.05 **unsplit**, `alternative='greater'`) of whether
> per-pair detector error breaches the theoretical floor `(1 − eps_hi)/2` more often than chance.
>
> | detector | holdout | n | violations | rate | p | reject |
> |---|---|---|---|---|---|---|
> | lightgbm | 0.05 / 0.10 / 0.20 | 340 each | 8 / 8 / 10 | 0.0235 / 0.0235 / 0.0294 | 0.9954 / 0.9954 / 0.9765 | **False** |
> | prototype | 0.05 / 0.10 / 0.20 | 340 each | 3 / 4 / 4 | 0.0088 / 0.0118 / 0.0118 | ≈1.0 | **False** |
> | ronetc | 0.05 / 0.10 / 0.20 | 340 each | 3 / 3 / 2 | 0.0088 / 0.0088 / 0.0059 | ≈1.0 | **False** |
>
> **⇒ ALL NINE CELLS FAIL TO REJECT (as committed). The bound is NOT falsified on the informative stratum**, at every detector
> and every holdout level. Strata **informative 340 / secondary 540 / excluded 110 = 990** — exactly X1's pair
> denominator. `floor_violation_test.status = computed`, `previously_deferred: true`. The pre-registered
> falsification condition was "an excess of floor violations falsifies either the TV estimate or the declared
> channel model and MUST be reported"; **there is no excess, so there is no falsification.**
> **⚠ TWO CAVEATS THAT MUST TRAVEL WITH THIS, NOT BE DROPPED LATER:**
> **(a) OBJECT SUBSTITUTION (proxy):** the "error" compared is a **pair-level MACRO-AVERAGE surrogate**, and it
> is **CLOSED-SET** classification error while the floor is an **OPEN-SET** error lower bound. **⇒ The citable
> sentence is "per-pair macro-average closed-set error stays above the floor on the informative stratum" —
> NOT "per-pair open-set error never beats the certificate".**
> **✅ THE 9-CELL COUNT IS RESOLVED — IT STAYS AT 9 (D081).** The `max_tpr` fix (`(correct & positive).sum()`)
> ran, and **I READ THE ARTIFACT MYSELF rather than relying on the worker's account** — the acceptance gate is
> **`reproduction_check.reproduced = true` with `absolute_differences` of 0.0** on all three known-wrong values; the
> acceptance gate PASSED: it reproduced the known-wrong values from the stored payloads FIRST
> (`a=0.39913232104121477`, `b=385.38`, `0.5*(a+b)=192.88956616052062`) before deriving any correction.
> **Verified from the artifact: `range_check.all_corrected_pair_values_in_[0,1] = true` for every detector×holdout, and
> `guard_check.can_fire_at_or_below_0.01 = false` in every cell.**
> **Corrected `max_tpr` = lightgbm 0.826/0.860/0.875 · prototype 0.817/0.813/0.826 · ronetc 0.789/0.778/0.776
> — every value inside [0.776, 0.875], far above the 0.01 guard.** ⇒ **the `near_zero_tpr` guard does NOT fire,
> so no cell moves from `computed` to `NO INFORMATION` and ALL NINE CELLS STAND.**
> **⚠ AND KEEP THE TWO STATEMENTS SEPARATE:** *"the guard cannot fire"* (still true — 0.78–0.87 ≫ 0.01, a
> statement about the threshold) and *"the quantity was miscomputed"* (also true — the numerator ranged over
> all flows) are DIFFERENT claims. **The corrected values are quotable as rates; the old 170.5/192.9/2.10 are not.**
> **✅ Citable now: `x12_k5_max_tpr_recomputed.json` (11,132 B / `e0dc82e0…`) is LOCAL, REGISTERED (`art_20260914_28bbfe`, commits to `artifacts/X12_k5/data/`), and its `content_sha256` is recorded.**
> **(b) `maximum_pair_tpr` CANNOT BE QUOTED (M113).** Its values (170.5 / 192.9 / 2.10) cannot be rates, and the
> per-service `max_tpr` beneath it spans **0.0022–341.06 with 22 of 53 services above 1.0**. **Third instance of
> this project's "field whose value cannot equal what its name claims" class** (after the retired
> `lower_side_fraction` and the self-referential `artifact_size_bytes`). **The containment verdict is NOT
> affected — it comes from the `binomial_test` block, and this field is reported alongside the test, not
> consumed by it — but the field must be RENAMED before the paper cites this artifact.**
> **✓ `pcap_encoder` is honestly recorded `not_run` (`ModuleNotFoundError`), listed as `NO INFORMATION` in the
> CSV rather than silently dropped** — which is why the CSV is 990 × 3 holdout × 4 slots.
> **✓ Liveness lesson (third instance, D048/D054 precedent):** the status probe read the bash WRAPPER
> (PID 683446, `do_wait`, CPU 0) and judged BLOCKED, while the python CHILD (683452) held the CUDA and was
> computing; the run finished on its own. **Probes must sample the process that holds the work, identified by
> CUDA ownership or real command line, never the first PID in the tree.**
> **★★ D076 — X11 CROSS-CORPUS RESULT: AN ARGUMENT AGAINST OUR OWN HEADLINE, AND ITS CAUSE IS MEASURED.**
> On **CESNET-QUIC22** (independent, public, same protocol: k=5 · M=1 · alpha=0.025 · channel (direction,size),
> timing excluded · service threshold 2,000 · **no tuning**, `tuning_performed: false`) the upper certifiable
> fraction is **534/3321 = 0.1608** against the primary corpus's **340/990 = 0.3434**. **`reproduces_upper_fraction: false`.**
> **I recomputed BOTH artifacts myself.** The raw gap is **18.3 points**, but it is **mostly composition**:
> | min(n_a,n_b) | QUIC22 pairs | frac eps_hi<0.5 | median tv |
> |---|---|---|---|
> | all | 3,321 | **0.1608** | 0.6892 |
> | >=13,049 (= primary median n) | 861 | **0.2485** | 0.6197 |
> | >=20,000 | 528 | **0.2822** | 0.5979 |
> | >=80,000 | 190 | **0.2789** | 0.5935 |
> **⇒ 64.7% of the gap is per-pair evidence volume and service granularity alone** (raw 0.1826 → matched 0.0645).
> **median tv CONVERGES under matching: 0.6892 → 0.5935 vs the primary's 0.5805** — so "QUIC22 services are
> intrinsically more separable" is itself largely an n effect. **Structural difference: 990 = C(45,2) vs 3,321 = C(82,2)**
> — 82 services at smaller n each is **a different measurement design, not the same experiment on another corpus.**
> **⚠ A common-n-band tv comparison has MIXED SIGN** (primary higher in 20k–50k; QUIC22 higher in 5k–10k and
> 10k–20k) ⇒ **pooled tv medians are band-noisy and are not a corpus property either.**
> **⇒ RULING: `does not reproduce` STAYS (not softened). But 0.1608 must NOT be cited as "single-corpus
> non-extrapolability", and X11 is neither falsification nor confirmation of C1 until a scale-matched
> resampling is done.** The citable form: *under a fixed protocol QUIC22's marginal upper-certifiable fraction
> is lower; at matched per-pair evidence the gap narrows from 18.3 to ~6.5 points and median tv converges
> (0.594 vs 0.581); the raw single point is a **composition-affected marginal proportion, not a corpus property**.*
> **★ The residual ~6.5-point gap is the REAL, still-unexplained signal** — far smaller, and far more
> interesting, than "half". **Credit: no tuning, no object substitution, and the artifact states outright that
> the two-sided decision is unavailable because the lower classifier pipeline did not run.** The defect is the
> interpretability of a pooled point, not honesty. **⚠ X11 is UNREGISTERED (0 hits in registry and manifest) —
> same "ran it but recorded it as never run" pattern; must carry this table, or the next reader sees only 16.08%.**
> **D068 — I over-reached and retracted:** the **0.608 mass figure is NOT freeze-contaminated** (direct
> drop/total ratio, no estimator in the path) — **the MASS is citable; the INFERENCE from it is not.**
> **★ D074 — THE FREEZE GUARD LANDED, AND ITS BOOLEAN SAID THE WRONG THING.** The guard is **correct**
> (reproduces **14/25** exact-zero increments vs the unfiltered control's **0/25**; quantifies the mechanism:
> new retained contexts collapse 2464→5→0 at k=13→14→16, total saturating at 8762; refuses to fit a frozen
> tail; non-frozen exponent **`p = 1.093` LINEAR**, exactly reproducing my independent computation; the
> superseded `0.539` is no longer emitted). **⚠ But `joint_tracks_thinning` flipped to False for a SEMANTIC
> reason, not a scientific one:** the assessable levels are **0.651 → 0.625 → 0.614, strictly monotone**,
> and the False came from **two levels being REFUSED** — a boolean cannot express "not assessable" and so
> reported "trend absent". **⇒ Correct statement everywhere: trend SUPPORTED on the three assessable
> levels; the two deepest NOT ASSESSABLE; mechanism NOT ESTABLISHED (two levels refused, not "trend
> absent"). Do NOT flip the stored `true` to `false`.** **6th instance today of a check whose output
> cannot distinguish its failure modes.**
> **D067** — 0.651-vs-0.539 closed as **three settings of ONE construction** (freeze point moves earlier as `T`
> rises: none/**k=28**/**k=20**/**k=16**/**k=14/13/11/10** ⇒ the sweep is a **freeze-length series, not a sparsity
> dose-response**). **D064** — **(ii): dependence present, first-order NOT supported.**
> **★ D072 — STAGE 2 RULED COMPLETE; k=5 IS NOW UNGATED AND ONLY NEEDS THE ENTRY-THEN-ALLOCATE STEPS.**
> Source-verified: stub and literal `DEFERRED` both **0 occurrences**; CSV genuinely **pair-level** with
> `pair_error_surrogate`; X1 field path **`rows[].upper_recomputed.eps_hi`** (top-level does NOT exist),
> 990 rows / 340 informative; **both no-evidence branches present and neither can fall through to
> `status=computed`**; score payload added and **smoke-passed** (`SCORES_RECOVERABLE True`, `AUC_CLASS_10 1.0`,
> float32 exact tier, duplicate-key rejection). **⇒ k=5 goes via CREATE-ENTRY → I ALLOCATE → SUBMIT** —
> **NOT a `submit_training_job` bypass** (that is what stranded the k=15 entry).
> **⚠ TWO BEHAVIOUR CHANGES TO STATE, not let anyone discover:** (a) **the per-flow CSV is replaced by a
> pair-level CSV** (does not break containment; per-flow error recoverable from the `.npz`) — a **schema
> change**; (b) **the containment default X1 input covers k=5 ONLY**, so **k≠5 needs explicit `--x1-json`**
> or it raises (correct — no silent fallback).
> **★ D072 also rules the D063/D068 conflict: D068 governs.** The **fitted exponent sequence is NOT citable**
> (it is a sequence of progressively shorter pre-freeze windows); the **`0.608` mass figure IS citable**
> (direct drop/total ratio, no estimator in the path, does not freeze). **My D063 dispatch merged the two
> quantities in one sentence — the split is the correction.**
> **⚠ AND THREE MANIFEST DEFECTS CONFIRMED (D072):** **`a4f090` is the only dangling entry of 44**;
> **⚠ the LOCAL `x3_variant_c_nested_lr.json` is STALE and LACKS the `heterogeneous_iid_null` section**
> (748,847 B / `81000d21…`) **while the manifest's LIVE entry points at it** — the server copy (750,706 B /
> `fa1eeaab…`) carries it; and the retired duplicate has **identical bytes** to the live file, confirming
> the reshape copied the OLD version twice. **Pull required.**

## Core direction
Measured, **certification-graded** epsilon-indistinguishability brackets for open-set QUIC service
recognition: for each service pair, a two-sided interval on the total-variation distance between observable
laws, whose two sides carry **explicitly different epistemic status**. Target: **USENIX Security 2027
Cycle 2, deadline 2027-01-26**.

**The claims, experiments and reviewer-concern mapping live in `paper_framing.md`; the experiment list is
`experiment_plan.yaml`. This dashboard does not duplicate them.**

## ★★ MVP: PASSED — 2026-09-14
Both questions answered on real wire data with **fully measured** quantities (record: `docs/IDEA_BRIEF.md`).

| object | result |
|---|---|
| **Q1 — k-prefix** (k=5, M=1) | **gate 336/990 = 33.94%** — upper `eps_hi<0.5` = **340/990** (finite-sample strict given the a-priori `m`); lower `eps_lo>0.05` = **986/990** (asymptotic) |
| **Q2 — PHIST whole-flow** (packet-cell, m=32) | **informative 342/990 = 34.55%** under the sharp sum-to-zero bound (16r) |

**FULLY MEASURED — `measured 990 / assumed 0`.**

## ★★ The three registered claims (labels C1/C2/C3)
- **C1** — a two-sided bracket is computable on real encrypted traffic, upper side finite-sample strict,
  lower side asymptotic (**336/990 = 33.9%** of pairs at k=5/M=1). **UNAFFECTED by X3.**
- **C2** — the certificate horizon is short and **the coarsest channel is the only viable rung**: the
  **upper-only** certifiable fraction falls monotonically in M (**0.3434 / 0.0475 / 0.0030 / 0 / 0**; the
  joint gate is undefined per-rung for M≥2) while saturation rises (0 / 0.105 / 0.239 / 0.336 / 0.391).
  **UNAFFECTED by X3.**
  **⚠ BASIS CORRECTED (M062):** the series is **upper-only throughout**; the **joint gate** `336/990 = 33.9%`
  is **C1's headline and is quoted separately**, not an element of this series.
  **⚠ MECHANISM, CORRECT DIRECTION:** a finer alphabet **RESOLVES MORE, not less** (`tv` medians at k=5 rise
  **0.5805 → 0.8833 → 0.9248 → 0.9462 → 0.9673**). What fails is **CERTIFIABILITY**: the certified floor is
  `(1 − eps_hi)/2`, so an *easily* distinguished pair has a *small* floor, and `eps_hi = tv + radius > 0.5`
  kills the certificate. **Finer M ⇒ higher channel TV ⇒ certificate lost.**
  **M=1 also has the HIGHEST `k_cert`** (17 / 8 / 5 / 4 / 3 at n=3.9e6, tv=0.30) — **not the lowest**.
- **C3** — ~~on the dependent packet prefix, the chain-rule `D_k` grows **sublinearly** against the linear
  i.i.d. null.~~ **REFRAMED (D044 → D046), NARROWED (D053). A methods/limits finding.**
  **(i) The standard PLUG-IN chain-rule divergence estimator cannot adjudicate the dependent-prefix growth
  question at this k window, n, and occupancy-collapse curve** — it DEFLATES large-k divergence (`est/true`
  1.0002→0.6769 on analytically-LINEAR truth) — **and this is robust to two independent repair attempts**
  (A jackknife, B exposure-conditioning: both failed their gates).
  **⚠⚠ BUT THE "B SHOWS THE FAILURE IS STRUCTURAL (61% MASS)" HALF IS NOW INVALID (D063).** I verified that
  **variant B's plain known-truth curve is FROZEN from k=16 to 30** — `D_k` pinned at exactly `5.908567858844014`
  for **every** k in that range, i.e. **14 of 25 increments are exactly zero**. **The freeze is introduced by
  B's `MIN_CONTEXT_COUNT` threshold filter, not by the data:** the **original, unfiltered** control's plain
  curve has **0/25** zero increments. **And the freeze CREATES the reported signal:** refitting B's own curve
  with B's own power form over the full window gives `p = 0.539` (reproducing the artifact), but **truncated to
  k≤16 — before the freeze — the same fit gives `p = 1.093`, i.e. LINEAR, not sublinear.**
  **⇒ So "B's plain arm p falls monotonically as the threshold tightens" is a FITTING ARTIFACT of a constant
  tail.**
  **⚠⚠ BUT I OVER-REACHED ON THE MASS FIGURE AND HAVE RETRACTED IT (D068).** The **`0.608` excluded-mass
  value is NOT freeze-contaminated and does NOT need recomputation** — verified in source: it comes from
  `condition_counts` (line 139) as a **direct ratio of dropped to total transition mass**
  (`p_excluded_mass = drop_p/raw_p`, `mean_two_sided = 0.5*(those)`, lines 198–211) with **no estimator and
  no fit anywhere in the path**. It behaves accordingly: **22 distinct values across the 26 ks**, monotone
  nondecreasing (`0.000` at k≤9 → `0.0029` at k=10 → `0.2654` at k=16 → `0.4124` at k=20 → **`0.6082` at
  k=30**), and it **does NOT freeze at k=16** the way the `D_k` curve does.
  **⇒ SO: the MASS is a valid, independently computed filter property and IS citable. What stays dead is the
  INFERENCE from it** ("therefore the plain arm's failure is structural rather than a tuning problem"),
  **because that verdict rested on the frozen-axis fit.** **Do not over-correct the other way either.**
  **⇒ LESSON: before saying "X is contaminated by defect Y", trace whether X's computation PASSES THROUGH
  Y. Here a one-line grep of where `excluded_mass` is produced would have settled it.**
  **⇒ Mechanism stays NOT ESTABLISHED — now for a simpler and STRONGER reason than "two controls disagree":
  one of the two controls is INERT over a third of its range and so cannot testify about the shape of growth.**
  This also dissolves the D052 tension: if both B's threshold scan and the dose-response largely reflect their
  own filter/dilution freeze lengths, there is nothing for "sparsity" to reconcile.
  **⇒ Fix direction:** make the retained context set keep **growing** with k rather than saturating; **or** report
  the retained-context count per k and **refuse to emit a fit when the curve is constant over a tail**; and add
  a **no-freeze assertion** to every filtered curve, at the same level as D056's bit-identical/analytic guards.
  **⇒ SIBLING-AUDIT RULE UPGRADED:** the earlier audit checked only for a **+4 label shift**, so it printed the
  freeze as normal data — its own table showed `k=20` and `k=30` with **identical** values. **Audit scope must be
  set by anomaly signals, not by the task description alone.**
  **⚠⚠ THE PARAMETRIC ROUTE RETURNED `LINEAR` — AND I REJECT IT AS VACUOUS (D057).** Read from the runner
  (`x3_parametric_growth.py`): it fits a Markov model of order 0/1/2 by BIC **once** per service, then computes
  `D_k` under that **fitted** model with **no per-k refit**, as `D_k = Σ_{i≤k} H(marginal_i) − H(X_1..X_k)`.
  **For any stationary chain the joint entropy grows by the constant entropy rate once k exceeds the order, so
  `D_k` is AFFINE in k with slope `H(X) − h ≥ 0`; the order-0 branch returns `D_k ≡ 0`.** I reproduced this
  numerically: order-1 increments constant at **+0.128424** for every k=2..30 (matching `(k−1)·MI` to 6 dp),
  order-2 constant at **+0.187831748** for k≥4 (spread 3.6e-15). **⇒ The only reachable outcomes are `D_k ≡ 0`
  (order 0) or `D_k` affine (order ≥1): SUBLINEAR IS UNREACHABLE and `LINEAR` IS FORCED. The route cannot
  distinguish the hypotheses on real data.** **⇒ So it does NOT demonstrate the question is adjudicable, and
  the D053 narrowing of (i) to "the plug-in estimator cannot" DOES NOT APPLY.**
  **⇒ Its own known-truth control is likewise incapable of failing** — it checks that the exact and fitted
  curves receive the same `fit_growth` verdict, and **both are affine by construction** — so "passed decisively"
  carries no weight.
  **⇒ (i) now reads: no route tried so far can adjudicate it**, which slightly strengthens (i) while keeping it
  correctly scoped. **Making the route non-vacuous requires changing WHAT IS COMPARED (a NEW design — e.g. a
  genuine alternative model, or a per-k refit compared against a known source's exact growth), NOT a bug fix,
  and must not be dispatched as a repair.**
  **(ii) THE VOTE IS NOT EVIDENCE (D055, superseding D053's "dependence is real").** C's "Markov 45/45 at
  every k" is **reproduced exactly by a ZERO-within-flow-dependence null**: the heterogeneous-i.i.d. arm
  (each flow draws its own rate from the pooled empirical per-flow rate distribution, then emits 30 i.i.d.
  bits) returns **45/45 Markov at k≥8, 98.2% overall — verdict `DEAD`.** **So the vote carries NO evidence for
  within-flow dependence.** **⚠ MY D053 WITHDRAWAL WAS WRONG; my original D052 point was right on this.**
  **⚠ BUT heterogeneity does not explain the MAGNITUDE either:** the arm's k=30 median `ΔBIC ≈ 1896` vs the
  real data's **≈110,091** — **~58× larger** (the independent simulation's ~47× on the per-observation
  advantage is the same phenomenon). **⇒ Neither "dependence is real and first-order" nor "heterogeneity
  explains it" is correct: THE VOTE IS NOT EVIDENCE, and the MAGNITUDE exceeds the null but a single-global-`p`
  null still cannot license "first-order".** **(ii) is demoted from sanity corroboration to NOT EVIDENCE.**
  **⚠ MECHANISM — TWO INDEPENDENT OBSTACLES, ONE FIXED AND ONE STILL STANDING (D056 → D060).**
  **① THE OFF-BY-4 IS FIXED, and it was real.** Defect located at `x3_control_occupancy_dose_response.py:179-181`:
  it read `counts_p = thinned_p[: k - 4]` while iterating `K_VALUES = range(5, 31)`, so label `k` consumed
  `k−4` transitions — label 9 used five, exactly matching the original control's `k=5`. **That is the +4 shift
  I measured (`dose(k) == orig(k-4)`, 22/22 exact at 1e-9).** Fixed to `[:k]`; nothing else touched. After the
  fix the un-thinned baseline gives `est/true = 1.0002` at k=5 and **`p = 0.651`, matching the original control
  exactly.** A permanent assertion now enforces this (zero-intervention curve **bit-identical** to the shared
  reference; analytic k=5 ratio within 0.001).
  **② BUT MY D056 PREDICTION WAS WRONG — THE DISAGREEMENT SURVIVES THE FIX.** I wrote that the two controls'
  opposition "was itself an artifact of this bug". **It is not.** With the corrected axis the directions remain
  OPPOSITE: the dose-response **adds** sparsity (0.4156 → 0.5694) and drives `p` **down**; variant B's
  real-data scan **removes** the sparsest contexts and **also** drives `p` down (0.539 → 0.210).
  **More sparsity → sublinear in one; less sparsity → sublinear in the other.** ⇒ **The disagreement is REAL
  and unexplained**, so the mechanism is unresolved for **two independent reasons, not one** — the bug (now
  fixed) **and** the remaining opposition.
  **③ ★★ AND THE FREEZE GUARD HAS NOW LANDED, WHICH CHANGES WHAT MAY BE QUOTED (D063 → D074).** The guard is
  **correct** — it reproduces **14/25 exact-zero increments** in B's plain curve against **0/25** in the
  unfiltered control, quantifies the mechanism (new retained contexts collapse 2464 → 5 → 0 across
  k=13 → 14 → 16, retained total saturating at **8762**), and **refuses to emit a fit on a frozen tail**
  rather than silently fitting it. **The non-frozen-window exponent is `p = 1.093` (LINEAR)** — exactly the
  value I computed independently — **and the superseded full-window `p = 0.539` is no longer emitted.**
  **⚠ BUT ITS SUMMARY BOOLEAN SAID THE WRONG THING (D074).** `joint_tracks_thinning` flipped to **False**,
  and the flip does **not** come from a monotonicity violation: the three ASSESSABLE levels are
  **0.651 → 0.625 → 0.614, strictly non-increasing**. It comes from **two levels being REFUSED**
  (`[0.1, 0.05]`), which shortened the emitted vector and made `p_nonincreasing` false. **A boolean cannot
  express "not assessable", so it reported "trend absent".**
  **⇒ THE CORRECT STATEMENT, and it is what every surface must carry:** *on the three assessable thinning
  levels the sparse-context statistic is non-decreasing and the fitted exponent is non-increasing
  (0.651 → 0.625 → 0.614); **the two deepest levels are NOT ASSESSABLE** because the guard refuses to fit a
  frozen tail.* **Mechanism remains NOT ESTABLISHED** — the reason is now precise: **two levels refused,
  not "trend absent".** **Do NOT flip the stored `true` to `false`** — that propagates the same semantic
  error the other way. **Sixth instance today of a check whose output cannot distinguish its failure modes.**
  **③ NEW BLOCKER EXPOSED BY THE FIX:** the **original known-truth control** and the **corrected dose-response**
  both give a no-filter baseline of **p = 0.651**, while **variant B** gives **0.539** — for nominally the same
  construction (200,000 synthetic 30-bit flows, p=0.30/q=0.70). **Two nominal quantities, one setting ⇒ per my
  own standing rule this is a BLOCKER on both, not a tension.** The corrected value **sides with the original
  control and against variant B**, so **variant B's construction is now the suspect** — and it must be resolved
  before either baseline is cited.
  **④ SIBLING SWEEP (as required):** `x3_variant_a`, `x3_variant_b`, `x3_controls` are **verified correctly
  labelled** (no +4 shift); `x3_variant_c` produces no `D_k` curve (test not applicable);
  `x6_divisibility_lower_bound` — **VERIFIED COMPLETE** (D065): artifact `d9e17986…` EXISTS (1,998,647 B, run 05:28:41, `status: COMPLETE`); **no k-axis defect applies — it produces no `D_k` curve.** **No sibling was modified.**
  **⇒ STANDS anyway:** the heterogeneous arm's `DEAD` verdict (a **vote**-based comparison with no `D_k`
  accumulation — the k-shift class does not apply), the original control's FAIL, variant B's gate failure, and
  the ~58× magnitude gap. **⇒ Mechanism remains NOT ESTABLISHED — for BOTH reasons above.**
  because two controls disagree.**
  **⇒ ACCEPTANCE TEST ADOPTED:** a control whose point is a **zero-intervention baseline** must reproduce the
  un-thinned reference exactly (bit-identical on a shared code path) — that would have caught this instantly.
  **⇒ C3 STILL STANDS ON PART (i) ALONE.** **Two-claim paper is a LIVE option, not a fallback.**

## ★★ X3 — THE THEORY TEST: **INCONCLUSIVE** → **C3 REFRAMED** (D044 downgrade, D046 reframe)
**The pre-committed rule fired. C3 as stated cannot be claimed.**
Adjudication rule, fixed *before* measurement: `SUBLINEAR` is **CONFIRMED** only if it survives **both** (i) a
fixed-population recompute and (ii) a known-linear-truth control the estimator must recover. **Otherwise
DOWNGRADE TO INCONCLUSIVE.** The artifact's own field says:
*"A fabricated direction is worse than an inconclusive test."*

| control | result |
|---|---|
| **(ii) known-truth — DECISIVE** | **FAILED.** Truth analytic and exactly LINEAR (`p=0.30,q=0.70` ⇒ `D_k = k·0.3389191441548814`). Estimator returned **SUBLINEAR** (p=0.651, √k AIC adv 29.52, ratio 2.631); **real-occupancy twin also SUBLINEAR** (p=0.897, adv 22.10, ratio 1.787). `est/true` **falls** 1.0002 (k=5) → **0.6769** (k=30). |
| **(i) fixed population** | **PASSED.** Fixed 820-pair denominator: p=0.844, adv 74.15, ratio 1.503. **Composition is NOT the cause.** |
| smoothing sweep | **UNSTABLE.** `0.0` ⇒ INCONCLUSIVE (p=1.25, adv 9.03); `0.5` ⇒ SUBLINEAR; `1.0` ⇒ SUBLINEAR (ratio 2.071). |

**WHY IT FAILS — the bias runs the WRONG WAY.** The estimator **DEFLATES** large-k divergence, i.e. it
**manufactures** sublinearity: a construction with truth pinned to straight-line growth is reported as
SUBLINEAR with high confidence. **It cannot distinguish the hypotheses.**

**⚠ RETRACTED, AND IT WAS LOAD-BEARING (M063/M093):** the claim *"the bias INFLATES `D_k`, so SUBLINEAR is
CONSERVATIVE"* is **backwards**. It came from a **proxy** estimator, never the real one, and it was written
before the kill-control returned.

**SCOPE:** **NOT a falsification** — a *LINEAR* result would have been. The estimator returns SUBLINEAR on
both truth-modes, so the dependent-prefix story is **UNRESOLVED**. **C1 and C2 are untouched.** Estimator
reproduction passed at tol 1e-9; the original artifact (`c19d7392…`) is **UNMODIFIED**.

**★ STANDING CONSTRAINT C027:** C3 may not be restated as SUBLINEAR unless the estimator **FIRST** recovers
LINEAR on the known-truth control **AND** the real-occupancy twin. **An estimator that has not cleared that
gate cannot adjudicate C3.** Third-party note: the project's distill-hub skill pattern #12 asserts the
*inflate* direction (Confidence: low); the control artifact is the measurement and overrides it.

### ★★ THE THREE GATED REPAIR VARIANTS — ALL LANDED (D046). C3 is now REFRAMED, not dropped.
Each variant had to **FIRST** recover LINEAR on the known-truth control **AND** on the real-occupancy twin
before touching real data (C027). **Two failed their gates; that failure is the finding.**

| variant | route | gate | outcome |
|---|---|---|---|
| **A** | estimator **family** change — concretely a **two-sample delete-one JACKKNIFE bias correction** on Laplace `alpha=1`-smoothed conditional KLs, directed terms projected to the nonnegative half-line | **FAILED, both arms** | Real data **never touched**. A bias-corrected estimator family does not fix the sparse-context bias. |
| **B** | **exposure conditioning** (contexts with `n_P,n_Q >= T`) | **FAILED** | Plain-IID arm passed at **no** `T ∈ {5,10,20,50,100}`; twin passed at all. **⚠ Its plain `p = 0.539` is a fit across a FROZEN tail (D063): the curve is pinned at `5.908567858844014` for k=16..30 (14/25 increments exactly zero); refitting before the freeze gives `p = 1.093` (LINEAR). — BUT the `0.608` excluded-mass figure IS valid and citable (D068): it is computed directly from filter counts with no fit in the path, and does not freeze. Cite the MASS, not the INFERENCE from it.** |
| **C** | **test route** (nested first-order-Markov vs i.i.d., BIC) | **CONTROL USABLE** | Control discriminates (synthetic IID ⇒ IID 12/12, median ΔBIC −21.77; synthetic dependent ⇒ Markov 12/12, ΔBIC 86689.85). Real data: **Markov 45/45 services at EVERY k=2..30**, IID 0/45, ties 0; at k=30 median ΔBIC **110091.14**. |

**⇒ (i) WHAT SURVIVES — the methods/limits finding.** The plug-in chain-rule estimator **cannot adjudicate**
the growth question here: it **DEFLATES** large-k divergence (measured on analytically-LINEAR truth, `est/true`
1.0002 at k=5 → 0.6769 at k=30), and this is **robust to two independent repair attempts (A jackknife,
B conditioning)** which both **failed their gates without touching real data**.
**⚠⚠ B's `p = 0.539` IS NOT USABLE — IT IS A FIT ACROSS A FROZEN AXIS (D063). BUT THE `0.608` MASS FIGURE IS VALID AND CITABLE (D068) — see below.**
I verified that **variant B's plain curve is pinned at `5.908567858844014` for every k=16..30** (**14 of 25
increments exactly zero**), that the **unfiltered** original control has **0/25** zeros (so the freeze comes from
B's threshold filter, not the data), and that **refitting B's own curve before the freeze gives `p = 1.093`
(LINEAR) instead of the reported `0.539`.** **⇒ B's "not fixable by conditioning" argument rested on a fitting
artifact of a constant tail. **The excluded-MASS figure itself is unaffected** — it comes from `condition_counts` as a direct drop/total ratio with no estimator or fit in the path, gives 22 distinct values across 26 ks, and never freezes (D068). **What is unsupported is the INFERENCE from it** (that the plain arm's failure is structural), because that verdict rested on the frozen fit.**
**⚠⚠ AND THE CAUSAL ATTRIBUTION IS RETRACTED (D052), now for a SIMPLER REASON (D063).** I had recorded that
tightening the threshold makes the plain arm MORE sublinear (`0.539/0.420/0.372/0.260/0.210`) at T=5/10/20/50/100
while the twin moves the opposite way (`1.042/…/1.007` vs `0.897`), and labelled that opposition **unexplained**.
**It no longer needs explaining: if B's per-threshold falls are largely produced by the freeze starting EARLIER
at higher T, then that trend measures the freeze length, not sparsity.** **⇒ The mechanism is NOT ESTABLISHED —
not because two controls disagree, but because one of them is INERT over a third of its range and cannot testify
about the shape of growth at all.** B's twin-arm numbers remain on the correct axis but say nothing about sparsity.
**⚠ MY D052 FINDING 1 IS WITHDRAWN.** I claimed between-flow heterogeneity explained C's result. **It does
not.** The BIC penalty is **2.43e-04** of ΔBIC at k=30 (`2·log N = 26.80` vs `ΔBIC = 110,091`), and a simulated
**pure heterogeneous-i.i.d. NULL** (each flow its own rate, i.i.d. within flow) predicts `2·ΔLL/N = 3.09e-03`
nats/obs against the observed **1.44e-01** — about **47× short**. Heterogeneity accounts for ~2% of the
advantage, so **real within-flow sequential dependence beyond between-flow mixing is present.**
**⇒ "first-order" IS NOT MERELY UNSUPPORTED — IT IS REFUTED (D064).** `fit_nested_models` uses an i.i.d. null
with **a SINGLE GLOBAL `p`** over all 30 positions, which is maximally weak; I had said a position-wise null was
needed to test "first-order" rather than assume it. **That test has now RUN, and it settles the question in the
opposite direction from a mere narrowing:** the **position-wise i.i.d. null** (independent across positions,
one free marginal rate PER position) **beats first-order Markov at most k — but the per-k shape matters,
and my first phrasing ("nearly every k") was WRONG.** Full table (position-wise wins / Markov wins / ties):
**k=2 45/0 · k=3 25/20 · k=4 33/12 · k=5 42/3 · k=6 44/1 · k=7–8 44/1 · k=9–29 43/2 (each) · k=30 41/4**,
**0 ties anywhere**; median `ΔBIC` negative at every k (−10.69 at k=2 → ≈−38k mid-range → −27,267 at k=30).
**⚠ k=3 (25/20) and k=4 (33/12) are MARGINAL** — not lopsided. The preregistered rule is decisive anyway
because it demands Markov strictly win at EVERY k, and **k=2 alone breaks it**.
**⚠ AND THE VOTE, NOT THE MEDIAN, IS THE INSTRUMENT:** at k=30 the largest per-service `ΔBIC` is
**+408,971 (POSITIVE)** — on the 4 services where Markov wins, the sign REVERSES against the −27,267 median.
**A pooled median would have hidden exactly those services.**
**Pre-registered rule** (written before measurement): "first-order" is licensed only if position-wise i.i.d. is
defeated by first-order Markov at k=30 **and** at every k=2..30; else not licensed. Artifact records
**`first_order_licensed: false`**.
**⇒ SO (ii) READS: dependence is present, but a FIRST-ORDER STRUCTURE IS NOT SUPPORTED by this test — per-position
MARGINAL structure explains the observed votes better than any transition structure does.** *(⚠ These numbers are
REPORTED from the server artifact (`x3_positionwise_iid_null.json`, 748,564 B); my local tree is stale and does
not yet hold it, so they are pending the pull. The conclusion is recorded now because it is decisive either way.)*
**⚠ This is a REVERSAL IN STRENGTH, not in direction, of what I wrote above (D053):** I said position-wise drift
"would also make Markov win" — measured, the position-wise model does not merely also win, **it wins outright.**
**⚠ AND ITS SCOPE IS ONLY THE VOTE:** it says nothing about part (i), which rests on the estimator's **deflation
on analytically-linear truth** (`est/true` 1.0002→0.6769) — an independent instrument — nor about C1/C2.
**⇒ (i) STANDS, with its supporting argument NARROWED (D063).** "Structural, not a tuning problem" **can no
longer rest on the excluded-mass curve** — that curve was computed on variant B's **frozen** axis (plain `D_k`
pinned at `5.908567858844014` across k=16..30; refit before the freeze gives `p = 1.093`, LINEAR). **What the
evidence actually supports is narrower and still real: the plug-in chain-rule estimator is DEFLATED on
analytically-linear truth (`est/true` 1.0002→0.6769), so it cannot adjudicate; and both repair attempts failed
on a VALIDATED axis.** **⚠ "cannot adjudicate the QUESTION" remains overstated** — what is established is that
**the plug-in chain-rule estimator** cannot adjudicate at this k window, n, and occupancy-collapse curve; **the
parametric route is not a counterexample either (D057: it is vacuous).** So the honest form is: **no route tried
so far can adjudicate it.**
**⇒ ⚠ GATE WEAKNESS (D052, STANDS):** `twin_services_used = [0, 1]` — the twin uses only the **two largest**
services (n≈1.38M/360K vs plain's 200K) and is therefore **easier**; it passed at all thresholds while plain
failed at all. The gate tests the **well-occupied** regime while what breaks the estimator is the **sparse** one.
**⚠ NOVELTY OBLIGATION:** the sparse plug-in KL/entropy bias is **classical** (Miller 1955; Grassberger 1988;
Paninski 2003; Kraskov 2004) — framing must position (i) against it or the novelty claim does not hold.
**⇒ C3 IS RETAINED as a methods/limits finding, NOT cut** — the growth-rate claim is correctly gone, but
"the standard plug-in cannot adjudicate this on this data" is a real negative with practitioner value.
**REQUIRED CONTROLS (D053):** ★ **the PARAMETRIC route is now MUST-DO, not a candidate** — fit a low-order
Markov (or BIC-select the order) and compute `D_k` **under the fitted model**; its conditionals have adequate
samples **by construction**, so it bypasses occupancy collapse and **decides (i)'s wording** (if it also fails,
"cannot adjudicate" stands; **if it returns LINEAR, the question IS adjudicable and only the plug-in fails**).
Also: keep the heterogeneous-i.i.d. arm but **publish it as a null inside the artifact** (so C's conclusion is
self-sufficient rather than needing a reviewer to re-derive it), and **add a position-wise i.i.d. null** so
"first-order" can be tested rather than assumed.
**⇒ Protected artifact `x3_chain_rule_divergence.json` is byte-unchanged (`c19d7392…`) across all variants.**

## ★ P0 experiments
| id | claim | state |
|---|---|---|
| **X1** | C1, C2 | **✓ REBUILT AND LOCAL** (`c9f840a9…`) — headline **340 / 986 / 336 = 0.3394**; `effective_alpha` printed from the code path (0.025). |
| **X2** | C1 | **DONE** — PHIST on the sharp 16r bound; coexisting and **not rankable** against X1 |
| **X3** | C3 | **REFRAMED (D046) → WEAKENED (D052)** — growth-rate verdict not recoverable (A and B both fail their gates; the estimator deflates) **but** the sparse-occupancy mechanism is **CONTRADICTED** by B's sweep and (ii) is **unsupported** by its control (heterogeneity confound). Two controls dispatched. |
| **X4** | C2 | **DONE** — frontier `M_max(k,n,tv)`; anchor `[7,7,6,5,4,3,2]` reproduced; certifiability crossover at tv=0.30 = **26,366,192** |
| **X12** | C1 (RC3/RC6) | **⚠ wrong k — RE-RUN AT k=5 (D047)**; guard cleared, full disjoint corpus, but k=15 has an empty informative stratum. See below |

P1: X5 estimator ground truth ✓ · **X6 divisibility lower bound (mechanism-novelty track)** · X7 masking with
genuinely different arms · X8 vector-level one-sided result · X9 SNI/ECH price.
P2: X10 close the environment gate · X11 QUIC22 replication · X13 Good-Toulmin missing mass.

## ★★ THE CERTIFIED-OBJECT RULE (C016 / C017 / M035 / D027) — binding on every number
**A bound is only meaningful once the object whose TV it bounds is named in one sentence.** The two sides of
one bracket must bound **the same object**. **Guards:** per-row `eps_lo <= eps_hi` (a violation is a **bug,
never a result**); a summary-level cross-check for mutually impossible field combinations; and **every
inequality the theory supplies asserted PER ITEM** — but an assertion is only a **DETECTOR** if BOTH (a) the
inequality is a theorem for the objects **named** and (b) the quantity **types** permit contradiction.
**Two lower bounds compared can never falsify (M056).** The valid theorem is
`TV(vector law) >= TV(POOLED CELL law)`; against the k-PREFIX SYMBOL law there is **no DPI order in either
direction** and the ordering **inverts on 78/990 pairs** by measurement.

## ★ Guarantee-strength discipline (the thesis, not a caveat)
- **Upper side** = finite-sample strict **given the a-priori `m`**.
- **Lower side** = **asymptotic**. **"Proven" is unavailable for the lower side at any stage.**
- **The asymmetry IS the paper's claim.**
- **Constants, per object:** `4.309` for Q1's one-hot categorical prefix symbols; `31.63` for Q2's mean of
  correlated 32-simplex vectors. `61.28` is **SUPERSEDED — do not resurrect**.
- **DO NOT adopt the Weissman categorical form** (935/990) for Q2. Defensible range `[152, 342]/990`.

## ★★ The gate, settled (D038)
**`336/990 = 33.94%` canonical (full-n) / `335` capped — the entire difference is pair (21,23) crossing
0.05.** Nearest margins at full n: **+0.0088** (nearest pass) / **−0.0073** (nearest fail),
`within_0.005 = 0`. **The earlier "0.0002 from the line" was the CAPPED value's margin — retracted.**

## ★ What must NOT be claimed
**Q1's 340 and Q2's 342 do NOT corroborate each other.** 2×2: own radii 340/342, but common radii 340 vs 935
and 81 vs 342 — statistics differ **2.7×**, constants **7.34×**: **two large differences cancelling.**

## ★ Step-0: PASS (XS subset) — **NOT closed**
53 services → 45 at threshold; two-axis **43/39**, full-crossing **39/36**; **32/53 single-ASN** ⇒ `DST_ASN`
is an **audit confound, not an environment axis**. **Not closed:** the XS subset has unknown month coverage
(X10 is the closing condition).

## ★★ X12 DETECTOR PANEL — **D054 + D059: THE "≤RANDOM" ALARM IS WITHDRAWN; THE METRIC IS THE SUSPECT.**
**L0 MEASURED (numbers only, plus the correction the reviewer supplied):**
- `service_labels_common_to_both_sides` = **`[0..52]`**, length 53, min 0, max 52 ⇒ **`max == len-1` = YES**
  ⇒ **the class list IS contiguous, so index == raw label. MY INDEX-VS-LABEL HYPOTHESIS IS REFUTED.**
- Per-row agreement with the true label over 1,493,995 rows: **lightgbm 48.58%** (725,738) ·
  **prototype 13.53%** · **ronetc 58.10%**.
- **⚠⚠ THE BASELINE I USED WAS WRONG (D059).** I compared against a **uniform** `1/53 = 1.89%`. The true label
  distribution is **strongly imbalanced**: majority class **14.73%** from the cached train-side flow counts
  (745,293 / 5,058,007; top-5 = 14.73 / 14.64 / 10.10 / 7.47 / 6.79%), and the reviewer measures **24.89%**
  on the held-out split. **⇒ ANY citation of these rates MUST carry the majority-class baseline.**
  **⇒ lightgbm and ronetc are ABOVE it; PROTOTYPE (13.53%) is BELOW it** — worse than always guessing the
  majority class. **So my earlier "all detectors predict far above chance" OVER-CLAIMED for prototype.**
- **⚠ `all_rows_accepted = true` for lightgbm is STRUCTURAL, not measured (D059):** line **486** hard-codes
  `"accepted": np.ones(...)`, independent of the data. The other two compute acceptance genuinely. **An open-set
  detector that never rejects has NO rejection capability**, so lightgbm's OSCR/FPR95 are computed in a
  **degenerate never-reject state**; its `accepted_rate = 1.0` is a design residue. **Label it STRUCTURAL.**
**⇒ So D051's "at or below chance" framing stays WITHDRAWN, the shared-path-defect story is unsupported, and
the supporting sentence is narrowed: two of three detectors beat the majority baseline.**
**★ THE METRIC IS STILL THE SUSPECT (code reading, NOT a settled fact).** In `oscr_and_fpr95`, `class_score` is
finite **only where `(pred == label) & accepted`** ⇒ the threshold sweep runs from `(0,0)` to
`(FPR_end, recall)` and **can never reach `(1,1)`** ⇒ `trapz(TPR, FPR)` is a **narrow** area, and for a
*perfect* one-vs-rest classifier the curve is a **vertical line at FPR = 0 ⇒ integral 0**. So **near-zero OSCR
is consistent with GOOD discrimination**, not with "accepting almost nothing". Same mechanism explains
**FPR95 null almost everywhere** (its precondition needs ≥95% of positives correct AND accepted).
**⇒ DIAGNOSTIC (runs IN PARALLEL, not in front — D058):** a **standard one-vs-rest AUC from per-class
probabilities swept over ALL rows**, beside the current OSCR, same services and holdouts. **High AUC (~0.9+)
with OSCR ~1e-3 ⇒ the metric is the artifact. AUC also ~0.5 ⇒ L0 continues.**
**⇒ k=5 is NOT blocked by this (D058): containment uses only per-pair error and `eps_hat_k_hi`.** Stage 2 must
still complete first, and the run must **persist per-class score material** so one run serves both.
**⇒ PRE-REGISTRATION CLAUSE (approved + extended):** the containment result must be reported as
**"uninformative" rather than "pass" whenever the violation count is vacuous for ANY reason** — near-zero TPR,
empty stratum, or any degenerate detector state. **An empty set is not a pass; a vacuous count is not evidence.**
**⚠ The k=15 entry must never read as an encouraging milestone** — "first real detector numbers" currently
means *near-zero, ≤chance, under L0 investigation, supporting no claim in either direction*.

## Near-term tasks
**★ PI CALLS (2026-09-14, user delegated the decisions):**
- **C3 IS SETTLED — keep it, three-claim paper.** Stop treating "two claims" as pending. Both outcomes of the
  parametric route leave C3 standing: if it fails too, (i) hardens; if it returns LINEAR, (i) narrows to
  "the **plug-in** estimator cannot" — and "the question IS adjudicable, the standard method is not" is itself
  a useful negative for practitioners. **C3 is written as a methods/limits finding, not cut.**
- **X11 (independent-dataset replication) IS STARTED — the single biggest strategic lever.** It is the ONLY
  direct answer to "one dataset", and it has **never run**. The plan sequenced it after X10, but **X10 is
  blocked on a paused data transfer** while X11 uses a **public dataset** and can proceed independently.
  **Feasibility + acquisition first, not a full run**: confirm availability/fields/volume and the loader; run
  one month under the **same protocol, channel, and split policy**; **report where it does and does not
  reproduce — non-reproduction is a finding about corpus-dependence and must not be tuned away.** A "cannot
  obtain" verdict needs a **literal error**, not an assertion.
- **X12's metric diagnosis precedes k=5** — it decides whether that GPU run means anything.

- [x] **① D056 off-by-4 — FIXED AND BYTES CORRECTED.** Defect at `x3_control_occupancy_dose_response.py:179-181`
  (`thinned_p[: k - 4]` while iterating `K_VALUES = range(5,31)`) ⇒ label `k` consumed `k−4` transitions.
  Fixed to `[:k]`; verified at its OWN labels (`est/true = 1.0002` at k=5, no-thinning `p = 0.651` matching the
  original control); a permanent assertion now enforces the **zero-intervention** test (bit-identical curve).
  **⚠ The fix first landed in `artifacts/X3/` while `_project/data/` kept pre-fix bytes, and the manifest carried
  two contradictory entries — I copied the fixed bytes over and verified (D061).**
  **⚠⚠ BUT D061's FRAMING IS OVERTURNED (D070): `artifacts/<EXPID>/` is produced BY `register_artifact` itself**
  for server-side registrations — **confirmed on disk**: `artifacts/X3/` is back with 4 files, the manifest
  carries 4 entries into it while 31 point into `_project/data/`, and my layer-convention comment was
  overwritten. **⇒ A one-shot merge CANNOT hold, and `_project/` has no canonical claim.** **NEW RULE: the
  MANIFEST is the authority for location, not any directory. The invariant is EXACTLY ONE LIVE ENTRY PER
  ARTIFACT, whose `path` RESOLVES TO BYTES** — a broken resolver is a defect, a second live entry is a defect.
  **Do NOT re-merge; both layouts coexist.**
  **Sibling sweep done:** `variant_a`, `variant_b`, `controls` correctly labelled; `variant_c` N/A;
  `x6_divisibility` **completed and verified separately (D065)**. No sibling modified.
- [x] **①b DUPLICATE ENTRY RETIRED, AND THE LAYER QUESTION RESOLVED (D061 → D070).** `art_20260914_b9b161` is
  now marked **SUPERSEDED / do-not-cite** with `path: null` and `superseded_by: art_20260914_4d9b49` — **one
  artifact, one live entry**, which is the model. **The layer question is settled differently from my first
  answer: no directory is canonical.** `register_artifact` writes `artifacts/<EXPID>/` for server-side pulls,
  so asserting `_project/` as canonical is **both unenforceable and unnecessary** — **correctness lives in the
  manifest** (one live entry, path resolves), **not in the layout**.
- [x] **①c THE 0.651-vs-0.539 QUESTION IS FULLY CLOSED (D066 → D067) — and the resolution SHARPENS D063.**
  **Three settings of ONE construction, not three values of one quantity:**
  | setting | value |
  |---|---|
  | original control, **unfiltered** | **`0.651`** |
  | corrected dose-response, **zero thinning** (bit-identical reference) | **`0.651`** |
  | **variant B at `T=0`** (recomputed by the reviewer, **in no artifact**) | **`0.6510`** ✅ *matches the control at all 26 k* |
  | **variant B as STORED** (`T=5`, since its gate failed and 5 is the minimum candidate; `selected_threshold: None`) | **`0.539`** |
  **My own independent measurement corroborates it:** B's stored curve is **bit-identical to the control at k=5..9** and **diverges only from k=10** — the exact signature of a `T=5` filter that does not bite until contexts fall below 5 samples. **Two independent measurements, same conclusion → the blocker is CLOSED.**
  **⚠ MY STANDING RULE (b) WAS MIS-SCOPED — AMENDED:** a same-nominal-quantity conflict is a blocker **only when the nominal SETTING is identical**. **A shared quantity under DIFFERENT intervention settings is a dose-response family, not a conflict.** Here the settings differed from the start, so **(b) should never have fired.**
  **⚠ AND THIS NAILS THE FREEZE MECHANISM BETTER THAN D063 DID (reported; per-threshold curves are not in the local artifact, so recorded as reported-not-locally-verified):** the freeze point moves **monotonically earlier as T rises** — `T=0` no freeze · `T=1` freezes at **k=28** · `T=2` at **k=20** · `T=5` at **k=16** · `T=10/20/50/100` at **k=14/13/11/10**.
  **⇒ So `p` falling "monotonically as the threshold tightens" (`0.651 → 0.539 → 0.420 → 0.372 → 0.260 → 0.210`) is NOT a sparsity dose-response — it is a sequence of progressively SHORTER effective k windows.** **`T=1` alone, discarding only the single sparsest context, lifts `p` from 0.651 to `0.955` (essentially LINEAR).** **The whole sweep measures the freeze.**
  **⚠ REQUIRED SO THE BLOCKER CANNOT REOPEN:** the value **`B @ T=0 = 0.651`** must land **in an artifact**, not only in a review — cheapest is a baseline row emitted at `T=0` by B's script, or the value recorded explicitly in D060/D062's conclusions. **Otherwise the next review re-derives it and re-raises the blocker.**
  **★ AXIS VALIDATION RAN — CONTENT GOOD, LABEL FIXED AT SOURCE (D069).** `x3_axis_validation`
  (122,617 B) verified: (a) the vote construction re-derived its expected votes with **separately written**
  BIC logic — **0 production-vs-independent mismatches**, incl. **S3 heterogeneous-iid → Markov 8/0/0**,
  **independently corroborating D055's `DEAD` at the vote level**; (b) the axis test is **SENSITIVE**, not
  just negative — dependence is built from `0→1, 1→2, 2→3` only, so the switch point is k=5, and the
  observed pattern is **IID at k=2,3 → MARKOV at k=4** (where `2→3` enters the prefix) **→ IID from k=5**,
  i.e. a **single-point flip** shows the test would CATCH a label shift; (c) parametric residuals **max
  1.07e-14** over k=5..30, with the k=1 boundary residual **disclosed** and marked outside the consumed
  range; (d) **`route_repaired: false`** — verification was **not** used as a back door to touch the route
  D057 retired.
  **⚠⚠ BUT THE LABEL WAS A HAZARD AND I FIXED IT AT THE SOURCE:** the script **hard-coded**
  `"parametric_artifact": "verified-correct"` (`x3_axis_validation.py:345`) while the artifact contains
  **zero** occurrences of `d057`/`tautolog`/`affine`/`non-diagnostic` — so a bare label beside
  "parametric_artifact" invites a reader to merge **axis alignment** with **conclusion validity** and read
  it as D057 overturned. **Now: `"axis-verified; conclusion remains NON-DIAGNOSTIC per D057"`** + an
  explanatory note + a `self_reference_note` (the embedded size/sha are a **pre-write snapshot** and must
  not be compared with the file's own bytes). **Axis correct ≠ conclusion usable — both sentences travel
  together.** **✅ STATUS AFTER THE SYNC (D084) — TWO DIFFERENT FACTS, DO NOT CONFLATE THEM:**
  **(i) THE RUNNER IS SYNCED AND FIXED.** `x3_axis_validation.py` is **16,592 B** (was ~15,394 B) and line 350
  carries the D057 wording; the byte-level deployment was done properly (server backup → upload → `py_compile` →
  before/after `sha256`). **This closes the two-trees failure I logged as M108** — my earlier fix never left the
  local tree, which is why a re-run then reproduced the SAME sha and the fix looked ineffective.
  **(ii) THE ARTIFACT HAS NOT BEEN REGENERATED.** It is still **122,617 B / sha `9f7578be…`** with the bare
  `"parametric_artifact": "verified-correct"` and **both notes absent** — because it records the LAST run, and no
  run has happened since the fix landed. **"The code is fixed" and "the artifact reflects the fix" are different
  facts; the sync closed the first, the second needs one execution.**
  **⇒ ACTION: re-run the fixed runner, then re-register so the manifest's live entry resolves to the NEW bytes
  (D070). SAFE TO DO: the stale sha `9f7578be…` appears ZERO times in `registry.yaml` and `manifest.yaml`, so
  regenerating breaks no binding** — unlike `x3_parametric_growth.json`, whose sha IS quoted and must NOT be
  hand-edited. **Report whether the sha actually changes; if it is unchanged after a genuine re-run, that is
  itself a finding. Do NOT hand-edit the artifact — the script writes it.**
  **⚠ STILL NOT A RESCUE:** the **61%/0.608 "structural" argument stays dead (D063)** — that curve is frozen from k=16, and 0.539 is a fit across a constant tail. **Closing the attribution question does not revive the argument; it replaces it with a cleaner explanation for why the sweep moved.**
- [ ] **② AUC diagnostic (routed by me; spec already in the registry).** Standard one-vs-rest AUC from
  per-class probabilities over ALL rows (curve reaches `(1,1)`), **beside** the current OSCR, same services and
  holdouts, plus a cheap proxy. Pre-registered criteria. **This is the L0 settling item.**
- [ ] **③ Parametric route (D053 REQUIRED).** Four parameters **approved as proposed**: order `{1,2,3}` chosen
  by BIC · per-item exact MLE+BIC reusing `fit_nested_models` · **≥3 seeds per arm** · same cached 45 services ×
  k=2..30 with `D_k` computed **under the fitted model** · **synthetic known-higher-order control FIRST**.
- [x] **④ Position-wise i.i.d. null — RAN. `first_order_licensed: false` (D064).** The position-wise null
  **beats first-order Markov at nearly every k** (45/45 at k=2; 43–44/45 for k=8..29; 41/45 at k=30; **0 ties**;
  median `ΔBIC` negative throughout). **⇒ Per-position MARGINAL structure explains C's votes better than any
  transition structure does**, so **"first-order" is REFUTED, not merely unsupported** — see the (ii) entry above.
  **⚠ Artifact not yet registered or pulled** (`x3_positionwise_iid_null.json`) — do that, and note the worker
  carried a **false `failed` flag** while producing both this and the amended variant-C artifact.
- [ ] **⑤ X11 feasibility + acquisition** (see PI calls above).
- [ ] **★ TWO STANDING RULES ADDED THIS ROUND:** (a) **zero-intervention acceptance** — any control with a
  no-intervention setting must reproduce its reference **exactly** (bit-identical on a shared code path);
  **this would have caught D056 immediately.** (b) **same-nominal-quantity conflict is a BLOCKER — ONLY WHEN THE
  NOMINAL SETTING IS IDENTICAL (amended, D067).** Two artifacts disagreeing on one nominal quantity **at one
  nominal setting** means *both* are untrustworthy, not a "tension" to note and proceed past. **⚠ BUT a shared
  quantity under DIFFERENT intervention settings is a DOSE-RESPONSE FAMILY, not a conflict** — and the check there
  is whether the family is **ordered by something real**, not whether the endpoints match. **I applied the rule
  without this limit and it fired on a case that was never a conflict (0.651 vs 0.539 across 0-intervention /
  0-thinning / `T=5`).** **(b) is the mistake I made writing D055; it cost half a decision — and the amendment
  cost another round. Both halves of the lesson: check the setting BEFORE calling a conflict.**

- [x] **X6 — THE MECHANISM-NOVELTY TRACK — ★ COMPLETED AND DELIVERED (D065).** The plan's only structurally
  different bound mechanism. **RESULT: non-empty exactly where the plug-in certificate is lost** — 100% of pairs
  nontrivial at k=15/20/25/30, informative 0.9989/1.0/1.0/1.0, per-k medians 0.8254/0.8164/0.8102/0.7987;
  **validity: 45/45 TESTABLE rows comply — NOT "0/120" (D071: ~75/120 rows cannot fail, bound clips to 0 at
  `VALIDITY_SAMPLE_SIZE=400`; all truth-0 rows are incapable by construction)**; the repo function was
  **called, not reimplemented**. **⇒ C2's
  "horizon is short" is now MEASURED.** ⚠ **Paper caveat: subsample 20,000 flows/service vs C1's full-n upper.** Uses the already-written
  `src/eibo/divisibility.py:130 tv_lower_bound_divisibility` (**call it — never restate the formula**, C020).
  It needs **no alphabet bound**, so it applies at **any k** — precisely the large-k region where the plug-in
  certificate is lost. **This is what turns C2's "at large k only the one-sided lower bound survives" from an
  assertion into a MEASURED result**, and it answers RC3 ("what does the asymptotic lower side actually
  certify?"). **Requirements:** state the `realizable` assumption explicitly and **never present it as
  distribution-free**; validity check at the declared alpha over replications; **same objects/channel as X1**
  or say so in one sentence; deliverable = the bound **as a function of k** with the large-k region populated,
  exploratory parts labelled. Runs alongside X12 Stage 2; does not touch `cuda:0`.
- [x] **X12 k=15 entry CLOSED** — registry `DONE`/`success` (completed 05:18:38Z); outcome, zero-evidence
  scope (both independent causes), corpus reduction, `pcap_encoder_formally_dropped`, the k=5 pre-registration
  and the "why k=5 is not post-hoc selection" note all written. **Detector numbers pending the extraction
  read** — not to be backfilled from memory.
- [ ] **X12 STAGE 2 — THE CONTAINMENT STATISTIC IS NOT IMPLEMENTED (D050). This is the real blocker, not k.**
  Verified in source: `deferred_floor_test()` (line 688) is a **stub** unconditionally returning `DEFERRED`
  with the **stale** reason "until the X1 upper side is rebuilt"; line **933** calls it unconditionally; line
  **309** writes the **literal string `"DEFERRED"`** into the `eps_hat_k_hi` and `floor_violation` columns of
  **every** per-pair row; and the script imports nothing from `eibo.statcore` and computes **no TV and no eps
  anywhere**. **⇒ A k=5 run with this script ALSO yields zero containment evidence.**
  **⇒ ORDER OF WORK: implement Stage 2 FIRST, then run ONCE at k=5. Do NOT run k=5 before that** (it would
  reproduce k=15's detector numbers at a different k for another ~68 min).
  **Required in the implementation:** source `eps_hat_k_hi` per pair from the rebuilt X1 data
  (`q1_lower_side_full_n.json`, per-row `upper_recomputed`; D042 landed it), **call the repo radius function —
  never restate the formula** (C020 cost a 2× defect once); compute the informative / secondary / excluded
  strata, the floor `(1-eps_hi)/2`, the violation count and the **one-sided binomial at nominal 0.95 (alpha
  0.05, unsplit)**; **replace the stub, do not wrap it**, and fix line 309 so the CSV carries real values.
  **⚠ OBJECT QUESTION — must be answered in one sentence:** the detector produces errors per held-out
  **SERVICE** while the floor is per **PAIR**. State what a "pair" is in `floor_violation` and how a
  per-service error maps to a pair-level floor. If no per-pair error exists without a pairwise construction,
  **say so** — do not silently substitute (the E7 / M040 object-mismatch class).
- [ ] **THEN X12 at k=5 — the containment-evidence run.** `--k-packets 5`, **no `--cpu-only`** (so `ronetc` uses
  `cuda:0`), `--label-field APP`, D043 months, guard untouched, **new output names**, **panel rebuilt**
  (features are k-dependent, line 165), `submit_on_allocated` (NOT `submit_training_job`).
  **Pre-register the k=5 containment test BEFORE running; a null/negative result is the reported result.**
- [x] **X12 k=15 run COMPLETED CLEANLY (exit 0, 04:59:32)** — D043 split fix **CONFIRMED** (guard PASSED
  unmodified; 5,039,616/4,268,367 flows, both disjoint); label axis confirmed (`APP`, 53 classes). Artifacts
  JSON 139,995 B; per-pair CSV 286.7 MB / 1,493,995 rows. **First real detector numbers** (lightgbm,
  prototype, ronetc — CPU) **scoped to k=15**. **⚠ ZERO containment evidence — for TWO INDEPENDENT reasons:
  (a) informative stratum empty at k=15 (0/946) AND (b) the statistic is unimplemented.** Both must be
  recorded; citing only k would falsely imply k=5 alone fixes it.
- [x] **Pcap-Encoder — formally DROPPED to a 3-detector pre-registration (D049).** By design (~800 GB
  pretraining size); never write "four-detector panel" unqualified.
- [ ] **k-required structural fix** — make `--k-packets` refuse-with-actionable-error instead of defaulting to
  15. **Root cause of the k error was MY command omitting `--k-packets`** (M096): the rule is TWO-SIDED — the
  author names every parameter the statistic depends on; the submitter **stops and asks** when one is missing.
  **Also re-verify the server's `--label-field` default and re-sync the local mirror before the k=5 run.**
- [~] **X3 propagation** — registry ✓ (`DOWNGRADED-TO-INCONCLUSIVE`, `CONTROLS_LANDED_FINAL`) · ROADMAP ✓ ·
  memory.md ✓ (§306 retracted, §318 verdict, C027) · **`paper_framing.md` C3 + plan entry pending**. Both
  control artifacts + `x3_controls.py` local; divergence artifact **UNMODIFIED** (`c19d7392…`).
- [x] **Pcap artifact** — corrected copy (`1234f2d8…`) in the canonical position; stale top-level copy retired
  to `…RETIRED_stale_do_not_cite.json`; manifest updated in the same pass ✓
- [~] **C3 estimator repair (C027-gated)** — **✓ ALL THREE VARIANTS LANDED (D046).** A (estimator-family) and
  B (exposure-conditioning) **both failed their known-truth gates** — that failure IS the finding. C
  (nested-likelihood-route) cleared its own discriminating control and found first-order Markov **45/45 at
  every k=2..30**. **C3 reframed: methods/limits finding (i) + existence corroboration (ii).** Pull/register
  the three new artifacts (C's `x3_variant_c_nested_lr.json` `81000d21…` was NOT registered — its toolset
  lacked the tool; B's `29f9bcab…`; A's final JSON).
- [ ] **Then P1:** X6 (mechanism-novelty — the only structurally different bound mechanism), X7, X9.
  **Then P2:** X10 (closes Step-0), X11, X13.
- [ ] **Registry/plan linkage** — backfill any remaining `registry_id`

## BLOCKED_ON — cross-experiment conditional gates

Cross-experiment conditional todos are the easiest thing to lose: they live as free text in a registry entry and
nothing guarantees they fire. This list is the single enumerable place for them. **A gate is added when it is
created and removed only when it fires and is verified, so an empty-looking entry is itself a claim to check.**

| gate | trigger | state |
|---|---|---|
| `X3_D056` point 3 — the X6 label audit must be re-run once X6 lands, and must not pass silently | X6 artifact lands | **FIRED AND CLOSED** — registry records `X6_LABEL_AUDIT_RE-RUN_RESULT`: *"THE AUDIT RAN AFTER X6'S ARTIFACT LANDED AND X6 IS VERIFIED-CORRECT -- THE CHECK DID NOT PASS SILENTLY."* Seeded as the first entry **to show the list starts accurate rather than empty** |
| `x3_parametric_growth.json` — the stored artifact still carries the D057-withdrawn sentence | the fixed runner is re-run on the server tree | **OPEN** — the source is fixed (both runner copies emit the non-diagnostic wording + `d057_caution`); the stored bytes must NOT be hand-edited because their sha is quoted in the registry as this defect's fingerprint |
| `x3_axis_validation.json` — the stored artifact predates the synced fix | the fixed runner is re-run and the output pulled | **RE-RUN DONE, PULL OUTSTANDING** — the server now holds **123,295 B / `4061258e…`** with the D057 wording and both notes, and all computed values unchanged; **the local copy is still 122,617 B / `9f7578be…`**. Re-register once pulled (D070) |
| ~~axis-validator "path split"~~ — **RESOLVED: it is the registration mechanism, not a defect** | n/a | **CLOSED.** The full chain, assembled from three independent evidences: **`runner writes to the FLAT layer`** (the Agent found server-side universality across 18 artifacts) → **`register_artifact SNAPSHOTS into <EXPID>/`** (D070, my own record) → **`manifest tracks the LOCAL snapshot`** (the piece that makes refresh-and-pull the correct action, not re-path). **Neither of us had all three alone; my check said "18/18 is the mechanism, not 18 defects", the Agent's said "flat is the convention", D070 supplied the middle step.** **⇒ The rule: when a pattern is UNIVERSAL, suspect the reading, not the system.** |
| ~~k=5 producer missing from the repository~~ — **CLOSED.** `x12_detector_validation.py` is now tracked at **56,232 B**, carrying the pair-level code (`pair_error_surrogate`, `maximum_pair_tpr`, `floor_violation_test`) and the corrected `(correct & positive).sum()` numerator, committed in `074a802` and published. **⇒ The repository can now REGENERATE the k=5 containment evidence rather than merely hold it** — before this, it held the 191,867 B artifact and the tracked runner was the pre-rewrite script. **For a paper whose contribution is certification-grade evidence, an untracked producer was a defect of the same severity as a missing artifact.** |
| ~~manifest content hashes~~ — **CLOSED and it immediately earned its keep.** 44/44 live entries now carry `content_sha256`. **Replacing the X6 artifact left its entry recording the PREVIOUS bytes — detected by comparing every recorded hash against its file, exactly one mismatch, fixed at text level (unique substitution, not a serializer round-trip).** **Before this field existed that divergence was invisible unless someone compared two files by hand — which is how three earlier problems were found.** **⚠ The failure mode it prevents is the bad one: a hash describing old bytes reads as a VERIFIED PASS.** |
| **manifest records NO content hashes (48/48 entries)** — so the manifest pins WHERE an artifact is but not WHICH BYTES it is | record a sha256 for every live entry's resolved file | **OPEN — HIGHEST-VALUE STRUCTURAL GAP.** This project's whole evidentiary claim is "every reported number maps to an artifact's bytes", yet nothing lets a reader detect that the file at a cited path has changed. **Three of today's problems would have been caught instantly by a recorded hash:** the axis snapshot going stale (found only because a size happened to differ), the variant-B pre-freeze bytes at a conventional path (found only by a reviewer comparing copies), and `x3_parametric_growth.json` (whose registry-cited sha is exactly what identified which bytes were which). **Action: compute and record the sha256 of every live entry's resolved file; report any path that does not resolve. Do NOT alter artifact files — this is metadata about existing bytes.** |
| ~~axis-validator SNAPSHOT~~ — **CLOSED 11:30.** The pull landed: local is now **123,295 B / `4061258e…`**, matching the server, with the qualified `parametric_artifact` string and both notes present. **Runner constants unchanged; no bytes moved** — the correct action was re-register-and-pull, not the path reconciliation I first proposed and retracted (D092/M121). **This was C031's third instance; the missing step was the PULL, not the run.** |
| ~~X6 validity artifact~~ — **CLOSED.** Local now reads **`outcome: "96/96 TESTABLE rows comply"`** with `testable_replications: 96`, `vacuous_replications: 24`, and the strictly-positive-bound fields present — **the superseded `PASS` on 120/120 with no split is GONE, so the corrected numbers are evidence rather than prose.** **Citable form: "96/96 testable replications comply at α=0.05", parenthetically noting 24 rows have true TV = 0.0 and are vacuously non-violating. Keep the two causes apart — `requested_tv = 0.00` (mathematically incapable) vs insufficient sample (the n=400 clipping) are different, and only 24 rows are the former.** |
| ~~`max_tpr`~~ — **RESULT OBTAINED 11:49; cell count STAYS AT 9, not 6** | pull the recomputed artifact | **RESULT: corrected `maximum_pair_tpr` = lightgbm 0.8746 / prototype 0.8264 / ronetc 0.7758 — all now inside [0,1]; `can_fire_at_or_below_0.01` FALSE in all 12 cells ⇒ THE GUARD STILL CANNOT FIRE ⇒ the 9-cell count STANDS.** **The acceptance gate PASSED** (`reproduced: bool(a==0.39913232104121477 and b==385.38 and 0.5*(a+b)==192.88956616052062)`) — **it reproduced the known-wrong values from the stored payloads BEFORE deriving the correction, which is what makes the corrected numbers usable.** **⇒ CORRECTED VALUES ARE NOW QUOTABLE** (rates in [0,1]); the old 170/193/2.10 are not. **⚠ But keep the two statements separate: "the guard cannot fire" (still true, values ~0.78–0.87) and "the quantity was miscomputed" (also true) are DIFFERENT claims.** **⚠ The recomputed artifact is SERVER-ONLY (11,132 B / `e0dc82e0…`) — numbers are citable only after the pull.** |
| `max_tpr` / `maximum_pair_tpr` — computed wrong, not merely mis-named (M115) | the numerator is constrained to the service's own positives | **OPEN** — fix `(correct & positive).sum() / n_positive`, add the `0 <= value <= 1` assertion, re-run, and re-measure whether the containment cell count is still 9 or has dropped to 6 |
| git push — the framework credential is not readable from a plain shell | a credential channel exists | **BLOCKED (cause known, not an action)** — remote is at `4242dd7`; local is 12 commits ahead; both shells get the identical `could not read Username`. **Report once; do not retry each round.** |

## GPU budget
1× RTX 5090 D bound. **X12 is RUNNING (PID 626935) but on CPU (`--cpu-only`) — the card is idle as a
property of the command, not an omission.** X12 is the only GPU-shaped work besides X11; `ronetc` trains on
CUDA when allowed, so **the next X12 invocation must drop `--cpu-only`**. Earlier the card sat idle for 3+
hours while rounds repeated "every computation is CPU-only" — true but a rubber stamp: *this project's
completed work is CPU-only* does not imply *no GPU work is available*.

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D084 | 2026-09-14 | Retracted my own D119 §3 instruction to take the b | X9, X9_E |
| D083 | 2026-09-14 | Ruled the X9 SNI arm: keep DST_IP as primary per s | X9 |
| D082 | 2026-09-14 | X9 measured a +0.38 SNI-inclusion delta, but the t | X9, X4 |
| D081 | 2026-09-14 | The max_tpr re-measurement produced its answer and | X12_k5, X12 |
| D080 | 2026-09-14 | M108 repeated on a second runner: the parametric r | X3, X6 |
| D079 | 2026-09-14 | Three instances of "the change was made but not pr | X3 |
| D078 | 2026-09-14 | k=5 containment completed and the floor is NOT fal | X12_k5, X1 |
| D077 | 2026-09-14 | Reviewer's three points accepted and acted on: wid | X12_k5 |
| D076 | 2026-09-14 | X11 measured 0.1608 vs the primary corpus's 0.3434 | X11, X1 |
| D075 | 2026-09-14 | Three rulings settled by measurement: (1) the k=5  | X12, X3 |

