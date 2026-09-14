# EIBO

**Epsilon-indistinguishability brackets for open-set encrypted-traffic recognition — certification grade.**

Measured, certification-graded ε-indistinguishability brackets for open-set QUIC service recognition: for
each service pair, a two-sided interval on the total-variation distance between observable laws, whose two
sides carry **explicitly different epistemic status**.

Target venue: **USENIX Security 2027, Cycle 2 (deadline 2027-01-26)**.

## Layout

| Path | Contents |
|---|---|
| `src/eibo/` | Reusable research code. `statcore.py` (TV bounds) and `divisibility.py` (rejection-generic lower bound) are the **authority** for their formulas — call them, never restate. |
| `scripts/` | Command-line experiment and analysis scripts. |
| `artifacts/` | **Tracked, including `artifacts/**/data/`.** The evidentiary chain: every reported number maps to an artifact's bytes. See `artifacts/manifest.yaml`, which is the authority for artifact location — not any directory. |
| `docs/` | Paper working tree (`docs/paper/main.tex`), briefs, framing. |
| `tests/` | Regression tests, including the alpha-split and radius guards. |
| `logs/` | **Not tracked.** Runtime logs and chat transcripts. |
| `data/` | **Not tracked** (root-anchored; corpora and staged inputs only). |

**Every artifact is tracked.** All 58 JSON artifacts under `artifacts/` are in version control. Bulk binaries —
`*.h5`, `*.pcap`, `*.pt`, `*.pth`, `*.safetensors`, `*.pkl` — are excluded by extension.

**Server-only payloads, listed by name (the one exception to byte-traceability).** The k=5 detector run wrote
three score payloads of about **1.14 GB each**:

| payload | size | why it is not tracked |
|---|---|---|
| `artifacts/X12_k5/data/x12_detector_validation_k5__per_class_scores__lightgbm.npz` | ≈1.14 GB | too large to version; per-flow error is reconstructable from it |
| `…__per_class_scores__prototype.npz` | ≈1.14 GB | same |
| `…__per_class_scores__ronetc.npz` | ≈1.14 GB | same |

These live on the experiment server only and are excluded by the `*.npz` rule. **They are named here because an
untracked artifact silently breaks the byte-traceability claim below** — a reader must be able to tell, from
this file alone, which artifacts are *not* in the repository and why. The results computed from them are in
`x12_detector_validation_k5.json`, which *is* tracked.

## Claims

- **C1** — a two-sided ε-bracket is computable on real encrypted traffic, upper side finite-sample strict,
  lower side asymptotic (**336/990 = 33.9%** of service pairs at k=5/M=1). **The gate is not a settled
  constant and must not be cited as one:** it sits at 336 because exactly one boundary pair crosses the
  0.05 line, and its own artifact requires the sensitivity to travel with the number. Corrected full-n
  margins are **+0.0088** (nearest passing pair) and **−0.0073** (nearest failing pair), **0 pairs within
  0.005**. Two companion readings travel with it: pair (35,49) moved the *wrong* direction as n grew, so
  "larger n tightens the lower bound" is a tendency, not a guarantee; and pair (39,44) is bit-identical
  across runs only because its full n sat *below* the cap, so "no change" there means "never bound", not
  "stable".
- **C2** — the certificate horizon is short and the coarsest channel is the only viable rung
  (upper-only certifiable fraction falls monotonically in alphabet resolution M). **The mechanism runs
  opposite to the intuition:** a finer alphabet **resolves more, not less** — channel TV at k=5 rises
  **0.5805 → 0.8833 → 0.9248 → 0.9462 → 0.9673** — and since the certificate requires
  `eps_hi = tv + radius < 0.5`, that *higher* TV is exactly what destroys it. Coarse-graining is
  *required* for a certificate to exist at all, not epistemically preferable. (M=1 also has the
  **highest** `k_cert`, not the lowest.)
- **C3** — a methods/limits finding: the standard plug-in chain-rule estimator **cannot adjudicate** the
  dependent-prefix growth question at this k window, n, and occupancy-collapse curve, and it is robust to
  two independent repair attempts.

## Reproducibility discipline

This project's working rules, learned by measurement rather than assertion, and worth preserving:

1. **Every reported number maps to an artifact's bytes.** The manifest is the authority for artifact
   location — not any directory. An artifact must have exactly one live manifest entry whose `path`
   resolves.
2. **A control must be able to fail.** Before treating a test as evidence, state what it would output if
   the hypothesis were false. A zero-intervention setting must reproduce its reference exactly; a fitted
   curve must be proven non-saturated before any exponent is reported from it; a replication count must
   carry its **testable** row count, not its total.
3. **Never restate a formula the repository implements.** Call the function and print the value beside it.
4. **Two artifacts disagreeing on one nominal quantity at one nominal setting blocks both** — but a shared
   quantity under *different* intervention settings is a dose–response family, not a conflict.
5. **The two trees are separate.** Writes on one are not visible on the other; a "file is missing" verdict
   is a statement about which tree, and needs a literal error before it becomes a claim of non-existence.

## Status

Active research. See `ROADMAP.md` for the live dashboard and `experiment_plan.yaml` for the experiment list.
