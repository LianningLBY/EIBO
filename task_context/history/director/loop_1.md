---
loop: 1
reason: max_wall_time
updated: '2026-09-14T03:37:11+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **GPU whitelist**: only `111:cuda:0` (1× RTX 5090 D, 32 GB). Server alias `111` (`connect.westb.seetacloud.com`), account `root`, project path `/root/eibo`.
- **Any text written into the paper or any artifact is English.** User-facing chat is **Chinese**. Working/knowledge files are English.
- **Never put server-side paths in user-facing messages** — no `/efs/...`, `/root/...`, `~/.agent-ml-research/...`. Use logical names, or paste content, or `upload_file`.
- **Do not reuse the retired phrasing.** The DPI inequality `TV(vector) >= TV(k-prefix symbol law)` is **NOT a theorem** (78/990 pairs invert). The valid theorem is `TV(vector law) >= TV(POOLED CELL law)`. This is now corrected in the artifact, registry, ROADMAP, framing **and manifest** — do not let it reappear.
- **The `X12` split guard must never be weakened** — no `<=` relaxation, no `--no-check`, no try/except. It fired correctly twice.
- `register_artifact` **appends a suffix, it does not overwrite** — never use it for placement, only for retrieval.

### 2. 🖥️ Infrastructure snapshot
- Server `111`; project `/root/eibo`; HDF5 `~/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5` (10M flows, 3.5 GB).
- Python: **`/root/miniconda3/bin/python3`** (absolute path; `python3` is NOT on PATH — a worker hit `command not found`). `cwd` must be `/root/eibo`.
- GPU: **idle** (2 MB / 0% / no processes) — no live run as of handoff.
- Local artifacts canonical dir: `projects/{proj}/artifacts/_project/data/`. Paper worktree `docs/paper/main.tex`.
- No active PID/tmux. X12's `pid 620376` on its registry entry is a **historical value** (process exited).

### 3. 📊 Current state
Registry: all 11 entries terminal — **X1, X3, X4, X5, E1, E3, E8, E9_Q2v3, E10 DONE/success; X12 DONE/failed; E7 DONE/failed.** No RUNNING/ALLOCATED.

Closed this round: **X1 headline verified 340/986/336** (`c9f840a9`); **X5 α aligned and canonical synced to server** (`31bbee3f`); **C2 correction propagated and independently verified**; **manifest repaired (3 entries, incl. the retracted DPI claim; 0 dangling)**; retired aliases deleted.

**X3's controls: still 0/2 artifacts landed** — worker reported `k=30 smoothing 0.5` wrote, `1.0` did not, re-running only that unit.

In flight (queue): resolve the **two X12 split workers** colliding; X3's last control unit; Pcap reason rewrite.

### 4. 📋 To-do (condition-triggered)
- **X3 control artifacts land** → report the **two questions separately, never merged**: (i) does the fitted SHAPE (exponent/increment ratio) move across smoothing settings ⇒ if yes **downgrade `SUBLINEAR` to `INCONCLUSIVE`**; (ii) does the fixed-population recompute survive independently. **Do not rescue.**
- **X12 split fix lands** → assert both guards still reject (reversed window pair; `CATEGORY`), **sync the local script from the server** (local still `default="CATEGORY"`), then `submit_on_allocated --label-field APP`; report managed metadata only.
- **Pcap artifact** → reason must lead with the **~800 GB model size (attributed to the authors' paper Q&A, NOT our measurement)**, network failures labelled transient; fill the two empty `[GitHub]`/`[Frozen weights]` slots.
- **Any future artifact rename/move/delete** → update its `manifest.yaml` entry **in the same pass**, asserting the path resolves to live bytes.

### 5. 🎯 Strategic context
**Paper**: USENIX Security 2027 C2, deadline 2027-01-26. Three claims: C1 = two-sided ε-bracket computable (**336/990 = 33.9%** upper strict, lower asymptotic); C2 = certifiability falls in M because **a finer alphabet RESOLVES MORE, not less** (`tv` medians 0.5805→0.9673) — the certificate is lost via `eps_hi = tv + radius > 0.5`, and `k_cert` is **HIGHEST at M=1** (17/8/5/4/3); C3 = chain-rule `D_k` grows **SUBLINEAR** vs the linear i.i.d. null — **verdict still provisional pending X3's controls.**

Decision chain: **D038** gate closed 336/990 · **D040** X1's 342/337 root-caused (two opposite-sign convention errors netting +1 while both sides wrong) · **D042** rebuild verified · **D043** split revised: adjacent local-time month buckets share raw-UTC `TIME_FIRST` boundaries, so **train=202406..202411, buffer 202412 UNUSED, test=202501..202505**.

**Pitfalls most likely to catch the next me:**
1. **A correct conclusion carrying a false justification is the most durable error** — it survives review. Three instances this session (X1 DPI, my "conservative bias" claim, my fabricated "I checked the published record"). Check reasoning, not just conclusions.
2. **Verify by reading the FILE, not a derived view.** `read_experiment_plan_with_status` overlays registry data and auto-links by name; it displayed links that were not in the file. Registry/plan/ROADMAP/manifest are **four separate surfaces** — a correction must be checked in all four.
3. **A probe whose value is identical in the state before and after cannot measure the change** (`without adding separation` = 2 both ways: live assertions vs quotations-in-retractions). Search case-insensitively; read the candidate region.
4. **`failed` is unreliable in both directions** — 8+ mislabels, several caused by my own `completion_checks` written against the pre-task state. **Judge work by its artifact.**
5. **Check for an active writer before dispatching.** I caused a double-writer three times. Two X12 split workers are colliding **right now**.
6. **X12 has produced NO detector numbers** across three attempts; both runs died at the split guard pre-CUDA with ≈0 GPU consumed. Do not let any summary imply otherwise.
