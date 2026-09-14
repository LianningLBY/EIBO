# Blocked dispatch packages (for Director routing)

Two tasks have been rejected by the content-screening guard on every attempt. Per instruction, they
are packaged here for you to route or re-dispatch. **No further attempts will be made from this
session.**

## Literal rejection text (identical for both, verbatim from the tool)

```
Paper writing is owned by the Director-dispatched Paper Agent. The agent role must report the
writing request and verified evidence state to the Director instead of spawning this Worker.
```

Cumulative rejections across the session: **ECH retrieval ×2, lit-map fixes ×2, ladder rerun ×3**.

---

## Package 1 — Retrieve the ECH source and assess novelty impact

**Purpose.** One bibliography entry has never been retrieved, and its absence is load-bearing for
the novelty claim `MEASURED_BRACKET_IS_NOVEL`. Read it before that claim is locked.

**Target.** Shamsimukhametov, Kurapov, Liubogoshchev, Khorov, "Indistinguishability of Traffic by
Open TLS Parameters with Encrypted ClientHello", *Journal of Communications Technology and
Electronics*, 2023. DOI `10.1134/s1064226923120173`.

**Files.** Writes `artifacts/ech_retrieval_report.json`. Tool groups: `knowledge`. Type `research`.

**Acceptance criteria.** An honest `retrieved` boolean; and explicit answers to: measured vs modelled;
exactly which quantity is reported; whether it is a two-sided bracket; whether its
"indistinguishability" is over *parameter values* (a discrete metadata alphabet) or over *packet
sequences* — this is the decisive distinction from our `TV(P_1^(1:k), P_2^(1:k))`; whether it handles
environment axes; whether any per-pair interval is reported; the strongest case *against* our novelty;
and the correct scoping sentence. Which questions remain unanswered if retrieval fails.

**Verbatim prompt body.**

> Retrieval task. WebSearch + WebFetch only. No SSH, no downloads.
>
> Retrieve and read this specific publication: Shamsimukhametov, Kurapov, Liubogoshchev, Khorov,
> "Indistinguishability of Traffic by Open TLS Parameters with Encrypted ClientHello", Journal of
> Communications Technology and Electronics, 2023. DOI 10.1134/s1064226923120173.
>
> It is the one source on the project's bibliography that has never been fetched, and its absence
> currently bears weight on a novelty claim, so it must be read before that claim is fixed.
>
> Try, in order, and report which succeeded: the DOI landing page via doi.org; arXiv; ResearchGate;
> Semantic Scholar; Google Scholar; the authors' institutional pages (Khorov is at MIPT / IITP RAS);
> any exposed PDF.
>
> Extract, quoting where possible, or state clearly "not stated":
> 1. Is this a measurement on real captured traffic, or a model / analytical study? If measured:
>    what corpus, how many traces, what traffic type?
> 2. What quantity is reported? Specifically — does it report a two-sided bound or interval on
>    total-variation distance between per-class distributions, or something else (entropy,
>    anonymity-set size, classification accuracy, a distinguishability predicate, a single
>    divergence point estimate, a capacity/leakage figure)?
> 3. Does it have a distinct lower and upper side with different certification status, or is any
>    bound one-sided / asymptotic only?
> 4. Is the "indistinguishability" it studies over the same object as `TV(P_1^(1:k), P_2^(1:k))`,
>    the law of the first k packets of a flow? Or is it over parameter values (SNI, certificate
>    fields, cipher lists) as a discrete metadata alphabet? This distinction is decisive.
> 5. Does it separate service identity from environment factors? Any paired design?
> 6. Does it report a per-pair interval, or only aggregate / per-parameter results?
> 7. Argue the strongest case that this work anticipates the project's contribution.
> 8. What is the correct scoping sentence: exactly what it covers and what it does not.
>
> Set an honest `retrieved` boolean. If the full text is unobtainable, say so plainly, report only
> what is verifiable from abstract and metadata, and list which questions remain unanswered. Do not
> infer content from the title.
>
> Output: `artifacts/ech_retrieval_report.json` with keys: retrieved, source_used, title_verified,
> authors_verified, venue_verified, measured_or_modeled, quantity_reported, is_two_sided_bracket,
> lower_upper_certification_split, object_compared, environment_axes_handled,
> per_pair_interval_reported, strongest_case_against_novelty, scoping_sentence, questions_unanswered,
> novelty_claim_impact (CONFIRMS_SCOPE | NARROWS_CLAIM | INVALIDATES_CLAIM | UNRESOLVED), blockers.

---

## Package 2 — Restore graded verification, categories, and notes in the source index

**Purpose.** The recently-completed migration into the loader's expected shape was non-destructive
but flattened or misplaced three things.

**Files.** Edits `literature_map.yaml` (project root); backup is `literature_map.yaml.bak`.
Writes `artifacts/litmap_fix2_report.json`. Group `knowledge`. Type `code`.

**Acceptance criteria — all three fixes, verified by the module's own reader, not by eye:**

- **Fix A (highest priority, C001-related).** The pre-migration file recorded a graded status
  (`verified-abstract` / `verified-fulltext` / `unverified`). The loader's shape has only
  `verified: true|false`, so abstract and fulltext both became `true` and the *level* is gone. The
  project has a rule that a source cited as the theoretical basis for a claim must be verified to
  the theorem level, and the file can no longer answer that. Two entries to get right:
  `michel2020high` (underpins the entire lower bound; backup records abstract level) and
  `liu2026inevitability` (its relevance text asserts a full-text section check while the carried
  status is abstract-level — self-contradictory). Restore `verification_level` ∈
  `abstract | fulltext | theorem | none`. Read `/app/core/tools/literature.py` first to determine
  whether an arbitrary new key survives a rewrite — that decides *how* the fix must be applied, and
  the mechanism must be evidenced by an actual re-read.
- **Fix B.** Top-level `categories` is empty while entries use 7 distinct values. Populate from the
  distinct values or remove the key; decide from how the loader uses it. Also determine which field
  the loader actually filters on — `category` (older vocabulary) or `role` (newer).
- **Fix C.** Each entry's old `notes` text was appended into its `relevance` field during migration.
  Nothing was lost, which was right at the time, but provenance must not live inside the semantic
  content field. Move it to a proper `notes` field and restore `relevance` to its semantic text.

**Must not regress:** the reader must still report **20** entries; all 20 preserved; the
`liu2026inevitability` §4.1 correction retained.

**Verbatim prompt body** (abbreviated only where it restates the above acceptance criteria):
> Local data-repair task on the project's source index. No SSH, no downloads.
> Read `/app/core/tools/literature.py` first to see which fields the writer persists, which the
> reader returns per mode, and whether an arbitrary new key survives a rewrite — that determines
> HOW you must apply the fixes. Back up the current file first and print its size. Verify with the
> module's own reader (mode="summary"): print the reported total and true entry count (must remain
> 20). Print one full example entry (`michel2020high`) showing every field. Output:
> `artifacts/litmap_fix2_report.json` with keys: backup_path, backup_bytes, read_before_total,
> read_after_total, verification_level_added, how_field_survived_rewrite, categories_before,
> categories_after, category_field_authoritative, notes_moved_count, example_entry, schema_valid,
> blockers.

---

## Third blocked task — the rung rerun (NOT one of the two above)

The rerun at corpus-scale n (and the compression-factor sensitivity band) was expected to pass the
guard but was **rejected 3 times** with the identical text. It is a pure local numpy task that reuses
`scripts/generate_channel_ladder_report.py`. Its full specification is in the session report;
it is listed here so the routing decision covers all three.
