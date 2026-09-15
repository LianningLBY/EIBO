# EIBO — project memory

> SPEC SOURCE OF TRUTH. **✅ THE PRE-REGISTRATION DOCUMENT IS THIS FILE.** **`ROADMAP.md` is NOT writable.**

## ⚠️ READER'S NOTE ON THIS FILE — SECTIONS HAVE BEEN LOST IN REWRITES
**I cannot do targeted edits; this file is rewritten in full every time. A rewrite has thrice silently dropped
sections (both PRE-REGISTRATION blocks, the `denominator_symbol_law` note, and the `TWO TREES` section).**
**⇒ After every rewrite, `grep` the headers** `FINITE-SAMPLE STRICTNESS`, `Q1 GATE`, `CALIBRE CLAIM`,
`RADIUS 2X DEFECT`, `SUM-TO-ZERO 2X DEFECT`, `Q1 vs Q2`, `M041`, `SPEC-LEVEL ERROR PROPAGATION`,
`C016 vs CONVENTION DRIFT`, `EMPTY-CRITERION DEFECT`, `EPISTEMIC ASYMMETRY`, `THRESHOLD DECISION`,
`TWO-OBJECT DEFECT`, `OBJECT ASSERTION RULE`, `CROSS-FIELD CONSISTENCY`, `FIELD NAMING DEFECT`,
`DISPATCH HYGIENE`, `STEP-0 STATUS`, `TWO TREES`, `ARTIFACT PATH`, `DISK`, `MONTHLY FLOW COUNTS`,
`MONTH-LEVEL SPLIT`, `denominator_symbol_law`, `SATURATION`, `MASKING SCOPE`, `E3 RESULT`, `Q1 eps_lo`,
`Q2 v3`, `BINDING-SIDE`, `REGISTRY` **and confirm all are present.**

## 🔴🔴 FINITE-SAMPLE STRICTNESS — **THE LOWER SIDE IS ASYMPTOTIC AND MUST BE PAIRED WITH `eps_hi < 0.5`** (D037)
> **"finite-sample strictness on the lower side is NOT required in this paper: that side is the asymptotic
> HPLB. The finite-sample strict side is the UPPER side (per-law `eps` uses k=1 separately). The artifact's
> `eps_hi < 0.5` remains the only finite-sample strictness gate; the asymptotic lower side stays reported as
> an HPLB alongside it, and is never required to reach a strict standard."**
**This is D030's EPISTEMIC ASYMMETRY promoted to a DECISION.** **⛔ It does not license "PROVEN" anywhere.**
**⚠️ Do NOT resolve the alpha question by tightening the lower side.** **Still OPEN**: whether `T(n)`'s `0.05`
constant depends on α. **⛔ AND THE LOWER SIDE STILL MAY NOT BE CLAIMED AS FINITE-SAMPLE STRICT.**

## 🔴🔴🔴 Q1 GATE — **`336/990` = 0.3394 — FULLY MEASURED** (E10)
**The gate is `(eps_lo > 0.05) AND (eps_hi < 0.5)`, both sides on ONE object.**
- **Upper side `eps_hi < 0.5` = 340/990 = 0.3434 on the REFERENCE radius** (per-rung 340 / 47 / 3 / 0 / 0;
  the 2× convention gave 292 / 27 / 0 / 0 / 0). It was recomputed row-by-row through the repository function;
  it matches the recorded 340 with **0 internal mismatches**.
- **Lower side `eps_lo > 0.05` at FULL n with the 20,000-flow cap removed = 986/990.** The completed
  `q1_lower_side_full_n.json` run recomputed the lower side for **all 990 pairs**:
  `measured_full_n_pair_count = 990`, `assumed_pair_count = 0`. Under the cap it was 985/990; the five pairs at
  or below the line under the cap were `11-51`, `39-44`, `27-29`, `35-49`, `21-23`.
> **⇒ THE JOINT GATE = 336/990 = 0.3393939394.** **`k_recovered = 1` — and "recovered pairs = 1", NEVER bare
> `k = 1`, because `k` already means PREFIX LENGTH = 5 in this project.**
**✅ INDEPENDENT CROSS-CHECK: computing the gate from E3's counts table gives `340 − 4 = 336`, matching the full-n
run's `gate = 336` exactly** — two different paths agree.
**The earlier range `[333, 336]` is SUPERSEDED:** it was an input range valid only while the lower side was
half-measured; with `assumed_pair_count = 0`, it has no basis.
**The gate is 336 because exactly ONE boundary pair (21-23) crosses 0.05, and its capped value sat 0.0002 from the threshold**
(capped `eps_lo` 0.049781366 vs full-n 0.058780592). Had it not crossed, the gate would be 335. **Report it as
336 WITH that sensitivity stated, not as a stable integer.** Two companion readings travel with it: **(i)** pair
(35,49) moved the WRONG direction as n grew (0.043732229 -> 0.042724656) — so "larger n gives a tighter lower
bound" is a statistical TENDENCY, not a guarantee; **(ii)** pair (39,44) is bit-identical across runs because
its full n (4624/5741) is BELOW the 20000 cap, so it was never capped — "no change" there means **"never bound"**,
NOT "stable".
**✅ Full-n consistency: `eps_lo > eps_hi` violations = 0; verdicts changed vs capped = 1 (pair 21-23:
0.049781366 -> 0.058780592); within 0.005 of the 0.05 line = 0 pairs; within 0.02 = 3 pairs.**
**Artifact:** `q1_lower_side_full_n.json`, sha256 `bbf5aa4e2cbf84be2c4544fa393c7518588940888e0d712114f4cc570d386467`,
990 rows.
**Q1 PASSES ON A MINORITY STRATUM (~34%), NOT CORPUS-WIDE.**

### E10's five pairs at FULL n (artifact `q1_gate_five_pairs_full_n.json`, 21,840 B, `91b3f512…`)
| pair | full n_a | full n_b | full `eps_lo` | `>0.05` | `eps_hi_ref` | `<0.5` |
|---|---:|---:|---:|:---:|---:|:---:|
| **11-51** | 13,049 | 1,399,495 | **0.0226071321** | **False** | 0.0857127379 | True |
| **39-44** | 4,624 | 5,741 | **0.0150712160** | **False** | 0.1964514557 | True |
| **27-29** | 137,553 | 11,462 | **0.0287054878** | **False** | 0.0995006316 | True |
| **35-49** | 159,842 | 2,791 | **0.0427246558** | **False** | 0.2164858582 | True |
| **21-23** | 187,588 | 15,238 | **0.0587805922** | **✅ True** | 0.1395166160 | True |

### ⚠️ THE POINT PREDICTION WAS WRONG; THE BRACKET WAS RIGHT
**The prediction was `340` (all five recover). The PRE-REGISTERED BRACKET was `[335, 340]`. MEASURED: `336` —
INSIDE the bracket.** **⇒ Learning: a directional argument bounds a QUANTITY; it does not predict a THRESHOLD
CROSSING when the margin is comparable to the estimator's noise. State the bracket; do not attach a point
prediction to it.**
- **`21-23` recovered** (0.049781 → 0.058781) — the predicted direction;
- **`11-51`** (0.012230 → 0.022607) and **`27-29`** (0.026651 → 0.028705) **rose but stayed under 0.05**;
- **`39-44` did not move at all** (0.0150712160 → 0.0150712160) — **its full n is 4,624 / 5,741, i.e. ALREADY
  BELOW the 20k cap, so the cap never bound it and there was nothing to recover**;
- **⚠️ `35-49` DECREASED** (0.043732 → **0.042725**) — **the opposite of the prediction** — **despite n going
  20,000 → 159,842.**
**⚠️ RETRACTED MECHANISM CLAIM (M050).** This slot previously read: *"`11-51` HAS IDENTICAL n ON BOTH SIDES
(13,049) yet its `eps_lo` moved +0.0104 ⇒ the movement is SEED NOISE, not an n effect."* **BOTH HALVES ARE
WRONG.**
- **`11-51` did NOT have identical n.** Only `n_a` was unchanged (13,049); **`n_b` went 20,000 → 1,399,495
  (70x)**, confirmed by the held-out split sizes `{3915, 6000}` → `{3915, 419849}`. **An n effect is therefore
  NOT excluded — and +0.0104 is the EXPECTED direction for far more data.**
- **There is no "seed noise" to appeal to.** `39-44` had **BOTH** `n_a` and `n_b` unchanged and its `eps_lo` is
  **identical to the digit** (Δ = 0.000000000) ⇒ **for fixed input the estimator is DETERMINISTIC**
  (`random_state=0`). **The other pairs moved because their INPUT changed, not because of randomness.**
**⇒ THE CORRECT READING:** `11-51` (+0.0104, `n_b` 70x) · `21-23` (+0.0090, `n_a` 9.4x) · `27-29` (+0.0021,
`n_a` 6.9x) all **rose with more data**, consistent with tightening; **`35-49` (−0.0010) FELL despite `n_a`
growing 8x (20,000 → 159,842) — that is the GENUINE non-monotonicity evidence and it carries the lesson
alone.**
**⇒ `eps_lo` is the Michel adaptive construction** (`method: michel_adaptive_sup_cutoff`) with an internal
split and a data-chosen cutoff, so **"larger n ⇒ `eps_lo` non-decreasing" is a tendency, not a guarantee.**
**Mechanism still withheld: no control varying only n has been run.**
**⇒ LESSON (M050): a claim that conditions are IDENTICAL must be checked PER SIDE (`n_a` AND `n_b`), and a
"noise" explanation requires first confirming the estimator is NOT deterministic — here a single pair with
both inputs unchanged settled it.**
**⚠️ THE FIVE PAIRS ARE A SELECTED SET — see BINDING-SIDE.**
**✅ THE STRONG SENTENCE, NOW MEASURED**: **"On the coarsest channel at k=5, 33.9% (336/990) of service pairs
admit a two-sided interval whose upper side is finite-sample strict (`eps_hi < 0.5`) and whose lower side is an
asymptotic lower bound exceeding 0.05."** **It describes THE ASYMMETRY, not a proof.**
**⛔ "PROVEN" REMAINS UNAVAILABLE.**
**✅ C016 ON THE CORRECTED RADIUS: 0/990 violations** — the completed full-n run recomputed both sides on
all 990 rows, with the upper condition evaluated row-by-row through the repository function. **The measured
`eps_lo > eps_hi` violation count is 0, with no assumed remainder.**

## 🔴🔴 BINDING-SIDE (M040) — **DO NOT READ A BINDING SIDE OFF THE FIVE-PAIR TABLE**
**Corpus-wide, over all 990 pairs: the UPPER side removes 650, the lower side removes 4 within the upper set.**
**⇒ The UPPER side binds — and it is also the finite-sample-strict side, so the binding constraint carries the
stronger guarantee.**
> **⚠️ The five-pair table CONDITIONED ON THE LOWER SIDE BY CONSTRUCTION** — those pairs were *selected* as the
> lowest capped-`eps_lo` pairs, i.e. **chosen for their value on the lower constraint**. **Reading "lower binds
> 4/5" there is SELECTION ON THE DEPENDENT VARIABLE and carries NO corpus information.**
> **⇒ RULE: to decide which constraint binds, compare how many pairs each removes CORPUS-WIDE — never on a
> subset chosen for its value on that same constraint.**

## 🔴🔴🔴 CALIBRE CLAIM — **I ASSERTED A MIXED-N CAVEAT THAT WAS FALSE (M040)**
**I claimed the `Q2/Q1 = 1.006` ratio "mixes full-n (Q1) with capped-n (Q2)" and was therefore unquotable. THE
DIRECTOR VERIFIED THE ARTIFACT AND REFUTED IT.** Row evidence:
```
radius_coordinate_a observed  = 0.0014239612024662647
  back-inferred from n_a       = 1,927,343  ->  0.0014239612024662647   (exact, 16 digits)
  back-inferred from lower_n_a =    20,000  ->  0.0139785673793481      (9.8x too large)
```
**And across all 990 rows, the upper radius matches the FULL n on 990/990.**
> **⇒ The 20k cap applies ONLY to the LOWER side (`eps_lo`); the UPPER side (`eps_hi`) uses FULL n.**
> **⇒ `342/990` IS a full-n number, same calibre as Q1's `340/990`.**
**⚠️ HOW I WENT WRONG, IN TWO STEPS**: I read `"n_a": 20000` in **`q1_eps_lo_symbol_map.json`** (where it IS
capped), and **generalised it to Q2 v3** — but **Q2 v3's rows carry `lower_n_a: 20000` ALONGSIDE full `n_a`,
and `radius_coordinate_a` reproduces from the FULL n.** **⇒ The product was self-documenting which side used
which; I did not read it.**
> **⇒ RULE: A ROW CARRYING BOTH A SAMPLE-COUNT COLUMN AND A DERIVED-QUANTITY COLUMN IS THE PRODUCT SELF-REPORTING
> WHICH SIDE USES WHICH. TO ASSERT "THE CALIBRES ARE MIXED", BACK-INFER THE DERIVED QUANTITY FROM EACH CANDIDATE
> COLUMN AND SEE WHICH ONE REPRODUCES.**
> **⇒ AND A CAVEAT IS ITSELF AN ASSERTION — it needs the same verification as a result. Over-conservatism is
> NOT the safe direction: it suppresses a correct conclusion, and that costs more.**
**⚠️ THIS IS MY SECOND UNVERIFIED ASSERTION OF THE SESSION** (the first: "the gate's intersection with the 5
lower-side failures is uncomputable" — it was 5/5, not unknown).

## 🔴🔴🔴 THE SUM-TO-ZERO 2X DEFECT — Q2's UPPER SIDE (D036) — **NOW INDEPENDENTLY REPRODUCED**
**The Q2 v3 run used `eps_hi = tv_hat + 31*r_a + 31*r_b`. THE COEFFICIENT 31 IS EXACTLY 2× TOO LARGE; the
correct coefficient is 16.**
**Derivation (no new assumptions)**: `delta = P_hat - P` on the simplex ⇒ `sum_c delta_c = 0` ⇒ the POSITIVE and
NEGATIVE parts have EQUAL total. With k positive coordinates the positive total is at most `min(k, 32-k)*r`,
and `max_k min(k,32-k) = 16` ⇒ positive total `<= 16r` ⇒ `L1 <= 32r` ⇒ **`TV <= 16r`.**
**The old 31 summed 31 per-coordinate bounds WITHOUT using `sum(delta)=0`, over-counting the positive part.**
**✅ EXHAUSTIVE CHECK (a run, not a hand argument)**: `max L1/r == m` for **m = 2, 4, 8, 16, 32 — all true**.
(It reported that a literal enumeration at m=32 has 601,080,390 balanced patterns and timed out, so it used the
`k`-positive-coordinate enumeration from the derivation, **stating the substitution openly** — acceptable.)
### RESULT (artifact `q2_upper_bound_16r.json`, 3,283 B, `3c16c6be…`)
| bound | informative |
|---|---|
| **31r (old, loose)** | **152/990 = 0.1535** |
| **16r (sharp, valid)** | **342/990 = 0.3455** |
**`eps_hi_16r` quantiles**: min `0.1269831004` · q5 `0.2652327069` · q25 `0.4351024714` ·
**median `0.5912627795`** · q75 `0.7682581658` · q95 `1.0124897150` · max `1.4619927351`.
> **⇒ The `342` is NOW EMITTED BY A RUN, not merely recomputed by hand. The earlier "pending confirmation by a
> run" reservation is DISCHARGED.**
**⛔ A STILL TIGHTER FORM IS OUT OF SCOPE AND MUST NOT BE USED**: the **Weissman categorical form
`0.5*(sqrt(m)+c)/sqrt(n)` gives ~935/990 = 0.9444 and is NOT adopted.** **Reason**: it bounds **IID one-hot
categorical observations**, whereas **the Q2 estimator is the mean of CORRELATED SIMPLEX VECTORS**;
`Var(f_i(c)) <= P(c)(1-P(c))` **does hold**, **but per-coordinate variance bounds do NOT establish an L1
concentration inequality for correlated coordinates.** **It must be PROVED for this estimator before it may be
quoted, and proving it is a SEPARATE piece of work, explicitly out of scope.**
**⇒ FEASIBLE RANGE: `[152, 342]/990`. `342` is the PROVEN sharp bound. `935` is UNPROVEN.**
**⚠️ DISCRIMINATOR EXTENSION**: for a `k·r` form, **first check whether a CONSTRAINT halves k.**
`31 = 2×16 − 1`, and the missing 1 comes from counting one coordinate too many after dropping `sum=0`.

## 🔴🔴🔴 Q1 vs Q2 — **LEVEL IN NUMBER, BUT THE AGREEMENT IS A CANCELLATION, NOT A CROSS-CHECK (M041)**
| | informativeness | calibre |
|---|---|---|
| **Q1** (k-prefix symbol law) | **340/990 = 0.3434** | upper at full n, constant `4.309/√n` |
| **Q2** (PHIST lattice law) | **342/990 = 0.3455** | upper at full n (16r), constant `31.63/√n` |
**⇒ Ratio 1.006. "Q1 is the stronger certified object" DOES NOT HOLD.**
### ⛔ M041 — **THE 1.006 RATIO CARRIES NO CORROBORATIVE WEIGHT**
**A 2×2 decomposition on the 990 common pairs:**
| radius convention | Q1 | Q2 | difference |
|---|---:|---:|---:|
| **each object's OWN radius** | **340** | **342** | **2** |
| **Q1's radius held for both** | **340** | **935** | **595** |
| **Q2's radius held for both** | **81** | **342** | **261** |
> **The underlying STATISTICS differ 2.7×** (`tv_hat` median: Q1 **0.5805**, Q2 **0.2157**) **while the radius
> CONSTANTS differ 7.34×** — **two large differences in OPPOSITE DIRECTIONS cancelling to the same fraction.**
> **⇒ A NUMERICAL COINCIDENCE, NOT CONVERGENCE. Two objects landing on the same number for unrelated reasons is
> not two objects agreeing.**
> **⇒ RULE: TO CALL AGREEMENT A CROSS-CHECK, COMPUTE THE 2×2 FIRST. Agreement that exists only where each side
> uses its OWN convention is CANCELLATION, NOT CONFIRMATION.**
**⚠️ THE EARLIER ERROR**: "Q1 is stronger" compared **Q1's tight radius against Q2's LOOSE one** ⇒ it measured
**bound conservatism, not object strength** — **exactly what the audit had warned about, now quantified twice
over.** **⚠️ And "PHIST may be the stronger carrier" remains REFUTED — the corrected statement is: NEITHER is
currently stronger, and the tie is not evidence of anything.**
**⚠️ The two objects are still DIFFERENT (k-prefix symbol law vs PHIST lattice law), so "comparable" is a
statement about the FRACTION, not about the objects.**
**⚠️ The one GENUINE regime difference is WHICH POPULATION each object admits** — Q2 takes any flow with a PHIST
record; Q1 requires `PPI_LEN >= 5` for k=5 eligibility — **measured per-service `n` differs by a median of only
0.5%** (ratio 1.005/1.004), so it does not change the conclusion.

## 🚨 DISPATCH HYGIENE — TWO DISTINCT WAYS A SPEC MISFIRES
> **① DO NOT PUT A DOCUMENT/METADATA EDIT INTO A NUMERIC DISPATCH SPEC.** The guard classified an "update the
> metadata" step as a writing request: **the same numeric task was REFUSED TWICE while it contained that step, and
> PASSED IMMEDIATELY once the step was removed.** **Fix = split the steps, never reword.**
> **② SPELL OUT KNOWN ENVIRONMENT NOISE, OR EVERY WORKER WILL RE-DISCOVER IT AS A BLOCKER.** A worker
> **invented** a `detect_image` prerequisite (it was NOT in my spec), got `SSH error: exit code 1`, and
> **stopped the whole task**. `detect_image` has returned that error for E8, E7, E8b, E3, E7b, E9 and E10 — **all
> of which completed normally.** **⇒ Routine noise, not a signal.** **Say so in every new spec**, and add
> **"if a command you were NOT asked to run fails, IGNORE IT and continue"**.
> **⇒ GENERAL FORM: a worker's caution can be aimed at the wrong thing — it correctly refused to fabricate, yet
> converted an unrequested probe's failure into a blocking condition.**

## 🔴🔴🔴 THE RADIUS 2X DEFECT — Q1's UPPER SIDE (M037/D031)
**The Q1 runner inlined `radius_i(M) = (sqrt((2M)^5) + 2.9604)/sqrt(n_i)`. The repository reference
`src/eibo/statcore.py::tv_upper_bound` (docstring 375–378, formula 406–411) is
`radius_1 = 0.5*sqrt(m/n1) + 0.5*fluctuation/sqrt(n1)` (likewise n2) ⇒ the runner is EXACTLY 2×.**
**Mathematics**: the L1 radius is `||P_hat-P||_1 <= sqrt(m/n) + sqrt(2log(2/α)/n)`; **TV = ½·L1 ⇒ a TV radius
MUST carry two ½'s.** **Hand check (M=1, n_a=1,375,270, m=32)**: reference `0.0036740`; runner `0.0073481`;
**ratio 2.0000.**
### CORRECTED vs CURRENT (k=5, 990 pairs)
| M | current | **corrected** | fraction |
|---:|---:|---:|---:|
| **1** | 289 (proxy) / 292 | **340/990** | **0.3434** (was 0.2919/0.2949) |
| 2 | 27/990 | **47/990** | **0.0475** (was 0.0273) |
| 4 | 0/990 | **3/990** | **0.0030** |
| 8 | 0 | **0** | 0 |
| 16 | 0 | **0** | 0 |
**✅ E10 INDEPENDENTLY RECONFIRMED 340 / 47 / 3 / 0 / 0 on the reference radius** (its Part 2, whole 990-row
pass), and reported the OLD column as 292 / 27 / 0 / 0 / 0 **in the same run** — **both conventions now
coexist in one artifact.** **E10 also printed a side-by-side against `statcore.tv_upper_bound` on a real row**
(n_a=1,375,270, n_b=359,864): **formula `0.0036740488509307036` vs repo `0.003674054979679717`, |diff| =
`6.1e-9`** — the formula matches the implementation to within the rounding of the supplied constant.
**UNCHANGED structurally**: M=1 the only feasible rung; upper side binding everywhere; frontier monotone
decreasing; M>=8 zero. **CHANGED numerically**: 29.2% → **34.3%**; M=4 from "exactly zero" to "3 pairs".
**⚠️ DIRECTION**: **CONSERVATIVE for the upper-side test** ⇒ no claim was overstated.
**⚠️ BUT `M=1` HAS TWO DIFFERENT NON-CANONICAL COUNTS — 289/990 = 29.19% (the `tv_hat > T(n)` PROXY) and
292/990 = 29.49% (the old 2× column). CANONICAL = reference radius + the D029 direct criterion = 340/990.**
**⚠️ REPORT THE CHANGE AS AN EXPLICIT `old → new` PAIR WITH THE CONVENTION NAMED** (292 → 340 at M=1,
27 → 47 at M=2, 0 → 3 at M=4): **an unexplained 29% → 34% jump between artifacts reads as a DATA REVISION
rather than a CONVENTION FIX — and this one moves in the project's favour.**
> **⭐ DISCRIMINATOR: a ratio CLEANLY equal to an integer or half-integer across rungs is the signature of a
> MISSING CONSTANT FACTOR, not of two objects differing in strength.**

## 🔴🔴🔴 SPEC-LEVEL ERROR PROPAGATION — **THE INDEPENDENT RECOMPUTE REPRODUCED THE ERROR (C020)**
**The wrong radius formula was MINE, written into the E3 spec, the independent-recompute spec, AND the `eps_lo`
spec** ⇒ the "independent" recompute reproduced the 2× form, and its **"maximum absolute deviation is zero" is
agreement between two implementations SHARING ONE WRONG FORMULA, not verification.**
> **⇒ C020: independence MUST be traced to the SOURCE OF THE FORMULA, not merely to a second implementation.
> A spec is a COMMON ANCESTOR: implementations derived from one spec cannot catch a spec-level error.**
**⇒ THE FIFTH REASON THE 2× SURVIVED** (alongside the Director's four): **⑤ THE SPEC THAT PRODUCED IT WAS ALSO
WRONG ⇒ every "independent" recompute did arithmetic on the same wrong formula.**
**★ THE FOUR SURVIVAL CAUSES, COMPLETE**: ① the artifact's metadata recorded the same wrong formula ⇒
self-consistency passed; ② the internal validation recomputed a quantity the radius never touches; ③ the error
was **conservative**, so the number looked plausibly bad; ④ **the spec that produced it was itself wrong.**
> **HARD CONSTRAINT (Rev 17/C020): NEVER RESTATE A FORMULA THE REPO IMPLEMENTS. Call `X.Y`, and require
> side-by-side printed values with a difference count.**

## 🔴🔴 C016 vs CONVENTION DRIFT — **"0 VIOLATIONS" PROVES SAME OBJECT, NOT SAME CONVENTION**
> **C016 CAN DETECT AN OBJECT MISMATCH; IT CANNOT DETECT A CONVENTION DRIFT. A 2× radius difference is
> completely invisible to it**, because `eps_lo`'s median (0.535) sits far below any version of `eps_hi`.
> **⇒ State the two roles separately in the methods section. Never let "0 violations" read as "conventions
> verified".**
**✅ Re-confirmed on the corrected radius: 0/990** (option (b), conservative in this direction — see Q1 GATE).
**⚠️ The `eps_lo` artifact's own 0/990 remains PROVISIONAL** (obtained against its own 2× `eps_hi`).

## 🔴🔴 EMPTY-CRITERION DEFECT — THE FOURTH "PASSES WITHOUT TESTING ITS HYPOTHESIS" CRITERION (D033/C019)
**Q2's original PASS criterion was "can a NON-EMPTY two-sided certificate be obtained" — but
`non-empty = (eps_lo <= eps_hi)`, which ANY sufficiently wide interval satisfies, and this construction (a
lower bound plus a large slack) satisfied it BY CONSTRUCTION.**
**⇒ Q2's PASS CONDITION IS NOW `eps_hi < 0.5` on a STATED FRACTION of eligible pairs — an informative error
floor `(1-eps_hi)/2`, the same shape as Q1's gate.** **Report the two groups SEPARATELY: (a) bounds CONSISTENT
(the C016 guard), (b) INFORMATIVE (`eps_hi < 0.5`). NEVER let (a) stand in for (b).**
**⇒ THE FOURTH SUCH CRITERION** (after the `k_cert`-only gate, `radius < 0.5` alone, and Q1's
`fraction_bracket_nonempty`) ⇒ **a RECURRING failure mode.**
**⇒ C019: ANY DECISION CRITERION MUST BE ABLE TO STATE WHEN IT WOULD FAIL IF THE HYPOTHESIS WERE FALSE.**
**⚠️ TWO DEFECTS COMPOUNDED IN `fraction_bracket_nonempty = 1.0`**: it is **both** an empty criterion **and**
inflated by the 2× radius (a too-large `eps_hi` makes a bracket EASIER to be non-empty ⇒ **ANTI-CONSERVATIVE**).

## 🔴🔴 THE TWO-OBJECT DEFECT — **THE Q2 "NON-EMPTY BRACKET" RESULT IS VOID (v1/v2); FIXED IN v3**
**E7b reported, on the SAME 990 pairs, `fraction_eps_lo_positive = 1.0` AND `fraction_bracket_nonempty = 0.002`.
Both can hold only if `eps_lo > eps_hi`.** **Largest pair: `tv_hat = 0.2584`, `eps_hi = 0.2718`,
`eps_lo = 0.4835`.**
> **When two bounds refer to the SAME object, `eps_lo > eps_hi` is MATHEMATICALLY IMPOSSIBLE.**
**Root cause**: the UPPER side bounded the **MEAN / LATTICE LAW** with an `m=32` **CATEGORICAL** radius; the
LOWER side ran on the **CONTINUOUS-support matrix of per-flow 32-vectors**.
**Synthetic demonstration (reproducible)**: A = half the flows `e_0`, half `e_1`; B = every flow `(0.5,0.5,0,…)`.
**Mean vectors differ by `0.00e+00` ⇒ `tv_hat = 0.0000`; the TRUE flow-level TV is `1.0`**; Michel returned
`0.1168`.
**✅ FIXED IN v3**: violations **988/990 → 0/990** on ONE declared object (**provisional, see C016 caveat**).
**⚠️ DPI gives `TV(marginal) <= TV(vector law)` — the vector-level quantity one-hot discards is REAL and
LARGER, and belongs in the paper as a SEPARATE ONE-SIDED RESULT.**

## 🔴 OBJECT ASSERTION RULE (standing constraint)
> **Every two-sided bound must assert `eps_lo <= eps_hi` per row; a violation is a bug, not a result. Every
> bound must declare WHICH OBJECT's TV it bounds. Never pair a CATEGORICAL finite-alphabet radius with a
> CONTINUOUS-support object. And this invariant certifies the OBJECT, never the CONVENTION.**
**⚠️ KS-type caveat**: `sqrt(ln(2/alpha_side)/(2*m_grid))` holds pointwise **only** when union-corrected over a
**categorical** score set; continuous scores must be **discretised to a fixed grid first**.

## 🔴 CROSS-FIELD CONSISTENCY (C016/C017 — C017 is C016's EARLIER-ACTING half)
> **Two or more proportions/statistics over the SAME pair set must be auto-cross-checked and the conflict count
> REPORTED. A mathematically impossible combination of summary fields is a MEASUREMENT BUG, never a finding.**
**C017 FIRES BEFORE C016** — C016 needs every row computed; C017 is discoverable **without reading code**.
**⚠️ COMPANION 1 (the Director's)**: **reading a field with the WRONG NAME silently yields a DEFAULT (0)** — he
read `saturation_fraction` when the field is `saturation_fraction_tv_ge_0_99`.
**⚠️ COMPANION 2 (M038)**: **`fraction_eps_lo_positive` (`eps_lo > 0`) was read as `eps_lo > 0.05`.**

## 🔴🔴 FIELD NAMING DEFECT — `lower_side_fraction` WAS NEVER A PROVEN LOWER BOUND
> **E3's `lower_side_fraction` was `tv_hat > T(n)`, a DETECTION THRESHOLD — the BAND'S LOWER-EDGE CONSTRAINT,
> NOT `eps_lo`. NO `eps_lo` WAS COMPUTED IN THAT RUN.**
**⇒ RENAME: `band_lower_edge_satisfied_fraction`.** **⇒ THE NEW CRITERION: `eps_lo > 0.05`, compared DIRECTLY.**
**✅ The rename has LANDED in code** (987/990, bit-identical to E3's own 987/990).
**⚠️ WORDING**: `eps_lo` is the **MICHEL ASYMPTOTIC HPLB ESTIMATE** ⇒ **"a proven-side (asymptotic) lower bound
exceeding 0.05"**, **NEVER a finite-sample certificate**.

## 🔴🔴 EPISTEMIC ASYMMETRY — **THIS IS THE PAPER'S THESIS, NOT A SHORTCOMING TO HIDE**
> **"a two-sided interval whose UPPER side is finite-sample strict (given the a-priori `m`) and whose LOWER
> side is an asymptotic lower bound."**
**That asymmetry IS the argument (C003).** **⛔ "PROVEN" IS NOT AVAILABLE AT ANY STAGE.**
**⛔ BANNED: *"admit a proven two-sided bracket"*.** **✅ PROMOTED TO A DECISION IN D037** — see
FINITE-SAMPLE STRICTNESS at the top of this file.
**⚠️ STANDARD PHRASING — use it verbatim: "a two-sided interval whose upper side is finite-sample strict (given
the a-priori `m`) and whose lower side is an asymptotic lower bound exceeding 0.05."**

## ✅✅ THRESHOLD DECISION — **DECIDED** (D025)
> **DECIDED: minimum 2,000 flows per service, SHARED BY BOTH QUESTIONS. The 53-service / 1,378-pair variant is
> SUPERSEDED and retired.** **Needs NO code change.**
### ⭐ THE CALIBRATED `T(n)` WAS INDEPENDENTLY VALIDATED
An exact Clopper-Pearson bisection (`U_i = BetaInv(0.975; e*n_i+1, n_i-e*n_i)`, `e=(1-TV)/2`,
`eps_lo = max(0, 1-min(U_a,0.5)-min(U_b,0.5))`; tol 1e-13, max interval width 5.684e-14, max 43 iterations)
gave **`T_exact(n_a) = 0.0516699007936` vs `T(n_a) = 0.0516696240918` ⇒ ~3e-7** (worst 1.6e-3 at the smallest
n), and **all five rungs' three fractions matched the calibrated form with maximum deviation 0**.

## 🔴 MONTH-LEVEL SPLIT — **PER-SERVICE SCOPE, NOT CORPUS SCOPE**
**Corpus-level feasibility is the WRONG test. Service sizes span FOUR ORDERS OF MAGNITUDE (617 … 1,927,343).**
- Thinnest training month (2024-07, 524,108 flows): the largest service has ~72,000 flows — ample;
- **but a service at the 2,000 threshold has only ~105 flows that month** (~148 in the thinnest test month);
- **at `m=32, n≈150` the upper radius is ≈0.744 ⇒ `eps_hi > 0.5` ⇒ no certificate can exist for that pair in
  that month.**
- **Corpus level, measured**: a clean **6,835,121 train / 3,164,810 test = 68/32** split with no empty month.
> **✅ CORRECT WORDING**: **"The month-level split is feasible IN AGGREGATE, but per-month certification covers
> only HIGH-VOLUME services; threshold-marginal services can support a TV POINT ESTIMATE within one month, but
> not a certifiable upper side."** **⚠️ Never let the bare word "feasible"/"satisfiable" appear alone in a
> framing document.**

## 🔴 MONTHLY FLOW COUNTS — **MEASURED** (E3b)
| 2024-05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 2025-01 | 02 | 03 | 04 | 05 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **69** | 611,478 | 524,108 | 531,597 | 979,976 | 1,176,029 | 1,217,162 | 691,573 | 1,103,198 | 791,427 | 741,237 | 848,009 | 784,137 |
1. **12 full months (5.2e5–1.2e6 flows each).**
2. **⚠️ 2024-05 holds only 69 flows — a BOUNDARY FRAGMENT (a one-day stub, not a month). **If the split is
   month-level it MUST BE EXCLUDED.**
3. **⚠️ "13 distinct months" IS MISLEADING** — **"12 full months plus a 69-flow boundary fragment."**

## 🟡 STEP-0 STATUS — **"PASS (XS SUBSET); FULL-CORPUS CONFIRMATION PENDING"** — NOT CLOSED
**⇒ The E1 result is already linked by `registry_id`; the remaining Step-0 closure status is separate from
registry linkage (see REGISTRY).**
**The Parquet month line is NOT on the MVP critical path, but it IS the condition for closing Step-0.**
**⚠️ ALWAYS state**: **on this subset `k >= 15` is unreachable for all flows anyway (only ~83–86% of flows reach
k>=15) ⇒ the full-crossing count is limited by FLOW-LENGTH variance, not environmental sparsity.**
**Supporting**: **32/53 single-ASN (27/45 at threshold)** ⇒ **`DST_ASN` demoted to an audit confound (Rev 12).**

## 🔴🔴 TWO TREES — **THE REMOTE TREE AND THE LOCAL TREE ARE GENUINELY SEPARATE; NEITHER SIDE SEES THE OTHER'S WRITES** (C014)
**There are TWO remote trees on one host, and a THIRD tree locally. They are NOT a shared mount.**
- **Evidence (C014)**: remote `/root/eibo/src/` was **EMPTY** while the local `src/eibo/` held the **complete**
  package (3 files, 971 lines, incl. `tv_lower_bound` at `statcore.py:599` and
  `tv_lower_bound_divisibility` at `divisibility.py:130`). **And the asymmetry runs BOTH ways**: artifacts
  produced on the server **do not appear** in the local tree, and locally-produced artifacts **do not exist** on
  the server.
- **Path probe (independent worker, `/root/eibo/artifacts/`)** → **exists**, 11 direct regular files,
  `du -sh` = `4.1M`. **`/root/autodl-tmp/eibo/artifacts/`** → **`ls: cannot access … No such file or directory`**
  (the probe then created it by writing a 900-byte `path_view_probe.json`, sha prefix `5d62ced2ca8c5395`, to
  BOTH trees — identical content, identical hash).
- **What lives where**: **`/root/eibo`** = **code + artifacts + logs** (container-root overlay, **30 GB**);
  **`/root/autodl-tmp/eibo`** = **the data disk** (**550 GB**, 515 free) holding `data/` —
  **`11240129415` bytes across 85 files**, incl. `CESNET-QUICEXT-25-XS.complete.h5` — plus `raw/`. **The data
  disk also holds `SHA256SUMS.txt`, `range-test.bin`, `.chunks/`, `.assembling`, and `raw/` — 85 files, NOT
  just the h5.**
> **⇒ CONSEQUENCES — these are OPERATIONAL RULES, not trivia:**
> **① A remote code edit is NOT pulled back locally; a local edit is NOT visible remotely.**
> **② `sync_code_to_remote` and `register_artifact(server=…, remote_path=…)` are the ONLY bridges.**
> **③ "Container-root writes sync to the shared tree" was asserted and is WITHDRAWN (correction 64).**
> **④ The file-retrieval ruling (see ARTIFACT PATH) rests on this: do NOT dispatch a worker to fetch a file.**
> **⑤ The ownership fence's `live_cwd: /root` vs `project_scope: /root/eibo` mismatch (C011) is THIS topology
> showing up as an attribution artefact.**
**⚠️ The consequence that produced a FALSE VERDICT**: E7 concluded *"the repository has no `tv_lower_bound`
implementation"* and recorded the lower side as `not_computed` for all 1,378 pairs — **a verdict of
"unavailable" for a package that was already written, tested and reviewed.** **⇒ C014: before reporting a
method unavailable, PROVE it — paste the literal `ImportError`; an existing-but-empty directory is NOT proof of
absence.**

## 🚨 ARTIFACT PATH — **SETTLED: KEEP AS IS; DO NOT MOVE; DO NOT RE-RAISE** (same topology as TWO TREES, above)
`/root/autodl-tmp/eibo/artifacts/` → **No such file or directory**; `/root/eibo/artifacts/` → **exists.**
**"Move artifacts to the data disk" was MISDIRECTED and is WITHDRAWN** — my error was treating a **conventional**
path as an **existent** one.
### ✅ FILE RETRIEVAL — `register_artifact(server=..., remote_path=...)` PULLS A SERVER FILE INTO THE LOCAL TREE
**Registered (13 of ours, local `artifacts/_project/data/`)**: `q1_absolute_summary.json`
`art_20260913_e08ee7` · `q1_absolute_counts.json` `art_20260913_3f762c` · `..._counts.csv`
`art_20260913_59bbc0` · `..._counts.meta.json` `art_20260913_6addd0` · `..._dense_counts_m1_m2.json`
`art_20260913_f2a9c4` · `..._counts_k10.json` `art_20260913_ea99d2` · `..._k10_summary.json`
`art_20260913_d887a7` · `..._counts_k10.meta.json` `art_20260913_1f0edb` · `q1_eps_lo_symbol_map.json`
`art_20260913_53ee73` · `q2_phist_certificate_v3.json` `art_20260913_0c7031` ·
`q1_independent_recompute.json` `art_20260913_791a79` · `q1_gate_five_pairs_full_n.json`
`art_20260913_613998` · `q2_upper_bound_16r.json` `art_20260913_262f85`.
**⚠️ `masking_verification.json` and `masking_regime_sweep.json` are NOT in this list** — E8's artifacts live
under `artifacts/` (not `_project/data/`) and were never registered. **STILL OWED.**
**Do NOT dispatch a worker to fetch files.**

## 💾 DISK — DENSE-COUNT OUTPUT IS CAPPED
**Container root carries `q1_absolute_dense_counts_k10_m1_m2.json` (519,609,851 B) and
`q1_absolute_k10_state.pkl` (94,928,854 B); container root is 30 GB.**
> **RULING: CAP the dense-counts output — DO NOT produce dense counts for M>=2.** The only use of dense counts
> is a second implementation recomputing TV, and that recompute has ALREADY been done at M=1/M=2 with max
> deviation 0.0 ⇒ no added verification value, only disk risk.

## 🔴 PRE-REGISTRATION 1 — THE CHANNEL IS (direction, size); TIMING IS DELIBERATELY EXCLUDED
`PPI` is `[3, 30]`: **row 1 = direction** · **row 2 = size** · **row 0 = inter-packet timing** (non-negative
proportion **1.0**, **p50 = 0**, **p95 = 97**, **max 59993**). **Downstream uses only TWO rows.**
> **REQUIRED DECLARATION: the channel is (direction, size). The exporter's third PPI channel — inter-packet
> timing — is deliberately excluded. Including it would change `|A_k|` and every `k_cert` value.**
**NOT a defect — a DELIBERATE restriction.** **Why**: a reviewer reading the dataset documentation **will** see
three channels and ask. **And because a grid fixed a priori satisfies C005, a timing channel is an AVAILABLE
EXTENSION PATH.** ✅ present here and in `experiment_plan.yaml` E2.
### ⭐ COMPANION DECLARATION — ML-ONLY INPUTS
**Consumes ONLY the channel-relevant fields.** Does **NOT** use `QUIC_USER_AGENT`, `QUIC_TLS_EXT_*`, or
`QUIC_*CID` — **visible BEFORE encryption.**
> **Our observable is restricted to protocol-forced packet-level quantities; we do NOT touch
> TLS-fingerprint-style side channels.**

## 🔴 PRE-REGISTRATION 2 — MASKING IS A PRECONDITION, NOT A CLEANUP STEP
**MEASURED**: 200,000 flows without replacement, seed `20260913`, **3,805,365 tail scalar slots, histogram
`{0: 3805365}`**, identical across all three rows.
> **Any downstream k-prefix computation MUST mask tail slots beyond `PPI_LEN`. UNMASKED `tv_hat` IS NOT
> CITABLE.** **⚠️ BANNED: "k=30 difference is small ⇒ masking is optional".**
### PREREG-2b — k=5 IS A CLEAN GATE DENOMINATOR
**E8: k=5 post-mask 990/990, 45/45, 0 dropped. E3: 53 labels → total-flow layer drops 8 → 45 → `PPI_LEN >= 5`
layer drops 0 more.**

## 🚨🚨 MASKING SCOPE — MY SPEC MADE THE E8b COMPARISON A STRUCTURAL NO-OP
**E8b's signed differences are exactly 0.0 at EVERY (M,k) — because I wrote "both arms must use the same flow
set: flows with `PPI_LEN >= k`".** ⇒ **`min(PPI_LEN,k) == k` ⇒ identical prefixes.**
> **✅ REAL FINDING: the masking requirement's SCOPE is exactly the flows ADMITTED while having `PPI_LEN < k`.**
**⇒ The masking effect has NEITHER been measured NOR refuted.** **Ruling: no discriminating power by
construction; keep as a NON-FINDING.** **⚠️ The test has now been run TWICE in regimes where the effect cannot
appear** (once at saturated TV, once at zero padding exposure) ⇒ **locating the scope needs a TWO-ARM DESIGN
WITH DIFFERENT FLOW SETS, and the requirement should be WRITTEN INTO THE SCRIPT rather than re-derived per run.**

## 🚨🚨 GATE DEFINITION DEFECT — MY `radius(M,n) < 0.5` WAS THE WRONG UPPER SIDE (RESOLVED)
The sufficient condition is **`eps_hi = tv_hat + radius_a + radius_b < 0.5`**. **✅ E3's worker CAUGHT IT
ITSELF.** **Lesson: a good worker corrects an erroneous spec — and the RADIUS 2X DEFECT shows the converse.**

## ✅✅✅ E3 / E3b — Q1 RESULTS
| k=5, M | band lower EDGE | upper **AS REPORTED (2×)** | **CORRECTED upper** | **corrected band membership** | `tv>=0.99` | `T_n_median` | `radius_median` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **1** | 0.9969697 (987) | 0.29495 (292) | **340/990** | **0.3434** | **0.0000** | 0.06714052 | 0.10047173 |
| 2 | 1.0000000 (990) | 0.02727 (27) | **47/990** | **0.0475** | 0.1050505 | 0.06714052 | 0.40761614 |
| 4 | 1.0000000 | 0.00000 (0) | **3/990** | **0.0030** | 0.2393939 | 0.06714052 | 2.14508727 |
| 8 | 1.0000000 | 0.00000 (0) | 0/990 | 0 | 0.3363636 | 0.06714052 | 11.97370826 |
| 16 | 1.0000000 | 0.00000 (0) | 0/990 | 0 | 0.3909091 | 0.06714052 | 67.57278466 |
**⚠️ `radius_median` and the "as reported" columns are the 2× form; corrected = 340/47/3/0/0
(0.34343/0.04747/0.00303/0/0), INDEPENDENTLY RECONFIRMED BY E10.** **Registry metrics carry BOTH conventions
under distinct keys (`..._ref_radius`) plus a `radius_convention` field.**
**READINGS (structure survives the correction)**: **`binding_side_by_rung` = upper at ALL FIVE rungs**;
**the feasible set shrinks monotonically in M**; **M=1 the ONLY feasible rung** despite the SMALLEST alphabet
and the LOWEST `k_cert` ⇒ **"a high `k_cert` does not imply feasibility" measured**;
**saturation rises monotonically** (0 / 0.105 / 0.239 / 0.336 / 0.391) ⇒ **finer alphabets have LESS resolving
power ⇒ coarse-graining is NECESSARY, not a concession**; **M=1's saturation fraction `0.0`**;
**`service_counts`**: 53 → drops **8** → **45** → `PPI_LEN>=5` drops **0**; **`coverage_by_k`**: k=5 `990/990`,
k=10 `990/990`, k=15 `946/990`, k=30 `820/990`; **`subsampled_for_tv: false`**.
**E3b, k=10**: upper/both = 0.011111 / 0 / 0 / 0 / 0; saturation 0.006061 / 0.290909 / 0.592929 / 0.638384 /
0.688889 ⇒ **only M=1 has any certificate ⇒ the cell-by-cell prediction HOLDS.** **⚠️ ALSO 2×.**
**⚠️ MY SATURATION THRESHOLD (0.5) WAS ARBITRARY** — **judge by whether a rung has pairs at 1.0 at all.**
**⚠️ E8b: the MEDIAN pair falls OUTSIDE the band** — and §48's mechanism sentence explains why M=1 wins (*the
upper side needs `comp × latent < 0.5 − radius`, so a rung retaining MORE separation loses the upper
certificate SOONER*). **Keep the two adjacent so the apparent tension is pre-empted.**

## ✅✅✅ Q1 `eps_lo` — THE LOWER SIDE IS MEASURED (one-hot symbol map), **20k-CAPPED**
**Object**: the k-prefix **CATEGORICAL SYMBOL LAW** at `k=5, M=1`, one-hot draws, `m = 32` (correct for 32
categorical cells), **cap 20,000 flows/service**, reservoir seed `20260913`, 990 pairs.
**`eps_lo` quantiles**: min `0.012229618353594561` · q5 `0.13882719950908506` · q25 `0.32683386139903453` ·
**median `0.5349447174554081`** · q75 `0.6922818802960757` · q95 `0.8879232523286932` ·
max `0.9668421939255496`.
**`eps_hi` quantiles (20k-CAP — do NOT compare with full-n)**: min `0.17936364346611072` ·
q5 `0.33507471788800786` · q25 `0.5136915815880585` · **median `0.7294065931913595`** ·
q75 `0.888851544991758` · q95 `1.076048866786942` · max `1.1954909853682723`.
**⚠️ ITS OWN `n_a` IS 20,000 AND ITS `radius_a = 0.06093329079402921` = `(√32+2.9604)/√20000`** ⇒ **for THIS
artifact both sides are capped. (This is where my M040 error started — I wrongly generalised it to Q2 v3.)**
**`band_lower_edge_satisfied_fraction` = 0.996969696969697 (987/990)** — **bit-for-bit identical to E3's
987/990** ⇒ **two paths cross-agree.** `fraction_eps_lo_positive` = 1.0 (`>0`, NOT `>0.05`). `violation_count` = 0
(**provisional**).
**✅ THE PREDICTION HELD**: median **0.858537 → 0.534945, a drop of 0.323593.** **The vector-level result
(median 0.858537) is kept as an INDEPENDENT ONE-SIDED result, never a lower bound on the marginal TV.**
**Registered `art_20260913_53ee73`.** **⚠️ Its own `eps_hi` also carries the 2× radius.**
**⚠️ A LATER RUN COMPUTED THE SAME FIVE AT FULL n — see Q1 GATE (E10).** **The full-n result is the one that
matters for the gate.**

## ✅✅✅ Q2 v3 — SINGLE OBJECT; SEE THE SUM-TO-ZERO DEFECT FOR THE CORRECTION
**Artifact** `q2_phist_certificate_v3.json` **1,540,318 B** `71a20309c2d12fbeb5f7204f312243c951e0259d6ae3550ea579fcf6cbb94840`,
990 rows, 45 services, cap 20,000, reservoir seed `20260913`, lattice-cell seed `20260914`, violating rows 0
(**provisional**).
- **Declared object**: *"Draw a flow uniformly at random from the service; then draw one cell from that flow's
  normalized 32-cell PHIST distribution."* ✓ ONE object.
- **Upper side as run**: `r_i = sqrt(log(2*31/0.025)/(2*n_i))`, `eps_hi = tv_hat + 31*r_a + 31*r_b` — **the 31
  is 2× too large; the corrected 16r gives 342/990.**
- **⚠️ ITS UPPER RADIUS USES FULL `n` (`radius_coordinate_a` reproduces from `n_a`), WHILE ITS LOWER SIDE USES
  `lower_n_a = 20000`.** **Both columns are present per row — the artifact self-documents the calibre.** **See
  CALIBRE CLAIM (M040).**
- **Lower side**: `tv_lower_bound(method="michel")` fed **one sampled cell per uniformly sampled flow as a
  32-column one-hot matrix** ✓.
- **`tv_hat` median `0.2157`** (vs Q1's `0.5805`) — **this is the 2.7× statistic gap in M041.**
- **`eps_lo` quantiles**: min `0.001220` · q5 `0.057705` · q25 `0.110293` · **median `0.161513`** ·
  q75 `0.233195` · q95 `0.428943` · max `0.837952`.
- **`eps_hi` quantiles (31r)**: min `0.183261` · q5 `0.372005` · q25 `0.638490` · **median `0.925919`** ·
  q75 `1.219624` · q95 `1.683410` · max `2.285121`.
**⇒ UNDER D033 THIS RUN IS NEARLY UNINFORMATIVE on its own loose constant (informative fraction brackets
between ~5% and ~25%); that fraction was NOT computed by the run and was NOT fabricated.**
**⚠️ v2 must NOT be overwritten** — separate at 1,536,452 B `655ab121…`. **Registered `art_20260913_0c7031`.**

## ✅✅ E1 STEP-0 (XS SUBSET) — **GATE PASSES**
**All 10,000,000 flows, no subsampling.** **53 distinct services**; **45 at `>= 2000`**;
**GATE all: 43 two-axis / 39 full-crossing**; **GATE `>= 2000`: 39 two-axis / 36 full-crossing**;
**Single-ASN: 32/53 all, 27/45 at threshold.** Artifact `step0_occupancy.json` 46,050 B `5bbfd722…`.

## ✅ `src/eibo` — UPLOADED AND WORKING; **IT IS THE AUTHORITY FOR THE UPPER RADIUS**
Remote `wc -l`: `38 / 711 / 222` = **971**; **import smoke PASSED**. sha256-verified: `statcore.py` 25,641 B
`c8b1fd15…`; `divisibility.py` 9,186 B `2607ee3b…`. **`sys.path.insert(0, "/root/eibo/src")`; numpy only.**
**`tv_upper_bound` at `:360` (formula 406–411) and `tv_lower_bound` at `:599`.**
**✅ Q2 computed 990/990 lower bounds (prior: 1,378/1,378 `not_computed`) — "the method does not exist" was an
AVAILABILITY failure.**
**C014: before reporting a method unavailable, PROVE it — paste the literal `ImportError`.**
**✅ INTERPRETER PATH IS A MEASURED FACT**: `/root/miniconda3/bin/python3` (symlink → `python3.12`);
**`/opt/conda/bin/` does NOT exist.**
**⚠️ The path probe saw `*.upload.guard` zero-byte sidecar files beside each module** — harmless, but they will
show up in any `ls` of `src/eibo/`.

## ✅ E8 / E7b
**E8**: 10,000,000 rows; **all-zero padding over 3,805,365 slots**; `PPI_LEN` min 2 / max 30 / median 30 /
q5 2 / q25 19; **`>= 15` fraction `0.8348841`**; **k=5 post-mask 990/990**. `masking_verification.json`
**92,947 B** `f7cbab76…`; `masking_regime_sweep.json` 832,121 B `453ac98d…`. **⚠️ NEITHER IS REGISTERED — OWED.**
**E7b**: `q2_phist_certificate_v2.json` **1,536,452 B** `655ab121…`; threshold 2,000; **388 rows excluded**;
`alpha_law = 0.025`; `fraction_eps_hi_below_half` = 0.9061 (v1: 0.7206). **RETRACTED as Q2 conclusions**:
`fraction_eps_lo_positive`, `fraction_bracket_nonempty`, the 7 certificate-lost pairs.
**E7 (v1)**,口径 retired: 53 services / 1,378 pairs; `eps_hi < 0.5` = 0.7206095791; zero-TV sanity check
941/1378 = 68.29%. `q2_phist_certificate.json` 887,700 B `2d9d1bbd…`.
**⚠️ E7 IS REGISTERED AS `failed`, DELIBERATELY NOT `negative`** — it is an **OBJECT-MISMATCH
implementation/design defect, not a scientific finding that the method does not work.** **Recording it as
negative would pollute later judgement.** Superseded by `E9_Q2v3`.
### ⚠️ SMALL SERVICES ARE STRUCTURALLY INFEASIBLE
At `n=617`, `m=32` the radius is `0.3469` ⇒ only `tv_hat < 0.1531` could certify. **Including them measures
COVERAGE, not NON-TRIVIALITY.**
**⚠️ The `radius_median` values 0.10047 / 0.40762 / 2.1451 / 11.974 / 67.573 in E3's summary are the 2× form.**
**⚠️ E8's "unmasked arm" is MISLABELED — do not cite it as an unmasked arm.**

## 🚨 THE GATE USES AN ABSOLUTE QUANTITY — NOT ANY RATIO
**`compression_ratio` must NOT gate.** Label **`cross_k_ratio_not_a_gate_criterion`**.
**⭐ POSITIVE EVIDENCE (D028)**: the design-time `comp(1) = 0.02 < T(n)` predicted an EMPTY window at M=1; the
**MEASURED k=5 absolute TV median is 0.5805** ⇒ **reading the band via the ratio would have reversed the
conclusion.** **§48's mechanism**: the upper side needs `comp × latent < 0.5 − radius` ⇒ **a rung that retains
MORE separation LOSES the upper certificate SOONER.** **This is WHY M=1 wins.**

## 🚨 `denominator_symbol_law` — SOURCE IS CORRECT; ONLY OLD ARTIFACTS ARE STALE
Local line 499 already says **"M=16 …"**, consistent with `known_limitations` (714). **⇒ fix by RERUN.**
### `chosen_k` / `alt_k` — RESOLVED FROM THE CODE (345–354)
`ok(k) := usable_pair_fraction >= 0.80 AND aggregate_flow_fraction >= 0.50`, from 30 DOWNWARD. **Measured ⇒
`chosen_k = 30`, `alt_k = 15`.** **Globally single-valued ⇒ header, NOT a table column.**

## 🚨 SATURATION IN THE ALPHABET — `|A_k|` vs n (the k=30 masking exhibit)
**M=16, k=30 ⇒ `|A_k| = 32^30 ≈ 1.4e45` vs a largest service of 1.93e6 ⇒ both arms pin at `tv_hat ≈ 1`**
(masked median `0.999833`; difference median `0.0`; max `|diff|` `0.0018372`).
**⚠️ ALWAYS ask whether a NEAR-NULL OR NEAR-MAXIMAL result comes from the claimed mechanism or from SATURATION.**

## 🚨 PADDING DIRECTION IS CONSERVATIVE ON THE ABSOLUTE QUANTITY
Padding makes services look **more alike** ⇒ absolute TV pushed **DOWN** ⇒ lower side looks **WORSE**.

## 🔴 ALPHA CONVENTION — BOTH SIDES MUST DECLARE IT (per-law alpha/2)
lower side (`T(n)`, two cells): alpha/2 per cell. upper side (`radius_1 + radius_2`, two laws): alpha/2 per law.
### ⚠️ THE UPPER SIDE WAS ASYMMETRIC — FIXED (M028)
Per-law α = 0.05 ⇒ joint 0.90 while the lower side unioned at α/2 ⇒ **two sides of ONE criterion claimed
different confidence levels, invisibly (~1e-4).** Fixed: `radius_sum` takes `alpha_per_law` (default α/2); a
regression test asserts α/2. **11 tests pass.** **⚠️ OPEN, LABELLED NOT ASSUMED**: whether `T(n)`'s `0.05`
constant depends on α. **⛔ D037 settles the POLICY (do not tighten the lower side to answer this) but does NOT
answer the question.**

## ⚠️ `T(n)` — CORRECTED, AND NOW INDEPENDENTLY VALIDATED
> **🚫 VOID — 0.0659 / 0.0550 / 0.0522 / 0.0511 with `c ∈ [2.239, 2.259]`.**
**`T(n) ≈ 0.05 + c(n)/√n`**: `0.05` **EXACT**; **`c ≈ 1.958`** — **CALIBRATED and validated to ~3e-7 against an
exact Clopper-Pearson bisection.**
| n | 2e4 | 2e5 | 1e6 | 3.9e6 |
|---|---|---|---|---|
| **CORRECTED** | **0.0639** | **0.0544** | **0.0520** | **0.0510** |
| *void* | *0.0659* | *0.0550* | *0.0522* | *0.0511* |
**⚠️ `c`'s PROVENANCE MUST BE PINNED**: `c` was recomputed under the M028 **`alpha/2`-per-law** convention; the
**void** `c ∈ [2.239, 2.259]` applied `alpha/4`. **The revision is PASS-FAVOURING** ⇒ its justification must be
**convention-driven and STATED**, never left for a reader to notice.
**⚠️ `T(n)` IS ONLY A CROSS-CHECK COLUMN NOW** (D029 replaced the proxy with the direct `eps_lo > 0.05` test).

## 🚨 PRIORITY REORDER: THE **h5** CARRIES THE LABELS ⇒ MVP RUNS NOW, WITHOUT MONTHS
| field | h5 (XS, 10M flows) | Parquet (June, 11.85M rows) |
|---|---|---|
| **`APP` (service label)** | **present, 10M/10M** | **ABSENT** |
| `QUIC_CLIENT_VERSION` / `DST_COUNTRY` / `DST_ASN` | present | present |
| `PPI` / `PPI_LEN` / `PHIST_*` / `QUIC_SNI` / `TIME_FIRST` | present | present |
### ⛔ CLAIMS THAT MUST NOT BE REVIVED
1. **"The two Q2 environment axes cannot be computed from the XS h5"** — FALSE; also banned: **"environment axes
   exist only in Parquet"**.
2. **The old Parquet occupancy result keyed on the RAW SNI must NOT be cited.**
3. **"Step 0 is not_measurable"** applies **ONLY to the Parquet route**.
4. **"Parquet-first"** requires a validated SNI→service mapping, which is **UNWRITTEN AND LOAD-BEARING**.

## 🔴 THE `3` IS RESOLVED — BY MEASUREMENT
`infer_ppi_channels()` (180–232): **highest direction-like = direction, next = size, remainder = timing**;
**acceptance requires `> 0.98` and `> 0.80`**, else a BLOCKER (432).

## 🚨 INDEPENDENCE MUST BE AT THE IMPLEMENTATION LEVEL
> **Two runs of the SAME implementation agreeing defines NOTHING.** **C012.**
**✅ The independent recompute PASSED where it mattered**: its own `own_tv_from_counts` reproduced the TV to
**max deviation 0.0** at M=1/M=2, having **deliberately NOT used** the project `tv`, any E3 script, or
`evaluate_q1_absolute.py`'s threshold routines. **⚠️ BUT ITS RADII ARE VOID** (2×, from my spec) ⇒ **its
upper-side conclusions are VOID; its two verification conclusions SURVIVE.** **Registered
`art_20260913_791a79`.** **⚠️ See SPEC-LEVEL ERROR PROPAGATION (C020).**

## ⚠️ M >= 8 IS n-CONDITIONAL
`radius(M=8) = (1024 + 2.9604)/√n` **in the 2× form** → 0.52001 at n=3.9e6, critical n 4,218,591. **In the
CORRECTED form the radius halves ⇒ the "M>=8 does not certify at n = 3.9e6" statement must be RE-DERIVED before
it is quoted.** **✅ NOW RE-DERIVED (M054): the crossovers below are the CERTIFIABILITY criterion
(`eps_hi = tv + radius < 0.5`), k=5, M=8 -- 4,218,591 / 6,591,548 / 26,366,192 at tv = 0.00 / 0.10 / 0.30.
The 4,218,591 above is the RADIUS-ONLY (necessary, not sufficient) value and coincides with tv=0.00 only.** **✅ E3 measured `radius_median` 11.97 (M=8) and 67.57 (M=16), both 2× forms.**

## ⚠️ SPLIT — MEASURED FACTS AND THE CORRECT WORDING
`split`: **`span_days: 365.0`**, `TIME_FIRST` `2024-05-31T21:00:00+00:00` → `2025-05-31T21:00:00+00:00`,
**`time_granularity_achieved: "day-level (/flows/DYYYYMMDD daily tables)"`**, **`deviation_label: null`**,
`policy: "flow-disjoint AND time-disjoint; packet-level PROHIBITED"`.
**⇒ CORRECT WORDING**: **"the span is about a year (365 days) covering 12 FULL months plus a 69-flow boundary
fragment ⇒ the pre-registered MONTH-LEVEL split IS SATISFIABLE at corpus level (excluding the fragment); a
DAY-LEVEL split is ALSO feasible — but see MONTH-LEVEL SPLIT — PER-SERVICE SCOPE."**

## k-PREFIX COVERAGE BIAS — Q1 ONLY (not Q2)
**E3**: k=5 `990/990`, k=10 `990/990`, k=15 `946/990`, k=30 `820/990 = 0.8282828`.
### PHIST IS IMMUNE TO BOTH COVERAGE DEFECTS (citable, with a MECHANISM)
> **PHIST is immune to the k<=30 coverage bias because it aggregates the entire flow; and it is immune to padding
> because the padding problem occurs only on k<30 short-flow prefixes and PHIST takes no prefix.**
**⚠️ NOTE THE CALIBRE CONSEQUENCE**: PHIST admits flows **without** the `PPI_LEN >= 5` requirement, so the two
objects admit slightly different flow populations — **measured difference: median 0.5% per-service n.**

## 🚨 REGISTRY
**The registry now holds 6 experiments (E1, E3, E7, E8, E9_Q2v3, E10) — the roadmap's "Registry is EMPTY: 0
experiments" is STALE.** **Verified linkage: 5 entries were ALREADY linked (E1→E1, E3→E3, E7→E7,
E8→E8, E9→E9_Q2v3); E10 was the only real gap and is now linked (backfilled).** **The coverage view is
therefore 6/10, not 0/8.**
**E2 / E4 / E5 / E6 are UNLINKABLE AND ARE NOT GAPS: they have NEVER RUN, so no registry entry exists;
creating one would FABRICATE provenance for an experiment never performed. They stay `planned`.**
**⚠️ Any blanket negative about file contents (for example, "all `registry_id` values are null") must be
re-verified at the moment it is made; report the specific entries and their actual state.**
**⚠️ `submit_on_allocated` is the ONLY path that publishes `ALLOCATED → RUNNING` with PID/log/monitoring
metadata; a registry-managed run must use it, never bare `submit_training_job` and never Bash `nohup`.**
**⚠️ E10 FINISHED BUT STAYED AT `RUNNING`** — `conclusion` was set with `completed_at` absent. **⇒ A finished
run does not always close itself; check for that signature and close it manually (ANALYZING → DONE).**

## MVP GATE
**PASS requires ALL THREE.** Any failure is a FAIL branch.
1. **`k_cert >= 5`, NO UPPER BOUND** — WITH J and L. **✅ ANSWERED: gate = `(eps_lo > 0.05) ∧ (eps_hi < 0.5)`
   on ONE object = `336/990 = 0.3394`**, **FULLY MEASURED** with `measured_full_n_pair_count = 990` and
   `assumed_pair_count = 0` (lower full n, cap removed: 986/990; upper repository-function result: 340/990).
   **The earlier range `[333, 336]` is SUPERSEDED** because it was valid only while the lower side was
   half-measured; with no assumed remainder, that range has no basis.
2. **`eps_lo` distribution** — **MEASURED**: median `0.534945` (20k-capped), min `0.012230`; the full-n
   threshold count is **986/990 above 0.05**.
3. **`eps_hi` / floor distribution** — must **not** sit at the maximum. **(Q1 upper 340/990 on the reference
   radius; Q2 342/990 at 16r.)**

## `eps_hi` CLIPPING POLICY
**Never silently clip `eps_hi` to [0,1].** **⚠️ The 7 former instances are RETRACTED to UNDETERMINED.**

## CITABILITY
- **Citable (at a stated n, WITH alpha and its split)**: the `k_cert` table (18/18); the analytic window table;
  the **r0 assumption-free statement**; the **PHIST-immunity line**; `tests/write_report.py` numbers; the
  **all-zero padding over 3,805,365 slots**; the **k=5 post-mask 990/990, BOTH layers**; the `PPI_LEN`
  distribution and per-k coverage; the three-channel finding; the ML-only-input fact; the field-matrix /
  `APP`-absent facts; the Zenodo-outage finding with its control; **E1's Step-0 table (WITH the XS-subset caveat
  and the k>=15 flow-length note)**; **E3's STRUCTURE — the binding side, the monotone M shrinkage, the monotone
  saturation growth**; **the `eps_lo` symbol-map distribution and the 0.323593 drop**; **the monthly flow
  counts**; the **SATURATION exhibit AND phase diagram**; the **M028 alpha fix**; the **D028 refutation of
  `comp(1) = 0.02`**; **the independently validated `T(n)` calibration (~3e-7)**; **the independent
  `own_tv_from_counts` recompute (deviation 0.0)**; **Q2 v3's object declaration**; **the GATE `336/990` and
  E10's five-pair table**; **the reference-radius per-rung counts 340/47/3/0/0, reconfirmed in one run against
  the old 292/27/0/0/0**; **the sum-to-zero `16r` derivation, the exhaustive sign-pattern check, and the
  run-emitted 342/990**; **the `[152, 342]/990` feasible range with `935` marked UNPROVEN**; **the M041 2×2
  cancellation table**; **the corpus-wide binding-side count (upper removes 650, lower removes 4)**; **the TWO
  TREES topology and its C014 evidence**; **E10's `6.1e-9` formula-vs-repo side-by-side**.
- **Downgraded**: `T(n)` → calibration-dependent AND alpha-corrected (**now independently validated**) AND
  **cross-check-column-only**; "M >= 8 does not certify" → **must be re-derived on the corrected radius**;
  **"M=1 INFEASIBLE" → REFUTED**; every design-time number; divisibility joint fractions as statements about
  **real data**; `compression_ratio` → not a gate criterion; "monthly ZIPs from DataZoo" → refuted; the masking
  readout's compression medians; the OLD readout artifact; **"Q1 is the stronger certified object" →
  OVERTURNED (D036)**; **"the Q2/Q1 ratio mixes n calibres" → REFUTED (M040)**; **"the Q2/Q1 tie corroborates"
  → REFUTED (M041)**; **the point prediction "340" → FAILED (336, inside the bracket)**.
- **⚠️ NOT CITABLE UNTIL CORRECTED**: **EVERY upper-side figure from E3, E3b and E9 on the 2× radius**; **the
  k=10 vs k=5 comparison**; **`fraction_bracket_nonempty` anywhere**; **`radius_median` as printed**;
  **`eps_hi` from the 20k-capped `eps_lo` artifact placed beside full-n `eps_hi`**;
  **`q1_independent_recompute.json`'s upper-side conclusions**; **the Weissman `935/990` form** (unproven).
- **⚠️ NOT CITABLE / RETRACTED**: **any use of `lower_side_fraction` as a proven lower bound**; **"proven" in any
  form**; **"29% of service pairs admit a proven two-sided bracket"**; **Q2's `fraction_bracket_nonempty` and
  `fraction_eps_lo_positive`**; **the 7 "certificate lost" pairs**; the k=30 masked-vs-unmasked difference; **any
  claim that the masking effect has been measured or refuted**; the 53-service variant; **"13 distinct months"**;
  **any reading of a binding side off the five-pair table**.

## `k <= 30` — CLOSED BY MEASUREMENT
**max=30 does NOT mean most flows reach 30 (q5 = 2; flow coverage 0.506 at k=30).**

## M_max IS A PAPER RESULT, NOT A CONCESSION
`(2M)^k < n·B^2` ⇒ `M < 0.5·(n·B^2)^(1/k)`. **A FUNCTION of (k, n, tv).** At n = 3.9e6, k=5: **≈ 4-5.**

## Channel ladder (pre-registered; EVERY rung reported)
| rung | channel | M | symbol alphabet | grid |
|---|---|---|---|---|
| 0 | direction only | 1 | 2 | 2^k |
| 1 | direction × 2 size classes {<=1200, >1200} | 2 | 4 | 4^k |
| 2 | direction × 4 size classes | 4 | 8 | 8^k |
| 3 | direction × 8 size classes | 8 | 16 | 16^k |
| 4 | direction × 16 size classes | 16 | 32 | 32^k |
**M=1 MUST be listed.** **A high `k_cert` does NOT imply feasibility** — **✅ measured.** **Rung 1's boundary is
genuinely a priori**: RFC 9000 §14.1.
### Full `k_cert` table (VERIFIED 18/18 — citable; criterion incl. tv_hat; alpha=0.05)
| n | tv | r0 | r1 | r2 | r3 | r4 |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | .05 | 7 | 3 | 2 | 1 | 1 |
| 1,000 | .30 | 3 | 1 | 1 | 0 | 0 |
| 10,000 | .30 | 8 | 4 | 2 | 2 | 1 |
| 100,000 | .30 | 11 | 5 | 3 | 2 | 2 |
| 1,000,000 | .30 | 15 | 7 | 5 | 3 | 3 |
| **3,900,000** | **.30** | **17** | **8** | **5** | **4** | **3** |
| 3,900,000 | .40 | 15 | 7 | 5 | 3 | 3 |
| 10,000,000 | .30 | 18 | 9 | 6 | 4 | 3 |
| any n | **.50** | **0** | 0 | 0 | 0 | 0 |

## MVP restructured into TWO separate questions
- **Q1** (k-prefix): the gate `(eps_lo > 0.05) ∧ (eps_hi < 0.5)` on ONE object = **336/990 = 0.3394**.
- **Q2** (PHIST): v3 aligns the object (0/990 violations, provisional); at the corrected 16r it reaches
  **342/990 = 0.3455** ⇒ **numerically level with Q1 — BUT THE TIE IS A CANCELLATION (M041), NOT CORROBORATION.**
They **never borrow from each other**.

## PHIST — VERIFIED (realized support 32/32 in BOTH formats)
Edges `[0,16), [16,32), [32,64), [64,128), [128,256), [256,512), [512,1024), [1024,inf)`; rule
`value < 16 → bin 1`, `value > 1023 → bin 8`. **All four fields `uint32`, shape `(8,)`; zero PHIST vectors 0.**
**(a) Cardinality 32, NOT 128.** Four **separate marginal histograms**; **no joint array is emitted.**
**(b) Fixed bins fix the DIMENSION, not the SUPPORT.** **The certified object must be named.**
**(c) PHIST and the k-prefix are unordered in BOTH directions.** **Large PHIST TV ⇒ large full-flow TV.**
**Small PHIST TV is SILENT about the k-prefix.**
**(d) THE LATTICE LAW vs THE COORDINATE LAW ARE DIFFERENT OBJECTS.**
### Sample thresholds — LABEL EVERY NUMBER WITH ITS eps
| m | eps | rough n/service | joint-95% n/service |
|---|---|---|---|
| 32 | **0.10** | **≈3,200** | **≈7,400** |
| 32 | 0.05 | ≈12,800 | ≈29,700 |
Verified joint-95% zero-TV radii at empirical TV = 0 (alpha=0.05):
| m | n=1e3 | n=1e4 | n=1e5 | n=1e6 | n=1e7 |
|---|---|---|---|---|---|
| 32 | 0.2725 | 0.0862 | 0.0273 | **0.0086** | **0.0027** |
**edges_data_adaptive = false.** **Framing verdict `STRONGER_AND_HONEST`, conditional.**
**Verification rule (binding)**: the question is **which class of claim PHIST supports**, NOT whether it is
"useful".

## Design-audit revisions
- **Rev 3** — divisibility REQUIRES realizability.
- **Rev 4** — q-escalation ladder: vacuous ⇒ report **explicitly as 0**.
- **Rev 5** — service-stratified sampling; **QUICEXT-25 vs QUIC22 ⇒ NOT comparable.**
- **Rev 7** — **no category-4 precedent found**; the **measured bracket itself is the primary gap**.
- **Rev 8** — the **service/pair threshold is 2,000, shared by both questions (D025)**.
- **Rev 9** — the E3/E5 `k ∈ [5,15]` window is **RETIRED**.
- **M028** — the upper side's radius constant was under-split; fixed with `alpha_per_law` + regression test.
- **Rev 10** — **`eps_lo > eps_hi` signals different objects.**
- **Rev 11** — **a masking comparison requires DIFFERENT flow sets between arms.**
- **Rev 12** — **`DST_ASN` collinearity ⇒ audit confound.**
- **Rev 13** — **every two-sided bound declares ONE object and asserts `eps_lo <= eps_hi` per row.**
- **Rev 14** — **`band_lower_edge_satisfied_fraction`; criterion `eps_lo > 0.05`.**
- **Rev 15** — **CROSS-FIELD CONSISTENCY.**
- **Rev 16** — **EPISTEMIC ASYMMETRY IS THE THESIS; "proven" unavailable (D030).**
- **Rev 17** — **NEVER RESTATE A FORMULA THE REPO IMPLEMENTS (C020).**
- **Rev 18** — **C019: a decision criterion must state when it would fail if the hypothesis were false (D033).**
- **Rev 19** — **C020: independence must be traced to the formula's source; the invariant certifies the OBJECT,
  never the CONVENTION.**
- **Rev 20** — **a `k·r` upper bound must be checked for an unused constraint that halves `k` (D036).**
- **Rev 21** — **DISPATCH HYGIENE: keep metadata edits out of numeric specs; state known environment noise.**
- **Rev 22** — **A CAVEAT IS AN ASSERTION AND NEEDS THE SAME VERIFICATION AS A RESULT.** **To claim "the
  calibres are mixed", back-infer a derived quantity from each candidate column and see which reproduces
  (M040).** **And over-conservatism is NOT the safe direction — it suppresses a correct conclusion, which costs
  more.**
- **Rev 23** — **"n larger ⇒ `eps_lo` non-decreasing" is an EXPECTATION, NOT a guarantee** for an estimator
  with an internal split and an adaptive cutoff (Michel). **Pair-by-pair it can fail (`35-49` decreased; `11-51`
  moved (that phrasing is RETRACTED -- `11-51`'s `n_b` changed 70x; only `n_a` was fixed).**
- **Rev 24** — **C014's topology is a STANDING fact, not a one-off incident: the remote tree and the local tree
  are separate, so "the file is not there" is a statement about WHICH TREE, and "the package does not exist"
  requires a literal `ImportError`.** **See TWO TREES.**
- **Rev 25 (NEW)** — **A NUMERICAL TIE BETWEEN TWO OBJECTS IS NOT CORROBORATION UNTIL A 2×2 IS COMPUTED.**
  **Agreement that holds only where each side uses its OWN convention is CANCELLATION (M041).** **Corollary:
  never read a binding side off a subset that was SELECTED on that same constraint.** **See Q1 vs Q2 and
  BINDING-SIDE.**
- **Rev 26 (NEW)** — **A DIRECTIONAL ARGUMENT BOUNDS A QUANTITY; IT DOES NOT PREDICT A THRESHOLD CROSSING when
  the margin is comparable to the estimator's noise.** **State a BRACKET, and do not attach a point prediction.**

## Key Decision Log
| ID | Summary | Related |
|----|---------|---------|
| **D037** | **Q1 gate CLOSED at 336/990 = 33.94%** (recovered pairs = 1, NOT the prefix `k`); **lower side is asymptotic by policy and is not tightened to answer the alpha question.** | E10 |
| **D036** | **Q2's upper-bound multiplier 31 is loose by 2×; the sharp sum-to-zero constant is 16.** | E9 |
| **D035** | The Q1 gate reduces to `335 + r` where `r ∈ {0..5}` (recovered pairs). | E3 |
| **D034** | **The 2× radius propagated through THREE specs, defeating implementation-level independence.** | E3, E9 |
| **D033** | **Q2's PASS condition "non-empty two-sided certificate" was VACUOUS**; replaced by `eps_hi < 0.5`. | E7, E9 |
| **D032** | Q1's two-sided claim is defensible at M=1: one object, both sides on it, 0 violations, prediction pre-registered and upheld. | E3, E7 |
| **D031** | **Correct E3's Q1 upper side to the repo reference radius (the runner dropped both 0.5's).** | E3 |
| **D030** | **SUPERSEDES D029's rationale wording**: the lower side is asymptotic by construction; "proven" is unavailable. | — |
| **D029** | **Replace the Q1 lower-side criterion `tv_hat > T(n)` with the direct `eps_lo > 0.05`.** | E3 |
| **D028** | **Q1 MVP: the absolute certified window is NOT empty; `comp(1) = 0.02` is REFUTED.** | E3 |
| **D027** | **C016: assert `eps_lo <= eps_hi` per row; a violation is a bug.** | E7 |
| **D025** | **Threshold 2,000 flows/service, shared by both questions.** | — |

### Open items flagged by review
- **ECH full text not retrieved** — `verified` = `false`.
- **`literature_map.yaml`'s `verification_level` restored but DISTILLATION NOT TRIGGERED.**
- **SNI→service mapping rule: unwritten and load-bearing.**
- **Whether `T(n)`'s `0.05` constant depends on α** — labelled, NOT assumed; **D037 forbids resolving it by
  tightening the lower side.**
- **Registry linkage is now 6/10: E10 was backfilled; E1/E3/E7/E8/E9_Q2v3 were already linked. E2/E4/E5/E6
  remain correctly `planned` because they never ran and are not gaps.**
- **E8's two artifacts (`masking_verification.json`, `masking_regime_sweep.json`) are UNREGISTERED.**
- **Vector-level distinguishability must be reported separately as a one-sided result.**
- **⚠️ UNRESOLVED**: (i) the masking-effect scope; (ii) **the Q1 runner's OTHER inlined formulas (`T(n)`'s
  `1.958`, the `(2M)^k`) — UNAUDITED**; (iii) **the `upper_side_formula` metadata is still WRONG on the server
  and needs its own edit** — deliberately kept OUT of numeric dispatches; (iv) whether the split excludes the
  69-flow 2024-05 fragment; (v) **why `35-49`'s `eps_lo` DECREASED as `n_a` grew 8x** (the phrasing about `11-51` moving "with identical n" is RETRACTED -- its `n_b` changed 70x) —
  mechanism not tested.

## Method decisions
### Upper bound
**THE AUTHORITY IS `src/eibo/statcore.py::tv_upper_bound` (406–411)**: **`radius_i = 0.5*sqrt(m/n_i) +
0.5*sqrt(2*log(2/alpha_law)/n_i)`.** **⚠️ The Q1 runner drops both 0.5's; the Q2 runner used `31r` where the
sum-to-zero constraint gives `16r`.** **`m` MUST MATCH THE OBJECT**: lattice-law MEAN parameterisation ⇒
**`m-1 = 31`**; **categorical symbol law over 32 cells ⇒ `m = 32`.**
### THE THREE RADIUS CONSTANTS — TWO ARE LEGITIMATELY DIFFERENT, NOT COMPETING
| constant /√n | applies to | status |
|---|---|---|
| **4.309** = `0.5·(√m + √(2 ln(2/α)))` | **Q1's one-hot categorical prefix symbols** | **correct** |
| **31.63** = `16·√(ln(2·31/α)/2)` | **Q2's mean of correlated 32-simplex vectors** | **correct** |
| **61.28** = `31·√(ln(2·31/α)/2)` | Q2 v3 as run | **SUPERSEDED — do not resurrect** |
**Q1 exploits one-hot independence; Q2 CANNOT** (its coordinates sum to zero by construction), so Q2 genuinely
requires the larger constant. **State the object WITH the constant, every time.**
### Lower bound — classifier-based
Michel, Näf, Meinshausen, arXiv 2005.06006 (2020) — **ASYMPTOTIC HPLB ESTIMATE, not a finite-sample
certificate.** `alpha/3` internally; **do NOT divide again.** numpy only. **Its input MUST be samples from the
SAME object the upper side bounds** — for a categorical symbol law, **one-hot single-symbol draws**. **⚠️ Its
value depends on the internal train/test split (`random_state=0`, `test_size=0.3`) and the adaptive cutoff, so
it is NOT monotone in n.**
### m: validity vs tightness
`m = (2M)^k` on a fixed a-priori grid is a legitimate **SUPERSET**. **The empirically realized support may never
be substituted for m.**

## Alphabet A_k
**`|R_k| = (2M)^k` where M is a pre-registered DESIGN CHOICE.** Client Initial datagrams padded to >= 1200 bytes
(RFC 9000 §14.1). **RFC 9000 §12.2 / RFC 9312 §2.2 give long-header packets a Length field ⇒ coalesced packets
ARE separable.** **⚠️ `|A_k|` must stay small relative to n.**

## CODE DEFECTS — TWO FIXED; THE SYNC RESOLVED; PLUS TWO CONSTANT-FACTOR RUNNER DEFECTS
1. `tests/write_report.py` — FIXED. 2. `src/eibo/__init__.py` eager import — FIXED.
**`denominator_symbol_law`: the SOURCE is correct; only OLD ARTIFACTS are stale.**
**⚠️ The Q1 runner inlines the upper radius and DROPS BOTH 0.5 FACTORS.**
**⚠️ The Q2 runner uses `31r` where `sum=0` forces `16r`.**
**✅ `evaluate_q1_absolute.py` takes `k` PER ROW** — it had silently scored any k=10 row with the k=5 alphabet
`(2M)^5`. **Tests 15/15 pass.**

## Dataset facts — DIRECT FILE READS ONLY
### Verified in the H5
`APP:int16` (10M/10M), `CATEGORY:int16`, `PPI` `('<i4',(3,30))`, `PPI_LEN:uint16`, four PHIST fields
`uint32 (8,)`, `QUIC_CLIENT_VERSION`, `QUIC_VERSION`, `QUIC_SNI`, `DST_COUNTRY`, `DST_ASN`, `TIME_FIRST`.
**sha256 `6b323c4c…10ab`; 3,544,625,537 bytes; 10,000,000 rows.** **TIME_FIRST span 2024-05-31T21:00:00+00:00 →
2025-05-31T21:00:00+00:00, 365 days, 360 daily tables.**
### Parquet differs — `APP`/`CATEGORY` ABSENT; June 2024 → 30 daily files, 11,850,145 rows.
### Service-count threshold — **DECIDED 2,000 (D025); 45 services; 53 without threshold (retired).**
### Corpus facts
- **QUICEXT-25** (Zenodo 17249078): CC BY 4.0, Open, no registration/DUA. 12 per-month ZIPs, **28.2 GB
  compressed**. Uniform **1:100**. Gaps: 31.10.2024, 11–14.12.2024, 15–16.3.2025.
- **QUIC22**: 102 service labels + 3 background = 105 `APP` classes. **Dynamic per-service sampling.**
- **Loader**: `cesnet-datazoo` (PyPI 0.2.0).
- **`2024-06.zip` expected 1,747,398,591 B, delivered exactly, sha256 `9277e2a2…`; the DIRECT FILE endpoint
  (`/files/<name>/content`) returned HTTP 200 + authoritative `Content-Length` while the RECORD/API endpoints
  returned 504** ⇒ **the failure is ENDPOINT-SPECIFIC, not a URL-type error.**
- **`cesnet-datazoo` is NOT installed**; `CesnetDataset.__init__(data_root, size='S')` takes `data_root` as a
  required positional and constructs its storage below it — **no library-default cache dir, no cache env var.**
### Source index (`literature_map.yaml`)
Graded `verification_level`: `verified-abstract` 12 / `verified-fulltext` 4 / `unverified` 4.
**WRITER TRAP**: `add_to_literature_map` **DROPS `verification_level` and `notes`**.

## DATA TRANSFER — PAUSED (approved; not on the MVP critical path)
> **0 of 11 months transferred; endpoint-specific failure; unkillable via both paths (cwd attribution); PAUSED
> by decision.**
### CONFIRMED from the log
- **`PART_RETRY` = 1764, `PART_OK` = 0**; **`504` × 1764 only**; grep for `200`/`206`/`Content-Range` produced NO
  output. **First retry already 504** (14:35:29). Span **00:59:07**.
- **356 distinct parts — ALL repeated 4–5×.** **Backoff ALREADY RAN**: `sleep_s` 1/2/4/8/16 ×356/340.
- `2024-06.zip` 1,747,398,591 B; `2024-07.zip` 4,973,604 B; `2024-08.zip` 0 B; **four** empty `.parts/` dirs.
- **507 GB free, 565 GiB RAM.** PID 512584 alive, `Ssl`, `futex_wait_queue_me`.
- **⚠️ The logged RETRY cadence (median interval 2.0 s) is NOT a tight loop** — it is consistent with the
  implemented backoff plus gateway latency. **Reporting it as a tight loop was WRONG (correction 58).**
### ⚖️ Cannot be killed — fence correct and moot
`live_cwd: /root` vs `project_scope: /root/eibo`. **C011.** **⚠️ This is the TWO TREES topology showing up as an
ownership-fence mismatch.**
### Environment reality
**Python at `/root/miniconda3/bin/python3`** (symlink → `python3.12`); **`/opt/conda/bin/` does NOT exist.**
**⚠️ `detect_image` returns `SSH error: exit code 1` as ROUTINE NOISE** — it has done so for E8, E7, E8b, E3,
E7b, E9 and E10 and the 16r retry, **all of which completed normally. It is never a blocker.**
### Working recipe
- **~300 s gateway ceiling** — every long run hit a variant; **checkpointed/atomic writes survive.**
- **cwd must be inside the project** (C011).
### Capacity probe rule
`/dev/md0` is mounted at both `/init` (150 MB quota view) and `/root/autodl-tmp` (550 GB). **A bare `df -h` gives
no useful information.**
### Artifact-status rule
- `status=failed` ≠ artifact invalid; **a worker can produce a full result while its artifact is unreadable
  here**; **`running` ≠ final.**

## THE RECURRING INFERENCE ERROR — one pattern, sixty-two instances
**A single failed, narrow, or proxy probe gets generalized into a statement about the system.**
1–59 as before. 60. **"The local tree and the remote tree are the same / a write on one appears on the other"**
— **refuted by C014 in BOTH directions; see TWO TREES.** 61. **"Q1/Q2 agreeing at 1.006 corroborates the
result"** — **a cancellation; the 2×2 shows the statistics differ 2.7× while the constants differ 7.34×.**
62. **"The point prediction 340 will hold"** — **a directional argument about a bound was treated as a
prediction of a threshold crossing; measured 336.**
**Rule: verify with the path that can actually observe it, and state what was measured, from where, over what
window.**
**Corollary: scope certainty to the layer it rests on; a function of parameters must never be reported as an
absolute; check what a derived number MEASURES before it may change a conclusion; never report an action as
complete before it is complete; never assert an external capability without verifying it; before asserting
something CANNOT be observed, look for a same-class counterexample; never let an aggregate adjudicate between
hypotheses it cannot distinguish; to locate which side a fault is on, test a CONTROL; when re-checking a number,
ask whether the check is a re-run or an implementation from the definition; never let a raw hostname stand in for
a validated label; prefer known-where observations over unknown-where agreements; NEVER transfer a behaviour from
one script to another; ALWAYS ask whether a near-null OR near-maximal result comes from the claimed mechanism or
from SATURATION; NEVER let a tooling/availability failure become a claim about existence; NEVER let prose about an
environment stand in for a runnable command; CHECK INTERNAL CONSISTENCY BETWEEN THE TWO SIDES OF ONE CRITERION;
DISTINGUISH "missing" FROM "empty"; CHECK WHETHER A CONTROL DESIGN THAT MADE A COMPARISON "FAIR" ALSO MADE IT
INCAPABLE OF DETECTING ANYTHING; TREAT A MATHEMATICALLY IMPOSSIBLE PAIR OF REPORTED NUMBERS AS A MEASUREMENT BUG;
DO NOT INFER THAT A TARGET PATH EXISTS MERELY BECAUSE IT IS THE CONVENTIONAL ONE; NEVER LET A POINT ESTIMATE BE
DESCRIBED BY THE WORD "PROVEN"; A COUNT OF BUCKETS IS NOT A DISTRIBUTION OVER THEM; NEVER RESTATE A FORMULA THE
REPO IMPLEMENTS; A CLEAN CONSTANT-FACTOR RATIO IS A MISSING-FACTOR SIGNATURE; INDEPENDENCE THAT SHARES A SPEC
SHARES ITS ERRORS; A THRESHOLD'S NAME IS NOT ITS THRESHOLD; CORPUS-LEVEL FEASIBILITY IS NOT PER-UNIT FEASIBILITY;
A CRITERION THAT ANY WIDE INTERVAL SATISFIES TESTS NOTHING; AN INVARIANT CERTIFIES THE OBJECT, NOT THE
CONVENTION; "UNCOMPUTABLE" IS ITSELF A CLAIM THAT NEEDS CHECKING; CHECK WHETHER AN UNUSED CONSTRAINT HALVES YOUR
CONSTANT; AN UNREQUESTED STEP'S FAILURE IS NOT YOUR TASK'S BLOCKER; A CAVEAT IS AN ASSERTION; BACK-INFER THE
DERIVED QUANTITY TO SETTLE A CALIBRE; AN EXPECTATION ABOUT A BOUND IS NOT A GUARANTEE ABOUT AN ESTIMATOR; WHICH
TREE THE FILE IS IN DECIDES WHETHER IT EXISTS AT ALL; A TIE BETWEEN TWO OBJECTS IS NOT CORROBORATION UNTIL THE
2×2 IS COMPUTED; and NEVER READ A BINDING SIDE OFF A SUBSET SELECTED ON THAT SAME CONSTRAINT.**

## Environment facts
- Server `111`: 1x RTX 5090 D (32 GB), account `root`. `execution.project_path` = `/root/eibo`.
- Python at `/root/miniconda3/bin/python3` (absolute; not on the default PATH).

## Corrections ledger (do not regress)
1. i.i.d. result is in **§4.1** of arXiv 2602.14055, not §5.1.
2. The brief **inverts** the lower-bound basis: correct basis is **ref 4 (arXiv 2005.06006)**.
3. "h5 lacks the environment axes" was **wrong**.
4. An earlier capacity blocker was **wrong** — a `df` probe echoing only `/`.
5. The coalescing quotient is **not** protocol-forced.
6. The divisibility route is **not** assumption-free.
7. "Close capacity with raw `df -h`" would have **reproduced** the capacity error.
8. The `k_cert ∈ [5,15]` window was **wrong**. `k_cert >= 5`, no upper bound.
9. **"PHIST = 8×8×2 = 128 cells" was WRONG** — 32 coordinates.
10. **"The server has no Python" was WRONG.**
11. **"Background transfer is forbidden by policy" was WRONG.**
12. **"0.083 MB/s ⇒ ~94 hours" was WRONG.** 13. **"~2.4 MB/s ⇒ ~3.2 hours" was ALSO WRONG.**
14. **"The XS transfer is still running and will finish shortly" was WRONG.**
15. **"No rung satisfies both conjuncts at k=5, so Q1 tends to fail" was WRONG** — n=1e4 artefact.
16. **`tests/write_report.py`** — now FIXED. 17. **"Run the rerun locally with Bash" was WRONG.**
18. **"Compression helps only the upper side" was WRONG.**
19. **"Local runs are impossible without scipy" was the wrong diagnosis.**
20. **"M=4 covers the full latent range at n=2e5" was WRONG.** 21. **"M=1 has the widest window" was WRONG.**
22. **"`eps_lo ≡ 0` at M=1" was WRONG.** 23. **"The constant term is exactly 0.05" was over-strong.**
24. **"The XS process is stopped" was not establishable.** 25. **A task spec's opening step is load-bearing.**
26. **"Add the instruction to the running worker's next turn" was WRONG AS A MECHANISM.**
27. **"The month files are missing / raw is empty" was WRONG.**
28. **"The k≤30 coverage bias affects both chains" was WRONG — Q1 ONLY.**
29. **"Swapping in a tighter lower bound rescues M=1/M=2" was WRONG.**
30. **A still-running worker's artifact may be PROVISIONAL.**
31. **"`generated_at` == worker start ⇒ pre-correction run" was WRONG.**
32. **PPI padding contamination was not previously handled.**
33. **"M=8/16 never certify" was WRONG as an absolute.** 34. **"`T(n)` is assumption-free" was WRONG.**
35. **A scalar `comp(M)` criterion was insufficient.**
36. **"The measured ratio can substitute for `comp(M)`" was WRONG.**
37. **"The assumed compression ordering is reversed" was WRONG.**
38. **"M=1 INFEASIBLE" downgraded to UNVALIDATED — and later REFUTED outright (D028).**
39. **The divisibility joint fractions are about the SYNTHETIC ensemble.**
40. **"I cannot read container-root artifacts"** — premature.
41. **"The 0.571 ratio is a LOWER bound" was WRONG.**
42. **Declaring the ratio unusable then using it in the same turn was self-contradictory.**
43. **"Padding is directionally the MOST DANGEROUS" was WRONG on the gate quantity.**
44. **"M=1/M=2 are infeasible" must be re-judged on the ABSOLUTE quantity.**
45. **"The months are stalled" was an INACCURATE diagnosis.**
46. **The failure is NOT a URL-type error.**
47. **The attribution fence must NOT be relaxed or escalated** — and it is **moot**.
48. **Container-root cwd (`/root` vs scope `/root/eibo`) is the CONFIRMED attribution mismatch.**
49. **An action must not be reported as complete before it is complete.**
50. **"Parquet has a service label" was WRONG — `APP`/`CATEGORY` are H5-ONLY.**
51. **Parquet Step-0 is `not_measurable`** — route-scoped.
52. **`BadZipFile` does NOT prove the bytes are garbage** — check `PK\x03\x04`.
53. **"The endpoint is consistently broken" was WRONG.**
54. **"The month ZIPs are available from DataZoo"** — **REFUTED.**
55. **"Add exponential backoff" was a fix for something already implemented.**
56. **"The container-root path fix solved visibility" was a no-op.**
57. **Within-run vs across-day failure must be stated separately.**
58. **"Aggregate median interval 2.0 s ⇒ tight retry loop" was WRONG.**
59. **"Container-root writes sync to the shared tree" is NOT established.**
60. **A worker can produce a full result while its artifact is unreadable here.**
61. **"Our concurrency causes the 504s" was WRONG.**
62. **"The month fetch is on the MVP critical path" was WRONG.**
63. **A short-window `stat` pair is not the durable progress probe** — `.parts` `file_count` is.
64. **"Container-root writes sync" was WITHDRAWN.**
65. **Citing a path-carrying artifact as evidence of syncing was WRONG.**
66. **The `compression_ratio` denominator identity is CONFIRMED by code** (line 566).
67. **PPI's third channel is timing, and its exclusion must be DECLARED.**
68. **`T(n)` = 0.0659/0.0550/0.0522/0.0511 and `c ∈ [2.239, 2.259]` are VOID.** Corrected:
    **0.0639/0.0544/0.0520/0.0510, `c ≈ 1.958`** — **independently validated vs exact CP to ~3e-7.**
69. **"Independently reproduced the `T(n)` numbers ⇒ confirmed" was WRONG.**
70. **"The `T(n)` numbers were out-of-sample validated" is WITHDRAWN.**
71. **The recorded upper-side radius constant 2.7162 is UNDER-SPLIT** ⇒ **2.9604**; fixed (M028).
72. **A "count table" is NOT a symbol-count vector** — **beyond M=2 it is INFEASIBLE.**
73. **The count table does NOT cover the `eps_lo` or `eps_hi` distributions.**
74. **The h5 is on the training server, not on the Director's side.**
75. **"The two Q2 environment axes cannot be computed from the XS h5" was WRONG.**
76. **"Environment axes exist only in Parquet" is WRONG.**
77. **The old Parquet occupancy result keyed on RAW SNI is DISCARDED.**
78. **"Parquet-first" requires a validated SNI→service mapping.**
79. **The audited h5 sits under another project's path — citations must use OUR verified copy.**
80. **The XS readout script's output paths were fixed ⇒ do NOT pass `--out`.**
81. **The `3` is RESOLVED.**
82. **The script consumes ONLY direction + size.**
83. **"A success window is a property of the endpoint" is WRONG.**
84. **"Three artifacts prove container-root writes sync" is REFUTED — AND the data-disk artifact path DOES NOT
    EXIST.**
85. **`step0_masking`'s `masked_vs_unmasked_k30_tv` was `None`** — a PLACEHOLDER.
86. **"THE k=30 MASKED-VS-UNMASKED DIFFERENCE IS STRUCTURALLY IDENTICALLY ZERO" IS WRONG AS STATED.**
87. **The "unmasked" arm in E8 is MISLABELED.**
88. **"The imported masking helper is the one that ran" is NOT established.**
89. **A behaviour observed in one script must NEVER be transferred to another script.**
90. **`src/eibo` WAS missing remotely** ⇒ the lower-bound side was blocked on a code sync. **RESOLVED.**
91. **E8: all-zero padding over `3,805,365` slots; k=5 post-mask 990/990; BOTH layers verified.**
92. **Q2's zero-TV sanity check is POSITIVE: `68.29%` (941/1378).**
93. **"Q2 is likely EASIER than Q1" was UNSUPPORTED.**
94. **E3's dispatch was REFUSED once and DISPATCHED CLEANLY the next time, same content** ⇒ **INTERMITTENT
    guard.**
95. **"The method does not exist" was actually "the remote tree lacked `src/`" — and the directory EXISTED but was
    EMPTY.**
96. **`denominator_symbol_law`: the SOURCE is correct; only OLD ARTIFACTS are stale.**
97. **The threshold is DECIDED at 2,000 (D025); the 53-service variant is RETIRED.**
98. **Small services are STRUCTURALLY INFEASIBLE.**
99. **"The k=30 difference is small ⇒ masking is optional" is BANNED.**
100. **SECTIONS HAVE BEEN DROPPED BY FULL-FILE REWRITES (thrice).**
101. **PROSE ABOUT AN ENVIRONMENT IS NOT A COMMAND.**
102. **`tail_training_logs` reads REMOTE training logs, not local worker logs.**
103. **A repeated `last_text` with GROWING `event_count`/log size may mean mid-turn, not stuck.**
104. **The Director APPROVED pausing the month acquisition and running the MVP on the h5.**
105. **GPU idle is a STANDING state of this session** — **do not invent a placeholder experiment.**
106. **The two sides of one criterion must declare the SAME confidence level** (M028).
107. **THE COUNT-TABLE SPEC IS FINALISED; E3 delivered it, validated.**
108. **E7b's `eps_lo` median 0.859 with 2/990 non-empty is FEATURE-SPACE SATURATION — and an object-mismatch
     defect.**
109. **The 7 `eps_hi > 1` pairs are RETRACTED to UNDETERMINED.**
110. **A running worker cannot be amended.**
111. **MY SPEC MADE E8b's MASKING COMPARISON A STRUCTURAL NO-OP.**
112. **MY GATE DEFINITION WAS WRONG** — the upper side is **`eps_hi < 0.5`**; **E3's worker caught it.**
113. **E1: STEP-0 GATE PASSES on the XS subset** — **39 two-axis / 36 full-crossing.** **⚠️ NOT closed.**
114. **"TIME_FIRST on a single file ⇒ daily-only split" was WRONG.**
115. **`DST_ASN` collinearity is HIGH** — 27/45 ≈ 60% ⇒ **audit confound.**
116. **The compression-ratio readout's approach to 1 in its upper rungs is SATURATION.**
117. **Citing a line number from an earlier revision of `memory.md` cites a stale document.**
118. **E3's STRUCTURE: the UPPER side binds at every rung; the feasible set shrinks monotonically in M; M=1 is
     the only feasible rung.**
119. **THE Q2 TWO-SIDED RESULT IS VOID in v1/v2** ⇒ **RETRACTED**; **v3 aligns the object.**
120. **MY SATURATION LABEL THRESHOLD (0.5) WAS ARBITRARY AND UNFOUNDED.**
121. **`lower_side_fraction` IS NOT A PROVEN LOWER BOUND**; **criterion becomes `eps_lo > 0.05`.**
122. **THE DATA-DISK ARTIFACTS PATH DOES NOT EXIST** ⇒ **non-issue.**
123. **`register_artifact(server=..., remote_path=...)` PULLS A SERVER FILE INTO THE LOCAL TREE.**
124. **AN INSTRUCTION DESCRIBED AS "JUST SENT" MAY SIMPLY BE LATER IN MY QUEUE.**
125. **CROSS-FIELD CONSISTENCY IS EARLIER-ACTING THAN THE PER-ROW INVARIANT** (C017 before C016).
126. **THE DESIGN-TIME `comp(1) = 0.02 < T(n)` PREDICTION IS REFUTED (D028).**
127. **THE STRONG SENTENCE IS NOW MEASURED: `336/990 = 0.3394`**, describing the ASYMMETRY.
128. **"THE BAND IS PROVEN" IS BANNED IN ALL DOCUMENTS** (Rev 16 / D030).
129. **E3b: THE k=10 PREDICTION HOLDS** — only M=1 has any certificate.
130. **"13 distinct months" IS MISLEADING** — **12 full months plus a 69-flow boundary fragment.**
131. **THE UPPER RADIUS IS 2X THE REFERENCE (M037/D031).**
132. **The error direction is NOT uniformly conservative.**
133. **INDEPENDENCE SHARING A SPEC SHARES ITS ERRORS (C020).**
134. **READING AN ARTIFACT WITH A WRONG FIELD NAME SILENTLY YIELDS A DEFAULT (0).**
135. **THE 2X CORRECTION SPEC WAS REFUSED TWICE** (and passed once the metadata step was removed).
136. **THE Q1 RUNNER'S OTHER INLINED FORMULAS ARE UNAUDITED.**
137. **`eps_lo > 0.05` IS 985/990 UNDER THE CAP AND 986/990 AT FULL n.** The full-n count covers all 990
     pairs with no assumed remainder.
138. **Q2's PASS CRITERION WAS EMPTY** ⇒ **changed to `eps_hi < 0.5` (D033/C019).**
139. **Q2 v3's 31r constant is 2× too large — the correct sum-to-zero coefficient is 16 (D036).**
140. **"Q1 IS THE STRONGER CERTIFIED OBJECT" IS OVERTURNED (D036)** — at 16r Q2 reaches **342/990**, level with
     Q1's **340/990**.
141. **CORPUS-LEVEL FEASIBILITY IS NOT PER-SERVICE FEASIBILITY.**
142. **DENSE-COUNTS OUTPUT IS CAPPED — no M>=2 dense counts.**
143. **The 519 MB + 95 MB intermediate pair on the 30 GB container root** — the cap is the remedy.
144. **"The gate intersection is uncomputable" was WRONG — it is 5/5.**
145. **`340` IS A MEASUREMENT** and was **independently reconfirmed by E10** against the old 292 in one run.
146. **C016 CERTIFIES THE OBJECT, NEVER THE CONVENTION** (re-confirmed 0/990 on the corrected radius, weakly).
147. **THE WEISSMAN `935/990` FORM IS UNPROVEN FOR THIS ESTIMATOR AND MUST NOT BE QUOTED.**
148. **"The 16r dispatch is blocked" was WRONG** — it had succeeded.
149. **A WORKER'S UNREQUESTED `detect_image` PROBE STOPPED A NUMERIC TASK.** **State known noise in every spec.**
150. **KNOWN-ENVIRONMENT-NOISE MUST BE WRITTEN INTO SPECS.**
151. **THE GATE IS `336/990 = 0.3394`** — E10 measured **recovered pairs = 1**; the point prediction that all 5
     recover **FAILED**.
152. **`39-44` DID NOT MOVE** because its full n (4,624 / 5,741) was ALREADY below the 20k cap — **nothing to
     recover.**
153. **`35-49`'S `eps_lo` DECREASED with more data** (0.043732 → 0.042725) — **the Michel estimator is not
     monotone in n**; mechanism untested.
154. **MY "Q2/Q1 MIXES n CALIBRES" CAVEAT WAS FALSE (M040)** — Q2's upper side uses full n; **and
     over-conservatism suppressed a correct conclusion.**
155. **A ROW CARRYING BOTH A SAMPLE-COUNT AND A DERIVED-QUANTITY COLUMN SELF-DOCUMENTS ITS CALIBRES** —
     back-infer the derived quantity from each candidate column.
156. **A CAVEAT IS AN ASSERTION** and needs the same verification as a result (Rev 22).
157. **THE 16r `342/990` IS NOW EMITTED BY A RUN** — the "pending confirmation" reservation is discharged.
158. **"n larger ⇒ `eps_lo` non-decreasing" IS AN EXPECTATION, NOT A GUARANTEE** (Rev 23).
159. **THE TWO REMOTE TREES AND THE LOCAL TREE ARE SEPARATE** (C014/Rev 24) — **a remote edit is not pulled
     back, and "the file is not there" is a statement about WHICH TREE.**
160. **D037: THE LOWER SIDE IS ASYMPTOTIC AND IS NOT HELD TO A STRICT STANDARD** — the finite-sample strict side
     is the UPPER side.
161. **E10 WAS STUCK AT `RUNNING` WITH A COMPLETE RESULT** — closed to DONE. **A finished run does not always
     close itself; check for `conclusion` set with `completed_at` absent.**
162. **THE Q2/Q1 TIE IS A CANCELLATION, NOT A CROSS-CHECK (M041)** — the 2×2 shows the statistics differ 2.7×
     and the radius constants 7.34×; **the tie carries NO corroborative weight.**
163. **NEVER READ A BINDING SIDE OFF A SUBSET SELECTED ON THAT SAME CONSTRAINT (M040)** — corpus-wide the upper
     side removes 650 and the lower side 4.
164. **AN EXPLAINED 29% → 34% JUMP MUST BE PRESENTED AS AN `old → new` PAIR WITH THE CONVENTION NAMED** — an
     unexplained jump between artifacts reads as a DATA REVISION rather than a convention fix, **and this one
     moves in the project's favour** (so it is the one most likely to be read that way).
165. **THE POINT PREDICTION `340` FAILED; THE BRACKET `[335, 340]` SUCCEEDED** (measured 336) ⇒ **state a
     bracket; do not attach a point prediction.**
166. **`c`'s M028 provenance must be pinned**: `c` was recomputed under the `alpha/2`-per-law convention; the
     **void** `c ∈ [2.239, 2.259]` applied `alpha/4`. **The revision is PASS-FAVOURING ⇒ its justification must
     be convention-driven and stated, not left for a reader to notice.**
167. **E7 IS REGISTERED AS `failed`, NOT `negative`, DELIBERATELY** — it is an implementation/design defect, and
     recording it as negative would pollute later judgement.
168. **E8's two artifacts are UNREGISTERED; `masking_verification.json` is 92,947 B `f7cbab76…` and
     `masking_regime_sweep.json` is 832,121 B `453ac98d…`.** **OWED.**
169. **THE ROADMAP'S "Registry is EMPTY: 0 experiments" IS STALE** — the registry holds 6 and the coverage
     view is 6/10. **Five entries were already linked (E1→E1, E3→E3, E7→E7, E8→E8, E9→E9_Q2v3); E10 was the
     only real gap and is now linked. E2/E4/E5/E6 never ran, are not gaps, and must stay `planned` rather than
     receive fabricated registry provenance.**

219. **★★★ THE EARLIER Q1 GATE RECORD WAS HALF-MEASURED (M042) — SUPERSEDED.** The upper side was over ALL
     990 pairs, while the earlier lower-side record covered only the 5 TARGETED pairs; its 282 capped survivors
     were **ASSUMED** to stay above 0.05 at full n. That historical assumption is now resolved by
     `q1_lower_side_full_n.json`, which recomputed the LOWER side at full n for ALL 990 pairs with the cap removed:
     `measured_full_n_pair_count = 990`, `assumed_pair_count = 0`, lower-side passes = 986/990.
     **The earlier range `[333, 336]` is SUPERSEDED** because it was valid only while the lower side was
     half-measured; with no assumed remainder, the range has no basis. **The current measured gate is 336.**
     The earlier five-pair deltas remain useful sensitivity evidence, including the WRONG-DIRECTION movement of
     35-49, but they are not a substitute for the all-pair measurement.
220. **★ CORRECT ARITHMETIC: 986.** Capped lower-side passes = 985/990 (failures 11-51, 21-23, 27-29, 35-49,
     39-44); exactly ONE pair (21-23) recovered at full n, so **985 + 1 = 986**; four failures ⇒ gate
     **340 − 4 = 336**. The withdrawn total had no accounting. Note **39-44 was never capped** (full n
     4,624/5,741 < the limit), which is why it is bit-identical across runs -- a useful instance of "no change"
     meaning "never bound".
221. **A RUN MARKED "CLOSED" MAY NOT BE CLOSED IN ITS OWN RECORD.** E10 carried `conclusion: success` but sat at
     `status: RUNNING` with `completed_at` absent. **A finished run does not always close itself** -- check for
     a set `conclusion` alongside a missing `completed_at`. (Companion to the earlier "don't leave a status
     claiming work continues" and "don't report an action complete before it is".)

222. **★ A BLANKET NEGATIVE ABOUT FILE CONTENTS MUST BE RE-VERIFIED AT THE MOMENT IT IS MADE (M043).** A report
     claimed "every `registry_id` in experiment_plan.yaml is still NULL, so the plan and registry are unlinked
     and coverage reads 0/8." **VERIFIED FALSE: 5 of 10 entries already carry a `registry_id`** (E1->E1, E3->E3,
     E7->E7, E8->E8, E9->E9_Q2v3), and the registry holds 6 experiments. **The only genuine gap was E10, and it
     is now linked (backfilled); the coverage view is 6/10.**
     **=> Two bad outcomes, both live: (a) wasted work re-doing what is done; (b) WORSE -- if read as a mandate
     to "link everything", it would FABRICATE registry entries for E2/E4/E5/E6, which have NEVER RUN.**
     **=> A blanket "all X are null/missing" is easier to state than the specific scope and is almost always
     wrong. Report the specific entries affected, and name which ones CANNOT be affected.**
223. **★ NOT EVERY NULL IS A GAP -- SOME NULLS ARE CORRECT.** `E2/E4/E5/E6` have `registry_id: null` because they
     have never run; there is no registry entry to point at. **Linking them would be fabricating provenance for
     experiments never performed.** **=> Distinguish "unlinked but should be linked" from "unlinked because it
     does not exist yet" before any backfill task.**
224. **★ "COMPLETED BUT ITS RECORD DID NOT CLOSE" pairs with "reported as still running": both are STALE-STATE
     COLLAPSES.** E10 had `conclusion: success` with `completed_at` absent and sat at `status: RUNNING`; earlier a
     reviewer read an artifact mid-flight (863 B, live PID) and called the job in progress when it had finished
     (21,840 B). **=> In BOTH directions, read the terminal event AND the artifact's final size before asserting
     run state. A point-in-time read is not a state.**

225. **★ THE WITHDRAWN TOTAL = `985 - 1`: THE SIGN OF THE DELTA WAS FLIPPED.** The corrected lower-side count
     is **986** (capped passes 985; exactly ONE of the five capped failures, 21-23, RECOVERED at full n, so
     985 + 1 = 986; four failed => gate 340 - 4 = 336). **The withdrawn total was the capped total MINUS the
     recovered pair -- i.e. the one improvement was counted as a loss.** Reverse-engineering a wrong number to its
     generating expression is worth the minute: it converts "this number is wrong" into "here is the operation that
     produced it", which is what prevents the same slip recurring. **=> When a number reconciles with nothing, try
     to DERIVE it from the neighbouring quantities under each plausible (mis)operation before asking for a recount.**
226. **★★ A PREDICTION IN THE `conclusion` FIELD PROPAGATES INTO EVERY GENERATED SUMMARY.** E10's `hypothesis`
     was corrected to prediction-vs-measurement, but its `conclusion` STILL read "...should recover at FULL n ...
     hence the gate should land at 340/990" -- a FALSIFIED PREDICTION stated as the finding. **report.md's
     "Recent Conclusions" is generated FROM the conclusion field, so the project's headline summary was
     presenting a failed prediction as a result.** **=> Fixing the hypothesis does NOT fix the conclusion;
     check both, and check any artifact generated from them.** A `conclusion` field is the most-quoted field in
     the registry and must state the MEASUREMENT, never the expectation.

227. **★★ A REDUNDANT CONSTRAINT IN MY OWN SPEC BLOCKED A CORRECT WORKER.** The M041 correction task requires only
     the LOCAL artifacts -- I verified all five local copies match the remote sha256 bit-for-bit
     (`3c16c6be…`, `91b3f512…`, `aafe46af…`, `71a20309…`, `979c462e…`). **My spec demanded host-side measurement
     and atomic writes on `/root/eibo`, which the session could not do, so a worker that was RIGHT to refuse a
     local-only variant stopped instead.** **=> THIS IS THE THIRD TIME MY OWN SPEC CREATED THE BLOCK** (1: a
     metadata-edit step got a numeric task classified as writing and blocked twice; 2: a self-introduced
     environment probe treated as a prerequisite; 3: this one). **=> Before sending any spec, ask of EVERY
     constraint: does this task actually need it? A redundant constraint stops a correct worker, and the worker
     gets blamed.**
228. **★ THE 2x2 WAS HAND-DERIVED, SO I RECOMPUTED IT MYSELF RATHER THAN ACCEPT THE TRANSCRIPTION -- all four
     cells MATCH (340 / 81 / 935 / 342), and the constant ratio confirms at 7.341x.** **=> A hand-transcribed
     number must be re-derived before it enters an artifact, even when the transcriber is confident.**
229. **★ THE 935 CELL IS `invalid-for-Q2`, NOT A THIRD SYMMETRIC CONVENTION -- and this STRENGTHENS the finding.**
     Applying Q1's radius to Q2 **IS IDENTICALLY** applying the Weissman categorical form:
     `0.5*(sqrt(32) + sqrt(2 ln(2/0.025))) = 4.30863` **is** the Weissman constant. That bound was ALREADY
     refused as unproven for Q2's correlated-simplex-vector estimator (it yields 935/990 = 0.9444, matching the
     cell to the digit). **=> the most extreme cell of the 2x2 corresponds to a bound we have already ruled out,
     so the cancellation conclusion is strengthened, not weakened. A counterfactual table must label cells that
     are KNOWN-INVALID for one of the objects, or a reader will treat them as legitimate alternatives.**
230. **★ TWO ADJACENT NUMBERS FOR ONE SYSTEM MUST CARRY THEIR DIFFERENT DEFINITIONS INLINE.** `336/990` is the
     JOINT gate (`eps_lo > 0.05` AND `eps_hi < 0.5`, defined at k=5); `340/990` is the UPPER side alone. The
     4-pair gap is exactly the pairs that pass the upper side and fail the lower. **Both are correct; the
     labelling was not.** **=> whenever two figures for "the same" quantity appear, state the conjunction each
     one denotes, in the same sentence.**

231. **★★ "THE ARTIFACT HAS BEEN CORRECTED" MUST SAY WHICH TREE.** The M041 corrections were reported complete
     with new sha256s (`54e7931f…`, `2442e29e…`), but **the LOCAL copies were still the OLD bytes** (`3c16c6be…`
     3,283 B; `91b3f512…` 21,840 B) -- the edits went to `/root/eibo` on the server. **=> Reporting a new hash
     without naming the LOCATION lets the other tree keep being treated as authoritative**, which is exactly the
     two-trees failure this project has already suffered (C014). **State which tree is authoritative and record
     old->new hashes per tree in the manifest.**
232. **A BARE `verified: False` IN AN ARTIFACT IS WORSE THAN NO CHECK.** The worker's constant self-check flagged
     `c_Q2` as `verified: False`. **Computed: the expression is `31.629887…` and the literal is `31.6299` --
     a difference of 1.3e-5, pure six-significant-figure rounding.** The constant is FINE; the tolerance was too
     tight. **=> Either loosen the tolerance and define what `verified` means ("literal agrees with the
     expression at display precision"), or keep the flag AND print the difference so a reader can judge. An
     unexplained `False` reads as "this constant is broken" to everyone downstream.**
233. **★ VALIDATE THE ARTIFACT, NOT THE REPORT ABOUT IT.** The completion report was accurate in substance but
     the artifacts' local bytes had not changed; only re-hashing the files revealed it. **=> For any claimed
     write, verify the TARGET (hash/size/mtime), not the message.** A report describes intent; a hash describes
     a file.
234. **★ A `failed` STATUS ON A COMPLETED WORKER -- the fourth member of the "status contradicts fact" family.**
     This session has now seen: a run completed but stuck at RUNNING; an artifact mid-flight called "still
     running"; 5/10 registry links called "all null"; and a worker that did the work flagged `failed`.
     **=> Judge an outcome by its ARTIFACTS and self-checks, and close the status FROM the artifact. Never
     read state off a label in either direction.**

235. **★ DON'T INFER A FIELD NAME FROM RENDERED TEXT -- READ THE SCHEMA (M044).** I told the agent to rewrite
     E10's `conclusion` field into prose. **`conclusion` is a STRICT ENUM** (`failed|killed|negative|success`)
     and rejects prose outright. **The text I was looking at renders from `hypothesis`** -- verified by verbatim
     comparison of E3's registry hypothesis against report.md's corresponding line (identical). **The section is
     titled "Recent Conclusions", which is exactly what makes `conclusion` the natural but wrong reading.**
     => **Before prescribing a change to a named field, read its type/constraints from the live record. A
     rendered document is not a schema.**
236. **★★ A DOCUMENT WITH A MARKER-DELIMITED BLOCK PLUS A HAND-AUTHORED TAIL HAS TWO WRITERS.** `report.md` is:
     (a) `<!-- AUTO-FACTS-BEGIN -->…<!-- AUTO-FACTS-END -->`, regenerated by the facts tool; and
     (b) everything BELOW the END marker, which is the DIRECTOR'S zone and is **never auto-overwritten**.
     The stale "Recent Conclusions" lived in (b) => **no amount of regeneration would ever have touched it.**
     **I had told the agent to regenerate a section I own.** Fixed it by editing it directly.
     => **"The generated document did not refresh" must be diagnosed by identifying WHICH WRITER owns each
     section** before concluding a tool is broken or escalating for a regeneration.
237. **A THIRD WRITER-SIDE PATTERN, ALL MINE:** (1) I read a field name off rendered prose (M044);
     (2) I treated a two-writer document as wholly generated; (3) I prescribed an edit to an enum field.
     **=> A single instruction can carry several wrong assumptions at once; when one is corrected, re-examine
     the others in the same instruction rather than accepting the fix and moving on.**

238. **★★★ THE Q1 GATE RESTS ON ONE MEASURED BOUNDARY PAIR -- this outranks the lower-count arithmetic slip.**
     The gate is `340 - (5 - k)` with `k = 1`, so **336 exists because exactly ONE boundary pair (21-23) crosses
     0.05, and its capped value sat 0.0002 from the threshold** (capped `eps_lo` 0.049781366 vs full-n
     0.058780592). Had it not crossed, the gate would be **335**. **=> Report 336 WITH that sensitivity stated,
     not as a stable integer.** The earlier range `[333, 336]` is **SUPERSEDED** because it was an input range
     valid only while the lower side was half-measured; the full-n run measured all 990 pairs, so it has no basis.
     **The full-n run found 0 pairs within 0.005 and 3 pairs within 0.02 of the 0.05 line.**
239. **★ PER-PAIR DELTAS EXPOSE WHAT A MONOTONICITY STORY HIDES.** capped -> full n: 11-51 +0.010377,
     21-23 +0.008999, 27-29 +0.002054, **35-49 0.043732229 -> 0.042724656 (WRONG DIRECTION)**, **39-44
     0.000000**.
     - **35-49 moved the wrong way as n grew** => "a larger n gives a tighter lower bound" is a **statistical
       tendency, NOT a guarantee**.
     - **39-44 is bit-identical because its full n (4,624/5,741) is BELOW the cap** => **"no change" can mean
       "never bound", not "stable".** Two pairs, two different non-monotonic explanations -- neither is "the
       method is wrong", and neither is evidence of stability.
240. **★ A NOTE THAT PROMISES A FIELD WHICH DOES NOT EXIST IS WORSE THAN NO NOTE.** `tree_sync_note` said the
     post-edit hashes "are recorded in `tree_sync_sha256` below" -- **that key exists in NEITHER artifact.**
     Only `source_sha256` (the PRE-edit inputs) is present. **=> the claim "the two trees are now byte-identical"
     was UNVERIFIABLE as delivered, because its own evidence was missing.** **A provenance claim must carry the
     artifact it cites; a pointer is not evidence.**
241. **★ THE FORK, AND THE FIX: two corrected copies of one artifact is a provenance failure, not a merge.**
     A remote worker corrected the server copies; a later LOCAL-ONLY dispatch corrected the local copies, so
     the same two filenames denoted different bytes in the two trees -- the **second fork of this pair**, the
     first having been avoided only by a worker declining to edit locally. **=> One canonical tree per artifact,
     direction of sync stated IN the artifact, and before/after hashes per tree.** A `local_only` flag is a
     MITIGATION, not a substitute for a single source of truth.
242. **A SELF-CORRECTION TO CREDIT: the agent retracted its own report.md claim** -- it had said the file renders
     `conclusion` (wrong: it renders `hypothesis`) and then that the file was stale (wrong: a cached read).
     **It noticed that it had been applying the "a point-in-time read is not a state" rule to everyone's
     artifacts but not to its own read**, and closed the item itself.

243. **★★★ RESTORING FROM A SNAPSHOT CAN DESTROY NEWER WORK -- SILENTLY, BECAUSE THE RESTORE SUCCEEDS
     (M046).** After `findings.md` was destroyed by a full rewrite, it was restored from a persisted
     tool-result cache. **That snapshot PREDATED two sections appended in the interim**, so the restore
     discarded them -- while reporting "28 sections intact", which was **true of the snapshot and false of the
     live state.** Verified: `ONE BOUNDARY` and `M045` were 0 in the restored file and present in `memory.md`.
     **=> BEFORE restoring any file from a cache/snapshot, compare the live file's mtime/size against the
     snapshot's. If the live file is newer, MERGE the snapshot into it -- do not replace it.** **A restore
     recovers SOME state, not the CURRENT state**, and the loss is invisible precisely because the restore
     looks complete. **A "sections intact" count is evaluated against whatever was restored, so it cannot
     detect what the restore dropped.**
244. **★ THE FULL-REWRITE DEFECT IS NOW A FOUR-INSTANCE CLASS** (three `memory.md` section-drops, one
     `findings.md` whole-file loss). **`save_project_file` REPLACES the entire file.** For any long-lived note
     file: **READ first, then write back "existing content + addition".** The "grep the headers after every
     rewrite" discipline applies to **every** file written that way, not just `memory.md`. (C023)
245. **★ A COMPLETION CHECK MUST FAIL WHEN THE WORK IS INCOMPLETE -- AND MY OWN CHECK VIOLATED THAT.**
     I wrote `grep -c "NOT directly comparable"` intending to confirm a caveat had been REMOVED, but expecting
     a MATCH -- i.e. **my post-condition required the exact string I had just asked the worker to delete.**
     **One reversed check turned a fully successful worker into `failed`.** => **Delete => assert ABSENT.
     Replace => assert NEW-PRESENT and OLD-ABSENT as two separate checks, each with the correct direction.**
     **Before sending a spec, ask of every check: if the worker does exactly as asked, will this pass?**
     **A reversed check manufactures a false record AT CREATION**, unlike the other status defects in this
     session which decayed over time.

246. **★★★ THE GATE IS FULLY MEASURED: 336/990 (D038).** The full-n lower pass over **all 990 pairs** (cap removed,
     no fallback) returned **upper set 340** (990 rows recomputed) and **full-n lower set 986** => **gate = 336**.
     Its own `measured_vs_assumed` reports **measured 990 / assumed 0** => **the earlier "half-measured"
     qualification (M042) IS RESOLVED -- nothing is assumed any more.** The run independently reproduced the
     derived 986, and `changed_vs_capped` = **1** (only 21-23). **The 282 pairs previously flagged as "assumed"
     were directly measured.**
247. **★★★ THE RESIDUAL SENSITIVITY IS ONE MEASURED BOUNDARY PAIR, NOT AN ASSUMED-REMAINDER RANGE.** The gate is
     **336 because exactly ONE boundary pair (21-23) crosses 0.05, and its capped value sat 0.0002 from the threshold**
     (capped `eps_lo` 0.049781366 vs full-n 0.058780592). Had it not crossed, the gate would be **335**.
     **=> Report 336 WITH that sensitivity stated, not as a stable integer.** Pair (35,49) moved the WRONG direction
     as n grew (0.043732229 -> 0.042724656), so "larger n gives a tighter lower bound" is a statistical tendency,
     not a guarantee. Pair (39,44) is bit-identical because its full n (4624/5741) is BELOW the 20000 cap, so it was
     never capped: "no change" means **"never bound"**, NOT "stable". The full-n run found **0 pairs within 0.005**
     and **3 within 0.02** of the 0.05 line. The earlier range `[333, 336]` is **SUPERSEDED** because it was valid
     only while the lower side was half-measured; with all 990 lower rows measured and `assumed_pair_count = 0`,
     it has no basis.

248. **★★★ MVP PASSED -- project is in the RESEARCH phase (2026-09-14).** Both questions answered with FULLY
     MEASURED quantities: **Q1 gate 336/990 = 33.94%** (upper 340/990 finite-sample strict, lower 986/990
     asymptotic; `measured 990 / assumed 0`); **Q2 informative 342/990 = 34.55%** under the sharp sum-to-zero
     bound. Recorded in `docs/IDEA_BRIEF.md` (the append target) and the ROADMAP.
249. **THE MVP'S THREE STRUCTURAL FINDINGS:**
     (1) **the UPPER side binds at every rung** (removes 650 pairs; the lower removes 4 within the upper set) --
     the tension is "can a certificate EXIST", not "can services be told apart", which is the OPPOSITE axis from
     the design-time worry;
     (2) **M=1 is the ONLY viable rung** and saturation rises monotonically in M (0/0.105/0.239/0.336/0.391), so
     **a finer alphabet has LESS resolving power -- coarse-graining is necessary, not a concession**;
     (3) **Q1's 340 and Q2's 342 do NOT corroborate each other** (2x2: own radii 340/342; common radii 340 vs
     935, 81 vs 342; statistics differ 2.7x, constants 7.34x => cancellation).
250. **★ WHEN A TOOL REPORTS ONLY A GENERIC FAILURE, CHECK WHERE IT EXPECTS THE FILE -- NOT THE CONTENT.**
     `complete_mvp` returned "Failed to append MVP results to IDEA_BRIEF.md"; the cause was that I created
     `IDEA_BRIEF.md` at the PROJECT ROOT while the tool reads **`docs/IDEA_BRIEF.md`**. Moving the file fixed it
     with no content change. **=> A generic failure message names the OPERATION, not the reason; locate the
     tool's expected path before rewriting what you believe is wrong with the content.**

251. **★★★ SETTLED: THE GATE DOES HINGE ON ONE PAIR -- and BOTH of us were partly wrong.** Direct arithmetic
     from the artifacts (upper set = 340 at full n / reference radius, and the lower status of each of the five
     boundary pairs):
     | convention | lower-fails | of those IN the upper set | gate |
     |---|---|---|---|
     | **capped** | 5 | **5** | **340 - 5 = 335** |
     | **full-n (canonical)** | 4 | **4** | **340 - 4 = 336** |
     **All five pairs -- including (21,23) -- ARE in the upper set** (its `tv_hat+rad = 0.1395 < 0.5`).
     **=> MY STRUCTURAL CLAIM WAS RIGHT: had (21,23) not crossed, the gate would be 335.** It crosses only at
     full n, so the capped gate is 335 and the canonical gate is 336.
     **=> MY MARGIN WAS WRONG:** I quoted 0.0002, which is the CAPPED value's margin. The canonical (full-n)
     margin is **+0.008781**.
     **=> THE REVIEWER'S "INVARIANT TO THE CAP" CLAIM IS FALSE.** It built a table row "capped: gate 336" --
     **no artifact ever recorded a capped gate of 336.** The only capped figure is E3's
     `per_rung_both` M=1 = **289**, which is the `tv_hat > T(n)` **PROXY** gate, a DIFFERENT criterion. The
     reviewer assumed the capped gate equalled the full-n gate, then concluded from that assumption that the
     gate was cap-invariant -- **circular**.
     **=> THE HONEST STATEMENT: "the gate is 336 under the canonical (full-n) convention; it would be 335 under
     the capped convention; the difference is entirely pair (21,23) crossing 0.05. The nearest in-gate margin is
     +0.0088 and the nearest upper-only margin is -0.0073; nevertheless, report 336 with the measured sensitivity
     of that capped-to-full crossing, not as a stable integer."**
252. **★ A CONSTRUCTED TABLE ROW CAN BE INVISIBLE AS A CONSTRUCTION.** The reviewer's invariance argument rested
     on a cell that appears in no artifact. **=> When a comparison table is used to argue invariance, verify EACH
     CELL traces to a recorded value -- a row the arguer computed is not a measurement, and if it was derived by
     assuming the conclusion, the argument is circular.** (Companion to M044: don't infer a field from rendered
     text; here, don't infer a MEASUREMENT from an assumed equivalence.)

253. **★★★ STRUCTURAL FIX: THE AGENT MUST NOT WRITE `findings.md` (C024).** The tool description designates
     `findings.md` as **Director (PI) territory** ("PI role ... maintain findings.md"), YET it is in the
     `save_project_file` writable whitelist -- so the Agent could write it, and did, using **whole-file
     replacement**. **Five separate content losses have now come from full-file writes** (three `memory.md`
     section-drops, two `findings.md` overwrites) plus one cache restore that reverted newer writes (M046).
     **My sections were dropped AGAIN this round (33 -> 29 sections); I restored them to 30.**
     **=> Per-occurrence warnings do not work. The collision must be removed STRUCTURALLY:** Agent notes go to
     `memory.md`, `report.md`'s handover tail, and artifact fields -- **not** `findings.md`, which the Director
     maintains. Any `memory.md` write must be read-modify-write with the `## ` section count verified
     NON-DECREASING before and after, plus a `/tmp` backup.
254. **★ RESTORE-BEFORE-VERIFY IS THE RIGHT ORDER, AND I USED IT.** Before assuming the loss was material I
     checked the authorities: `memory.md` 246-252 present, `mistakes.yaml` M047 present, `decisions.yaml` D038
     present. **=> the casualty was narrative notes, not research content.** **Verify the substance survives in
     the durable store BEFORE characterising a note-file truncation as anything worse than record hygiene.**
255. **★ THE FULL-REWRITE FAMILY, COUNTED: five losses + one bad restore.** `memory.md` x3 (sections), findings.md
     x2 (whole file). Every one was a whole-file write where an append was intended. **The recurring lesson is
     not "be careful" but "remove the write path":** a cumulative log must not be reachable by a tool that
     replaces the file.

256. **★★ THE REVIEW RETRACTED ITS "CAP-INVARIANT" CLAIM; MY STRUCTURAL CONCLUSION STANDS -- and the two
     errors were the SAME DISEASE.** The review confirmed: the gate is NOT cap-invariant (**capped 340-5=335 /
     full-n 340-4=336**, all five boundary pairs in the upper set), and its premise ("the upper set changes with
     the cap") was false -- **`eps_hi` depends on `n_a`/`n_b`, not on the lower-side reservoir cap.** It asked
     that its Finding 4 be discarded.
     **=> SETTLED AND AGREED: gate = 336 canonical / 335 capped; the entire difference is pair (21,23).**
     **=> THE META-LESSON, on BOTH sides:** the review applied "verify against the artifact" to the workers'
     claims but **not to its own arithmetic**, and published an unverified derivation (its second such this
     session); I (M047) **retracted a correct conclusion on the strength of that unverified objection**.
     **=> ONE RULE COVERS BOTH: for ANY claim resting on derived arithmetic -- whoever makes it -- NAME the
     quantity, PULL it from the artifact, and only then draw the conclusion.**
257. **★ WHEN "RECORDING AN INCIDENT" WOULD ITSELF REPRODUCE THE INCIDENT, STOP RECORDING AND STORE THE
     CONCLUSION IN STABLE PLACES.** `findings.md` was restored twice more, and each restoration is itself a
     whole-file write -- the very operation that caused the loss. **=> the value of the note was already
     realised** (the conclusion lives in `findings.md`'s existing section AND in `memory.md` 246-255, M047,
     D038). Ordered the restoration worker stopped or limited to ONE append with `after == before` asserted.
     **=> A record whose upkeep costs more than it carries has stopped being a record.**
258. **★ IMPROVING THE NUMBERS REQUIRES ADDING A NUMBER, NOT RE-DERIVING A SETTLED ONE.** The gate is pinned
     (upper 340, lower 986, both full-n measured; gate 336). **The only unreported paper number is the
     VECTOR-LEVEL distinguishability** -- `TV(per-flow 32-vector law)`, the quantity one-hot discards to put
     both sides on ONE object. **It must be reported as a ONE-SIDED result: `TV(vector) >= TV(marginal)`, so it
     is a STRONGER claim, but the two are NOT interchangeable and it may not be presented as a better bound on
     Q1's or Q2's object.** Its vector-level median is 0.858537 (from the earlier run) vs the marginal median
     0.534945. Dispatched.

259. **★★ THIRD INSTANCE OF A SPEC NAMING A NONEXISTENT FIELD (M048).** I specced an assertion on
     `per_rung[*].gate_fraction`; **the real key is `gate_fraction_both`.** The worker reported the FAIL, listed
     the actual keys, and **refused to substitute -- so nothing was written.** Prior instances: (1)
     `tree_sync_note` citing a `tree_sync_sha256` key present in neither artifact; (2) the sensitivity worker
     told to edit `gate_is_half_measured` / `honest_interval`, which are **registry metrics, not artifact keys**.
     **=> PROCESS FIX (not "be careful"): any spec that names a field must PASTE THE FIELD INVENTORY READ FROM
     THE TARGET FILE. A recalled field name is a memory claim wearing a spec's clothing.** The real key list for
     `q1_absolute_summary.json`'s `per_rung[*]`: M, T_n_median, alphabet_cardinality, gate_fraction_both,
     gate_pairs_both, lower_side_fraction, lower_side_pairs, pairs, radius_median,
     saturation_fraction_tv_ge_0_99, saturation_label, upper_side_fraction, upper_side_pairs.
260. **★ ALL THREE FIELD-NAME FAILURES WERE CAUGHT BY THE WORKER REFUSING, AT A COST OF ONE WASTED DISPATCH --
     NOTHING WAS EVER WRITTEN WRONG.** **=> "Refuse an instruction that contradicts what you read" outperforms
     "write the instruction more correctly", because the former does not depend on me being right the first
     time.** Worth preserving as a deliberate property of the specs, not an accident.
261. **★ A CORRECTION SHOULD SUPERSEDE, NOT DELETE -- and the memory.md worker did exactly that.** The withdrawn
     total was rewritten as **`225. THE WITHDRAWN TOTAL = 985 - 1: THE SIGN OF THE DELTA WAS FLIPPED`** rather
     than removed. **65 sections / 1400 lines (non-decreasing), entries 246/251/252/253/256/258 all present,
     `/tmp/memory.md.bak` taken.** **=> "correct the old number" means MARK IT SUPERSEDED AND SAY WHY; deleting
     it destroys the reader's ability to tell that a change occurred.**

262. **★★ A CORRECTION SHOULD SPLIT THE FUSED CLAIMS, NOT ENDORSE EITHER WHOLESALE.** Two assertions had been
     fused in the boundary-pair text: **(a) STRUCTURAL** -- the gate's value depends on a single boundary pair
     and moves 335 <-> 336 with it (**TRUE, preserved**); **(b) SCALE** -- the pair sits ~2e-4 from the line
     (**drawn from the CAPPED eps_lo, a quantity the canonical gate does not use => RETRACTED**).
     **=> My own retraction was right on (a) and over-broad on the rest; and the review's earlier blanket
     endorsement of entry 238 was likewise over-broad, implicitly including (b).** **=> When correcting, ASK
     WHICH SUB-CLAIM is false -- a correction that endorses a whole paragraph re-imports the error it was
     meant to remove.**
263. **★ A BOUND THAT COMES FROM A THEOREM MUST CARRY THAT THEOREM'S ITEMWISE CHECK.** Per-pair
     `TV(vector) >= TV(marginal)` follows from DPI, so it MUST hold 990/990 -- **which makes it a
     self-failing OBJECT-MISMATCH DETECTOR.** My spec omitted it; the agent caught the omission.
     **=> Any time two quantities are related by a known inequality, the spec must include that inequality as
     a per-item assertion. It is not "one more check" -- it is the theory used as a falsifiable claim.**
     (This session already lost a full round to an object mismatch, which this check would have caught.)
264. **★ A SUMMARY ARTIFACT MUST NOT CARRY TWO CONVENTIONS WITHOUT A PER-ROW LABEL.** `q1_absolute_summary.json`
     now holds BOTH the 2x-radius `per_rung` values AND `_ref_radius` siblings. That is acceptable ONLY because
     a `radius_convention` field names which is which, and a `per_rung_note` distinguishes all THREE circulating
     M=1 figures -- **289 (proxy criterion + 2x radius; NOT the gate under any correct convention), 292
     (understated-radius upper, no proxy), 336 (canonical full-n gate).** **=> the note is the positive pattern:
     let the artifact explain itself where a confusion HAS ALREADY HAPPENED.**
265. **★ SCOPE A REASSURANCE TO THE CONVENTION IT HOLDS IN.** `gate_convention_sensitivity` ended "…so no single
     sample sits close to the line", while its own first clause supplies the counterexample (the gate is 335
     under the capped convention precisely BECAUSE a pair sat 2.19e-4 away there). **=> A reader stopping at the
     last clause concludes there is no boundary sensitivity at all -- the opposite of the field's purpose.**
     Fixed to "…so UNDER THE CANONICAL CONVENTION no sample sits close to the line; the convention-dependence is
     the separate matter described in the first clause." **Batched into the planned follow-up rather than opening
     a separate write.**

266. **★★★ RESEARCH PHASE LAUNCHED (post-MVP protocol executed in full).**
     (1) `paper_framing.md` written: target USENIX Security 2027 C2 (ddl 2027-01-26), **3 core claims**,
     story spine, venue-fit risks, and the explicit "what must never be written" section;
     (2) claims **registered as C1/C2/C3** (`register_claims(replace=True)`) -- the structured registration,
     not the framing prose, is what the progress page shows;
     (3) `experiment_plan.yaml` RESTRUCTURED to **X1-X11 bound to C1/C2/C3** with P0/P1/P2; P0 =
     X1 headline bracket table, X2 PHIST on the sharp 16r bound, **X3 the chain-rule-vs-i.i.d. test (the only
     experiment that can FALSIFY the framing)**, X4 the frontier as a function; **X6 divisibility lower bound
     is the retained mechanism-novelty track**;
     (4) **`dream_simulate(review_mode="full")` dispatched** (dream_20260913T222513260561) -- simulate before
     spending GPU; result arrives by injection, and does NOT gate P0;
     (5) ROADMAP rewritten to reference framing + plan (no hand-drawn matrix; `compute_coverage_matrix()`
     derives coverage live).
267. **★★ I COMMITTED THE EXACT ERROR I HAD WARNED THE AGENT AGAINST AN HOUR EARLIER (M049).** I gave four
     NEVER-RUN experiments `registry_id` values (E2/E4/E5/E6), so `compute_coverage_matrix()` reported them
     **orphaned** -- bound to registry entries that do not exist. **One round earlier I had instructed: "E2/E4/
     E5/E6 cannot be linked -- they have never run; linking them would fabricate registry entries for
     experiments never performed."** Fixed by clearing all four to null.
     **=> registry_id may cite ONLY an entry that EXISTS; a planned experiment has NO registry_id by
     definition. Before writing one, LIST the registry's actual ids.** The registry holds exactly
     E1, E3, E7, E8, E9_Q2v3, E10.
     **=> WHY IT IS EASY: I reused the old plan's ids (E1..E10) as if they were registry ids -- two different
     namespaces.** The next numbers in sequence (E2/E4/E5/E6) are the MOST likely to be invented.
     **=> SAME DISEASE AS M048: a recalled name wearing a confident-looking costume. Read the source of truth.**

268. **★★★ I WROTE A FALSE MECHANISM CLAIM INTO THE AUTHORITY FILE, AND THE CONTROL THAT REFUTES IT WAS IN THE
     SAME TABLE (M050).** The claim: *"`11-51` has IDENTICAL n on BOTH SIDES (13,049) yet its `eps_lo` moved
     +0.0104 ⇒ the movement is SEED NOISE, not an n effect."* **BOTH HALVES WRONG.**
     **(1) It was NOT identical.** Only `n_a` was unchanged; **`n_b` went 20,000 -> 1,399,495 (70x)**, confirmed
     by the held-out split `{3915, 6000}` -> `{3915, 419849}`. **So an n effect is NOT excluded, and +0.0104 is
     the EXPECTED direction.** I had read "n_a is the same" as "n is the same" -- collapsing a two-sided
     condition onto the one column I happened to be looking at.
     **(2) There is NO seed noise.** `39-44` had BOTH `n_a` and `n_b` unchanged and its `eps_lo` is **identical
     to the digit (delta = 0.000000000)** ⇒ **for fixed input the estimator is DETERMINISTIC** (`random_state=0`).
     **The other pairs moved because their INPUT changed.**
     **=> THE CONTROL WAS ALREADY IN THE ARTIFACT.** One pair with both inputs unchanged settles determinism
     immediately; I reached for "randomness" without looking at it.
     **=> RULES: (a) "conditions are identical" is a TWO-SIDED assertion -- verify `n_a` AND `n_b` separately
     before using it to exclude a cause; (b) before attributing a movement to randomness, CONFIRM THE ESTIMATOR
     IS NOT DETERMINISTIC. Randomness is the explanation of last resort, not the first.**
     **=> The genuine non-monotonicity evidence is `35-49` alone** (`eps_lo` FELL -0.0010 as `n_a` grew 8x,
     20,000 -> 159,842), and it is sufficient on its own. `11-51` (+0.0104, n_b 70x), `21-23` (+0.0090, n_a 9.4x)
     and `27-29` (+0.0021, n_a 6.9x) all ROSE with more data -- consistent with tightening.
     **WHERE IT MATTERED:** the false claim was load-bearing -- it was one of two "hard pieces of evidence"
     supporting the recorded lesson that "larger n ⇒ larger `eps_lo`" is a tendency not a guarantee, in the file
     every worker reads. Corrected in place with the original text preserved and marked RETRACTED, plus two
     downstream references.

269. **★★★ I WROTE C2'S CAUSAL EXPLANATION BACKWARDS, IN BOTH PARTS (M051).** C2 is the framing's
     "sharpest design result" and answers "why not a finer alphabet?" -- exactly the sentence a reviewer probes.
     **WRONG (a):** "a finer alphabet has LESS resolving power". **Measured `tv` medians at k=5 RISE monotonically
     with M: 0.5805 -> 0.8833 -> 0.9248 -> 0.9462 -> 0.9673.** **A finer alphabet resolves MORE.**
     **WRONG (b):** "M=1 has the LOWEST `k_cert`". **Computed at n=3.9e6, tv=0.30: M=1 -> 17, M=2 -> 8, M=4 -> 5,
     M=8 -> 4, M=16 -> 3.** **M=1 has the HIGHEST `k_cert`** -- which is precisely WHY it alone retains a
     certificate at k=10. The parenthetical contradicted C2's own conclusion.
     **=> THE CORRECT MECHANISM (and it is more interesting):** what fails is **CERTIFIABILITY, not resolution.**
     The certified floor is `(1-eps_hi)/2`, so an easily-distinguished pair has a SMALL floor; when
     `eps_hi = tv + radius > 0.5` the certificate is lost. **The coarse channel wins BECAUSE it resolves LESS,
     leaving pairs close enough to certify** -- the opposite direction from what I wrote.
     **=> WHY THE ERROR IS DANGEROUS: the conclusion was right and the REASON was inverted.** "Conclusion right,
     reason backwards" is harder to notice than being wrong outright, and here the reason was the load-bearing
     part (a reviewer plots tv against M and sees it immediately).
     **=> ROOT: I inferred the mechanism FROM THE FINDING'S DIRECTION ("coarser wins") instead of FROM THE
     MEASURED QUANTITY.** "Coarser wins" felt like it implied "coarser resolves more" -- backwards. I also carried
     the `k_cert` ordering from memory of an earlier discussion instead of recomputing.
270. **★★ C3'S WINDOW WAS UNFALSIFIABLE BY CONSTRUCTION -- corrected to the all-pairs design.** I had confined
     adjudication to "the k where two-sided brackets exist" = **{5, 10}**, i.e. TWO points, one resting on
     **11 pairs (1.1%)**. **A growth-RATE claim needs >=3 points to have leverage; with two points any concave
     curve fits.** Worse: the window was defined by **the object that dies first**, so "inconclusive" was not a
     possible outcome but the **predetermined** one -- **the opposite of X3's stated purpose ("the only
     experiment that can falsify the framing")**.
     **=> FIX: compute `D_k` over ALL 990 pairs across the full k range (5..30), and use the certified subset
     ONLY to validate the estimator.** The growth claim and the certification claim then rest on separate
     footing; many k-points for the rate, C1 untouched. **`D_k` is defined on the k-prefix law, so the
     certified subset was an unnecessary restriction.**
271. **★ TWO COMPONENTS OF THE ORIGINAL BRIEF WERE ABSENT FROM MY FIRST PLAN.** (a) **Detector validation** --
     the brief's falsifiable containment: pre-registered one-sided coverage on the INFORMATIVE-pair stratum
     (`eps_hi < 0.5`), binomial violation count, OSCR/FPR95, named baselines. **Without it the paper reports
     brackets but never tests them against a detector.** (b) **Good-Toulmin missing-service mass**, scoped as a
     DEPLOYMENT-SITE quantity with Eriksson-type intervals and a 1:100-sampling sensitivity analysis.
     **=> ADDED as X12 / X13.** **=> LESSON: check the new plan against the ORIGINAL BRIEF's step list before
     committing; a framing rewrite can silently drop load-bearing components.**
272. **★ A CONCERN MITIGATED ONLY BY PROSE IS UNCOVERED.** Added `framing_ref` to all 13 plan entries and an
     explicit "Anticipated Reviewer Concerns" table (RC1-RC7), so `compute_coverage_matrix()` can show whether
     each is carried by an EXPERIMENT. **RC3 (the asymptotic lower side) was prose-only and RC6/RC7 were absent
     entirely** -- both now bound (X12, X13).

273. **★ THE FIRST DREAM (FULL REVIEW) FAILED ON AN INFRASTRUCTURE ERROR, NOT A SCIENTIFIC ONE.** `dream_20260913T222513260561`
     died in **phase1**: *"LLM subprocess completed without a terminal event"* -- **zero stages completed, no review
     content produced.** **=> Re-dispatched once (dream_20260913T223952620684) with the trigger_reason recorded.**
     **=> A failed simulation is NOT a failed plan, and skipping it is NOT a pass:** the pre-GPU simulation exists to
     catch structural problems in framing+plan cheaply. **A retry is justified precisely because the failure is
     unrelated to the content being simulated** -- but do NOT retry indefinitely; if it fails again, note that the
     pre-GPU check is unavailable and proceed on the reviewed-by-hand framing.
274. **★ WHAT THE DREAM WOULD HAVE CAUGHT, I CAUGHT BY CHECKING THE MEASUREMENTS (M051):** C2's inverted mechanism
     (finer resolves MORE; the coarse rung has the HIGHEST `k_cert`) and C3's unfalsifiable-by-construction window
     ({5,10} = two points, one on 11 pairs). **=> Both were found by pulling the measured quantity rather than by
     reasoning from the finding's direction.** The Dream is a backstop, not the primary check.

275. **★★ I BATCHED A CHEAP FIX WITH A SLOW JOB TO AVOID A CONFLICT THAT DID NOT EXIST (M052).** I told the agent to
     write the four-file wording fix "in one write" together with the vector-level follow-up, reasoning that two
     writers on artifacts risk a fork. **Verified: ZERO overlap** -- the vector worker writes a **NEW** file
     (`q1_vector_level_one_sided_full_n.json`); the wording fix touches **four existing artifacts**.
     **=> the batching prevented nothing and its only effect was to bind a ~5-minute edit behind a ~9-hour job
     that had committed 0 rows in 36 minutes.** Decoupled on the spot.
     **=> RULE: before batching two edits "to avoid a write conflict", LIST THE TWO FILE SETS AND CONFIRM THE
     CONFLICT. A conflict-avoidance measure must be able to name the shared resource it protects.** I had been
     burned twice by genuine concurrent writers earlier in the session (the local/server fork; findings.md
     overwrites) and **over-applied that caution without checking the particular case.**
276. **★★ A LONG JOB'S PROGRESS PROBE IS "UNITS COMMITTED", NOT "IS THE LOG GROWING".** The vector-level run went
     ~36 minutes with **0 committed rows** while its log grew steadily -- because every retry lengthtens the log
     without persisting anything. **=> ask for the committed-unit count early; a growing log is consistent with
     zero progress, and the earlier that distinction is made, the cheaper it is.** The agent's own probe sequence
     (check the checkpoint to see WHICH row committed -> reduce batch size -> write a per-pair ledger) was correct
     each time; what lagged was the *visibility* of "0 rows done".
277. **★ NO ETA WITHOUT A STEADY-STATE WINDOW -- and the agent refused to invent one.** With zero successful batch
     commits, there is no throughput evidence, so the ETA is UNKNOWN and the event that makes it measurable is
     "the first per-pair ledger entry lands". The arithmetic caveat (8-10 pairs exceed 300s => ~8-10 h for 990
     pairs) was correctly labelled AN ESTIMATE FROM A TIMEOUT, NOT A MEASUREMENT -- and pair cost varies with
     service size across three orders of magnitude, so extrapolation from a non-stratified sample would be
     systematically optimistic. **=> if a pilot is needed, sample STRATIFIED BY n, never "the first 50 pairs".**

278. **★★ "THIS ID DOES NOT EXIST" MUST NAME WHICH FILE WAS SEARCHED (M053).** The agent asserted the X-series ids
     (X1/X3/X4/X8) are "not this project's", that there is "no X8 entry", and that it would **ignore** my
     priority note as a cross-project slip. **VERIFIED FALSE.** **This project has TWO namespaces:**
     | namespace | file | ids |
     |---|---|---|
     | **PLAN** | `experiment_plan.yaml` | **X1 … X13 (13 entries)** |
     | **RUN** | `registry.yaml` | E1, E3, E7, E8, E9_Q2v3, E10 (6 entries) |
     **X8 exists and IS the job the agent was running** (the vector-level one-sided result). **Acting on its own
     judgement would have led it to treat its OWN RUNNING TASK as nonexistent.**
     **=> The E->X renumbering I did this round was precisely intended to remove this confusion** (the old plan
     used E1..E10, colliding with the registry's E-series -- the root of M049). The renumbering succeeded and
     produced an unfamiliarity effect as a side effect.
     **=> RULE: an existence/non-existence claim is an assertion about a SPECIFIC SOURCE. Say which file you
     searched.** Same family as reading the schema only to the top level and checking artifacts but not the
     registry: **the coverage of the check was assumed wider, or aimed at the wrong place.**
279. **★ A RENUMBERING THAT REMOVES A COLLISION CREATES AN UNFAMILIARITY WINDOW.** Immediately after the ids
     change, a reader who has the OLD namespace in mind will report the NEW ids as foreign. **=> when
     renumbering or renaming, state the old->new mapping in the same breath, and expect at least one
     round of "that isn't ours" from anyone working from the previous namespace.**

280. **★ FOURTH INSTANCE OF "STATUS CONTRADICTS FACT": a worker labelled `failed` whose report shows every check
     OK.** The four-file wording fix self-reported: Step-0 assertions OK, four atomic replacements, four JSON
     parses OK, fragment verification `OLD absent / NEW present` OK. **I verified by sha256 instead of reading the
     label: all four post-edit hashes match its report exactly** (`cec89fde…`, `0b654e84…`, `b959863a…`,
     `9fc9e17e…`), and the corrected clause appears once in each while the old clause appears zero times.
     **=> FOUR members now: (1) a run completed but stuck at RUNNING; (2) an artifact mid-flight called "still
     running"; (3) 5/10 registry links called "all null"; (4) this one. => JUDGE AN OUTCOME BY ITS ARTIFACTS AND
     SELF-CHECKS, NEVER BY THE STATUS LABEL -- and close the label FROM the artifact.**
281. **★★ P0 DISPATCHED (the research-phase main line).** Three CPU-only items, file-disjoint from the two running
     jobs, with the schemas and key names READ FROM THE FILES and pasted into the spec:
     - **X3** (C3) -- chain-rule `D_k` over **all 990 pairs and the full k range (5..30)** vs the linear i.i.d.
       null. **RANKED FIRST: it is the only experiment that can FALSIFY the framing**; the others confirm a
       number. The certified subset is used ONLY to validate the estimator (the old {5,10} window was
       unfalsifiable by construction).
     - **X1** (C1+C2) -- complete the headline table on the REFERENCE radius. **k=10 currently carries the OLD 2x
       values** (`upper_side_pairs = 11` at M=1), so k=10/15/30 must be recomputed to make one uniform-convention
       table with k=5.
     - **X4** (C2) -- the frontier as a FUNCTION with `tv_hat` PINNED, the M=8 crossover in n and k=8/k=10
       columns. **CORRECTED SAME TURN -- see M054: this entry originally said "only ~8% above the corpus mean"
       for the crossover at ~4.2186e6, which is the RADIUS-ONLY (necessary, not sufficient) boundary; the
       certifiability crossover at tv=0.30 is 26,366,192, ~6.2x larger. The dispatch was corrected before the
       worker finalised.**
     **Common requirements, each paid for this session:** state the alpha split on every number; paste the
     file-read key inventory into any spec that names a field; assert any theory-supplied inequality per item.

282. **★★★ THE LOCAL/REMOTE FORK RECURRED A FOURTH TIME, NOW SPANNING TWO UN-PUSHED ROUNDS (C025).** The four-file
     wording fix was dispatched **local-only**, so the corrected clause exists **only** in
     `artifacts/_project/data/`; the server copies were untouched **and the string `"UNDER THE CANONICAL
     CONVENTION"` appears 0 times in all four remote files -- as does the OLD clause**, i.e. the remote predates
     this entire cluster. **`q1_absolute_summary.json` remotely is the 6,434-byte pre-retention version vs 10,009
     locally**, so the remote is ALSO missing the `radius_convention` / `per_rung_note` / `_ref_radius`
     quarantine -- **the very trap this session spent rounds fixing: a reader opening the remote copy sees none
     of the "two conventions coexist, here is which to cite" guidance.**
     **=> A declared canonical direction (LOCAL -> SERVER) is STALE unless a push accompanies the edits.**
     **=> C025: for any artifact set, dispatch ALL-REMOTE or ALL-LOCAL, never a mix; after any local edit to a
     synced artifact, push it in the same task or record an explicit pending-sync entry; verify byte-identity on
     BOTH sides after every push.** Dispatched the reconciliation (push all four, before/after hashes per side).
283. **★ A CHECKSUM IN A RECORD IS AN INTEGRITY CREDENTIAL, NOT PROSE -- a wrong-length "hash" is worse than none.**
     The worker reported the post-edit hash of `q1_gate_five_pairs_full_n.json` as **65 hex characters**; the real
     value is the same string's **first 64**. **The file is fine; the report has one spurious trailing character.**
     **=> anyone comparing it gets a silent mismatch that looks like data corruption.** Correct to the 64-char
     value and record the cause.
284. **★ THE STATUS-LABEL DEFECT NOW HAS A MECHANICAL CAUSE, NOT A "BE CAREFUL" FIX.** The same worker was marked
     `failed` again. **Root: the completion check was `grep -c '<old string>' <file>` intending to confirm ABSENCE
     (expect 0) -- but `grep -c` returns EXIT CODE 1 when the match count is 0.** **So a check written as
     `grep -c <old>` to confirm the old string is GONE will ALWAYS report failure when the task SUCCEEDED.**
     **=> To assert absence, use `test $(grep -c ...) -eq 0` or `! grep -q ...`; NEVER bare `grep -c`.**
     **=> Third instance of a reversed completion check, and the first with a mechanical cause:** the previous two
     fixes were intent-level reminders ("write the expected value explicitly"), which demonstrably do not stick.
     **A FORM CONSTRAINT is executable; an intent reminder is not.** This is the third worker killed by my own check.
285. **★ X8 CROSSED FROM 0 TO 22 COMMITTED ROWS -- the third checkpoint design worked, and the switch condition was
     FALSIFIED BY FACT rather than triggered.** After three `0 committed rows` rounds, per-pair ledgers committed
     **22/990**. **=> the pre-written condition ("one more zero-commit round triggers a staged pilot") did NOT
     fire, so the conclusion is KEEP, not stage.** **=> Positive instance of the probe rule: the log grew 1.51 ->
     1.56 MB (almost no information) while the real signal was `22`.** **AND a new fact: the host has 208 CPUs**,
     so it is expanding the worker pool with short bounded batches **=> the earlier "~30s per pair" was measured
     UNPARALLELISED, so extrapolating from it would be systematically PESSIMISTIC. ETA remains unpublished; the
     event that makes it measurable is one bounded batch completing inside a clean time window** (that yields both
     per-pair cost and the real speed-up).

286. **★★★ "THE M=8 CROSSOVER IS ~4.2186e6" IS THE **RADIUS-ONLY** BOUNDARY -- NECESSARY, NOT SUFFICIENT
     (M054).** The verdict uses the CONJUNCTION `eps_hi = tv + radius < 0.5`; `radius_sum < 0.5` alone is only
     necessary. Independently computed at k=5, M=8, reference radius:
     | criterion | tv=0.00 | tv=0.10 | **tv=0.30** | tv=0.48 |
     |---|---:|---:|---:|---:|
     | **A. radius-only** (`radius_sum<0.5`) | 4,218,591 | 4,218,591 | **4,218,591** | 4,218,591 |
     | **B. certifiability** (`tv+radius<0.5`) | 4,218,591 | 6,591,548 | **26,366,192** | 2,636,619,232 |
     **=> citing A as "the M=8 crossover, only ~8% above the corpus mean" UNDERSTATES the requirement by ~6.2x at
     tv=0.30, and by ~600x at tv=0.48.** (A is tv-independent, which is exactly why it is comfortable to quote
     and why it is the wrong one.)
     **=> CROSS-CHECKED against the plan's OWN frontier formula** `M_max = 0.5*(n*B^2)^(1/k)`,
     `B = 0.5 - tv - sqrt(2 ln(2/alpha_law)/n)`: at n=3.9e6, tv=0.30 it gives `M_max = 5.45` (so M=8 does not
     certify), and solving it for `M_max = 8` reproduces the B row exactly.
     **=> ALSO: memory records 4,218,591 explicitly as a **2x-FORM** value, with its own note that it "must be
     RE-DERIVED before it is quoted" -- so the figure was cited downstream of its own invalidation warning.**
     **=> RULE (2nd occurrence of this confusion -- the first was E3's `upper_side_formula` metadata, which also
     recorded radius-only): whenever a criterion is a CONJUNCTION, any threshold/crossover/feasibility boundary
     quoted from it MUST NAME WHICH CONJUNCT it used, and MUST DEFAULT TO THE FULL CONJUNCTION. A necessary
     condition's boundary is not the feasibility boundary. The two differ by orders of magnitude here.**
     **=> Fixed by X4: report the eps_hi crossover as PRIMARY across the same tv grid as the frontier table, keep
     radius-only only if labelled "necessary, not sufficient", and state the ~6x understatement explicitly.**
287. **★ FOUR WORKERS, ONE h5 => I/O CONTENTION MAKES ANY TIMING JUDGEMENT UNRELIABLE.** X1/X3/X4/X8 all read the
     same 10M-row HDF5 on one host. **This does not affect correctness (all four write DIFFERENT new files) but it
     destroys any "steady-state" reading => NO ETA is publishable**, not even single-task. **=> when parallel work
     shares a slow resource, correctness and timing must be reported separately, and timing declared unavailable.**

288. **★★★ X8'S MANDATORY CHECK ASSERTED AN INEQUALITY THAT IS NOT A THEOREM -- AND IT CONTRADICTED OUR OWN
     FRAMING (M055).** I wrote: *"assert `TV(vector)_i >= TV(marginal)_i` on EVERY pair; DPI guarantees it;
     a violation is a BUG"*. **The word "marginal" silently named TWO DIFFERENT OBJECTS:**
     | object | is it a deterministic function of the other? | is the DPI bound valid? |
     |---|---|---|
     | **A. PHIST-side POOLED CELL LAW** (average the per-flow 32-vectors within a service) | **YES** -- pooling is a deterministic map, same flows, same channel | **YES**: `TV(vector) >= TV(pooled)` |
     | **B. k-PREFIX SYMBOL LAW** (first 5 (direction,size) codes) | **NO** -- the two consume DIFFERENT aspects of the flow (prefix order/length vs whole-flow size & IPT histograms) | **NO**: no DPI order in EITHER direction |
     **=> the artifact compares against B** (k-prefix marginal, median 0.5349). **So the required per-item
     inequality asserts a relation that is not a theorem.** The observed medians DO order (0.8674 > 0.5349),
     but that is an empirical fact about this corpus, not a guarantee; per-pair it can go either way, and a
     "violation" would NOT be the object-mismatch bug the spec claims it detects. **A check whose premise is
     false cannot function as a detector.**
     **=> WORST PART: it CONTRADICTS OUR OWN FRAMING.** The framework explicitly records **"PHIST and k-prefix
     have NO DPI order in either direction."** So the spec refuted our own argument.
     **=> RULE: before writing any per-item assertion from a stated inequality, verify (a) the inequality is a
     theorem FOR THE TWO OBJECTS NAMED, and (b) both objects are identified UNAMBIGUOUSLY. "Marginal" is a
     RELATIONAL word -- it denotes different distributions relative to different objects, and here it named two
     in one sentence.** Check any inequality meant as an automated detector against the framing's own DPI
     statements FIRST.
289. **★ ON A REPORTED DUPLICATE-DISPATCH RISK, VERIFY THE FILE COUNT BEFORE ACTING.** The agent asked whether two
     workers were writing `x1_/x3_/x4_*.json` (its set and mine). **Checked: exactly ONE worker per target** (X4's
     second file is its result JSON). **=> no withdrawal was needed; cancelling on suspicion would have discarded
     live compute.** The agent's own instinct ("I will not withdraw on a guess") was right, and the resolution was
     a file count, not a judgement call.

290. **★ THE FALSE DPI PREMISE REACHED THE ARTIFACT -- but the CORRECT CONCLUSION was attached to it.** The landed
     vector artifact states: *"By the data-processing inequality TV(vector law) >= TV(marginal symbol law), so this
     is a STRONGER claim -- but the two quantities are NOT interchangeable and this figure must NEVER be reported as
     a better bound on Q1's or Q2's object."* **The discipline sentence is RIGHT; the justification clause is the
     M055 non-theorem.** **=> a correct CONCLUSION carrying a FALSE justification is the most durable form of this
     error**, because the conclusion survives review and the reasoning rides along into the paper. Fix worker
     dispatched (23:19) to replace the justification and record that the earlier version asserted a non-theorem.
     **=> CHECK REASONING, not just conclusions: when a correct statement arrives attached to a derivation, verify
     the derivation independently. A right answer does not validate its own argument.**
291. **★ `yaml.safe_load` STRIPS BACKTICKS FROM PLAIN SCALARS, so a spec pattern written with backticks can silently
     fail to match what is actually stored.** A replacement I attempted did not apply because the stored text had
     no backticks; the fix was to read the string from the loaded YAML and match THAT. **=> when patching a YAML
     scalar programmatically, read the value first and match the loaded form, never a hand-retyped version.**

292. **★ THE PRE-GPU DREAM FAILED TWICE, BOTH AT PHASE 1, ON EXECUTION-LAYER ERRORS -- so the pre-GPU simulation
     is UNAVAILABLE (not "negative").** Attempt 1: *"LLM subprocess completed without a terminal event"*. Attempt 2
     (retry, `trigger_reason` recorded): *"Phase 1 failed: LLM subprocess exited with code 1"* -- `stages_completed:
     []`, no tier errors, no review content. **Per the rule recorded in entry 273, NO THIRD RETRY.**
     **=> What this means: the plan has NOT been pre-screened by simulation.** That is a MISSING CHECK, not a
     failing one -- do not treat the absence as a pass, and do not treat it as a verdict on the plan.
     **=> What stands in its place: the framing and plan have been reviewed by hand, repeatedly, and every one of
     this session's structural defects was found that way -- C2's inverted mechanism, C3's unfalsifiable-by-
     construction window, the M=8 crossover criterion error (M054), and the false DPI premise (M055). The
     simulation is a BACKSTOP, not the primary check.**
     **=> Re-attempt only when the execution layer is known healthy, and record the attempt; do not loop.**

293. **★★ CALIBRATION: TWO 'n' SCALES DIFFER BY 17.5x -- the frontier is evaluated at FULL-CORPUS projection scale
     while the measured brackets are XS-scale.** X4's `corpus_mean_n_input: 3,900,000` is the full-corpus
     projection (194.3M / 50 services = 3,886,000); **the project actually MEASURED the XS subset (10M / 45
     services = ~222,222)**. The artifact's scope text called 3.9e6 "the stated corpus mean slice", which reads
     as the measured corpus. **=> a reader checking the frontier against the XS data finds the XS mean far below
     the crossover for reasons unrelated to the certificate.** Every `n` input must carry an `n_scale` label
     (full-corpus projection vs XS measured), and the artifact must state that the two differ by ~17.5x and must
     not be compared directly.
294. **★★ THE TWO UNDER-STATEMENTS COMPOUND: M054 (wrong criterion) x the scale mix = up to TWO orders of
     magnitude.** At tv=0.30 the M=8 CERTIFIABILITY crossover is **26,366,192** -- **6.8x the full-corpus mean
     and 119x the XS mean**. So BOTH "it is only ~8% above the mean" (criterion A, M054) and "3.9e6 is our
     corpus mean" (scale mix) understate the requirement, and together they do so by orders of magnitude.
     **=> when a threshold is quoted, state its CRITERION (which conjunct) AND its SCALE (which corpus).**
295. **★★ THE FORK WAS NOT A SINGLE-POINT ACCIDENT -- ALL FOUR FILES WERE TWO ROUNDS BEHIND, one by +56%.** The
     reconciliation revealed the old server copies as 6,434 / 25,510 / 9,469 / 1,674,208 B vs local 10,009 /
     28,598 / 11,667 / 1,676,890 B. **`q1_absolute_summary.json` was +3,575 B (+56%)**, missing
     `radius_convention` + `per_rung_note` -- exactly the quarantine that stops the stale per_rung table being
     read as citable. **=> a mixed local/remote dispatch behind a whole round does not fork ONE file, it forks
     the ENTIRE set; and the sync must therefore cover EVERY artifact touched, not "the ones I listed".**
296. **★ `tree_authority` INSIDE THE ARTIFACT IS THE ONLY STRUCTURAL FIX FOR A FOUR-TIME-RECURRING FORK.** Four
     prior rounds relied on messages, roadmap lines and memory entries; none prevented recurrence. Recording
     *"LOCAL is AUTHORITATIVE; direction LOCAL -> SERVER; any future edit must be made on the LOCAL side and then
     pushed; do not edit the server copy"* **inside each artifact** means the next reader is told which tree to
     edit. **=> a rule that must survive its author belongs in the artifact, not in the conversation.**
     **=> And the declared authority must be COMPLETE:** if an artifact is server-only while LOCAL is declared
     authoritative, the next local-side push will never carry it -- so any artifact the project relies on
     (X4, X8) must be pulled local.

297. **★★★ THIRD INSTANCE OF "I HAD JUST WRITTEN THE RULE AND THEN BROKE IT" -- the most important pattern this
     session.** (1) I recorded "read field names, never recall them", then wrote `gate_fraction` from memory in a
     spec; (2) I recorded "when a criterion is a conjunction, name the conjunct", then asserted a DPI inequality
     that is not a theorem (M055); (3) I recorded "state which TREE you are writing to" (after four forks), then
     dispatched a correction worker **server-side while LOCAL was the just-declared authority**.
     **=> COMMON FORM: the rule was EXTRACTED FROM A LESSON, not READ FROM A CHECKLIST.** I remember the lesson's
     *content* but do not convert it into a gate that every dispatch must pass.
     **=> FIX (form, not memory): before dispatching ANY task that touches artifacts, pass a fixed three-question
     gate -- (a) WHICH FILE (paste the real key inventory read from it); (b) WHICH SIDE (which tree, which
     direction); (c) is a delete/replace check's direction correct (assert absence with
     `test $(grep -c ...) -eq 0`, never bare `grep -c`).** **(= C026.)** A checklist beats remembering, because remembering has
     now failed three times on rules I had personally just written down.
298. **★ A MIXED-SIDE DISPATCH FORKS THE WHOLE SET, AND THE ONLY CAUSE THAT MATTERS IS AN UNRECORDED SIDE.**
     Reviewed the fork history: round 1 = both sides edited, no direction recorded; round 2 = local-only, no push;
     round 4 = reconciled once `tree_authority` was written INTO the artifact. **=> in every fork the failure was
     an UNRECORDED side choice, not a wrong side.** **=> so a per-round `direction` field plus an explicit
     "this round is the EXCEPTION" note addresses the cause; forcing one side does not.** Accepted
     `direction: SERVER -> LOCAL` for round 3 on that reasoning, with three conditions: direction written into
     the artifact; the exception labelled AS an exception (so a reader of "LOCAL authoritative" still knows the
     server copy may need pulling); and post-pull byte-identity asserted, with the round's scope covering EVERY
     artifact touched, not a hand-listed subset.
299. **★ CREDIT THE ARGUMENT TO ITS AUTHOR.** The agent's message said "your argument I accept" about a piece of
     reasoning **it had produced itself**; I had only checked it. **=> attributing one's own judgement upward
     distorts the reasoning chain and hides who decided what.** Say plainly when a judgement is the other party's.
300. **★ "AN AUTHORITATIVE SIDE THAT IS INCOMPLETE HAS, IN EFFECT, NO AUTHORITY."** (The agent's phrasing, adopted --
     better than my own.) If artifacts live server-only while LOCAL is declared authoritative, the next
     local-side push will never carry them. **=> when declaring a canonical tree, verify the canonical tree
     actually CONTAINS everything the project relies on.**

301. **★★★ THE "SELF-FAILING DETECTOR" WAS WRONG TWICE OVER (M055 + M056).** X8's spec called the per-item
     inequality a self-failing object-mismatch detector. **Defect 1 (M055): wrong object** -- "marginal" named
     two distributions, and the theorem holds only against the PHIST-side POOLED CELL LAW, not the k-prefix
     symbol law (no DPI order relates the latter pair). **Defect 2 (M056, deeper): wrong QUANTITY TYPE.** The
     vector run is `tv_lower_bound(..., method='michel')` with guarantee text *"asymptotic HPLB estimate, not an
     exact finite-sample certificate"*, and the pooled side carries `tv_hat`. **BOTH SIDES ARE LOWER BOUNDS.**
     **A lower bound on `TV(vector)` may sit BELOW `TV(pooled)` even when DPI holds** => the assertion
     `vector_lo_i >= pooled_i`:
       - PASSING => only "no contradiction was observed" (weak);
       - FAILING => EXPECTED, indicates nothing.
     **=> it cannot falsify anything. It is a one-sided SANITY check, not a detector.**
     **=> RULE (form): to call an assertion a "detector" or a "self-failing check", BOTH must hold: (a) the
     inequality IS a theorem FOR THE TWO OBJECTS NAMED; (b) the quantity TYPES permit contradiction -- at least
     one side must be an UPPER bound or a POINT ESTIMATE. TWO LOWER BOUNDS COMPARED CAN NEVER FALSIFY.**
     **=> This is the FOURTH instance of "a check that cannot fail is not a check"** (after: the `k_cert`-only
     gate; `radius < 0.5` alone; the non-empty-bracket fraction). **C019's family keeps growing; audit every new
     assertion against (a) and (b).**
     **=> Recorded in the artifact: `vector_side_quantity_type: lower-bound`, `pairs_where_the_check_can_falsify: 0`,
     `check_is_sanity_not_detector: true`** -- so no reader can read a pass as "the theorem is verified".
302. **★ "NOT PERFORMABLE / DOES NOT EXIST" IS ITSELF A CLAIM REQUIRING VERIFICATION.** A worker reported
     `status: NOT_PERFORMABLE` on the pooled-cell-law join, reason *"No per-pair pooled-cell-law values exist"*.
     **VERIFIED FALSE**: `q2_phist_certificate_v3.json`'s own `certified_object` block states
     `probability_parameter = E[per-flow normalized 32-vector]` with `tv_identity = 0.5*||mean_a - mean_b||_1`,
     and all **990** rows carry `tv_hat`. **The values were always available; the worker did not recognise the
     object's name.** **=> same family as "984 cannot be computed" and "the registry is all NULL": a negative
     existence/ feasibility claim is as checkable as a positive one, and must be checked before it is accepted.**
303. **★★★ THE SELF-CORRECTION ITSELF FELL INTO THE SYNC GAP — a fix recorded as DONE while the authoritative side
     still carried the defect (M057).** `q1_vector_level_one_sided_full_n.json` was written locally at **23:12:42**
     carrying the false DPI justification; a fix worker was dispatched at **23:19**; §290 recorded *"Fix worker
     dispatched"*. **At 23:42 the LOCAL artifact still returns `grep -c "data-processing inequality"` = 1**, the
     `NOT_PERFORMABLE` reason appears **only in memory.md** (nowhere in the local tree), and the Agent was **idle
     with an empty queue**. **Reading: the 23:19 fix very likely landed SERVER-side and the local tree was never
     re-synced — the same local/server divergence as before, now swallowing its own remedy.**
     **=> THE LESSON THAT MATTERS: "dispatched" is not "landed", and "landed" is not "landed on the authoritative
     side". Record the SIDE and re-verify with a read on that side; never close a defect on the strength of a
     dispatch confirmation.** A defect-closing record must cite a fresh observation of the corrected text on the
     declared authoritative tree — which in this project is LOCAL (§295's convention).
     **=> AND: A CORRECT CONCLUSION CARRYING A FALSE JUSTIFICATION is the most durable form of this error** (§290):
     the conclusion survives review, so the bad reasoning rides along into the paper. Here the artifact's DISCIPLINE
     sentence ("must NEVER be reported as a better bound on Q1's or Q2's object") is right, while its DPI
     justification is the M055 non-theorem — so a reviewer skimming would pass it.
304. **★ EMPIRICAL REFUTATION OF THE FALSE DIRECTION, MEASURED ON THE REAL CORPUS (closes the M055/M057 loop).**
     Comparing per-pair `tv_hat` for the **k-prefix symbol law** vs the **pooled cell law**:
     **78 of 990 pairs INVERT** (`symbol_tv < pooled_tv`), largest gap **0.3415 on pair (29,38)** — symbol
     `tv_hat = 0.102034` vs pooled `tv_hat = 0.443496`. The `eps_lo` variant inverts on **75/990**. Under the
     retracted "object-mismatch detector" framing those 78 pairs would have been flung as bugs; they are exactly
     the expected behaviour when two objects have **no DPI order in either direction**.
     **=> RULE: before calling a per-pair inequality a DETECTOR, compute the inversion count on the real data. A
     substantial inversion fraction proves the inequality is not a theorem for those objects — the check is
     measuring a difference between objects, not a fault.**
     **=> the VALID theorem is vector-vs-POOLED (`TV(vector law) >= TV(pooled cell law)`, deterministic pooling,
     same flows, same channel) — that is the inequality worth asserting.**
305. **★★★ X3's OWN VALIDATION CANNOT VALIDATE ITS CLAIM — the validation runs at FIXED k, the claim lives
     ACROSS k (M059).** The artifact's `estimator_validated_on_certifiable_subset` compares the estimator
     against an independently produced `tv` **separately at k=5 (990 pairs) and k=10 (990 pairs)**: Spearman
     0.944 / 0.955, Pinsker violations 0. That is real evidence — that the estimator **tracks TV within a
     k-slice**. But the adjudication (`SUBLINEAR`) rests **entirely on how the estimator's bias behaves as k
     GROWS**, and a comparison performed **at a fixed level of the very variable whose effect is claimed**
     cannot speak to that at all. The validation is orthogonal to the claim it is presented beside.
     **=> RULE: before accepting a validation as support for a claim, ask WHICH AXIS the validation varies and
     which axis the CLAIM varies. If the validation holds the claim's axis fixed, it is not evidence for the
     claim — however many pairs, however high the correlation, however zero the violations.**
     **=> this is why the known-truth control is decisive and not a nicety: the estimator's k-dependent bias
     profile is UNCHARACTERISED, and every candidate mechanism for producing the observed curve (Jeffreys
     smoothing on contexts that thin out as k grows; the `PPI_LEN >= k` population change) acts ALONG k.**
     **=> generalises to: a control that cannot exercise the mechanism under test is not a control, exactly as
     a check that cannot fail is not a check (§301's family).**
306. **⛔⛔ RETRACTED AND SUPERSEDED (D044, 2026-09-14): THE DIRECTION BELOW IS BACKWARDS FOR THE ACTUAL
     ESTIMATOR.** The measured `est/true` is **1.0002 at k=5 FALLING to 0.6769 at k=30** (real-occupancy twin:
     0.9987 → 0.8824) — the estimator **DEFLATES** `D_k` as k grows, so the bias **MANUFACTURES** sublinearity
     and `SUBLINEAR` is **NOT** conservative. **Consequence: X3 = INCONCLUSIVE**, not SUBLINEAR.
     **The numbers in the retracted text below (1.98 → 9.67, "INFLATES") came from a PROXY construction —
     "an estimator of this shape" — NOT from the actual estimator.** The proxy had the sign right for itself
     and wrong for the real estimator. The lesson to keep is the RULE at the end (pin the sign with a
     control); **the lesson to add is that the control must be the ACTUAL estimator, not a reconstruction of
     it.** A proxy can pin a sign for a different function. **See M093.**
     **⇒ AND THE META-FAILURE: this paragraph was the load-bearing justification that made `SUBLINEAR` look
     safe, it was written BEFORE the kill-control returned, and it was wrong. When a pre-registered
     kill-control is in flight, do NOT write interim reassurance about its outcome.**
     **⛔ THE FOLLOWING IS THE RETRACTED TEXT, RETAINED ONLY AS A RECORD OF THE ERROR:**
     **★★★ I ASSERTED A BIAS DIRECTION FROM PLAUSIBILITY, AND THE MEASUREMENT SAYS THE OPPOSITE (M061).**
     I told the user and wrote into the ROADMAP that Jeffreys smoothing on sparse contexts would
     **"manufacture sublinearity"** — i.e. that the bias **helps** the observed `SUBLINEAR`. **That is
     backwards.** A synthetic probe on an estimator of this shape, with the truth pinned to **strictly
     linear** (`D_k = k·KL₁`, `KL₁ = 0.010205` known exactly), gave **est/true = 1.98 at k=5 rising to 9.67
     at k=30**: smoothing **INFLATES** `D_k` as k grows, which **STEEPENS** the curve and therefore works
     **AGAINST** sublinearity. **⇒ the observed `SUBLINEAR` is CONSERVATIVE with respect to this bias.**
     **⇒ root cause: I derived a direction from a verbal story ("sparse contexts shrink the estimate")
     without pinning the sign. The story is even locally true — a *noisier* estimate is pulled toward
     uniform — but the DOMINANT effect at these k is that two differently-smoothed conditional laws are
     pulled APART in relative terms, which inflates the symmetric KL. Plausibility gave me a direction;
     only the probe gave me the sign.**
     **=> RULE: a claimed sign (increases / decreases / inflates / shrinks / conservative / anti-conservative)
     is a MEASURABLE claim and must be pinned by a control or a probe BEFORE it is written, especially when
     it is used to argue that a result is safe. "It would manufacture the effect" and "it makes the result
     conservative" are opposite claims, and getting it wrong flips a caveat into a false reassurance.**
     **=> AND THE CONTROL MUST BE THE ACTUAL ESTIMATOR, NOT A RECONSTRUCTION OF IT (D044/M093): a proxy
     pins the sign for whatever function the proxy is, which need not be the one under test.**
     **=> note the meta-shape: the same turn that corrected the user's claim was the turn I introduced an
     unverified directional claim of my own. Correcting someone is not evidence of being careful.**
307. **★★★ X1's HEADLINE DISAGREES WITH THE SETTLED GATE — 337/342/985 vs 336/340/986 (M063). OPEN.**
     Recomputed by hand this turn, from the artifacts rather than from any report:
     `q1_lower_side_full_n.json` (990 rows, full n) → upper **340**, lower **986**, **joint gate 336**
     (0.339394); capped lower **985**, upper ∧ capped **335**. `q1_gate_five_pairs_full_n.json` →
     `gate.count` **336**. **X1 reports upper 342 / lower 985 / gate 337.** Neither 342 nor 985 matches.
     **⇒ THREE things make this the highest-consequence open item:**
     1. **It is the paper's central number.** C1's registered claim and the framing headline both quote 33.9%
        = 336/990. A ±1-pair shift is 0.1pp on the abstract's number.
     2. **`342` is Q2's informative count** (`q2_phist_certificate_v3.json`, `eps_hi < 0.5` = 342, verified
        this turn). The M041 2×2 finding exists precisely because **340 and 342 are the two numbers that must
        never be conflated**, and X1 reports 342 on Q1's cell.
     3. **`985` is exactly the CAPPED lower count.** So my leading hypothesis is a **mixed-convention join**
        (capped lower side joined to a reference-radius upper side) — the same class of error C016 guards
        against, and it would produce both the 985 and a 337 arithmetically.
     **⇒ X1 ALSO CONTRADICTS ITSELF**: `claim_sentence_supported` says **33.9%** while its own
     `gate_fraction_both_ref_radius` = **0.3404** (34.04%). If X1's own fraction is right, the **claim** is
     wrong — a framing-level change, not a table fix.
     **=> RULE: a headline number appearing in two artifacts is a CONFLICT to be reconciled per pair, never
     averaged, never resolved by taking the rounder value, and never left standing. The reconciliation must
     produce the NAMED symmetric-difference pair list — a total that matches for the wrong pair set is not a
     reconciliation.**
     **=> method note: my own first pass got `upper = 0` because I read `eps_hi` at the top level; the field
     is nested at `upper_recomputed.condition_eps_hi_lt_0_5`. Reading the real key list before counting is
     what turned a zero into 340 — the M056 question-1 failure, caught in under a minute.**
308. **★ A MONOTONE SERIES MUST BE ON ONE BASIS — MINE MIXED TWO (M062).** C2's falsifiable statement read
     *"gate 0.3394 / 0.0475 / 0.0030 / 0 / 0 across M = 1/2/4/8/16"*. But `0.3394 = 336/990` is the **joint
     gate** at M=1, whereas the M≥2 entries are **upper-only** counts. **A per-rung joint gate does not exist
     for M≥2** (no per-rung lower side was computed), so the series was internally inconsistent: one point
     measured a different quantity from its siblings, **making M=1 look lower than it is** (0.3434 is the
     upper-only value).
     **=> RULE: before stating a series as monotone, check that EVERY element is the same quantity. A series
     whose first element is a conjunction and whose rest are single conditions is not a series.** Corrected:
     the C2 series is **upper-only throughout** (0.3434 / 0.0475 / 0.0030 / 0 / 0), with the joint gate
     336/990 quoted **separately** as C1's headline.
309. **★★★ X1's DISCREPANCY IS FULLY REPRODUCED — TWO ERRORS IN OPPOSITE DIRECTIONS THAT NEARLY CANCEL
     (M064; detection was M063).** I recomputed the upper side from the real 990 rows of `q1_lower_side_full_n.json`
     at several per-law alpha values:

     | `alpha_per_law` | upper count | |
     |---|---|---|
     | **0.025** | **340** | canonical (alpha/2 per law, union bound ⇒ joint 0.95) |
     | **0.05** | **342** | **UNSPLIT alpha — X1's number** |
     | 0.005 | 335 | the alpha/4 over-split the repo already guards |

     **Exact flipped pairs** (both ~1e-4 from the line, so only a convention change moves them):
     **(22,36)** canonical `eps_hi` 0.500137 → unsplit 0.499025; **(32,52)** 0.500183 → 0.499096.
     **The lower side carried the SECOND error**: X1's **985** is the **capped** count; full-n is **986**,
     the sole differing pair being **(21,23)** (full `eps_lo` 0.058781 vs capped 0.049781).

     | upper | lower | up | low | gate |
     |---|---|---|---|---|
     | canonical | full-n | 340 | 986 | **336** ← canonical |
     | unsplit | full-n | 342 | 986 | 338 |
     | canonical | capped | 340 | 985 | 335 |
     | **unsplit** | **capped** | **342** | **985** | **337** ← **matches X1 exactly** |

     **My independent implementation reproduced 340 at alpha/2 BEFORE being used to explain 342** — so the
     method was validated against the settled number first, then applied to the deviation.

     **★★ THE LESSON IS THE CANCELLATION, NOT THE FINAL INTEGER.** The two errors point **opposite ways**:
     the upper error alone gives **338 (+2)**; the lower error alone gives **335 (−1)**; **together they give
     337 (+1)**. **So "337 vs 336, close enough" is doubly wrong** — a near-correct total masking two
     independent convention defects. **=> RULE: a small net difference is NOT evidence of a small cause.
     When a recomputed total is off by one, check whether two larger errors of opposite sign are
     cancelling — the correct diagnostic is a per-item symmetric difference, not the total's magnitude.**
     **=> and the `342` coincidence with Q2's count is now EXPLAINED as an artifact of the alpha under-split
     on Q1's own rows, so the feared Q1/Q2 object merge did NOT happen — but the coincidence is precisely
     why a count-level check would have missed this: the number matched something, so it looked plausible.**
     **=> repo guard already exists for the MIRROR bug** (`test_not_doubly_conservative`, alpha/4 over-split);
     **the corresponding UNDER-split guard was missing** and has been requested — a test asserting the
     upper-side radius uses alpha/2 per law, so the unsplit form fails loudly instead of silently shifting
     two pairs.
310. **★★★ BOTH S1/S2 CONFIRMED BY A REPRODUCING CHECK, AND THE SCOPE IS ALL 20 CELLS — NOT ONE (M064
     closed).** `x1_convention_check.json` settled both hypotheses by **reproduction**, not argument:
     `alpha=0.05 → 342`, `alpha=0.025 → 340`; `constant_reproducing_table_342: 2.7162`,
     `alpha_reproducing_table_342: 0.05`. The correction lands exactly:
     `corrected_m1_k5_cell` = upper **340**, lower **986**, gate **336**, fraction **0.3393939393939394**,
     `equals_canonical_340_336: True`.
     **⇒ SCOPE, AND THIS IS THE PART THAT MATTERS: the `alpha=0.05` call sits inside `radius_for_n`, used
     while assembling EVERY cell, and the raw `.x1_k15/k30` intermediates record NO alpha or radius at all
     — so the same wrong alpha was applied to ALL 20 CELLS.** `scope: all 20 cells`.
     **⇒ the earlier "fix the M=1/k=5 cell" reading was WRONG and was superseded: this is a table-wide
     rebuild, and it would have shipped 19 uncorrected cells had the scope not been checked explicitly.**
     **=> RULE: when a defect is found in one cell of a table, do not assume the cell is the unit of the
     defect. Ask what the DEFECTIVE CODE PATH is shared by — here a shared `radius_for_n` helper used in a
     `for m in RUNGS: for k in KS` loop. The cell is where it was DETECTED, not where it is CONTAINED.**
311. **★★★ A DEAD PROXY RESURRECTED INTO A LIVE FIELD — SIX NUMBERS, THREE CONVENTIONS EACH SIDE (M065).**
     The X1 cell carried: upper **292 / 342 / 340** (2x inlined radius / ref-radius-wrong-alpha / correct)
     and lower **987 / 985 / 986** (**proxy `tv_hat > T(n)`** / capped / full-n).
     **`987` is the PROXY** — proven arithmetically: `0.996969696969697 × 990 = 987`, and the E3 metrics
     field `band_lower_edge_fraction` is exactly `0.996969696969697`. **The record ALREADY states the proxy
     is NOT a bound and that no artifact ever contained that value as a gate — and it is back in the table
     as a first-class field beside the live numbers.**
     **⇒ this is the mirror of the dead-value problem: a superseded number that stays as a FIELD is
     pickable-up regardless of which one is right. With three self-consistent-looking values per side, a
     reader has a 1-in-3 chance per side and no way to tell.**
     **=> RULE: correcting the live column is NOT sufficient. A wrong-convention or superseded number must
     be SUPPRESSED or confined to an explicitly-labelled `superseded` block — never left as a sibling field
     that looks equally citable.** (Same remedy as the dead `61.28` constant and the dead 2x radius.)
     **=> and note the compounding: the proxy 987 was itself the residue of an earlier retraction. Retracted
     values do not stay retracted by being retracted; they must be moved out of the citable namespace.**
312. **★★★ A DISPATCH IS NOT A RUN — AND THE MONITORING LINE IS ONLY AS GOOD AS ITS SOURCE (M071).** A status
     line reported **"[Resources] GPU 1/1 RUNNING (X12 just took cuda:0)"**. **Every axis of a live check
     contradicted it** the same turn:
     - `list_available_gpus` → **2 MB used / 0% util / no processes** (card idle);
     - registry → **no X12 entry**, and nothing in ALLOCATED / RUNNING / PENDING;
     - checkpoint `X12_PREPARING_…` → `state: PREPARING`, `previous_state: PREPARING`, `retry_count: 0`;
     - the worker's own log → *"I'll dispatch X12 directly to server 111"* then *"dispatched to worker
       **Rawls**"* — a **coordinator**, and **no `Rawls` log exists**.
     **⇒ true state: dispatched-but-not-started.**
     **⇒ THE ENABLING CAUSE WAS DIAGNOSED IN ADVANCE BY THE EXECUTING ROLE:** the spec granted
     `tool_groups=["ssh","experiment"]` — a group *containing* `submit_on_allocated` — but **never required
     the submission to go through it.** So the run could proceed unmanaged, and **an unmanaged run publishes
     no PID, no log path, no GPU attribution ⇒ "is it running?" has no authoritative answer, and the status
     line necessarily becomes an ASSERTION rather than an OBSERVATION.**
     **=> RULE 1: a resource/status line must be derived from a LIVE QUERY of the authoritative source, never
     from the dispatch record.**
     **=> RULE 2: granting a tool is not requiring an action. "The tool was available" and "the action was
     required" are different, and only the second produces the metadata that makes a status verifiable.**
     **=> NOTE the chain shape too: this was worker → worker (the X12 worker spawned a further Worker), so the
     artifact will name a worker that was not the one spawned, and the GPU attribution sits one level down.
     Nested dispatch is legitimate but it lengthens provenance — require the ACTUAL EXECUTING worker and PID.**
     **=> this is the fifth declared-vs-actual divergence of the session (M057 dispatched-not-landed, M060
     correction-on-the-mirror, M066/M069 done-status-not-actual, M070 narrated-near-miss that did not occur),
     and the first where the cause was named ahead of the failure by the role that owns execution.**
313. **★★★ A CORRECTION PROPAGATES BY DOCUMENT, NOT BY INTENTION — AND THE LAST COPY IS THE ONE THAT BITES
     (M051 → registry).** C2's mechanism was corrected in `paper_framing.md` and `ROADMAP.md` early, and I
     reported to the user that the correction "had reached the framing and roadmap but **not** the registry".
     **That was wrong, and wrong in a revealing way: the registry had also been corrected, by the executing
     role, at 02:20:31 / 02:20:35.** I then **ordered it re-corrected**, which would have overwritten correct
     text — the destructive version of repairing something that was never broken.
     **⇒ WHY I GOT IT BACKWARDS, and the two errors stacked:** (a) I grepped **case-sensitively** for my own
     paraphrase (`RESOLVES MORE` → 0) when the text writes `resolves MORE`; (b) the old phrasing greps **2**
     in **both** states — pre-edit as two **live assertions**, post-edit as two **quotations inside their own
     retractions** — so **the probe's value was invariant under the change it was meant to detect.** A count
     that takes the same value in both states cannot measure a difference between them.
     **⇒ and the decisive evidence was existence-based, not form-based:** the phrases I had quoted to the user
     from my OWN earlier tool output (`"despite having the LOWEST k_cert"`, `"retaining more latent
     separation"`, `"shrinks monotonically in M"`) are now **absent from the file entirely** — **text that was
     never present cannot be absent.** So the text had been **replaced**, and the replacement was the
     correction. **Existence beats form: "the old words are gone" is stronger than "the new words are quoted".**
     **=> RULE 1: a tool result rendered earlier in the conversation is a DATED SNAPSHOT, not current file
     content. Re-read before quoting — this is "conversation is not runtime state", which I had applied to
     infrastructure claims but not to my own quoted text.**
     **=> RULE 2: before using a count as evidence, ask what value it takes in EACH state being distinguished.
     If they coincide, the probe is blind — and a blind probe reports certainty it has not earned.**
     **=> RULE 3 (the general form): when a correction is issued for text that appears in several documents,
     the correction is not done until EVERY copy is checked — and the check must read each candidate region, not
     count a phrase. A retraction necessarily QUOTES what it retracts, so grepping the retracted phrasing is
     guaranteed to hit correct text.** Confirmed closed at 3 places (X1.hypothesis 1,255 chars; X4.hypothesis
     926; X4.metrics `why_finer_alphabet_cannot_help`), independently verified by an external reviewer who
     recomputed `k_cert = [17,8,5,4,3]` from scratch.**
314. **★★★ THE MANIFEST IS A THIRD RETRACTION SURFACE — AND ARTIFACT OPERATIONS MUST UPDATE IT IN THE SAME
     PASS (M092).** `artifacts/manifest.yaml` held **three** entries inconsistent with the bytes on disk:
     `art_20260914_9fb96b` **pointed at the canonical path but described the OLD 0.05-semantics run**;
     `art_20260914_55a5af` **claimed to be the corrected run while its path was DANGLING**; and
     **`art_20260913_f8b2e5` still carried the refuted DPI non-theorem** — *"By DPI TV(vector) >= TV(marginal)"*
     — **hours after the artifact's own fields, the registry, the roadmap and the framing were all corrected.**
     **⇒ WHY THE THIRD IS WORST: `paper_provenance.yaml` binds artifact descriptors, so a writer citing that
     entry reproduces the retracted claim in the manuscript while every artifact field says the opposite.**
     **⇒ ROOT CAUSE, single: registration / rename / consolidate / delete were performed as SEPARATE
     operations from the manifest update, so the manifest kept paths and descriptions from earlier states.**
     **=> RULE 1: any operation that changes an artifact's path, name or existence must update its manifest
     entry IN THE SAME PASS, and the entry must assert the path resolves to live bytes with a cited hash.**
     **=> RULE 2: the retraction checklist is THREE layers, not two — (a) the artifact's own fields;
     (b) the registry / ROADMAP / framing prose; (c) the manifest descriptions of every derived artifact.
     I had (a) and (b); (c) I had never enumerated.**
315. **★★★ RETRIEVAL AND PLACEMENT ARE DIFFERENT OPERATIONS (M089) — and `register_artifact` APPENDS A
     SUFFIX rather than overwriting.** A worker's correct refusal caught this after I instructed it to use
     that tool for *placement*: following my instruction would have created a **fourth** copy of the X5
     artifact. **⇒ RULE: retrieval MUST use the tool (the content lives on the authoritative side);
     placement MUST bypass it (read → atomic write → `os.replace()`).** The worker's formulation was better
     than mine, which is why it is recorded verbatim. **⇒ Corollary: after any server-side fix, the local
     mirror is not merely stale — it is a MISLEADING DOCUMENT** (the local X12 script kept
     `default="CATEGORY"` while the server carried `"APP"`), **so placement needs a mirror-side sync as a
     mandatory follow-up.**
316. **★★★ CANCELLING IS NOT RETURNING TO THE PRE-CANCEL STATE (M090).** I cancelled a worker on the
     inference "just started, low event count = wrote nothing". **It had already partially applied its
     renames**, so cancellation left **two identically-named `RETIRED_duplicate_do_not_cite` files in
     different directories** — a state my own naming scheme had not anticipated, since I designed those
     names to be unique **within one directory**. **⇒ RULE: before cancelling, check whether the worker has
     already written; then READ the affected paths rather than assuming the pre-cancel state.** The
     executing role stated the principle better than I had, which is why it is kept.
317. **★★★ COMPLETION CHECKS MUST BE WRITTEN AGAINST THE POST-TASK STATE, NOT THE PRE-TASK STATE (M082/M087).**
     Three of my own `completion_checks` asserted conditions inconsistent with the task's own goal: a check
     that the *alias file should exist* after dispatching its **deletion**; a probe string drawn from the
     **registry** but tested against the **plan** (guaranteed to fail on a correct edit); and a numeric
     baseline **inferred** rather than counted (`null` count said 10, was 9). **⇒ each produced a FALSE
     `failed` on correct work, and a false failure is indistinguishable from a real one in the status, so it
     misattributes blame and triggers rework.** **=> RULE: before dispatch, ask of every check — "will this
     pass after my task is completed as specified?"** And: **verify each probe string exists in the TARGET
     file before using it; state a numeric baseline only if COUNTED from the file.** This is now the largest
     single source of mislabelled `failed` in this project (8+ instances), alongside the runtime's own
     status-field unreliability — **judge work by its artifact, in both directions.**
318. **🔴🔴🔴 X3 IS `INCONCLUSIVE` — THE KNOWN-TRUTH CONTROL FAILED, AND THE VERDICT IS NOT RESCUED (D044).**
     **THE VERDICT: `SUBLINEAR` is DOWNGRADED TO `INCONCLUSIVE`. C3 as stated may NOT be claimed.**
     The pre-committed rule (fixed before measurement, restated in ROADMAP + framing) was: `SUBLINEAR` is
     CONFIRMED only if it survives **BOTH** (i) a fixed-population recompute and (ii) a known-linear-truth
     control the estimator must recover. **Otherwise DOWNGRADE TO INCONCLUSIVE.**
     | control | result |
     |---|---|
     | **(ii) known-truth — DECISIVE** | **FAILED.** Truth analytic and exactly LINEAR (`p=0.30,q=0.70` ⇒ `D_k = k·0.3389191441548814`). Estimator returned **SUBLINEAR** (p=0.651, √k AIC adv 29.52, ratio 2.631). **Real-occupancy twin also returned SUBLINEAR** (p=0.897, adv 22.10, ratio 1.787). |
     | **(i) fixed population** | **PASSED.** Fixed 820-pair denominator: p=0.844, adv 74.15, ratio 1.503 — near-identical to variable-population (0.838 / 88.84 / 1.556). **Composition is NOT the cause.** |
     | smoothing sweep | **UNSTABLE.** `0.0` ⇒ INCONCLUSIVE (p=1.25, adv 9.03); `0.5` ⇒ SUBLINEAR; `1.0` ⇒ SUBLINEAR (p=0.766, ratio 2.071). |
     **Artifacts (server): `x3_control_known_truth.json` `048cf42f…`, `x3_fixed_population_and_occupancy.json` `394b7790…`; runner `x3_controls.py`. `x3_chain_rule_divergence.json` is UNMODIFIED — keep it so.**
     **Estimator reproduction against the published medians PASSED at tol 1e-9** (k=5 diff 2.22e-16, k=10 4.44e-16, k=20 1.78e-15, k=30 1.42e-14) ⇒ **this is estimator DESIGN, not a reimplementation defect.**
     **⚠ WHAT THIS DOES *NOT* MEAN: it is NOT a falsification.** A *LINEAR* result would have falsified our own framing. The estimator returns SUBLINEAR on **both** truth-modes, so the test **cannot discriminate** — the dependent-prefix story is **UNRESOLVED**, not refuted. **C1 and C2 are UNAFFECTED** (they do not rest on X3).
     **⚠ MECHANISM — A HYPOTHESIS, NOT A FINDING.** Sparse prefix contexts are the candidate cause: measured `frac_<5` **0.0154 (k=5) → 0.9055 (k=30)**, `effective_n/context` **64966 → 8.1**, so Jeffreys add-0.5 pulls large-k conditionals toward uniform. **Consistent with the measured deflation, but NOT tested against an alternative — do not state it as the cause without a discriminating control.** (Asserting a mechanism from plausibility is exactly M061/M093.)
     **🔴 STANDING CONSTRAINT C027 (added):** C3 may not be restated as SUBLINEAR unless the estimator **FIRST** recovers LINEAR on the known-truth control (`D_k = k·0.3389191441548814`) **AND** on the real-occupancy twin. **An estimator that has not cleared that gate cannot adjudicate C3.**
     **⇒ REPAIR IS A SEPARATE WORK ITEM** (2-3 different-type variants: estimator-family / support-conditioning / test-route), dispatched for reviewer design review. **It may NOT be used post hoc to restore the previously published verdict** — it clears the gate prospectively or it does not. **A failure is a legitimate outcome; if no variant clears the gate, C3 stays INCONCLUSIVE and the fallback is a two-claim paper or a reframed methods/limits contribution.**
     **⇒ LESSON (M093):** the verdict's supporting argument was that the bias INFLATES `D_k` and therefore made SUBLINEAR *conservative*. **That was measured backwards, and it came from a PROXY estimator, not the real one.** See §306 (retracted in place).
     **★★★ FINAL DISPOSITION — C3 REFRAMED, NOT DROPPED (D046).** Three gated repair variants were run; each had to FIRST recover LINEAR on the known-truth control AND the real-occupancy twin before touching real data (C027). **A** (estimator FAMILY change — concretely a **two-sample delete-one JACKKNIFE bias correction** on Laplace `alpha=1`-smoothed conditional KLs, directed terms projected to the nonnegative half-line) **FAILED both arms — real data never touched.** **B** (EXPOSURE conditioning to contexts with `n_P,n_Q >= T`) **FAILED** — the plain-IID arm passed at **NO** `T ∈ {5,10,20,50,100}` while the twin passed at all; **the excluded mass needed grows to `0.608` (plain) at k=30**, so the sparse contexts cannot be dropped without discarding most of the data. **C** (TEST ROUTE: nested first-order-Markov vs i.i.d., BIC) had a **USABLE, discriminating control** (synthetic IID ⇒ IID 12/12, median ΔBIC −21.77; synthetic dependent ⇒ Markov 12/12, ΔBIC 86689.85), and on real data **Markov beat i.i.d. 45/45 services at EVERY k=2..30** (k=30: 45/45, median ΔBIC 110091.14).
     **⇒ C3 IS NOW A METHODS/LIMITS FINDING (i) + AN EXISTENCE CORROBORATION (ii), NARROWED PER D053:** (i) the **PLUG-IN** chain-rule divergence estimator **cannot adjudicate** the dependent-prefix growth question at this k window, n, and occupancy-collapse curve — it DEFLATES large-k divergence — and this is **robust to two independent repair attempts (A, B)**, with B's excluded-mass curve showing the failure is **structural, not a tuning problem** (k=30 would need **61%** of transition mass discarded, and the plain arm **still fails**). **⛔ BUT "cannot adjudicate the QUESTION" OVERSTATES IT (D053): the parametric/model-internal route is NOT excluded — it is now a MUST-DO control that decides the wording.**
     **⇒ (ii) NARROWED — it is "the direction sequence is FAR FROM GLOBALLY i.i.d.", NOT "first-order" (D053).** C's i.i.d. null is a **SINGLE GLOBAL `p`** (`iid_ones/n_observations` over all 30 positions) while Markov carries a position-1 parameter plus one shared transition matrix ⇒ **a one-parameter global null is maximally weak: any position-wise marginal drift makes Markov win.** To support "first-order" specifically the null must be **position-wise i.i.d.** (independent across positions, marginal free per position), or a variable-order Markov selection must be used.
     **⛔⛔ D052's HETEROGENEITY CONFOUND IS **WITHDRAWN** (D053) — I asserted it and the simulation refuted it.** The BIC penalty is **2.43e-04** of ΔBIC at k=30 (`2·log N = 26.80` vs `ΔBIC = 110,091`), and a **pure heterogeneous-i.i.d. null** (each flow its own rate, i.i.d. WITHIN each flow, zero within-flow dependence) predicts `2·ΔLL/N = 3.09e-03` nats/obs against the observed **1.44e-01** — about **47× short**. Heterogeneity explains ~2%, so **real within-flow sequential dependence beyond between-flow mixing IS present.** **⇒ The dependence is real; it is the *"first-order"* LABEL that is unsupported.** The reviewers' own earlier critical was self-withdrawn on the same numbers.
     **⇒ GATE WEAKNESS (D052, STANDS):** `twin_services_used = [0, 1]` — the twin uses only the **two largest** services (n≈1.38M/360K vs plain's 200K) and is therefore **easier**; it passed at all thresholds while plain failed at all. The gate tests the well-occupied regime while what breaks the estimator is the sparse regime.
     **⇒ NOVELTY OBLIGATION (D052):** the sparse-regime plug-in KL/entropy bias is **classical** (Miller 1955; Grassberger 1988; Paninski 2003; Kraskov 2004) — framing must position (i) against it or the novelty claim does not survive one review sentence.
     **⇒ C3 IS RETAINED, NOT CUT (D053):** the growth-rate claim is correctly gone, but "the standard plug-in cannot adjudicate this on this data" is a real negative with practitioner value.
     **⛔ (ii) MUST NOT BE SOLD AS THE FINDING:** a first-order Markov law beating i.i.d. by BIC on real packet data is **expected** — packets are serially dependent by nature. (ii) is a **sanity corroboration, NOT a novel result**, and it **must never be read as a restored `SUBLINEAR`**. **The novel content is (i).**
     **⇒ Protected artifact `x3_chain_rule_divergence.json` is byte-unchanged (`c19d7392…`) across all three variants** (B verified before/after explicitly); all three new artifacts are separate, new-named files.
     **⇒ RULE (generalises): when a measurement instrument fails its own control, the failure is itself a reportable RESULT about the instrument, provided the failure is shown to be structural (robust to independent repair attempts) rather than a bug. Do not discard such a test as "merely inconclusive" — and do not let a corroborating side-route stand in for the claim the instrument could not make.**

## 🔴🔴 DISPATCH PRE-FLIGHT CHECKLIST — THREE QUESTIONS, ASKED IN THIS ORDER (M056)

**Why this exists.** Three separate failures this session shared one shape: **a rule was extracted from a lesson and remembered as CONTENT, but never converted into a GATE that every dispatch must pass.** Extracted rules did not fire at the moment of dispatch. The evidence, in order:
1. The rule "read field names, never recall them" was written — and then a spec was sent naming a key (`gate_fraction`) that does not exist in the target (the real key is `gate_fraction_both`).
2. The rule "a criterion that is a CONJUNCTION must name which condition it uses" was written — and then a spec was sent asserting a DPI inequality that is **not a theorem**.
3. The rule "**which side** an edit lands on must be stated" was written — and then a dispatch went out **without naming the side**, creating the fourth local/server divergence.

**⇒ THE FIX IS NOT "REMEMBER HARDER". A rule that lives only in memory fires only sometimes. Convert it into a FORM that is answered before every dispatch that touches an artifact.**

### The three questions — answer all three, in writing, before dispatching

**1. WHICH FILE(S)?**
Paste the **real key list read from the target file**, not a recalled one. If the spec names a field, that field's existence must have been established by reading the file in this session. **"I read the top level" is not enough — read to the DEPTH you will modify** (a top-level key list does not license a nested key name).

**2. WHICH SIDE?**
State **which tree the edit lands on** (local workspace vs server) and **the direction of any sync**. A declared authority is meaningless if the dispatch does not name the side it acts on. **The failure was never choosing the wrong side — it was choosing without writing it down.**

**3. DO THE CHECKS FAIL WHEN THE WORK IS NOT DONE?**
For every completion check, ask: *if the worker does exactly what I asked, does this pass?*
- **Deletion / absence** ⇒ assert absence with `test $(grep -c ...) -eq 0` or `! grep -q ...`. **Never bare `grep -c`** — it exits non-zero on zero matches and inverts the result.
- **Replacement** ⇒ two checks: new string present AND old string absent.
- **A "cannot be done" verdict is itself a claim.** Before accepting `NOT_PERFORMABLE` / "unobservable" / "no such values", check whether the quantity exists **under another name**. One such verdict was already false this session: a per-pair quantity was reported as nonexistent while another artifact declared it in its own object definition.

### Companion rules that belong to this gate
- **Verify the inequality is a THEOREM for the two objects actually named**, and that both objects are pinned unambiguously. A RELATIONAL word like "marginal" names a different distribution depending on what it is marginal to, and it named two distributions at once in the failure above.
- **A conjunction's threshold must name its condition, and default to the BINDING one.** Reporting a necessary-only condition's boundary as THE boundary understated a requirement by ~6x.
- **Scope a reconciliation to EVERY artifact changed since the last one**, not the list that happens to be recalled. The fourth divergence arose because a sync covered only the files a single dispatch had named.
- **★ A DECLARED SYNC DIRECTION IS ONLY SAFE WHILE IT MATCHES REALITY — RE-VERIFY IT BEFORE ACTING (M060).** The standing rule was `LOCAL -> SERVER, LOCAL authoritative`. Three consecutive remote-only edit rounds then put **eight fields on the remote that the local copy never had** (`pooled_cell_law_theorem_check`, `spec_correction_no_dpi_order`, `pooled_cell_law_is_the_theorem_case`, `vector_side_quantity_type`, `pairs_where_the_check_can_falsify`, `check_is_sanity_not_detector`, `not_performable_verdict_corrected`, `detector_qualification_rule`), while local `q1_vector_level_one_sided_full_n.json` stayed at its **2,620 B / Sep 13 23:12** original and local `x4_frontier_function.json` **did not exist at all**. **Running the declared rule literally would have overwritten the newest and most valuable content in the project with a stale file** — including the very rule that prevents this class of error recurring.
  **⇒ RULE: before any reconciliation, compare mtime + size + sha256 on BOTH sides for every in-scope artifact, and apply the direction PER ARTIFACT from what you observe. A direction that was correct when declared becomes destructive the moment a remote-only edit happens, and the declaration itself carries no expiry.**
  **⇒ Corollary: a correction that lands on the mirror instead of the authority is not "half done", it is INVERTED — the declared authority is now the stale side, and every rule that trusts the declaration points the wrong way.**
- **State known environment noise inside the spec** (`detect_image` failing on server 111 is routine and non-blocking), and add "if a command you were NOT asked to run fails, IGNORE it and continue".
- **★★★ A FIELD'S NAME IS A CLAIM, AND IT MUST BE VERIFIED AGAINST THE EXECUTING CODE PATH — NOT AGAINST INTENT (M067).** A mislabel is worse than a missing label, because **the name vouches for a property the value does not have**, so a reader who trusts it is actively misled rather than merely uninformed. **Three instances this session, all the same shape — a name vouching for a property its VALUE did not have:**
  1. **`lower_side_fraction`** named the band's **EDGE** (`tv_hat > T(n)`) as though it were a proven **lower bound** — relayed to the user as a bound. **The name said a lower bound; the value was EDGE occupancy — a detection threshold, not a bound at all.** Renamed to **`band_lower_edge_satisfied_fraction`**.
  2. **`NOT_PERFORMABLE`** asserted a quantity **did not exist** while another artifact's own object definition declared it — a negative claim wearing the authority of a status field. **A "cannot be done" verdict requires the same verification as a positive one.**
  3. **`_ref_radius`** asserted the **correct convention** while the executed call passed `alpha=0.05` (constant **2.7162**, instead of the per-law `alpha/2 = 0.025`, constant **2.9604**) — the suffix named the very property the number lacked, on **all 20 cells of the P0 headline table**. **The name vouched for the OPPOSITE of the convention the value used.**
  **⇒ WHERE THE ARGUMENT COMES FROM, NOT WHERE A FIELD SITS.** In every instance the value came from a call site whose arguments differed from what the field name (or the surrounding prose) declared. **Reading the artifact could not reveal this; only reading the call could.** So the check is: **`grep` the call site — the executing argument list — and compare it to the name.**
  **⇒ RULE: to establish what a field's value IS, read the call site that produced it, never the field's name and never the prose that declares the convention. A declared field is not evidence the code used it — that is now the FOURTH consecutive declared-vs-executed mismatch** (the 2x inlined radius; the capped lower-side join; the **alpha/4 over-split** that `test_not_doubly_conservative` guards; and the `alpha=0.05` under-split above). **A field that DECLARES a convention and a call that USES one are different objects; only the second produces the numbers.**
  **⇒ REMEDY, not just detection: a name that lies must CHANGE, not merely be annotated.** Make the name carry the executed value (`_alpha_0p025`) rather than trusting prose beside it — **printing the effective value next to a misleading name still misleads anyone who greps the suffix.**
- **★★ THE UNIT OF A DEFECT IS THE SHARED CODE PATH, NOT THE SITE OF DETECTION (M065).** A wrong `alpha=0.05` lived inside a shared `radius_for_n` helper called from a `for m in RUNGS: for k in KS` loop, so a defect **found in one cell** of the headline table was in fact present in **all 20**. Had the fix been scoped to the detection site, 19 defective cells would have shipped.
  **⇒ RULE: when a defect appears in one cell of a table, do not treat that cell as its boundary — ask what code path the defect is shared by, and derive the scope from the call graph.** Related, and useful in the opposite direction: **scope a fix by monotonicity where the correction is one-directional** — making the radius strictly larger can only *reduce* a pass count, so **cells reporting 0 need no re-evaluation**. That turned 20 cells into 4 and is the reason the bounded rebuild is cheap.
- **★★ "DONE" / "LANDED" / "DISPATCHED" IS NOT "THE INTENDED STATE HOLDS" — CHECK THE DESTINATION (M057, M060, M066).** Three instances: a fix **dispatched** but never landed on the authoritative side; a correction that **landed on the mirror** instead of the authority, inverting the rule; and a transfer worker whose status read **done** while its own body said **BLOCKED at transfer**, leaving both targets untouched. In every case a reader taking the status at face value would have believed the defect was closed.
  **⇒ RULE: when a task's success criterion is destination-side ("the target now carries X"), verify ON THE DESTINATION — and at spawn time confirm the worker actually holds the capability that direction needs. A read/execute plus local→server-upload toolset cannot close a server→local task however well it executes, and the mismatch is silent until the destination is checked.**
  **⇒ and do not generalise an absent tool into an absent capability: a registration tool missing is not a transfer path missing. Enumerate the read→write route and ATTEMPT it before concluding a move is impossible.**
  **★★★ CORRECTION (M069): this was NOT a capability mismatch — it was an UNTESTED REFUSAL, and my first framing laundered it.** I initially recorded it as "spawned without the capability the direction required". **False, and the facts say so:** the worker held `ssh_read_only` and **used it 14 times**; its only two `ssh_execute` calls were `find … | wc -l` **counts** — **it never issued a single `cat`/`head` of either target file, i.e. it never attempted the transfer it declared impossible**; local write demonstrably exists here (earlier workers wrote `memory.md` locally); and **the same transfer later SUCCEEDED** — X4 landed in the local tree at 01:01 with `scale_mismatch_17_5x` and `certifiability_gap_in_both_scales`, and parses, at the expected 14,893 B. It had generalised "`register_artifact` is not mounted" into "no transfer path exists" — but `register_artifact` is a **registration** tool, not a transfer mechanism, and the task never needed it. **`register_artifact` is a registry-registration tool; the task never needed it.**
  **=> RULE (replaces the wrong one): a capability verdict must be TESTED, not inferred. A capability limit is established only by an ATTEMPTED ACTION that fails — never by an absent tool name in an inventory. Before recording "no path exists", enumerate the read→write route and try it.**
  **=> and a RETROSPECTIVE rule that matters as much: when writing up a failure, do not classify an untested refusal as a provisioning mismatch. That framing is too generous to the process — it moves the fix from "attempt it before declaring impossible" to "provision better", which addresses a cause that did not exist.**
  **⇒ STILL OPEN for the OTHER file:** at the time of writing, `q1_vector_level_one_sided_full_n.json` local remains **2,620 B** with `grep -c "data-processing inequality"` = **1** and all eight correction fields at 0. X4 landed; **the vector file did not.** (See the file-level rule below — a later pull created a SUFFIXED SIBLING rather than overwriting, so this entry's remedy is superseded.)
- **★★★ A DEAD ARTIFACT CAN OUTLIVE ITS RETRACTION AT THE **FILE** LEVEL, NOT JUST THE FIELD LEVEL.** When a corrected copy must replace an existing one and the tool **creates a suffixed sibling instead of overwriting**, the superseded file **keeps the canonical name** — so anyone reading by filename gets the retracted content. Observed here: the retrieval appended `_eb0904`, leaving **two** files for one logical artifact, with the **stale** one holding the canonical name.
  **⇒ the field-level rule ("a dead value must not sit beside the live one") has a file-level twin: A DEAD FILE MUST NOT HOLD THE LIVE NAME. Suffixed-sibling creation turns a replace into an append, and an append is invisible to every name-based reader — the next worker, the Paper Agent, any script.**
  **⇒ REMEDY: after any replacement-style write, assert the CANONICAL path carries the new content — not merely that a file with the new content exists somewhere. This is the destination-side check applied to filenames.**
  **⇒ AND A TRAP IN THE CHECK ITSELF.** The corrected file contains the phrase "data-processing inequality" **twice**: once in a **legitimate** note explaining the sanity-check rule, and once in the **UNCORRECTED `non_interchangeability` claim** that asserts the very non-theorem this project disproved (78/990 per-pair inversions). **So a `grep -c "data-processing inequality" = 0` check would REJECT the correct file, and would be satisfied by a file that merely deleted the legitimate mention.** **⇒ a phrase-presence check cannot distinguish "the false claim is present" from "the false claim is quoted in its own retraction" — the check must target the SPECIFIC FIELD, never the phrase anywhere in the file.**
  **⇒ and the substantive consequence: the "corrected" copy still carries the uncorrected claim in `non_interchangeability` and `relationship_to_marginal`.** The eleven added fields are right and the `spec_correction_no_dpi_order` note is right, **but the original false sentence was never edited out** — so the file now asserts the non-theorem in one field and retracts it in another. **A retraction that does not remove the retracted text leaves the reader with both, and the false one is the one with the author's original voice.**
- **★★★ "CANNOT BE DONE" IS A CLAIM LIKE ANY OTHER — CHECK WHETHER THE QUANTITY EXISTS UNDER ANOTHER NAME (M057), AND WHETHER THE FILE WAS SIMPLY THE WRONG ONE (M058).** A `NOT_PERFORMABLE` verdict was false because the values sat in an artifact the worker had read but whose object it had not recognised. **And the inverse error is the same family: I declared X3 "not running" from a local `ls scripts/`, when the run had completed server-side via a deleted temp runner and left its log in `logs/workers/`.** **Before recording either verdict, look in the places you have not yet looked — for a "does not exist", check alternate names; for "not running", check the completion log, which exists even when the runner was deleted.**
- [failure pattern] infrastructure: the X12 detector script's DEFAULT train/test split was auto-derived across adjacent local-time (UTC+3) month buckets, which SHARE raw TIME_FIRST boundary values, so the strict raw-UTC guard `max(train TIME_FIRST) < min(test TIME_FIRST)` could not be satisfied by any clean adjacent-month split; fixed by resolving the D043 pre-registered split with one UNUSED buffer month (train 202406..202411, buffer 202412 unused, test 202501..202505) -> the guard is correct and must never be weakened; when a strict ordering invariant fails on a derivation the script chose itself, fix the derivation, not the invariant.

## 🔴 DATA-PULL GATE — X12_k5 must be read from local manifest path (D094)
The chain of record for X12_k5 is **local (git-tracked) + manifest sha + registry pointer**, all agreeing at
**193,228 B / sha `bebe6bf00ec3b48a541c948353b7db8574fa7721fec64199c614b239adf0a8d5`** (with `backfill_note`
and violations/trials provenance). The server scratch copy is 192,372 B / sha `71fa0233` (without the note).
**If any figure or table script pulls X12_k5 data from the server, it gets the version whose violations/trials
have no provenance marker.** Any downstream read must resolve through the manifest path (local), never a
hardcoded server path. The server copy stays un-updated — D094 rules the server is a compute scratch copy,
not a distribution surface.

## 🔴 PROVENANCE GATE — provenance.yaml before number-freeze
`provenance.yaml` must be built before any quantitative number is finalized in the draft. Every
figure/table claim needs an exp_id chain back to the registry. Run `auto_build_provenance` during the
first data-pull pass — not before (there is no draft text to trace yet), but as a mandatory
gate before numbers are frozen.
