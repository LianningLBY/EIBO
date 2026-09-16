# Feasibility: finite-sample replacement for the lower side's confidence constant

Prepared 2026-09-16. Question: can the lower side's **asymptotic** confidence constant be replaced by a
**finite-sample** one, and would that be a genuine methodological addition?

## What the implementation actually does

`src/eibo/statcore.py::_michel_beta(alpha, m)` implements, verbatim, Michel et al.
*Appendix B.1, Corollary 4*:

```
beta_{alpha,m} = sqrt(2 log log m)
                 + ( log log log m - log(pi) + 2*x_{alpha/3} ) / ( 2 sqrt(2 log log m) )
```

where `x` is the Gumbel quantile `-log(-log(1-alpha))`. **Verified:** our implementation reproduces this
expression to 1e-9 at m = 50, 100, 1000, 20000, 100000. So the paper's claim that the constant is "the
iterated-log expression of Appendix B.1, which is an asymptotic form" is accurate.

The source paper itself confirms the provenance: it labels the combination "(17)+(B.1)" as the
**asymptotic bounding function**, and explicitly warns that *"for smaller sample sizes, the (asymptotic)
QA could be a potentially bad approximation."* It offers an alternative: obtain the band by **simulating**
the standardised process instead.

## The domain guard is not a corner case — it fires at real operating points

The implementation substitutes a conservative constant `sqrt(2 log(6/alpha))` whenever the **effective**
count `m_tilde = m - q_m` falls at or below `exp(e) = 15.15`. Measured:

| m | lambda | m_tilde | regime |
|---|---|---|---|
| 32 | 0.1 | 24 | asymptotic |
| 32 | 0.5 | **9** | **FALLBACK** |
| 100 | 0.9 | **4** | **FALLBACK** |
| 100 | 0.5 | 38 | asymptotic |
| 1000 | 0.9 | 78 | asymptotic |
| 20000 | 0.9 | 1899 | asymptotic |

So at small alphabet and mid/high cutoff the asymptotic form is **undefined**, and the code deliberately
falls back to a conservative value rather than extrapolating. Because the band must hold **simultaneously
over all cutoffs**, these small-`m_tilde` cutoffs are on the boundary of the feasibility region — the
fallback is what keeps the method valid there. This is the paper's live weak point.

## How much does a finite-sample constant change the bound?

Simulated the standardised hypergeometric process and took the sup over the **full cutoff path** (the
correct object; a single-cutoff sup gives a falsely small constant):

| m | asymptotic beta | simulated path-sup quantile | ratio |
|---|---|---|---|
| 100 | 4.2783 | 3.5789 | 0.84 |
| 1000 | 4.2754 | 3.7919 | 0.89 |
| 10000 | 4.2948 | 3.6773 | 0.86 |
| 100000 | 4.3176 | 3.7337 | 0.86 |

**Reading:** an exact finite-sample quantile is roughly **0.86x** the asymptotic constant at these
sizes — i.e. mildly *tighter*, not looser. The magnitude is modest, and it is flat in `m` (the
iterated-log factor is nearly constant at these scales), which is consistent with the asymptotic form
being a Gumbel-type extreme-value constant.

### The fallback constant is already nearly right

The implementation's conservative fallback `sqrt(2 log(6/alpha)) = 3.6275` fires exactly where the
asymptotic form is undefined. Compared against a simulated finite-sample path-sup quantile at those
same small counts:

| m | n | fallback constant | finite-sample path-sup | ratio |
|---|---|---|---|---|
| 32 | 32 | 3.6275 | 3.2205 | 0.89 |
| 32 | 100 | 3.6275 | 3.5767 | 0.99 |
| 64 | 64 | 3.6275 | 3.3580 | 0.93 |
| 100 | 100 | 3.6275 | 3.3720 | 0.93 |
| 200 | 200 | 3.6275 | 3.5071 | 0.97 |

**So the fallback is only 3–11% conservative.** This materially weakens the case for the replacement:
the current code is not leaving much on the table at the operating point that motivated the change.
The gain from replacing it is real but small, and it enters as a multiplier on a correction term, not
on the bound itself.


## Verdict

**Feasible, but on its own it is "tighten a published constant", not a new method.** Three findings:

1. **The replacement is real and well-defined.** Replacing the B.1 expression with a simulated (or
   analytically bounded) finite-sample quantile gives a band that is valid at **all** `m_tilde`,
   removing both the asymptotic caveat and the `exp(e)` fallback. That is a genuine improvement in
   rigor.
2. **But the source paper already proposes exactly this** ("simulate S times from the process") and
   already warns the asymptotic form is bad at small sample sizes. So doing it is *adopting their
   stated alternative*, not contributing a new construction. A reviewer who knows the source can say so.
3. **The gain is modest** — about 0.86x on the constant, and the constant enters as a multiplier on a
   correction term, not on the bound itself.

**Therefore:** this closes the paper's *honesty* gap (removing "nominal" and the fallback) and is
worth doing for that reason, but it is **unlikely to move the novelty rating on its own**. Three
reasons, in order of force:

1. **The source paper already proposes the fix** ("simulate S times from the process") and already
   warns the asymptotic form degrades at small samples. Adopting it is following their stated
   alternative.
2. **The gain is small where it matters.** At the fallback operating point (small effective counts)
   the current constant is only 3–11% conservative; at large counts the asymptotic form is 14%
   conservative. Both enter as a multiplier on a correction term.
3. **It is a constant, not a construction.** Nothing about the estimator's form, assumption, or scope
   changes.

To count as the "methodological addition" the reviewers want, it would need the extra increment:
either a **closed-form finite-sample bound** (not a simulation) provably tighter than B.1 at small
effective counts, or a demonstration that the construction can be **adapted to the prefix channel**
in a way the source's does not cover.

## Recommendation

**Do the replacement, but not for novelty — for accuracy.** It is cheap (no experiments; the band is a
one-dimensional quantile), it removes a live caveat from the paper's weakest side, and it produces the
comparison tables above as citable evidence. Combined with the second point below it becomes defensible
as "we tightened and made rigorous the lower side, and here is the quantification."

**Do not expect it alone to convert 4/5 into clear accept.** Bundle it with the open-set reduction (the
other named gap) so the round carries a real methodological increment rather than two small tightenings.

