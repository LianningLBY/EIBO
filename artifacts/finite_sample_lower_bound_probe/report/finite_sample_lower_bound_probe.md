# Finite-Sample Lower-Bound Probe

Date: 2026-09-18 UTC

## Decision

**(a) exists and is tight enough to be worth using**, with an important scope
qualification: the finite-sample lower side is a held-out test-witness bound,
not a universal positive lower endpoint for every pair. It is distribution-free
conditional on independent iid held-out samples and a test fixed by the
training split (or fixed in advance). Its usefulness depends on whether the
witness separates the two laws.

The finite-sample construction is:

```text
TV(P,Q) >= 1 - e0 - e1
```

for any binary test, where `e0` and `e1` are its two population error rates.
On an independent held-out split, replace each error by a one-sided exact
Clopper-Pearson upper endpoint and protect the finite pre-declared q ladder
with Bonferroni allocation. The implemented candidate is
`eibo.divisibility.tv_lower_bound_divisibility`; its returned value is
`max(0, 1 - U0 - U1)`, with the explicit cap at zero.

No parametric or realizability assumption is needed for validity of this
inequality. A realizability or classifier-quality assumption affects
tightness/usefulness only. The construction assumes independent iid samples
for the held-out binomial calibration.

## Literature Verification

### Our own citations

- `lecam1973convergence`: the two-point decision reduction is a valid finite
  sample ingredient, but this citation alone does not provide an observed-data
  lower confidence endpoint for `TV(P,Q)`. DOI:
  https://doi.org/10.1214/aos/1193342380
- `tsybakov2009introduction`: Chapter 2 contains finite-sample two-point,
  Fano, and Assouad lower-bound machinery. It supports the reduction as a
  minimax/testing construction, not the missing one-sided confidence endpoint
  for an unknown pair. DOI: https://doi.org/10.1007/b13794
- `chan2013closeness`: Theorem 1 is a finite-sample closeness tester for
  `p=q` versus `TV(p,q) >= epsilon`, with matching sample-complexity lower
  bounds. It is a testing result, not a lower confidence interval for TV.
  https://arxiv.org/abs/1308.3946
- `diakonikolas2020highprob`: Theorem 1.2 gives a finite-sample
  `(epsilon,delta)` closeness tester with matching information-theoretic
  sample complexity, including the dependence on `delta`. It is high-confidence
  hypothesis testing, not an observed-data lower endpoint. The theorem does
  not supply the bracket's lower-side object directly.
  https://arxiv.org/abs/2009.06540
- `michel2020high`: Proposition 6 and Proposition 7 construct the adaptive
  classifier/projection lower bound, but the relevant bounding function is
  explicitly asymptotic. Appendix B, Corollary 4 supplies the iterated-log
  constant and its proof uses a `limsup` statement. This is the source that
  decides the current implementation's guarantee: Michel's endpoint is not an
  exact finite-sample certificate.
  https://arxiv.org/abs/2005.06006

### External search

- **Exact result:** no cited or outward-searched primary source was found that
  gives the requested assumption-free, finite-sample, observed-data lower
  confidence endpoint for TV in the same form as the bracket.
- **Adjacent-only:** Chan et al. (2013) and Diakonikolas et al. (2020) give
  finite-sample closeness testing; Han, Jiao, and Weissman (2015) and Jiao,
  Han, and Weissman (2018) give non-asymptotic estimation-risk bounds for
  discrete distributions or L1 distance. Those are valid finite-sample
  results, but risk or testing guarantees are not one-sided coverage for a
  realized TV lower endpoint.
  https://arxiv.org/abs/1411.1467
  https://arxiv.org/abs/1705.00807
- **Nothing found:** no primary theorem was found establishing that such a
  finite-sample lower bound is impossible without extra assumptions. The
  negative conclusion `(c)` is therefore not supported.

Michel et al. also state that simulating the standardized hypergeometric
process is the appropriate alternative for smaller effective samples. That is
useful context, but a simulated quantile would require its own Monte Carlo
coverage treatment; it is not needed for the exact held-out binomial witness
used here.

## Numerical Probe

The existing synthetic generator was used: `P` uniform on an `m`-symbol
alphabet and `Q=(1-delta)P+delta*point_mass_at_symbol_0`, so the analytic
truth is

```text
TV(P,Q) = delta * (1 - 1/m).
```

The q-ladder candidate used the repository implementation with
`q in {2,4,8,16,32}`, a 70/30 train/held-out split, one-sided CP endpoints,
and `alpha=0.025` (97.5% confidence). The held-out set was never used to fit
the classifier. The grid below reports medians over 8 independent replications
for the q-ladder candidate; the fixed-event CP values were also checked on
1000 replications over the same generator grid.

| candidate | `m` | total `n` | `delta` | true TV | lower value | gap to true TV | held-out valid? | falsifying number |
|---|---:|---:|---:|---:|---:|---:|:---:|---|
| fixed event `A={0}`, exact CP | 32 | 1,000 | 0.10 | 0.096875 | 0.0263 | 0.0706 | yes | 1/1000 empirical exceedances; exact CP theorem remains the validity argument |
| fixed event `A={0}`, exact CP | 32 | 1,000 | 0.20 | 0.193750 | 0.1115 | 0.0822 | yes | 0/1000 |
| q-ladder CP witness | 32 | 1,000 | 0.10 | 0.096875 | 0.0115 | 0.0853 | yes | 0/8 |
| q-ladder CP witness | 32 | 1,000 | 0.20 | 0.193750 | 0.0935 | 0.1002 | yes | 0/8 |
| fixed event `A={0}`, exact CP | 32 | 2,791 | 0.10 | 0.096875 | 0.0557 | 0.0412 | yes | 2/1000 empirical exceedances; exact CP theorem remains the validity argument |
| q-ladder CP witness | 32 | 2,791 | 0.20 | 0.193750 | 0.1330 | 0.0607 | yes | 0/50 in the headline comparison |
| fixed event `A={0}`, exact CP | 32 | 10,988 | 0.10 | 0.096875 | 0.0771 | 0.0198 | yes | 1/1000 empirical exceedances; exact CP theorem remains the validity argument |
| fixed event `A={0}`, exact CP | 32 | 10,988 | 0.20 | 0.193750 | 0.1700 | 0.0238 | yes | 1/1000 empirical exceedances; exact CP theorem remains the validity argument |
| fixed event `A={0}`, exact CP | 32 | 50,953 | 0.10 | 0.096875 | 0.0872 | 0.0097 | yes | 2/1000 empirical exceedances; exact CP theorem remains the validity argument |
| fixed event `A={0}`, exact CP | 32 | 50,953 | 0.20 | 0.193750 | 0.1828 | 0.0110 | yes | 0/1000 |
| q-ladder CP witness | 32 | 107,065 | 0.10 | 0.096875 | 0.0904 | 0.0065 | yes | 0/8 |
| q-ladder CP witness | 32 | 107,065 | 0.20 | 0.193750 | 0.1859 | 0.0079 | yes | 0/8 |
| fixed event `A={0}`, exact CP | 32 | 1,000,000 | 0.10 | 0.096875 | 0.0948 | 0.0021 | yes | 1/1000 empirical exceedances; exact CP theorem remains the validity argument |
| fixed event `A={0}`, exact CP | 32 | 1,000,000 | 0.20 | 0.193750 | 0.1913 | 0.0024 | yes | 2/1000 empirical exceedances; exact CP theorem remains the validity argument |

The empirical exceedance counts in the fixed-event table are Monte Carlo
diagnostics, not the coverage proof. Exact one-sided CP limits provide the
finite-sample guarantee; the two one-sided limits are allocated half of the
candidate alpha budget.

The broader fixed-event grid used `m in {16,32,64}`, `n in
{1,000,2,791,10,988,50,953,107,065,1,000,000}`, and
`delta in {0.10,0.20}`. The median lower endpoints were:

| `m` | `n=1,000` (`d=.10/.20`) | `n=2,791` (`d=.10/.20`) | `n=10,988` (`d=.10/.20`) | `n=50,953` (`d=.10/.20`) | `n=107,065` (`d=.10/.20`) | `n=1,000,000` (`d=.10/.20`) |
|---:|---:|---:|---:|---:|---:|---:|
| 16 | 0.0107 / 0.0970 | 0.0441 / 0.1345 | 0.0695 / 0.1608 | 0.0827 / 0.1750 | 0.0861 / 0.1790 | 0.0912 / 0.1847 |
| 32 | 0.0263 / 0.1115 | 0.0557 / 0.1455 | 0.0771 / 0.1700 | 0.0872 / 0.1828 | 0.0904 / 0.1864 | 0.0948 / 0.1913 |
| 64 | 0.0345 / 0.1205 | 0.0628 / 0.1537 | 0.0810 / 0.1757 | 0.0904 / 0.1869 | 0.0929 / 0.1901 | 0.0966 / 0.1947 |

The analytic truths for these columns are respectively
`0.1*(1-1/m)` and `0.2*(1-1/m)`. Across the 36 fixed-event cells, the
empirical coverage was 995--1000/1000; this is a diagnostic range, while the
exact CP theorem supplies the stated coverage.

The fully distribution-free empirical-TV-minus-radius construction was also
checked against the repository's finite-alphabet radius. It is valid but much
looser at the real small count: at `m=32, n=2,791, true TV=0.19375`, its
median lower value was `0.0339`, versus `0.1330` for the held-out test
witness. It is not the candidate worth carrying forward.

## Cost Against Michel at Real `n`

At `n = 2,791` with `m=32` and generator TV `0.19375`, the exact finite-sample
held-out CP construction gives **`Y=0.1330`** (median over 50 headline
replications), where the current asymptotic Michel form gives
**`Z=0.1198`**, at a cost of **`W=0.0132` in the opposite direction**:
the finite-sample endpoint is 0.0132 higher, not lower. The finite endpoint
still leaves a `0.0607` median gap to the analytic truth, while Michel leaves
`0.0739`.

At `n=107,065`, the corresponding medians are approximately `0.1859` versus
`0.1819`, with true TV `0.19375`. At `n=1,000,000`, the fixed-event
finite-sample endpoint is `0.1913` for that same truth. The finite-sample
construction is therefore not hopelessly loose over the project's actual
`10^3`--`10^6` range; it becomes tight once the held-out witness has enough
counts.

## Combinatorial Re-Derivation

```text
max(0, 1 - m/C) at m=32, C=46
= max(0, 1 - 32/46)
= 14/46
= 7/23
= 0.3043478261.
```

For `C=45`, the value is `13/45 = 0.2888888889`. Both exceed the existing
`0.186` certified floor. Verification used exact integer arithmetic for the
fractions and independently compared the resulting decimals with the
`floor_M46=0.18577` value read from `artifacts/openset_delta.json`; no rounded
intermediate was used.

## Required Summary

STEP 1 OUR OWN CITATIONS: `lecam1973convergence` and `tsybakov2009introduction` are valid finite-sample two-point/minimax ingredients but do not by themselves give a usable observed-data TV lower endpoint; `chan2013closeness` and `diakonikolas2020highprob` are finite-sample closeness testers, not lower confidence intervals; `michel2020high` is the current adaptive lower side but merely asymptotic, not finite-sample.

STEP 1 EXTERNAL: (i) exact result: no matching external finite-sample TV lower-confidence endpoint found; (ii) adjacent-only: Chan et al. 2013, Diakonikolas et al. 2020, Han et al. 2015, and Jiao et al. 2018; (iii) nothing found: no theorem-level impossibility result without extra assumptions.

STEP 1 VERDICT: **(a)** — a finite-sample held-out test-witness lower bound exists and is tight enough to be worth using at the project's real `n`; Michel et al., Proposition 6/7 and Appendix B, decides that the current adaptive form itself is only asymptotic, while the exact finite-sample replacement is the held-out CP construction above.

STEP 2 CANDIDATES: `fixed-event CP witness | values shown for m=32, n=10^3--10^6 and delta=0.1/0.2 | gaps 0.0021--0.0822 in the shown grid | valid on held-out? yes | falsifying number: no theorem-level falsification; empirical exceedances were at most 2/1000`; `q-ladder held-out CP witness | 0.0115--0.1859 on the shown grid | gaps 0.0065--0.1002 | valid on held-out? yes | falsifying number: 0/50 headline exceedances and 0/300 violations in the existing synthetic validity report`; `empirical-TV-minus-radius | valid but loose | at n=2791,m=32,true TV=0.19375 median 0.0339, gap 0.1598 | held-out? yes | falsifying number: none observed`.

STEP 3 COST AT REAL n: "at n=2791, m=32: finite-sample Y=0.1330 vs asymptotic Z=0.1198, cost W=0.0132 in endpoint value"; the finite-sample endpoint is higher and has the stronger guarantee.

COMBINATORIAL RE-DERIVATION: `max(0,1-m/C)` at `m=32,C=46` = `0.3043478261`; exceeds `0.186`? **yes**; verified by exact arithmetic `14/46=7/23` and an independent read of `artifacts/openset_delta.json`.

INVALID CANDIDATES: none by theorem-level validity; the empirical-TV-minus-radius candidate is retained only as a valid-but-too-loose diagnostic, not as the recommended lower side.

FULL VERSION WORTH BUILDING?: **yes** — estimated remaining effort `0.5--1 CPU day` to integrate the held-out CP witness, its alpha/split metadata, caps, and regression tests; **not built here**.

MEMO: `artifacts/finite_sample_lower_bound_probe.md` size 12247 bytes

BLOCKERS: none
