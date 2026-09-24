# Capacity-axis limitation — the ladder was NOT run (D143)

## The capacity axis was NOT measured on this hardware within this session

This is a **stated limitation, not a result**, and it is **not** substituted by any capacity claim
derived from the architecture table. The three-detector table in `openset_delta.md` varies
*architecture*, not *capacity*; the two must not be conflated.

## Evidence: three attempts, all infrastructure failures

1. **LightGBM smoke (rounds=30, CPU)** — dispatch rejected twice by the content guard, then abandoned.
2. **RoNeTC/lightgbm ladder v1 (leaf-sweep design)** — died pre-execution; the Worker issued no
   `ssh_execute`.
3. **RoNeTC ladder v2 (GPU primary, `--ronetc-epochs` axis)** — died mid-wrapper-authoring at
   **09:44:34**; **no rungs run, and no ladder output was written on either host**. (This note is the
   only file matching `**/openset_capacity_ladder*`, and it is the *limitation note*, not a result:
   it was created after that check, so the check's "zero files" finding was true only at 09:44.)

All three failed with `stream disconnected before completion: stream closed before response.completed`.
Roughly two clean Worker executions were obtained this session against these three deaths, so the
execution channel — not the design — was the binding constraint.

## Two facts that must be kept apart

These are different statements and neither implies the other:

- **The capacity question is answered WEAKLY by the tier axis.** Per-service error spans 0.735 → 0.837
  (~14% relative); Δ moves 0.5424 → 0.6360; the ratio moves 3.79× → 4.27×. So Δ tracks classifier
  quality, in the right direction, but weakly.
- **The capacity question is NOT answered at all by a dedicated ladder.** No rung was ever measured.
  There is no measured Δ-vs-capacity curve, and none may be inferred from the architecture comparison
  above.

## Why the ladder was not re-attempted (the stronger reason)

Not merely transport yield. The ladder's purpose was to vary classifier quality and ask whether Δ
tracks it — and the three-detector tier axis **already answers that from bytes on disk**. A 14% range
the artifact already reports is not worth a fourth attempt on a channel that fails roughly half the
time. The capacity ladder was therefore **redundant on the merits**, which is the decisive ground; the
transport failures are a secondary, corroborating reason.

## Transport for any FUTURE remote need

One self-contained script, uploaded once, launched once with `nohup`/`setsid`, then the output file
read back — two or three remote calls instead of dozens. That is the shape a flaky stream can survive.
This transport was deliberately **not** spent on this experiment.

## Provenance note for any future capacity experiment

Train error cannot be read from the reviewed runner: `run_ronetc` computes `train_probabilities` only
to set the acceptance threshold (`quantile(train_score, 0.05)`) and on a truncated slice
(`train_scaled[:min(len, ronetc_calibration_rows)]`), and returns no train error. The minimal
auditable addition is a single second forward pass over the FULL training set reusing the model that
call already produced — a *measurement* addition, never a retraining, re-seeding, or
reimplementation. A rung whose `epochs=5` baseline does not reproduce 0.8302 is a reproduction
failure and the ladder is uninformative.

## Status

The open-set line is closed on the evidence side: Δ registered and independently reproduced; the
rejection arm cancelled on two independent grounds — (1) **thin U** (3,539 test flows, max 1,000,
and the gate verdict flips 8/8 → 1/8 purely with the floor chosen), which is sufficient on its own;
and (2) **svc 47 sits closer to known svc 37 than any known pair sits to another, and this ordering
is stable across train and test windows once the certificate's own eligibility rule is applied.**

On the certified channel (`pack_rung_prefix`, k=5, m=32, direction_row=1, size_row=2) **and the
ledger's eligibility rule `PPI_LEN >= 5`**:

| window | tv(47,37) | nearest known-known | ordering |
|---|---|---|---|
| train **calendar-year 2024 (incl. the 202412 buffer month)** | 0.1402 | 11-51 at 0.1658 | holds |
| test 2025-01..05 | **0.0146** | 27-29 at 0.0851 | holds |

**The train window above is the calendar year, not the declared modelling split** — state it that way
so it is not confused with D043's buffer-dropped split (2024-06..11, buffer 202412 excluded). Under the
declared split the pair reads tv(47,37) = 0.1497 vs 11-51 at 0.1741; under the calendar year,
0.1402 vs 0.1658. **The ordering holds under both**, so nothing below turns on the choice — but the
window must be named, which is the whole point of this correction. The buffer contribution checks out
exactly: filtered n37 = 10,111 (2024-06..11) + 1,855 (202412) = 11,966.

The margin is window-dependent (≈0.17× in test, ≈0.85× in train) but the **ordering is stable**,
which is what reason 2 needs. The filter is not discretionary: the ledger's `representation` block
states `eligible_rule: PPI_LEN >= 5`, and the filtered counts close exactly against its bookkeeping
(train 11,966 + test 19,250 = **31,216** = the recorded `eligible_n` for label 37). An unfiltered TV
measures a channel the certificate never defines — unfiltered values are 0.0414 (test) / 0.2011
(train), and **blended** values (0.0687, 0.1132) mix the classification regimes and should not be
quoted as a headline. Superseded: the earlier `0.0687` and its baseline `0.1394` (that number is a
distance-to-line cutoff, not a tv). **Any cross-service distance must carry its window, its channel,
and its eligibility rule.** The capacity axis is recorded as unmeasured; the floor choice is
documented in `openset_delta.json` (uniform is the certified floor, 3.79× headline, with 2.03× /
1.98× under the LP and exclude-U references).
