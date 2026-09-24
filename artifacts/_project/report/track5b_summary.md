# Track 5b: between-block diagnosis and conditional Arm D

## Step 1 diagnosis

- Design: n=60000, B=64, K=938, concentration=0.1, true TV=0.4.
- Diagnosis seed: `20260919`; outer replicates: `200`; within-block redraws: `32`.
- Mean between-block variance of c_k: `0.0264282997`.
- Mean conditional within-block variance of c_k: `7.74215125e-05`.
- Empirical SD of tv_hat: `0.0169715358`; i.i.d. reference SD/radius: `0.0351798518`.
- Arm B implied SD: `0.0169826453` (1.0007x empirical).
- Arm C implied SD: `0.016971999` (1.0000x empirical).
- Wrong-denominator prediction: factor `8.0`; observed empirical/mean(B,C implied SD) factor: `0.9997`.
- Verdict: B and C recover the directly measured tv_hat SD to within 10% (approximately 1.0x), so the diagnosis supports neither a wrong denominator nor an absent between-block term. The large block-level spread is not evidence that B/C omitted a variance component; Arm D must not be run.

## Step 2

Arm D was not run because the Step 1 diagnosis did not support it.
