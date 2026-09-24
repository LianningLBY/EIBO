---
loop: 5
reason: max_wall_time
updated: '2026-09-20T08:40:44+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Language**: reply to the user in **Chinese**; ALL working/knowledge files (ROADMAP, memory, decisions, mistakes) in **English**; paper/.tex/.bib/captions always **English**.
- **Never put server-side paths in user-facing messages** (`/efs/...`, `/root/...`, `~/...`, `~/.agent-ml-research/...`). Use logical names ("the registry", "main.tex §3"), paste the actual content, or `upload_file`. No "saved at" footers.
- **Never reveal the underlying model/provider/vendor**, or Apex runtime, control-plane locators, credentials, or a cloud/rental provider name. Identity question → "I am Apex Research Director."
- **GPU**: exactly 1 card bound, `111:cuda:0`. All tracks are **CPU-only**; there is no GPU-eligible job. The recurring "GPU idle" nudge is a binding/timing artifact — do NOT re-triage it per alert, and never demand the card be returned.
- **Body page cap is 13** (CFP: "must not exceed 13 pages excluding References and any appendices"; bibliography/appendices uncapped). Current total 24 pages is **COMPLIANT**. Never compress body prose to buy a page.
- **Any source edit voids the SHA-bound visual-gate receipt** — a fresh full render-and-inspect is mandatory before delivery. Never upload a Worker-produced PDF; the owning role inspects.
- Never run arbitrary `git`/deletion on remote hosts for housekeeping; declare residue, don't delete.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (root), project path `/root/eibo`, interpreter `/root/miniconda3/bin/python3` (python 3.12.3, sklearn 1.9.0, numpy 2.3.2, scipy 1.18.1) — this is the host that produced the **canonical lower-side ledgers**.
- Platform-local container `/app/.venv` = python 3.12.14 / sklearn 1.9.1 / numpy 2.5.3; use `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3` for local python. **Do not use it to reproduce 111 artifacts.**
- Paper tree: `docs/paper/` (entry `main.tex`, output `main.pdf`). Corpus h5: `/efs/workspace/_corpus/` (one level ABOVE the project tree), sha `6b323c4c…`.
- No active processes, no tmux, no cron jobs, 0 Workers, registry RUNNING/ANALYZING empty.

### 3. 📊 Current state
- **Round 13 is closed.** All P0/P1/W fixes landed and I verified them at source and in the render. `artifacts/review_issues.yaml`: **21 resolved / 1 in_progress**; only **W9** remains.
- **Final bytes: sha `cd34c2800f9746c9835fd2718d4cd81047b27d0f1b463e623ae08d1115ad1680`, 412,332 bytes, 24 pages, body ends p.13, Ethics p.14, References pp.22-24.** Visual gate **PASSED 24/24** (full render+inspect done by me). 0 undefined / 0 overfull / 0 `??` / 0 multiply-defined / 0 empty cross-refs / 0 doubled appendix numbers / 0 em-dashes.
- This session also: removed the Open Science placeholder (**D177** — see §5), added 6 artifact citations to the Open Science list (**all 15 cited ids verified to resolve + hash-match, none superseded**), removed the unsourced "3000 draws" claim, corrected the coarse-resolution advantage sentence at three sites, corrected the refuted solver/penalty mechanism (**C054/M177**), audited the manifest (**0 hash mismatches, 0 path-but-no-hash**), consolidated duplicate registrations, declared remote upload residue, refreshed ROADMAP (142 lines).
- Pending: nothing running. Waiting on the user for the review re-run decision and T3 positioning.

### 4. 📋 To-do (condition-triggered)
- **User answers on the review re-run** → if YES, call `submit_paper_to_review` on the current bytes with `reference_verification_policy` per their decision; check `get_formal_review_status` first so no duplicate round is created.
- **User answers on T3 (planning tool)** → feed the choice into `paper_framing.md` / a Paper Agent Patch task.
- **W9 — do NOT batch it.** The body sits at exactly p.13 against the cap. I dispatched a page-budget assessment: get the measured options first (free space on p.13, candidate compact table forms, and whether the appendix `tab:bracket` becomes a duplicate needing a label check). If nothing fits, leave it appendix-only and say so.
- **W11g (24→20-page camera-ready plan)** → defer to the camera-ready stage; does not block.
- **W7/W11f** → both closed this session (citation gap, not registration gap).
- **Before any delivery**: re-run `pdf_to_images` (all 24, batches ≤20) → Read every page → `confirm_pdf_visual_review` → `cleanup_pdf_images` → `upload_file`.
- `mark_project_passive` is **blocked by `X9_C`** (`status: PREPARING`, `conclusion: killed`, a properly-specified-then-deliberately-killed withdrawn design; the enum has no honest terminal value). Do not fabricate run history to close it.

### 5. 🎯 Strategic context
- **Core claim**: a two-sided ε-indistinguishability bracket — upper side a finite-sample strict bound, lower side a classifier-based high-probability bound — per service pair on real QUIC wire data. Target **USENIX Security 2027 Cycle 2** (submission 2027-01-26). Contribution type: **measurement/rigour**.
- **D177 (mine, reversible)**: the Open Science external anonymous-repository promise was **removed** rather than a URL inserted. Reasoning: (b) needs an account the project cannot create; (a) would make the paper promise infrastructure that must exist by the submission date — an unverifiable forward promise contradicting the paper's own "every claim checkable from the submitted bytes" standard. I explicitly told the user they may overturn this.
- **Hard-won corrections that must not be reinstated**: (1) the ledger generation split is **NOT** explained by solver/penalty — `lbfgs` is sklearn's default and the effective penalty resolves to `l2` identically on 1.9.0/1.9.1; cause **unexplained** (C052 rule stays binding, C054 corrects its mechanism, M177). (2) The m-free advantage is bounded by **M, not k** (M178, see memory). (3) "Zero from M=8 on at every k" and "vanishes from k≥15 onward at every M" are **both false**.
- **Pitfalls the next me is most likely to step into**:
  - **Green checks that cannot fail.** This session produced FOUR: a page-fill probe measuring the footer/page-number band (752 on every page), ymax from a running header, and earlier a "goes to 0" test that inspected the wrong object. Ask "what would make this check fail?" before trusting a pass.
  - **A count is a weak instrument for presence** — grep/substring patterns silently miss (an apostrophe in a quoted YAML scalar broke the whole tracker; a "3 occurrences" substring count was really 0 with word boundaries). Use key-set comparison or direct lookup.
  - **Verifying a neighbouring object.** Multiple instances; the fix is to name exactly what was inspected.
  - **The Reviewer is fallible on wording** — its proposed replacement reproduced a false claim. Verify its fixes as claims too.
  - **Registration COPIES and suffixes.** Never assume a registered path is the file you wrote.
- **User profile**: engaged PI who verifies with evidence, edits the repo directly, wants findings over status, and expects me to retract my own errors explicitly. The standing discipline is: verify load-bearing numbers FROM the artifacts, not from any agent's summary.
