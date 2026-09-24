---
loop: 9
reason: max_wall_time
updated: '2026-09-24T01:52:01+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only.** Only output channel is `reviewer_post_to_director`. `save_project_file` is NOT in my toolset — memory persists via system distillation + the auto-memory dir (`Write`/`Edit` there). Never attempt `save_project_file`.
- **CPU-only project.** GPU `111:cuda:0` idle is CORRECT — no GPU-eligible work exists. Never invent GPU work; the idle alert is a binding/timing mismatch (C055, do not re-triage per alert).
- **Never quote server-side paths in user-facing text**; replies in **Chinese**, artifacts/paper in English.
- `ssh_read_only` whitelist: `cat/ls/grep/find/head/tail/wc/stat/du/df`. No `;`, `|`, `>`, no `sed`. `python3 -c` blocked if it contains `open(`.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. System `python3` has no scipy. **`sympy` is BROKEN** in that env.
- Corpus is **one level ABOVE** the project tree (`/efs/workspace/_corpus/…`).
- Paper tree `docs/paper/` (entry `main.tex`); it compiles `docs/paper/figures/paper/`, **not** repo-root `figures/paper/`.
- **Lower-side generation rule (C052):** no two lower-side ledgers may be compared at ROW level without stating which generation each is. Medians/counts allowed; per-pair values NOT.
- **A PDF sha is a BUILD-INSTANCE id, not a content id.** Verify rebuilds by per-page text, never by expected hash.

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-…-certification-grade/`; knowledge files at root, artifacts under `artifacts/` (+ `_project/{data,intermediate,report}/`).
- Registry 24 experiments; manifest `artifacts/manifest.yaml` ~167 entries.
- **Server 111 `/root/miniconda3` = sklearn 1.9.0** → produced the canonical ledgers. **Local `/app/.venv` = sklearn 1.9.1** → T1/T1b.
- No RUNNING processes, no active crons, no pending worker callbacks at handoff.
- Key artifacts: `d181_joint_coverage_reaggregation.json` (sha `c0573590…`), `d181_balanced_accuracy_risk_interval.json` (sha `06c0e766…`), `eth_full_mk_grid_a73525.json` (the 20-cell (M,k) grid), `openset_delta.json` (detector deltas), `ci_cross_corpus.json` / `ci_main_table.json` (bootstrap intervals).

### 3. 📊 Current state
- Registry: 24 experiments, DONE 23 / PREPARING 1 = `X9_C` (withdrawn design, never ran; exclude when filtering).
- **Current PDF:** sha `de5e4b63…`, 416,639 B, 24 pp, body p.13. This is a **rebuild** from the same sources as the delivered `32dadd14…` (same byte count, all `.tex` predate it). ROADMAP header still records `32dadd14…` and the 24/24 visual-gate receipt was on those bytes — **does not automatically transfer** to the new sha. If the rebuild goes forward, a fresh visual gate is needed.
- **Draft delivered to the PI, awaiting verdict.** D191–D195 (the floor-labelling defect class, six instances + reference check) all installed and gate-passed.
- **Class sweep of ALL sections complete (this session):** §Measurement Design (18 expressions, WRONG 0, UNDECLARED 4 — all fixed in D191/D193); the remaining sections (WRONG 0, UNDECLARED 3 — the 2.9× radius-vs-bound naming at abstract/intro, fixed in D193; one cross-corpus framing note).
- Worker `Extract_per-page_PDF_text_metrics` (PyMuPDF, sha-asserted on `de5e4b63…`) produced 24-page metrics. These are the camera-ready regeneration I flagged. **The per-page table must name the extractor (`fitz`) and the unit, or it will appear unreproducible under poppler (`pdftotext`)** — verified: 0/24 pages match between extractors on the same file.

### 4. 📋 To-do (condition-triggered)
- **PI accepts the revision** → fresh `submit_paper_to_review` (Round 14 is the last registered; check `get_formal_review_status` first). Then I re-run build-state + rendered-PDF scan on whichever bytes are submitted.
- **PI rejects** → their specific findings first; do not pre-emptively open new experiments.
- **Paper bytes change** → re-verify build state AND run the process-vocabulary scan on the RENDERED PDF (`Round-`, `revision`, internal hostnames). The current 24/24 receipt is void on any byte change.
- **Anyone cites `0.186`/`0.363`/`0.194`** → superseded; correct to `0.197`/`0.375`.
- **Anyone cites `32dadd14…` as the current sha** → superseded by rebuild `de5e4b63…`; note both are content-identical by per-page text (not by hash).
- **"2.9× tighter" appears bare** → it is the RADIUS ratio (2.9108), not the bound ratio (1.0880 at median tv̂). The abstract/intro are fixed; `results.tex:168` still says "tighter" (the parenthetical names the object, but the word is inconsistent with the other two sites which now say "smaller confidence radius").
- **Any boundary claim over a 2-D grid** → check EVERY cell, not the axis that motivated it. Both prior single-axis statements were false.
- **A new artifact claimed** → hash it; if registered, confirm `content_sha256` is present. Grep manifest for name AND hash before registering (registration copies; cannot undo).
- **Any numeric expression compared against a floor** → name the floor (open-set M46 = 0.1969805; matched M45 = 0.2059342; LP = 0.3748400). The class is closed but can recur on new text.

### 5. 🎯 Strategic context
- Contribution type **measurement/rigour**. Three core claims (C1 bracket existence 336/990, C2 horizon with saturation separation 13/7, C3 the four M=1 monotone series) each backed by independently verified artifact rows.
- **The route-mix pitfall**: a ratio across the old→new route hides two changes (a route gain vs a union-bound cost). Decompose before quoting.
- **Four times this session my own quick check was wrong, not theirs** — the RNG stream, the bias-shift, the `penalty="deprecated"` sentinel, and the arm-arithmetic ("weakest arm" = highest error = 0.830, not 0.737). The memory entry `extremum-label-inverts-the-arithmetic` records the last one; it was the Director who caught it. Re-derive, then audit the re-derivation.
- **An artifact's summary/prose field is a CLAIM, not an observation** — repeatedly the source of inherited falsehoods. Check it against the artifact's own rows.
- **Generations and streams multiply silently**: canonical D (n=5000) vs the coverage run (n=1000, no inner draws, sd 3.5% apart) vs T1 vs Eq6-vs-m-free routes. Naming which one is load-bearing is the single most common missing qualifier.
- **"Unsourced" is a claim about an absence, and an absence claim needs the exhaustive read on the value side.** I filed 0.63 as unsourced, then found it in `openset_delta.json` — the lesson is [[absence-claimed-from-a-search]]. Similarly, "only in X" for a value needs grepping the value, not just confirming X.
- **Hash-matching is not scope-matching.** Two cited artifact hashes verified perfectly while their contents recorded the *previous* generation's floors. The defect class is [[cited-hash-records-old-generation]] — open the cited bytes and check what they record.
- **The per-page metric table is extractor-dependent.** PyMuPDF and poppler disagree by 4–73 chars per page on the same file. The camera-ready plan must name the extractor alongside the unit, or the table will again appear unreproducible.
