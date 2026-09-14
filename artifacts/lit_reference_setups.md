# Literature Reference Setups for EIBO

Research date: 2026-09-13

This note separates statements verified in primary sources from inferences and
items that remain unverified. No dataset was downloaded.

## A. Michel, Naf, and Meinshausen: classifier-based TV lower bounds

### Bibliography

Verified arXiv record:

> Loris Michel, Jeffrey Näf, and Nicolai Meinshausen. "High Probability Lower
> Bounds for the Total Variation Distance." arXiv:2005.06006, 2020.

The paper is available as arXiv:2005.06006. The fetched sources identify the
work as an arXiv preprint; a peer-reviewed venue was not verified from the
primary record. A thesis record says it was submitted to the Journal of
Multivariate Analysis, but that is not treated as a publication venue.

Sources:

- https://arxiv.org/abs/2005.06006
- https://arxiv.org/pdf/2005.06006

### Population inequality and classifier notation

Let `P` and `Q` be probability measures on `X`, and let
`rho: X -> [0,1]` be any measurable score/projection. For a cutoff `t` define

```text
rho_t(z) = 1{rho(z) > t}.
```

The in-class accuracies are

```text
A0(t) = P(rho_t(X) = 0) = P(rho(X) <= t)
A1(t) = Q(rho_t(Y) = 1) = Q(rho(Y) > t).
```

The paper's classifier form is

```text
TV(P,Q) >= sup_{t in [0,1]} [ A0(t) + A1(t) ] - 1.
```

Equivalently, with `F = rho#P` and `G = rho#Q`,

```text
A0(t) + A1(t) - 1 = F(t) - G(t).
```

The more general preceding inequality is

```text
TV(P,Q) >= TV(rho#P, rho#Q)
         >= sup_t | F(t) - G(t) |.
```

The paper writes the in-class form as a one-sided supremum; the score
orientation can be reversed if the useful direction is `G-F`.

### Fixed-cutoff, asymptotic HPLB

For independent held-out samples

```text
X_1,...,X_m iid~P
Y_1,...,Y_n iid~Q,
```

and a fixed cutoff `t`, compute

```text
Ahat0(t) = (1/m) sum_i 1{rho(X_i) <= t}
Ahat1(t) = (1/n) sum_j 1{rho(Y_j) > t}

sigmahat(t) =
  sqrt( Ahat0(t)(1-Ahat0(t))/m
      +Ahat1(t)(1-Ahat1(t))/n ).
```

Proposition 3 gives the fixed-cutoff estimator

```text
lambdahat_bayes(t)
  = Ahat0(t) + Ahat1(t) - 1
    - q_(1-alpha) * sigmahat(t),
```

where `q_(1-alpha)` is the `(1-alpha)` standard-normal quantile. The paper
calls this an asymptotic HPLB at level `alpha`, meaning

```text
limsup_N P(lambdahat_bayes(t) > TV(P,Q)) <= alpha.
```

The R implementation uses the default cutoff `0.5`, computes the two empirical
accuracies, subtracts `qnorm(1-alpha)*sigmahat`, and clips the returned value
at zero.

The fixed-cutoff estimator is the high-probability version of the usual
empirical balanced-accuracy expression. It is not a simultaneous search over
cutoffs.

### Adaptive sup-over-cutoff estimator

The implementable adaptive construction uses the ranks of held-out scores.
Pool the `m+n` test observations, sort them by increasing `rho`, and let

```text
J_mn = {1,...,m+n-1}
V_m,z = number of class-0 observations among the first z ranked observations.
```

If `z` is the rank endpoint associated with a cutoff, then

```text
Fhat_m(t) - Ghat_n(t)
  = (m+n)/(m*n) * [ V_m,z - m*z/(m+n) ].
```

For a candidate TV value `lambda_tilde in [0,1]`, define

```text
q_m(lambda_tilde) = qbinom(1-alpha/3, size=m, prob=lambda_tilde)
q_n(lambda_tilde) = qbinom(1-alpha/3, size=n, prob=lambda_tilde)

m0 = m - q_m(lambda_tilde)
n0 = n - q_n(lambda_tilde)
N0 = m0 + n0.
```

The paper's bounding function is

```text
Q_m,n,alpha(z, lambda_tilde) =

    z,                                  1 <= z <= q_m(lambda_tilde)

    q_m(lambda_tilde) + S(z-q_m),       q_m(lambda_tilde) < z
                                         < m + n0

    m,                                  m + n0 <= z <= m+n,
```

where the middle confidence band `S` can be simulated from the hypergeometric
process or evaluated analytically. For the analytical band in Appendix B,

```text
S(u) =
    u * m0/N0
    + beta_(alpha/3,m0) * w(u,m0,n0)

w(u,m0,n0) =
    sqrt( (m0/N0) * (n0/N0)
          * ((N0-u)/(N0-1)) * u ).
```

The paper's analytical multiplier is

```text
x_alpha = -log( -log(1-alpha) / 2 )

beta_(alpha,m0) =
    sqrt(2*log(log(m0)))
    + [ log(log(log(m0))) - log(pi) + 2*x_alpha ]
      / [ 2*sqrt(2*log(log(m0))) ].
```

For the adaptive bound, use `alpha/3` in both the binomial witness quantiles
and the confidence-band multiplier.

The adaptive estimator is

```text
lambdahat_adapt =
  inf { lambda_tilde in [0,1]:
        sup_{z in J_mn}
        [ V_m,z - Q_m,n,alpha(z,lambda_tilde) ] <= 0 }.
```

In code, evaluate candidates in an increasing grid, find the smallest
candidate for which the entire ranked count process is below the bounding
function, and return that candidate. The published R implementation uses this
grid-search form. For small samples, the paper recommends a simulated
simultaneous confidence band because the analytical band is asymptotic and can
be a poor approximation.

The paper's formal guarantee for the adaptive construction is an asymptotic
HPLB at level `alpha`:

```text
limsup_N P(lambdahat_adapt > TV(P,Q)) <= alpha.
```

Thus the confidence parameter is `alpha`, and the nominal coverage statement
is `1-alpha`. The internal construction splits the error budget into three
parts using `alpha/3`.

### Assumptions

Verified assumptions in the paper:

1. The test samples are two independent iid samples, one from `P` and one from
   `Q`.
2. The held-out sample sizes are non-random, with `N=m+n` and
   `m/N -> pi in (0,1)` as `N -> infinity`. The paper also adopts `m <= n`
   for notational convenience.
3. The score `rho` must be measurable and bounded in `[0,1]` for the displayed
   binary-classification formulas.
4. If `rho` is estimated by a classifier, it must be trained on data
   independent of the held-out test sample. Formally, the paper assumes
   independent training and test samples, both increasing in size, and
   `m_test/N_test -> pi in (0,1)`.

No known class-prior value is required to compute the held-out accuracies,
their ranks, or the adaptive HPLB. The observed class counts `m` and `n` are
used directly. A prior is relevant only if one wants to interpret `rho` as a
Bayes posterior or choose the Bayes-optimal fixed cutoff. In particular, for a
posterior using class prior `pi`, the paper notes that cutoff `1-pi` recovers
the balanced Bayes classifier; cutoff `1/2` is correct for equal priors.

The main finite-sample statement in the paper is not a generic exact
finite-sample guarantee: the principal `bayes` and `adapt` results are
asymptotic HPLBs. The package also exposes simulation-based and other
practical variants.

### Weak versus strong classifiers

For a weak classifier/cutoff with

```text
A0(t) + A1(t) <= 1
```

the population classifier witness is nonpositive, so the lower bound is
trivial after clipping to the valid range `[0,1]`. The fixed-cutoff empirical
HPLB can be negative before clipping because it subtracts a one-sided
confidence penalty. The adaptive estimator will normally return zero (or the
lowest grid value) when no cutoff clears its simultaneous boundary.

For a strong classifier, the per-class accuracies produce a positive witness.
The adaptive estimator can use a cutoff different from `1/2` and can therefore
recover a positive bound when a fixed `1/2` cutoff has little or no power.

### Relation to `TV >= 2a - 1`

For balanced accuracy

```text
a(t) = [A0(t) + A1(t)]/2,
```

the classical population inequality at a fixed cutoff is exactly

```text
TV(P,Q) >= 2*a(t) - 1.
```

Michel et al. generalize this in two ways:

1. They take the supremum over all score cutoffs, rather than fixing `t=1/2`.
2. They add a simultaneous high-probability correction for held-out sampling.

At the population level,

```text
sup_t [A0(t)+A1(t)-1] >= A0(1/2)+A1(1/2)-1,
```

with strict improvement possible when `1/2` is not the useful cutoff. The paper
gives examples where the fixed `1/2` estimator achieves only the
`N^(-1/2)` detection rate while the adaptive estimator reaches the oracle
rate. This occurs, for example, when the distributional difference is
concentrated in a tail or otherwise requires a nonstandard cutoff.

This is not a claim that the finite-sample HPLB is numerically larger than the
uncorrected empirical `2*ahat-1` on every sample. The HPLB pays a confidence
penalty and is designed to be valid with high probability.

### Public implementation

Verified public implementation:

- GitHub: https://github.com/lorismichel/HPLB
- Main R implementation: https://raw.githubusercontent.com/lorismichel/HPLB/master/R/HPLB.R
- Package description: https://raw.githubusercontent.com/lorismichel/HPLB/master/DESCRIPTION

The repository implements `bayes`, `adapt`, simulation-based adaptive
variants, and examples using independent train/test predictions. The
repository DESCRIPTION reports version `1.0.0`; CRAN's current package page
reported that HPLB had been removed and archived on 2026-05-14.

## B. CESNET QUIC22 and QUICEXT-25 conventions

### Primary sources

- Luxemburk et al., QUIC22 article: https://pmc.ncbi.nlm.nih.gov/articles/PMC9851865/
- QUIC22 DOI: https://doi.org/10.1016/j.dib.2023.108888
- QUIC22 associated data record: linked from the article's Data Availability
  Statement at the PMC page above.
- CESNET DataZoo repository: https://github.com/CESNET/cesnet-datazoo
- CESNET DataZoo PyPI project: https://pypi.org/project/cesnet-datazoo/
- CESNET DataZoo documentation landing page: https://cesnet.github.io/
- QUICEXT-25 Zenodo search: https://zenodo.org/search?q=CESNET-QUICEXT-25

The associated Mucke et al. measurement paper, "Waiting for QUIC: Passive
Measurements to Understand QUIC Deployments" (Proc. ACM Networking, CoNEXT
2025), was identified by title but its full primary text and exact
bibliographic identifier were not exposed by the fetched pages in this scan.
Claims below that are explicitly about QUICEXT-25 rather than QUIC22 are
marked accordingly.

### 1. QUIC22 service-label derivation

Verified from the dataset article:

1. The service-selection process first chose a diverse, high-volume subset of
   web services. The selected services cover 84% of all QUIC traffic observed
   in the CESNET2 network.
2. The authors recognized services using SNI domains extracted from the QUIC
   handshake.
3. To construct the SNI-to-service map, they used service documentation,
   including "whitelist domains for network and firewall settings", Netify's
   Application Lookup Tool, and manual inspection/hand-picking of observed SNI
   values for the remaining cases.
4. The SNI-to-service map was then used to assign the `APP` service label to
   each captured flow.
5. Each selected web service is its own traffic class. The dataset also
   provides a `CATEGORY` field and organizes services from the same provider
   into provider groups, such as Google and Facebook/Meta.
6. The primary article states 17 service categories. Category/provider
   organization is additional grouping metadata; it does not replace the
   individual `APP` service labels.
7. Traffic not mapped to one of the selected services is split into three
   background classes: Google Background, Facebook Background, and Default
   Background.

The article states 102 service labels, plus the three background classes. Thus
the QUIC22 label inventory is 102 selected-service labels and 3 background
labels, i.e. 105 `APP` classes if all background classes are included.

No explicit minimum-flow threshold per selected service was found in the
primary article. The selection criteria are described as traffic volume and
diversity, but a numeric per-service minimum is **unverified**.

### 2. Sampling and tier sizes

The original QUIC22 capture uses dynamic per-service sampling, not one uniform
sampling ratio:

- top 5% of services: 1:15;
- bottom 60%: no sampling;
- middle 35%: ratios from 1:2 to 1:9;
- all three background classes: 1:15;
- ratios were updated every five minutes;
- the resulting per-service sampling ratios are included in the dataset.

The DataZoo paper/search result verifies the standard size tiers:

| Tier | DataZoo sample/flow budget |
|---|---:|
| XS | 10,000,000 |
| S | 25,000,000 |
| M | 50,000,000 |
| L | 100,000,000 |
| Original | original dataset size |

The fetched DataZoo metadata reports 153,226,273 available QUIC22 samples.
The QUIC22 article itself describes the dataset as over 153 million flows.

The following exact values were not exposed by the fetched primary pages and
are **unverified**:

- compressed/on-disk byte size of each XS/S/M/L tier;
- uncompressed byte size of each XS/S/M/L tier;
- exact per-tier file count and archive layout;
- whether the published tier byte size includes metadata/statistics files.

Therefore, feasibility of an XS download on a machine with approximately 29 GB
free disk cannot be certified from this scan. The verified 10 million-flow
budget is not a substitute for the compressed and uncompressed byte sizes.

### 3. QUIC22 fields and recommended feature set

The QUIC22 article's Table 1 lists these fields:

```text
ID
SRC_IP
DST_IP
DST_ASN
SRC_PORT
DST_PORT
PROTOCOL
QUIC_VERSION
QUIC_SNI
QUIC_USER_AGENT
TIME_FIRST
TIME_LAST
DURATION
BYTES
BYTES_REV
PACKETS
PACKETS_REV
PPI
PPI_LEN
PPI_DURATION
PPI_ROUNDTRIPS
PHIST_SRC_SIZES
PHIST_DST_SIZES
PHIST_SRC_IPT
PHIST_DST_IPT
APP
CATEGORY
FLOW_ENDREASON_IDLE
FLOW_ENDREASON_ACTIVE
FLOW_ENDREASON_OTHER
```

The paper describes the core traffic representation as:

- first-30-packet sequences containing packet size, direction, and
  inter-packet time;
- sequence length, sequence duration, and roundtrip count;
- whole-flow duration, bytes, packets, and packet/inter-packet-time histograms;
- QUIC handshake metadata such as SNI, QUIC version, and user agent.

For a service classifier, the canonical non-label feature set is therefore the
PPI sequence plus the flow-statistic and histogram fields above. Excluding
`APP`, `CATEGORY`, and identifiers such as `ID` is an implementation
recommendation/inference, not a new dataset-author rule. IP/SNI fields should
also be excluded when the experiment is intended to measure content-based
encrypted-traffic recognition rather than endpoint memorization.

The article does not prescribe one universal train/test split. The associated
classifier study evaluates consecutive time periods, and DataZoo exposes
configuration for train/validation/test periods, application classes, and
known/unknown class assignment. The field-practice recommendation is therefore
a time-blocked, flow-disjoint split with explicit service/OOD controls, not an
unqualified random row split. The exact default DataZoo split used by a
particular loader configuration is **unverified** here.

### 4. Class counts and paired-design feasibility

Verified:

- 102 selected-service labels;
- 3 background labels;
- 105 total `APP` classes if backgrounds are retained;
- over 153 million original QUIC22 flows;
- metadata/search output reports 153,226,273 available QUIC22 samples.

Exact flow counts for every class, and the number of classes meeting any
particular paired-design threshold, are **unverified**. The article says that
per-service saved and pre-sampling counts are supplied in JSON statistics
files, but those files were not downloaded or parsed in this literature-only
scan. A paired-design count must therefore be computed from the chosen
threshold and the released per-class statistics rather than inferred from the
105-class total.

### 5. QUICEXT-25 attribute changes

The fetched QUICEXT-25 metadata identifies `DST_ASN` as the destination ASN
attribute and specifically lists `DST_COUNTRY` and `QUIC_CLIENT_VERSION`.
The comparison with QUIC22 is:

| Field | QUIC22 status | QUICEXT-25 status |
|---|---|---|
| `DST_ASN` | Already present in QUIC22 Table 1 as Destination Autonomous System number | Retained/available; not new |
| `DST_COUNTRY` | Not present in the QUIC22 Table 1 fetched here | New extended destination-country attribute |
| `QUIC_CLIENT_VERSION` | Not present; QUIC22 has `QUIC_VERSION` | New client-version-specific attribute |

The exact QUICEXT-25 schema, including whether `QUIC_VERSION` is retained
alongside `QUIC_CLIENT_VERSION`, is **unverified** without fetching the release
metadata/schema file.

### 6. Dataset caveats and limitations

Verified for QUIC22:

- capture is from a real CESNET2 backbone environment, not a controlled
  endpoint testbed;
- sampling is dynamic and service-dependent, so the released service
  distribution is softened relative to the observed network distribution;
- flows are filtered to destination port 443/UDP, a filled SNI field, and at
  least one packet in both directions;
- flow records use a 5-minute active timeout and a 65-second inactive timeout,
  so long connections can be split and idle connections can be clipped at
  export;
- only the first 30 packets are represented in PPI;
- client IP addresses are anonymized with Crypto-PAn, MAC-identifying fields
  are stripped, and the authors state that deanonymization is impossible;
- user-agent information is sparse: the article reports it in 0.2% of flows,
  approximately 342K samples.

The following items were requested as QUICEXT-25 caveats but remain
**unverified** from a fetched primary source in this scan:

- a uniform 1:100 sampling rule;
- the exact time-clipping/flow-timeout policy;
- exact missing-day dates or count;
- the exact QUICEXT-25 privacy transformation, including whether the released
  IP-derived fields use SHA hashing and the precise field-level mapping;
- whether any missing days are caused by collection outage, filtering, or
  release policy.

Do not transfer the QUIC22 dynamic-sampling rule to QUICEXT-25 without checking
the QUICEXT release metadata. Conversely, do not describe QUIC22 as uniformly
1:100 sampled: the QUIC22 article explicitly gives the dynamic ratios above.

### 7. CESNET loader/API

Verified package/API direction:

- package/project name: `cesnet-datazoo`;
- source repository: https://github.com/CESNET/cesnet-datazoo;
- PyPI project: https://pypi.org/project/cesnet-datazoo/;
- DataZoo provides a standardized API for CESNET-QUIC22 and related CESNET
  traffic datasets, with feature scaling and temporal/service-aware
  partitioning controls.

The PyPI page currently reports `cesnet-datazoo 0.2.0` (latest release date
2026-03-20 in the fetched listing). Use `cesnet-datazoo==0.2.0` as the
research-note reference version; still pin the exact version in an experiment
lockfile because PyPI is mutable.

## EIBO implementation implications

1. Use an independently trained classifier score and an independent held-out
   test set for the Michel HPLB. Treat `alpha` as the total type-I/HPLB error
   level; use `alpha/3` inside the adaptive witness and confidence-band
   construction.
2. For a directly implementable first version, use the public HPLB R code as
   the reference behavior: rank held-out scores, construct `V_m,z`, search an
   increasing `lambda` grid, and return the smallest candidate whose process
   stays below `Q`.
3. Use QUIC22 `APP` labels derived from SNI-to-service mapping. Keep
   `CATEGORY` as separate 17-group metadata; do not silently collapse the 102
   service labels into categories.
4. Treat QUIC22 XS/S/M/L as 10M/25M/50M/100M flow budgets, but do not claim
   disk feasibility for the XS tier until compressed and uncompressed byte
   sizes are obtained from the release metadata.
5. Use time-blocked, flow-disjoint evaluation with explicit known/unknown
   service controls. Record the exact DataZoo split configuration in the
   experiment metadata.
