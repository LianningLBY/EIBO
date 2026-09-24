# Alphabet-Penalty Feasibility Scout

Checked: 2026-09-18 11:14 UTC. Theorem statements were checked in the cited papers' full text/HTML, not abstracts. No `.tex` file was opened or modified.

VERDICT: (c) — Jiao, Han & Weissman (2018), *Minimax Estimation of the L1 Distance*, Theorems 3–6: for arbitrary declared S-symbol distributions the minimax squared error is `S/(n log n)` in its stated large-alphabet regime, with a matching lower bound. This is a real log improvement over plug-in `S/n`, but it remains polynomial in the declared alphabet; no m-free or logarithmic-in-m finite-sample TV/L1 certificate was found. Therefore the short horizon is inherent to the assumption-free method class, up to logarithmic functional-estimation improvements. Do not claim that the exact `sqrt(m/n)` exponent is unimprovable.

STEP 1 OUR OWN CITATIONS: Han, Jiao & Weissman, “Minimax Estimation of Discrete Distributions under L1 Loss,” IEEE Transactions on Information Theory 61(11), 2015; Jiao, Han & Weissman, “Minimax Estimation of the L1 Distance,” IEEE Transactions on Information Theory, 2018; Chan, Diakonikolas, Valiant & Valiant, “Optimal Algorithms for Testing Closeness of Discrete Distributions,” SODA 2014; Diakonikolas, Gouleakis, Kane, Peebles & Price, “Optimal Testing of Discrete Distributions with High Probability,” arXiv:2009.06540, 2020; Wei & Dudley, “Dvoretzky–Kiefer–Wolfowitz Inequalities for the Two-Sample Case,” arXiv:1107.5356, 2011; Reeve, “A Short Proof of the Dvoretzky–Kiefer–Wolfowitz–Massart Inequality,” arXiv:2403.16651, 2024.

| key | theorem-level result | log or polynomial in m | usable under DECLARED alphabet? | theorem checked? |
|---|---|---|---|---|
| `wei2011dkwtwo` | Two-sample DKW bounds the Kolmogorov/empirical-CDF statistic with `exp(-2M^2)` tails. | no m | No for categorical TV; it is a CDF sup-norm result, not full discrete TV. | yes |
| `reeve2024dkwmassart` | Theorem 1 gives a finite-sample local one-sided empirical-CDF bound; Corollary 2 gives a dimension-free DKW-Massart tail. | no m | No for the project's categorical TV object without an additional ordered-CDF reduction. | yes |
| `han2015l1distribution` | Theorem 1 gives empirical L1 risk `<= sqrt((S-1)/n)`; Theorem 2 gives a nonasymptotic minimax lower bound of order `sqrt(S/n)` for arbitrary S-symbol laws. | polynomial (`sqrt(m)`) | Yes, with S=m as an a-priori model alphabet; this is expected-risk, not a direct high-probability certificate. | yes |
| `jiao2018l1distance` | Theorem 6 gives unknown-P,Q MSE `<= C S/(n log n)` when `log n <= C log S`; Theorems 3–4 give matching minimax lower/upper rates in the stated regime. | polynomial (`sqrt(m/(n log n))` RMSE) | Yes, with declared S; the estimator is support-size agnostic, but the theorem is risk/MSE rather than the project's direct confidence upper bound. | yes |
| `chan2013closeness` | Theorem 1: L1 closeness testing needs `Theta(max{m^(2/3)/eps^(4/3), m^(1/2)/eps^2})` samples at constant confidence. | polynomial | Yes for a declared domain, but testing is not a TV upper bound. | yes |
| `diakonikolas2020highprob` | Theorem 1.2: high-probability closeness testing has `Theta(m^(2/3) log^(1/3)(1/delta)/eps^(4/3) + (sqrt(m log(1/delta)) + log(1/delta))/eps^2)` samples. | polynomial | Yes for a declared domain, but testing is not estimation/certification of TV. | yes |

The bounded-entropy part of Han, Jiao & Weissman (IEEE TIT, 2015) is a genuine structural escape hatch: Theorem 3 gives a finite-sample expected L1 risk controlled by `H/log n`, and Theorem 4 gives a hard-thresholding estimator with the same entropy-controlled form. It requires an a-priori entropy class, not realized support, and is not already a high-probability upper certificate for this pipeline. No verified a-priori entropy/sparsity bound for the corpus was available here.

STEP 1 EXTERNAL: (i) exact: Jiao, Han & Weissman, IEEE TIT 2018, “Minimax Estimation of the L1 Distance,” is exact for finite-sample L1/TV functional estimation but retains polynomial declared-alphabet dependence; Han, Jiao & Weissman, IEEE TIT 2015, “Minimax Estimation of Discrete Distributions under L1 Loss,” is exact for finite-sample distribution estimation and supplies the `sqrt(S/n)` minimax lower bound. (ii) adjacent-only: Wei & Dudley 2011 and Reeve 2024 (ordered CDFs); Chan et al., SODA 2014 and Diakonikolas et al., arXiv 2020 (testing); Orlitsky, Suresh & Wu, PNAS 2016, “Optimal prediction of the number of unseen species”; Valiant & Valiant, STOC 2011, “Estimating the Unseen”; Paninski, Neural Computation 2003, “Estimation of Entropy and Mutual Information”; Nemenman, Shafee & Bialek, NeurIPS 2002, “Entropy and Inference, Revisited”; Cohen, Rosenfeld & Kolter, ICML 2019, “Certified Adversarial Robustness via Randomized Smoothing.” (iii) nothing found: a finite-sample, high-probability, exact-TV bound whose dependence is logarithmic in the declared alphabet and which requires no additional declared structure.

CANDIDATE TABLE:

| name | log-or-poly in m | declared-alphabet? | falsifying number / limitation |
|---|---|---|---|
| Han-Jiao-Weissman distribution estimator | polynomial `sqrt(m/n)` minimax lower rate | yes | Theorem 2 lower bound: arbitrary m-symbol laws retain `Omega(sqrt(m/n))` risk. |
| Jiao-Han-Weissman L1-distance estimator | polynomial `sqrt(m/(n log n))` RMSE | yes | Theorem 6 is MSE, with hidden constants and regime conditions; no direct `1-alpha` TV upper endpoint. |
| Known a-priori entropy class | no explicit m, risk `O(H/log n)` | yes, only if H is declared | H is an additional structural premise and is not established for this corpus; expectation/risk is not the current certificate. |
| DKW / local CDF | no m | no for exact categorical TV | Controls CDF sup norm, not the full subset supremum defining categorical TV. |
| Closeness testers | polynomial | yes | They decide `TV=0` versus `TV>=eps`; they do not return a finite-sample upper bracket for TV. |

M_max COMPARISON (only if a/b): no candidate

ADAPTIVE-PARTITION TENSION: yes — a partition selected from realized support/data is not an admissible replacement for the declared alphabet. Sample splitting can make a selected partition conditionally fixed, but it then certifies the coarsened partition TV; exact original TV requires an a-priori partition/model class or a complexity/approximation correction. No such correction with logarithmic dependence in the full declared alphabet was verified.

CLAMPED CELLS: none; no candidate radius was computed.

FULL VERSION WORTH BUILDING?: no — estimate 2–4 weeks for a separate proof-grade estimator, high-probability concentration argument, implementation, and independent calibration; the literature check does not justify that work for this paper.

MEMO: artifacts/alphabet_penalty_scout.md

BLOCKERS: none
