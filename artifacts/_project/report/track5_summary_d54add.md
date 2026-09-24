# Track 5: dependence-aware radius calibration

Fixed design: n=60000, B=64, concentration=0.1, true TV=0.4, seed=20260919.
i.i.d. reference radius: `0.035179851843`.

Power calculation
-----------------
Required replicates recomputed from p0=0.95, p1=0.9825, two-sided alpha=0.05, target power=0.95: ceil(N)=800; the displayed dispatcher approximation 897 does not follow from the displayed formula, which evaluates to 799.44.

The interval coverage is the two-sided 95% Clopper-Pearson interval over outer replicates. The verdict criterion is the CP lower endpoint versus nominal 0.975; interval non-exclusion is only a reporting distinction, not the verdict.

| Arm | Coverage | CP95 | CP lower clears 0.975 | Radius median | i.i.d. radius | Relation | Falsifier |
|---|---:|---|---|---:|---:|---|---|
| Arm A - block bootstrap | 0.9940 (994/1000) | [0.9870, 0.9978] | yes | 0.041097 | 0.035180 | larger | did not fire |

**Arm A - block bootstrap**: Each sample is partitioned into contiguous B=64 blocks; B-sized blocks are resampled with replacement, with a residual block to preserve n=60000. The radius is recomputed per replicate.
Radius: r_boot = Quantile_0.975(|TV_hat_boot - TV_hat|) over 128 block-bootstrap resamples. Median/mean/min/max = 0.041097/0.041272/0.029112/0.055676.
Falsifier: Fails if the CP lower endpoint remains below nominal 0.975, or if the median block-bootstrap radius is not larger than the i.i.d. radius at n=60000. Result: did not fire.
| Arm B - cluster-robust sandwich | 0.9780 (978/1000) | [0.9669, 0.9862] | no | 0.033172 | 0.035180 | smaller | fired |

**Arm B - cluster-robust sandwich**: The plug-in TV influence function is aggregated by dependence block; the two law-specific cluster-robust variance estimates are summed.
Radius: r_sandwich = z_0.975 * sqrt(V_cluster,A + V_cluster,B), with block-level finite-sample variance correction. Median/mean/min/max = 0.033172/0.033188/0.031047/0.036221.
Falsifier: Fails if the CP lower endpoint remains below nominal 0.975, or if the median cluster-robust radius is not larger than the i.i.d. radius at n=60000. Result: fired.
| Arm C - LOBO | 0.9780 (978/1000) | [0.9669, 0.9862] | no | 0.033117 | 0.035180 | smaller | fired |

**Arm C - LOBO**: For every contiguous B=64 block, TV_hat is recomputed after removing that block from both laws; the LOBO spread estimates the sampling variance.
Radius: r_LOBO = t_0.975,K-1 * sqrt((K-1)/K * sum_j(TV_hat_-j - mean(TV_hat_-j))^2). Median/mean/min/max = 0.033117/0.033242/0.030705/0.037045.
Falsifier: Fails if the CP lower endpoint remains below nominal 0.975, or if the median LOBO Studentized radius is not larger than the i.i.d. radius at n=60000. Result: fired.

Overall verdict
---------------
**The result is RESOLVED, and it is split: one arm succeeds and two fail.**

- **Arm A (block bootstrap) restores nominal coverage**: 0.9940, CP lower endpoint 0.98699 > 0.975. Its interval excludes nominal **from above**, so it clears the gate by over-covering — conservative, not tightly calibrated.
- **Arms B (sandwich) and C (LOBO) do not**: 0.9780, CP lower endpoint 0.96688 < 0.975. Both falsifiers fired.

**The direction is NOT explained by radius size, and the earlier "shrink -> fail" reading is RETRACTED.** Measurement (Track 5b, `track5_diagnosis_between_block.json`) shows the i.i.d. reference is a **union-bound confidence radius** (0.0351799), not a standard error: it is **2.07x the empirical SD of `tv_hat`** (0.0169715). So B and C do not "shrink below a radius that already understates the variance" — they compute a **correctly scaled standard error** against a differently-defined quantity. Their z-multiples are 1.955 and 1.951, i.e. essentially 1.96, while Arm A's is 2.422.

The corrected statement of what happened: **B and C recover the true SD to within 0.1%** (ratios 1.0007 and 1.0000 against the directly measured SD) and land at coverage **statistically indistinguishable from nominal** (978/1000 vs 0.975, exact two-sided binomial p = 0.61); only Arm A deviates significantly (994/1000, p < 0.0001). Their CP lower endpoints do sit just below 0.975, and the likely cause is the **two-sided symmetry** of the interval against an asymmetric `tv_hat` distribution — not a mis-estimated variance. **The open question is therefore whether an asymmetric interval closes the residual gap, not whether the variance is wrong.**

*(The z-multiples quoted above — B 1.955, C 1.951, A 2.422 — were derived as radius / empirical SD (0.0169715358) from the stored radii 0.033172 / 0.033117 / 0.041097 and verified independently; they are not fields in the diagnosis JSON.)*

**Claim boundary (binding):** under the modelled block law at B=64, concentration 0.1, true TV 0.4, a block-bootstrap radius restores nominal coverage at fixed n where the i.i.d. radius does not, while a cluster-robust sandwich and a LOBO Studentized radius do not. This does **NOT** say coverage holds on real traffic — these are synthetic block-law draws; the arms validate a modelled dependence structure, not the corpus.

- `track5_armA_block_bootstrap.json` sha256 `ba58986dd587380ff783ea1c56dce5c131e4c95bdf2f2aa4aaf61df68dfa1f21`
- `track5_armB_sandwich.json` sha256 `c57ab446cd1ca8330f2cb2f3e229bdba289826d5ecab9bfcdb205b7ac46cba77`
- `track5_armC_lobo.json` sha256 `9bc65ce63b391145441df58c1d314473c8fe9ab5ccdf82d8885709cb30852a57`
content_sha256: track5_armA_block_bootstrap.json=ba58986dd587380ff783ea1c56dce5c131e4c95bdf2f2aa4aaf61df68dfa1f21; track5_armB_sandwich.json=c57ab446cd1ca8330f2cb2f3e229bdba289826d5ecab9bfcdb205b7ac46cba77; track5_armC_lobo.json=9bc65ce63b391145441df58c1d314473c8fe9ab5ccdf82d8885709cb30852a57
