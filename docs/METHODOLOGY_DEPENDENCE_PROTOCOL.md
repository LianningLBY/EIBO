# Conditional sampling-unit certificates: protocol v2

This is an exploratory mathematical and implementation protocol, not manuscript
content or a novelty claim. It extends the classical bounded-differences
baseline while explicitly separating valid model conditions from negative
controls. No raw-traffic independence assumption has been established.

## Fixed target

For fixed known-class priors and fixed categorical laws, define

`F(p) = sum_i pi_i - sum_x max_i pi_i p_i(x)`.

Its empirical version uses normalized per-class flow counts. Unknown-class error
is discarded. This target and all representation parameters remain fixed before
certificate sampling. A certificate for this observable is not a certificate for
a finer observable.

## Conditional independent units

Let G be exogenous sampling geometry: class sample counts n_i and the number
ell_ib of class-i observations affected by independent unit b. Conditional on G,
require:

1. The underlying random units are independent. Within-unit observations may be
   dependent, and one unit may affect several classes.
2. Each empirical class law is unbiased for the fixed p_i conditional on G.
3. Replacing a unit affects at most ell_ib observations of each class.

F is concave in the class laws, so `E[Fhat | G] <= F`. Changing one class-i
observation changes Fhat by at most pi_i/n_i. Thus a unit has change bound

`c_b = sum_i pi_i * ell_ib / n_i`.

McDiarmid's inequality gives the conditional lower certificate

`L_G = max(0, Fhat - sqrt(0.5 * log(1/alpha) * sum_b c_b^2))`.

Its conditional failure probability is at most alpha for every admissible G.
Integrating over G preserves the same unconditional budget. A random number of
units is permitted because the bound is conditional on the complete geometry.
No extra budget is consumed for observing exogenous geometry.

The implementation authority for this radius is
`eibo.riskcert.joint_radius_from_change_budget`. The caller must justify the
budget; the function cannot establish independence or unbiasedness from counts.

## Sticky iid-refresh chains

Each class starts with an independent draw from p_i. At every subsequent step it
retains the current symbol with probability rho, or redraws independently from
p_i with probability 1-rho. Its kernel is

`P_i = rho I + (1-rho) 1 p_i^T`.

Generate geometric regeneration lengths independently of the iid segment labels,
then truncate the final segment at n_i. Conditional on these lengths the
flow-weighted empirical law remains unbiased: segment weights sum to one.
For independent class chains, the oracle squared-change budget is

`S_G = sum_i pi_i^2 * sum_b (ell_ib / n_i)^2`.

Variable lengths must be preserved. Replacing this expression by the number of
segments, or using n/tau from a variance calculation, does not establish this
certificate. The simulator records latent lengths for an oracle comparison.

## Observable constant runs

Two adjacent regenerations can redraw the same symbol. An observed maximal
constant run therefore merges one or more true regeneration segments; it never
splits a true constant segment. All change bounds are nonnegative, so merging
units increases their sum of squares:

`sum_a (sum_{b in a} c_b)^2 >= sum_b c_b^2`.

For independent class chains, replacing latent lengths by observed run lengths
therefore yields `S_runs >= S_G` on every sample path. The resulting lower bound
is no larger than L_G on that path and inherits its coverage guarantee.

Observed runs depend on labels. They must NOT be declared independent conditional
on their observed boundaries. Validity follows from pathwise domination of the
latent conditional certificate, rather than that incorrect conditional argument.
The observable-run calculation does not require rho or hidden regeneration
boundaries, but its guarantee still requires the sticky iid-refresh structure.
It can be conservative when common symbols create long observed runs.

## Time-correlated shared shocks

The private/common-symbol case has common probability 0.4 and one private symbol
per class with probability 0.6. A shared Bernoulli shock determines the symbol
for every class at the same aligned position. In `cross_markov` the shock itself
follows a stationary sticky-refresh chain. All class observations share its
regeneration segments.

For each segment, sum affected class contributions BEFORE squaring. The budget
is `sum_b (sum_i pi_i * ell_ib/n_i)^2`. Unequal class sample sizes are handled by
clipping each global segment to the class observation window. A class window
ending within a segment must not split the independent global shock into two
independent units.

The observed shared shock runs coarsen the global latent segments and again
dominate their budget. The negative control `joint_separate_run_heuristic`
instead squares class contributions separately, omitting cross terms. It is
explicitly tagged as not satisfying the assumptions.

## Hidden blocks: model mismatch

In `hidden_blocks`, each class has independent fixed-size blocks. Each block
draws its common-symbol probability q from {0.1, 0.7}, with equal probabilities,
then draws conditionally independent Bernoulli observations within that block.
The unconditional common probability remains 0.4, preserving the same target F.

Symbols can change inside one dependent latent block. Observed constant runs can
therefore SPLIT that independent unit, and their squared-change budget need not
dominate the valid block budget. `joint_observed_runs` is a negative control here
for b>1. The oracle groups the full block, including its latent probability and
all within-block draws, as one independent unit. This is valid even though the
block is not constant.

A failed negative control illustrates the boundary of the sticky-refresh model;
it is not a counterexample to the certificate under its stated assumptions.

## Experiment and audit fields

The second-round command in METHODOLOGY_RUNBOOK.md runs 117 configurations and
489 method rows at the default grid, with 2,000 independent replications per
configuration. Alpha=0.05 is the per-method certificate budget. Exact binomial
intervals and a Bonferroni correction over every row control the familywise
Monte Carlo conclusion error at 0.05; no joint certificate is claimed by selecting
the maximum of multiple methods' floors.

Report coverage together with the mean floor, gap to truth, zero-floor fraction,
mean radius and radius quantiles. Valid coverage obtained by clipping every
lower bound to zero provides no information about the error floor.

The first replication's geometry and labels are recorded in progress.jsonl.
Markov and shared-shock generators preserve v1 count streams for the previously
used positive rho values and fixed seeds/batches. The optional rho=0 trace path
draws explicit iid labels rather than aggregate multinomial counts; protocol,
seed, batch size and library versions are recorded for reproducibility.

## Before connecting real traffic

Real-data work needs the raw file path and a field-level schema for service ID,
timestamp, session/connection ID, observable prefix and capture period. These
fields support grouping and auditing; their presence alone does not prove
independent groups or unbiased conditional laws.

- Define the target population and whether observations are weighted by flows
  or by sessions. Variable session lengths can change that target.
- Establish a justified unit model, including cross-service shared events and
  within-unit dependence. An ordinary session can contain changing symbols, so
  constant-run certificates cannot automatically be applied to sessions.
- If separated time blocks are justified through mixing or coupling, include
  the associated approximation error in the confidence budget. An estimated
  effective sample size is not a replacement for that argument.
- Keep representation selection and prior/cost selection on a separate pilot
  sample unless a valid simultaneous selection argument is supplied.

The present script implements the synthetic unit models only. It does not infer
the required structure from real traffic, estimate mixing coefficients, or claim
new paper evidence before review and registration.
