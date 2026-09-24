# Coverage Calibration v2b — near-binding and pipeline-control arm

- Verdict: **SUPPORTED**.
- Seed `20260918`, replicates per cell `400`, runner sha `f2ef594c82ee1713e15cf0692f4d5d92648442c26ad010883823ec498793c02c`.
- Control: MATCH (expected `0.16311342728653244`).

## Why this arm exists

The parent calibration (`coverage_calibration_v2.json`) tested only cells whose
true-TV/radius ratio was 1.2-1.9, i.e. the radius exceeded the entire deviation being
estimated. In that regime coverage ~1 is expected even under substantial dependence, so a
clean sweep is consistent with both 'the assumption is fine' and 'the violation is smaller
than this design can see'. This arm adds cells at ratio ~1.0 and a mis-specified pipeline
control, so the sweep becomes interpretable.

## Near-binding cells (iid)

- TV=0.40, n=500, ratio=1.038, coverage=1.000, CP=[0.9908, 1.0000], near_binding=True
- TV=0.40, n=400, ratio=0.928, coverage=1.000, CP=[0.9908, 1.0000], near_binding=True
- TV=0.30, n=300, ratio=0.603, coverage=1.000, CP=[0.9908, 1.0000], near_binding=True
- TV=0.20, n=150, ratio=0.284, coverage=1.000, CP=[0.9908, 1.0000], near_binding=True

## Near-binding cells (dependent)

- TV=0.40, n=500, B=1, ratio=1.038, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.40, n=500, B=8, ratio=1.038, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.40, n=500, B=64, ratio=1.038, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.40, n=400, B=1, ratio=0.928, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.40, n=400, B=8, ratio=0.928, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.40, n=400, B=64, ratio=0.928, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.30, n=300, B=1, ratio=0.603, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.30, n=300, B=8, ratio=0.603, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.30, n=300, B=64, ratio=0.603, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.20, n=150, B=1, ratio=0.284, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.20, n=150, B=8, ratio=0.284, coverage=1.000, CP=[0.9908, 1.0000]
- TV=0.20, n=150, B=64, ratio=0.284, coverage=1.000, CP=[0.9908, 1.0000]

## Mis-specified pipeline control

- **Not constructible.** ValueError: alphabet_size is smaller than the observed support.
- the harness REFUSES to produce a bound when the declared alphabet is smaller than the observed support, so this family of mis-specification cannot yield a wrong bound. The pipeline control the reviewer proposed is therefore not constructible; the guard itself is the evidence that this failure mode is excluded by construction.

## Interpretation

- The mis-specified control is **not constructible**: the guard raises a
  `ValueError` before any bound exists, so there is no mis-specified arm to
  run and no coverage number to compare. The guard is the evidence; it does
  not demonstrate that the harness can report a violation from this family.
- Near-binding iid cells: 4 at ratio <= 1.25; all cover at nominal.
- Dependency shown above is reported as an empirical stress test, not a theorem claim.

