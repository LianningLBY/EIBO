---
loop: 11
reason: max_wall_time
updated: '2026-09-25T11:41:35+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only.** Only output channel is `reviewer_post_to_director`. `save_project_file` is NOT in my toolset — memory persists via the auto-memory dir (`Write`/`Edit` there) + system distillation. Never attempt `save_project_file`.
- **CPU-only project.** GPU `111:cuda:0` idle is CORRECT — no GPU-eligible work exists. The idle alert is a binding/timing mismatch (**C055: acknowledge once, do not re-triage**).
- **Never quote server-side paths in user-facing text**; replies in **Chinese**, artifacts/paper in English.
- `ssh_read_only` whitelist: `cat/ls/grep/find/head/tail/wc/stat/du/df`. No `;`, `|`, `>`, no `sed`. `python3 -c` blocked if it contains `open(`.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. System `python3` has no scipy.
- Corpus is **one level ABOVE** the project tree (`/efs/workspace/_corpus/…`).
- Paper tree `docs/paper/` (entry `main.tex`) compiles `docs/paper/figures/paper/`, **NOT** repo-root `figures/paper/`.
- **A read is evidence for the READ, not for the SEND.** Re-run the exact command that produced a finding as the LAST step before sending, and quote the hash beside the number. Four stale-read filings happened this session; this rule is what fixed it.
- **Never execute a venue rule without the CFP line.** Verbatim CFP: `artifacts/_project/reference/usenix_sec27_cfp_extracted_20260918.txt`. "Open Science is capped at one page" DOES NOT EXIST.
- **CONVENTION × ROUTE:** two conventions (capped/uncapped — paper uses UNCAPPED) and two upper routes (Eq (6) at α_law=0.025 vs m-free at α_pair=0.05/990). Never name one α for both.
- **A PDF sha is a BUILD-INSTANCE id, not a content id.** Verify rebuilds by per-page text.

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-…-certification-grade/`; knowledge files at root, artifacts under `artifacts/` (+ `_project/{data,intermediate,scratch,report}/`). Subdir artifacts: `X1/`, `X9_E/`, `X11/`, `X12_k5/`, `X3/`.
- **Preview/receipt store: `.agent-ml/state/pdf_visual_reviews.json`** (runtime state, keyed by PDF sha, NOT in the project tree — searching the tree reports it missing).
- Server 111 `/root/miniconda3` = **sklearn 1.9.0** → canonical ledgers. Local `/app/.venv` = 1.9.1 → the `t1*` lower-side ledgers.
- **Build (current):** `docs/paper/main.pdf` sha `4e0a80a2…`, 421,196 B, 24 pp, body ends **p.13**, Ethics p.14, Open Science p.15, 0 `??`, no source newer than the render. `passed` 24/24 receipt bound to `4e0a80a2…` (confirmed 2026-09-25T10:56:40; expires 2h).
- **Archive:** `artifacts/supplementary.tar.gz` sha `7a48cf6e…`, 88 entries, **three-way hash agreement** (manifest `art_20260924_2d151d` = cited `_project/data/` copy = tree copy). Embedded `main.pdf` = `4e0a80a2…`, `references.bib` = `7f179141…`, both byte-identical to the tree.
- Build script `scripts/build_supplementary_archive.py` (own guards: census baseline, binary content, freshness, manifest-hash, mirror-to-registered).
- No running processes, no crons, no pending callbacks.

### 3. 📊 Current state
- **Registry: 24 experiments, all DONE, 0 RUNNING** (X9_C closed as `killed`). No GPU-eligible work.
- **Just finished:** verified the batched bibliography pass landed. All three fixes correct in source AND render: `sekeh2019learning` → `10.1109/TSP.2020.2994807` (was dead `…2999953`); `smith2021website` → `10.2478/popets-2021-0017` + vol/no/pages (was `…0018`, a different paper); `li2023facing` → **Xiaolin Xu** added, `10.1109/ISCC58397.2023.10218269`. All three wrong values confirmed ABSENT from the PDF. `luxemburk2023cesnet` "omitted author" RETRACTED — all 5 authors present in tree, HEAD, first commit, and render (parser artifact, M181).
- **Manifest:** 171 entries, 15 without `content_sha256` (all superseded/scratch); all 17 paper-cited artifacts carry their hash. 253 decisions in `decisions.yaml`.
- **Round 19 registration FAILED — twice.** Two submits returned DISTINCT approval ids (`apr_20260924T225518_cl7h`, `apr_20260925T011505_9gg9`) instead of `deduplicated`; `get_formal_review_status` still reads round 18; no `review_round_19` dir. Fails ONE STAGE EARLIER than rounds 15–17. Escalated as platform-side; **do not blind-retry a third time.**
- **Venue is ASSUMED, not decided** (D236, open, escalated to PI). Round 18's reviewers recommended PoPETs (IMC second) and called USENIX the weakest fit; no decision-log entry adopts or overrules.

### 4. 📋 To-do (condition-triggered)
- **Any source edit lands → re-render + full 24/24 gate BEFORE delivery**, and rebuild the archive + update the manifest hash. Order is **render → gate → cleanup images → THEN submit**.
- **If Round 19 ever registers** → regenerate `artifacts/submission.tar.gz` from the CURRENT tree (the on-disk one is the 01:15 snapshot of the failed attempt and is stale in all three paper files); also confirm the dropped scratch PNGs stay out.
- **PI rules on the PoPETs trim vs revert to USENIX** → the switch is DONE (D255); only the trim/revert question is open.
- **PI answers the `liu2026inevitability` name** ("Guang Cheng" vs arXiv's "Guang Chen"; the sister paper 2607.17889 disagrees with 2602.14055) → edit only against an authoritative record.
- **Next real edit pass** → batch the deferred one-liners: `main.tex:632` `√C ≈ 2.96×` half-clause; `results.tex:168` `tighter`; `main.tex:2` EIBO comment. Each alone is not worth a gate cycle.
- **Anyone cites `0.186`/`0.363`/`0.194`** → superseded; correct to `0.197`/`0.375`.
- **A new artifact claimed** → hash it; grep the manifest for name AND hash before registering (registration copies; cannot undo).

### 5. 🎯 Strategic context
- Contribution type **measurement/rigour** (D180). Three core claims (C1 bracket 336/990; C2 horizon with saturation separation; C3 four M=1 monotone series), each backed by independently verified artifact rows.
- **Planning constant:** `n > C/(0.5−tv̂)²` with **C = 2ln(2/α_law) = 8.764053**. **Do NOT divide by √C = 2.960414** (understates n by 2.96×). Both numbers are correct in their own roles — the paper prints `2.96` once, at `main.tex:632`, **in the sentence warning against the substitution**, so a grep hit there is NOT evidence of the error.
- **Pitfalls the next me is most likely to step into:**
  1. **Reading, then composing, then sending.** The object moves in that window. Re-run the producing command immediately before sending — this is the single highest-value habit this session produced.
  2. **Trusting a defect report from an instrument already shown unreliable.** M181: a brace-unaware author parser manufactured a defect that reached the PI. Every comparator needs a FALSE-POSITIVE control per new data shape.
  3. **A check that "passes" over what was chosen cannot see omissions.** 41/41 hashes and 17/17 ids were both true while four promised categories were absent.
  4. **Registration is not validation** — an entry can resolve and still carry no `content_sha256`; the generator may write a different path than the entry cites.
  5. **Bibliographic fields are verify-or-omit — every field, not just DOIs.** This class shipped twice (fabricated DOIs + 4th author; then a fabricated title + 2 invented given names — the CFP's named desk-reject class).
