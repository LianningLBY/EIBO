# Conditional open-set corollary: the missing measurement, checked

Prepared 2026-09-16. The verified conditional corollary is

```
open-set error >= (1/2) * (1 - max_i tv(P_i, U))
```

where `U` is the unknown class and `P_i` the known service laws. It needs a bound on
`max_i tv(P_i, U)` — the distance from the unknown class to the *whole* known set.

**Checked whether the project already has this. It does not, and the gap is not a wording problem.**

## What X13 actually measures

`artifacts/X13/data/x13_missing_service_mass.json` measures, verbatim in its own fields:

- `identifier_field: DST_IP`, `identifier_granularity: flow-level frequency-of-frequencies over
  anonymized destination-host identifiers`
- `estimator: good_turing`, `missing_mass_estimate: 0.002023566874936503`,
  `n_unique_identifiers: 22108`, `n_total_flows: 5039616`
- `scope: deployment-site missing service mass, NOT a universal unknown prior`

So X13 answers **"how much of the deployment's flow mass belongs to services absent from the known
set?"** It is a scalar **mass** estimate over destination-host identifiers.

It does **not** answer **"how far is the unknown class's prefix law from the known laws?"** — the
quantity the corollary needs. There is no distance, no `tv(P_i, U)`, and no per-service law for the
unknown class anywhere in the artifact. The identifier used is a different object from the declared
(方向, size) prefix channel the certificate is defined on, and the artifact explicitly records that
`identifier_enters_declared_channel: False`.

**Conclusion: the required measurement is genuinely absent.** It would need a new pass over the
corpus that (a) forms the unknown-class prefix law on the declared channel and (b) computes its tv
distance to each of the known service laws. That is a real experiment, not an aggregation of
existing artifacts.

## Why it is not worth running now

Even if it were run, the result would be a **conditional** statement — "if the unknown class is at
distance ≥ δ from every known service, then the open-set error is at least (1-δ)/2" — and that
condition is exactly what the corpus is unlikely to satisfy, since the deployment's missing mass is
dominated by rare services that are typically *close* to known ones (that is why they were hard to
separate in the first place). A measurement that returns δ ≈ 0 would yield a corollary that is true
and empty.

So the honest position is:

- the corollary is **correct** and verified;
- its input is **measurable in principle** but **absent**, and requires a new corpus pass;
- running that pass would most likely produce a vacuous δ, and would not constitute the
  methodological addition the reviewers named.

**Disposition: do not run it.** The corollary can be stated in the paper as a conditional
observation with the assumption named on its face, without claiming the measurement — or omitted
entirely. Either is defensible; spending a corpus pass on it is not.
