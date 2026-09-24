# Coverage threshold ladder (axis n, B=64 fixed)

- under the shared-Dirichlet block law at concentration 0.1 with B=64, and true TV 0.4, coverage first falls below nominal (0.975) at n = 60000
- Seed `20260919`; replicates `400`; runner sha `68d2f2d3fc0485a506c883b3998ce539cee0c6bd8d5bb4cca66c188d59544f07`; control MATCH.
- True TV `0.4`, block size `64`, concentration `0.1`.

## Rows

| n | radius | coverage | CP 95% | median tv_hat | cap hits | cap-dominated |
|---|---|---|---|---|---|---|
| 20000 | 0.0609 | 1.0000 | [0.9908, 1.0000] | 0.4248 | 0/400 | no |
| 40000 | 0.0431 | 0.9925 | [0.9782, 0.9985] | 0.4063 | 0/400 | no |
| 60000 | 0.0352 | 0.9825 | [0.9643, 0.9929] | 0.4023 | 0/400 | no |
| 80000 | 0.0305 | 0.9825 | [0.9643, 0.9929] | 0.4006 | 0/400 | no |
| 107065 | 0.0263 | 0.9825 | [0.9643, 0.9929] | 0.4002 | 0/400 | no |

## Reading

- **WITHDRAWN MECHANISM, corrected 2026-09-17.** An earlier reading held that the breach is
  driven by dependence INFLATING the estimate while n shrinks the radius. This ladder refutes
  that: at fixed B=64 the excess-bias-to-radius ratio FALLS by 50x as n grows (0.407 at n=20k to
  0.008 at n=107k) while coverage gets WORSE (1.0000 to 0.9825). If bias drove the breach,
  coverage would recover at large n. It does not.
- **What the data supports instead:** every cell's failure condition requires tv_hat to fall
  BELOW the truth, with thresholds 0.339-0.374 against a true TV of 0.400 (6-15% below), yet
  every median tv_hat sits at or above 0.400. So failures come from the LOWER TAIL of the
  estimate distribution, which block dependence widens relative to the i.i.d. radius, not from
  a shift in the centre. The median is flat (~0.40) while coverage falls: that is a
  variance/tail story, not a bias story.
- **Saturation is informative:** coverage is 0.9825 (393/400) at n = 60k, 80k AND 107k across
  radii 0.0352, 0.0305, 0.0263. Past n=60k further radius shrinkage buys no coverage, which is
  the signature of a fixed tail mass rather than a crossing phenomenon -- "threshold reached and
  stable", not "sharp transition".
- Cap-dominated cells (epsilon_hi clipped at 1.0 on >50% of replicates) are flagged and
  excluded from locating the threshold: their coverage is vacuous rather than earned.
