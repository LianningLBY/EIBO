# Fusion gain under independent sampling units

This exploratory study compares necessary and attainable sample sizes at the same false-positive rate and power in a binary model. It then checks how the sampling geometry affects certification in two archived QUIC pilots. The model benchmark, the conditional QUIC22 result, and the archived XS pairwise bounds each have their own stated target.

## Fixed-size power in a shared-bit model

Each unit contains equal numbers of observations from two classes. The coarse feature is constant. For every observation in unit $b$, the fine feature equals its label if $U_b=1$ and the opposite label otherwise. The bits $U_b$ are independent Bernoulli$(p)$ draws. Observing any number of repetitions within one unit gives the same information about $p$ as observing one bit. The coarse Bayes balanced accuracy is $1/2$, the fine Bayes balanced accuracy is $\max(p,1-p)$, and the Bayes gain is $|p-1/2|$.

We compare $p=1/2$ with $p=1/2+\Delta$ using one predeclared orientation. For a fixed number of units $n$, a test with size at most $\alpha$ and power at least $1-\beta$ must satisfy

$$
n\,d(1/2+\Delta\mathbin\Vert 1/2)\;\ge\;d(1-\beta\mathbin\Vert\alpha),
$$

where $d$ is Bernoulli KL divergence. Independence adds the unit KL divergences, and data processing through the rejection event gives the inequality. This argument also permits randomized tests. The corresponding change-of-measure inequality is discussed by [Kaufmann, Cappé and Garivier](https://jmlr.org/papers/volume17/kaufman16a/kaufman16a.pdf).

The success count has an increasing likelihood ratio, so an upper-tail binomial test is optimal for this simple alternative. The optimal benchmark fills any unused size budget by randomizing at the boundary. We also evaluate the deterministic exact binomial test and two one-sided Hoeffding certificates. The certificate using the probe's generic change budget uses a range of $2/n$ for each unit contribution. The certificate that uses the known support in this model uses the actual range $1/n$. Power for each method is computed from the binomial distribution at the alternative. The scan checks every unit count up to the first qualifying count, accounting for nonmonotone power from discrete thresholds. [Neyman and Pearson](https://doi.org/10.1098/rsta.1933.0009)

All rows use single-window $\alpha=0.025$ and target power $0.80$. The quantities in the four rightmost columns are the smallest unit counts at which the corresponding tests reach that power.

| Bayes gain (pp) | KL necessary units | Optimal randomized test | Deterministic exact test | Hoeffding with known range | Generic Hoeffding |
|---:|---:|---:|---:|---:|---:|
| 1.00 | 12,279 | 19,621 | 19,648 | 31,577 | 98,344 |
| 2.00 | 3,069 | 4,904 | 4,927 | 7,865 | 24,572 |
| 4.76 | 542 | 865 | 869 | 1,377 | 4,330 |
| 5.27 | 441 | 705 | 716 | 1,121 | 3,527 |

The optimal column gives the exact minimum for this pair of hypotheses. The positive orientation is fixed before testing, and the power applies to that orientation. The 5.27 pp alternative uses the unrounded QUIC22 witness as an illustrative effect size. The earlier planning calculation asks when a radius falls below an observed difference. At 4.76 pp, 3,257 equal-weight units make the generic radius smaller than an observed 4.76 pp difference. For a true difference of 4.76 pp, the same method reaches 80% power at 4,330 units in this model.

## A conditional limitation on the archived QUIC22 timing holdout

We reproduce the frozen frequency rules and the pooled holdout of 283,526 flows from the [timing pilot](../artifacts/quic_timing_pilot_20261111/report.md). The sample Bayes ceiling difference is 5.44 pp. The frozen timing rule exceeds the sample coarse optimum by 5.27 pp.

Condition on the frozen rules, the holdout's class labels and coarse features, and the assignment of records to blocks. Each block can have an arbitrary joint distribution over its timing bins. The blocks are independent and may have different laws. The target is the frozen timing rule's expected class-weighted accuracy under these conditional laws minus the optimal accuracy on the fixed coarse distribution.

For a given flow, vary its timing bin while fixing its coarse feature and label. If the frozen rule's correctness can change, include that flow's weight in the block's change budget $m_b$. The other flows have deterministic correctness. The conditional Hoeffding radius uses $\sum_b m_b^2$ at $\alpha=0.05$.

The same geometry permits a converse. Let $A_0$ be the fixed coarse optimum, $D$ the weight of always-correct flows, and $x_b$ the observed correct weight among flows whose correctness can change in block $b$. Independently in each block, retain the observed timing vector with probability $s_b$. Otherwise, assign each flow whose correctness can change a timing bin for which the frozen rule is wrong. These vectors exist by the definition of the change budget. The expected frozen accuracy is $D+\sum_b s_b x_b$. Choose the probabilities so that it equals $A_0$.

For $x_b>0$, maximizing the probability of retaining the full observation subject to the zero-gain constraint yields $s_b=\min(1,c/x_b)$. Here $c$ solves $\sum_b \min(c,x_b)=A_0-D$. This follows by maximizing $\sum_b\log s_b$ under the weighted-sum constraint and $s_b\le 1$. Blocks with $x_b=0$ are retained with probability one. Under this null, the full observation occurs with probability at least $\prod_b s_b$. If that probability exceeds $\alpha$, a deterministic lower confidence bound with uniform conditional coverage in this model must return a nonpositive value on the observed timing vectors. A positive value there would exceed the zero target with probability greater than $\alpha$.

| Time block | Observed units | Original radius (pp) | Conditional radius (pp) | Probability of retaining the full observation under the zero-gain model |
|---|---:|---:|---:|---:|
| 1 h | 40 | 49.47 | 17.19 | 8.53% |
| 6 h | 20 | 54.75 | 19.04 | 11.02% |
| 24 h | 20 | 54.75 | 19.04 | 11.02% |
| 48 h | 11 | 75.45 | 26.24 | 32.91% |

The probability is a property of the constructed zero-gain law. The conclusion applies to the frozen rule versus the optimal coarse rule for this fixed cohort under the stated conditional model. The fine Bayes optimum can change under the constructed law, so a converse for that optimum requires a separate construction. Stronger restrictions on the timing laws can exclude the constructed null.

## XS pairwise block geometry at eight output bins

The [IF-E1 source result](../artifacts/methodology/if_e1_fusion_20261111_184554.json) uses a different target, the pairwise Bayes gain of the quantized fusion view over the better single view. The archived simultaneous panel covers 2,688 tails per sampling scenario at family error 0.05. Each effective unit count is the inverse squared-mass sum of the units for one pair. The medians below summarize geometry and are conditional on the chosen grouping.

| Window | Grouping | Median effective units | Late pairs with positive gain lower bound | Late pairs with TV upper bound of 1 |
|---|---|---:|---:|---:|
| Certificate | Flow independence | 12,000 | 5/28 | 0/28 |
| Certificate | Start-assigned 24 h | 66.67 | 0/28 | 16/28 |
| Certificate | Span-merged 24 h | 1.33 | 0/28 | 28/28 |
| Evaluation | Flow independence | 12,000 | 1/28 | 0/28 |
| Evaluation | Start-assigned 24 h | 73.67 | 0/28 | 16/28 |
| Evaluation | Span-merged 24 h | 1.00 | 0/28 | 28/28 |

The timing and XS pilots illustrate different losses of information. In QUIC22, an explicit zero-gain construction gives a limitation for the conditional frozen rule. In XS, merging overlapping flow envelopes leaves most of the mass in very few units, and the recorded bound is vacuous under that scenario. The shared-bit power calculations give model benchmarks for these effect sizes. Translating them into collection requirements for either corpus requires a validated sampling model and a test for the corresponding target.

## Reproduction

Run from the repository root with NumPy and SciPy installed. The archived timing report documents reconstruction of the local `.prefix` inputs. The script verifies their manifests and reproduces the timing witness and historical radii before computing the conditional quantities. The XS calculation reads the archived aggregate JSON.

```bash
python3 scripts/fusion_certification_limits.py \
  --prefix-dir data/quic_timing_pilot \
  --xs-result artifacts/methodology/if_e1_fusion_20261111_184554.json
```

The [aggregate result](../artifacts/methodology/if_e1/certification_limits.json) records the critical counts, rejection probabilities, and source hashes.
