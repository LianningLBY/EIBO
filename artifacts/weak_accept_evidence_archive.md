# Weak-accept evidence archive — frozen 2026-09-17

Purpose: preserve the complete basis for the Round 6 verdict (weak accept, 4/5 unanimous) so the
decision to move on to new mathematical work rests on a recoverable record, not on memory.

## The verdict

- **Round 6, weak accept 4/5. Panel unanimous**: R1 4/5, R2 4/5, R3 4/5. R3 withdrew its earlier
  4.5 after cross-response, conceding that the §3.3 coverage calibration is an unfilled
  substantive item even within its reproducibility remit.
- Full reports: `artifacts/review_reports/round_{1,3,4,5,6}.md` (round 2 produced no report — a
  platform fault; the manuscript was unchanged between rounds 2 and 3 by construction).
- Trajectory: Round 1 **reject** (resubmit-worthy) → Rounds 2–5 repaired correctness, positioning,
  reference coverage, citation integrity, ethics → Round 6 **weak accept**.

## Why it is not a clear accept (the reviewers' own statement)

Round 6 names the clear-accept threshold as **two** things: *"one substantive methodological
addition plus the four-round-stale §3.3 coverage calibration."* And R2 states the distance
*"is not something editing can shorten; it needs an addition in the mathematics."* Novelty has been
rated **"incremental" for six consecutive rounds**, and Round 6 *"added no mathematics."*

**Both named directions were evaluated this session and neither supplies the addition:**

| direction | outcome | evidence |
|---|---|---|
| Coverage calibration | **executed** — 96/96 cells coverage 1.000, but the result is **vacuous under saturation**: the radius is a pure function of n (1.63x the true TV at n=2791), so small-n coverage is trivially guaranteed | `artifacts/coverage_calibration.json`, `finite_sample_band_gate_impact.md` |
| Finite-sample lower bound | achievable but a **tightening of a published constant** (~0.86x, and the fallback is only 3–11% conservative). No-op on every reported number | `artifacts/finite_sample_lower_bound_feasibility.md`, `finite_sample_band_gate_impact.md` |
| Pairwise→open-set reduction | the natural Le Cam generalisation is **valid for all K and is textbook material**; must be cited, not claimed. A conditional corollary exists but needs a measurement the project lacks | `artifacts/pairwise_to_openset_aggregation.md`, `conditional_corollary_missing_measurement.md` |

## What the paper claims, and what backs it (unchanged, all still valid)

- **C1** — two-sided bracket computable on real encrypted traffic: **336/990 = 33.9%** at k=5/M=1,
  upper side binds. Constant frozen at 2.9604; 95% **cluster**-bootstrap CI **[26.5%, 43.1%]**
  (the pair bootstrap understated width 2.84x). Cross-corpus replication supports
  **non-reproduction** (15.75%); the scale-matched strata do not survive (intervals include zero).
- **C2** — certificate horizon is short; the coarsest channel is the only viable rung. Includes the
  divisibility lower bound. **Ceiling:** the ladder saturates — the informative count is non-zero in
  only 4 of 20 cells and zero by M=8 at every k.
- **C3** — methods/limits: the standard plug-in chain-rule estimator cannot adjudicate the
  dependent-prefix growth question; robust to two independent repairs.
- Detector validation: nine cells below the null; **no gross violation of the floor is present**,
  with the closed-set-surrogate scope restriction stated on the face of it.

## Artifacts that constitute the evidence

- `artifacts/review_reports/round_6.md` — the verdict and its reasoning;
- `artifacts/review_issues.yaml` — cross-round tracker. **Note: 14 items still show open or
  partially_resolved, but most are stale** — the fixes were applied to `docs/paper/` and the tracker
  lags. Verified fixed in the tree: R6-W1 (abstract causality), R6-W3 (abstract power/convention
  caveats), R6-W4 (substitution direction), R6-W5 (not-falsified wording), R6-W6 (§2.3 grouping),
  R6-W7 ("significant unmatched"), R6-W8 (statistic naming). The genuinely open item is **R4-W7 /
  R5-W7** — the coverage calibration, now executed with its saturation caveat recorded.
- `artifacts/manifest.yaml` — 96 entries, **zero stale hashes**; every figure regenerates
  deterministically from manifest-resolved artifacts and all copies agree modulo PDF metadata.
- `artifacts/coverage_calibration.json`, `finite_sample_lower_bound_feasibility.md`,
  `finite_sample_band_gate_impact.md`, `pairwise_to_openset_aggregation.md`,
  `conditional_corollary_missing_measurement.md`, `operator_runbook_blocked_experiments.md`.

## Paper state at freeze

`docs/paper/`, entry point `main.tex`, **20 pages**, compiles clean, no undefined citations or
references. The two-point (Le Cam) consequence is now **cited** where the paper relies on it.
The single overfull hbox is pre-existing in `tab_boundary.tex` and non-blocking.

## What was deleted, and why it was safe

A stale duplicate `paper/` tree (21 tracked files, `references.bib` with 58 entries vs the live 60,
untouched by this session's corrections) was removed. Nothing referenced it: the `figures/paper/`
paths in the provenance notes point at a different directory. Its full history remains in git, so it
is recoverable if ever needed.
