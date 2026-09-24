---
loop: 1
reason: max_wall_time
updated: '2026-09-14T19:30:16+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **GPU whitelist**: only `cuda:0` on server `111` (1× RTX 5090 D). No other GPU exists in the project binding.
- **X12 k=5 is CPU-fallback**: lightgbm fell back to CPU (no OpenCL), so the GPU was idle during that run. This is expected behavior, not a stall.
- **D087 claim boundary**: the X9_E channel-sensitivity finding is at `tv_hat` (radius-free) level ONLY. The paper may write "identifier content changes radius-free separation beyond cardinality" — must NOT write "SNI destroys the ε-certificate" or "degrades the bracket."
- **X3 conclusion = "success"** refers to the reframed C3 (methods/limits finding), NOT the original sublinear growth-rate claim. Notes field carries the D085 audit explanation.
- **Do not run k=5 again unless Director explicitly requests a GPU re-run** — the CPU X12_k5 already produced valid containment evidence (all reject_null=false, 340 informative pairs).
- **ROADMAP is stale on X12 Stage 2** — it still says "stub returns DEFERRED unconditionally" and lists it as BLOCKED. The registry, source code, and artifact all confirm Stage 2 is implemented and ran successfully. The Director was informed three times; awaiting ROADMAP update.

### 2. 🖥️ Infrastructure snapshot
- **Server**: `111`, working directory `/root/eibo`
- **Python**: `/root/miniconda3/bin/python3` (used in all experiment commands as absolute path)
- **Conda env**: base (no venv; commands use `cd /root/eibo && /root/miniconda3/bin/python3 <script>`)
- **Data**: `/root/eibo/data/` (CESNET-QUIC22 XS at `/root/autodl-tmp/eibo/data/cesnet-quic22-explicit-v2/XS/`)
- **Artifacts (server)**: `/root/eibo/artifacts/`
- **X1 rebuilt data**: `artifacts/q1_lower_side_full_n.json` (flat path, FLAT-FIRST resolution via `resolve_existing_path`)
- **Active processes**: NONE — all experiments completed, no crons active, no workers running
- **Git**: local branch `main`, last pushed commit `f2b3464`. Director has 8 local commits; push when convenient.

### 3. 📊 Current state
**All experiments are DONE.** No RUNNING, ALLOCATED, or QUEUED experiments exist.

| Exp | Status | Conclusion | Key finding |
|-----|--------|-----------|-------------|
| X9_E | DONE | negative | Dose-response falsified: arms separate at matched m → genuine identifier channel effect (tv_hat level only, D087) |
| X12_k5 | DONE | success | Containment holds: 8/340 violations (lightgbm), p=0.995, reject_null=false at all holdouts |
| X12 | DONE | — | Stage 2 implemented, metric payload added, k=15 stratum empty (vacuous) |
| X3 | DONE | success | Reframed C3: methods/limits finding (D046/D085) |
| X6 | DONE | success | Divisibility lower bound non-empty at large k → C2 "horizon is short" is measured |
| X9 | DONE | negative | +0.39 delta confounded by 1e24 alphabet ratio; attribution open |
| X11 | DONE (PREPARING in registry) | — | Feasibility confirmed; 16% vs 34% upper fraction, but 64.7% gap explained by n-stratification |
| X9_C | PREPARING | killed | Superseded by X9_E |

**Pending**: Nothing. No workers, no crons. The Director's last instruction was to implement X12 Stage 2 (already done — reported three times). Awaiting Director acknowledgment and direction on X11 or remaining CPU tasks.

### 4. 📋 To-do (condition-triggered)
- **Director confirms X12 Stage 2 is done** → update ROADMAP to close the BLOCKED_ON entry; proceed to X11 feasibility implementation or remaining CPU comparisons (X2/X7/X8/X10/X13)
- **Director requests GPU re-run of X12_k5** → register new experiment, allocate, submit with `--k-packets 5` and NO `--cpu-only` flag so ronetc trains on CUDA
- **Director greenlights X11** → dispatch Worker to implement the full X11 protocol on CESNET-QUIC22 (public corpus, same channel/split); non-reproduction is a finding, not to be tuned away
- **Git push requested** → push main; 8 Director commits are local at `f2b3464`
- **x3_axis_validation pull** → server has re-run bytes (123,295 B / 4061258e); local copy is stale; pull when the file is next edited
- **x6 hardcoded paths** → apply `resolve_existing_path` (flat-first) to x6's four input paths when the file is next edited

### 5. 🎯 Strategic context
**The three claims (C1/C2/C3) are all supported by completed experiments.** The project is past mechanism validation and into comparison/assembly/writing territory.

**Critical-path items remaining:**
1. X11 full implementation (strongest answer to "one dataset" concern)
2. X2/X7/X8/X10/X13 — CPU-only comparisons and assembly for C1 coverage (currently 58.3%)
3. Registry/plan linkage backfill so coverage matrix reads real state
4. Paper: channel-sensitivity section for X9_E (scoped to tv_hat per D087)

**Pitfalls the next "me" will likely hit:**
- **ROADMAP says X12 Stage 2 is blocked** — it is NOT. The Director has been told three times. Do not dispatch a Worker to implement something that already exists. Verify against `grep DEFERRED x12_detector_validation.py` (zero matches) and registry metrics `D070_STAGE_2_VERIFIED_FROM_SOURCE`.
- **"Check that cannot exercise its own failure mode"** is the project's dominant defect class (6 instances). Before treating any control or test as evidence, ask: "what would this output if the hypothesis were false?" If the answer is "nothing it could output," it is not a test.
- **Two-tree layout**: local artifacts/ vs server /root/eibo/artifacts/ can diverge. Always use `resolve_existing_path` (flat first). The cross-tree audit found one snapshot-only defect and four silent-fallback sites (deferred).
- **memory.md is 207KB** and has lost sections in past rewrites. After any rewrite, grep the header checklist at the top of the file to confirm nothing was dropped.
- **Object substitution warnings travel with every containment number**: the pair error is a PROXY (macro-average of two per-service errors), and classification_error is CLOSED-SET while the floor is OPEN-SET.
