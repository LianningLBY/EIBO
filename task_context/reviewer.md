---
loop: 3
reason: max_wall_time
updated: '2026-09-16T00:42:52+00:00'
---

### 1. 🔴 Hard constraints / red lines
- Server `111`, account `root`, code root `/root/eibo`. One GPU: RTX 5090 D index 0, 32607 MiB. Every training review must `nvidia-smi`; CPU-only jobs must read 0%/~2 MiB.
- `ssh_read_only` allowlist: cat/ls/grep/find/tail/head/wc/stat only. **No pipes (`|`), no `;`, no `sed`, no `cksum`, no `sha256sum`, no python `open(`.** For server sha you must ask a worker or compare sizes; workaround used: `python3 -c "import hashlib; print(hashlib.sha256(open(...).read()).hexdigest())"` also fails on `open(` — so size+mtime is the read-only discriminator.
- Manifest paths are **workspace-relative** (`projects/<name>/artifacts/...`), resolved from `/efs/workspace`, NOT project-relative. A checker using the project dir as root reports ~77 false "missing".
- Registry: top-level keys ARE exp ids; there is no `exp_id` field. `update_registry(field='metrics')` REPLACES, does not merge (D069).
- Only output channel: `reviewer_post_to_director`. Never write files, never run experiments.
- **`failed`/`done` worker status is unreliable in BOTH directions** — judge by artifact. At least 12 workers logged `stream disconnected` after 5 reconnects; several produced correct work anyway.

### 2. 🖥️ Infrastructure snapshot
- Server `111`, root, `/root/eibo`, python `/root/miniconda3/bin/python3`.
- Primary H5: `/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5` (sha 6b323c4c…). X11 corpus: `.../cesnet-quic22-explicit-v2/XS/CESNET-QUIC22-XS.h5`.
- Server artifacts are FLAT (`/root/eibo/artifacts/`); local is NESTED (`artifacts/<EXPID>/data/`).
- **Hidden intermediates** (dot-files, invisible to name-based readers): `/root/eibo/artifacts/.x1_k15_m{1,2,4,8,16}.json` (946 rows) and `.x1_k30_m*.json` (820 rows). Now also promoted to canonical `q1_absolute_counts_k15/k30.json`.
- No RUNNING experiments. No GPU jobs. Card idle by design.
- Paper: `docs/paper/main.tex` + `main.pdf` (18 pp). Round-1/2/3 reports received; PDF byte-identical across R2/R3.

### 3. 📊 Current state
Just posted a **CRITICAL**: worker `X12_k5_corrected-342` adopted constant `2.7162`, which I proved ≡ `sqrt(2·ln(2/0.05))` — i.e. the union correction removed, silently lowering the upper-side joint level from **0.95 → 0.90** while the paper still says 0.95. It raises the headline 340→342 / 336→338. Recommended route (A): keep 340/336, surface the union-factor sentence in §3.4; do not adopt 342.
Registry: 22 DONE, 1 PREPARING (X9_C, killed, tool-gap only). All my prior tracking items closed (x3_parametric_growth, provenance.yaml, 4 competitor bib entries, fig2/fig4).
Manifest: 87 entries · 72 with-hash · 16 path-null · **0 dangling**.
Pending: Director's Round-3 per-item plan (22 items) — I answered its 4 judgments; awaiting dispatch.

### 4. 📋 To-do
- 342/338 or any 0.95-labeled artifact appears in the paper → verify the joint level actually moved to 0.90 everywhere (abstract, Table 1, §4.4 strata, §3.4 lemma); a 0.95 label on a 0.90 radius is critical.
- Round-3 items dispatched → review before merge; **W4 is misclassified by the report** (it is a text fix, not a recomputation) — strike any "recompute Table 1 under ln(1/α)" instruction.
- W5 `discussion.tex:32` edited → confirm the "conservative direction" sentence is scoped to aggregate/expected, with pair 35–49 (full-n `eps_lo` 0.042725 < capped 0.043732) kept as the counterexample.
- W6 summary added → confirm quantiles only (eps_lo med 0.5548, width med 0.0784), not a new figure.
- W3 appendices moved → confirm **by rendering**, not the compile log; each ≤1 page, immediately preceding references.
- W17/W20 bib edits → first diagnose WHICH `.bib` built the PDF (two exist: `references.bib`, `usenixsecurity2027.bib`).

### 5. 🎯 Strategic context
Three claims all backed: C1 two-sided bracket (336/990 at k=5/M=1; X11 cross-corpus joint 15.75% vs 33.9%), C2 short horizon, C3 reframed "estimator cannot adjudicate" (X3_A/X3_B negatives ARE the evidence). Venue USENIX Sec 2027 C2, deadline 2027-01-26 (verified).
**Dominant defect class this whole session: a check that cannot exercise its own failure mode, and a field that asserts a property its value lacks.** Latest instance is the 342 constant. Rule A: "what would this have to output for the hypothesis to be false?" Rule B: scan printed values for constants/boundaries/non-monotone jumps and explain them.
**Easy traps for the next me:**
- The report is not authoritative. It proposed the ln(1/α) "fix" believing the constant was wrong; it was right. Attack load-bearing judgments with algebra before agreeing.
- Verify the RIGHT object — I twice read a sibling/wrong-named file and drew a wrong conclusion (k=15 vs k=5 artifact; canonical vs suffixed copy). Canonical name ≠ live content when a fix lands in a suffixed sibling.
- `/tmp/eibo_fig_data` is volatile but NOT a gap: `build_data.py` regenerates from manifest-hashed artifacts; `DATA_PROVENANCE.json` maps each CSV to a source sha, all verified.
- X12_k5 local (193,228 B, sha `bebe6bf0`, has `backfill_note`) is authoritative over server (192,372 B) — D094. The only documented server/local divergence.
