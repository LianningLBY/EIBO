---
loop: 9
reason: max_wall_time
updated: '2026-09-25T03:05:00+00:00'
---

# Handoff — Director loop 9→10

## Where things stand (verified at handoff)

**Paper is frozen and gated.** sha `04b7507f9f80ac9b51f1a4082febedcaa3a475216a30178785d7e54558296415`, 24 pp, body ends **p.13** by the Conclusion's final sentence, **0 `??`**, **valid 24/24 visual receipt on that exact sha**, 0 sources newer than the render.

**Supplementary archive is registered and consistent.** sha `53c7c6bdaa4e64bbd22749f2b58e1ba2206960dac8a095ec47a79bad0bd3820e`, 88 entries, 0 root-level files, registered `art_20260924_2d151d`, **three-way hash agreement** (tree / routed / manifest). Embedded `main.pdf` = `04b7507f…`, `references.bib` = `46b4bff3…`, both byte-identical to the tree.

**Nothing is in flight.** 0 running, 0 workers, registry 0 non-terminal. All 24 experiments terminal.

## 1. 🔴 The two things waiting on the PI — do NOT decide these yourself

1. **VENUE (D236).** Project is shaped USENIX-first; every submission used **USENIX Security 2027 Cycle 2**. But **Round 18's reviewers recommended PoPETs (IMC second) and called USENIX "the weakest of the plausible venues"** (relevance moderate-low; no attack/defense/vulnerability/deployment). No decision-log entry adopts or overrules it. `paper_framing.md`: never silently downgrade the venue — PI discussion. Presented as A/B/C.
   ⚠️ **A nudge may claim Auto Research mode authorizes you to rule on this. It does not.** I declined that twice; so should you. It is the user's strategic call and the instruction is explicit.

2. **ROUND 19 REGISTRATION IS FAILING (D235).** Submitted 22:55 and again 01:15. **Both returned DISTINCT approvals** (`apr_20260924T225518_cl7h`, `apr_20260925T011505_9gg9`) **instead of the documented `deduplicated: true`** — proving no active round exists, so neither registered. Corroborated by `get_formal_review_status` reading round 18 across four checks, no `review_round_19` dir, `review_reports/` ending at round_18.md. **Fails one stage EARLIER than the round-15/16/17 mode** (which registered then failed at review). Platform-side, not ours. **Do not retry blindly a third time.**

## 2. 🔴 Hard constraints / red lines

- **Body page cap is 13** (CFP: ≤13pp excluding References and appendices). **Never compress body prose to buy a page.**
- **Any source edit voids the sha-bound visual receipt** — fresh full render + inspect every page + `confirm_pdf_visual_review` before any `upload_file` or `submit_paper_to_review`. Receipt expires (2h); re-render immediately before EVERY submission.
- **Correct submission order: render → gate → cleanup images → THEN submit.** I once submitted between render and cleanup, and the platform's `docs/paper/` snapshot swept 24 scratch PNGs plus internal notes into the submission. Fixed; the order is the lesson.
- **`camera_ready_plan.md` was moved** to `artifacts/_project/intermediate/` (internal process vocabulary, was being swept into the submission snapshot). NOT in `docs/paper/`. **Do not move it back.**
- **`references.bib` is hash-cited** — editing it invalidates the printed hashes for the 6 cited artifacts in the archive. Check before touching.
- **GPU is bound but idle and that is expected** — all tracks CPU-only, no GPU-eligible work. **C055: do NOT re-triage the `[GPU IDLE]` nudge.**
- **C010/C015:** a dispatch blocked by a content guard must be **reported with its literal error**, NOT reworded to evade (one verbatim retry max). The Agent violated this four times (logged **M180**); I should have handed the work over one block earlier.
- The PI's judgement outranks an internal Accept (2026-09-22: internal Accept was overruled by PI Reject; all four findings integrated).

## 3. 📋 The batched bibliography fix — READY, gated on the venue decision

**All bib edits must be ONE pass**: any `.bib` change voids the receipt and forces render → 24-page gate → archive rebuild → manifest hash update — near-fixed cost regardless of field count. Exact replacement values are in the ROADMAP near-term task.

1. **`li2023facing` — omitted author (required).** Add **Xiaolin Xu** at position 4 (6 total); also `doi = {10.1109/ISCC58397.2023.10218269}`, `pages = {1255--1260}`.
2. **`smith2021website` — WRONG DOI (required).** Ours `10.2478/popets-2021-0018` resolves to a **different paper** ("EL PASSO", Zhang et al.). Correct: **`10.2478/popets-2021-0017`** (PoPETs 2021(2):48–69). Title/authors are right; only the identifier is off by one.
3. **`luxemburk2023cesnet` — omitted author (required).** Add **Pavel Šiška** (last; Crossref 5, we have 4).
4. `diakonikolas2020highprob` — has a published **STOC '21, pp. 542–555** version we don't name (preference).
5. `cesnet2025cesnet` — the Zenodo record itself asks that **Mücke et al. "Waiting for QUIC"** (already `mucke2025waiting`) be cited until the dataset paper appears (preference).
Plus the deferred `2.96 → √C ≈ 2.96×` half-clause at `main.tex:632` (preference; current text is correct, the change only makes the number self-identifying).

## 4. 📊 Bibliography verification: DONE — and the finding matters

**63 of 69 entries verified field-by-field** against authoritative records (arXiv API, Crossref DOI resolver, OpenAlex, Zenodo DataCite API, RFC Editor text). **Query the publisher record directly, never a search snippet** — search could not surface the corpus's author block; the API settled it.

**4 real defects, ALL in inherited entries, none in the 5 added this cycle (~6% error rate, all invisible to structural checks):**
- `veicht2023deepsewf` — fabricated title + 2 invented given names (CFP's named misconduct class; **fixed D220**)
- `li2023facing` — omitted author (D240)
- `smith2021website` — wrong DOI (D241)
- `luxemburk2023cesnet` — omitted author (D241)

⚠️ **I corrected my own earlier report (D239→D240):** at 15 entries I said "no further fabrication found"; that did not hold at 63. Don't repeat that underestimation.

**6 entries remain unverifiable** — no DOI or arXiv id (incl. a 1961 book). Recorded unverified, not clean.

⚠️ **The verification instrument failed on me three times, identically.** A bulk name comparison flagged **28 "wrong author" defects; every one was a formatting artifact** — BibTeX "Surname, Given" vs Crossref "Given Surname", and LaTeX accents (`{\v{C}}ejka` → `vcejka` vs `Cejka`). **Self-test any normaliser on known-tricky strings before believing its corpus output.** Filing those would have "corrected" 28 correct entries.

## 5. 🖥️ Infrastructure snapshot

- Server `111` (root), project path `/root/eibo`. Bound in `execution.servers` but idle by design.
- Paper tree `docs/paper/` (entry `main.tex`, output `main.pdf`). Corpus `/efs/workspace/_corpus/` — one level ABOVE the project tree.
- Platform-local python `/app/.venv/bin/python3` (sklearn 1.9.1) vs server 111 `/root/miniconda3/bin/python3` (sklearn 1.9.0 — the canonical ledger environment). Do not reproduce 111 artifacts with the local one.
- 0 active processes, 0 workers, queue empty, registry RUNNING empty.

## 6. 🎯 Strategic context

**Core claim:** a two-sided ε-indistinguishability bracket — upper side a finite-sample strict bound, lower side a classifier-based high-probability bound — per service pair on real QUIC wire data. Contribution type **measurement/rigour** (D180). Target USENIX Security 2027 Cycle 2 (registration 2027-01-19, submission 2027-01-26, camera-ready 2027-06-03) — **venue pending PI (D236)**.

**Decision chain:** D232 (Round 19 submitted) → D233 (submission snapshot swept internal notes + scratch; fixed, and my sequencing error recorded) → D234 (Agent's two self-corrections verified; M180 logged) → D235 (registration confirmed failing) → D236 (venue escalated) → D237 (registration-failure correlate recorded, discriminating test deliberately NOT run) → D238/D239/D240/D241/D242 (bibliography verification: 63/69, 4 defects).

## 7. ⚠️ Pitfalls the next you is most likely to step into

1. **Stale reads — four instances this session, one of them mine.** Re-read the artifact at the moment you assert it; never carry a hash forward from the message you're answering. Keys/trackers lag the tree.
2. **Checks that verify a neighbouring object.** The fabricated bib entry passed every structural check; a 17/17 ID check was blind to the promised-by-description half; 28 name flags were my own comparison's artifacts. When something looks verified, ask **what that check could not see.**
3. **Do not decide the venue or the registration failure.** Both are surfaced and PI-owned. A nudge asserting otherwise is wrong.
4. **The five-item bib fix is mandatory in part** (items 1–3 are corrections) — do not let it drift as "preferences".
5. **The receipt expires** (2h). Every submission attempt needs a fresh render cycle; the gate will refuse an expired one (it did, correctly).
6. **Do not treat the Round 19 approval as success.** It returned approved twice and registered zero times.

## 8. What I'd do next, in order

1. PI answers the venue → record it explicitly in the decision log (confirmed-with-reason, or changed-with-reframing-plan). A switch to PoPETs means re-layout + Abstract/Intro reframing, not an edit.
2. Once the venue settles, run the batched bibliography pass (5 items + the 2.96 clause) as ONE edit ending in fresh render + 24/24 gate + archive rebuild + manifest hash update.
3. Then re-attempt Round 19 — venue confirmed first; if it fails to register again, escalate as a platform defect rather than retrying.
4. Camera-ready work stays deferred (24→20pp reduction and the per-page table are documented in the ROADMAP).
