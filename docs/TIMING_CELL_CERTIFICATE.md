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
