# The floor against measurement: Δ, and why the open-set rejection arm was not run

2026-09-17. Supersedes the plan to run an open-set rejection evaluation; reports the quantity that
plan was for, computed from existing artifacts, and states plainly why the run itself was cancelled.

## The headline

**Δ = measured multiclass error − floor**, macro over the 45 graph services, cluster bootstrap over
the **45 services** (not the 990 pairs):

| detector | per-service error range | macro err | Δ vs floor (M=45) | ratio | 95% CI on Δ |
|---|---|---|---|---|---|
| lightgbm | 0.735–0.737 | **0.7366** | **0.5424** | **3.79×** | [0.454, 0.627] |
| prototype | 0.816–0.819 | 0.8190 | 0.6248 | 4.22× | [0.534, 0.708] |
| ronetc | 0.830–0.837 | 0.8302 | 0.6360 | 4.27× | [0.547, 0.715] |

Floor = 0.19422 at M=45, 0.18577 at M=46, from S_known = 384.5529 over the 990 certified pairs.
Per-row invariant `eps_lo <= eps_hi`: **0 violations**. Every detector satisfies
`floor <= CI_low` at every holdout — the bound holds, as it must.

**The bound is loose on this corpus, by ~4×.** Δ is ~0.54 and its 95% interval excludes zero by a
wide margin, so this is not a precision limitation: no classifier in the panel comes near the floor.

## What the tier axis shows

The informative comparison is across detectors whose per-service error spans 0.735→0.837, a ~14%
relative range. Δ moves 0.5424→0.6360 (**+17%**), and the ratio moves 3.79×→4.27× (**+13%**).

So Δ **does** track classifier quality, and in the right direction — a worse classifier sits further
above the floor. But it tracks it **weakly**: a 14% swing in error produces only a 13% swing in the
ratio, i.e. the floor's *distance* from achievable performance is roughly scale-invariant here. That
is the honest finding, and it is the opposite of what a tight bound would look like.

## Why the open-set rejection arm was NOT run

Two independent reasons, either sufficient:

**(1) U is too thin, and the gate verdict is a threshold artifact.** The unknown class can only be
drawn from the 8 labels absent from the 45-member graph (7, 12, 24, 30, 42, 45, 46, 47). Their **test
window** (2025-01..05, the only window an evaluation can draw on) flows: 1000, 828, 389, 326, 320,
258, 249, 169 — total 3,539, largest single service 1,000. On that window the "≥N flows → U
qualifies" gate gives 8/8 at N=100, 5/8 at N=300, 2/8 at N=500, **1/8 at N=1000**.
A go/no-go decided by an arbitrary threshold is not an experiment.

**Every gate number in this note is on the TEST window.** Counts on the **full corpus** (all 12
months, 10M flows) are larger — 8/8 at N=100, 8/8 at N=500, **3/8 at N=1000** (svc 7, 30, 47) — and
are context only. Both sets are correct and they contradict on their face if the window is omitted,
so it is named here and in the `gate_counts` block of `openset_delta.json`.

**(2) Δ cannot discriminate, independent of the gate.** Any M=46 equiprobable average blends the
known-service mean with U's error. With a **perfect** rejector (err_U = 0) the measured error is
0.7206; with a **never-rejecting** classifier, 0.7423. Across the entire range from perfect rejection
to none, the measured error moves ~2%, against a floor of 0.186. Every possible outcome sits ~4×
above the floor, so "floor holds" is fixed by construction and carries no information about the
rejector. This is the defect class flagged repeatedly in this project: a quantity that cannot take a
different value is not a measurement.

## What this does NOT show

- **Not an open-set evaluation.** The unknown class is never exercised; U is never a target. The
  floor's unknown-class terms are discarded (safely — every term is non-negative), so what is tested
  is the known-class subproblem.
- **Not a certificate on any classifier.** The floor bounds *any* classifier from below; the measured
  values are three specific classifiers' errors. The floor sitting below them is consistency, not
  validation.
- **`pcap_encoder` is excluded** — it exposes no per-service `classification_error` in the artifact.

## Status

The floor stays a **standard consequence of the two-point lemma, not a new construction**. It is
valid, substantive (it excludes error below 0.186 for any classifier), and **loose by ~4×** on this
corpus. The honest sentence for the paper is the Δ statement, not "the bound was respected."
