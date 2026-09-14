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
| `artifacts/` | **Tracked.** The evidentiary chain: every reported number maps to an artifact's bytes. See `artifacts/manifest.yaml`, which is the authority for artifact location. |
| `docs/` | Paper working tree (`docs/paper/main.tex`), briefs, framing. |
| `tests/` | Regression tests, including the alpha-split and radius guards. |
| `logs/` | **Not tracked.** Runtime logs and chat transcripts. |
| `data/` | **Not tracked.** Local corpora and staged inputs. |

## Claims

- **C1** — a two-sided ε-bracket is computable on real encrypted traffic, upper side finite-sample strict,
  lower side asymptotic (**336/990 = 33.9%** of service pairs at k=5/M=1).
- **C2** — the certificate horizon is short and the coarsest channel is the only viable rung
  (upper-only certifiable fraction falls monotonically in alphabet resolution M).
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
