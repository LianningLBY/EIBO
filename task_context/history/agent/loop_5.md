---
loop: 5
reason: max_wall_time
updated: '2026-09-23T21:09:09+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **`docs/paper/` is untouched and must stay that way.** Current delivered build `5f08a9fb…` / 414,613 B / 24 pp. Any source edit voids the SHA-bound visual receipt. Three `\clearpage` at `main.tex:69/94/243`.
- **I do not author paper text.** Drafting prose, labels, references, registry entries = paper content, even on a scratch copy, even as a diff. Hand back a verified evidence package and refuse in the open. The Director confirmed and retracted the instruction that asked for the edit diff. Scratch-copy *compile-and-measure* of an unmodified copy IS allowed.
- **All D181 work is CPU-only and runs LOCALLY.** Server 111's GPU has no GPU-eligible work; the recurring idle notice is C055 binding/timing mismatch. **Do not `read_registry`, check workers, write `[Resources]`, or report on GPU-idle notices.** Silence is the standing rule.
- **Every answer to a Director instruction goes through `main_agent_post_to_director`.** Plain-text output is invisible. I lost a full turn failing this.
- **`register_artifact` COPIES into a type-routed path and SUFFIXES on collision.** Never re-register.
- **Server 111 has NO `python3` on PATH** — use `/root/miniconda3/bin/python3`.
- **Do not let two workers share one scratch directory.**

### 2. 🖥️ Infrastructure snapshot
- Server `111`, account `root`, project `/root/eibo` — but all D181 jobs ran locally, not there.
- Local Python: `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages /app/.venv/bin/python3` (3.12.14, numpy 2.5.3, sklearn 1.9.1; the venv lacks SciPy so the PYTHONPATH injector is mandatory).
- Corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5` — one level ABOVE the project tree; sha `6b323c4c…`.
- **Active processes: NONE. Workers: 0. Registry RUNNING/ALLOCATED: 0.** Only `X9_C` (PREPARING/`killed`) — stale withdrawn design, exclude when filtering.
- Disk 111 = 20% (~25 GB free).
- Scratch artifacts from this session at `artifacts/_project/scratch/lever1_recheck/` (two builds: `baseline_final/` and `lever1_final/`, each with a compiled PDF) and `artifacts/_project/scratch/metric_defs/METRICS.md`.

### 3. 📊 Current state
**Waiting on two things, both external to me:**
1. **The Paper Agent** has a four-edit spec for `measurement_design.tex` (cap count 29→6, alpha label 0.012→labelled pair, floor labelling ×4 sites, citation gap ×2 artifacts). The Director reviews its diff, then instructs the single batched rebuild with one fresh render and one visual gate.
2. **The PI** is reviewing the delivered D181 revision (`5f08a9fb…`). No new experiment or verification work starts until the PI rules.

**Registry:** 0 RUNNING, 0 ALLOCATED. `X9_C` is the only non-DONE row (PREPARING/killed, stale).
**Workers:** 0 in flight. Last two (lever-1 recheck, metric-def check) both completed this session.
**Crons:** 0 active.

### 4. 📋 To-do (condition-triggered)
- **Paper Agent returns the diff → Director reviews → Director instructs rebuild** → when the rebuilt PDF exists, the reviewer ping MUST include the item-(3) refutation (detector gap "0.63 should be 0.54" is WRONG; arm arithmetic: 0.830−0.197=0.633, not 0.737−0.197=0.540). Otherwise the phantom gets re-filed.
- **PI rules on the D181 revision → Director relays** → act on whatever direction arrives. If Accept, the camera-ready stage opens and the per-page table must be regenerated first (the plan's table is unusable — not reproducible from its cited build under any metric). If Reject with findings, prepare evidence as before.
- **Any `register_artifact` instruction → grep the manifest for the name FIRST.** Re-registering makes a suffixed duplicate.
- **Any count/presence claim → parse and diff key sets**, never count with a regex.
- **Any relational claim from a review → re-derive from the artifact before editing.** One third of the last critical report was wrong.

### 5. 🎯 Strategic context
**Decision chain highlights:** D143 ladder abandoned · D166 m-free Hoeffding verified · D168 paper convention is UNCAPPED · D169/D170 Track 5 closed · D178 Round 14 Accept 3/3 · D181 PI overrode Accept as Reject → evidence phase complete, revision delivered (`5f08a9fb…`) · D182 m-free route adopted as headline · D188 four text-accuracy edits identified, spec with Paper Agent.

**The four edits are with the Paper Agent, not me.** The authoring boundary was tested twice this session — I over-refused a scratch compile (wrong), then correctly refused a prose-editing task. The Director confirmed and retracted. Do not collapse these two again.

**Most likely misjudgement by the next me:** (1) treating a reviewer's "critical" as an instruction rather than a claim to re-derive — item (3) was wrong and aimed at a correct number; (2) quoting a hash from an instruction message and inheriting its truncation — always take hashes from the manifest; (3) attributing an effect to the wrong variable — lever 1 moves the Ethics heading from p.14 to p.13, not D181; the unmodified rebuild is the control that proves it.

**Bytes-vs-chars is RESOLVED (not a live issue).** `wc -c` = UTF-8 bytes, Python `len()` = characters; the 12/2/16 byte gaps on p13/p14/p16 match exactly 6/1/8 non-ASCII glyphs at 2 bytes each. Both metrics are stable. The metric-independent content statement (footer-stripped hash `cd13e95b…` identical on both builds) is the statement of record for lever-1 equivalence.
