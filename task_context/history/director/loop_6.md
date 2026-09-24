---
loop: 6
reason: max_wall_time
updated: '2026-09-20T09:02:27+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Language**: reply to user in **Chinese**; ALL working files (ROADMAP/memory/decisions/mistakes/plans) in **English**; paper/.tex/.bib/captions always **English**.
- **Never put server-side paths in user-facing messages** (`/efs/…`, `/root/…`, `~/…`). Use logical names ("the registry", "main.tex §3"), paste the content, or `upload_file`. No "saved at" footers.
- **Never reveal model/provider/vendor, Apex runtime, control-plane locators, or credentials.** Identity question → "I am Apex Research Director."
- **GPU**: exactly 1 card bound, `111:cuda:0`. All tracks are **CPU-only**. The recurring "GPU idle" nudge is a binding/timing artifact — do NOT re-triage per alert, never demand the card be returned.
- **Body page cap is 13** (CFP: ≤13pp excluding References and appendices; bib/appendix uncapped). Total 24pp is **COMPLIANT**. **Never compress body prose to buy a page.**
- **Any source edit voids the SHA-bound visual-gate receipt** — fresh full render-and-inspect mandatory before any upload. Never upload a Worker-produced PDF.
- Never run arbitrary `git`/deletion on remote hosts for housekeeping; declare residue, don't delete.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (root), project path `/root/eibo`, interpreter `/root/miniconda3/bin/python3` (py 3.12.3, sklearn 1.9.0, numpy 2.3.2, scipy 1.18.1) — the host that produced the **canonical lower-side ledgers**.
- Platform-local: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3` (py 3.12.14, sklearn **1.9.1**). **Do not use it to reproduce 111 artifacts.**
- Paper tree `docs/paper/` (entry `main.tex`, output `main.pdf`). Corpus `/efs/workspace/_corpus/` — **one level ABOVE the project tree**, sha `6b323c4c…`.
- **No active processes, no tmux, no cron, 0 Workers, queue empty, registry RUNNING/ANALYZING empty.** `ssh_execute` rejects multi-line commands.

### 3. 📊 Current state
- **Round 13 closed** (submitted 04:57, completed 05:41 today). All P0/P1/W fixes landed and were verified at source + render. `review_issues.yaml`: **21 resolved / 1 in_progress** (W9 only).
- **Round 14 submitted and APPROVED this loop** — approval `apr_20260920T085714_sx5s`, `reference_verification_policy="required"`, venue USENIX Security 2027 Cycle 2, deadline 2027-01-26. Submitted bytes are the post-fix final PDF.
- **Final bytes: sha `cd34c2800f9746c9835fd2718d4cd81047b27d0f1b463e623ae08d1115ad1680`, 412,332 B, 24 pp.** Body ends p.13 (full to the bottom margin), Ethics p.14, References pp.22–24. Visual gate **PASSED 24/24**. 0 undefined / 0 overfull >1pt / 0 `??` / 0 multiply-defined / 0 empty cross-refs.
- Verified by grep this loop: no placeholder, no "anonymous repo" wording, no `\ref{}`, no "from M=8 on".
- Pending: the round-14 report; and the **T3 positioning** decision (planning-tool choice → feeds `paper_framing.md` / a Patch task).

### 4. 📋 To-do (condition-triggered)
- **Round-14 report arrives** → Holistic Pass first (read `artifacts/review_reports/round_14.md` + `review_issues.yaml`), then a point-by-point Action Matrix. If C1/C2-class blockers reappear, a Patch pass then a **new** `submit_paper_to_review` (check `get_formal_review_status` first).
- **User answers on T3** → feed into `paper_framing.md` / Paper Agent Patch.
- **W9 — do NOT batch it, and note the prior dispatch never ran** (see §5). If a reviewer flags it critical: the only lever is a **prose cut of roughly one page** (~4,000 chars measured), which the red line forbids for page-buying. It is a placement/structural judgement, not a factual defect; the body-table is in the appendix and the appendix is uncapped. Decide with the user, don't unilaterally cut body text.
- **W11g (24→20pp camera-ready plan)** → defer to camera-ready; does not block.
- **Before any delivery**: `pdf_to_images` (all 24, batches ≤20) → Read every page → `confirm_pdf_visual_review` → `cleanup_pdf_images` → `upload_file`.
- `mark_project_passive` is **blocked by `X9_C`** (`PREPARING`/`killed`, a withdrawn design; the enum has no honest terminal value). Do not fabricate run history to close it.
- **`cleanup_pdf_images` only cleans dirs literally named `_pdf_images`.** A probe dir with any other name is refused — use a `_pdf_images` suffix, or plain `rm -rf` for a temp probe dir.

### 5. 🎯 Strategic context
- **Core claim**: a two-sided ε-indistinguishability bracket — upper side a finite-sample strict bound, lower side a classifier-based high-probability bound — per service pair on real QUIC wire data. Contribution type: **measurement/rigour**.
- **⚠️ This loop's main catch — the handoff claimed work that never happened.** The previous handoff read "I dispatched a page-budget assessment" for W9. There was **no Worker log, no result artifact, no queue entry**. A dispatch *plan* had been recorded as a dispatch *action*. I measured page 13 myself instead (full to the bottom margin). **Lesson written into memory.md** ("Verify handoffs against the tree before relaying status"). Treat any prior "I dispatched/I ran X" as unverified until you find the artifact.
- **D177 (mine, reversible)**: the Open Science external anonymous-repository promise was **removed** rather than a URL inserted — neither (a) standing one up nor (b) sourcing a URL was available, and a forward promise of infrastructure contradicts the paper's own "every claim checkable from the submitted bytes" standard. Explicitly told the user they may overturn it.
- **Hard-won corrections that must NOT be reinstated**: (1) the lower-side generation split is **NOT** explained by solver/penalty — `lbfgs` is sklearn's default and the effective penalty resolves to `l2` identically on 1.9.0/1.9.1 (C054 corrects C052's mechanism; cause **unexplained**; M177). (2) The m-free advantage is bounded by **M, not k** (M178). (3) "Zero from M=8 on at every k" and "vanishes from k≥15 onward at every M" are **both false**.
- **Pitfalls the next me is most likely to step into**: **green checks that cannot fail** (this project has produced several — a probe measuring the page-number band, a "goes to 0" test inspecting the wrong object); **a count is a weak instrument for presence** (an apostrophe in a quoted YAML scalar once broke the whole tracker; a "3 occurrences" substring count was really 0 with word boundaries — use key-set comparison or direct lookup); **verifying a neighbouring object** (name exactly what was inspected); **the Reviewer is fallible on wording** (its proposed replacement once reproduced a false claim — verify its fixes as claims too); **registration COPIES and suffixes** (a registered path is not necessarily the file you wrote).
- **User profile**: engaged PI who verifies with evidence, edits the repo directly, wants findings over status, and expects me to retract my own errors explicitly. Standing discipline: **verify load-bearing numbers FROM the artifacts, not from any agent's summary.**
