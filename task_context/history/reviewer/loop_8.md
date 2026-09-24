---
loop: 8
reason: idle_timeout
updated: '2026-09-22T13:21:32+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only.** Only output channel is `reviewer_post_to_director`. `save_project_file` is **NOT in my toolset** — memory persists via system distillation + the auto-memory dir; do not attempt it. I do have `Write`/`Edit` on the auto-memory directory and have been maintaining it.
- **CPU-only project.** GPU `111:cuda:0` idle is **CORRECT** — no GPU-eligible work exists. Never invent GPU work; the idle alert is a binding/timing mismatch (C055, do not re-triage per alert).
- **Never quote server-side paths in user-facing text**; replies in **Chinese**, artifacts/paper in English.
- `ssh_read_only` whitelist: `cat/ls/grep/find/head/tail/wc/stat/du/df`. **No `;`, `|`, `>`, no `sed`.** `python3 -c` blocked if it contains `open(`. Use `grep -n -A/B`, `cat -n` + `head|tail` substitutes.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. System `python3` has no scipy. **`sympy` is BROKEN** in that env (`ModuleNotFoundError: sympy.utilities`) — do algebra numerically.
- Corpus is **one level ABOVE** the project tree (`/efs/workspace/_corpus/…`); a project-tree search reports it missing and is wrong.
- Paper tree `docs/paper/` (entry `main.tex`); it compiles `docs/paper/figures/paper/`, **not** repo-root `figures/paper/`.
- Every relational claim carries a `falsifiers` field (build rule) — *"if a falsifier cannot be written, the sentence is not a claim."*

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-…-certification-grade/`; knowledge files at root, artifacts under `artifacts/` (+ `_project/{data,intermediate,report}/`).
- Registry 24 experiments; manifest `artifacts/manifest.yaml` ~163 entries.
- **Server 111 `/root/miniconda3` = sklearn 1.9.0** → produced the canonical ledgers. **Local `/app/.venv` = sklearn 1.9.1** → T1/T1b. Row-level cross-generation comparison forbidden; medians/counts allowed.
- No RUNNING processes, no active crons, no pending worker callbacks at handoff.

### 3. 📊 Current state
- Registry: 24 experiments, DONE 23 / **PREPARING 1 = `X9_C`** (withdrawn design, never ran; no honest terminal status; blocks `mark_project_passive`). Exclude when filtering.
- **D181 revision DELIVERED, awaiting PI review.** Paper sha **`5f08a9fb1cd3d277…`, 414,613 B, 24 pp, body p.13**, visual gate 24/24, no `.tex` newer than the PDF. Headline **0.186→0.197** (route change Eq6→m-free + Bonferroni ≥0.95 simultaneous), LP **0.363→0.375**.
- I just completed the ROADMAP hygiene review: verified build state, number sweep (**0.197 ×6, 0.375 ×3; 0.186/0.363/0.194 → 0 hits** in source *and* render), floors (S=**407.7497**, floor=**0.196981**), and the saturation separation (**13/20 cells with the advantage vs 7 without; max 0.696617 < min 0.728049 — perfect**).
- Flagged two one-clause, no-number-change items: (a) the "overstated by at most 0.012" sentence uses per-pair α=0.025 while S is computed at **0.05/990**, making the true expected overstatement **0.0000241** — conservative ~500×, not wrong; (b) lines 45 vs 47-48 need an object-distinguishing word ("simultaneous pair-level coverage" vs "aggregate excess").
- **Five D181 artifacts remain UNREGISTERED** (Exp1/2/3, balanced-accuracy follow-up, saturation sim). They are the evidence base for the delivered revision.

### 4. 📋 To-do (condition-triggered)
- **Any "violation"/"falsifier fired" claim → check METRIC and SIDE before accepting.** Raw error is class-imbalance-biased (recall_A 0.964 vs recall_B 0.244); use **balanced** error. And `eps_lo` is the *asymptotic* estimate — the finite-sample direction is the **upper** side. One test produced three counts this way (73 / 910 / 378 / true 0).
- **Any boundary claim over a 2-D grid → check EVERY cell**, not the axis that motivated it. Both prior single-axis statements were false.
- Anyone cites `0.186`/`0.363`/`0.194` → **superseded**; correct to `0.197`/`0.375`.
- Anyone writes "numerical coincidence" for B/C's identical CP interval → wrong; it is **structural** (CP is a function of count and n alone).
- A new worker reports `failed` → read artifacts + log first; `failed` is usually a transport label, work often complete.
- Any new artifact claimed → hash it; if registered, confirm `content_sha256` is **present** (several entries lack it entirely — that is a real defect class here).
- Paper bytes change → re-verify build state **and** run the process-vocabulary scan on the **rendered** PDF (`Round-`, `revision`, internal hostnames).
- Registering anything → grep the manifest for name **and** hash first (registration routes/copies).

### 5. 🎯 Strategic context
- Contribution type **measurement/rigour**. ROADMAP now opens **"D181 REVISION DELIVERED — awaiting PI review"**; the Round-14 internal "Accept 3/3" is **superseded** by the PI's Reject on those same bytes. Do not describe the paper as ready.
- **The route-mix pitfall**: the D181 1.059× ratio netted a **route** gain (+8.6%) against a **union-bound** cost (−2.3%). A union bound can only ever cost; a ratio across two changes hides both. Decompose before quoting.
- **Four times this session my own quick check was wrong, not theirs** (RNG stream omitted inner draws; bias-shift folded into a coverage probability; `penalty="deprecated"` read as the penalty; `q(0.975)/q(0.975)` as "normal theory"). Re-derive, then **audit the re-derivation**, and state which file/pairing/generation/level you read.
- **An artifact's summary/prose field is a CLAIM, not an observation** — repeatedly the source of inherited falsehoods. Check it against the artifact's own table.
- **Generations and streams multiply silently**: canonical D (n=5000) vs the coverage run (n=1000, no inner draws, sd 3.5% apart) vs T1 vs Eq6-vs-m-free routes. Naming which one is load-bearing is the single most common missing qualifier.
