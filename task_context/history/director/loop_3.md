---
loop: 3
reason: max_wall_time
updated: '2026-09-18T02:52:02+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Body limit is 13 pages** (USENIX Sec 2027 C2, DDL 2027-01-26); references/appendices unlimited. **Verify by rendering and finding the body's last page** — never from the compile log or an agent summary. A previous "body ends p.13" report was false while its own parenthetical said otherwise (M150).
- **Do NOT shrink a figure to buy a page.** fig4 went 0.58→0.54→0.50→0.46 across rounds for a page that **moving it to the appendix** bought outright; it is now back at 0.62. Any further page pressure = relocate a float or cut prose.
- **The floor is a standard consequence of the two-point lemma, NOT a new construction.** Never write "our new bound". Only the **uniform** floor (0.186 = M=46 / 0.19422 = M=45) is certified; LP 0.36307 / mixture 0.36347 / exclude-U 0.37155 are **references only, not certified** — they descend from one derivation line that carried three normalisation errors.
- **Never mix M**: 0.186 is the M=46 open-set floor; 0.737 is the 45-class closed-set error. The matched comparison is **0.194 / 3.79×**. The paper dual-reports this — do not "simplify" it.
- **The 45 known services are a label LIST spanning 0–52** (incl. 48–52), not `range(45)`. Filtering by label value inverts the unknown set and corrupts S_known (990 rows, 384.5529).
- **Every reported number carries its window AND channel** (and eligibility rule `PPI_LEN>=5` for proximity). tv(47,37) = 0.1402 train / 0.0146 test.
- Paper/artifacts English; **user-facing replies Chinese**. Never put server paths in user-facing messages.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (connect.westb.seetacloud.com), path `/root/eibo`, account `root`, auth password. 1× RTX 5090 D (32 GB).
- Python: `/root/miniconda3/bin/python3` (absolute; not on PATH). Local: `/app/.venv/bin/python3` + `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages` (has `tables`, `numpy`, `scipy`, `fitz`).
- **Corpus is LOCAL at `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5`** (3,544,625,537 B, sha `6b323c4c…`) — **one level ABOVE the project tree**, which is why project-tree searches miss it. Byte-identical to the server copy. Never re-hash; stream it (~10 s).
- Paper tree: `docs/paper/` (`main.tex` entry). **Compile: pdflatex → bibtex → pdflatex → pdflatex.** `pdflatex` exits 1 on this template despite a clean log (breakurl warning) — not a failure.
- **Figures: `docs/paper/figures/paper/` is what compiles**, NOT the repo-root `figures/paper/` where generators write. Sync + md5-verify after any regeneration.
- Active processes: none. Registry: no RUNNING/PREPARING. GPU idle is correct (X12, the only GPU entry, is DONE).

### 3. 📊 Current state
- **Paper is at ACCEPT 4.5/5** (trajectory R7 3/5 → R8 4/5 → R9 4.5/5 unanimous; R9 was the **first round in nine with no critical from any reviewer**).
- **Round 10 is submitted and active** (`75b5fe73`, `director_planning`). Await its report.
- Submitted bytes: `main.pdf` sha `eccee2f3…`, 384,579 B, 21 pages, **body ends p.13**, visual gate passed 21/21. All six R9 shepherding items are reviewer-verified PASS.
- **Zero unresolved criticals** on `artifacts/review_issues.yaml` (23 active entries).
- One known-unverified edit: `background.tex` §2.3's compression (mtime 02:32:26) landed **after** the reviewer's 02:25:07 build, so that single edit is unverified by anyone but me — it is a pure duplication-cut of §6.1 territory, but a Round-10 reviewer may notice.

### 4. 📋 To-do (condition-triggered)
- **Round 10 report arrives →** if critical/warning: run the standard 9-step protocol (verify each against source; `post_to_reviewer` for independent audit *before* dispatching; every W-item fix returns to the reviewer for PASS). If accept: report to user.
- **Any further page pressure →** relocate a float, never shrink one.
- **Any figure regeneration →** regenerate, copy into `docs/paper/figures/paper/`, md5-verify both trees, then scan the compiled figure's OWN text layer (positive-control the scanner on a known-leaky file first).
- **If a page count or "fixed" claim is disputed →** render the PDF and print its sha256; compare per-page text sizes, not hashes (identical sources give different hashes).
- **Before final camera-ready →** run the figure escape-leak gate once more on the final bytes (reviewer-requested checklist item).

### 5. 🎯 Strategic context
- **Contribution type: measurement/rigour, not a new mechanism.** We are the only work giving a finite-sample strict upper side AND a classifier lower side on real QUIC wire traffic. The accept is for that; do not let it drift into a mechanism claim.
- **Closed lines**: open-set floor (D139–D145), Δ measurement (D142: 3.79× loose on the open-set reading, ~2× matched, insensitive to classifier strength), coverage calibration (D153; **confirmation loss, not degradation** — i.i.d. holds in all 17 informative cells, the dependence arm breaches in exactly 2 cells at B=64), capacity axis unmeasured (D143), post-selection route refuted (D147 — Michel et al. arXiv:2005.06006 already solves it and we already implement it).
- **Pitfalls this session produced, all verified real:**
  1. **"Fixed" claims are claims.** I re-measured a reported "body ends p.13" and found p.14. Render and locate the boundary yourself.
  2. **A check aimed at the neighbouring object** — five instances: wrong text layer (compiled PDF vs the figure's own), wrong tree (figures/), point estimate vs CP lower endpoint, "exceeds 1.0" vs "reaches 1.0", wrong file for a compile warning. Each produced a clean-looking result that was an artifact.
  3. **PDF sha256 ≠ content identity.** Same sources, three hashes, identical per-page text.
  4. **Multiplicity corrections weaken bounds.** Bonferroni must *lower* S; my inverted claim implied a negative confidence level (M149). Re-apply the `eps_hi ≤ 1` cap and reproduce a known value before reporting a changed one (constraint C050).
  5. **Prose can invert the maths while the numbers stay right** — three direction words were printed backwards in W1; a reviewer will catch these.
