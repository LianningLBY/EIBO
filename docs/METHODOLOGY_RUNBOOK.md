# EIBO 学校服务器实验启动说明

This first stage uses tracked k=5 count tables, so no raw corpus or GPU is needed.
It prepares strong classical baselines before work on representation-loss control.
It does not change the manuscript or upgrade its sampling assumptions.

The synthetic stage below checks coverage against exact known truth and isolates
within-service and cross-service dependence. It also runs without raw traffic or
a GPU.

## 当前环境

项目目录为 `/data/xjw/EIBO`，继续使用当前已激活的 `traffic-ncde` 环境。先检查解释器和已有依赖：

```bash
which python
python --version
python -c "import numpy, scipy; print('numpy', numpy.__version__, 'scipy', scipy.__version__)"
```

脚本使用兼容 Python 3.8 的语法，依赖范围为 NumPy 1.22 至 1.x、SciPy 1.8 至 1.x。目录为空时克隆代码，再安装缺少的依赖并运行：

```bash
git clone --branch codex/methodology-risk-certificates git@github.com:LianningLBY/EIBO.git /data/xjw/EIBO
cd /data/xjw/EIBO
python -m pip install -r requirements-methodology.txt
python -m unittest discover -s tests -p test_riskcert.py -v
python scripts/methodology_baselines.py --out artifacts/methodology/baselines_20261012_01.json
```

已有仓库时，先执行 `git fetch origin`，再执行 `git switch codex/methodology-risk-certificates` 和 `git pull --ff-only`。

每次运行使用新的输出文件名，脚本会拒绝覆盖已有结果。已有依赖满足要求时可以跳过安装。
If the server cannot access GitHub, transfer this checkout to
the project folder first; all subsequent commands run offline after dependencies
have been installed.

## What is computed

- A direct multiclass risk floor using per-service TV deviation radii and a union
  bound. The radii are obtained by calling `eibo.statcore.tv_upper_bound`.
- A second direct floor from concavity and bounded differences. This requires
  mutual independence across all services, a stronger assumption, and is reported
  separately.
- A weighted Hunter spanning-tree floor from simultaneously valid pairwise TV
  upper bounds, including a sample-count and TV reconciliation with the ledger.
- Original uniform and LP values as references under their original prior.

Known services have total prior `1 - unknown_prior`. Unknown error is discarded;
its law is neither estimated nor assumed close to the known laws. The default is
the paper's uniform prior on 45 known services plus one unknown class. The optional
`--unknown-prior` changes that mass while keeping known classes uniform.

## Interpretation and next stage

All floors concern the declared quantized observable. They cannot be compared as
certificates against detectors using additional packet-size or timing features.
Aggregate tables contain no timestamps, so this stage cannot verify temporal
splits, clustering, or deployment shift. A report is exploratory until reviewed
and registered in the project evidence chain.

The next raw-data stage should use explicit time periods and buffer intervals,
fit a frequency classifier on training counts, and evaluate it on disjoint test
counts. Representation selection must use a separate pilot set. Any certificate
for a finer observable must account for representation loss; merely certifying a
coarse representation does not certify the original observable.

## 合成分布覆盖率与相关采样压力测试

服务器已经克隆该分支并安装依赖时，在当前 `traffic-ncde` 环境完整执行：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= \
        -c core.askPass= \
        -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_synthetic.py \
    --trials 2000 \
    --samples-per-service 128 512 2048 \
    --block-sizes 8 32 128 \
    --markov-rhos 0.9 0.99 \
    --alpha 0.05 --mc-alpha 0.05 --seed 20261012 \
    --include-tree \
    --out-dir "artifacts/methodology/synthetic_$(date +%Y%m%d_%H%M%S)"
```

这次 Git 操作临时绕过代理，保留服务器已有凭据配置。需要认证时，Username 输入有仓库访问权限的 GitHub 用户名，Password 输入该账号的 Personal Access Token。依赖保持前一步已安装的版本。

上述默认网格有 **168 种采样配置**，每种配置独立重复 2,000 次。初版输出 597 行方法结果；v2 加入 Markov 修正及可观测连续段对照后输出 **711 行**。脚本按批次运行并逐配置输出进度，所有结果放在新目录中。仅跨服务相关模式适用于 `private_*` 分布；生成树默认只在 K ≤ 8 的小类别数场景运行，以控制计算量。

输出包括：

- `report.md`：概览及失败率显著超过预算的场景。
- `summary.csv` / `summary.json`：所有方法的失败次数、失败率置信区间、下界与真实风险的差距、零下界比例和假设标签。
- `laws.json`：固定的真实类别分布、先验和真实风险。
- `progress.jsonl`：每个已完成配置的结果及独立单位或 Markov 方差诊断。
- `run.json`：运行状态、参数、随机种子规则、版本、代码及输出文件 SHA256。中断后状态不会标为 complete；重新运行使用新目录。

快速检查可以用 `--trials 20 --samples-per-service 128`。完整覆盖率结论应使用正式重复次数；小规模检查只能验证程序可运行。已有输出目录会被拒绝覆盖。

### 固定目标与采样机制

真实目标为已知类别的 Bayes 风险贡献：

`F = sum_i pi_i - sum_x max_i pi_i p_i(x)`。

所有分布、先验、字母表和方法均在采样前固定。已知先验总质量为 K/(K+1)，丢弃未知类自身的错误贡献。9 个场景涵盖相同分布、近似相同分布、公共符号与类别私有符号、强区分分布、Zipf 稀有尾部，以及不均衡的先验与样本量。包括 K=45、m=32/1024 的场景；`private_45_64` 是用来隔离共同冲击的额外合成场景。

1. `iid`：所有服务内外样本独立。
2. `block`：每个独立块抽一个符号，并重复 b 次。原始流数用于 naive 方法；oracle 对照使用已知独立块数。等长块保证两者的经验分布相同，修正无需估计有效样本量。
3. `markov`：从真实边际分布开始的平稳链，转移核 `P = rho I + (1-rho) 1 p^T`。每个服务单独生成，避免混入初始分布偏移。v2 保留隐藏再生段长度来构造条件证书，并加入只使用可观测连续相同符号段的保守对照；后者的保证来自对隐藏段预算的逐路径支配。精确方差膨胀因子仍仅供诊断，不把 `n/tau` 代入 iid 公式。
4. `cross_service`：各服务在同一位置共享“公共符号/私有符号”的 Bernoulli 冲击。每个服务内仍为 iid，只有跨服务独立性被破坏。classwise 和 pair/tree 的边际条件仍成立；原始 joint 的条件不成立。额外对照按已知独立的整列冲击计算改变上界。

oracle 修正使用模拟器已知的独立单位；不能从这些结果推断真实流量中块长度或独立性已知。`grouped_joint_risk_bound` 的证明依据是经验 F 的凹性（`E[Fhat] <= F`）以及独立单位的有界差分；调用方必须另行证明经验分布无偏、单位相互独立和每个改变上界。

### 判读规则

失败事件是 `lower_floor > F + 1e-12`，名义失败预算 alpha=0.05。每行给出双侧 95% Clopper–Pearson 区间；最终判定使用对所有方法/配置 Bonferroni 修正的同时区间，整体 Monte Carlo 错判预算为 0.05。

- 同时区间的下端点 > alpha：该固定场景的失败率显著超预算。
- 同时区间的上端点 ≤ alpha：该固定场景的失败率低于预算；不代表证明所有分布上的覆盖率。
- 其余情况：当前重复次数不足以判断。

`assumptions_met` 来自模拟器定义。假设被破坏的压力测试出现超预算属于诊断结果，程序正常退出；满足假设的方法出现超预算则退出码为 2，应检查实现及理论依据。零下界比例用于区分保守但无信息的覆盖与有用的证书。生成树测试使用 `statcore` 的有限字母表 pair upper，不能将其数值与先前读取 m-free ledger 的生成树结果直接等同。

这些输出在审查和登记前均属于探索性结果，不直接写入论文。

## 第二轮：Markov 修正与模型不匹配

第二轮默认参数下有 **117 种配置、489 行方法结果**。它保留 iid 和跨服务相关基线，增加 Markov 再生修正、可观测连续段对照、时间相关与跨服务相关叠加的场景，以及段内会变化的隐藏块负对照。第一轮重复常数块已验证，此轮不再选择 `block` 模式。

当前环境依赖已齐，完整执行：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= -c core.askPass= -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_synthetic.py \
    --trials 2000 \
    --samples-per-service 128 512 2048 \
    --modes iid markov cross_service cross_markov hidden_blocks \
    --block-sizes 8 32 128 --markov-rhos 0.9 0.99 \
    --alpha 0.05 --mc-alpha 0.05 --seed 20261012 \
    --include-tree \
    --out-dir "artifacts/methodology/dependence_v2_$(date +%Y%m%d_%H%M%S)"
```

这段更新命令保留服务器已有凭据配置。没有缓存凭据时仍需 GitHub 用户名与 Token。

新增方法和场景的适用条件、证明及真实流量接入条件详见 [dependence protocol](METHODOLOGY_DEPENDENCE_PROTOCOL.md)。重点查看覆盖率、`mean_lower_floor`、`zero_floor_rate` 和 `mean_radius`，同时查看 `assumptions_met`。`progress.jsonl` 保存第一条重复实验的段长度与标签，便于重建采样计数和核对预算。

## 第三轮：真实数据准备审计

已在学校服务器确认 XS 文件的位置和结构：

`/data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5`

字段检查显示 360 张 `/flows/DYYYYMMDD` 表、10,000,000 条记录，包含 `TIME_FIRST`、`TIME_LAST`、`ID`、多个 QUIC CID 字段及 `APP`、`PPI`、`PPI_LEN`。官方说明中，`ID` 是每个数据集内唯一的流记录编号，不能直接作为多条流的会话分组键。源 IP、源端口没有提供；目标端点键是服务端聚类候选。CID 键需先检查空值、重复、跨类别和跨日期复用。

另一个关键限制是流开始时间被截到整点小时，结束时间也相应调整。细于一小时的顺序不能从这些绝对时间字段恢复，文件行序也不构成小时内真实时间顺序。脚本逐记录审计小时对齐比例，以核对当前 H5 版本；默认使用 1 小时、6 小时和 24 小时分组。

Sources: [official release](https://zenodo.org/records/17249078), [DataZoo field definitions](https://cesnet.github.io/cesnet-datazoo/features/).

当前 `traffic-ncde` 环境已成功使用 PyTables 读取该文件，可以直接执行以下完整命令；无需重装依赖：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= -c core.askPass= -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_real_prepare.py \
    --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
    --backend tables --time-unit seconds --k 5 \
    --gap-seconds 86400 --rounding-seconds 3600 \
    --block-seconds 3600 21600 86400 \
    --identifier-sample 50000 --min-pilot-flows 2000 \
    --expected-sha256 6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab \
    --out-dir "artifacts/methodology/real_prepare_$(date +%Y%m%d_%H%M%S)"
```

SHA256 来自原实验脚本登记的 XS 字节记录。如果不匹配，程序会在正式扫描前停止，需核对文件版本。脚本按块读取，不修改 H5，也不导出原始 IP、CID、哈希键或逐流记录。另一台环境缺少读库时使用 `requirements-realdata.txt`；当前服务器不需要重复安装。

输出包括 `report.md`、`audit.json`、`tables.json`、`experiment_plan.json`、逐日/分期类别计数 CSV、`time_unit_diagnostics.json` 和含代码/输入/输出 SHA256 的 `run.json`。`--max-rows` 只用于读取烟测；未完整扫描时计划状态为 `needs_review`。

准备阶段固定按日历跨度 50%/25%/25% 划分 pilot、certificate、evaluation，在后两段开头留出 24 小时间隔。每条流的整个区间都必须落在所属窗口内。由于绝对时间的小时截断会把结束时间一起前移，窗口末端另留 1 小时包络。短前缀、无效时间、间隔和越界流的排除都会改变目标总体，报告明确记录这点。

类别仅根据 pilot 的可用整流数 ≥ 2,000 选择。证书期和评估期缺失的 pilot 类别会被报告，而不会被悄悄移除。ID/CID 审计采用在所有有效 k≥5 流上均匀抽取的 50,000 条样本；没有观察到重复不证明全文件唯一性，更不证明会话或时间块相互独立。

时间块统一覆盖所有类别，敏感性预算按 `sum_b (sum_i pi_i*n_ib/n_i)^2` 计算，调用 `eibo.riskcert` 的公式实现。独立性和条件无偏性均标为未证实，此阶段只报告假设成立时的半径诊断，不给出真实流量风险下界或覆盖率。完成准备审计后，再接固定观测计数、pilot 训练的频数分类器和跨时段评估；真实覆盖率不能像合成分布一样直接用已知 Bayes 风险核验。

## 第四轮：真实数据计数与跨时段评估

2026-10-12 的 ToDesk 报告已确认完整扫描、44 个 pilot 类别，以及所有开始时间对齐整点。CID 样本不支持可靠的多流会话划分：OCCID 有 72.83% 空值或零值，仅 3 个重复键且存在跨 APP、跨日期复用；组合键未观察到重复。详细判读见 [real audit memo](METHODOLOGY_REAL_AUDIT_20261012.md)。当前继续使用时间划分，不把 CID 当作独立单位。

下面命令直接复用已经完成的审计目录，不必重新跑准备审计，也不必安装依赖：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= -c core.askPass= -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_real_experiment.py \
    --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
    --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
    --backend tables --chunk-rows 20000 \
    --block-seconds 3600 21600 86400 \
    --out-dir "artifacts/methodology/real_experiment_$(date +%Y%m%d_%H%M%S)"
```

程序先校验准备文件的清单 SHA256、重新校验 H5 的 SHA256 和表结构，再完整扫描。时间窗口、k、类别、先验、alpha 和两种表示均从准备计划复制，不能根据后期结果临时移除类别或改变表示。新增输出目录必须不存在。若前 k 个包有非法方向或非正尺寸，程序会停止，不会静默改变审计所定义的总体。

输出包括 `report.md`、`summary.json`、`symbol_counts.json`、`time_unit_diagnostics.json`、`per_service_metrics.csv`、`plan_snapshot.json` 和 `run.json`。逐 APP 的三个时期计数必须与准备 CSV 完全一致；M=2 计数向 M=1 的投影及时间单位计数也必须一致。没有逐流记录、原始 CID/IP 或哈希键输出。

重点查看：

- pilot 分类器在 certificate/evaluation 的已知类加权错误、未见符号质量，以及 certificate 训练的近期模型在 evaluation 的错误。未知类自身的错误未测量，先验由计划固定，不是流量实际比例。
- 每个类别的 certificate→evaluation 经验 TV 与 M=1/M=2 的经验 Bayes 风险差。二者都是样本统计，不能当作总体漂移界或表示损失证书。
- iid 条件下界与 1/6/24 小时的条件敏感性下界。所有依赖假设均未验证；不从这些结果推断真实覆盖率，也不将证书期下界直接用于评估期。
- 时间块合并前后的半径、单位数与连接边数。任何可用整流的时间包络跨块时，相关相邻块会合并；跨类别共用一个单位，先求和再平方。该操作修复同一流被拆分的问题，不能证明不同流、不同单位相互独立。

本阶段明确使用 `statcore` 的固定 `log` 网格。`log M=2` 的尺寸边界与旧实验的 1200 字节切分不同，不能直接作为旧表示的复现实验。只比较当前两种明确的固定表示，不选择多个方法/块宽中最大的下界作为同时有效证书。

## 第五轮：逐类别、逐月漂移分解

上一轮服务器实验已经完成，目录为 `artifacts/methodology/real_experiment_20261012_205629`。本轮仍使用原计划的 44 个 APP、固定先验、k=5、两个 log 表示和三个时间窗口。原输出没有逐月计数，因此需要再扫描一次 H5；扫描后所有整段符号计数和指标必须与上一轮完全核对。

当前 `traffic-ncde` 环境可以直接运行，不需要新增依赖或重新跑前三轮：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= -c core.askPass= -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_real_monthly.py \
    --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
    --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
    --experiment-dir artifacts/methodology/real_experiment_20261012_205629 \
    --backend tables --chunk-rows 20000 \
    --small-n 200 --top 10 \
    --out-dir "artifacts/methodology/real_monthly_$(date +%Y%m%d_%H%M%S)"
```

程序重新核验 H5 的 SHA256，以及准备审计和上一轮实验的文件清单哈希。按 UTC 开始时间把已经满足原时间窗口、整流包络、前缀长度条件的流分配到月份。**不额外按月末排除跨月流**，确保月计数之和仍等于上一轮整段计数。若同一个月被 pilot/certificate/evaluation 边界分开，会保留为不同片段，不跨期合并。缺表日期、无样本月份和缺失 APP 都会显式报告。

输出包括：

- `report.md`：月度概览、错误分解、错误增加最多的类别、表示收益贡献下降的类别、缺样情况。
- `monthly_summary.csv`：每月的样本量、最小类别样本量、缺失/小样本 APP、经验 F、分类错误、pilot 与相邻片段的经验 TV，以及 M=1/M=2 的经验风险差。
- `class_metrics.csv`：每个 APP 在整段和月份片段中的样本量、固定 pilot 模型错误、评估期近期模型错误、经验最优错误，以及全局/类别专属未见符号质量。
- `class_drift_decomposition.csv`：逐 APP 的经验 TV、固定 pilot 模型错误变化，以及 `错误变化 = 经验 F 变化 + 经验差距变化` 的带符号贡献。包含三组整段比较、pilot/证书期参照和相邻月份片段比较。
- `representation_contributions.csv`：每类对 M=1/M=2 经验风险差的带符号贡献、相对 pilot 的变化，以及固定模型分类改善。
- `summary.json`、`rankings.json`：完整指标、缺失值的可辨识范围及分类别排名。
- `monthly_symbol_counts.json`、`plan_snapshot.json`、`run.json`：可复查的聚合月计数、固定计划和输入/代码/输出 SHA256。

完成后终端会直接显示 12 个月的 M=2 概览、certificate→evaluation 分解和错误增加最多的 APP，方便在 ToDesk 中查看。表内错误、F、TV 以原固定先验计算；终端 `delta_*_pp` 为加权百分点，`error/F/TV/loss` 为 0 至 1 尺度的值。

`--small-n 200` **只标记样本量，不筛选类别**。月份缺失任何固定类别时，不计算完整类别混合的经验 F/经验最优表示收益，也不对剩余类别重新归一化先验。固定分类器的已有类别错误贡献仍保留，并报告未观测类别引起的数值范围；这种范围不是置信区间，不包含采样误差。小样本行保留在排名中并带标记。

同一类别的表示贡献可以为负，因为细表示会改变经验最优分类器在不同类别之间的错误分配；完整类别集合的贡献之和必须非负。pilot 月份的模型误差复用了训练数据，属于重代入统计；证书期训练的近期模型仅在后续 evaluation 月份评估。分析保留正、负错误变化贡献以显示抵消，并区分全局新符号与类别内新符号。所有差异均为描述性结果，不推断显著性、真实 Bayes 风险、时间块独立性或新的风险证书。

## 第六轮：APP=2 符号、混淆归因与滚动训练

逐月分解已经在服务器完成，目录为 `artifacts/methodology/real_monthly_20261012_213718`。本轮直接使用该目录中的聚合计数，**无需重新扫描原始 H5，不新增依赖**。全部 44 类、固定先验、k=5、原 log M=1/M=2 表示和原目标总体均保持不变。

服务器当前 `traffic-ncde` 环境完整执行：

```bash
cd /data/xjw/EIBO && \
git switch codex/methodology-risk-certificates && \
env -u http_proxy -u https_proxy -u all_proxy \
    -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u GIT_ASKPASS -u SSH_ASKPASS \
    GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
    git -c http.proxy= -c core.askPass= -c http.extraHeader= \
        pull --ff-only origin codex/methodology-risk-certificates && \
python -m unittest discover -s tests -p '*riskcert*.py' -v && \
python -u scripts/methodology_real_rolling.py \
    --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
    --app 2 --reference-months 2024-12 2025-01 \
    --matched-repeats 100 --seed 20261012 \
    --small-n 200 --top 10 \
    --out-dir "artifacts/methodology/real_rolling_$(date +%Y%m%d_%H%M%S)"
```

先验证缓存文件清单 SHA256、编码实现来源、时间片段、全部类别顺序、先验、M=2→M=1 的投影和原月度指标。输出目录必须不存在。原始 H5 不参与本轮读取；完整测试会使用临时的小型合成 H5 夹具验证早期流水线。

### 符号与混淆归因

以 2024-12 和 2025-01 合并计数为描述性参照，分析之后的 2025-02 至 05。这个参照来自前一轮观察，结果属于事后诊断。APP=2 的每个 log M=2 符号会记录概率变化、对固定 pilot 模型错误变化的加权贡献、参照期/目标期的经验最优标签、最强竞争类别、焦点类别分数与已知类别条件后验，以及对应粗符号的经验最优标签。全部类别都参与竞争。

输出区分两个恒等分解：

- 固定 pilot 错误变化：保持分类规则不变，逐符号统计 APP=2 的概率质量转移，贡献之和必须与类别错误变化一致。
- 焦点类别经验最优错误变化：保持参照期规则计算概率质量变化项，再计算目标期经验规则改变引起的错误重新分配项。二者之和必须与经验最优错误变化一致。这是样本代数分解，不是因果效应。

同时逐符号计算 APP=2 对 M=1/M=2 经验风险差的带符号贡献变化，以及前五个包位置的方向/尺寸边际 TV。位置边际 TV 不是联合前缀 TV 的可加贡献。符号解码由 `statcore` 的固定网格和 ID 编码核对；C/S 对应 PPI 原始 +1/-1 方向，1–38/39+ 对应当前 log M=2 尺寸桶，不能恢复桶内实际尺寸。

### 过去月份的监督滚动模型

对 certificate/evaluation 六个月分别比较固定 pilot、最近 1 个日历月、最近 3 个日历月的频数分类器。每个目标月只允许使用之前月份的训练记录；当前月不会被纳入训练。窗口严格按日历取值，缺失/空月份不会被更早月份替换。缺失训练类别时模型标为不可用，不缩减类别集合或重新归一化先验。该对照假设过去月份标签已可用。

除使用窗口内全部训练记录外，默认增加 100 次匹配训练量的对照：每个类别的预算取三个模型训练量的最小值，从各自已有计数中不放回抽样。先抽 M=2，再投影为 M=1，保证两种表示使用相同训练子集。每个类别预算在模型之间相同，不要求不同类别之间样本量相同。固定随机种子及月/模型/重复编号规则确保重现。`--matched-repeats 0` 可跳过这项。

随机重复的均值、标准差和分位数只反映给定已有数据时的训练子集敏感性，**不是总体置信区间，不证明样本独立**。整段错误先按类别汇总各月错误计数，再除以各类目标样本量并施加固定先验；不会直接平均各月的宏观错误率。当前月经验最优标签仅用于诊断，不作为待比较的预测模型。

### 输出与查看

- `report.md`、`summary.json`：三模型的月度/整段比较、匹配训练量结果和 APP=2 的归因概览。
- `rolling_monthly_summary.csv`、`rolling_period_summary.csv`、`matched_training_summary.csv`：完整及匹配训练量的汇总；跳过随机对照时不生成最后一项。
- `rolling_class_metrics.csv`：全部类别的训练量、目标样本量和错误；`--small-n` 仅标记目标小样本。
- `focal_model_confusions.csv`、`focal_attribution_confusions.csv`：APP=2 的误判去向和其他类别被判为 APP=2 的情况；区分实际过去训练模型与诊断性经验规则。
- `focal_symbol_attribution.csv`：全部固定字母表上的逐符号贡献、竞争类别及细/粗经验标签；`focal_packet_marginals.csv`、`focal_packet_TV.csv`：包位置边际变化。
- `confusion_matrices.json`：全部已知类别的完整计数混淆矩阵；`plan_snapshot.json`、`run.json`：计划及输入/代码/输出哈希。

完成后终端直接显示各月三模型错误、整段完整/匹配错误，以及 APP=2 每月最主要的误判符号与竞争类别。`error` 为固定先验加权错误，`APP_error` 为 APP=2 类别条件错误，`*_pp` 为加权百分点。未知类自身错误未计入；已知类别条件后验和精确率不描述未知类。所有本轮结果仍是探索性证据，不新增表示选择或风险证书。

## 第七轮：全部 44 类的错误重分配与符号 479 原始特征

本轮输入为已经完成的月计数 `artifacts/methodology/real_monthly_20261012_213718`、滚动实验 `artifacts/methodology/real_rolling_20261013_102535`，以及原始 H5 和准备审计。使用当前 `traffic-ncde` 环境，不增加依赖，不改变 `statcore.py` / `realexperiment.py`，原缓存的编码来源校验继续有效。

完整命令如下。外层子 shell 的 `set -euo pipefail` 确保拉取、测试或实验失败后停止，不通过 `tee` 掩盖 Python 错误；日志和两份报告放在同一个新目录中。

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_DIAG_OUT="artifacts/methodology/real_collision_$(date +%Y%m%d_%H%M%S)"
    mkdir "$EIBO_DIAG_OUT"

    python -u scripts/methodology_real_reallocation.py \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --rolling-dir artifacts/methodology/real_rolling_20261013_102535 \
        --small-n 200 --top 10 \
        --out-dir "$EIBO_DIAG_OUT/reallocation" \
        2>&1 | tee "$EIBO_DIAG_OUT/reallocation.log"

    python -u scripts/methodology_real_collision.py \
        --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
        --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --backend tables --chunk-rows 20000 \
        --symbol-id 479 --apps 2 34 \
        --reference-months 2024-12 2025-01 --small-n 200 \
        --out-dir "$EIBO_DIAG_OUT/symbol479" \
        2>&1 | tee "$EIBO_DIAG_OUT/symbol479.log"
)
```

### 全类别错误与预测转移

`methodology_real_reallocation.py` 先核验两轮输出的文件清单、原始数据来源、完整计划和固定先验，再从已核验的月计数重建三个模型的每一张混淆矩阵，核对保存的逐月/整段错误。随后比较最近 1 个月、最近 3 个月相对固定 pilot 的变化，两种原表示和全部 44 类均保留。

- `class_error_changes.csv`：逐月和 certificate/evaluation 整段的每类错误、条件错误变化、固定先验加权变化及样本量标记；区分错变对（rescued）、对变错（harmed）、错变另一错误类别，以及预测改变总数。
- `confusion_changes.csv`：全部真类/预测类组合的计数与变化，保留对角项。非对角项的加权变化之和等于全部类别错误变化。
- `prediction_transfers.csv`：同一目标样本在两个模型之间的原预测→新预测转移；由公共符号计数精确汇总，无需输出单流记录。若预测没有改变，文件仅保留表头。
- `matched_class_changes.csv`：重放第六轮原种子、原重复次数和逐类共同训练预算，保存全部类别的条件变化均值、加权变化均值和随机子集标准差/分位数。若第六轮没有匹配实验，不生成该文件。重放的月度整体及 APP=2 指标必须与第六轮一致。
- `report.md`、`summary.json`、`plan_snapshot.json`、`run.json`：整体变化、正负贡献、改善/恶化类别数、评估期主要类别、完整来源与哈希。

每类 `harmed - rescued` 必须等于错误计数增量；全部类别贡献必须等于整体错误变化。整段先在每类内部合并各月错误计数，再按固定先验加权，**各类具有不同的月份权重**。因此，整段改善与每月宏观错误恶化可能同时发生，必须同时检查两种口径。匹配重复仍是给定训练计数的子集敏感性，不是总体置信区间或时间相关性修正。

### 符号内部的精细尺寸和时间分布

`methodology_real_collision.py` 重新校验原 H5 SHA256、大小和准备审计的表/字段元数据，完整扫描全部记录。沿用原窗口、整流包络和前缀有效性，先按原 log M=2 编码筛选符号 479，再记录 APP=2、34 的前五个包细节。**所有类别、所有月份和两种原表示的符号计数必须逐项等于已保存月缓存**，APP=2/34 的细节流数也必须等于该格子的原计数。

符号 479 为 `C:39+ S:39+ C:39+ S:39+ S:39+`。根据 [CESNET 官方特征说明](https://cesnet.github.io/cesnet-datazoo/features/) 和 [PPI 通道常量](https://github.com/CESNET/cesnet-datazoo/blob/main/cesnet_datazoo/constants.py)，PPI 第 0 行为毫秒级包间隔，第 1 行为方向，第 2 行为传输层载荷字节数。载荷尺寸不是完整线上包长；现有数据无法恢复亚毫秒时序。编码筛选仍按原规则饱和到 1500，但细节统计**保留实际超过 1500 的尺寸**。首包间隔应为结构性 0；保留其统计及非零诊断，差异排名排除该位置。其余位置的零间隔正常保留。

- `cell_occupancy.csv`：逐月、原整段和 12–1 月参考期的全部 44 类总流数、格子流数、类内格子概率、固定先验质量和已知类条件后验。后验分母包含全部已知竞争类，不能用 APP=2/34 的原始二类比例替代。
- `distributions.csv`：APP=2、34 在各范围内每个包位置的精确观测值计数和概率，分别记录 `size_bytes` / `IPT_ms`。
- `feature_summary.csv`：均值、经验逆 CDF 分位数、极值、零值比例、等于 1200 / 超过 1500 的比例、有效/无效数。数值阈值使用各自特征单位；尺寸比例用于检查尺寸饱和。小样本仅标记。
- `marginal_comparisons.csv`：同月两类在符号内的边际 TV、CDF 最大距离、分布重叠，以及 12–1 月参考期到之后各月的同类边际漂移。
- `report.md`、`summary.json`、`plan_snapshot.json`、`run.json`：类别竞争、逐月分位数、主要差异/漂移、完整扫描与原计数核对、输入/代码/输出哈希。

非有限/负间隔只从相应边际分布中排除，保留该流的格子计数并报告无效数，不改变审计总体。边际分布结果不等于联合序列可分性，精确支持集 TV 会受稀疏观测和采样噪声影响；不计算独立样本 p 值，不声称分类提升。符号和焦点类别来自前一轮观察，属于事后诊断，本轮不选择新表示、不拟合新分类器、不新增风险证书。

## 第八轮：符号 479 的四组过去月份表示对照

`scripts/methodology_real_refinement.py` 比较原 log M=2 表示、仅细分包长、仅加入第二包间隔、两者结合。全部 44 类与原先验不变。每组分别在固定 pilot、最近 1 个日历月、最近 3 个日历月的训练窗口中运行，对 certificate/evaluation 六个月逐月评估。**同一窗口下四组使用同一批完整训练流和目标流**，不为不同表示重新抽样。过去标签可用的假设沿用第六轮。

原来的符号检查只保留 APP=2/34 的细节，无法支持全部 44 类的联合细分。本轮需重新扫描一次 H5，保留符号 479 内全部已知类的有限联合原子计数；两种原编码的所有月计数、原窗口/整流包络及固定类别顺序必须逐项核对，原表示的预测混淆矩阵必须重现第六轮。`statcore.py` 与 `realexperiment.py` 不变，旧缓存仍可校验。

服务器当前 `traffic-ncde` 环境完整执行，无需新增依赖：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_REFINE_OUT="artifacts/methodology/real_refinement_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_REFINE_OUT"
    test ! -e "${EIBO_REFINE_OUT}.log"
    python -u scripts/methodology_real_refinement.py \
        --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
        --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --rolling-dir artifacts/methodology/real_rolling_20261013_102535 \
        --symbol-id 479 --size-positions 1 2 3 4 5 \
        --models fixed_pilot rolling_1m rolling_3m \
        --backend tables --chunk-rows 20000 \
        --min-leaf-flows 200 --small-n 200 \
        --out-dir "$EIBO_REFINE_OUT" \
        2>&1 | tee "${EIBO_REFINE_OUT}.log"
)
```

### 训练期选阈值与四组表示

候选网格在代码中固定，且在扫描前写入 `selection_protocol.json`。包长阈值单位为实际传输层载荷字节，包含 1200、1500 两侧和更高尺寸的候选；时间阈值单位为毫秒，包含 0–5 的细网格及较大间隔候选。原始超出 1500 的尺寸按新候选正常分箱，不能用原编码的饱和值代替。候选列表完整记录在协议文件，可用 `--size-cuts` / `--ipt-cuts` 显式替换为严格递增的固定列表；改变候选网格需要重新生成对应的原子计数。

对每个目标月，先按第六轮严格日历规则取得过去窗口。包长组在前五个包的位置与候选阈值中选择**一个位置、一个二分阈值**；时间组只对第二包间隔选择一个二分阈值。选择目标为全部已知类的训练经验风险下降：每个子格子的竞争分数是 `pi_i * child_count_i / n_i`，其中 `n_i` 是该类在整个训练窗口的流数。不能把分母替换成该类在符号 479 内的数量，不能按 APP=2/34 二类比例选择。

组合组直接交叉上述两个已选阈值，不再额外搜索组合阈值，便于解释两种特征的组合收益。两组主效应分别最多产生两个有效子格子，组合最多产生四个有效子格子；无效/负/非有限第二包间隔有额外的无效子格子，保留全部流。因此时间组最多三个子格子，组合最多六个。缺失的候选分割显式回退为原表示或已有单一特征，不伪造阈值。训练中全类别均未见过的子格子回退到原父符号的分类规则，报告未来落入该子格子的流数/加权质量。

每个可选二分的低/高有效子格子至少包含 `--min-leaf-flows 200` 条训练流，该条件按全部类别的原始计数判断。无效时间子格子由记录内容确定，不参与这个最低流数门槛。此门槛仅限制分割复杂度，**不是独立样本量或置信保证**。分数在 1e-12 内并列时，固定选择更早的包位置和更小阈值。实际阈值及模型只使用过去窗口的标签；目标月只用于冻结后的评估。

符号 479 之外的表示和同窗口原模型预测必须保持一致，所有细子格子都有到原符号的确定投影。训练期与完整类别目标期的经验风险在细化后不能增加，组合表示的经验收益不能小于任一主效应。实际过去训练分类器的未来错误仍可能增加，需通过类别错误与混淆表检查。

### 输出和解释

- `report.md`、`summary.json`：全部阈值、每月四组错误、APP=2/34 条件错误、经验 F 与经验表示收益、各训练窗口的整段错误及评估期主要改善/恶化类别。
- `monthly_summary.csv`：分类错误相对同窗口原表示的变化、经验表示收益、经验差距变化、有效细分标记和未见子格子流数。样本恒等式为 `错误变化 = -经验表示收益 + 经验差距变化`；差距指实际分类错误减去当前样本经验 Bayes 泛函，不能解释为因果效应。
- `period_summary.csv`、`period_class_metrics.csv`：certificate/evaluation 先在每类内合并各月错误计数，再施加固定先验；保留全部 44 类，不直接平均月度宏观错误。**滚动阈值可逐月不同，不能把不同细表示的子格子当作共同字母表池化；整段不报告池化经验 F/表示收益**。
- `class_metrics.csv`：每月每组全部类别的错误与增量、错变对/对变错计数，以及每类的带符号经验表示收益贡献。分类变化必须完全来自符号 479；全类别贡献之和须等于相应整体指标。
- `threshold_selections.csv`、`threshold_candidates.csv`：过去训练月份、最后训练结束/目标开始时间、实际位置/阈值、训练目标得分、每个候选的子格子数量和是否符合门槛。
- `cell_children.csv`：每个子格子的条件、全部竞争类别的训练/目标计数、训练预测类别及已知类训练后验。
- `monthly_atomic_counts.json`：固定候选网格下的月度联合原子计数，轴为包长位置、固定类别、包长原子、第二包间隔原子；末时间原子为无效标记。用于按已保存协议复现四组，不导出单流或身份字段。
- `confusion_matrices.json`、`selection_protocol.json`、`plan_snapshot.json`、`run.json`：全部混淆矩阵、选择协议、原计划与输入/代码/输出哈希。

缺失训练类别时，四组全部标为不可用，不缩减类别或重归一化先验。目标月份缺失类别时，保留已有类别的分类指标和缺失值可辨识范围，完整经验 F/表示收益为 NA；小样本只标记。带符号的每类经验表示收益可以为负，完整类别之和必须非负。

本轮不新增跨训练窗口的等样本量随机对照；同窗口四组已经使用相同训练流，窗口之间仍有训练量差异。符号、时间特征与实验家族来自此前已查看的月份，虽然实际阈值按过去数据选择，结果仍属于探索性证据，不是新确认性留出集，不新增显著性或有效风险证书。引入时间和更细包长后，原粗表示的风险下界不能直接当作新分类器的下界。

## 第九轮：仅在低间隔分支内细分包长

上一轮服务器结果中，加入第二包间隔的评估期收益全部来自 APP=21，APP=2 的条件错误没有改变。交叉组合虽有额外整体收益，固定 pilot 与最近 3 月模型却使 APP=34 条件错误增加约 12.94 个百分点。本轮 `scripts/methodology_real_hierarchy.py` 检查：**先使用上一轮选出的间隔阈值，只在低间隔分支内搜索包长二分，高间隔与无效间隔分支保持时间组的原判决**，是否能够获得额外收益并避免 APP=34 的上述代价。

复用第八轮 `real_refinement_20261013_123459` 保存的全部已知类联合原子计数，**无需重新读取 H5，无需安装新依赖**。输入的完整运行状态、文件/旧代码哈希、原计划、类顺序、先验、每月符号 479 总数和各包位置的间隔边际须全部核对；再按保存协议重现第八轮四组阈值、每月/整段指标与全部混淆矩阵。若来源或结果不一致，脚本停止。按原目录名定位月度输入，避免多个阶段同名 `summary.json`、`run.json` 的哈希混淆；迁移缓存时保留这些目录名。

服务器当前 `traffic-ncde` 环境完整执行：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_HIER_OUT="artifacts/methodology/real_hierarchy_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_HIER_OUT"
    test ! -e "${EIBO_HIER_OUT}.log"
    python -u scripts/methodology_real_hierarchy.py \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
        --min-leaf-flows 200 --small-n 200 \
        --out-dir "$EIBO_HIER_OUT" \
        2>&1 | tee "${EIBO_HIER_OUT}.log"
)
```

### 冻结高间隔判决与过去月份选择

四组为 `original`（原表示）、`ipt_split`（上一轮时间组）、`crossed_size_ipt`（上一轮交叉组合）和 `low_size_split`（新增低间隔分层细分）。三个对照的全部混淆矩阵必须重现第八轮。同一窗口四组保持全部 44 类、原先验、原训练流与目标流；固定 pilot、最近 1 月、最近 3 月仍沿用严格过去日历规则。

时间根阈值、交叉组的主效应阈值及最低训练流门槛直接重现第八轮协议。新增包长选择只查看同一过去训练窗口的低间隔计数，使用缓存原来的包位置与阈值网格。训练得分仍是 `pi_i * child_count_i / full_training_class_n_i`，不能以低间隔/符号 479 内数量为分母，也不只比较 APP=2/34。两个新增子格子各至少有 200 条全部类别合计的训练流，整体训练经验收益须严格大于 1e-12；没有符合条件的正收益分割便完全回退为时间组。并列时按包位置/阈值升序确定。未见低间隔子格子回退到**时间组低间隔父格子**的判决。

新增表示最多四个符号 479 子格子：低间隔小尺寸、低间隔大尺寸、高间隔、无效间隔。它们必须确定投影到原时间组及原符号。高间隔、无效间隔及符号 479 之外的判决逐项检查不变。

这一约束给出一个可直接检查的分类性质：低间隔父格子原来只预测一个类别，改变其中的判决，只可能给**该原预测类别**增加错误；其余类别在任意目标分布上均不会新增错误。如果低间隔父判决为 APP=21，则 APP=34 相对时间组逐流受保护，但 APP=21 仍可能受损。脚本不默认父判决一定为 21，会报告实际类别和 APP=34 是否受保护，并核对全部类别的错变对/对变错计数。这是分类规则的结构性质，不是依赖假设下的总体风险证书。

### 重点结果与输出

- `report.md`：过去月份阈值、低分支原预测、APP=2 的训练/目标竞争排名、四组逐月/整段错误、相对时间组的额外收益、APP=2/21/34 条件错误及主要改善/受损类别。
- `low_threshold_selections.csv`、`low_threshold_candidates.csv`：实际位置/阈值、训练月份与截止时间、全部候选的整体得分和 APP=2/21 带符号贡献。`best_eligible_APP2_training_gain` 仅说明有限候选中 APP=2 最多可获多少训练收益，不能作为事后替代决策；部署的选择仍按全部类别整体目标。
- `branch_competition.csv`：每个时间父格子和分层子格子的全部 44 类训练/目标流数、使用全类分母计算的已知类后验、过去训练判决及目标经验赢家。APP=2 排名并列取最优名次；完整分数差保留在阈值选择记录。目标排名/后验只在冻结规则后计算，不能参与阈值拟合。
- `class_metrics.csv`、`period_class_metrics.csv`：所有类别的错误、相对时间组的条件/加权变化、每月的精确获救与受损流数、带符号经验表示贡献。新增错误只能来自低分支原预测类别，逐类贡献须重现整体变化。
- `monthly_summary.csv`、`period_summary.csv`、`summary.json`：相对原表示和时间组的错误变化、三个重点类别指标；每月另外报告目标经验 F、相对时间组的经验收益与经验差距变化。整段先在每类内池化错误数，再施加固定先验；不同月份阈值可变，不池化经验 F。
- `confusion_matrices.json`、`selection_protocol.json`、`plan_snapshot.json`、`run.json`：完整混淆、协议、计划和哈希。`run.json` 的 `rows_read=0` 表示本轮不读取原始流，`cached_source_rows` 保留原缓存的完整扫描数量。

若 APP=2 仍无改善，先检查低分支中它与全部竞争类别的排名、选中子格子的赢家，以及是否存在能帮助 APP=2 的合格包长候选；据此判断当前二分家族的局限，不能从二类分布差异直接推断 44 类中的可分类收益。新增模型允许 APP=21 受损，须同时比较它的代价和整体收益。缺失类别保留先验/NA，小样本不剔除；本轮实验家族来自此前评估月份，结果仍是探索性证据，不新增确认性、显著性或独立时间单元保证。

## 第十轮：低间隔细原子诊断与逐月收益归因

第九轮的额外评估期收益来自 APP=15/22，APP=2 仍未改善。固定 pilot 和最近 3 月模型在固定先验下获益，但原始错误条数可能增加；不能只凭加权错误下降判断流量整体准确率。本轮 `scripts/methodology_real_atomic.py` 复用第八/九轮缓存，完成两项检查：更细的包长×间隔区域是否存在 APP=2 获胜机会，以及 APP=15、22 的逐月改善和 APP=21 的损失如何抵消。**全部 44 类与先验不变，不读取原始 H5，不新增依赖。**

完整执行命令：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_ATOMIC_OUT="artifacts/methodology/real_atomic_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_ATOMIC_OUT"
    test ! -e "${EIBO_ATOMIC_OUT}.log"
    python -u scripts/methodology_real_atomic.py \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
        --hierarchy-dir artifacts/methodology/real_hierarchy_20261013_131451 \
        --min-atom-flows 200 --small-n 200 \
        --out-dir "$EIBO_ATOMIC_OUT" \
        2>&1 | tee "${EIBO_ATOMIC_OUT}.log"
)
```

### 先复现旧结果，再区分表示与判决问题

脚本核验完整运行状态、原计划、原先验和类别顺序、输入/输出/旧代码哈希。第八轮四组结果和第九轮分层结果的全部阈值、指标、混淆矩阵须按联合计数重现，月度输入按父目录名定位，避免同名文件混淆。`statcore.py`、`realexperiment.py`、`refinement.py`、`hierarchy.py` 及其旧脚本均不修改，保持已有缓存的代码谱系可校验。

先读取全部合格二分候选的**未舍入** APP=2 得分。记录最佳加权增益、17 位有效数字的百分点显示、是否严格为零、正收益候选个数，以及对应训练正确条数变化。此前 `0.00000` 的显示不能自动认定为数学上的零；本轮明确区分。

时间根阈值与最低流数门槛沿用第八轮。对每个过去训练窗口和目标月，每个包位置分别展开低间隔内的全部包长原子×有效第二包间隔原子；各原子类别分数仍为 `pi_i * atom_count_i / full_training_class_n_i`。训练流数合计不足 `--min-atom-flows 200` 的原子回退为时间组低父判决，**不剔除流、不合并目标样本、不使用目标流数决定回退**。高间隔、无效间隔和符号 479 外的表示/判决保持时间组规则。各位置的细表示均确定投影到原时间组和原符号。

各位置独立形成训练模型与诊断结果；实际选中位置只按过去窗口的整体训练错误下降选择，1e-12 内并列时保留较早位置，无正收益则保留时间组。各位置观察是相同流的不同视图，不能跨位置把计数相加。现有缓存没有多个包长位置之间的联合关系，本轮不能据此拼造多包长联合表示。

目标月的经验最优规则仅用于低间隔区域，其余判决固定；这些规则不会参与模型/位置选择。完整类别月份分解为：

- `root_adaptation_gain`：原过去时间组与目标样本最优低父判决之间的错误差，表示不变。
- `empirical_representation_gain`：目标样本最优粗低父判决与最优细原子判决之间的错误差，整体须非负。
- `past_model_regret_to_atomic_oracle`：实际过去训练细原子模型相对目标细原子经验最优规则的错误差，包含漂移与训练回退的差距。

另外以相同过去训练直方图、仅保留未见原子回退的模型作比较，记录 `unguarded_past_regret` 和最低训练流门槛带来的 `guard_error_change`，满足 `past_model_regret_to_atomic_oracle = unguarded_past_regret + guard_error_change`。门槛影响可正可负：回退可能保护未来错误，也可能抹去 APP=2 的收益。未加门槛的判决差距仍包含有限训练估计误差，不能全归因于时间漂移。

恒等式是 `相对时间组的错误变化 = -(root_adaptation_gain + empirical_representation_gain) + past_model_regret_to_atomic_oracle`。同时检查 APP=2 是否为某原子的过去分数赢家、经过最低训练流门槛后的实际预测类别，以及目标样本经验赢家。这样可识别中间尺寸区间有机会但单阈值看不见、机会仅在未来出现、机会被训练流门槛回退等不同情况。经验最优只是当前有限缓存的样本比较器，细稀疏区域会显得乐观，**不是总体可分类准确率的上界或风险证书**。

### 精确逐月归因与输出

第九轮原分层模型的归因与新细原子模型分开保存。旧模型按整数混淆矩阵重建每类错误变化，逐月/整段核对 `新增错误数 = 受损条数 - 获救条数`，保留全部类别的原始条数、条件错误变化和固定先验加权贡献；重点展示 APP=15/21/22。整段先在每类内合并错误计数，再按原先验加权，不能直接平均逐月宏观错误。

- `binary_candidate_precision.csv`：二分候选未舍入得分、严格零标记与正确条数变化。
- `atomic_selections.csv`、`atomic_monthly.csv`：过去训练月份/截止时间、选中位置、各位置及选中模型的逐月分类变化、经验机会/判决差距、回退目标流数。
- `APP2_atomic_cells.csv`：每个位置和小区域的实际区间、过去/目标流数、APP=2 未舍入分数/竞争边际、最强竞争类别、实际训练判决与目标经验赢家。保留空区域和回退状态。
- `atomic_monthly_classes.csv`、`atomic_period_classes.csv`、`atomic_periods.csv`：新模型的全类别指标、固定先验加权错误及原始错误数。整段不池化不同月份的经验最优/表示收益。
- `hierarchy_attribution.csv`、`hierarchy_attribution_summary.csv`：旧第九轮模型全部类别的逐月/整段获救、受损、原始错误变化和加权贡献。
- `report.md`、`summary.json`、`confusion_matrices.json`、`selection_protocol.json`、`plan_snapshot.json`、`run.json`：核心诊断、全部选中模型混淆矩阵、协议及谱系。`rows_read=0`，`cached_source_rows` 保留原扫描数量。

缺失训练类别则该窗口不可用；目标缺失类别保留原先验和分类可辨识范围，完整经验最优诊断为 NA；小样本仅标记。本轮仍是此前查看过月份上的探索性诊断，不产生确认性或依赖修正保证。月度缓存不能确定收益是否集中于某天或会话；日/会话集中度需要更细聚合或另行扫描 H5。

## 第十一轮：联合包长与过去验证下的代价约束

第十轮的单个包长×低间隔细原子没有降低 APP=2 的实际错误，APP=21 的损失使原始错误条数增加。本轮 `scripts/methodology_real_joint.py` 采集前五包全部位置对的**真实联合包长计数**，检验两个包长共同出现时是否有稳定信号，并比较过去验证与代价约束的作用。旧单位置边际不能确定两个包长的联合关系，因此第一次需要重新扫描原 H5；之后可复用联合缓存，不新增依赖。

完整执行命令（继续使用当前 `traffic-ncde` 环境）：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_JOINT_OUT="artifacts/methodology/real_joint_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_JOINT_OUT"
    test ! -e "${EIBO_JOINT_OUT}.log"
    python -u scripts/methodology_real_joint.py \
        --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
        --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
        --hierarchy-dir artifacts/methodology/real_hierarchy_20261013_131451 \
        --backend tables --chunk-rows 20000 \
        --ipt-threshold-ms 4 --validation-day 21 \
        --validation-gap-seconds 86400 \
        --min-leaf-flows 200 --app21-budget-pp 0.1 \
        --max-validation-raw-increase 0 --small-n 200 \
        --out-dir "$EIBO_JOINT_OUT" \
        2>&1 | tee "${EIBO_JOINT_OUT}.log"
)
```

### 先隔离过去验证，再拟合并冻结规则

全部 44 类、原先验、原目标月份和原目标流不变。默认时间根为 `IPT2 <= 4 ms`；这个值由此前实验启发，在本轮扫描前写入协议，仍属探索性选择。包位置、尺寸网格与间隔单位沿用第八轮已校验协议。

- 固定 pilot：6 月至 11 月 1 日前用于拟合，11 月 2 日至原 pilot 结束用于验证。
- 最近 3 月：前两个月用于拟合，最后一个月留一天隔离后用于验证。
- 最近 1 月：过去月 21 日前用于拟合，22 日起用于验证。原月份起止与原计划的隔离仍保留。

边界只按日历确定。流的整个时间区间（包括一小时截断保护）必须落在拟合或验证窗口内；跨边界及隔离期的过去流不参与这两个角色，逐类记录 `unused_past_sample_counts`。这些流仍属于原历史窗口，目标月份完整保留。每类分母是该拟合/验证角色内的**全类流数**，不能改为符号 479、低间隔或叶子内的数量。

先用拟合数据确定所有候选的叶子判决，验证数据只选择候选，**不使用验证标签重新拟合**。任何固定类别在拟合角色缺失，该窗口的新模型不可用；任何固定类别在验证角色缺失，两种验证选择均回退为时间组。类别与先验不删减；未来缺失类别继续保留原先验的可辨识范围。

### 七组比较与结构保护

| 组 | 拟合与选择方式 |
|---|---|
| `time_fit` | 相同拟合子集上的时间根，作为新方法共同基线 |
| `single_fit` | 用拟合收益选择一个包长二分 |
| `joint_fit` | 用拟合收益选择一对包长的交叉二分，最多四个低间隔叶子 |
| `validation_weighted` | 从同一已拟合单包/双包候选池中，按正的验证加权收益选择 |
| `validation_constrained` | 验证加权收益须为正，另要求原始错误条数不增加、APP=21 条件错误增量不超过 0.1 个百分点 |
| `legacy_time_full` | 重现第八轮使用完整过去窗口的时间组 |
| `legacy_hierarchy_full` | 重现第九轮使用完整过去窗口的分层组 |

后两组用到更多拟合流，只作为旧结果参照。前五组共享拟合数据、目标流和先验；验证组额外使用同一过去验证数据选择规则。两种验证组的差别可识别代价约束的影响。

双包候选穷举全部位置对和两个网格阈值，低分支局部树深度最多二层，能够检验单包主效应为零的交互。每个非空拟合叶子至少有 200 条所有类别合计的流，至少存在两个非空叶子；拟合未见叶子回退到低父判决，未来流不剔除。恒等模型始终可选，无正收益时回退，并列优先较少非空叶子，再按固定候选顺序选择。

高间隔、无效间隔和其他原符号的判决冻结为 `time_fit`。修改低分支只能给其原预测类别新增错误；如果父判决为 APP=34，则禁用细化，因此 APP=34 相对 `time_fit` 逐流受保护。**APP=21 的 0.1 个百分点与原始错误零增量只是过去验证约束，未来漂移下可能失效**，须检查目标月实际代价。所有叶子仍由全部 44 类竞争。

### 输出、校验与复用

读取前校验准备、月度、第八/九轮的完整状态与全部输入/输出/旧代码哈希，重现旧阈值、指标和混淆。原 H5 校验 SHA256、大小、表结构和扫描前后状态。新的月度原表示和单位置原子必须逐项重现旧缓存，每个真实包长对必须投影回两个旧单位置边际；拟合/验证子集也分别检查类数、原符号、时间子格子和包长边际守恒。旧核心与脚本保持原样。

- `joint_counts.npz`：月度和拟合/验证角色的整数联合直方图；保留低间隔内的细时间原子，不保存逐流数据或身份。当前树只切包长轴。
- `collection_protocol.json`、`selection_protocol.json`：固定网格、全部角色边界、叶子门槛、代价预算、不重拟合规则。
- `candidate_scores.csv`：所有候选的拟合/验证得分、叶子判决与原始代价，不含目标标签得分。
- `selections.csv`、`summary.json`：实际冻结规则，逐类拟合/验证/未使用过去流数。
- `monthly_summary.csv`、`period_summary.csv`、`report.md`：七组逐月/整段结果，重点比较 APP=2 收益、APP=21 代价、APP=34 保护与原始错误条数。
- `monthly_classes.csv`、`period_classes.csv`、`confusion_matrices.json`：完整 44 类错误分解与混淆；新模型每类错误变化必须等于受损流数减获救流数。整段先在每类内池化错误，再按固定先验加权。
- `plan_snapshot.json`、`run.json`：原计划与源文件/代码/产物谱系。首次运行 `rows_read` 为完整扫描量，复用运行为 0；`cached_source_rows` 保留原扫描量。

复用时把首次输出目录填给 `--reuse-counts-dir`，取代 `--h5`，并指定新的输出目录。例如，仅调整 APP=21 验证预算：

```bash
python -u scripts/methodology_real_joint.py \
    --reuse-counts-dir artifacts/methodology/real_joint_替换为首次时间戳 \
    --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
    --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
    --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
    --hierarchy-dir artifacts/methodology/real_hierarchy_20261013_131451 \
    --ipt-threshold-ms 4 --validation-day 21 --validation-gap-seconds 86400 \
    --min-leaf-flows 200 --app21-budget-pp 0.2 \
    --max-validation-raw-increase 0 --small-n 200 \
    --out-dir "artifacts/methodology/real_joint_budget_$(date +%Y%m%d_%H%M%S)"
```

缓存复用严格校验联合产物哈希、角色几何、网格、原计划和源代码；叶子门槛与经验代价预算可变，不重新读取 H5。改变角色边界、根阈值或网格须重新采集。本轮的阈值家族和未来月份已被此前实验观察，验证选模自身也可能乐观；它仍是探索性方法检验，不提供总体风险保证或已验证的会话独立性。下一步依据冻结模型的真实目标收益和代价，决定是否值得固定方案、预留新时间段并开展确认性验证。

## 第十二轮：联合收益归因、APP=2 候选机会与逐月预算审计

服务器第十一轮输出 `real_joint_20261014_150841` 已完成 1000 万条扫描与投影校验。联合细化改善了整体错误，APP=2 仍未改善；过去约束下最近 1 月模型在 2025-03/04 的 APP=21 条件错误增量仍达 0.11950/0.11039 个百分点，最近 3 月模型在 2025-03 原始错误多 1 条。整段预算合格不能直接解释为逐月保护。

本轮 `scripts/methodology_real_joint_diagnostic.py` **仅复用缓存，不读取 H5、不改原规则或预算、不新增依赖**。它检查收益来自哪些类别，APP=2 是没有合格获胜区域、被样本门槛挡住，还是候选存在但未被整体目标选择，并定位留出验证后的基线退化。

完整执行命令：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_JOINT_DIAG_OUT="artifacts/methodology/real_joint_diagnostic_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_JOINT_DIAG_OUT"
    test ! -e "${EIBO_JOINT_DIAG_OUT}.log"
    python -u scripts/methodology_real_joint_diagnostic.py \
        --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
        --hierarchy-dir artifacts/methodology/real_hierarchy_20261013_131451 \
        --joint-dir artifacts/methodology/real_joint_20261014_150841 \
        --small-n 200 --top 5 \
        --out-dir "$EIBO_JOINT_DIAG_OUT" \
        2>&1 | tee "${EIBO_JOINT_DIAG_OUT}.log"
)
```

### 冻结旧模型并完整重现

读取原准备、月度、第八/九轮与第十一轮的完整状态、原计划、全部类别/先验及输入/输出/旧代码哈希。第十一轮联合 NPZ 必须投影到旧单位置边际，拟合/验证数量须守恒；用原始叶子门槛、预算和时间角色重新计算全部候选和七组选模，重现所有保存的逐月/整段指标、实际规则及混淆矩阵。旧核心与脚本均保持原样，避免使现有缓存谱系失效。

所有比较保持完整 44 类、原先验及目标流。除各细化组相对 `time_fit` 外，另外比较双包长相对单包长、验证收益选择相对训练收益选择、约束组相对无约束验证组，以及拟合子集基线相对旧完整过去基线。

按整数混淆计算每类净错误变化、条件变化和固定先验贡献；整段先在每类内池化。只有相对共同时间基线的原已保存配对转换可以报告精确获救/受损条数，并核对 `受损 - 获救 = 新增错误`。不同规则的两张混淆矩阵只能给出净变化，不能据此推算逐流获救/受损。

### APP=2 的候选与更细联合原子

逐个检查原来全部单包长和双包长候选，保留拟合叶子预测、原样本量门槛、APP=34 父分支保护、全部类分母。记录 APP=2 的拟合/验证/目标正确条数变化、拟合赢家叶子数、与最强竞争类别的分数差，以及候选实际被哪些原组选中。另记录原验证预算的拒绝原因：叶子门槛、父分支保护、验证缺类、无正验证收益、原始错误预算或 APP=21 预算。

每个家族汇总原始正 APP=2 收益候选数、合格正候选数、通过原验证约束的正候选数与最佳拟合收益。恒等规则提供零收益参照；没有正收益候选时不把负收益候选标成赢家。被选中规则和最佳合格拟合 APP=2 候选另展开逐叶子分数与样本量，便于识别整体目标忽略了局部 APP=2 机会的情况。

还检查每个包长对的完整细尺寸网格，低间隔内 IPT 轴在本轮合并。这个网格比两个交叉二分更细，**仅用于诊断，不部署或用目标标签重选模型**。统计原始 APP=2 获胜原子、按原门槛回退后的获胜原子、门槛抹去的 APP=2 拟合流数，以及目标样本的经验赢家。目标经验赢家须全部固定类存在才定义；经验赢家和“过去拟合候选在目标上的最大收益”均是事后样本诊断，不是总体可分类上限，也不能替代原选择。

不同包位置对是同一批流的多个视图，不能跨位置对相加获胜流数。完整原子表只省略拟合/验证/目标三个角色中 APP=2 均为零的原子；它们不会贡献 APP=2 正确条数。包长区间为 `(前一阈值, 当前阈值]`，首尾区间无相应界限；字节单位沿用源数据协议。

### 逐月预算与训练划分的区域分解

预算审计并列显示每月选择时的验证 APP=21 代价、验证原始错误增量，以及实际目标月对应代价。保持原 0.1 个百分点与零条增量预算，分别记录违约，不根据目标月表现调整预算。按窗口汇总检查月份数和违约数；这些模型月份并非独立试验，不输出二项显著性或成功概率保证。

训练划分另做一个严格的同表示比较：完整过去数据与原拟合子集，都使用本轮固定的 4 ms 时间根，分别拟合并在相同目标流上评价。每类错误变化精确分成符号 479 外、低间隔、高间隔、无效间隔四部分，并核对总和。这样可判断 APP=2 的退化是否主要发生在当前局部细化无法改变的区域。它仍不能单独识别样本量、数据新鲜度和估计噪声各占多少。实际旧完整过去模型可能使用不同学习阈值，因此也单独保留旧模型比较，不混为同一个比较器。

主要输出：

- `class_attribution.csv`、`attribution_summary.csv`：全部类别、月份和整段比较；稀有类与缺失类保留，原先验不重归一。
- `APP2_candidates.csv`、`APP2_candidate_summary.csv`、`APP2_candidate_leaves.csv`：完整候选、拒绝原因、实际选择组和逐叶子竞争。
- `APP2_pair_atoms.csv`、`APP2_pair_summary.csv`：细联合原子、样本门槛影响及明确标记的事后经验机会。
- `budget_monthly.csv`、`budget_summary.csv`：逐月预算迁移与违约。
- `training_split_regions.csv`：完整过去与拟合子集的逐类/逐区域变化。
- `report.md`、`summary.json`、`audit_protocol.json`、`collection_protocol.json`、`plan_snapshot.json`、`run.json`：核心表、原协议及谱系；`rows_read=0`，`cached_source_rows` 保留原始扫描量。

缺失拟合类使该窗口不可用，缺失目标类保留 NA 和原先验可辨识范围，小样本仅标记。未来若修改时间角色边界做新的多块验证，需要与第十一轮缓存几何区分；本轮诊断不声称已经完成新的稳健选模或确认性实验。

## 第十三轮：保留完整过去外围基线的局部增量验证

第十二轮精确审计表明，最近 3 月模型的 APP=2 相对完整过去固定时间根，多错 2541 条、约 7.27226 个百分点，全部发生在符号 479 外；最近 1 月在同一区域则少错 345 条。完整过去数据的使用不能预先假定必定更好。局部预算共有 4 个违约模型月份：2025-03 固定 pilot 的 APP=21 增量为 0.10457 个百分点、2025-03/04 最近 1 月为 0.11950/0.11039，以及 2025-03 最近 3 月原始错误增加 1 条。

本轮 `scripts/methodology_real_regional.py` 比较两种外围训练方式，**直接复用第十一轮联合缓存，不读取 H5、不新增依赖、不重新选择局部规则或预算**。它检验能否保留完整过去数据在非细化区域的分类能力，同时用单独的过去拟合/验证控制局部增量代价。

完整执行命令：

```bash
(
    set -euo pipefail
    cd /data/xjw/EIBO
    git switch codex/methodology-risk-certificates
    env -u http_proxy -u https_proxy -u all_proxy \
        -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
        -u GIT_ASKPASS -u SSH_ASKPASS \
        GIT_TERMINAL_PROMPT=1 NO_PROXY='*' no_proxy='*' \
        git -c http.proxy= -c core.askPass= -c http.extraHeader= \
            pull --ff-only origin codex/methodology-risk-certificates
    python -m unittest discover -s tests -p '*riskcert*.py' -v

    EIBO_REGIONAL_OUT="artifacts/methodology/real_regional_$(date +%Y%m%d_%H%M%S)"
    test ! -e "$EIBO_REGIONAL_OUT"
    test ! -e "${EIBO_REGIONAL_OUT}.log"
    python -u scripts/methodology_real_regional.py \
        --prepare-dir artifacts/methodology/real_prepare_20261012_180750 \
        --monthly-dir artifacts/methodology/real_monthly_20261012_213718 \
        --refinement-dir artifacts/methodology/real_refinement_20261013_123459 \
        --hierarchy-dir artifacts/methodology/real_hierarchy_20261013_131451 \
        --joint-dir artifacts/methodology/real_joint_20261014_150841 \
        --small-n 200 \
        --out-dir "$EIBO_REGIONAL_OUT" \
        2>&1 | tee "${EIBO_REGIONAL_OUT}.log"
)
```

### 两种外围基线与同一个局部规则

全部 44 类、原先验、原目标月份和原目标流不变。先校验旧产物/代码哈希并完整重现第十一轮，随后保留原五个局部组：`time_fit`、`single_fit`、`joint_fit`、`validation_weighted`、`validation_constrained`，每组各配两种外围预测：

- `fit_subset`：完整重现第十一轮的拟合子集模型。
- `full_past`：只有原符号 479 外的预测改用完整过去窗口拟合；479 内的低间隔、高间隔、无效间隔三个根预测及细化叶子均保持原拟合子集规则。

每种外围预测都有自己的共同 `time_fit` 基线。原训练/验证角色、原 4 ms 时间根、候选阈值、叶子门槛、判决、验证选模和预算全部冻结，不按目标月表现选择外围版本。

另外单独列出 `full_past_time`：在所有区域均用完整过去窗口拟合、时间根也固定为本轮相同阈值；以及原 `legacy_time_full`：第八轮实际学习阈值的旧时间模型。两者不能自动等同，也不能把混合基线直接叫作完整过去时间模型。

### 验证仅针对可变区域的增量

完整过去的外围模型可以使用局部验证期的流，因此其**绝对验证准确率不是留出指标，本轮不报告该值**。可用于原局部选模的是新规则相对共同基线的配对错误差：在 479 外，两者逐流预测完全相同，外围错误在相减时严格抵消；在 479 内，判决只来自原拟合子集，验证不重新拟合叶子。

脚本在验证和目标上都逐项检查完整类别混淆矩阵：`full_past 细化组 - full_past time_fit` 必须等于 `fit_subset 细化组 - fit_subset time_fit`。同时，所有局部组的 `full_past - fit_subset` 混淆差须一致；逐类整数错误变化必须完全来自原符号 479 外。原第十一轮的拟合子集对照混淆也必须逐项重现。

这允许把外围训练数据的影响与局部表示/选模的增量分开。它不使原先跨月失效的预算自动恢复；预算仍是相对**各自共同基线**的局部增量，不是绝对错误上限，也不是相对任意其他模型的总代价上限。APP=34 的结构保护同样只针对局部细化增量；外围训练方式本身可能改善或损害类别，绝对错误另列。

### 输出与判断方式

- `monthly_summary.csv`、`period_summary.csv`：两种外围训练与原五个局部组的所有结果，分别列出局部增量、相同局部组的外围变化，以及相对完整过去固定根/实际旧模型的总变化。整段先在每类内合并整数错误，再施加固定先验。
- `reference_summary.csv`：完整过去固定时间根和实际旧时间模型的独立参照指标。
- `class_metrics.csv`：全部类别及其原先验、条件/加权变化；局部精确获救/受损仍逐类核验。缺失类别保留 NA 和原先验可辨识范围；小样本只标记。
- `outside_class_effects.csv`：逐月的外围错误变化及完整过去、局部拟合、验证、未使用过去流的每类数量。不能只凭这个对照单独识别样本量、数据新鲜度和估计噪声。
- `APP2_outside_symbols.csv`：每个发生 APP=2 错误变化的原外围符号、两种过去判决、APP=2 分数和目标错误条数变化；条数总和必须重现外围 APP=2 的精确变化。
- `validation_local_increments.csv`：仅报告两个外围版本共同的逐类配对增量，不含外围绝对验证错误。
- `budget_monthly.csv`、`budget_summary.csv`：保留原局部预算和全部真实违约，因局部混淆增量严格一致而沿用原值。
- `frozen_selections.json`、`regional_protocol.json`、`invariants.json`、`collection_protocol.json`、`plan_snapshot.json`、`confusion_matrices.json`、`summary.json`、`report.md`、`run.json`：原规则、两种外围协议、全部不变量、计数与谱系；`rows_read=0`，保留 `cached_source_rows`。

运行末尾直接打印 `INVARIANTS`、两种外围下的评估期 `PERIOD`、APP=2 的 `OUTSIDE_APP2` 变化与 `LOCAL_BUDGET`，便于 ToDesk 核对。重点观察最近 3 月的 APP=2 是否恢复，以及其他窗口/类别是否付出代价；局部收益和原预算违约应与第十一轮一致。

本轮是基于已观察目标月份提出的探索性训练数据使用对照，不新增稳健预算、不声称会话独立、未来风险保证或方法新颖性已经成立。多过去时间块的稳健选模与新时间段确认仍是后续独立实验。
