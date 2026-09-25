# Camera-ready plan — W11g / R14-M2 (24 pp -> 20 pp)

Status: PLAN ONLY. Do not execute now.
Written 2026-09-20. Transcription of the plan as delivered to the user in chat.

## The rule (verified verbatim from the CFP, not from any summary)

From `artifacts/_project/reference/usenix_sec27_cfp_extracted_20260918.txt`:

- "The main body of the submission must not exceed 13 pages excluding References
  and any appendices." -> SUBMISSION rule. Current build is COMPLIANT (body p.13).
- "At submission time, there is no limit on the length of the bibliography and
  optional appendices" -> SUBMISSION rule. Current build is COMPLIANT (24 pp total).
- "Once accepted, papers must be reformatted to fit in 20 pages, including any
  'Ethical Considerations' or 'Open Science' appendices, the bibliography, and any
  additional optional appendices." -> CAMERA-READY rule, and it is TOTAL: the 20
  counts Ethics, Open Science, bibliography and every appendix. This is why the
  reduction cannot be met by shuffling material into appendices.
- "Papers must be self-contained without the optional appendices." -> This is the
  CFP basis for R14-M7/W9. The primary result table living in §A.4 is a
  SELF-CONTAINMENT issue, not merely a placement preference.

## Measured page layout (CURRENT build, 24 pp, sha256 `32dadd14…`, 416,639 B)

**⚠️ RE-MEASURED 2026-09-22 against the CURRENT delivered build.** An earlier table on this page was
attributed to `789fa982…` but reproduced under no metric and stated none — it was superseded. A second
version tracked `5f08a9fb…`, which is now two builds stale (D191/D192/D193 changed the body). **The table
below is measured on `32dadd14…`, the build delivered to the PI. Any further edit invalidates it — re-measure
rather than reuse.**

**METRIC, stated explicitly because its absence caused the original defect.** Counts are
**UTF-8 bytes of the extracted text, with ALL whitespace removed**:
`pdftotext -f N -l N main.pdf - | tr -d '[:space:]' | wc -c`. (Note `wc -c` counts *bytes*, not
characters — the pages carry non-ASCII glyphs (en-dash, curly apostrophes, ℓ, ≥) at 2 bytes each,
so a char count reads lower on affected pages. State the unit whenever quoting these.) A second column
gives whitespace-INCLUSIVE bytes for reference.

| page | no-ws bytes | incl-ws bytes | note |
|---|---|---|---|
| 1–12 | 3,915–5,159 | 4,643–6,191 | body (fullest p9 at 5,159) |
| **13** | **4,076** | 4,804 | **body END — Conclusion** |
| **14** | **1,109** | 1,312 | Ethical Considerations — **whitespace slack** |
| 15 | 4,424 | 5,116 | Open Science (1 of 2) |
| 16 | 3,070 | 3,476 | Open Science (2 of 2) — slack |
| 17–21 | 3,062–4,058 | 3,759–4,950 | Appendix |
| 22–24 | 3,177–6,647 | 3,638–7,605 | References |

Full per-page no-ws values (p01→p24): 3915, 4980, 4098, 5066, 4403, 4524, 4778, 4878, 5159, 5026, 4824,
4851, **4076**, **1109**, 4424, 3070, 4058, 4038, 3314, 3062, 3771, 4662, 6647, 3177. Total 101,910.

**Body pages run 3,915–5,159 no-ws bytes; the fullest body page is p9 (5,159) and the body's last (p13)
is 4,076.** The back matter is where the reduction lives: **p14 (1,109) and p16 (3,070)** are far below the
band. The camera-ready target is the CFP rule at the top of this file: **20 pp total, inclusive of Ethics,
Open Science, bibliography and every appendix** (verified verbatim). Current 24 pp → gap **4 pages**; that
figure is arithmetic from the page counts, NOT from this table. What must be re-derived per lever is the
**pp estimate**, not the gap.


| page | no-ws bytes | incl-ws bytes | what it is |
|---|---|---|---|
| 1 | 3,656 | 4,342 | body (title/abstract) |
| 2 | 5,016 | 5,980 | body |
| 3 | 4,500 | 5,354 | body |
| 4 | 4,757 | 5,769 | body |
| 5 | 4,356 | 5,293 | body |
| 6 | 4,825 | 5,815 | body |
| 7 | 4,709 | 5,636 | body |
| 8 | 4,876 | 5,888 | body |
| 9 | 5,178 | 6,215 | body (fullest) |
| 10 | 4,951 | 5,919 | body |
| 11 | 4,818 | 5,736 | body |
| 12 | 4,685 | 5,546 | body |
| 13 | 4,620 | 5,441 | **body END — Conclusion** |
| 14 | 1,109 | 1,312 | Ethical Considerations — **whitespace slack** |
| 15 | 4,257 | 4,914 | Open Science (1 of 2) |
| 16 | 2,395 | 2,707 | Open Science (2 of 2) — slack |
| 17 | 4,104 | 4,958 | Appendix |
| 18 | 3,470 | 4,190 | Appendix |
| 19 | 3,610 | 4,403 | Appendix |
| 20 | 4,189 | 5,095 | Appendix |
| 21 | 3,276 | 4,014 | Appendix (sparse — table) |
| 22 | 4,668 | 5,509 | References (start) |
| 23 | 6,662 | 7,610 | References |
| 24 | 1,965 | 2,256 | References (end) |

**Body pages (1–13) run 3,656–5,178 no-ws bytes; the fullest appendix page 21 is 3,276 and
References p24 is 1,965.** Note the body band is considerably *lower* than the superseded table
claimed (~6,600–8,100) — that band was an artifact of the unreproducible metric, so any
"page is under-filled" judgement must be made against the numbers above, not the old band.

**Recoverable slack without content loss:** p14 (~1,109 no-ws) and p16 (~2,395 no-ws) are far below
the body band, so the back matter is where the page reduction lives. The target is the CFP
camera-ready rule at the top of this file: **20 pp total, inclusive of Ethics, Open Science,
bibliography and every appendix** (verified verbatim from the CFP). Current build 24 pp, so the gap
is **4 pages** — that figure is arithmetic from the page counts, not from the superseded per-page
table, and it stands. What must be re-derived from the table above is the **pp estimate per lever**
(the old "p14 ~0.75 pp / p16 ~0.4 pp / p13 ~0.2 pp -> about 1.3 pages" line was computed on the
unreproducible numbers and is superseded).

## Planned levers, in safest-first order

**⚠️ LEVER 1 IS NOW TESTED, NOT ESTIMATED (2026-09-20, in a scratch copy — the working tree was
NOT touched and its visual receipt is intact).** Result: **24 pp -> 23 pp with zero content loss**,
body still ending p.13 (the hard constraint holds), References moving p.22 -> p.20.

The mechanism is NARROWER than this plan originally assumed, and the correction matters:

- Removing ONLY the `\clearpage` before Ethical Considerations buys **NOTHING** — the document
  stays at 24 pp and that page stays near-empty (150 chars). The Ethics page is not made empty by
  its own break; it is pinned empty by the *next* one.
- The two breaks are **COUPLED**. Removing BOTH (before Ethical Considerations AND before
  Open Science) is what recovers the page. Neither alone does.
- The mechanism is therefore an **explicit `\clearpage`**, not float placement — which is why
  plain flow removal works and no float surgery is needed for this lever.

Measured per-page density after removal (scratch): p13 6,732 / p14 6,668 / p15 3,839 — p15 still
carries roughly 2,800 chars of slack, so more than one page remains recoverable here.

1. **Remove BOTH `\clearpage` calls before the Ethical Considerations and Open Science sections
   (do first — TESTED).** ~1.0 pp recovered, no content loss, body stays p.13. Appendix-side of
   the 13-page body rule, so it cannot break the submission constraint.
2. **Tighten the Open Science tail.** Reflow the artifact list and consider presenting the
   registered loads as one table rather than a paragraph each; that page is only ~58% full
   after lever 1.
3. **Merge §A.7 with §5.5.** Both discuss dependence/coverage. **Scope this as
   APPENDIX-SIDE ONLY** — the body must not lose prose (the body is already at exactly
   p.13 and body-prose cuts to buy a page are a standing red line). Estimated ~0.8-1 pp
   only if the merge is genuinely appendix-side.
4. **Compress Table 6** to the key rows plus an interval description. ~0.2 pp.
5. **Reference compression.** p20+; the CFP counts them. Tighter spacing, or accepting
   the template's default grouping.
6. **Return the M=1 row of Table 3 to the body** — this is the R14-M7/W9 fix, NOT a page
   saver (it costs body space). Do this with the page budget in hand so it does not push
   the body over 13.

Lever 1 is measured; levers 2-6 remain estimates and each must be measured before it is relied on.

## Hard constraints on execution

- Any source edit voids the visual-review receipt for the current bytes; the whole
  reduction must be ONE pass followed by ONE fresh full render and a 24-page (or
  post-reduction, N-page) visual gate.
- Body prose must NOT be compressed to buy a page.
- If a float moves, re-check file -> label -> number -> prose by reading `\newlabel`
  from the `.aux`; `??`-counting and bare grep are both blind to a resolving-but-wrong
  reference.
- Do NOT mix conventions in any table touched by the compression.

## Timing

Not urgent. Camera-ready deadline is 2027-06-03; the submission deadline is
2027-01-26 and the paper is already submission-compliant at 24 pp. Execute this
only after acceptance, and only in one batched pass.
