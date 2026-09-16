# Round 6 editorial change list (no experiment required)

Prepared 2026-09-16. Delivered to the user as exact location + current text + replacement, so
it can be applied locally without the worker dispatch path.

Source: `artifacts/review_issues.yaml`, Round 6 open items, each re-verified against the current
`docs/paper/*.tex` before writing. Several tracker entries were stale — already fixed in the
working tree — and are listed below as verified-closed so they are not re-applied.

## Verified already fixed (do NOT re-apply)

- **R6-W4** "Both substitutions run in the same direction" — no longer present. `results.tex:228,234`
  now reads "The resolution substitution runs in the direction of an easier test ... The closed-set /
  open-set substitution declared below runs the other way, narrowing the citable statement".
- **R6-W7** "significant unmatched" — no longer present in the paper; the wording is unified to
  "significant before matching" (`abstract.tex:23`, `discussion.tex:58`).
- **R6-W8** two names for one statistic — `results.tex:149` now consistently uses "median of the
  paired differences" and explicitly contrasts it with "difference of the two rungs' medians".

Note: these were flagged fixed by scanning the current `docs/paper` tree. The tracker entries still
show `open`; the tracker is stale relative to the working tree, not the reverse.

## Still open — 5 items

### 1. Abstract causality (R6-W1, warning) — highest priority
- **Location:** `abstract.tex:16`
- **Current:** `Raising the alphabet resolution resolves more structure and destroys the certificate at the same time`
- **Problem:** conflicts with `results.tex:171-172` — "A finer alphabet is associated with higher
  median divergence, but the confound named above leaves the causal claim open."
- **Replace with:** `Raising the alphabet resolution is associated with higher median divergence while destroying the certificate at the same time`

### 2. Abstract missing power + convention qualifiers (R6-W3, minor)
- **Location:** `abstract.tex:23` (the cross-corpus sentence)
- **Current:** `the gap is significant before matching but not statistically resolved at matched evidence`
- **Append:** `the compared figures use different per-service flow caps; the gap is significant before matching but not statistically resolved at matched evidence, and the test has limited power to detect a two- or three-point excess.`

### 3. Convention-matched cross-corpus contrast (R6-W2, warning)
- **Location:** `discussion.tex:26`
- **Current:** `The comparison pairs the primary corpus's full-$n$ $33.9\%$ against QUIC22's capped $15.75\%$`
- **Append after that sentence:** `Under a convention-matched contrast the primary corpus's capped figure is $33.8\%$ against QUIC22's $15.75\%$, so the direction and rough magnitude of the gap are unchanged by the convention.`
- **Why:** both corpora were measured under both conventions, so the matched contrast costs one
  sentence. The reviewer called disclose-without-translating defensible but not optimal.
- **Verify before applying:** confirm the 33.8% capped figure for the primary corpus is the value the
  artifacts actually carry; it is quoted from the review, not independently re-derived here.

### 4. "not falsified" vs "not a falsifiable test" (R6-W5, warning)
- **Location:** `results.tex:270`
- **Current:** `all nine cells are below the null, and the floor is not falsified`
- **Problem:** `results.tex:233` says the same validation "is a consistency check, not a falsifiable
  test" — one site says unfalsifiable, the other says not-falsified.
- **Replace with:** `all nine cells are below the null, so no gross violation of the floor is present`
- Keep "not falsified" only in the explanatory passage that unpacks it.

### 5. Background 2.3 grouping vs 6.2 (R6-W6, warning)
- **Location:** `background.tex:49`
- **Current:** `classical Kolmogorov-Smirnov style constructions supply exactly that \citep{wei2011dkwtwo,reeve2024dkwmassart}, while the minimax analysis under $\ell_1$ loss gives the tightest constants we know \citep{han2015l1distribution,jiao2018l1distance}`
- **Problem:** the surrounding sentence groups `[11] Diakonikolas` with `[19, 22]` under
  "Kolmogorov-Smirnov style refinements", while §6.2 correctly separates closeness testing
  `[5, 11]` from l1 minimax `[19, 22]`. The RT-W16 fix was applied at one site only.
- **Fix:** move [11] out of the KS group into a closeness-testing clause, matching §6.2:
  `classical Kolmogorov-Smirnov style constructions supply exactly that \citep{wei2011dkwtwo,reeve2024dkwmassart}, and the closeness-testing line \citep{chan2014closeness, diakonikolas2016closeness} addresses the sparse-support regime, while the minimax analysis under $\ell_1$ loss gives the tightest constants we know \citep{han2015l1distribution,jiao2018l1distance}`
- **Verify before applying:** cite keys must match the actual `.bib`; confirm [5] and [11]'s keys
  rather than copying the placeholders above.

## Residual

After these five, the only Round 6 item left is **R4-W7 / R5-W7** — the §3.3 coverage calibration
with a dependent-data arm. That one requires a real execution and is blocked by the absent
remote-execution capability, so it cannot be done in this pass.
