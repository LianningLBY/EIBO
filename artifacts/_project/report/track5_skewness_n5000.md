# Track 5 signed-deviation skewness

- Design: n=60000, B=64, concentration=0.1, TRUE_TV=0.4, outer replicates=5000.
- Seed: `20260919`; matches diagnosis-of-record seed `20260919`: yes.
- Stream: `inner redraws consumed`; reused the diagnosis-of-record loop structure with 32 inner redraw pairs per outer replicate.
- Stream control: sd(D) = `0.016078662416` vs the n=200 reference `0.0169715358`; control **PASSED** under the corrected band `[0.015275, 0.018669]`; not the wrong ~0.0151 stream.
- SD trajectory: `n=200: 0.0169715358`, `n=500: 0.0167711400`, `n=1000: 0.0162722914`, `n=2000: 0.0161860482`, `n=3000: 0.0159308502`, `n=5000: 0.0160786624`.
- The SD trajectory is non-monotone: it dips at n=3000 before rising, so no single window is a checkpoint at any n. A run validated only at n=3000 lands further from the final estimate than the n=200 start does.
- A properly scaled 2-SE band around the convergent `0.01608` contains both n=3000 (`[0.015665, 0.016495]`) and n=200 (`[0.014468, 0.017692]`); only the un-scaled hand-set band rejects them. The n=3000 window is not evidence of control failure.
- Mean(D): `0.002429536667`.
- Skewness(D): `-0.008893329301` using `g1 = m3 / m2**1.5` with 1/n central moments.
- Skewness trajectory: `n=200: -0.139556`, `n=500: -0.103819`, `n=1000: 0.055349`, `n=2000: 0.036285`, `n=3000: 0.025623`, `n=5000: -0.008893`; it crosses zero twice, so the sign is non-resolvable as a sequence rather than a single number.
- Analytic SE: `0.034630629906`; 95% CI: `[-0.076769363918, 0.058982705315]`; z = `-0.256805`.
- CI contains zero: `True`.
- Bootstrap percentile 95% CI (20000 resamples): `[-0.071635614218, 0.053988687344]`.

## Pre-committed falsifier

- Proposition tested: **"the signed deviation D = tv_hat - TRUE_TV is negatively skewed."**
- Falsifier fired: `True`. The falsifier fires if the n=5000 analytic 95% CI contains zero.

Boundary: this conclusion is about the modelled block law at this design, never about real traffic.

content_sha256: bc4ddebbbbe44ace06fc7fa2abbb1acf4139a9f6fa01395b4a809843c87f80d5
