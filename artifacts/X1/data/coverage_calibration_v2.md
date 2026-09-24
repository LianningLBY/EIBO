# Coverage Calibration v2

- Verdict: **PARTIALLY SUPPORTED**.
- Upper-side nominal coverage: `0.975`; the upper side is a finite-sample finite-alphabet certificate only under iid sampling.
- Replicates per cell: `200`; coverage intervals are exact two-sided 95% Clopper-Pearson intervals with total alpha=0.05 and alpha/2 per tail.

## What the calibration shows

- Arm 1 has `17` informative cells (ratio > 1) and `3` trivially-guaranteed cells (ratio <= 1).
- Arm 2 has `51` informative cells and `9` trivially-guaranteed cells across the fixed block-size stress ladder.
- Informative means the reported nominal radius is smaller than the known true TV, so coverage is not guaranteed merely by radius size. Trivially-guaranteed means the radius alone already reaches or exceeds the true TV.

## Informative cells

Arm 1:
- TV=0.05, n=50953, ratio=1.309740, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=107065, ratio=1.898559, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=10988, ratio=1.216437, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=50953, ratio=2.619481, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=107065, ratio=3.797118, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=2791, ratio=1.226141, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=10988, ratio=2.432874, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=50953, ratio=5.238962, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=107065, ratio=7.594237, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=2791, ratio=1.839211, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=10988, ratio=3.649312, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=50953, ratio=7.858443, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=107065, ratio=11.391355, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=2791, ratio=2.452281, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=10988, ratio=4.865749, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=50953, ratio=10.477924, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=107065, ratio=15.188473, coverage=1.000, CP CI=[0.981725, 1.000000]
Arm 2:
- TV=0.05, n=50953, B=1, conc=0.1, ratio=1.309740, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=50953, B=8, conc=0.1, ratio=1.309740, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=50953, B=64, conc=0.1, ratio=1.309740, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=107065, B=1, conc=0.1, ratio=1.898559, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=107065, B=8, conc=0.1, ratio=1.898559, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.05, n=107065, B=64, conc=0.1, ratio=1.898559, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=10988, B=1, conc=0.1, ratio=1.216437, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=10988, B=8, conc=0.1, ratio=1.216437, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=10988, B=64, conc=0.1, ratio=1.216437, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=50953, B=1, conc=0.1, ratio=2.619481, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=50953, B=8, conc=0.1, ratio=2.619481, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=50953, B=64, conc=0.1, ratio=2.619481, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=107065, B=1, conc=0.1, ratio=3.797118, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=107065, B=8, conc=0.1, ratio=3.797118, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.10, n=107065, B=64, conc=0.1, ratio=3.797118, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=2791, B=1, conc=0.1, ratio=1.226141, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=2791, B=8, conc=0.1, ratio=1.226141, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=2791, B=64, conc=0.1, ratio=1.226141, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=10988, B=1, conc=0.1, ratio=2.432874, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=10988, B=8, conc=0.1, ratio=2.432874, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=10988, B=64, conc=0.1, ratio=2.432874, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=50953, B=1, conc=0.1, ratio=5.238962, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=50953, B=8, conc=0.1, ratio=5.238962, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=50953, B=64, conc=0.1, ratio=5.238962, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=107065, B=1, conc=0.1, ratio=7.594237, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=107065, B=8, conc=0.1, ratio=7.594237, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.20, n=107065, B=64, conc=0.1, ratio=7.594237, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=2791, B=1, conc=0.1, ratio=1.839211, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=2791, B=8, conc=0.1, ratio=1.839211, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=2791, B=64, conc=0.1, ratio=1.839211, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=10988, B=1, conc=0.1, ratio=3.649312, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=10988, B=8, conc=0.1, ratio=3.649312, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=10988, B=64, conc=0.1, ratio=3.649312, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=50953, B=1, conc=0.1, ratio=7.858443, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=50953, B=8, conc=0.1, ratio=7.858443, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=50953, B=64, conc=0.1, ratio=7.858443, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=107065, B=1, conc=0.1, ratio=11.391355, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=107065, B=8, conc=0.1, ratio=11.391355, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.30, n=107065, B=64, conc=0.1, ratio=11.391355, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=2791, B=1, conc=0.1, ratio=2.452281, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=2791, B=8, conc=0.1, ratio=2.452281, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=2791, B=64, conc=0.1, ratio=2.452281, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=10988, B=1, conc=0.1, ratio=4.865749, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=10988, B=8, conc=0.1, ratio=4.865749, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=10988, B=64, conc=0.1, ratio=4.865749, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=50953, B=1, conc=0.1, ratio=10.477924, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=50953, B=8, conc=0.1, ratio=10.477924, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=50953, B=64, conc=0.1, ratio=10.477924, coverage=0.995, CP CI=[0.972458, 0.999873]
- TV=0.40, n=107065, B=1, conc=0.1, ratio=15.188473, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=107065, B=8, conc=0.1, ratio=15.188473, coverage=1.000, CP CI=[0.981725, 1.000000]
- TV=0.40, n=107065, B=64, conc=0.1, ratio=15.188473, coverage=0.980, CP CI=[0.949586, 0.994524]

## Interpretation

- The informative Arm 1 cells are the evidence relevant to the iid finite-sample upper-side claim. The small-n cells are reported separately because their radius is already at least the known TV.
- Arm 2 is a dependence stress test, not a finite-sample theorem claim. Coverage degradation there would show sensitivity to dependence rather than invalidate the iid certificate.
- Final classification is **PARTIALLY SUPPORTED** because the informative Arm 1 cells are evaluated against the nominal coverage using their CP lower interval endpoints, while the dependence arm is reported as an empirical out-of-scope stress test.

## Cap

- Any cell hit the explicit `eps_hi <= 1` cap: **no**.

## Provenance

- Runner SHA-256: `050eef347c124a673711bc7951deb5c8e12ddf4eb73746a830f801bf57908233`; seed: `20260917`.
- Effective sample sizes came from `/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade/artifacts/_project/data/q1_lower_side_full_n.json` for services 49, 10, 50, 6; the HDF5 corpus was not read for this calibration.
- Deviations from the earlier calibration: replaced the fixed n ladder with verified per-service effective n values; expanded the TV sweep through 0.40; marked informative versus trivially-guaranteed cells; added explicit cap tracking; added the seed and CP alpha convention; and added the fixed dependence stress ladder.
