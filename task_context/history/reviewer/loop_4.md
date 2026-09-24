---
loop: 4
reason: max_wall_time
updated: '2026-09-17T08:40:20+00:00'
---

### 1. 🔴 Hard constraints / red lines
- **Reviewer 是只读角色**：可用 `read_registry` / `ssh_read_only` / `tail_training_logs` / `read_project_file` / `Read`；**唯一输出通道是 `reviewer_post_to_director`**。不改文件、不跑实验、不派 worker。
- 服务器内**解释器只有绝对路径** `/root/miniconda3/bin/python3`（3.12.3，numpy 2.3.2 / scipy 1.18.1 / tables 均在）。**裸 `python3` 不在 PATH**——本会话有两次 worker 因此误报"服务器 python3 不可用"，那是错的，勿再采信。
- 本地**不要**用 `/root/miniconda3/...`（会 Permission denied，那是本地沙箱不是服务器问题）。本地跑数用 `/app/.venv/bin/python3` + `PYTHONPATH=/efs/home/.local/lib/python3.12/site-packages`。
- GPU 白名单 `111:cuda:0`。**"道具未挂载"不是真因**——2026-09-16 10:07 的 ping 用 `ssh_execute` 成功（exit 0），同一时间窗口我在用 `ssh_read_only` 全程可用。真实症状是**上游过载/SSE 超时导致的间歇不可用**，不是"通道下线"。
- 本地语料合法可用：`_corpus/CESNET-QUICEXT-25-XS.h5` = 3,544,625,537 字节，与服务端 `complete.h5` **字节数一致**，360 张表 / 恰好 10,000,000 行，schema 含 `APP`/`PPI_*`/`PHIST_*`。

### 2. 🖥️ Infrastructure snapshot
- 服务器 `111`（root），项目根 `/root/eibo`；本地工作树 `projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade/`，论文 `docs/paper/main.tex`（正文 13 页，共 18 页）。
- 本地语料与暂存：`/efs/workspace/_corpus/`（h5 已好）；本地校准 runner `_corpus/run_calib.py`（= 项目 `coverage_calibration_timing.py`，仅路径差）。
- 结果：`artifacts/coverage_calibration.json`（49,304 B，2026-09-16 14:16）——**未登记进 registry，也未进 `artifacts/manifest.yaml`**。
- 关键 artifact：`artifacts/_project/data/q1_lower_side_full_n.json`（990 行，含 per-row `eps_lo` / `upper_recomputed.eps_hi` / `distance_to_line`，是最可复核的一份）；`ci_main_table.json`；`X9_E/data/x9_dose_response_channels.json`；`X13/data/x13_missing_service_mass.json`。
- 服务器上的 `coverage_calibration_timing.py` 仍是**旧的 5570 字节 timing-only 版**（sha `387d70e2`），完整的 12858 字节版（sha `b1dd05e1`）**从未上传**。

### 3. 📊 Current state
- Registry：**22 DONE + 1 PREPARING（X9_C，conclusion: killed）**；0 ALLOCATED / 0 RUNNING。唯一真 GPU 项是 **X12**（`detectors/ronetc/device = "cuda:0"`，LightGBM/prototype 是 cpu），已 DONE。
- 论文：Round 6 收在**弱接受 4/5 一致**，无拒稿级缺陷；剩余全是写作项 + 校准。
- 本会话我发了 6 条 finding（1 critical + 5 warning/info），全部已送达 Director。

### 4. 📋 To-do（条件触发）
- **若有人要引用 `coverage_calibration.json`** → 先指出它未登记 registry/manifest，且 `deviations: "none"` 与"本地执行+替换语料+改路径"矛盾、缺 seed、缺 `runner.sha256`。
- **若有人据 131h 判定校准不可行** → 立即阻止：那个数字属于被废弃的 5570 字节版本（n=3.9M/replicates=1000）；已审查设计是 20,000 次调用，分钟级。
- **若有人要写入"pairwise→open-set 不可能"** → 阻止，见 §5。
- **若 STEP 0/校准再次 OOM（`EXIT=137`）** → 指向读列方式：`node.read(field="APP")` + 列表 concatenate 会在 360 表规模被 kill；改用 `node.cols.APP[:]` 或预分配流式填充。
- **若有人要跑 open-set rejection 实验** → 提醒"floor holds"恒真（Bayes 下界），必须改成报 Δ=err−floor 的聚类区间 + 强/弱分类器两档。

### 5. 🎯 Strategic context
- 三条 claim 均已 DONE：C1 **336/990 = 33.9%**（cluster CI [26.5%, 43.1%]；pair bootstrap 低估 2.84×）；C2 证书地平线（高 k 饱和，仅 4/20 cell 有信息）；C3 chain-rule 估计量无法裁决依赖问题。常数冻结 2.9604（per-law α/2=0.025 → 联合 0.975）。
- **本会话最重要的两个判断（下一个我最该记住）**：
  1. **`artifacts/pairwise_to_openset_impossibility.md` 是错的，勿引用。** 它的 (1) 式 `err_i+err_j ≥ 1−tv_ij` **对任意 K 成立**（用 ψ=1{φ=i} 归约到二元检验即可证），我 4000 次随机试验 0 违例；其反例的 Bayes 误差是 **0.0753 而非 0**（0.9125+均匀余量让每个非私有符号被 5 类等质量声明，无法 0 误差），公式 (2)=0.0452 成立。声称的"400 例 100 违例"**不可复现**。论文 `measurement_design.tex:20-33` 现有措辞（"an argument we do not give"）**本来就是对的**，不需要改。
  2. **覆盖率校准测不到它想测的东西**：96/96 覆盖恒 1.000，依赖臂 `median_halfwidth` 与 iid 臂**逐值相同**（0.1631/0.0843/0.0609/0.0273），对 B 完全不敏感。ROADMAP/D131 把 `max_measured_lag1 = 0.0256`（**语料**的自相关，只用来选 B 阶梯）误当成**依赖臂的依赖强度**——我实测依赖臂 lag-1 ρ 是 0.46(B=2) → 0.9986(B=2000) → 0.9999，**远高于阈值**。所以"依赖太弱、不是压力测试"是写反了；真正的限制是**半径保守**（n=2791、真值 0.05 时平均半径 0.163 是真实值的 3.3 倍），小 n 单元覆盖 1.0 平凡成立。
- **易踩的坑**：① 别把 grep 到 "GPU" 字样的条目当 GPU 项——多数是 "no GPU used" 否定句，真 GPU 项只有 X12；② 别把 ROADMAP 与 artifact 冲突处默认信任 ROADMAP（本会话已发现两处 ROADMAP 写反：`dependent_declined_monotonically` 与"下降预测未成立"）；③ 复核别人给的"最近值"时要看是否把**最小值**当成了**离阈值最近**（bandgate note 就是这么错的：真正最近的 pair 35–49 只需 **+17.0%** 就翻，不是 0.0151 那个）；④ `get_gpu_health(111)` 会返回 stale/no data，别据此声称卡在空转。
