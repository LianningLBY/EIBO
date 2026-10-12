# CESNET real-data audit: screen-observed findings, 2026-10-12

This exploratory memo transcribes the report displayed in ToDesk. The source
JSON/CSV files remain on the school server; they have not been retrieved or
registered as paper evidence. No manuscript conclusions are updated.

Server report:

`/data/xjw/EIBO/artifacts/methodology/real_prepare_20261012_180750/report.md`

## Completed preparation

- Complete scan: 10,000,000 / 10,000,000 records across 360 daily tables.
- Plan status: `prepared`, with 44 APP codes selected only from pilot counts.
  This status requires all selected codes to have observations in certificate
  and evaluation; it does not establish independence or adequate counts per
  class in every smaller time slice.
- Hour-aligned flow-start fraction: 1.0.
- Fixed known-class prior: 1/45 each, plus unknown mass 1/45. This differs from
  the earlier 45-known-class experiment and is not an estimate of actual unknown
  prevalence. APP selection is numerical, not a semantic background filter.

| Period | UTC start | UTC end, exclusive |
|---|---|---|
| pilot | 2024-06-01 | 2024-11-30 |
| certificate | 2024-12-01 | 2025-03-01 |
| evaluation | 2025-03-02 | 2025-06-01 |

The 24-hour gaps and whole-flow interval guards provide temporal isolation for
individual flow records. They do not prove stationarity or independent periods,
and do not prove that a connection cannot have separate records in both periods.
The one-hour end envelope accounts for jointly shifted start/end timestamps.
Subhour chronology and Markov runs cannot be recovered from file order.

## CID sample

The reservoir contains 50,000 uniformly sampled usable flow records.

| Key | Empty/zero-like rows | Repeated keys | Repeated keys across APP | Across dates |
|---|---:|---:|---:|---:|
| ID | 0 | 0 | 0 | 0 |
| QUIC_OCCID | 36,415 | 3 | 2 | 3 |
| QUIC_OSCID | 0 | 0 | 0 | 0 |
| QUIC_SCID | 872 | 0 | 0 | 0 |
| QUIC_RETRY_SCID | 49,983 | 0 | 0 | 0 |
| OCCID_OSCID_pair | 36,415 | 0 | 0 | 0 |
| endpoint_OCCID_OSCID | 36,415 | 0 | 0 | 0 |

OCCID is non-informative in 72.83% of this sample. Its three repeated candidate
keys cross dates, and two cross APP codes; equality of this field alone is not
enough to identify a session. Retry SCID is non-informative in 99.966%. The pair
keys are informative for 13,585 sampled records but have no observed repeats.
OSCID and SCID likewise provide no sampled multi-record groups. Unique flow ID
is useful for record identity but supplies no multi-flow connection grouping.

Decision: use time periods for the next descriptive experiment; do not use these
CID keys as validated independent sampling units. No-repeat sampling is not a
global uniqueness proof: only a small fraction of the corpus was sampled, and
the released collection itself is flow-sampled. Full key auditing and protocol
semantics would be needed before connection-level leakage or independence claims.
The absence of source endpoint fields prevents reconstructing a complete tuple.

## Global time-block sensitivity

These are the preparation report's **start-assigned** block diagnostics, before
coarsening blocks joined by a flow's rounded interval.

| Block | Nonempty blocks | Squared-change budget | Conditional radius |
|---|---:|---:|---:|
| 1 hour | 2,029 | 0.000826555 | 0.0351862 |
| 6 hours | 339 | 0.00466557 | 0.0835967 |
| 24 hours | 86 | 0.0140678 | 0.145161 |

The radii amount to 3.52, 8.36 and 14.52 percentage points of known weighted
risk. Daily grouping is about 4.13 times wider than hourly grouping. This
demonstrates numerical sensitivity to geometry, not evidence that one width
achieves 95% coverage. Only 86 nonempty daily blocks remain in the certificate
period; additional merging or longer correlation could weaken information further.

The next script counts the same population and merges adjacent blocks touched
by any one usable flow, including unselected APP codes. It reports both budgets.
Such merging prevents within-flow splitting; distinct flows may still be
dependent across the remaining units. Conditional unbiasedness given the
data-dependent geometry is also unverified.

Because every stored start is hour-aligned, any positive-duration flow has a
one-hour envelope extending beyond its assigned hour. Adjacent blocks can therefore
merge across much of the capture period, even when actual flow durations are
short. This pessimistic scenario may yield zero floors. It reflects uncertainty
in the released timestamps, rather than proving that every flow is dependent.
Start-assigned grouping is retained as a separate conditional scenario, requiring
its own model that whole-flow dependence is contained by the start-time units.

## Next experiment and interpretation

`scripts/methodology_real_experiment.py` copies the completed plan, checks its
artifact manifest, rehashes the H5 source, reconciles every period/APP count,
and checks exact projection from canonical log M=2 to log M=1.

It reports empirical Bayes functionals, pilot-trained frequency classification
error in later periods, a certificate-trained recency comparison on evaluation,
unseen-symbol mass, per-class temporal empirical TV, empirical coarsening loss,
and conditional iid/time-unit floors. No classifier is fitted on evaluation.

Both representations use `statcore`'s log codec: log M=2 differs from the legacy
1200-byte split in `xs_compression_early_readout.py`. Results must not be presented
as an exact reproduction of that older count table. Observable coarsening loss
also does not certify loss relative to richer packet/timing features.

Population Bayes risk is unknown on this corpus. Real coverage therefore cannot
be evaluated by comparing a floor with known truth as in synthetic experiments.
Empirical shift includes sampling noise; it is not a valid shift penalty for
transporting a certificate to a future period. Every conditional floor remains
exploratory until its sampling assumptions are justified.

Primary schema references: [official release](https://zenodo.org/records/17249078),
[DataZoo feature definitions](https://cesnet.github.io/cesnet-datazoo/features/).
