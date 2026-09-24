---
loop: 6
reason: max_wall_time
updated: '2026-09-18T19:20:08+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only**: only `read_registry` / `read_project_file` / `ssh_read_only` / `tail_training_logs` / `read_roadmap` / `Bash` (local read) / `Read`. **Only output channel is `reviewer_post_to_director`.** `save_project_file` is NOT in my toolset — memory persists via system distillation at reset, do not attempt it.
- GPU whitelist `111:cuda:0`; card is idle and that is **correct** — no GPU-eligible work exists (X12 DONE, open-set line closed). Do not invent GPU work.
- **Never quote server-side paths in user-facing text** (logical names only). Paper + submission artifacts are English; user-facing replies Chinese.
- Local Python: `/app/.venv/bin/python3` with `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages` (has scipy/numpy). Server interpreter is `/root/miniconda3/bin/python3`, absolute path, not on PATH.
- **`main.pdf` is newer than `main.tex` at a fixed instant only** — the tree has moved repeatedly mid-audit. Always re-read at the moment of writing the finding; quote sha + mtime. I filed two stale-finding errors this session by not doing so.

### 2. 🖥️ Infrastructure snapshot
- Project root: `/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade/`; paper tree `docs/paper/` (entry `main.tex`).
- **The paper compiles `docs/paper/figures/paper/`, NOT repo-root `figures/paper/`** — two copies that once diverged for two rounds. Regenerate → sync BOTH → scan the COMPILED one. Currently 5/5 byte-identical.
- Key artifacts: `artifacts/_project/data/q1_lower_side_full_n.json` (990-pair M=1/k=5 ledger; carries BOTH `eps_lo` and `capped_eps_lo`), `q1_absolute_counts.json` (k=5, all 5 M-rungs, 4950 rows), `q1_absolute_counts_k{10,15,30}.json`, `eth_full_mk_grid.json` (20-cell grid, sha `8f434930…`).
- Corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5`, sha `6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab`. Stream the hash; never load 3.5 GB.
- **Alphabet is `m=(2M)^k`, not 32.** Recomputing a rung needs BOTH a per-M row filter AND `m` rebuilt from M.
- No RUNNING/ALLOCATED experiments, no cron, no workers. `X9_C` is a stale `PREPARING` — deliberately documented, exclude when filtering on status.

### 3. 📊 Current state
- Registry: all DONE except `X9_C` (PREPARING, withdrawn design, documented). Decisions through **D166**.
- **D166 = the big one, verified by me independently**: an m-free Hoeffding upper bound (`A*={x:P(x)>Q(x)}` is population-determined → 2 events, not `2^m`, so no `√m`). I reproduced **all 20 (M,k) cells with zero mismatches** (340/363 at k=5/M=1; 47/127; 28/98; 0/18; 0/0). It invalidates C2's stated mechanism (the cause is plug-in saturation, not the alphabet price) and it is **confined to M=1** — 18 pairs at k=15/M=1, zero from M=8 on. D166 is **already integrated** into `results.tex:167–212`.
- Current build: sha `9cbada35d9e0689727c614923d852d86f89e21ab22bc102b1b4b0bd104c12073`, **22 pp**, body ends **p.13**, Ethics p.14, 0 fatal/undefined/overfull, 0 `??`, 64/64 citations.
- **Four of five dispatched patches fixed** (LP feasibility `main.tex:455-459`; the three radius-attribution sites; the "not local" claim removed).
- **Awaiting user decisions**: (1) revise vs submit-as-is; (2) stand up the `anonymous.4open.science` repo (ID `SEC27`) for CFP compliance.

### 4. 📋 To-do (condition-triggered)
- **If asked to re-audit after any edit** → re-read the file at that moment; do not answer from this handoff. Quote sha + mtime.
- **If the Open Science paragraph still says "scope of effort"** → report non-compliant. CFP requires anonymous links (double-blind); recognized omission grounds are licensing / adversarial risk / harm to subjects / NDA only. Fix is the user's repo action, not prose.
- **If anyone cites "0.08617 / 0.02960 / 0.04750"** → wrong. At n=2791 I compute **0.08156 / 0.02802 / 0.05354**; no convention reproduces the cited triple. Bound itself is verified; this is a bad figure in the audit trail.
- **If a figure is renumbered or relocated** → run the three-layer binding check (file→caption→label; label→number from `.aux`; citing prose matches the figure). Neither `??`-counting nor a label/cite grep catches a mislabel.
- **If "the horizon is dissolved" appears** → wrong; it is an M=1 phenomenon only.
- **If asked about `[31]` Liu et al.** → my complaint was STALE; both citing sites now correctly say it admits correlated, non-stationary observations.

### 5. 🎯 Strategic context
- **Contribution type is measurement/rigour, NOT a mechanism — settled deliberately since the MVP.** Four "raise it to clear-accept" routes were audited and none is open. Do not manufacture method novelty.
- Trajectory: R10 4.7 → R11 4.5 → **R12 5/5 unanimous, panel released for submission**. **D166 landed after that release** — the 5/5 was earned on pre-D166 bytes, which is why revise-then-re-review (not silent patch) is the standard I applied.
- **The dominant defect class of this whole project is "the check verified the neighbouring object."** Operational rule: state the predicate and the statistic in the same sentence as the threshold, and confirm the threshold's definition names the same object.
- **Two probes probed the two admitted limitations and both came back inherent-to-method-class**: lower side (b) captures only ~5–17% of true TV at the real deviation structure; upper side, the m-free route's advantage collapses past M=1. Both negatives are registered and recorded.
- **Retracted, must not be revived**: the pairwise→open-set impossibility claim (D138); the bias-driven coverage-breach mechanism (D155); the Bonferroni 394.27 figure; the memo's `0.1330` (unreproducible; agreed value **0.1723**, cost **+0.052** not +0.0132); my own "horizon extends to k=15" phrasing (overstated — M=1 only).
- **My own two errors this round were both stale-finding errors** — repeating the `[31]` complaint without re-reading the render, and overstating the D166 extension. The next "you" is most likely to err the same way: **the tree moves under you; re-read before asserting.**
