# IF-E1 experimental results

The local QUIC22 pilot files under [local_quic22](local_quic22/) are the original aggregate JSON outputs and their label mapping. They were produced using a locally assembled subset with a different label encoding. The tables below transcribe the numerical results printed by the school-server runs. All gains and intervals are in percentage points (pp).

## QUICEXT-25 XS discovery

| Bins | Window | Early vs frozen best single | Late vs frozen best single | Positive Bayes lower bounds, early / late |
|---:|---|---:|---:|---:|
| 4 | Certificate | +1.11 | +1.11 | 0/28 / 0/28 |
| 4 | Evaluation | +0.04 | +0.50 | 0/28 / 0/28 |
| 8 | Certificate | +1.20 | +1.35 | 0/28 / 0/28 |
| 8 | Evaluation | +1.27 | +1.71 | 0/28 / 0/28 |
| 16 | Certificate | +1.37 | +1.33 | 0/28 / 0/28 |
| 16 | Evaluation | +0.66 | +1.09 | 0/28 / 0/28 |

The lower-bound counts use the simultaneous panel with merged 24-hour blocks. At B=8, late fusion exceeded the sample-optimal single source in 17/28 certificate pairs and 16/28 evaluation pairs. Under flow independence, 5/28 and 1/28 had positive lower bounds. The median radii were 4.26 pp in both windows under flow independence and 404.00 and 466.74 pp under the merged 24-hour construction. APP 0 vs 1 was the only pair with a positive lower bound in both windows under flow independence, at +1.15 and +0.50 pp.

| APP pair | Certificate sample gain | Evaluation sample gain |
|---|---:|---:|
| 0 vs 1 | +5.41 | +4.76 |
| 0 vs 2 | +2.61 | +3.18 |
| 0 vs 3 | +1.19 | +2.71 |
| 0 vs 4 | +5.74 | +4.13 |
| 0 vs 14 | +4.42 | +2.73 |
| 0 vs 16 | +5.27 | +3.44 |
| 0 vs 51 | +5.33 | +3.56 |
| 1 vs 14 | +0.65 | +1.82 |
| 2 vs 4 | +1.16 | +2.47 |
| 3 vs 4 | +0.78 | +0.02 |
| 3 vs 14 | +3.25 | +2.33 |
| 4 vs 14 | +1.08 | +0.88 |
| 4 vs 51 | +1.62 | +1.54 |

These 13 pairs exceeded the sample-optimal single source in both original windows. The certificate window was 2024-12-01 through 2025-02-28 and the evaluation window was 2025-03-02 through 2025-05-31, in UTC. The frozen B=8 artifact contains the APP 0 vs 1 reference and 21 control pairs.

### APP 0 vs 1 by date

| Window | Dates with both classes | Dates beating frozen single | Dates beating daily sample-optimal single | Pooled gain vs frozen single |
|---|---:|---:|---:|---:|
| Certificate | 86/90 | 86/86 | 68/86 | +5.41 |
| Evaluation | 87/91 | 86/87 | 59/87 | +6.62 |

The largest three daily contributions were +0.17 pp each in certificate (2025-02-24, 2025-02-11, and 2024-12-18) and +0.18 pp each in evaluation (2025-05-15, 2025-04-07, and 2025-04-01).

| Window | Date stride | Dates | Single-source rule | Mean gap | Geometric equivalent gap | Conditional lower bound | Projected independent batches |
|---|---:|---:|---|---:|---:|---:|---:|
| Certificate | 1 | 86 | Best for each date | +1.78 | +1.67 | −2.60 | 224 |
| Certificate | 1 | 86 | Fixed over window | +5.50 | +5.46 | +1.03 | 70 |
| Certificate | 2 | 43 | Best for each date | +1.93 | +1.80 | −6.57 | 207 |
| Certificate | 2 | 43 | Fixed over window | +4.92 | +4.88 | −3.74 | 78 |
| Certificate | 7 | 13 | Best for each date | −0.29 | −0.47 | −25.06 | — |
| Certificate | 7 | 13 | Fixed over window | +6.21 | +5.75 | −20.38 | 67 |
| Evaluation | 1 | 87 | Best for each date | +1.39 | +1.29 | −2.92 | 289 |
| Evaluation | 1 | 87 | Fixed over window | +4.61 | +4.41 | +0.08 | 86 |
| Evaluation | 2 | 44 | Best for each date | +1.43 | +1.30 | −6.85 | 286 |
| Evaluation | 2 | 44 | Fixed over window | +4.67 | +4.45 | −3.95 | 85 |
| Evaluation | 7 | 12 | Best for each date | −0.37 | −0.42 | −26.78 | — |
| Evaluation | 7 | 12 | Fixed over window | +3.89 | +3.63 | −23.79 | 104 |

The product bounds are conditional on independence between the retained date batches. The 7-day stride selected Sundays in both windows. The following planning simulation used the old windows' daily bin counts and resampled contiguous date blocks under both alternate-day phases.

| Planned capture days per window | Calendar days per window | Certificate pass estimate | Evaluation pass estimate | Conservative joint pass estimate |
|---:|---:|---:|---:|---:|
| 90 | 179 | 96.5% | 30.6% | 27.0% |
| 100 | 199 | 100.0% | 55.0% | 55.0% |
| 125 | 249 | 100.0% | 94.4% | 94.4% |
| 150 | 299 | 100.0% | 99.9% | 99.8% |
| 180 | 359 | 100.0% | 100.0% | 100.0% |
| 220 | 439 | 100.0% | 100.0% | 100.0% |

The server inventory found zero eligible H5 files with dates from 2025-06-02 onward. The formal new-period validation remains unrun.

## QUIC22-S transfer and target calibration

APP 0 is `default-background` and APP 1 is `google-www` in both releases. QUIC22-S covered 28 UTC dates, 2022-10-31 through 2022-11-27. The pooled scan found 973,743 and 1,716,141 eligible flows in the two classes. The full-window comparisons used 6,000 sampled flows per class.

| Analysis | Prefix BA | PHIST BA | Late BA | Late gain vs strongest single |
|---|---:|---:|---:|---:|
| Direct transfer, equal dates, target-optimal singles | 77.01% | 77.67% | 77.43% | −0.24 |
| Direct transfer, pooled flows, target-optimal singles | 76.77% | 76.84% | 77.08% | +0.23 |
| Same-sample optimal bin rules, equal dates | 77.01% | 77.67% | 79.95% | +2.28 |
| First 14 dates, target calibration | 77.17% | 77.15% | 80.13% | — |
| Last 14 dates, fixed calibrated rules | 76.24% | 78.18% | 80.18% | +2.00 |

The chronological calibration used 2022-10-31 through 2022-11-13. The holdout used 2022-11-14 through 2022-11-27. Each window retained 6,000 flows per class and all 14 dates. The calibrated rules for bins 0–7 were prefix `[0,0,0,0,1,0,1,1]`, PHIST `[0,0,0,0,1,1,1,1]`, and late `[0,0,0,0,0,0,1,1]`. Original frozen late BA in that holdout was 76.97%, so target calibration increased it by 3.21 pp. The gain over the calibration-selected single (prefix) was +3.94 pp.

| Paired circular date block length | APP 0 vs 1 holdout gain, approximate 95% CI |
|---:|---|
| 3 days | [+1.03, +2.97] |
| 2 days | [+0.97, +3.03] |
| 4 days | [+1.13, +2.87] |

The interval projects the simultaneous intervals for the two fixed calibrated comparisons onto their minimum gain.

### 21 frozen control pairs

The QUIC22-S panel reproduced +2.00 pp for APP 0 vs 1. The 21 control pairs exclude APP 0. All 21 were scored under the same chronological calibration and holdout split. APP codes in this table are from QUICEXT-25.

| APP pair | Services | Strongest single on holdout | Late gain |
|---|---|---|---:|
| 1 vs 2 | google-www vs google-play | PHIST | +1.63 |
| 1 vs 3 | google-www vs google-services | Prefix | +1.84 |
| 1 vs 4 | google-www vs google-gstatic | Prefix | +2.43 |
| 1 vs 14 | google-www vs youtube | PHIST | +2.24 |
| 1 vs 16 | google-www vs google-ads | Prefix | +0.81 |
| 1 vs 51 | google-www vs google-background | Prefix | −8.90 |
| 2 vs 3 | google-play vs google-services | Prefix | −0.83 |
| 2 vs 4 | google-play vs google-gstatic | Prefix | +1.31 |
| 2 vs 14 | google-play vs youtube | PHIST | +0.12 |
| 2 vs 16 | google-play vs google-ads | Prefix | +0.47 |
| 2 vs 51 | google-play vs google-background | PHIST | +3.54 |
| 3 vs 4 | google-services vs google-gstatic | PHIST | +1.08 |
| 3 vs 14 | google-services vs youtube | PHIST | +2.80 |
| 3 vs 16 | google-services vs google-ads | Prefix | +3.35 |
| 3 vs 51 | google-services vs google-background | Prefix | +0.26 |
| 4 vs 14 | google-gstatic vs youtube | Prefix | +2.36 |
| 4 vs 16 | google-gstatic vs google-ads | Prefix | +2.06 |
| 4 vs 51 | google-gstatic vs google-background | Prefix | +0.95 |
| 14 vs 16 | youtube vs google-ads | Prefix | +1.26 |
| 14 vs 51 | youtube vs google-background | Prefix | −0.92 |
| 16 vs 51 | google-ads vs google-background | PHIST | +3.66 |

The panel had 18 wins, no ties, and 3 losses. Mean gain was +1.02 pp and median gain was +1.31 pp. The shared-date circular bootstrap gave an approximate 95% interval for the mean of [+0.25, +1.80] pp with 3-day blocks, [+0.25, +1.80] with 2-day blocks, and [+0.26, +1.79] with 4-day blocks. This retrospective comparison measures the gain of calibrated decisions on the target holdout.

The [panel implementation](../../../scripts/if_e1_fusion_quic22_panel.py) produced the school-server panel result. The [experiment runbook](../../../docs/IF_E1_FUSION_PROBE.md) describes the original probe and frozen artifact.
