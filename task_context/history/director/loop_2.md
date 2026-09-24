---
loop: 2
reason: max_wall_time
updated: '2026-09-17T08:38:41+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Paper body limit is 13 pages** (`main.tex` line 7: "Body limit: 13 pages. References and appendices unlimited."). The reviewed artifact currently ENDS THE BODY ON PAGE 14 — a pre-existing overrun, measured, not assumed. Do NOT trim reviewed text without the user's explicit A/B choice (he was asked and has not answered; he said "先不管这个吧").
- **Do NOT present the open-set floor as a new contribution.** Every ingredient is textbook (Le Cam two-point, union bound, TV convexity, triangle inequality). The paper wording must keep "standard aggregation … consequence … rather than a new construction". The user explicitly rejected packaging it as "our new bound".
- **The 45 known services define S_known; do NOT shrink K** without noticing the floor drops (S is defined over known-known pairs only).
- **Never materialize a project credential**, never retrieve a secret into context (C045). Read-only credential-free checks only.
- **Server 111's project dir is NOT a clone of the published repo** (C036) — no remote, no push from it.
- Paper/artifacts are English; user-facing replies Chinese.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (`connect.westb.seetacloud.com`), path `/root/eibo`, auth password. 1× RTX 5090 D, **idle** (2 MB used, 0% util, no processes) — idle is a plan property, not an omission; do NOT invent GPU work.
- Corpus: `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5` (3,544,625,537 bytes). Helper scripts in same dir (`excl_verify.py`, `hybrid_stress.py`, `lp_clean.py`, `mix_clean.py`, `final_compare.py`, `allbounds.py`).
- Detector script: project root `x12_detector_validation.py` — full CLI (`--h5 --train-months --test-months --output-json --output-csv --label-field --k-packets --holdouts --lgbm-rounds --cpu-only` …). Fits **multiclass** classifiers.
- Paper tree: `docs/paper/` (`main.tex` entry). Compile cycle **must** be pdflatex → bibtex → pdflatex → pdflatex, else every citation renders undefined.
- No active processes, no tmux, no cron.

### 3. 📊 Current state
- **Just finished:** paper scope-correction patch (3 sites: abstract, introduction, measurement_design §3.1 + a reproducibility note in §3.9). Applied, compiling clean, zero undefined citations. `tsybakov2009introduction` bib key was misspelled `tsyabakov…` and silently dropped — fixed.
- **Page forensics resolved:** the committed reviewed PDF *already* has a 14-page body (References start p17; 20 total). My edit added **zero** pages. A stale ROADMAP line claiming "Body 13 pages, 18 total" is WRONG — correct it.
- **Experiment STARTED but NOT RUN:** a genuine open-set rejection evaluation. Design: keep all 45 services as known (S unchanged), reserve corpus services outside the 45 as the unknown class, train a 45-class classifier, add a rejection threshold τ chosen on held-out data, measure error over M=46 equiprobable classes, compare to the 0.186 floor.
- **Design review dispatched to Reviewer** with four questions (a) macro vs pooled average for the uniform prior, (b) whether U must be a single distribution vs a service-mixture, (c) whether K should shrink, (d) confound control if the classifier trivially clears the floor. **Answers not yet received** — this was the Reviewer's last outstanding item before reset.
- Registry: no RUNNING/PREPARING experiments. 23 total, 22 done.
- Exploration artifacts registered: `openset_floor_assumption_free.md` (⚠️ banner: number superseded), `tightened.md`, `looseness.md`, `optimal_weighting.md`, `vs_measured.md`, `mixture_bound.md`, `four_constructions.md`. Manifest ~103 entries, zero stale.

### 4. 📋 To-do
- **Reviewer answers (a)–(d) arrive →** dispatch the open-set experiment to Main Agent with the settled definitions; report the measured error and its ratio to 0.186.
- **User answers 页数 A or B →** A = leave 14 pages; B = cut ~1 column from related_work tail or a contribution bullet (never a number). Then recompile with the full cycle and **verify by render** that the body ends ≤ p13.
- **User asks to fold the floor into the paper →** use the PLAIN version only (0.186, uniform weights). Do NOT use 0.363 (LP) or 0.372 (exclude-U + shortest path) — those stack three techniques on a line where I made three normalization errors.
- **ROADMAP still says floor = 0.363** — it is not wrong (that is the LP value) but is stale relative to the four-construction note; update when the exploration line closes.

### 5. 🎯 Strategic context
- **Core state:** paper is FROZEN at the weak-accept version except for this scope correction. Round 6 was weak accept 4/5 unanimous; the reviewers' clear-accept threshold is "one substantive methodological addition plus the §3.3 coverage calibration", and they NAMED a pairwise→open-set reduction as one option. That is exactly what the floor now supplies — as a stated standard consequence, not a new mechanism.
- **Decision chain:** D136 (impossibility claimed) → D138 (RETRACTED; the reduction is a valid corollary) → D139 (assumption-free floor, 0.118→0.186 via the input-filter fix) → LP 0.363 → mixture 0.3635 → exclude-U 0.372. Three structurally different arguments clustering at 0.363–0.372 is evidence that **~0.37 is the ceiling of the pairwise-certificate family**; do not expect re-weighting to close the remaining ~2× to the measured 0.737.
- **Measured comparison:** LightGBM macro multi-class error over the same 45 services = 0.7366. The floor is 25.2% of it (uniform) / 49.3% (LP). This measurement ALREADY EXISTED in `x12_detector_validation_k5.json` (timestamped 2026-09-14); three earlier notes wrongly claimed no multi-class run existed.
- **Pitfalls the next you is most likely to step into:**
  1. Trusting a workspace note over a direct read (the 13-page claim; the "no multi-class measurement" claim). Read the artifact.
  2. Building a baseline by hand instead of from the committed bytes (my 21-page phantom baseline).
  3. Reporting a derived range without the M=2 check — this session's errors were all factor-of-two normalisation slips, caught only by cross-computing the same quantity two ways.
  4. Overclaiming the floor's novelty or its tightness. Both the user and the reviewer will see through it, and the user has said so directly.
