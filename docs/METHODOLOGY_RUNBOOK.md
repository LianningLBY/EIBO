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
