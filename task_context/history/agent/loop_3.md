---
loop: 3
reason: max_wall_time
updated: '2026-09-20T09:02:34+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **`register_artifact` COPIES into a type-routed location (`data`→`_project/data/`, `report`→`_project/report/`) and SUFFIXES on collision.** So: it never binds the path you give it; a manifest can never bind a top-level `artifacts/` file; repointing can only ADD a copy, never relocate; registering twice always makes a suffixed duplicate. **The fix for any in-place-edited registered artifact is always "write through to the registered path", never "repoint".** Read the hash back over the path the ENTRY names (usually the routed copy).
- **`content_sha256` is NEVER written by the tool** (C053, ~11 instances). Treat a hash-less entry as the expected initial state. **`manifest.yaml` is generated — never hand-edit it.** Retirement is a convention I cannot execute: `superseded_by` + `retirement_note` + **`path: null`**; null paths on RETIRED entries are NORMAL and must not be "corrected".
- **No writable path from my session to:** `ROADMAP.md` (use `update_roadmap`, Director-only), manifest fields, auto-memory files, or any remote file. No shell, no `Write`. Digests are ALWAYS the Director's to compute — do not restate structure as byte-identity.
- **`ssh_execute` = ONE non-empty single-line command.** No heredocs, no newlines, no file bodies.
- **Server 111 has NO `python3` on PATH** — use `/root/miniconda3/bin/python3` absolute. 111 has THREE sklearn installs; the interpreter path is load-bearing, not the host.
- **Do NOT re-register the probe family** (`sklearn_solver_probe_*`, `lower_side_classifier_environment_canonical_111_*`). Duplicates already exist; consolidation is pending.
- Paper is FROZEN; `.tex` is the Paper Agent's and I must not touch it. Its visual gate is pinned to a sha — any source change voids the receipt.

### 2. 🖥️ Infrastructure snapshot
- Server `111`, account `root`, project `/root/eibo`. Interpreter `/root/miniconda3/bin/python3` (python 3.12.3, numpy 2.3.2, scipy 1.18.1, **sklearn 1.9.0**). Local container: `/app/.venv/bin/python3` (3.12.14, numpy 2.5.3, **sklearn 1.9.1**) — but the venv lacks SciPy; `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages` injects the stack, and **`/usr/local/bin/python3` resolves to the same EFS site-packages bit-for-bit**.
- Corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5` — **one level ABOVE the project tree**; sha `6b323c4c…`. Read via `node.cols.APP[:]`, never per-table.
- **Active processes: NONE. Workers: 0. Registry RUNNING/ANALYZING: 0. GPU idle and correctly so** — every open line is CPU-only.
- Key artifacts: recovered stream `_project/intermediate/track5_skewness_D_5000.npy` (sha `2445c866…`, 5000-D, registered `art_20260920_a6e233`); re-run confirming copy `art_20260920_7376cc`; probe `sklearn_solver_probe_111` (`art_20260920_69abb9`); producer `art_20260920_7f5f57`. Manifest 156 entries, all hashes populated.

### 3. 📊 Current state
Just closed the **Track 5 provenance thread** (all 20 entries hash-verified, copies bit-identical at `6558da38…`, `provenance` rewritten to carry both the recovery and the bit-identical reproduction). Before that: a full-grid recompute line, T1/T1c lower-side work, and an sklearn environment probe on 111.

**`X9_C` is still `status: PREPARING`, `conclusion: killed`** — the stale row blocking `mark_project_passive`. It records a *properly specified then deliberately killed* design (the M055 class: one treatment changing two things); the enum simply has no terminal value for "killed before submission".

**Pending on the Director (I have no write path for either):** retire the suffixed duplicates `art_20260920_c6f9ab` and `art_20260920_e84e87`; declare the `.upload.guard` residue text I drafted; populate hashes on my last two registrations (`69abb9`, `7f5f57`).

### 4. 📋 To-do
- **Any `[WORKER DONE]` with `Edit` in the tool summary → read the file and diff the KEY SET, not just values.** Two workers this thread edited after I read them; one replacement silently dropped three fields.
- **Any "register X" instruction → check the manifest for an existing entry FIRST** (`grep` the name), and report the path the new entry takes; do not re-register blind.
- **Director says "verify/recompute" → read the file first.** Three of my re-raised items were already closed; the accurate phrasing is "I have not checked", not "open".
- **Any count/presence claim → parse and diff key sets.** Never count with a regex; three runs gave 6, 7, 8 for one file.
- **Any radius/coverage claim → confirm `bound/true_TV` and state whether the quantity is an ORACLE (uses `TRUE_TV`) before quoting coverage.**

### 5. 🎯 Strategic context
**Decision chain:** D143 ladder abandoned · D144–D147 post-selection/efficiency routes closed · **D166** m-free Hoeffding bounds verified, C2's mechanism wrong, integrated in `results.tex:176–220` · **D168** paper's convention is UNCAPPED. **Track 5 closed:** canonical SD `0.016078662416248272`; skewness `-0.0088933` with CI containing zero (**sign NOT resolvable at n≤5000** — the sequence crosses zero twice); no stream fork (the 11% sd decline is drift, and the trajectory is **non-monotone**, dipping at n=3000).

**OPEN — do not treat as settled:** the **radius-form question**. Symmetric and one-sided radii do NOT coincide even under perfect symmetry (`F⁻¹(0.9875)` vs `F⁻¹(0.975)`, ~12.6% under normality, **measured ~10.7–11.4%** on the registered array, all pairing choices agreeing the one-sided form is smaller). The paper's deleted clause was **false empirically, not just algebraically**. **B/C's radius sits BETWEEN the two forms**, which is why they land slightly above nominal — so "B and C shrink the radius, therefore they fail" is wrong twice over. **The three arms do not share a radius form** (A is a `|·| @ 0.975` quantile; B/C are `z`/`t × SE`), so there is no single "the symmetric radius".

**Most likely misjudgement by the next me:** trusting a *summary* or a *count* over the file. This thread's dominant failure was **checking a neighbouring object** — a name instead of a relationship, a count instead of a key set, a sibling's revision instead of the cited path, a top-level key instead of a nested one, the wrong file for a field, and a statistic two hypotheses both predicted. Second most likely: **reporting an item as OPEN when I simply had not checked it.**
