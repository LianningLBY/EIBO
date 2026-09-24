---
loop: 7
reason: max_wall_time
updated: '2026-09-19T20:24:31+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only**: `read_registry` / `read_project_file` / `ssh_read_only` / `tail_training_logs` / `read_roadmap` / local `Bash`+`Read`. **Only output channel is `reviewer_post_to_director`.** `save_project_file` is NOT in my toolset — memory persists via system distillation; do not attempt it.
- GPU whitelist `111:cuda:0`; card idle and that is **correct** — every T1/T1b/T1c/Track5 run is CPU-only. Do not invent GPU work. If a worker claims a GPU need, demand a written number against the ≤8 GPU-h rule.
- **Never quote server-side paths in user-facing text.** Paper/artifacts are English; user-facing replies Chinese.
- Server `111` is reachable via `ssh_read_only` (whitelist: cat/ls/grep/find/head/tail/wc/stat/du/df; **no `;`, `|`, `>`**). `python3 -c` is blocked when it contains `open(`.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. The system `python3` has **no scipy**.
- **Core standing rule (now a build rule):** every relational claim carries a `falsifiers` field — (claim, one-query falsifier, result). *"If a falsifier cannot be written, the sentence is not a claim."*

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-...-certification-grade/`; paper tree `docs/paper/` (entry `main.tex`), compiles `docs/paper/figures/paper/`, **not** repo-root `figures/paper/`.
- Corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5` (sha `6b323c4c…`). Sits **one level above** the project tree.
- CPU-only project. GPU `111:cuda:0` idle/allocated — a binding/timing mismatch, already raised as a platform decision; **do not re-triage per alert**.
- Registry 23 experiments, all DONE except stale `X9_C` (PREPARING, withdrawn design, never ran). Exclude it when filtering.
- **Memory namespace caveat (M167/M168):** my shell reads `/proc/meminfo` = 791 GB **host**, cgroup `0::/` with `memory.max` 90 GiB. The Director's container reports 31 GB and OOM-kills at a measured ~16 GB. **Never size an allocation from MemTotal/MemAvailable**; establish the namespace first.

### 3. 📊 Current state
- Just verified **Track 5** (block-bootstrap / sandwich / LOBO radius arms): `status=failed` is a **transport artifact — the work completed and all four artifacts registered**. Arm A restores coverage (0.994, CP lower clears 0.975); B and C do not (0.978 each).
- Track 5 is **not recorded** in ROADMAP or mistakes.yaml. Flagged two items: the transport failure, and the power formula using a **two-sample** form (799.44→800) where the coverage problem is **one-sample** (correct: 391.24→**392**) — conservative, label-only.
- Earlier this session: T1/T1b/T1c verified (M=2 and k=10 both show `upper ⊆ lower`, so joint == upper-only by set ceiling; M=2's 127 is a **mixed-convention** number — full-n upper, capped lower); T2 exact; T3's `C = 2 ln(2/α) = 8.764053`.
- **Paper is frozen, correctness-complete**, but **NOT deliverable**: Open Science clause carries `[ANONYMOUS-REPO-URL-TO-INSERT]` inside `\url{}` and is non-compliant.
- Pending: integration brief was **never delivered** to the Paper Agent (`created_new_session: true`); Director has re-queued it with the mixed-convention instruction.

### 4. 📋 To-do (condition-triggered)
- **Integration diffs arrive** → verify: the five patches, horizon qualification, convention labels on every table, coverage mechanism's **source attribution** (ladder is 400 replicates vs the paper's 200), grep for the three deleted `data/` filenames, and a `falsifiers` field on any new relational claim.
- **Any new sha quoted** → re-read the file at that instant and quote sha + mtime; the tree has moved mid-audit eleven times.
- **Anyone cites "0 crossings"** → wrong; exactly **1** pair crosses (21,23).
- **Anyone argues invariance from "uncapping only raises `eps_lo`"** → false, 38/990 lower it; argue from the margin (0.0755 vs 0.05 gate).
- **A new worker reports `failed`** → read the artifacts and the log's token counts first; check whether work completed before the disconnect.
- **Publish/submit asked** → the Open Science clause is the one blocking manuscript-level defect; the repo is a user action.

### 5. 🎯 Strategic context
- **Contribution type: measurement/rigour**, and T1/T3 push it somewhat beyond that. Four "raise it to clear-accept" routes were audited; none open. **Do not manufacture method novelty.**
- The session's **dominant defect class, named and now proceduralised**: *the values are checked, the relation between them is not.* Every finding this session — the false monotonicity claim, the withdrawn coverage mechanism re-derived (M169), the unrecorded invariant, the unrecorded CFP rule, the wrong-namespace memory figure — had that shape. The fix is a **field**, not a rule.
- **Retracted, must not be revived**: the pairwise→open-set impossibility claim (D138); the bias-driven coverage-breach mechanism (D155) — the supported mechanism is a **widening lower tail**; the `0.1330` memo figure; "the horizon is dissolved" (M=1 only); "compliant by disclosure"; "uncapping can only raise".
- **My own errors this session** (both correctable by the falsifier rule): a 791 GB host reading used to size a container job, and a 3× constant error from re-deriving T3's formula from the brief instead of from `eq:mfree`.
- **The next "you" is most likely to err by accepting a correct conclusion resting on an unchecked premise** — and by quoting a sha or page count from prose rather than re-reading the file. Re-read before asserting; state the predicate and the statistic in the same sentence as the threshold.
