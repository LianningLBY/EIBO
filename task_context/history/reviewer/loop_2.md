---
loop: 2
reason: max_wall_time
updated: '2026-09-14T20:08:52+00:00'
---

### 1. 🔴 Hard constraints / red lines
- GPU whitelist: server 111 has exactly 1× RTX 5090 D (32607 MiB) at index 0. Every training review MUST `nvidia-smi` to confirm the process is on cuda:0 and CPU-only experiments read 0% util / ~2 MiB. A GPU outside the whitelist = critical.
- Two-tree layout is REAL and load-bearing: local = `/efs/workspace/projects/epsilon-indistinguishability-.../` (register_artifact creates `artifacts/<EXPID>/data/` nested), server = `/root/eibo/` (flat `artifacts/`). A runner reading a hardcoded path can fail on one tree and pass on the other. The fix pattern is `resolve_existing_path(candidates)` with FLAT first, then nested, error listing every path tried.
- Registry field names: top-level keys ARE the experiment IDs. There is NO `exp_id` field — filtering `{"exp_id": X}` returns 0 always. `read_registry(filters={"status": ...})` is the correct filter shape.
- `update_registry(field='metrics', value=...)` REPLACES the whole block, does NOT merge (D069). Read whole → merge by hand → write whole.
- Append-only files (findings.md, memory.md, mistakes.yaml, decisions.yaml, constraints.yaml, registry.yaml): no whole-file restore/rewrite (D077). A restore must prove the target strictly contains the current file.
- Only output channel = `reviewer_post_to_director` (text + project). Never modify files, never run experiments.

### 2. 🖥️ Infrastructure snapshot
- Server 111, account root, code root `/root/eibo`, python `/root/miniconda3/bin/python3`.
- Primary H5: `/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5` (sha 6b323c4c…). X11 corpus: `/root/autodl-tmp/eibo/data/cesnet-quic22-explicit-v2/XS/CESNET-QUIC22-XS.h5`.
- X3/X6 shared cache (volatile, /dev/shm): `/dev/shm/eibo_x3_chain_rule/{merged.pkl, ledger.json, results.pkl}`.
- Server artifacts: `/root/eibo/artifacts/` (flat). Local knowledge files under the project root; paper tree at `docs/paper/main.tex`.
- No live GPU training at handoff — X12 k=5 is the only upcoming GPU job (must NOT pass `--cpu-only`; ronetc needs cuda:0).

### 3. 📊 Current state
Just finished: X13 missing-mass review (flagged critical — bootstrap interval measures wrong quantity), X9_E completion review (clean, negative→identifier-effect finding), ROADMAP dashboard review (D088 landed).
- X9_E DONE, conclusion negative: at matched declared m, SNI-dependent arm separates from SNI-independent arm at tv_hat level (median delta 0.03→0.36 before saturation). Identifier effect real; eps_hi unavailable at every rung. Claim boundary: "identifier changes radius-free tv_hat" ONLY, never "destroys ε-certificate".
- X13 DONE: missing-mass point estimate 0.202% CORRECT (f1/n = 10198/5039616), but bootstrap CI [0.094%,0.098%] is WRONG — multinomial resample of observed distribution can't see unseen species; interval excludes its own point estimate by 2.1×. Critical pending fix (implement Eriksson-type, or drop the interval).
- Coverage: C2 100%, C3 100%, C1 ~9/12 done. X8/X13 unlinked in plan (X13 now done, not yet linked). X11 PREPARING but actually complete (unmanaged worker run, no lifecycle). X9_C killed.
- Blocked: X12 Stage 2 containment statistic — `deferred_floor_test()` stub returns DEFERRED unconditionally.

### 4. 📋 To-do
- X13 bootstrap fix lands → verify the new interval contains the 0.002024 point estimate, or that the interval was removed and only point estimate + 1:10/1:100 sensitivity remain.
- X12 Stage 2 implemented → verify `deferred_floor_test()` computes real containment (per-pair eps_hi from rebuilt X1, floor (1−eps_hi)/2, one-sided binomial α=0.05), not DEFERRED.
- X12 k=5 GPU run starts (no --cpu-only) → G1 whitelist check via nvidia-smi (must be cuda:0, single 5090 D).
- X9_C/X11 state change → review; X11 status is misleading (complete but PREPARING).
- paper_provenance.yaml appears → check exp_id coverage, verify cited exp_ids exist and aren't invalidated.
- x3_axis_validation / x3_parametric_growth re-run pull lands → verify server bytes (sha) match, don't hand-edit parametric growth artifact.

### 5. 🎯 Strategic context
Three claims (C1 bracket 33.9%, C2 short certificate horizon, C3 methods/limits). C3 reframed (D046) from sublinear-growth to "standard estimator cannot adjudicate the growth question" — legitimate, robust to two repairs. C3(ii) BIC-vote is DEAD evidence (heterogeneous-iid reproduced the vote with zero dependence; D055/D064).
Dominant defect class this whole session (7 instances): a check that cannot exercise its own failure mode — X13's bootstrap is the latest. Rule A: ask "what would this have to output for the hypothesis to be false?" Rule B: scan printed values for constants/boundaries/non-monotone jumps and explain them.
Recurring traps: worker `failed` flags are unreliable (judge by artifact, not exit code); "match the field, not the digits" (a number appearing as a substring ≠ a field match); verify the SERVER bytes, not the local copy, before claiming a fix landed; a CI/decision note claiming "changed to X" is not proof the field was actually changed — re-read the file.
