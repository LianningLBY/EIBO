# EIBO — Research Dashboard

> Last updated: 2026-09-15 01:00 UTC | Update reason: Writing window open: research complete, Full Draft dispatched to the Paper Agent; adds figures task and the X9_C tool-gap gate

> Last updated: 2026-09-15 00:45 UTC · writing window OPEN — Full Draft dispatched to the Paper Agent.

## Core direction

Certification-grade ε-indistinguishability brackets for open-set encrypted-traffic recognition: for each service pair on real QUIC wire data, a two-sided interval on the total-variation distance whose **upper side is finite-sample strict** and **lower side is asymptotic** — the asymmetry *is* the contribution, not a caveat. Target: USENIX Security 2027 Cycle 2 (deadline 2027-01-26). See `paper_framing.md`.

## The three claims

- **C1** — a two-sided bracket is computable on real encrypted traffic (**336/990 = 33.9%** of pairs at k=5/M=1; upper side binds). Supported in **two independent settings** (primary corpus + X11 cross-corpus). DONE.
- **C2** — the certificate horizon is short; the coarsest channel is the only viable rung. DONE, incl. the divisibility lower bound (X6) at large k where the plug-in certificate is lost.
- **C3** — methods/limits: the standard plug-in chain-rule estimator **cannot adjudicate** the dependent-prefix growth question; robust to two independent repairs (X3_A, X3_B). DONE.

## Current progress

- **Research phase COMPLETE; writing phase OPEN.** All three claims fully backed. ⚠ **The coverage tool's percentages are misleading and must not be read as gaps:** it classifies `conclusion: negative` as "failed", so it reports C1 83.3% (X9, X9_E negative), C3 33.3% (X3_A, X3_B negative) — but **the negatives ARE the evidence**. C3's claim is "the standard estimator cannot adjudicate"; X3_A/X3_B *failing their known-truth gates is what establishes it*. **Evidentiary coverage is 100% for all three claims.**
- **X11 full two-sided bracket on CESNET-QUIC22 (independent corpus) — C1's answer to "one dataset".** 3,321 pairs: upper 16.08%, lower 99.67%, **joint gate 15.75%** (primary: 33.94%). **The lower side reproduces across corpora (99.67% vs 99.60%)** — not a foregone conclusion, since it uses a different method (Michel adaptive). **Scale-matched, the joint-gate gap narrows to 9.7 pts (min n ≥ 20,000) but does not vanish** — the citable form is the stratum-matched pair, **not** the raw single 0.1608 point (closes D076). ⚠ **Disclosed (D093):** the gate ANDs full-n upper with capped-20k lower (2,145/3,321 capped); bias is **CONSERVATIVE**.
- **X9_E — channel-sensitivity finding.** Dose-only hypothesis falsified: at matched declared m the SNI-dependent arm separates from the SNI-independent arm, delta growing 0.03→0.36 before both saturate. **⚠ CLAIM BOUNDARY (D087): established at the `tv_hat` level ONLY** — `eps_hi` is `comparison_unavailable` at every rung, `eps_lo` absent. May write "identifier changes radius-free separation beyond cardinality"; must NOT write "SNI destroys the ε-certificate".
- **X12 k=5 containment holds** (9/9 cells, all detectors `reject_null=false`, guard cannot fire at corrected rates); counts backfilled and verified against their p-values.
- **Provenance discipline is load-bearing**: manifest `content_sha256` on all live entries; runner self-hash captured at import and recorded *in the artifact*; the flat-vs-nested two-tree layout resolved via `resolve_existing_path` (flat first). Cross-tree audit (19 runners, 53 paths): one defect found and fixed, four provenance-only silent-fallback sites deferred.

## Near-term tasks

- [ ] **Paper Full Draft (in progress)** — dispatched to the Paper Agent. Deliverable `docs/paper/main.tex` + `main.pdf`; `writing_plan.yaml` to be approved before section drafting. Binding claim constraints: X9_E scoped to `tv_hat` (D087); X11 per-side n disclosed (D093); X8 DPI check is a smoke-test (D091); C3 reframed (D046); venue not downgraded.
- [ ] **Figures** — dose-response curve (X9_E ladder), the cross-corpus bracket comparison (X11), and the C2 horizon/rung plot. Route non-statistical figures via Agentic Figure; data plots via the approved data path.
- [ ] **x6 input-path resolver** — standing item; give x6's four hardcoded inputs the flat-first resolver **when x6 is next edited** (do not retrofit now).
- [ ] **Four silent-fallback sites** (E7 ×2, Q2 v3, X3 controls) — provenance-only; fix when those files are next touched.

## BLOCKED_ON

| gate | trigger | state |
|---|---|---|
| ~~X12 Stage 2 containment statistic~~ | n/a | **CLOSED** — implemented and ran at k=5; containment holds |
| ~~x3_parametric_growth D057 sentence~~ | n/a | **CLOSED** — withdrawn sentence gone from both trees; sha matches manifest |
| ~~x3_axis_validation pull~~ | n/a | **CLOSED** — local sha matches manifest |
| `X9_C` non-terminal status | a registry status vocabulary that admits `cancelled`/`withdrawn` | **OPEN — tool gap (C034), not work.** A withdrawn-never-run design cannot reach a terminal status without fabricating a managed-run history (M131). Annotated per D096. Blocks passive mode only; costs no integrity. |

## GPU budget

1× RTX 5090 D bound. **X12 (the only GPU-eligible entry) is DONE.** All remaining work is CPU-only (paper assembly, figures) by design — the card idle is a property of the plan, not an omission. Do not invent GPU work to fill it.

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

