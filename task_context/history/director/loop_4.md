---
loop: 4
reason: max_wall_time
updated: '2026-09-18T18:28:56+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Paper tree is `docs/paper/` (`main.tex` entry). Compile: pdflatex → bibtex → pdflatex → pdflatex.** `pdflatex` exits 1 on this template despite a clean log — not a failure.
- **Which page cap binds at which stage (verified from the CFP PDF, D162):** submission = **body 13 pages HARD**, appendices/references **unlimited**; the **20-page max is camera-ready only** (final papers 2027-06-03). So **22 total pages is compliant at the 2027-01-26 submission**; only the body must be ≤13. Do NOT trade away `\clearpage`s, figures, or protected disclosures to chase 20 today.
- **Never locate the body's end by the "Conclusion" heading** — heading and final sentence can differ by a page. Match the final sentence ("…cannot settle the growth question"). This error was made twice, by two different parties.
- **To restore an overrun, relocate a FLOAT — and it may be a TABLE, not a figure.** With all figures already in the appendix, moving **Table 3** to §A.4 was the only lever that worked (nine probes). Never shrink a figure; never cut a protected disclosure.
- **Protected — do not weaken:** §3.3 combinatorial disclosure, §3.4 object/sample + M-scope, §4.5 covariance, §1 "alternative dependence mechanism", §7 calibration sentence, §3.1 hedges, the abstract's four qualifiers + combinatorial clause, and the D166 both-bounds statements.
- **Never put a `\label` on a `\section*`/`\subsection*` heading** — prints an EMPTY string, no error, no `??`. Zero remain; keep it that way.
- **`m = (2M)^k`, never 32.** The per-k files hold 990 pairs × 5 M values = 4950 rows — **filter per-M AND recompute m per M** or rung counts come out silently wrong (I nearly published this).
- **Every bound must declare which object's TV it bounds**, and every claim carries its window and channel.
- Paper English; **user-facing replies Chinese**; never put server paths in user-facing messages.

### 2. 🖥️ Infrastructure snapshot
- Server `111` (connect.westb.seetacloud.com), path `/root/eibo`, account `root`, auth password. 1× RTX 5090 D (32 GB) — **idle and correctly so**: X12 is DONE, the open-set line is closed, everything remaining is CPU-only authorship. Do not invent GPU work.
- Python: `/root/miniconda3/bin/python3`. Local: `/app/.venv/bin/python3` with `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages` (has `numpy`, `scipy`, `tables`, `fitz`).
- **Per-rung data is LOCAL in `artifacts/_project/data/`**: `q1_lower_side_full_n.json` (990 rows, full-n), `q1_absolute_counts{,_k10,_k15,_k30}.json` (per-pair tv + n_a/n_b, 5 M values each), `q1_absolute_dense_counts_m1_m2.json` (per-symbol counts, M=1/M=2 only), `x1_headline_table.json` (20 (M,k) cells). The corpus `CESNET-QUICEXT-25-XS.h5` is at `/efs/workspace/_corpus/`, **one level ABOVE the project tree** — a project-tree search reports it missing and is wrong.
- Active processes: none. Registry: no RUNNING/PREPARING except the stale `X9_C` (below).

### 3. 📊 Current state
**D166 landed and I verified it myself.** A reviewer-supplied finite-sample upper bound (population-optimal distinguishing set `A*`; `TV <= tv_hat + sqrt(ln(2/δ)/(2n_a)) + sqrt(ln(2/δ)/(2n_b))`) is **valid and 2.91× tighter** than Eq (6); the `√(m/n)` term is a property of the L1/subset-supremum *route*, not of the problem. Recomputed from local ledgers: k=5 **340→363**, k=10 **28→98**, k=15 **0→18**, k=30 0→0 (597/820 already saturated, median tv 0.9979), M=2/k=5 **47→127**. Both 340 and 47 reproduce the paper's own counts — the convention check.

**⇒ C2's mechanism sentence was FALSE** ("the radius grows with the alphabet"). The binding cause is **saturation of the plug-in estimate's own upward bias**. The paper now states both bounds, keeps Eq (6) primary (R12 was scored on it), attributes the frontier to saturation, and writes "we first attributed this to the radius". The old attribution **survived one edit pass** and had to be caught twice — `grep -rn "as the alphabet is refined"` after any C2 edit.

**Also landed:** citation [31] corrected in **three** places (its Theorem 1 carries no independence/stationarity hypothesis — the blanket claim was false about someone else's theorem); Open Science artifact-access made CFP-compliant (a first attempt **invented** an access agreement and was caught only by reading our own Data statement).

**Current bytes verified:** sha `cf7bf7b3…`, **22 pages, body ends p.13**, Ethics p.14, 64 bibitems, 0 undefined/overfull/fatal/`??`, visual review passed 22/22, figure/table bindings verified at three layers. **Not submitted.**

**Pending:** nothing in flight. No workers, no cron, no experiments.

### 4. 📋 To-do (condition-triggered)
- **User picks (A)/(B)/(C) →** (A) run a verification round on the final bytes then submit **[my recommendation: the bytes have changed materially since R12's 5/5, so its score is not about them]**; (B) submit now **[not recommended]**; (C) paste the revised C2/A.4 passages for them to read first. I have deliberately NOT taken the submit decision myself.
- **If revising further →** the only local gap is the (M,k) cells beyond M∈{1,2} at k=5; they need higher-M per-pair data (not local) or a corpus pass. **Do not interpolate them** — the paper says so explicitly.
- **Before camera-ready →** fold 22 → 20 pages (that cap binds 2027-06-03, not now). The near-empty p.16 (Open Science tail, ~41 KB) is the obvious absorber.
- **Before any submission →** re-run the visual gate if bytes change; `\bibitem`=64; 0 `??`; body's last page by final-sentence match.
- **If a page count or "fixed" claim is disputed →** compare sha256 first, then render. A disagreement about a number is usually a disagreement about which file was opened.

### 5. 🎯 Strategic context
- **Contribution type: measurement/rigour, NOT a new mechanism** — the project's self-description since the MVP, not a later retreat. Target USENIX Sec 2027 Cycle 2: registration 2027-01-19 (ORCID + fixed author list), submission 2027-01-26.
- **Review history:** R12 was **strong accept 5/5, the first unanimous full-marks round in twelve**, with the panel explicitly releasing the paper. **That was earned on pre-D166 bytes.** Every previous round's fixes moved toward *weaker and more accurate* claims — that is the property the panel named, and it is the one to protect.
- **Two negative-by-design probes closed the "is there a cheap way around this?" question on both sides of the bracket:** lower side (D165) — an exact finite-sample endpoint exists but captures only ~5–17% of true TV at the real deviation structure; upper side — the horizon is inherent to the method class **for the L1 route**, and D166 now shows the two-point route escapes the alphabet price.
- **Easy mistakes to step into:** (i) believing a quoted page count or "fixed" claim from any handoff or audit — verify the sha256 and render; (ii) reading `x1_headline_table.json`'s `upper_radius_median` as a radius — in saturated cells it is post-clamp slack (M=16,k=5 records 0.03270 = 1−0.9673) and a naive "radius vs k" plot **manufactures** the very growth the paper wrongly claimed; (iii) trusting a passing completion check as evidence the *claim* survives replication (the D165 probe passed while its headline number did not reproduce); (iv) inferring a figure number from a filename (`fig4` is Figure 3, `fig2` is Figure 4, `fig3` is Figure 2).
- **Registry hygiene:** `X9_C` carries a stale `PREPARING` for a **withdrawn design that never ran** — deliberate and documented, no honest terminal value exists; **exclude it when filtering on status.**
- **Known recorded limitation:** Fig 1's in-figure text is 2.1–5.1pt against 10pt body — illegible at print size. Accepted wontfix after six rounds, **recorded rather than dropped**, and it will be visible in any submitted PDF.
