---
loop: 7
reason: max_wall_time
updated: '2026-09-22T12:59:17+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Language**: reply to the user in **Chinese**; ALL working files (ROADMAP/memory/decisions/mistakes) in **English**; paper/.tex/.bib always **English**.
- **Never put server-side paths in user-facing messages**. Use logical names, paste content, or `upload_file`.
- **GPU**: exactly 1 card bound, `111:cuda:0`. All tracks are **CPU-only** — the recurring "GPU idle" nudge is a binding artifact (constraint C055). Never re-triage it, never demand the card be returned.
- **Body page cap is 13** (CFP: ≤13pp excluding References and appendices). Current build is at exactly p.13. **Never compress body prose to buy a page** — standing red line.
- **Any source edit voids the SHA-bound visual-gate receipt** — fresh full render-and-inspect mandatory before any upload. Never upload a Worker-produced PDF.
- The **PI reviews the paper personally and is usually right**. On 2026-09-22 they assessed the internally-"Accept" version as **Reject**; all four of their findings proved substantive. Do not treat an internal Accept as authoritative over their judgement.
- Never fabricate run history to clear `X9_C` (it blocks `mark_project_passive`; the enum has no honest terminal value).

### 2. 🖥️ Infrastructure snapshot
- Server `111` (root), project path `/root/eibo`, interpreter `/root/miniconda3/bin/python3` (py 3.12.3, sklearn **1.9.0**) — the host that produced the **canonical lower-side ledgers**. **No `python3` on PATH.**
- Platform-local: `/app/.venv/bin/python3` (py 3.12.14, sklearn **1.9.1**). Do NOT use it to reproduce 111 artifacts.
- Paper tree `docs/paper/` (entry `main.tex`, output `main.pdf`). Corpus `/efs/workspace/_corpus/` — **one level ABOVE the project tree**, sha `6b323c4c…`.
- **No active processes, no tmux, no cron, 0 Workers, queue empty, registry RUNNING empty.** `ssh_execute` rejects multi-line commands.

### 3. 📊 Current state
- **D181 revision COMPLETE and delivered.** Final bytes sha256 `5f08a9fb…`, 414,613 B, **24 pp, body p.13**, visual gate **passed 24/24**. All six edits landed: headline 0.186→**0.197** (LP 0.363→**0.375**) with ≥0.95 simultaneous guarantee; "saturation"→**alphabet sparsity**; coverage language corrected; same-channel validation added (§4.4, 0/990 violations, "consistent with, not tight against"); §3.4 M=1 disambiguation; 2.9× scope labelled.
- **Registry**: 23 DONE + `X9_C` (PREPARING/killed, withdrawn design — exclude when filtering).
- **The PI has NOT yet reviewed the revised draft** — this is the gate. The revision has deliberately NOT been resubmitted for formal review.
- Two items surfaced to the user and awaiting their word: (a) their review of the revision; (b) the **Table 5 trade-off** — moving the grid into the body would breach the 13-page cap without cutting ~1 page of prose.

### 4. 📋 To-do (condition-triggered)
- **PI responds on the revision** → if they accept, the next step is a **new** `submit_paper_to_review` (check `get_formal_review_status` first; Round 14 is the last registered round). If they reject again, get their specific findings before touching anything.
- **PI rules on Table 5** → if "move it in", cut ~1 page of body prose deliberately (they must accept the trade); if "keep", ensure the cross-reference is prominent.
- **Before ANY delivery**: `pdf_to_images` (all 24, batches ≤20) → Read every page → `confirm_pdf_visual_review` → `cleanup_pdf_images` → `upload_file`. The receipt expires; re-render if it lapses.
- `mark_project_passive` is **blocked by `X9_C`** — do not retry expecting a different result.

### 5. 🎯 Strategic context
- **Core claim**: a two-sided ε-indistinguishability bracket — upper side a finite-sample strict bound, lower side a classifier-based high-probability bound — per service pair on real QUIC wire data. Contribution type: **measurement/rigour**. Target USENIX Security 2027 Cycle 2 (registration 2027-01-19, submission 2027-01-26).
- **Decision chain**: D177 (removed the Open Science external-repo promise) → D178/D179 (Round-14 Accept + corrections) → **D180** (T3 decided: stays measurement/rigour, planning tool is a corollary) → **D181** (PI Reject, four findings) → **D182** (adopt the m-free route: 0.186→0.197) → **D183** (evidence phase complete).
- **Pitfalls the next you is most likely to step into**:
  1. **Unit/prior mismatches masquerading as violations** — this session produced two false counts (73, then 910) that were purely definitional. Write out the units of BOTH sides before reporting a violation.
  2. **Summary fields are claims, not observations** — an artifact's `threshold_statement` was the *source* of a paper error; a `falsifier_fired` flag contradicted its own rule. Read the tables.
  3. **Check the artifact's own diff/self-report** — a Paper Agent batch claimed six edits while its token diff showed one file IDENTICAL; the seventh edit had never run.
  4. **Don't trust a claimed "done"** — verify at source AND in the render; fixed-in-source and fixed-in-render are different claims.
  5. **A geometric construction cannot be recovered from pairwise scalars** — the mixture/exclude-U floors were uncomputable and correctly deleted rather than restated.
