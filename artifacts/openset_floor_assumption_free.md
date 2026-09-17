# An assumption-free open-set error floor from pairwise certificates

Prepared 2026-09-17. This **corrects a claim I made and retracted yesterday**, and it produces a
result the paper does not currently have.

## The correction

Yesterday I claimed that aggregating pairwise certificates into an open-set floor *"would require an
argument we do not give"* and, later, that it **cannot be done at all** from this object. I then
retracted the impossibility after an independent check found my verification script had a bug. The
retraction was correct but incomplete: I concluded that what remained was only a *conditional*
corollary needing a separation assumption the project lacks.

**That was also wrong, and in the paper's favour.** A positive, **assumption-free** open-set floor
follows directly, because of the sign of the discarded terms.

## Derivation

Let there be `M` classes with a uniform prior and a classifier `φ`; write `err_i = P(φ errs | Y=i)`.
For each **ordered** pair `(i,j)` construct the binary test

```
ψ_ij(X) = 1{ φ(X) = i }
```

Under `Y=i`, `ψ` errs exactly when `φ` errs, so `P(ψ errs | Y=i) = err_i`. Under `Y=j`, `ψ` errs iff
`φ(X)=i`, and `{φ=i} ⊆ {φ≠j}`, so `P(ψ errs | Y=j) ≤ err_j`. Le Cam's two-point lemma applied to
`(P_i, P_j)` then gives

```
err_i + err_j ≥ 1 − tv(P_i, P_j)                                   (1)
```

**for every ordered pair, at every M.** Summing (1) over ordered pairs:

```
Σ_{i≠j}(err_i + err_j) = 2(M−1) · Σ_i err_i = 2(M−1) M · E[err]
Σ_{i≠j}(1 − tv_ij)     = 2 Σ_{i<j}(1 − tv_ij) = 2S
```

hence

```
E[err] ≥ S / (M(M−1)),      S = Σ_{i<j} (1 − tv_ij)                 (2)
```

For `M=2` this reduces to `(1−tv)/2`, i.e. Le Cam. **Verified numerically** on `M=2` (exact match),
`M=4` identical laws, `M=4` disjoint one-hot supports, and the private-symbol construction whose
Bayes error I previously miscalculated — all hold.

## Why it extends to open-set with no new assumption

Take `M = K + 1`: the `K` known services plus the unknown class `U`. The sum `S` splits into

- `S_known` — pairs among the known classes, **certifiable from our artifacts**;
- `S_unknown` — pairs `(known i, U)`, which we cannot certify.

Every term is non-negative, so **discarding `S_unknown` only weakens the bound; it never invalidates
it.** Therefore

```
E[err] ≥ S_known / (M(M−1))                                        (3)
```

is a valid open-set floor **with no assumption on `U` at all**. This is the step I got wrong: a
covering/separation assumption is needed only to *recover the discarded mass* and tighten the bound —
not to state one. Discarding terms with a positive sign is always safe.

**Verified under stress:** 1500 randomised configurations, including the adversarial case where `U`
sits within a small ball of one known class, near-identical laws, disjoint supports, and `U` as a
point mass far from everything. **Zero violations.**

## The number, on the real corpus

Using the certified pairs at the coarsest channel (340 pairs at `eps_hi ≤ 0.5` over 43 services):

| setting | M | certified pairs used | floor |
|---|---|---|---|
| known-class only | 43 | 340 | **0.1232** |
| **open-set, + unknown** | 44 | 340 | **0.1176** |

So the corpus yields an open-set error floor of **≈ 0.118** — meaning any classifier that must place
a flow among the 43 known services or reject it as unknown errs on at least ~11.8% of flows, on
average, under a uniform prior. Adding the unknown class costs only 0.0056 of the floor.

For contrast, the incorrect constant I used yesterday (`1/(2K(K−1))`) would report 0.0616 — **half**
the correct value. The `M(M−1)` denominator is the right one.

## Honest limitations

1. **This is Le Cam applied carefully, not new mathematics in the sense the reviewers asked for.**
   Equation (1) is standard; the contribution is the observation that (3) needs no assumption, which
   contradicts what the paper (and I) previously asserted. That is a **claim correction with a
   number attached**, not a new mechanism.
2. **The uniform prior is required** for `E[err]` to equal the average of the per-class errors. Under
   a non-uniform prior the floor applies to the prior-weighted error, not to each class.
3. **The bound is loose by construction** — it discards all `S_unknown` terms, and it uses a
   `1/(M(M−1))` normalisation that averages over all pairs rather than concentrating on the hardest
   one. A tighter version would need the anchoring assumption.
4. **Rare-class behaviour is not captured**: the average error is dominated by easy classes; a
   classifier could be near-perfect on most services and still satisfy this floor.

## Consequence for the paper

The paper currently says (§3, and repeated in the abstract) that it makes *"no multi-class or
open-set reduction"* and that aggregating *"would require an argument we do not give."* **The second
half is false**: the argument is one line, and it is safe precisely because the discarded terms have
positive sign. The paper can therefore state a genuine open-set floor — on real data, ≈ 0.118 — while
keeping every existing claim intact.

Whether that is worth a round depends on whether the reviewers accept "an assumption-free open-set
floor, stated and measured" as the methodological addition. **It is closer to that than anything else
produced this session**, because it converts an explicit *absence* ("we make no open-set claim") into
a stated and measured result. But it is still a corollary of textbook machinery, and I would not
claim otherwise.
