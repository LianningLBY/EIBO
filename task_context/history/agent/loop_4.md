---
loop: 4
reason: max_wall_time
updated: '2026-09-22T13:02:48+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **`register_artifact` COPIES into a type-routed path (`data`→`_project/data/`) and SUFFIXES on collision.** It never binds the path you give it. Never re-register: that always makes a suffixed duplicate. The fix for an in-place-edited artifact is "write through to the registered path", never "repoint".
- **`content_sha256`**: the old blanket "never written" (C053) is TOO STRONG — two 2026-09-22 D181 entries (`91028b`, `a6078a`) DO carry it. Read the entry; never assume either convention. `manifest.yaml` is generated — **never hand-edit it.**
- **No writable path from my session to:** `ROADMAP.md` (Director-only), any manifest field, auto-memory files, or any remote file. No shell, no `Write` tool. Digests are always the Director's to compute.
- **`ssh_execute` = ONE non-empty single-line command.** No heredocs, no newlines.
- **Server 111 has NO `python3` on PATH** — use `/root/miniconda3/bin/python3`. 111 has three sklearn installs; the INTERPRETER is the provenance unit, not the host.
- **The paper `.tex` is the Paper Agent's** — D181 explicitly said "do NOT edit the manuscript yet". I touched nothing under `docs/paper/`. Any source change voids the SHA-bound visual receipt.
- **All D181 work is CPU-only and runs LOCALLY.** Server 111's GPU has no GPU-eligible work here; the recurring idle notice is a binding/timing mismatch, not a backlog. Do not manufacture a GPU job to silence it.

### 2. 🖥️ Infrastructure snapshot
- Server `111`, account `root`, project `/root/eibo` — but **all D181 jobs ran locally**, not there.
- Local Python: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3` (3.12.14, numpy 2.5.3, sklearn **1.9.1**; the venv lacks SciPy so the PYTHONPATH injector is mandatory).
- Corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5` — **one level ABOVE the project tree**; sha `6b323c4c…`. **⚠️ It has NO root-level `cols` node** — the old `node.cols.APP[:]` recipe FAILS on the local copy; read `APP`/`PPI`/`PPI_LEN` from each `/flows/*` table in bounded chunks. `PPI_LEN` is `(N,30)`, row 1 = direction, row 2 = size.
- Packer that defines the 32-symbol object: `scripts/xs_compression_early_readout.py` (sha `5b38a573…`).
- **Active processes: NONE. Workers: 0. Registry RUNNING/ALLOCATED: 0.** Disk 111 = 20% (25 GB free).

### 3. 📊 Current state
**D181 round complete — all five deliverables registered.** Round-14 was assessed **Reject** by the PI; these were the evidence-prep experiments (manuscript deliberately untouched).
- `art_20260922_f7853e` — Exp1 joint-coverage: Eq(9)+Bonferroni floor **0.197 uniform / 0.375 LP**, strictly positive, and **HIGHER** than the expectation-form 0.186/0.363 (Eq(9) is tighter than Eq(6) at m=32).
- `art_20260922_91028b` — Exp2 same-channel classifier (raw; carries the scale-mismatch caveat).
- `art_20260922_764458` — Exp2 follow-up balanced accuracy: **0/990 violations** (the raw 73 were a scale artifact).
- `art_20260922_a6078a` — Exp3 TV saturation: **large upward bias confirmed** (median tv_hat ≈ 0.998 at m=1M regardless of true TV).
- `art_20260922_d0bf02` — Coverage-language audit: 5 instances, all `discussion.tex` lines 140–150; body never states `0.9825 > 0.975`.
**Registry:** only `X9_C` (PREPARING/`killed`) — stale row for a withdrawn design, blocks `mark_project_passive`, no honest terminal enum value. Exclude when filtering.

### 4. 📋 To-do (condition-triggered)
- **Director replies on the four flagged decisions → act only on that reply.** The decisions are: (1) whether Exp2 needs any further recomputation (I believe it is now settled at 0/990), (2) exact wording for the Exp3 "estimator bias" qualifier, (3) where the high-probability floor (0.197/0.375) goes in the paper, (4) whether the 5 coverage-language sentences are a mechanical or structural rewrite.
- **A `[WORKER DONE]` with `Edit` in the summary → read the file and diff the KEY SET, not just the values.**
- **Any "register X" instruction → grep the manifest for the name FIRST**, and report the routed path the entry takes. Do not re-register blind.
- **Director says "verify/recompute" → read the file first.** Three of my re-raised items were already closed; the accurate phrasing is "I have not checked", not "open".
- **Any count/presence claim → parse and diff key sets**, never count with a regex.
- **Durable-memory writes are BLOCKED** (`Write` is not in my toolset); `save_project_file(file='memory.md')` is the only path — I used it twice this session and it works.

### 5. 🎯 Strategic context
**Decision chain:** D143 ladder abandoned · D144–D147 post-selection/efficiency routes closed · D166 m-free Hoeffding verified · D168 paper convention is UNCAPPED · D169/D170 Track 5 · **D181 = the Round-14 Reject response** (PI overrode the internal Accept).

**Track 5 is fully closed** (radius-form coverage measured; the convention is NOT cosmetic — 1.6pp between the two computable arms; three of five arms are ORACLE and must never be cited as achievable).

**Most likely misjudgement by the next me:** trusting a *summary* or a *count* over the file. This session's dominant failure was **checking a neighbouring object** — a name instead of a relationship, a count instead of a key set, a total instead of a per-class split. **The specific trap in D181:** the 73/990 "violations" are a SCALE artifact (error ∈ [0,0.5] vs TV ∈ [0,1]; the bridge is `(1−TV)/2`), and on imbalanced test sets you must use BALANCED error. Corrected: **0/990**. Do not revive the 73.

**Second most likely:** reporting an item as OPEN when I simply had not checked it.

**Third:** the recorded ~11.39% radius-form gap is NOT reproduced by the 2026-09-20 coverage run (closest pairing 12.65%, different generator pass, sd 3.5% apart). That is expected, not an error — the paper's "about 11%" is sourced to the n=5000 array and its own text names that pairing. **Do not import the new run's coverage numbers into that passage.**
