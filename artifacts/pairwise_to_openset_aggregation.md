# Pairwise→open-set aggregation: what is true, and what is NOT

Corrected 2026-09-16 after an independent check found my earlier "impossibility" claim wrong.
The retracted version is archived at `_archive_retracted_pairwise_to_openset_impossibility.md`.

## The true result (standard Le Cam; cite, do not claim)

For a classifier `phi` over K classes with a uniform prior, let `err_i = P(phi errs | Y = i)`.
For every ordered pair `(i,j)`, with no restriction on K, define the binary test

```
psi_ij(X) = 1{ phi(X) = i }
```

Under `Y = i`, `psi_ij` errs exactly when `phi` errs, so `P(psi errs | Y=i) = err_i`.
Under `Y = j`, `{phi = i} ⊆ {phi ≠ j}`, so `P(psi errs | Y=j) = P(phi = i | Y=j) <= err_j`.
Le Cam's two-point lemma applied to this test gives

```
err_i + err_j >= 1 - tv(P_i, P_j)                                          (1)
```

**for all K.** Summing (1) over ordered pairs yields

```
E[err] >= (1/(2K(K-1))) * sum_{i≠j} (1 - tv_ij)                            (2)
```

which for K=2 reduces to the classical `(1-tv)/2`.

**Status: a direct generalisation of the Le Cam two-point method, i.e. textbook material.**
`references.bib` currently contains no Le Cam, Fano, Assouad or Tsybakov entry, so if this is used
it must be cited as a known result.

## The error I made, and how it was caught

1. I claimed (2) is false for K>2, based on "100 violations in 400 randomised cases". **The
   violations were an artifact of my test harness.** It scored accuracy as
   `argmax(P, axis=1) == arange(K)`, which assumes class `i`'s modal symbol is the `i`-th column —
   true only for index-aligned one-hot supports. The duplicated-support generator violated that
   assumption, so the harness measured a *mislabelled* classifier. With the correct uniform-prior
   Bayes error the same 400 cases give **0 violations**.
2. My "counterexample" (K=6 classes on 32 symbols, 0.9125 mass on a private symbol each) does not
   work. Recomputing by hand: every non-private symbol carries mass `(1-0.9125)/31 = 0.002823` for
   **five** classes, so `argmax` must misassign `5 × 0.002823 = 0.014113` per class. Per-class
   errors are `[0.014113, 0.0875 ×5]`, mean **0.075269**, against a floor of **0.045161** — the
   formula holds with slack 0.030. Separability would require `rest = 0`, i.e. `tv = 1` and a floor
   of 0, which is consistent rather than contradictory. **The two conditions I claimed to co-occur
   cannot.**

**Disposition:** constraint C044 (which forbade attempting this reduction) has been removed.
No paper change follows — see below.

## What IS available: a conditional open-set corollary

With an unknown class `U` in addition to the K known classes,

```
open-set error >= (1/2) * (1 - max_i tv(P_i, U))
```

equivalently the sum form `(1/K) sum_i (1/2)(1 - tv(P_i,U))`. Verified numerically in all three
variants (mean / max / min over i) on benign configurations and on the adversarial case where `U`
sits close to exactly one known class — it holds in every case tested.

**This requires a measurement the project does not yet have.** It needs the distance from `U` to the
known laws. The existing missing-mass estimate (X13) measures **mass**, not distance, so it cannot
substitute. That makes this a bounded real task, not a writing task — but it is also **not** the
methodological addition the reviewers asked for.

## Paper impact: none

The manuscript already states the per-pair scope correctly and consistently at
`measurement_design.tex:20-33` ("requires no further aggregation … nowhere claim a multi-class
reduction"), `abstract.tex:10`, and `introduction.tex:78`. The headline numbers (336/990, the cluster
CI, 340 upper / 336 joint) are untouched by any of this. **No edit is required, and the previously
planned edit is withdrawn.**
