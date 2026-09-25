---
loop: 10
reason: idle_timeout
updated: '2026-09-24T18:11:02+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only.** Only output channel is `reviewer_post_to_director`. `save_project_file` is NOT in my toolset — memory persists via the auto-memory dir (`Write`/`Edit` there) + system distillation. Never attempt `save_project_file`.
- **CPU-only project.** GPU `111:cuda:0` idle is CORRECT — no GPU-eligible work exists. Never invent GPU work; the idle alert is a binding/timing mismatch (C055, do not re-triage).
- **Never quote server-side paths in user-facing text**; replies in **Chinese**, artifacts/paper in English.
- `ssh_read_only` whitelist: `cat/ls/grep/find/head/tail/wc/stat/du/df`. No `;`, `|`, `>`, no `sed`. `python3 -c` blocked if it contains `open(`.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. System `python3` has no scipy. **`sympy` is BROKEN** there.
- Corpus is **one level ABOVE** the project tree (`/efs/workspace/_corpus/…`).
- Paper tree `docs/paper/` (entry `main.tex`); it compiles `docs/paper/figures/paper/`, **NOT** repo-root `figures/paper/`.
- **Lower-side generation rule (C052):** no two lower-side ledgers may be compared at ROW level without stating which generation each is. Medians/counts allowed; per-pair values NOT.
- **A PDF sha is a BUILD-INSTANCE id, not a content id.** Verify rebuilds by per-page text, never by expected hash.
- **Never execute a venue rule without the CFP line.** The verbatim CFP is in the tree; "Open Science is capped at one page" DOES NOT EXIST (I verified; a fix plan had cited it).

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-…-certification-grade/`; knowledge files at root, artifacts under `artifacts/` (+ `_project/{data,intermediate,report}/`). Subdir artifacts: `X1/`, `X9_E/`, `X11/`, `X12_k5/`, `X3/`.
- Registry 24 experiments (23 DONE / 1 PREPARING = `X9_C`, withdrawn). Manifest `artifacts/manifest.yaml` **170 entries**.
- **Server 111 `/root/miniconda3` = sklearn 1.9.0** → canonical ledgers. **Local `/app/.venv` = sklearn 1.9.1** → T1/T1b (the lower-side ledgers `t1*` are LOCAL-host; their `execution_environment` says so).
- Verbatim CFP: `artifacts/_project/reference/usenix_sec27_cfp_extracted_20260918.txt` (84,784 B). Read it directly for any deadline/limit question.
- No RUNNING processes, no active crons, no pending worker callbacks at handoff.
- Key artifacts: `d181_joint_coverage_reaggregation.json` (sha `c0573590…`, S_known 407.75), `d181_balanced_accuracy_risk_interval.json` (sha `06c0e766…`), `eth_full_mk_grid_a73525.json` (20-cell grid), `_project/intermediate/t1_lower_side_M1.json` / `t1_lower_side_M2.json` / `t1c_lower_side_M1_uncapped.json` / `t1b_lower_side_k5.json` / `t1b_lower_side_k10.json`, `openset_delta.json`, `ci_main_table.json`.

### 3. 📊 Current state
- **Just delivered the Round-18 fix-plan review** (the highest-stakes output of this loop). Verdict: 3 of the Director's premises refuted. Details in §5.
- **Current PDF:** sha `de5e4b63…`, 416,639 B, 24 pp, body p.13, 24/24 visual gate PASSED. Round 17 formal review was dispatched on these bytes; **Round 18 came back weak-reject/borderline with 14 findings C1–C14**. The Director is about to dispatch fixes.
- Also this loop: reviewed the `supplementary.tar.gz` build (sha `dc57e6b9…`, 3,695,151 B, 71 files) — hash chain verified (34/34), but filed 3 defects: wrong exclusion list, missing `x12_detector_validation_k5.json` (sole source of body Table `tab:detectors`), and internal process vocabulary in `latex/camera_ready_plan.md`. Unregistered archive.
- Registry: 0 RUNNING. D197–D201 reviewed and all sound.

### 4. 📋 To-do (condition-triggered)
- **Director dispatches Round-18 fixes → re-verify the three items I flagged:** (a) `main.tex:729` must read `0.197` not `0.1858`; (b) any added M=2 `127` / k=10 `98` to Table 3 must carry a caption stating M=2's lower side passes 990/990 (mixed-convention artifact); (c) no fix dispatched against a non-existent Open Science page cap.
- **Paper bytes change** → re-verify build state AND run the process-vocabulary scan on the RENDERED PDF (`D181`, `Round-`, `relocated here from`, internal hostnames). The current 24/24 receipt is void on any byte change.
- **Anyone cites `0.186`/`0.363`/`0.194`** → superseded; correct to `0.197`/`0.375`.
- **"2.9× tighter" appears bare** → it is the RADIUS ratio (2.9108), not the bound ratio (1.0880 at median tv̂). Abstract/intro fixed; `results.tex:168` still says "tighter" (parenthetical names the object) — one-word residual.
- **Any numeric expression compared against a floor** → name the floor (open-set M46 = 0.196981; matched M45 = 0.205934; LP = 0.374840; combinatorial 0.289/0.304).
- **A new artifact claimed** → hash it; grep manifest for name AND hash before registering (registration copies; cannot undo).
- **PI replies on the revision** → `get_formal_review_status` first; Round 18 is the latest registered.

### 5. 🎯 Strategic context
- Contribution type **measurement/rigour**. Three core claims (C1 bracket 336/990; C2 horizon with saturation separation 13/7 cells; C3 four M=1 monotone series), each backed by independently verified artifact rows.
- **Round-18 fix-plan review (this loop's main output) — what the Director must not get wrong:**
  1. **S1 is NOT a claim downgrade.** I reproduced the whole chain from `d181` rows: S_known = **407.7497**, floor M=46 = **0.19698055**, M=45 = **0.20593421**, cap-at-1 count = **6**. The artifact's own `guarantee_statement` says the floor is a high-probability bound *to the extent it uses the simultaneous upper-side event*; "in expectation" is the residual budget (≤0.012), not the confidence level. **Abstract's 0.197 + 0.95 both stand.** The real defect: `main.tex:729` names `0.1858` as the base of a 45/44 factor that belongs to the pair (0.2015, **0.197**) — 0.201457/0.196981 = 45/44 exact; 0.201457/0.185774 = 8.4%. **One-number fix.**
  2. **The Director's "6.0%" is real arithmetic, wrong pairing** (0.196981/0.185774 = the two generations' M=46 uniform floors). Same trap as `factor-ratio-real-pairing-wrong`.
  3. **C2: §3.4 is false (Director right), but `127` is a MIXED-CONVENTION number.** The artifact's own `falsifiers` says `MISMATCH on 840/990 rows` (full-n upper + capped lower). Citable only because M=2's lower side passes 990/990 → count insensitive to the lower convention; **the caption must say so**, or re-run M=2 uncapped. k=10's `98` (from capped `t1b`) has the same problem vs the uncapped k=5 headline.
  4. **C9 premise false:** `0.304` and `0.375` ARE in the same paragraph (`measurement_design.tex:70` and `:74`). Do not promote the LP to headline — the PI's own prior review flagged its selection-correction as unresolved.
  5. **C10: a service-clustered re-split check is NOT a coverage substitute — do not run it.** §3.3 already carries the honest wording ("claim no more from it"). Align the Limitations wording instead.
  6. **Fabricated venue rule caught:** no Open Science page cap exists in the CFP. The real defect is the missing anonymous artifact URL.
  7. **Free win I found:** D198's open question is now closable — from the released M1/M2 ledgers the paired increment is positive on **99.9%** of 990 pairs (tv_hat median +0.2093, eps_hi median +0.2115). §4.4's resolution-substitution becomes verified.
  8. **Figure 1 caption has a second defect the Director missed:** `main.tex:282-283` claims "Cited from … `\Cref{sec:design/frontier}`", but `measurement_design.tex:331-338` never cites Fig 1 — a false citation; plus "relocated here from the Introduction" is editing-history prose.
- **Standing pitfall for the next me:** the Director's summaries are usually right about *direction* and often wrong about *pairing/base/generation*. This loop, three premises failed on re-derivation and two of my own framings needed narrowing. **Re-derive from rows before endorsing, and read the artifact's `falsifiers` field — a reproduced count proves the arithmetic, not the label.**
