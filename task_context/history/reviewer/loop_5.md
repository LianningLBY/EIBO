---
loop: 5
reason: max_wall_time
updated: '2026-09-18T02:51:02+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer is read-only**: `read_registry` / `ssh_read_only` / `tail_training_logs` / `read_project_file` / `Read`. Only output channel is `reviewer_post_to_director`. No file writes, no experiments, no workers. (`save_project_file` is NOT in my toolset — memory is auto-distilled at reset; do not attempt it.)
- Server interpreter is absolute-path `/root/miniconda3/bin/python3`. Local work uses `/app/.venv/bin/python3` + `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages`. Bare `python3` is not on PATH.
- GPU whitelist `111:cuda:0`; the card is idle and that is correct (all remaining work is CPU authorship).
- **Never quote server-side paths in user-facing text** — logical names only.
- Paper and all submission artifacts are English; user-facing replies Chinese.

### 2. 🖥️ Infrastructure snapshot
- Project root `/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade/`; paper tree `docs/paper/` (entry `main.tex`).
- **The paper compiles `docs/paper/figures/paper/`, NOT repo-root `figures/paper/`** — two independent copies that had silently diverged for two rounds. Regenerate → sync BOTH → scan the COMPILED one. This is now a mandatory rule with a positive-controlled build gate.
- Local corpus `/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5`, 3,544,625,537 bytes, sha `6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab` (matches server). Hash by streaming `sha256sum` (~10s); never load the whole file (per-process cap ~7.5 GB; the naive all-nodes read dies `EXIT=137` around 240/360 tables — use per-node short-lived processes).
- No RUNNING/ALLOCATED experiments, no cron, no workers.

### 3. 📊 Current state
- **Round 9 = accept 4.5/5, unanimous, the first round in nine with no critical.** Paper is at accept, in shepherding.
- **Current build I last verified: `main.pdf` sha256 `80a8ba1bdac8475e7ec18a7579bbb141269286198caf02134dbf76bfe121da15`**, 21 pages, body ends **p.13** (limit 13), Ethics p.14, Open Science p.15, Appendix p.16+, Table 6 p.19, References p.20+. Always quote the PDF sha in review exchanges — three items were disputed across builds and the hash is what resolves them.
- Verified PASS this session: W1(a)(b)(c) direction words, W2 deletion, W4 Table 6 marking, both appendix-provenance items (all four 64-hex digests present exactly once and matching the manifest), and the fig4 relocation to A.4 (refs resolve, no orphan, width restored to 0.62).
- Registry: 22 DONE + X9_C PREPARING/conclusion=killed. C1/C2/C3 all DONE.

### 4. 📋 To-do (condition-triggered)
- **If anyone cites the open-set floor**: only the UNIFORM form is certified — 0.18577 (M=46) / 0.19422 (M=45). LP 0.36307 / mixture 0.36347 / exclude-U 0.37155 are REFERENCES ONLY, uncertified, and must never be shipped as headline.
- **If a floor-vs-error ratio is quoted**: pair floor and delta from the SAME M. Paper frames M=K+1 → floor 0.186 / delta 0.55. The 0.5424 delta is the M=45 margin; mixing them is off by 0.0084.
- **If anyone proposes another figure shrink**: refuse — fig4 is at 0.62 after being shrunk three times. Move a float to the appendix instead; that is the lever that actually recovered the page.
- **If a "figures regenerated" claim arrives**: require the escape scan to be positive-controlled on a known-leaky file first, and require it to run on BOTH trees including the compiled one.
- **If asked whether the calibration "closes" the i.i.d. clause**: it does for the literal ask, but the licensed claim is narrow — one generator, one concentration, one TV, B≤64, and it does NOT test the corpus's own ρ≈0.46 at B=2.

### 5. 🎯 Strategic context
- **Contribution type is measurement/rigour, NOT a mechanism — and that was settled deliberately.** I audited the four "raise it to clear-accept" routes and found none open: scale/breadth is padding, the post-selection gap is closed in the literature (Michel et al., already implemented in `tv_lower_bound`), the floor gap is closed within the family, and re-framing cannot cross the line. Do not manufacture method novelty; failure mode this session was exactly that.
- **Trajectory**: R6 4/4/4.5 weak accept → R7 3/3/4 borderline (my option-B recommendation caused it) → R8 4/4/3.5 → R9 accept 4.5/5.
- **The dominant defect class of this whole project is "the check verified the neighbouring object."** Five instances this session: floor/blend confusion, cap-vs-widening on the Bonferroni recompute, "exceeds 1.0" vs "reaches 1.0" (29 of 990 pairs sit exactly at the cap, not zero), point estimate vs CP lower endpoint, and a figure scan aimed at the compiled paper instead of the figure's own text layer. **Operational rule that catches all of them: state the predicate and the statistic in the same sentence as the threshold, and confirm the threshold's definition names the same object.** ("coverage 0.9825 ≥ 0.975" is ill-formed; "CP lower endpoint 0.9643 ≥ 0.975" is well-formed.)
- **Text-layer greps must be whitespace-normalized.** Two of my own false negatives this session came from line-wrapping splitting a phrase. Normalize before reporting an absence.
- **Cross-service TV is only meaningful on the certificate's own channel AND with the ledger's eligibility rule.** `PPI_LEN >= 5` is a ~2x effect — bigger than the window choice; the unfiltered object measures a channel the certificate never defines.
- Retracted and must not be revived: the pairwise→open-set impossibility claim (D138), the bias-driven coverage-breach mechanism (D155), and the Bonferroni 394.27 figure (direction inverted; the true correction lowers S to 374.39).
