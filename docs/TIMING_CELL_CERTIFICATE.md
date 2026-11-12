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

| Corpus | Block width | Pooled Hoeffding | Pooled product | Cell Hoeffding | Cell product |
|---|---|---:|---:|---:|---:|
| QUIC22 | 1 day | 0 | 0 | +0.01605 | +0.05429 |
| QUIC22 | 2 days | 0 | 0 | 0 | 0 |
| QUIC22 | 4 days | 0 | 0 | 0 | 0 |
| QUICEXT-25 XS | 1 day | Pending H5 rerun | Pending H5 rerun | Pending H5 rerun | +0.02206 |
| QUICEXT-25 XS | 2 days | Pending H5 rerun | Pending H5 rerun | Pending H5 rerun | +0.01793 |
| QUICEXT-25 XS | 4 days | Pending H5 rerun | Pending H5 rerun | Pending H5 rerun | +0.01606 |

In QUIC22, both cell methods obtain their daily lower bound from coarse symbol 501. Both pooled bounds are zero. Cell Hoeffding certifies a positive gain, and the cell product bound increases it by 0.03824 pp. In XS, the archived output gives the cell product bound and identifies symbol 469 as the contributor at all three widths. The other columns require the original H5 to recover the block-level weights and scores. [QUIC22 matched comparison](../artifacts/methodology/if_e1/timing_certificate_comparison_quic22.json) · [XS product result](../artifacts/methodology/if_e1_timing_cells_xs_20261112_123022.json)

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

Check the eight-class run against the archived result. It should retain 1,182,338 flows across 81 occupied cells, with 91, 46, and 23 blocks and cell product bounds of 0.02206, 0.01793, and 0.01606 pp at the three widths. Report class counts, retained flows, sample Bayes gains, positive cells, and all four lower bounds for the expansion cohorts. The coverage guarantee applies to each fixed cohort, method, and width. Different cohort sizes use their own class priors and target distributions.
