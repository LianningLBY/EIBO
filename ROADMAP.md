# EIBO — Research Dashboard

> Last updated: 2026-09-15 05:55 UTC | Update reason: Paper drafted and in formal review Round 1; check off the completed build/figure work, add the review-response task

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is finite-sample strict** and **lower side is asymptotic** — the asymmetry *is* the contribution, not a caveat. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). Supported in **two independent settings** (primary corpus + X11 cross-corpus: 523/3321 = 15.75%, upper 534 / lower 3310). DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung. DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs (X3_A, X3_B). DONE.

## Current progress

- **Research phase COMPLETE.** All three claims fully backed; evidentiary coverage 100%. (The coverage tool labels `conclusion: negative` as "failed", so it under-reports C1/C3 — the negatives ARE the evidence; noted, not "fixed" in the tool.)
- **Paper DRAFTED AND IN FORMAL REVIEW — Round 1 active** (`review_id ebf482e0`), 3 reviewers dispatched. Deliverables: `docs/paper/main.tex` + `main.pdf`, 16 pages with the body ending mid-page-12 (inside the 13-page limit), appendices carry the mandatory Open Science and ethics sections. Compiled against the genuine USENIX Security 2027 kit.
- **Pre-submission verification (all done by me, not relayed):** 3 pdflatex passes + bibtex exit 0, 44 bibitems, 0 undefined citations, 0 overfull boxes; **visual review 16/16 pages passed** (receipt bound to sha256 `abc000bd`); headline numbers independently re-derived from artifacts — C1 336/990, X11 523/3321, chain-rule per-position truth `0.3389191441548814`; references 44 entries all cited, zero dangling, both bib copies byte-identical.
- **Claim boundaries honoured in the prose**: X9_E's identifier finding scoped to `tv_hat` only (D087); X11's joint gate discloses its per-side sample sizes and the **conservative** bias direction (D093); X8's DPI check is a smoke-test, never cited as theorem verification (D091); C3 reframed as a methods/limits finding (D046); novelty stated as a knowledge claim ("to our knowledge"), never "exhaustive search".
- **Provenance discipline is load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; figures regenerate from manifest-resolved artifacts via committed generators; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first).

## Near-term tasks

- [ ] **Await and act on the Round 1 review report** — on arrival run the holistic pass then the per-comment Action Matrix (`review-report-action` skill); do not respond with a blanket acknowledgement.
- [ ] **x6 input-path resolver** — standing: give x6's four hardcoded inputs the flat-first resolver **when x6 is next edited** (do not retrofit now).
- [ ] **Four silent-fallback sites** (E7 ×2, Q2 v3, X3 controls) — provenance-only; fix when those files are next touched.

## BLOCKED_ON

| gate | trigger | state |
|---|---|---|
| ~~X12 Stage 2 containment statistic~~ | n/a | **CLOSED** — implemented and ran at k=5; containment holds |
| ~~x3_parametric_growth D057 sentence~~ | n/a | **CLOSED** — withdrawn sentence gone; sha matches manifest |
| ~~x3_axis_validation pull~~ | n/a | **CLOSED** — local sha matches manifest |
| `X9_C` non-terminal status | a registry status vocabulary admitting `cancelled`/`withdrawn` | **OPEN — tool gap (C034), not work.** A withdrawn-never-run design cannot reach a terminal status without fabricating a managed-run history (M131). Annotated per D096. Costs no integrity. |

## GPU budget

1× RTX 5090 D bound. **X12 (the only GPU-eligible entry) is DONE**; all remaining work is CPU-only (paper, review response) by design. The card idle is a property of the plan, not an omission — do not invent GPU work to fill it.

## Key Decision Log

| ID | Date | Summary | Related experiments |
|----|------|---------|---------------------|
| D099 | 2026-09-15 | D099: C3's control citation pointed at the BIC rou | X3 |
| D098 | 2026-09-15 | D098: do not reshape registry keys to satisfy a va | X1, X11 |
| D097 | 2026-09-15 | D097: figures verified (fig3 synthetic data fixed, | X3 |
| D096 | 2026-09-15 | D096: do not force X9_C to terminal; accept the st | X9_C |
| D095 | 2026-09-14 | D095: the 5 unlinked experiments split into MVP-er | X3_A, X3_B, E3, E7, E10 |
| D094 | 2026-09-14 | D094: artifact chain-of-record is local+manifest+r | X12_k5 |
| D093 | 2026-09-14 | D093: X11 joint gate mixes two sample sizes (conse | X11 |
| D092 | 2026-09-14 | D092: X11 full bracket closes D076 — joint-gate ga | X11 |
| D091 | 2026-09-14 | D091: X8 DPI check is vacuous (0/990 testable); re | X8 |
| D090 | 2026-09-14 | D090: X12 containment WAS executed at k=5 (9/9 rej | X12_k5 |


