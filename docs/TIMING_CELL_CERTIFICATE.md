# A conditional lower bound on the Bayes gain from timing

Adding timing refines the original coarse observation. This lets us lower-bound the gain in each coarse cell and add the positive contributions. The conditional target is the gain in class-weighted Bayes accuracy for the retained cohort, given its labels, coarse observations, block membership, and the timing rule fitted on a separate window.

## Bound and coverage

Use equal class priors and weight each record of class $y$ by $w_i=1/(K n_y)$. In coarse cell $c$, the best coarse rule has known accuracy contribution $A_c=\max_y\sum_{i:C_i=c,Y_i=y}w_i$ under the conditioning. The optimum with timing is $B_c$, obtained from the conditional expected weighted law of labels and timing bins in cell $c$. Since the fine rule can ignore timing, $B_c\ge A_c$ for each $c$.

Hold the fitted timing rule fixed. Let $D_c$ be its known correct mass from records that it classifies correctly for every possible timing bin. Records classified incorrectly for every timing bin contribute zero. For each block $b$ that contains any remaining record in $c$, let $X_{cb}\ge0$ be their observed correct mass. The set of such blocks is determined by the coarse geometry and the fitted rule. Write $m_c$ for its size and $\mu_c=\sum_b\mathbb{E}X_{cb}$. The fitted rule attains expected accuracy contribution $D_c+\mu_c\le B_c$.

Assume independence between the chosen time blocks conditional on the fixed information above. Dependence within a block and dependence across cells in the same block can be arbitrary. For $m_c>0$, independence and the arithmetic–geometric mean inequality give

$$
\mathbb{E}\prod_b X_{cb}=\prod_b\mathbb{E}X_{cb}\le(\mu_c/m_c)^{m_c}.
$$

Markov's inequality then gives a lower confidence bound for $\mu_c$ of $m_c(\alpha_c\prod_b X_{cb})^{1/m_c}$, with failure probability at most $\alpha_c$. If the product is zero or there are no such blocks, the bound for $\mu_c$ is zero. This also covers $\mu_c=0$, when the product vanishes almost surely.

The procedure tests every occupied coarse cell. Occupancy is fixed by conditioning on the coarse observations. With $M$ occupied cells, set $\alpha_c=0.05/M$. A union bound gives simultaneous coverage across the cells at 95% for the fixed block width. The reported lower bound on total Bayes gain is

$$
\sum_c \max\{0,\;D_c+m_c(\alpha_c\prod_b X_{cb})^{1/m_c}-A_c\}.
$$

The nonnegative truncation follows from $B_c\ge A_c$. It permits reporting the contributing cells after evaluation. The earlier zero-gain example concerns the aggregate performance of a single frozen rule, which can lose accuracy in other cells. Here the fine Bayes rule can use timing selectively in each coarse cell. [Frozen-rule analysis](FUSION_CERTIFICATION_LIMITS.md)

## HDF5 reproduction record

The two school-server runs used code commit `81726206cd743c351683982c36c667e846574b80`. The five HDF5 outputs were compared with their respective reference archives. All parsed values matched exactly.

| Reproduced output | Archive comparison |
|---|---|
| [XS service sweep](../artifacts/methodology/timing_repro_VH3il3MK/xs_sweep.json) | Serialization-only difference |
| [XS disjoint window](../artifacts/methodology/timing_repro_VH3il3MK/xs_temporal.json) | Byte-identical |
| [XS omission of symbol 479](../artifacts/methodology/timing_repro_VH3il3MK/xs_omit_479.json) | Byte-identical |
| [QUIC22-S service sweep](../artifacts/methodology/timing_repro_VH3il3MK/quic22_s.json) | Byte-identical |
| [XS block diagnostics](../artifacts/methodology/timing_block_repro_QfpnhZIJ/diagnostics.json) | Byte-identical |

The XS service sweep serializes `fit_counts` in a different position at the top level and in the two expanded cohort objects. Reordering those keys reproduces the new file byte for byte. The new file's SHA-256 is `4ecf051afb0f81bc0de4d035450e4d8e72f35f1031f0bd4b66120dfebbe1c51f`. Use the [original XS service sweep](../artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json) and its SHA-256 `481d73fb0e6be159055dd0c70cb4d9315c04321da3c201c0875340654927a716` as the reference for downstream provenance checks.

The [parity-group bounds](../artifacts/methodology/timing_block_repro_QfpnhZIJ/parity.json) were recomputed from the daily scores. The pooled product bounds match Appendix C at 1.54325 and 1.27665 percentage points for the original and disjoint windows. The two Hoeffding bounds are zero.

The XS block-width figure in Section 4.2 uses the original [service sweep](../artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json) and the [retrospective check](../artifacts/methodology/if_e1_timing_temporal_xs_20261112_150118.json). The [figure script](paper/timing-fusion/plot_fusion_followups.py) reads both archives and plots the cell product bound for 16 classes and the pooled product bound for 44 classes.

## Cross-block dependence and sensor fusion

The dependence experiment uses a balanced binary cohort with known zero Bayes gain. Each block has the same two possible scores and the same marginal law at every correlation level. A recursion computes the exact false-certification rate for the independent-block and parity versions of both the pooled product and pooled Hoeffding bounds. Independent adjacent pairs satisfy the parity assumption by construction. A persistent Markov chain induces dependence at lag two as well. Its rates describe sensitivity under the specified data generating process. The block counts include those of the QUIC22-S sensitivity analysis and the one- and two-day counts of the original XS window.

The sensor experiment uses the [KU-HAR v5 trimmed and interpolated release](https://doi.org/10.17632/45f952y38r.5). The archive contains paired smartphone accelerometer and gyroscope streams in 1,945 activity recordings. Its filenames expose 89 distinct subject IDs. Each sensor is interpolated onto the overlapping clock support and summarized over common, nonoverlapping three-second windows. Windows crossing a gap longer than 15 ms and recordings with ambiguous clocks are counted and excluded. The 18 activity classes have equal evaluation weight. Encoders and class-normalized frequency rules are fitted using only the 30 subjects drawn by the fixed seed. The primary representation uses up to eight decision-tree leaves for each sensor and the primary certificate is pooled product. The 16-leaf encoding and other methods are sensitivity comparisons. The coarse representation uses only accelerometer leaves. The fine representation retains the accelerometer leaf and appends the gyroscope leaf. All windows from one evaluation subject form a single block. Coverage is conditional on the cohort and assumes independence across subject blocks. The JSON keeps the sample Bayes gain, frozen-rule comparison, and four bounds in separate fields.

Run both scripts on the school server in a Python environment with NumPy, SciPy, and scikit-learn. The runner validates the publisher SHA-256 and stores the public v5 download in the ignored data directory. Pass an existing archive as the runner's first argument to reuse a server copy. Output names are timestamped so reruns retain earlier results.

```bash
cd /data/xjw/EIBO &&
conda activate traffic-ncde &&
bash scripts/run_fusion_followups.sh
```

The subject omission check keeps the training set, sensor encoders, and fitted rules fixed. It removes each evaluation subject in turn and recomputes the class weights and coarse optimum for the remaining cohort. An omission that removes an entire activity is marked unavailable. The output reports pointwise pooled product bounds at 0.05 and bounds with a Bonferroni budget of 0.05 divided by the number of candidate omissions. The latter give simultaneous coverage of the evaluable reduced-cohort targets under the subject-block model. The reference check verifies the full primary analysis against the archived result before writing the omission report.

The [KU-HAR archive](../artifacts/methodology/fusion_kuhar_20261114T075451Z.json) gives a primary eight-leaf pooled product bound of 2.419 pp. The [participant omission archive](../artifacts/methodology/fusion_kuhar_omit_subject_20261114T100646Z.json) verifies that result and records all 59 reduced cohorts. The [exact null coverage archive](../artifacts/methodology/fusion_block_dependence_20261114T071847Z.json) contains all 70 settings. Run the [figure script](paper/timing-fusion/plot_fusion_followups.py) with Python to regenerate these plots and the XS block-width figure from the archives.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/fusion_kuhar_certificate.py \
  --archive data/fusion_sensor/kuhar-trimmed.zip \
  --reference artifacts/methodology/fusion_kuhar_20261114T075451Z.json \
  --leave-one-subject-out \
  --out "artifacts/methodology/fusion_kuhar_omit_subject_$(date -u +%Y%m%dT%H%M%SZ).json"
```

## QUIC22 reproduction and null checks

The reproduction uses the archived fit dates, the 283,526 retained evaluation flows, and the original five-packet direction and size representation with the second-packet interval bins. It verifies the archived input manifests and reproduces the original sample Bayes gain and frozen-rule gap.

| Grouping | Units | Positive cells | Conditional Bayes gain lower bound |
|---|---:|---:|---:|
| 1 day | 20 | 1/36 | +0.05429 pp |
| 2 days | 11 | 0/36 | 0 pp |
| 4 days | 6 | 0/36 | 0 pp |

Coarse symbol 501 contributes the entire daily lower bound. Its frozen sample gain contributes +0.14557 pp to overall accuracy. The grouped results use the same records and are sensitivity analyses, each with coverage under its own block-independence assumption. The daily result is exploratory because the holdout informed development of the method. [Reproduction JSON](../artifacts/methodology/if_e1/timing_cell_quic22.json)

The known-null simulations use 36 equally weighted cells with 10 independent time blocks. A shared bit within each cell and block determines whether timing agrees with the label or flips it for all records. Class balance and mean success probability $1/2$ make the conditional Bayes gain exactly zero. The exact family rates provide a check on 100,000 simulated families per scenario.

| Null model | Simulated family false-positive rate | Exact rate |
|---|---:|---:|
| Independent cells with fair bits | 3.541% | 3.456% |
| Fair bit shared across all cells within a block | 0.117% | 0.098% |
| Independent cells with alternating 0.1 and 0.9 block success probabilities | 0.024% | 0.021% |

The simulation JSON includes the one-sided 95% Monte Carlo upper bounds for these rates. [Simulation JSON](../artifacts/methodology/if_e1/timing_cell_null_simulation.json)

## Matched comparison of four certificates

The `--compare` flag evaluates all four certificates from the same retained flows, fitted rule, class weights, and time blocks. The estimand is the conditional Bayes gain defined above. Write $v_{cb}$ for the total weight in cell $c$ and block $b$ of records whose correctness can change with timing. The score $X_{cb}$ is in $[0,v_{cb}]$.

- **Pooled Hoeffding.** Sum the cell scores within each block and use the range $\sum_c v_{cb}$. At tail probability $0.05$, subtract $\sqrt{\tfrac12\log(1/0.05)\sum_b (\sum_c v_{cb})^2}$ from the pooled frozen-rule gain over the coarse optimum. Truncate the result at zero using the nonnegative Bayes gain.
- **Pooled product.** Apply the product lower bound at tail probability $0.05$ to the pooled scores $\sum_c X_{cb}$ over blocks with positive pooled mutable weight. Add the fixed correct mass, subtract the pooled coarse optimum, and truncate at zero.
- **Cell Hoeffding.** At tail probability $0.05/M$, subtract $\sqrt{\tfrac12\log(M/0.05)\sum_b v_{cb}^2}$ from the frozen-rule gain in cell $c$. Truncate each cell at zero and sum. This gives simultaneous coverage across all $M$ occupied cells for the fixed width.
- **Cell product.** Apply the product lower bound to the same $X_{cb}$ with the same cell tail probability and the same truncation and sum.

Each method gives a 95% lower bound under the same conditional block-independence model for the specified width. The table compares methods and grouping assumptions. Each entry is a lower bound on the overall cohort gain in percentage points.

| Corpus | Classes | Block width | Pooled Hoeffding | Pooled product | Cell Hoeffding | Cell product |
|---|---:|---|---:|---:|---:|---:|
| QUIC22 | 8 | 1 day | 0 | 0 | +0.01605 | +0.05429 |
| QUIC22 | 8 | 2 days | 0 | 0 | 0 | 0 |
| QUIC22 | 8 | 4 days | 0 | 0 | 0 | 0 |
| QUICEXT-25 XS | 8 | 1 day | 0 | 0 | +0.03118 | +0.02206 |
| QUICEXT-25 XS | 8 | 2 days | 0 | 0 | +0.01548 | +0.01793 |
| QUICEXT-25 XS | 8 | 4 days | 0 | 0 | 0 | +0.01606 |
| QUICEXT-25 XS | 16 | 1 day | 0 | 0 | 0 | +1.48313 |
| QUICEXT-25 XS | 16 | 2 days | 0 | 0 | 0 | +0.96655 |
| QUICEXT-25 XS | 16 | 4 days | 0 | 0 | 0 | +0.30540 |
| QUICEXT-25 XS | 44 | 1 day | +0.94622 | +2.03485 | +0.70709 | +2.01152 |
| QUICEXT-25 XS | 44 | 2 days | 0 | +1.84013 | +0.00043 | +1.53983 |
| QUICEXT-25 XS | 44 | 4 days | 0 | +1.67772 | 0 | +0.78488 |

In QUIC22, both cell methods obtain their daily lower bound from coarse symbol 501. Both pooled bounds are zero. Cell Hoeffding certifies a positive gain, and the cell product bound increases it by 0.03824 pp. In the eight-class XS cohort, symbol 469 supplies the entire cell product bound at all three widths. Cell Hoeffding gives the larger daily bound, and the cell product bound is larger at the two coarser widths. [QUIC22 matched comparison](../artifacts/methodology/if_e1/timing_certificate_comparison_quic22.json) · [XS service sweep](../artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json)

In the 16-class XS cohort, symbol 509 supplies the entire cell product lower bound at all three widths. The cell includes 574,783 flows and contains mutable records in all 91 daily blocks. On daily blocks its frozen-rule gain contribution is 2.79020 pp and its cell Hoeffding radius is 3.32999 pp. In the 44-class cohort, five cells contribute to the daily cell product bound, and symbols 479, 511, and 509 account for 91.41% of it. Pooled product gives the largest bound at each width in that cohort. [XS per-cell results](../artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json)

## Frozen QUICEXT-25 XS protocol

- Use the registered XS H5 with the SHA-256 in the command below. The established calendar 50/25/25 split fixes the pilot and evaluation windows before reading flow values. On this release they are `[2024-06-01, 2024-11-30)` and `[2025-03-02, 2025-06-01)` in UTC. Use the eight most frequent eligible APP codes in the pilot, the original timing bins and the pilot frequency rule with equal class priors. QUIC22 and XS fit their rules separately and use their respective pilot cohorts.
- The evaluation cohort consists of fitted-class flows whose full timestamp envelope stays within one UTC date. Allow a one-hour margin on the stored end timestamp because the XS absolute times are rounded. Record the number excluded by the daily guard. An absent fitted class makes the evaluation undefined and is reported as an error.
- The primary result is the 95% simultaneous cell bound using UTC days and the full evaluation window. The replication criterion is a strictly positive summed lower bound. Compute 2-day and 4-day sensitivity results on the same retained cohort using fixed UTC epoch-aligned groups. Report all widths and keep the daily result primary.
- The independence assumption is conditional on the fixed labels, coarse observations, grouping, and fitted rule. The day guard confines the records' time envelopes to their assigned days. The provenance of any prior timing analyses on the XS evaluation window determines whether this run is an untouched replication or a retrospective cross-corpus check.

Run from the EIBO checkout on the school server using the existing `traffic-ncde` environment.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_cell_certificate.py xs \
  --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --expected-sha256 6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_cells_xs_$(date +%Y%m%d_%H%M%S).json"
```

For local reproduction and simulation, choose new output paths.

```bash
python3 scripts/quic_timing_cell_certificate.py quic22 --out /tmp/timing_cell_quic22.json
python3 scripts/quic_timing_cell_certificate.py simulate --out /tmp/timing_cell_null_simulation.json
```

For the matched comparison, add `--compare` to the `quic22` or `xs` invocation and choose a new output path. The JSON includes the pooled radius, the two cell-based lower bounds, and the cell Hoeffding radius and contribution for each occupied cell.

## XS service-count expansion

Run the XS command with both `--compare` and `--service-sweep` to obtain the four-way comparison for the original eight classes and two expanded cohorts in one H5 scan. The top-level fields contain the eight-class result. The `service_sweep.expanded_cohorts` object contains the 16-class and all-eligible-class results.

The eight-class baseline retains its original selection rule. For both expansion cohorts, require at least 2,000 usable flows per service in the pilot window, following the [existing methodology runbook](METHODOLOGY_RUNBOOK.md). Rank by decreasing pilot count and use APP code order to break ties. Take the first 16 eligible codes and all eligible codes, respectively. Fit a separate frequency rule for each cohort with equal class priors. The input hash, time windows, daily guard, and block definitions are shared across the sweep. If a selected service is absent after the holdout guard, report its code and the counts for that cohort. Preserve results for the other cohorts.

The archived sweep matches the original eight-class cohort and its per-cell results. It retains 1,182,338, 1,763,662, and 2,038,134 flows for the 8-, 16-, and 44-class cohorts, respectively. Their sample Bayes gains are 3.27412, 4.84831, and 6.39494 pp. Each cohort has 91, 46, and 23 blocks at the three widths. The coverage guarantee applies to each fixed cohort, method, and width. Different cohort sizes use their own class priors and target distributions. [Original eight-class result](../artifacts/methodology/if_e1_timing_cells_xs_20261112_123022.json) · [XS service sweep](../artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json)

## Fixed temporal check for the 16- and 44-class cohorts

Rebuild the frequency rules from the original XS pilot and match the exact APP lists and fitting counts in the archived sweep. The temporal check uses the same equal class priors, feature encoding, one-hour end margin, and daily guard. Its two primary lower bounds use UTC daily blocks. The primary method is cell product for 16 classes and pooled product for 44 classes. Each primary bound uses tail probability 0.025 and has at least 97.5% coverage under conditional daily block independence given its own cohort information. A positive result for both cohorts requires both prespecified bounds to exceed zero. The remaining methods and the 2- and 4-day widths are descriptive sensitivity comparisons at the same per-cohort level.

The executable check uses the middle XS window `[2024-12-01, 2025-03-01)` in UTC. It is disjoint from both the registered pilot and the March–May evaluation used for the service sweep. Earlier project work used the middle window for a different IF-E1 comparison, so report this check as a time-disjoint reanalysis. To evaluate a later untouched capture, use `--later-h5 FILE --later-window START STOP --same-app-codes`. Confirm the APP code semantics and record the capture and half-open UTC dates before inspecting results. The later window starts at least one day after the archived end. The script records missing dates and verifies both H5 digests. A cohort with absent classes records the missing codes and leaves its primary result unavailable. [XS temporal results](../artifacts/methodology/if_e1_timing_temporal_xs_20261112_150118.json)

Run on the school server after updating the experimental branch.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_temporal_check.py \
  --xs-h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_temporal_xs_$(date +%Y%m%d_%H%M%S).json"
```

## QUIC22-S comparison and XS cell contributions

The QUIC22-S comparison scans all 25 million rows of the S release. It uses the timing pilot's fitting dates (October 31 through November 6, 2022), leaves November 7 as a gap, and evaluates November 8 through 27. Dates use the stored H5 timestamps in UTC. Apply the XS H5 rules for valid prefixes, a one-hour end margin, and the holdout daily guard. This is a cross-corpus comparison with the H5 protocol. The original QUIC22 archive-prefix analysis used same-hour eligibility.

Select the top eight, top sixteen, and all non-background APP codes with at least 2,000 usable fitting flows. Use the [CESNET DataZoo APP enumeration](https://github.com/CESNET/cesnet-datazoo/blob/main/cesnet_datazoo/datasets/datasets_constants.py) for the background codes 0, 109, and 110. Fit each cohort's equal-prior frequency rule before evaluation. Keep the cohort fixed if a service is absent from the eligible holdout, and report that cohort as unavailable. Within each cohort and block width, all four methods share the same fitted rule, flow records, and class weights. Daily blocks are primary. The two- and four-day groupings are sensitivity analyses. The 95% coverage applies to each fixed method, cohort, and width under its block independence assumption. [QUIC22-S results](../artifacts/methodology/if_e1_timing_quic22_s_20261112_151423.json)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_cell_certificate.py quic22-s \
  --h5 /data/xjw/traffic-drift2/Experiment/core_code/data/CESNET-QUIC22-S/CESNET-QUIC22-S.h5 \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_quic22_s_$(date +%Y%m%d_%H%M%S).json"
```

The XS diagnosis verifies the fitted cohorts and provenance before comparing the original and temporal windows. It reports positive contributions to the cell product certificate, their shares, and the number of blocks with mutable records in each positive cell. It also reports the product-bound gap and identifies which positive cells recur. The windows use tail probabilities of 0.05 and 0.025, respectively. Interpret the cell shares and overlap descriptively at these levels. In the 16-class cohort, symbol 509 supplies the entire cell product bound in the original window. In the temporal window it supplies 99.97% of the daily bound and the entire two- and four-day bounds. [XS contribution results](../artifacts/methodology/if_e1_timing_xs_diagnostics_20261112_151423.json)

```bash
python scripts/quic_timing_xs_diagnostics.py \
  --temporal artifacts/methodology/if_e1_timing_temporal_xs_20261112_150118.json \
  --out "artifacts/methodology/if_e1_timing_xs_diagnostics_$(date +%Y%m%d_%H%M%S).json"
```

Use `--leave-one-cell-out` to omit the largest daily contributor from the original window and sum the remaining simultaneous cell product bounds for that cohort in both windows and all widths. The weights and error allocation refer to the original cohort. In the 16-class cohort, omitting symbol 509 leaves daily bounds of 0 and 0.00061 pp. In the 44-class cohort, omitting symbol 479 leaves 1.199 and 0.664 pp. [Ablation results](../artifacts/methodology/if_e1/timing_xs_leave_one_cell_out.json)

For the pooled product ablation, use the 44-class equal-prior rule and the two registered XS windows. Select symbol 479 as the largest original daily cell product contributor. Remove that symbol from the block scores, fixed correct mass, and coarse optimum. Keep the original weights and block partition, and report the gain summed over the remaining symbols. The script verifies that the full-cohort bounds match both archives before writing its output. It reports a pointwise bound at the archived tail probability of each window (0.05 and 0.025, respectively) and a bound with Bonferroni allocation over all possible single-symbol omissions in that window and width.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_xs_pooled_ablation.py \
  --xs-h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_xs_pooled_ablation_$(date +%Y%m%d_%H%M%S).json"
```

## Controlled simulation of signal concentration

Use 32 equally weighted coarse cells, balanced binary labels in every cell, and a fixed fine rule that predicts the added binary feature. In each cell and block, eight independent group-level bits set whether that feature agrees with the labels of all flows in each group. Groups contain a balanced pair of labels. Repeat the pair within a group as needed to hold the flow count at 81,920 across 20, 40, 80, and 160 blocks. The data share the same block draws across all four certificates within each replicate.

Under the null the agreement probability is 0.5 everywhere. Under the alternative, distribute exactly 4 pp of Bayes gain across 4, 8, 16, or 32 cells, equally among the selected cells. Keep agreement at 0.5 elsewhere. Use 10,000 replicates per scenario and a tail probability of 0.05 for each fixed method. Report the frequency of a positive lower bound, the median and mean lower bounds, and the frequency of exceeding the known gain.

At 80 blocks with gain concentrated in four cells, the cell and pooled product median lower bounds are 3.064 and 1.940 pp, respectively. With gain spread across all 32 cells, the corresponding medians are 0.030 and 1.928 pp. With 20 blocks, the median pooled bound is zero in both scenarios and the median cell bound is positive in the four-cell scenario. The comparisons identify a concentration effect in this fixed simulation model. [Simulation results](../artifacts/methodology/if_e1/timing_certificate_mechanism.json)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_mechanism_simulation.py \
  --out /tmp/timing_certificate_mechanism.json
```

Use `--cell-count-sweep` to compare 32, 88, and 199 occupied cells for the null and the 4-, 8-, and 16-signal-cell scenarios. Only zero-gain cells split. The children divide the parent's mass and share its block draws. This fixes the true gain and pooled block scores within every matched replicate. The family tail probability remains 0.05. With 80 blocks and eight signal cells, the cell product median falls from 2.146 to 1.817 pp while the pooled median is 1.926 pp. The share of paired replicates in which the cell bound is larger falls from 75.47% to 35.19%. [Cell count sweep results](../artifacts/methodology/if_e1/timing_certificate_cell_count_sweep.json)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_mechanism_simulation.py \
  --cell-count-sweep --out /tmp/timing_certificate_cell_count_sweep.json
python scripts/quic_timing_xs_diagnostics.py --leave-one-cell-out \
  --temporal artifacts/methodology/if_e1_timing_temporal_xs_20261112_150118.json \
  --out /tmp/timing_xs_leave_one_cell_out.json
```

## XS sensitivity to the fitted rule and class prior

Use the exact registered 16- and 44-class cohorts, original fitting period, and both disjoint evaluation periods. Within a cohort and window all scenarios use the same retained records and time blocks. Each fixed bound uses tail probability 0.05. The original-window frequency-rule results are checked against the archived sweep.

- Fit the original frequency rule with equal class priors and use equal priors in evaluation.
- Fit a multinomial logistic rule with additive one-hot terms for the coarse symbol and the timing bin. Fit the rule on counts from the original pilot with equal total weight per class. Fix the L2 penalty coefficient at 0.001 in the normalized objective. Unseen coarse symbols use the original fallback. Use equal priors in evaluation so the Bayes gain target is shared with the frequency rule.
- Keep the equal-prior frequency decisions fixed and evaluate with class priors proportional to the square roots of the pilot class counts. This changes the target while holding the rule fixed. Report both prior vectors and the evaluation counts for all classes. In the 44-class cohort, the APP with 190 original holdout flows receives about 0.675% of the mass under the alternative, compared with 2.273% under equal priors.
- Refit the frequency decisions on the original pilot using those square-root priors. Freeze the refitted rule and evaluate it with the same prior, holdout flows, and blocks as the preceding scenario. The two scenarios use the same Bayes gain target. Compare the frozen-rule gain over the coarse optimum and the resulting lower bounds.

With square-root priors, the archived 44-class sample Bayes gains are 4.471 and 5.137 pp in the original and temporal windows, respectively. The equal-prior frequency rule falls below the reweighted coarse optimum by 4.523 and 1.923 pp. The matched-prior refit gives positive gains over the coarse optimum of 2.968 and 4.415 pp with the same target weights. The daily cell product lower bounds are 1.390 and 1.837 pp. The two- and four-day cell product bounds are also positive in both windows. [Original sensitivity results](../artifacts/methodology/if_e1_timing_xs_sensitivity_20261112_153107.json) · [Matched-prior refit results](../artifacts/methodology/if_e1_timing_xs_refit_20261112_154300.json)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_xs_sensitivity.py \
  --xs-h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_xs_refit_$(date +%Y%m%d_%H%M%S).json"
```

## XS time-block diagnostics and prior comparison

Run one scan of the XS file with the archived 44-class frequency rules and two evaluation windows. Keep the daily guard, flows, feature cuts, and equal evaluation weights fixed for the block diagnostic.

- Report daily mutable correct weight, mutable weight, and their ratio. Calculate descriptive Pearson correlations at lags one through seven UTC days. Pairs must have a defined ratio at both dates, so missing days do not become consecutive observations.
- Recompute the pooled product bound for every calendar offset at widths one, two, and four days. Offset zero reproduces the archived partition. The script checks its bound and block counts against the archive before writing results. Partial blocks at the window edges retain their flows. Each bound is pointwise under conditional independence for that partition. The correlations describe the observed scores.
- On the same retained flows, cross the archived equal-prior and square-root-prior frequency rules with both evaluation priors. The script verifies the three archived comparisons and reports the additional square-root-fitted rule under equal evaluation weights. This comparison uses the archived pointwise error level of 0.05.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/quic_timing_xs_block_diagnostics.py \
  --xs-h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --out "artifacts/methodology/if_e1_timing_xs_block_diagnostics_$(date +%Y%m%d_%H%M%S).json"
```

[Archived XS time-block and prior results](../artifacts/methodology/if_e1_timing_xs_block_diagnostics_20261113_010220.json)

For the manuscript's daily dependence comparison, use each window's
`daily_scores[*].mutable_weight` as $v_b$, `daily_scores[*].mutable_correct_weight`
as $X_b$, and
`prior_comparison.frequency_equal.results_by_block_width.1d.frozen_rule_minus_sample_coarse_optimum`
as the observed gap. Take $\alpha$ from the zero-offset daily row in
`pooled_product_by_block_offset`. The parity-group bounds assume mutual
conditional independence within the even days and within the odd days and
permit dependence between the two groups.

- Hoeffding uses radius $\sqrt{\log(1/\alpha)\sum_b v_b^2}$. Subtract the
  radius from the observed gap and truncate at zero.
- The product method uses $m$ active days with $v_b>0$. Subtract $\sum_b X_b$
  from the observed gap, add $m(\alpha^2\prod_{b:v_b>0}X_b)^{1/m}$, and truncate
  at zero. The product term is zero when an active score is zero or there
  are no active days. The bounds are 1.54325 pp in the original window and
  1.27665 pp in the disjoint window.

## Manuscript simulation figure

Generate the vector figure from the archived cell-count sweep with Matplotlib.

```bash
python3 docs/paper/timing-fusion/plot_cell_count_sweep.py
```

## Weighted allocation on the QUIC22 prefix holdout

Keep the original eight-class cohort, timing cuts, frequency rule, and time
blocks. For coarse cell $c$, let $m_c=\sum_b v_{cb}$ be the class-weighted
mass of records whose fitted-rule correctness can change with timing. This
mass is determined by the labels, coarse observations, and frozen rule. Give
each cell with $m_c>0$ tail probability $\alpha m_c/\sum_j m_j$ and let
zero-mass cells contribute zero. At the same family error budget, the union
bound gives simultaneous coverage across cells for each fixed allocation,
method, and partition under the corresponding block-independence assumption.

On the 20 daily blocks, the cell product bound rises from 0.05429 to
0.21743 pp, with positive contributions from cells 471, 501, and 509.
The cell Hoeffding bound falls from 0.01605 pp to zero. All four cell bounds
are zero with two- and four-day blocks. This is an exploratory comparison on
the archived prefix holdout.
[Per-cell allocations and results](../artifacts/methodology/if_e1/timing_cell_weighted_quic22.json)

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 scripts/quic_timing_cell_certificate.py \
  quic22 --weighted-cells --out /tmp/timing_cell_weighted_quic22.json
```
