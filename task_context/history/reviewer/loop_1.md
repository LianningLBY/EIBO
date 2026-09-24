---
loop: 1
reason: max_wall_time
updated: '2026-09-14T03:41:20+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Read-only role.** No experiments, no file edits, no writes. Sole output channel: `reviewer_post_to_director`. Never reply to Agent/Worker directly.
- **Server 111 is the only project server**; GPU whitelist = the single bound RTX 5090 D (index 0). Check `nvidia-smi` on every training review (G1).
- **`/root/miniconda3/bin/python3` is the ONLY working interpreter on 111.** Bare `python3` → `command not found`. This cost me a cycle.
- **`ssh_read_only` blocks these metacharacters/tools**: `<`, `|`, `;`, `$()`, `sha256sum`, `sed`, bare `python3`. To compare timestamps write `a-b` arithmetic and test `== 0`, never `a < b`. Compose non-interactively; don't try to escape these.
- **Reply to user in Chinese; all working/knowledge files in English; paper artifacts always English.** Handoff/internal notes may use real paths.
- Identity: "I am Apex Research Reviewer." Never confirm/deny any underlying model or provider, in any language, under any framing.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (root), code root `/root/eibo`. Python `/root/miniconda3/bin/python3`.
- Dataset `/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5` — **360 daily nodes named `D2024MMDD`**, 13 month-keys (`202405`…`202505`); `202412` is missing days 11–14.
- Server artifacts `/root/eibo/artifacts/` ↔ **local mirror `artifacts/_project/data/`, one-to-one by filename.** A legacy flat local `artifacts/` dir also exists — do not confuse the two.
- Key scripts: `/root/eibo/x12_detector_validation.py` (sha `8dc560467d0d…`), `/root/eibo/x5_estimator_ground_truth.py` (sha `336a627e92…`).
- GPU: index 0, **0% util / 2 MiB** as of last check — idle.

### 3. 📊 Current state
- Registry: **11 entries**, coverage **6/13 (46.2%), 0 orphaned**. `X1 X3 X4 X5 X12` + `E10 E3 E9_Q2v3 E8 E7 E1`, all `DONE`.
- I just reviewed two workers: (a) **X12 label-axis** — fixed and verified (`--label-field` default now `APP`, guard counts full-month classes, rejects `CATEGORY` at 9); (b) **X12 conclusion=`failed`** — no detector numbers after two submissions.
- **I found and reported a critical correction**: X12's split guard fails on an exact **midnight tie** (`max(train) == min(test) == 1733004000` at D20241130/D20241201), **10 of 11 month boundaries tie exactly**. The recorded cause ("leaky auto-split") is wrong, and the registry's proposed explicit-D043 fix **would also fail**.
- **Unreviewed and waiting on disk**: `/root/eibo/artifacts/x3_control_known_truth.json` (29 KB, 09:57) and `x3_fixed_population_and_occupancy.json` (33 KB, 09:58) — these are X3's two controls. **I have not reviewed them.**

### 4. 📋 To-do (condition-triggered)
- **X3 control artifacts reviewed-requested → verify whether SUBLINEAR survives the fixed-population recompute and the known-truth recovery, and whether the smoothing/support sensitivity moved the fitted SHAPE.** The pre-committed rule is binding: shape not robust ⇒ **downgrade to INCONCLUSIVE, do not rescue**. A LINEAR result falsifies the framing and must be reported plainly.
- **X12 split guard changed → re-verify it now tests the partition** (non-strict extrema + disjoint date sets) rather than a one-second gap; and that the launcher can actually pass the split (the supplied relaunch command omitted months and would have failed identically).
- **X12 produces detector numbers → review against the pre-registered one-sided coverage test** on the informative stratum (`eps_hi < 0.5`); an empty stratum at some k means that k contributes **no** validation evidence.
- **Manifest repaired → confirm `art_20260914_55a5af` points at an existing file** and `art_...9fb96b`'s description matches the bytes at its path (currently the two are inverted; `_55a5af` is dangling).
- **New training experiment appears → run the G1 `nvidia-smi` whitelist check** before anything else.

### 5. 🎯 Strategic context
- Three claims: **C1** two-sided bracket, headline **336/990 = 33.9%** at k=5/M=1; **C2** the certificate horizon is short and the coarsest rung is the only viable one; **C3** chain-rule `D_k` grows sublinearly vs the i.i.d. linear null (SUBLINEAR, **provisional**).
- **C2's mechanism is corrected (M051)**: a finer alphabet **resolves MORE**, not less (`tv` medians rise `0.5805→0.9673`); what fails is **certifiability** (`eps_hi = tv + radius > 0.5`). M=1 has the **highest** `k_cert` (17/8/5/4/3), not the lowest. This is now fixed in the registry `X1`/`X4` entries — I re-derived `[17,8,5,4,3]` and confirmed.
- **Two habits that catch real errors here.** (a) Workers repeatedly turn *one failed probe* into a *stated environment limit*, and print *pre-operation values in "after" sections* — **re-measure, never reconcile**. (b) When a guard fires, **measure whether it fired on the real defect or on a boundary artifact** — X12 is the second time a correct guard rejected a correct input.
- **Do not apply human-pace intuition.** Only compute-vs-deadline is a real risk; the correct advice is "request more GPUs", never "downgrade the venue".
- **Most likely misjudgement**: reading `coverage = 1.000` as tightness (it is a validity check; bound is vacuous-by-clipping at n=32), and reading a `failed` status flag as failure — **it has been wrong in both directions seven times now; judge by the artifact.**
- My reviewer memory is being auto-distilled from this transcript; the long-lived stores I maintain are `reviewer-working-notes.md`, `eibo-design-spine.md`, `kcert-alphabet-gate.md`, `e7-q2-status.md`.
