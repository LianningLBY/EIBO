# Operator runbook: the two blocked experiments

Prepared 2026-09-16. For anyone with access to the project's bound server. No access to this
platform is needed to execute these; the results come back as two JSON files.

## Why this exists

Two experiments are ready to run but cannot be executed from the analysis environment: the ~3.5 GB
primary corpus exists only on the server, the configured SSH key is absent locally, and the worker
dispatch path is currently not mounting a remote-execution tool. The scripts themselves are
reviewed and unchanged — do not edit them. Both are deterministic (fixed seeds) and both write a
single JSON artifact plus a one-line summary to stdout.

## Experiment 1 — known-truth coverage calibration

**Script:** `coverage_calibration_timing.py` (12,858 bytes; sha256 `b1dd05e1...` — verify before running)

**What it does:** draws synthetic flow pairs with a *known* true total-variation distance, then checks
whether the certified bracket actually covers the truth. 20 i.i.d. cells (16 TV×N grid + 4 unequal-n
specs) and 80 dependent cells (4 TV × 4 N × 5 block sizes `{1,2,4,8,n//10}`), 200 replicates each,
with Clopper-Pearson intervals per coverage fraction. It also measures the corpus autocorrelation
first and builds the dependent arm from those measured values, and it writes its decline prediction
into the artifact **before** measuring.

**Requirements:** the corpus at one of its two hardcoded paths, `numpy`, `scipy`, `tables`, and the
project package importable at `/root/eibo/src`.

**Run:**

```bash
cd /root/eibo
python3 -c "import numpy, scipy, tables; print('deps ok')"   # confirm before the real run
timeout 1800 python3 coverage_calibration_timing.py
echo "EXIT:$?"
```

**Expected output:** `artifacts/coverage_calibration.json`, plus a one-line JSON summary on stdout.

**What to send back:** the JSON file itself (or its stdout summary if the file is large), and the exit
code. If the run is cut off at the 1800 s timeout, report "started correctly and still running" —
do not report it as a completed result.

**What the result decides:** the paper calls itself *certification-grade* on the strength of the
upper side's derivation. This is the check that demonstrates coverage empirically. A covering bound
supports the term; a non-covering one is a finding that must be reported as such, not tuned away.

## Experiment 2 — X9_C cardinality vs SNI attribution

**Script:** `x9_cardinality_control.py`

**What it does:** settles whether a previously measured +0.39 TV shift is attributable to **alphabet
cardinality** or to **SNI dependence**. The original comparison changed both at once: one arm used a
32-symbol alphabet while the other partitioned on a 256^10 domain (24 orders of magnitude finer) and
its upper bound was clipped at 1.0 on 100% of 703 pairs, so the shift is dominated by a saturating
radius term and carries no resolved separation information. The script runs two matched arms —
(a) cardinality-matched but SNI-dependent, (b) same 256^10 domain but random identifiers — and the
two falsification conditions are stated in its docstring.

**Run:**

```bash
cd /root/eibo
python3 x9_cardinality_control.py --smoke   # fast sanity check first
timeout 3600 python3 x9_cardinality_control.py
echo "EXIT:$?"
```

**Expected output:** the artifact path and its sha256, plus an `outcome` field, printed as one line
of JSON on stdout.

**What to send back:** that JSON line, the artifact file, and the exit code.

**What the result decides:** the paper attributes part of its divergence behaviour to SNI-based
separation. If cardinality alone explains the shift, that attribution must be corrected — this is a
substantive question about a claim, not a wording matter.

## Reporting back

For each experiment: the exit code, the artifact JSON, and the one-line stdout summary. If either
fails, the verbatim error is more useful than a summary — in particular for the interpreter, since
the server-side Python has never actually been confirmed to execute from the analysis environment.
