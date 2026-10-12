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
