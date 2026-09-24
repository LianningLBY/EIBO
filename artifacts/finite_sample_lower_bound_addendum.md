# Finite-Sample Lower-Bound Addendum

| Item | Measurement / result |
|---|---|
| Scope | CPU-only, local, no corpus download, no GPU, no manuscript or `.tex` access. |
| Source memo | `artifacts/finite_sample_lower_bound_probe.md`; left unchanged. |
| Real-pair source | `artifacts/_project/data/q1_absolute_dense_counts_m1_m2.json`, M=1, k=5, 45 services, 990 pairs. |
| Dense-count check | Recomputed per-symbol TV from the dense 32-symbol counts; maximum discrepancy against the published 990-pair TV values: `2.22e-16`. |
| Alphabet | `m=32`, fixed a priori; no realized-support cardinality was used. |
| Guarantee convention | Coverage entries below refer to the exact one-sided Clopper–Pearson theorem for a witness fixed by the training split and evaluated on a disjoint held-out split. They are not Monte Carlo estimates of theorem coverage; observed coverage diagnostics are reported separately where available. |

## TASK 3 (DECISIVE) — REAL-PAIR CONCENTRATION

| Per-pair statistic over all 990 pairs | q05 | q25 | median | q75 | q95 |
|---|---:|---:|---:|---:|---:|
| Top-1 share of L1 distance | 0.2463 | 0.3163 | **0.4009** | 0.4788 | 0.5000 |
| Top-2 share of L1 distance | 0.4386 | 0.5430 | **0.6472** | 0.7328 | 0.8482 |
| Top-4 share of L1 distance | 0.7011 | 0.7997 | **0.8605** | 0.9087 | 0.9603 |
| Top-8 share of L1 distance | 0.9170 | 0.9524 | **0.9677** | 0.9787 | 0.9910 |
| Effective support, `(sum |d|)^2 / sum d^2` | 2.6592 | 3.1722 | **3.8556** | 5.0041 | 6.3431 |

| Task 3 conclusion | Result |
|---|---|
| Per-pair concentration across 990 pairs | Top-4 symbols carry median `0.8605` of the L1 distance; median effective support is `3.8556/32`. |
| VERDICT | **CONCENTRATED — deciding numbers: median top-4 share `0.8605`; median effective support `3.86/32`.** |
| IMPLICATION | **asymmetry removable (a)**, conditionally on using a held-out witness construction and verifying the corresponding real-pair lower endpoints. |
| Qualification | This concentration result supports the structural premise for usefulness; it does not by itself establish finite-sample coverage for a real-data classifier witness, nor does it license reusing the memo's unreconciled `0.1330`. |

## TASK 1 — STRUCTURE TABLE

| k / structure | true TV | witness bound (median) | coverage diagnostic | RATIO bound/trueTV | same-data variant invalid-rate |
|---|---:|---:|---:|---:|---|
| 1, one positive symbol; control | 0.193750 | 0.1723 | 0.994 (994/1000) | **0.8894** | n=2791: 0.001 (1/1000); separate prior calibration at n=100/1000/10000: 0.000/0.007/0.015 |
| 2, two positive symbols | 0.193750 | 0.0785 | 1.000 (1000/1000) | **0.4051** | n=2791: 0.000 (0/1000) |
| 4, four positive symbols | 0.193750 | 0.0327 | 1.000 (1000/1000) | **0.1689** | n=2791: 0.000 (0/1000) |
| 8, eight positive symbols | 0.193750 | 0.0101 | 1.000 (1000/1000) | **0.0522** | n=2791: 0.000 (0/1000) |
| 16, sixteen positive symbols | 0.193750 | -0.0012 (vacuous) | 1.000 (1000/1000) | **-0.0059** | n=2791: 0.000 (0/1000) |
| 32, smooth all-symbol zero-sum perturbation | 0.193750 | 0.0071 | 1.000 (1000/1000) | **0.0367** | n=2791: 0.000 (0/1000) |

| Task 1 control / interpretation | Result |
|---|---|
| Generator used for this table | `P` is uniform on 32 symbols. For k<32, `Q` adds `true_TV/k` to k symbols and subtracts `true_TV/(32-k)` from the other symbols. For k=32, `Q` uses a smooth linear zero-sum perturbation rescaled to the same true TV. |
| CONTROL AGREEMENT | **No.** Clean control replication: `0.1723` median at true TV `0.193750` over 1000 held-out replications; the memo headline is `0.1330`. The earlier independent control was `0.1711`, consistent with the clean replication; neither reaches `0.1330`. |
| Validity versus usefulness | Coverage diagnostics are all at or above the nominal 0.95 in this clean grid, but the exact theorem is the validity claim. Tightness collapses as the deviation spreads: k=8 captures `5.22%` of true TV, k=16 is vacuous, and the smooth k=32 row captures `3.67%`. |
| Prior stress reference | A separately measured, non-comparable stress set reported single-point `TV=0.1937`, bound `0.1709`, ratio `0.8825`; spread-8 `TV=0.6000`, bound `0.0566`, ratio `0.0943`; smooth `TV=0.0330`, bound `-0.0115`, ratio `-0.3485`. It is retained as corroborating structure evidence, not mixed into the fixed-TV table. |
| Bonferroni singleton repair | Previously measured and not rescuing tightness: concentrated `0.1709 -> 0.1576`; spread-8 `0.0566 -> 0.0454`. |
| Same-data hole | The clean fixed-TV grid reports same-data selection at n=2791. The separate calibration rates `0.000 / 0.007 / 0.015` at n=100/1000/10000 are from the measured point-mass selection-hole experiment and show the invalid-rate increasing with n; selecting the witness on the evaluation sample is not covered by the held-out CP argument. |

## TASK 2 — RECONCILED NUMBER

| Field | Result |
|---|---|
| Agreed value | **0.1723**, for the clean explicitly reproducible train-selected singleton-witness construction below. The earlier independent `0.1711` is within replication variation and is not treated as a separate construction. |
| Construction for 0.1723 | `m=32`; `P` uniform; `Q=(1-0.20)P+0.20 e_0`; true TV `0.193750`; a 70/30 train/held-out split; select the singleton witness by largest empirical train gap; evaluate on a disjoint held-out split; one-sided CP with total `alpha=0.05`, `alpha/2=0.025` per law; 1000 independent replications; median `0.1723`, observed coverage diagnostic `0.994`. |
| Memo construction attributed to 0.1330 | `m=32`; same point-mass generator; 70/30 split; q ladder `{2,4,8,16,32}`; DecisionTree classifier; one-sided CP allocation `alpha/(2*5)` per class and q; memo says 50 headline replications and selected q=2 in all 50. |
| DOES 0.1330 COME FROM A DIFFERENT CONSTRUCTION THAN THE MEMO DESCRIBES? | **Yes, relative to the agreed value: the reproducible `0.1723` number is from direct train-selected singleton witness CP, whereas the memo attributes `0.1330` to its q-ladder/DecisionTree candidate. The exact source of the memo's `0.1330` remains unresolved; the memo's surrounding q-ladder rows also use 8 replications, creating a separate replication-count inconsistency.** |
| Variants tried and what they gave | At n=2791, the independent reconciliation variants all landed in approximately `0.157–0.175`; none reproduced `0.1330`: same-data witness, per-side alpha, half-sample split, and Bonferroni over m. The clean direct-witness replication gives `0.1723` (1000 reps). |
| Downstream use | Do not cite `0.1330` as an agreed number. Use `0.1723` only with the explicit construction above; the memo value remains unresolved and candidate-specific. |

## CLAMPED CELLS

| Cell | Status |
|---|---|
| Task 1 k=16 row | Raw witness bound `-0.0012`; this is **vacuous**, not a cap. |
| Other cells | No upper cap or lower-bound clamp was reported for the measured rows. The prior non-comparable smooth stress row also had raw bound `-0.0115` and was vacuous. |

## BLOCKERS

| Blocker | Status |
|---|---|
| Full k grid | Resolved locally for k=1,2,4,8,16,32 on a fixed true-TV grid; the structure-specific rates use 1000 replications at n=2791. |
| Exact provenance of memo `0.1330` | Unresolved after the stated variants; the memo's candidate and replication-count description do not agree with the reproducible `0.1723` construction. |
