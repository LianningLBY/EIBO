# The floor against measurement: it holds, and it recovers half the error

2026-09-17. This closes the gap the previous three notes all flagged as open — that the floor had
never been compared against a measured multi-class error. **The measurement already existed in the
project**; no new run was needed, only the recognition that the existing detector artifact contains it.

## Where the measurement was

`x12_detector_validation_k5.json` fits **multi-class** classifiers (`objective="multiclass"`; not
one-versus-rest), and records per-service `classification_error` under a stratified holdout. For each
service, the error rate is the fraction of that service's held-out flows the classifier misassigns
among all classes — which is exactly the per-class error our floor bounds, and whose **uniform
average is the macro-average multi-class error under a uniform prior**, the same prior the floor
assumes.

The earlier notes missed this because they looked for a purpose-built "open-set run" rather than
inspecting what the existing artifact already computes.

## The comparison, on matched objects

Same 45 services that define the 990-pair graph (all 45 present in the detector metrics — no service
is missing, so no subsetting is needed on either side):

| quantity | value | vs measured |
|---|---|---|
| **measured** multi-class error (LightGBM, macro over 45 services, uniform prior) | **0.7366** | — |
| uniform-weight floor | 0.1858 | 25.2% |
| **LP-optimal floor** | **0.3631** | **49.3%** |

**Both bounds hold** (`0.3631 <= 0.7366`), as validity requires. The LP weighting closes **32.2% of
the remaining slack** against the measured error.

## What this establishes, and what it does not

**Establishes:**
- The floor is a **valid** lower bound against a real, measured multi-class error on the same data,
  services, and prior — not merely against synthetic ground truth.
- It is **substantive rather than vacuous**: at 49.3% of the measured error it carries real
  quantitative content, and the LP weighting nearly doubles the fraction the uniform form captured.
- It is **not tight**: the measured error is about 2.8× the LP floor. The residual slack is the price
  of the assumption-free property, consistent with the diagnosis in `openset_floor_looseness.md` —
  equal weighting was one cause and the LP removed part of it, but the construction's inability to
  concentrate on the few confusable classes remains.

**Does not establish:**
- **Not a certificate on this classifier.** The floor bounds *any* classifier's error from below; the
  measured value is *one* classifier's error. The floor being below it is consistency, not validation
  of the classifier.
- **Not an open-set evaluation.** The models are closed-set multi-class over 53 labels; the unknown
  class is not exercised as a rejection target. The comparison is legitimate because the floor's
  unknown-class terms are discarded, so the bound applies to the known-class subproblem — but it does
  not test rejection behaviour.
- **Two detectors remain unmeasured**: `pcap_encoder` did not import, and `prototype`/`ronetc` give
  0.816 and 0.856, consistent with the LightGBM comparison but not part of it.

## Status

Exploration line. The paper remains frozen at the weak-accept version; this is the fourth companion
note and the first with an empirical counterpart.
