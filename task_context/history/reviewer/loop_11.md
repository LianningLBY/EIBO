# Reviewer Loop 11 handoff

## 1. 🔴 Hard constraints / red lines (carried forward, still binding)
- **Reviewer is read-only.** Only output channel is `reviewer_post_to_director`. `save_project_file` is NOT in my toolset — memory persists via the auto-memory dir (`Write`/`Edit` there) + system distillation. Never attempt `save_project_file`.
- **CPU-only project.** GPU `111:cuda:0` idle is CORRECT — no GPU-eligible work exists. The idle alert is a binding/timing mismatch (C055, do not re-triage).
- **Never quote server-side paths in user-facing text**; replies in **Chinese**, artifacts/paper in English.
- `ssh_read_only` whitelist: `cat/ls/grep/find/head/tail/wc/stat/du/df`. No `;`, `|`, `>`, no `sed`. `python3 -c` blocked if it contains `open(`.
- Local Python with scipy: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3`. System `python3` has no scipy. **`sympy` is BROKEN** there.
- Corpus is **one level ABOVE** the project tree (`/efs/workspace/_corpus/…`).
- Paper tree `docs/paper/` (entry `main.tex`); it compiles `docs/paper/figures/paper/`, **NOT** repo-root `figures/paper/`.
- **Lower-side generation rule (C052):** no two lower-side ledgers may be compared at ROW level without stating which generation each is. Medians/counts allowed; per-pair values NOT.
- **A PDF sha is a BUILD-INSTANCE id, not a content id.** Verify rebuilds by per-page text, never by expected hash.
- **Never execute a venue rule without the CFP line.** Verbatim CFP: `artifacts/_project/reference/usenix_sec27_cfp_extracted_20260918.txt` (874 lines). "Open Science is capped at one page" DOES NOT EXIST — re-verified this loop with `grep -i "one.page|1.page|single.page"` → **zero hits**.

## 2. 🖥️ Infrastructure snapshot
- Registry **24 experiments, all DONE, 0 RUNNING** (confirmed at loop start; `X9_C` closed as `killed`). No active crons, no pending callbacks.
- Manifest `artifacts/manifest.yaml` is a **top-level LIST**, 170 entries (each: id/name/type/description/path/content_sha256/url/project/exp_id/skill/created_at/tags).
- **Server 111 `/root/miniconda3` = sklearn 1.9.0** → canonical ledgers. **Local `/app/.venv` = sklearn 1.9.1** → T1/T1b lower-side ledgers (`t1*` are LOCAL-host; their `execution_environment` says so and warns they'd need re-running on 111 under the uncapped convention).
- Paper build: `docs/paper/main.pdf`, sha `de5e4b63…`, 416,639 B, **24 pp**, body ends **p.13**, Ethics p.14, Open Science pp.15–16, References pp.22–24. **Bytes UNCHANGED this loop** — Round-18 edit pass has NOT landed yet.
- **Measured body slack:** p.13 right column ends **y≈495** vs text-block bottom **y≈722** ≈ **~20 lines (~1/6 page)**. Full pages = 53–57 lines/col. This is the ENTIRE budget (13pp cap binding; prose compression is a red line).

## 3. 📊 Current state
- **Round 18 review on disk** (`artifacts/review_reports/round_18.md`): weak reject/borderline, 14 findings C1–C14. Read it in full this loop.
- **Director is mid-fix-pass**; decisions D205–D212 written **18:04–18:49 today**. The Director ran the protocol-mandated adversarial audit with me *before* dispatching, and **D206 records that I refuted 3 of their premises (C8 pairing, C9 co-location, C4 page cap) — all three accepted and re-derived.**
- **My loop-11 report** (dispatched): 1 critical + 1 warning + 1 info. See §5.

## 4. 📋 To-do (condition-triggered)
- **Round-18 edits land → re-verify:** (a) `main.tex:729` must read `0.197` (not `0.1858`) as the base of the 45/44 factor; (b) any M=2 `127`/k=10 `98` added to Table 3 must carry the mixed-convention caption condition; (c) **body must still end p.13** — the three top fixes are additive against ~20 lines of slack.
- **Paper bytes change** → re-verify build state AND run the process-vocabulary scan on the RENDERED PDF (`D181`, `Round-`, `relocated here`, `EIBO`, internal hostnames). The 24/24 receipt is void on any byte change.
- **Archive rebuild after the edit pass** → `scripts/build_supplementary_archive.py` now exists (dispatched D210). It enumerates from the manifest (stray-root file structurally excluded) and asserts expected main.pdf sha. **It has NO content scan** — see §5 critical.
- **Anyone cites `0.186`/`0.363`/`0.194`** → superseded; correct to `0.197`/`0.375`.
- **"2.9× tighter" bare** → it is the RADIUS ratio (2.9108), not the bound ratio (1.0880 at median tv̂). Abstract/intro fixed; `results.tex:168` is a one-word residual (parenthetical names the object).
- **Any numeric expression vs a floor** → name the floor (open-set M46 = 0.196981; matched M45 = 0.205934; LP = 0.374840; combinatorial 0.289/0.304).
- **A new artifact claimed** → hash it; grep manifest for name AND hash before registering (registration copies; cannot undo).
- **PI replies on the revision** → `get_formal_review_status` first; Round 18 is the latest registered.

## 5. 🎯 Strategic context — what I filed this loop (the three items that matter)
1. **[critical] The archive's leak set ≠ the scan's pattern set.** 17 shipped files carry `/root/eibo/…` and `/root/autodl-tmp/…` and **NONE of them contains `/efs/` or `/home/`** — the two patterns D211 dispatched. 30 files carry the codename `eibo`, 11 carry `autodl`. `FORBIDDEN_ENTRY_RE` (`scripts/build_supplementary_archive.py:129`) matches **entry names only**; there is no content scan anywhere. A fix built to the dispatched spec passes while de-anonymising the very ledgers Open Science nominates as evidence. Also: the long project slug (10 files) is NOT a substitute for the short codename (30 files).
2. **[warning] Additive fixes vs ~20 lines of slack.** Round 18's top three (C7 four-reference subsection, C9 dominance clause, C1 α-attribution) all land in the body; C7 alone is the largest addition in the plan. Ask whether they were word-budgeted, and pre-clear a float (Table 5 relocation) as the overrun lever. D199 already hit this once by lifting Table 5 into the body.
3. **[info] Three D206/D209 dispositions confirmed by re-derivation.** C8: S_known 407.7497; LP uniform point 0.20145738; eq:floor 0.196981; ratio **1.0227273 = 45/44 exactly**; `0.185774` is `controls.canonical_uniform` (S=384.5529, superseded generation) → wrong base, one-digit fix. C4: no page cap (zero grep hits). Archive 96-vs-89: **directory entries vs files**, file sets byte-identical except the added README — no regression.

## 6. ⚠️ Standing pitfalls for the next me
- **The Director is usually right about direction, often wrong about pairing/base/generation.** This loop every premise I re-derived held on direction; the failures were in which two numbers a ratio joins. **Re-derive from rows before endorsing, and read the artifact's `falsifiers` field** — a reproduced count proves the arithmetic, not the label.
- **Two decisions ten minutes apart can contradict.** D207 said the capped median is 0.5368 (t1 ledger); D209 said 0.5349 (q1 capped column) and superseded it. Both are real *different artifacts'* capped columns; the printed 0.535 is q1's. Compute from rows, then check which artifact the *sentence* cites.
- **`pdftotext` column order can make a complete page look truncated.** p.13 appeared to end mid-sentence ("…while we report"); PyMuPDF reading order showed the full §6.4 + Conclusion. Use `get_text('text')` for completeness, `get_text('dict')` for column geometry.
- **A guard described in prose is not the guard in the code.** D211 called it a "forbidden-content scan"; the implementation searched filenames. Read the regex and its call site.
- **My own prior findings can be stale.** The Open Science placeholder memory said the appendix ships `[ANONYMOUS-REPO-URL-TO-INSERT]`; the placeholder is **gone** and was never filled — memory corrected this loop, but the *requirement* (C5 anonymous URL) is still open and needs a PI value.
