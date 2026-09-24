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

## Measured page layout (CURRENT build, 24 pp, sha256 `de5e4b63…`)

Measured 2026-09-24 from the current build (sha256 `de5e4b63e24d830f9606f7783fe37835fe23a25d0b2b4b7a6031b10b1060f15d`).
Supersedes all prior tables on this page, which were measured on earlier builds and/or with unstated metrics.
Any further source edit invalidates this table — re-measure rather than reuse.

**EXTRACTOR AND METRICS (stated explicitly — the extractor is part of the metric definition because
poppler's pdftotext disagrees by 4–73 chars/page on the same file).**

Extractor: **PyMuPDF (fitz) `page.get_text('text')`**.

- **chars (len)**: Python `len(text)` on the extracted Unicode string — counts characters, not bytes
- **bytes (UTF-8)**: `len(text.encode('utf-8'))` — counts UTF-8 bytes; non-ASCII glyphs (en-dash, curly quotes, ℓ, ≥) count 2+ bytes
- **words**: `len(text.split())` — whitespace-delimited token count
- **no-ws chars**: `len(''.join(text.split()))` — characters after removing all whitespace
- **no-ws bytes**: `len(''.join(text.split()).encode('utf-8'))` — UTF-8 bytes after removing all whitespace

Reproducible via `artifacts/_project/scratch/page_metrics.py` and its output `page_metrics_result.json`.

| page | chars (len) | bytes (UTF-8) | words | no-ws chars | no-ws bytes | section |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4,620 | 4,647 | 725 | 3,895 | 3,922 | body (title/abstract) |
| 2 | 5,937 | 5,968 | 967 | 4,970 | 5,001 | body |
| 3 | 4,892 | 4,909 | 794 | 4,098 | 4,115 | body |
| 4 | 5,983 | 6,058 | 978 | 5,005 | 5,080 | body |
| 5 | 5,173 | 5,314 | 899 | 4,274 | 4,415 | body |
| 6 | 5,437 | 5,465 | 925 | 4,512 | 4,540 | body |
| 7 | 5,699 | 5,723 | 930 | 4,769 | 4,793 | body |
| 8 | 5,814 | 5,861 | 974 | 4,840 | 4,887 | body |
| 9 | 6,157 | 6,188 | 1,018 | 5,139 | 5,170 | body (fullest) |
| 10 | 5,982 | 6,016 | 977 | 5,005 | 5,039 | body |
| 11 | 5,693 | 5,751 | 919 | 4,774 | 4,832 | body |
| 12 | 5,733 | 5,751 | 880 | 4,853 | 4,871 | body |
| 13 | 4,821 | 4,831 | 736 | 4,085 | 4,095 | **body END — Conclusion** |
| 14 | 1,315 | 1,317 | 204 | 1,111 | 1,113 | Ethical Considerations — **slack** |
| 15 | 5,114 | 5,137 | 697 | 4,417 | 4,440 | Open Science (1/2) |
| 16 | 3,434 | 3,461 | 382 | 3,052 | 3,079 | Open Science (2/2) — slack |
| 17 | 4,810 | 4,847 | 780 | 4,030 | 4,067 | Appendix |
| 18 | 4,837 | 4,901 | 853 | 3,984 | 4,048 | Appendix |
| 19 | 3,951 | 3,988 | 671 | 3,280 | 3,317 | Appendix |
| 20 | 3,707 | 3,723 | 651 | 3,056 | 3,072 | Appendix |
| 21 | 4,496 | 4,549 | 766 | 3,729 | 3,782 | Appendix |
| 22 | 5,371 | 5,435 | 766 | 4,605 | 4,669 | References (start) |
| 23 | 7,596 | 7,641 | 974 | 6,622 | 6,667 | References |
| 24 | 3,649 | 3,655 | 468 | 3,181 | 3,187 | References (end) |
| **total** | **120,221** | **121,121** | **18,859** | **100,330** | **101,226** | |

**Body pages (1–13)** run 3,895–5,139 no-ws chars (fullest p9; body end p13 = 4,085).
The back matter carries the slack: **p14 (1,111 no-ws chars)** and **p16 (3,052)** are far below the body band.

**Recoverable slack without content loss:** the camera-ready target is the CFP rule at the top of this
file: **20 pp total, inclusive of Ethics, Open Science, bibliography and every appendix** (verified
verbatim from the CFP). Current build 24 pp, so the gap is **4 pages** — that figure is arithmetic
from the page counts, NOT from this table. What must be re-derived per lever is the **pp estimate**,
not the gap.

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
