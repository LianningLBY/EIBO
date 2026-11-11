# IF-E1 两视图融合探针

## 学校服务器运行

使用现有 `traffic-ncde` 环境。脚本沿用 NumPy、SciPy 和 PyTables，无需 GPU。

```bash
cd /data/xjw/EIBO &&
git switch codex/methodology-risk-certificates &&
git pull --ff-only origin codex/methodology-risk-certificates &&
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/if_e1_fusion_probe.py \
  --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --expected-sha256 6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab \
  --out "artifacts/methodology/if_e1_fusion_$(date +%Y%m%d_%H%M%S).json"
```

默认用拟合期最常见的 8 个 APP（28 对），每个时间窗口对每类用固定种子的等概率抽样保留至多 6,000 条。可用 `--top-apps 4 --max-per-app 2000` 缩小首跑；读 H5 仍扫描所有日表以完成分层抽样与时间包络审计。主比较使用默认配置。`--expected-sha256` 与已登记的 XS 文件对应；输入不匹配会报出实测哈希。输出为一个聚合 JSON，包含数据摘要、所有比较和分块界。使用一个新文件名。

## 比较口径

- 两个视图从 H5 同一行读取。保留前五包有效、PHIST 非零且整条流落入对应时间窗口的样本。Prefix 用现稿的 `log M=2` 编码。PHIST 用四个 8 格数组的完整向量，归一化后取平方根。所有方法按同一规则使用整流已结束的观测时点。
- 采用与 XS 时间探针相同的日历分期和一小时截断包络。将原 pilot 再划分为拟合、stacking、校准三个时间窗，按日历留一天间隔。两个后续时间窗用于留出评估。类别仅依据拟合期选定，后续窗口缺失类别时脚本会明确报出。
- 单源模型与 early fusion 在拟合和 stacking 两个窗口合并后训练逻辑回归。Early fusion 连接 prefix one-hot 与 PHIST。Late fusion 在拟合期分别训练单源，再在 stacking 期用两个 logits 训练融合器。各候选总体使用相同的训练标签和流量。所有二分类采用等类别权重和同一个固定 ridge 惩罚。
- 四种方法的最终观测都是一个量化标量。对每个预算，在校准期用同一分位数算法生成 4、8、16 格的分箱，并根据分箱类频率冻结判决。相同分数可产生重复边界，结果会记录实际占用格数。最强单源由校准期平衡准确率选定，随后用于两个留出期。

## 如何看结果

先看 `summary` 下的各预算和留出期。`mean_frozen_accuracy_gains` 是逐对平衡准确率差的描述性均值。`early` 和 `late` 分别以校准期胜出的单源为基线，`late_minus_early` 为两者的直接配对差。逐对结果位于 `pairs[].budgets[B].holdouts`。

- `methods` 给出各方案的冻结规则准确率、留出样本 TV、样本贝叶斯准确率及分箱计数。TV 和贝叶斯错误率的界适用于这个量化输出。
- `bounds.*.frozen_gain_intervals` 比较冻结判决。`bayes_gain_lower_vs_best_single` 比较融合表示与两个单源表示中总体最优者。它用融合冻结规则减去两个单源样本最优准确率的较大者，再扣除分块半径。压缩输出之间的真实增益允许为负，脚本保留其符号。
- `iid_flow` 是逐流独立参照。`start_*` 按开始时间分块，`span_merged_*` 合并可能被一条流的时间包络跨过的相邻块。查看 `span_merged_24h` 并对照其他块长和 `effective_blocks`。界以拟合、分块和各块类计数为条件，允许块内任意相关，并假设块间独立。分块只是显式的假设敏感性分析。
- `pointwise` 给出逐项区间，`simultaneous_panel` 在单个分块假设内对两段留出、全部服务对、预算和端点做 Bonferroni 校正。比较效果是否跨两个时间段复现时，看同一预算、同一分块口径下的结果。区间包含 0 表示现有比较的精度不足以确定符号。

每个块的质量为两类各半权重下该块的样本占比。配对正确性差、固定判决的 TV 对比，以及总体最优事件的 TV 对比，在质量为 `w` 的块上取值范围长均为 `2w`。脚本以此用 Hoeffding 计算半径。TV 上界使用样本 TV 不小于总体最优事件的样本对比，TV 下界使用校准期冻结的判决事件。输出中的风险区间由等先验二分类的恒等式 `R* = (1 - TV) / 2` 得到。

## 新留出数据上的复验

固定 8 格 late fusion。主检验为 APP 0 vs 1，辅助比较为原来不含 APP 0 的全部 21 对。新留出结果出来前固定两个 UTC 日期窗口和 APP 映射。

旧 JSON 没有保存所有系数。`freeze` 依据旧 JSON 的设置，从原拟合、stacking 和校准窗口重建模型，核对 stacking 系数、分箱边界和校准判决，再一起保存模型及其分箱。学校服务器上运行：

```bash
cd /data/xjw/EIBO
conda activate traffic-ncde
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/if_e1_fusion_validate.py freeze \
  --discovery /data/xjw/EIBO/artifacts/methodology/if_e1_fusion_20261111_184554.json \
  --h5 /data/xjw/CESNET-QUICEXT-25/XS/CESNET-QUICEXT-25-XS.h5 \
  --backend tables \
  --out /data/xjw/EIBO/artifacts/methodology/if_e1_frozen_b8.json
```

`evaluate` 使用兼容 H5 和两个新窗口，日期右端不含当天。脚本要求首窗比旧评估期结束晚至少一天，且新窗之间留至少一天。根据采集来源确认新文件确实是新流量，并根据两份数据的标签表确认 APP 指向同一服务。下例的路径和日期是占位符。APP 编码一致时用 `--same-app-codes`，否则用 `--app-map` 指定一个以旧 APP 编号为键、新 APP 编号为值的 JSON 对象。

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -u scripts/if_e1_fusion_validate.py evaluate \
  --frozen /data/xjw/EIBO/artifacts/methodology/if_e1_frozen_b8.json \
  --h5 /data/xjw/path/to/new-capture.h5 \
  --certificate YYYY-MM-DD YYYY-MM-DD \
  --evaluation YYYY-MM-DD YYYY-MM-DD \
  --same-app-codes --backend tables \
  --out /data/xjw/EIBO/artifacts/methodology/if_e1_validation_b8.json
```

每个窗口从首日开始交替保留一天、间隔一天，只评估整条流的时间包络都落在保留日内的记录。结果的总体是符合该规则的流量。JSON 报告各批次的样本数、配对增益和样本最优单源差距；缺少任一类的批次只报告样本数。

主检验要求 `separated_24h` 下 APP 0 vs 1 的贝叶斯增益下界在两窗都为正。每窗用单侧尾概率 0.025，使两窗下界同时覆盖至少 95%。辅助比较以 42 个单侧下界单独校正。`iid_flow` 是用同批流量的敏感性对照。间隔用于减少相邻批次的关联，置信界仍以批次独立及其条件均值解释为前提。对 4.76 个百分点的差距，现有主检验的最坏情形半径要更小，每个窗口约需 3,257 个等权独立批次。短留出期主要用于观察配对增益在时间上的表现。
