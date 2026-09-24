---
round: 7
review_mode: fresh
overall_score: "borderline (3/5)"
score_value: 3.0
score_max: 5.0
score_label: "borderline (3/5)"
verdict_canonical: "borderline"
verdict_raw: "borderline"
timestamp: 2026-09-17T16:37:36.493966+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 7 评审汇总报告
**目标会议**: USENIX Security 2027 Cycle 2（Research Track；注册截止 2027-01-19，投稿截止 2027-01-26 AoE，均未过期；正文 ≤13 页不含参考文献/附录，USENIX 模板，双盲）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮内收敛，无未决分歧
**评分**: R1 3/5（方法+实验，置信 4/5）· R2 3/5（新颖性+相关工作，置信 4/5）· R3 4/5（格式/伦理/复现职责内，置信 4/5）→ **合并 3/5，borderline**

## Summary
论文对开放集加密流量识别给出逐对 ε-indistinguishability 双侧区间（上侧有限样本、下侧渐近），并在本轮首次新增开放集聚合：由 Le Cam two-point lemma 得到的 pairwise-sum 误差下限 0.186，与实测检测器误差 0.737–0.830 对照（3.97–4.47×）。测量纪律（预注册、service-cluster bootstrap、known-truth 控制、负结果如实报告、内容寻址溯源）是全场公认的一流水平；但本轮新增的头条数字 0.186 存在三重记账缺陷，聚合形式对既有多类下界文献零定位，且 "certification-grade" 标签的最后一块支撑（上侧 coverage 校准）连续第五轮缺席。

## Strengths（三方一致）
1. 罕见的自我审计诚实度：负结果（chain-rule 估计器 known-truth 失败）、confound（heterogeneous-i.i.d. null 复现 Markov vote）、cancellation 全部如实入文并给数字。
2. 推断单元正确：990 对 = 45 服务完全图，全程 service-cluster bootstrap；跨语料 gap 结论（unmatched 显著、matched 未解析、power 有限）如实且已入摘要。
3. 可复核性极强：R1 重算全部承重数值（比值、二项 p 值、Table 3、式(3) 在 M=2 的归一化）全部吻合；content-addressed manifest + 64-hex 哈希 + 时间戳排序为 artifact evaluation 模板级。
4. 格式全面合规：正文实测恰好 13 页（零余量）、总 19 页 ≤ 20 页 camera-ready 限；双盲干净；Ethics/Open Science 附录实质性。上一轮的 12 项遗留问题本轮验证关闭 9 项（R6-W1/W2/W3/W4/W6/W7/W8、RT-W14、R5-W6），无回归。

## Weaknesses（核心，三方共识）
**[Critical] W1 — 0.186 floor 三处不 sound**（R1-N1 ≡ R2-N1，R3 从提交物证实，自动审计独立发现）：
(a) 措辞与算术矛盾：摘要/贡献 1 称 "aggregation of the certified pairs"，但仅认证对（336 对，每项 ≤1）最多给 336/2070=0.162 < 0.186；S_known=384.55 必然是全部 990 对之和（含 650 个未认证对）。
(b) 无联合置信水平：990 个各 97.5% 的区间需同时成立，naive union bound 在 990×0.025 下 vacuous——违反论文自设标准 "every number is tied to a stated confidence level"。两条修法均经组内数值复核可行：Bonferroni α/990（radius 每侧 +≈0.02，floor 存活，高概率语义）或期望修正（偏差 ≤≈0.012，期望语义）。
(c) "assumption-free" 丢失 §3.3 自认的 within-service i.i.d. binding assumption。
**[Critical] W2 — 信道条件性使 "shows the bound to be valid" 过强**（R1-N2，R2/R3 引论文 §4.4 原文背书）：floor 界的是粗信道（k=5, M=1, 32 格），panel 检测器用论文自称 "strictly finer" 的 10 维观测，数据处理不等式下细信道真实 floor 可低于 0.186；0.737≥0.186 只是"一致"。§4.4 在 pair 级已正确弃用该强措辞，摘要/§3.1 聚合级退回了旧版本。改 "consistent with" 并声明适用范围。
**[Critical] W3 — 聚合对多类 Bayes 误差下界文献零定位，4× 松弛无法归因**（R2-N2，R1/R3 背书）：pairwise-sum 是已知最松聚合族；Fano、Henze–Pearson（Berisha 2016；Sekeh–Oselio–Hero）、LP 最紧聚合均可用同一 990 对输入，论文未引未比。项目自有工件中存在三个更强已验证构造（LP 0.363、mixture+metric 0.363、exclude-U 0.372，对同一实测 0.7366 仅松 2×），均不在提交 PDF——A.3 承诺公开工件，该缺席可被发现并读作选择性报告。R1 补充可辩护点：pairwise-sum 是唯一平凡保持逐对置信语义与开集丢项性质的形式——但辩护必须写进论文且不豁免数值对照。
**[Critical] W4 — 上侧 coverage 校准第五轮缺席**（R4-W7 升级；R1-N3，R2 背书，R3 职责内保留）：§3.3 本轮新增的是承认段而非测量；其"合成对不可检验"论证只排除 near-identical 设计，中等 true-TV 扫描 + 依赖数据 arm 仍可行且是作者自指的威胁方向。这是 "certification-grade" 标题的最后一块空支撑。
**[Warning] 摘要级**：W5 0.737 对象规格不清（闭集 45 类还是含拒识 46 类；§3.1 缺 §4.4 式 scope 声明；审计另指措施设计文本疑将 delta CI [0.454,0.627] 置于实测误差语境，实测误差自身 bootstrap 为 [0.648,0.821]，待作者澄清）；W6 下侧仅 M=1 计算，"scarce object" 单档验证；W7 gate 常数出处（0.5 以他用注册、0.05 从未注册）；W8 Mmax 闭式未印出；W9 Table 2 caption 范畴错误（residual）；W10 "14% swing" 无口径可得（实为 12.6%）；W11 "four rungs finer" 与 Table 1 首零点 M=8（三档）计数矛盾；W12 εhi>1 截断未声明。
**[Warning] 图件/引文**：W13 图 2a "33.9\%" 转义泄漏（主结果图）、图 3b y 轴截断、图 1 打印不可读（三方独立发现）；W15 引文卫生批次（[5] Le Cam 姓氏解析为 "Cam" 致排序错误、2 条 luxemburk 缺 author、4 条缩写未保护、15 条元数据不匹配含 3–4 个疑似错误 DOI）。
**[执行约束] W20**：正文零余量——W1/W3/W4/W8 的修复合计约 0.3–0.5 栏增量，需同步删减（§5.5 重复句、压缩 §3.1、Mmax 入附录、Background/Related Work 去重）。

## Reviewer Consensus
全部 critical 与绝大多数 warning 为三方 [AGREE]：R1-N1≡R2-N1；R1-N2 获 R2/R3 引原文背书；R2-N2/N3 获 R1/R3 验证背书；R3 的格式实测与图件缺陷获 R1/R2 复核确认。9 项上轮遗留验证关闭。

## Reviewer Divergence
无未决 [REBUT]。仅有的两个 [REBUT] 均为以证据关闭 R3 自标"待验证"的 [15] Eriksson 引用存在性：自动核验 + R1 + R2 三重独立确认 arXiv:2602.08769 真实存在，非幽灵引用，不触发 must-fix。R3 对 R1 预注册时间戳 minor 的部分反驳（所求限定声明已在 Open Science "That ordering, not the word itself, is the claim"）成立，该 minor 降为可选。

## Questions（需作者澄清）
1. S_known 求和中 εhi 是否截断于 1？0.186 拟采用哪种联合置信语义（Bonferroni α/990 还是期望修正）？
2. 0.737 是 45 类闭集 macro 误差还是含拒识的 46 类开放集误差？[0.46,0.63] 区间指向哪个量？
3. 同一 990 对输入下，LP/Fano 型聚合的 floor 是多少？工件中的 0.363/0.372 构造为何未入文？
4. gate 阈值 (0.05, 0.5) 的出处与敏感性？
5. coverage 校准（中等 TV 扫描 + 依赖 arm）为何连续五轮未做？
6. camera-ready 阶段 artifacts 归宿（DOI 化仓库 vs USENIX AE）？

## Missing References
1. **WeFDE**：Li, Guo, Hopper, "Measuring Information Leakage in Website Fingerprinting Attacks and Defenses", CCS 2018——必引；"测量问题本身泄漏"的最直接先例；需明确区分互信息点估计 vs 有限样本双侧区间（novelty 声明区分后仍可存活）。
2. Sekeh, Oselio, Hero, "Learning to Bound the Multi-class Bayes Error"；Berisha et al. 2016（Henze–Pearson 型多类下界）——支撑 W3 的聚合定位。
3. （可选）Scarlett & Cevher, Fano 不等式指南。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审（状态：not_requested）。

## Visual Layout Check（非计分）
独立视觉检查代理本轮以错误退出（无诊断输出，可重试）；未产出报告。其缺口已被三位评审的逐页目检实质覆盖（图 2a 转义泄漏、图 3b 截断、图 1 可读性、附录排布、y 轴刻度等均已入 Weaknesses），用户可决定是否重触发。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）已完成**：60/60 在线核查，0 缺失、0 孤儿、0 幽灵、0 撤稿；15 条元数据不匹配、2 条缺 author、4 条缩写未保护——已并入 W15。
- **论文质量审计已完成**：6 critical / 83 warning / 6 info。其中 3 项 critical（最弱构造做头条、certified-pairs 描述矛盾、"certification-grade" 标题张力）与评审组发现三方吻合并已由评审独立裁决（W1/W3）；1 项（CI 对象错位）并入 W5 待作者澄清；其余叙事漂移条目（scarce 对象措辞、Background/Related Work 重复、Conclusion 过短、4 处 "---"）作为未裁决参考项记入追踪器 R7-W19。

## Overall Assessment
**Verdict: borderline（3/5，置信 4/5）**。
论文的测量纪律与可复核性达到该 venue 的 accept 水平，格式/伦理/复现接近满分（R3 4/5）；但本轮的核心新增——开放集 floor 0.186——恰好在论文自设的 "certification-grade" 标准上失守：描述与算术矛盾、无联合置信语义、假设限定丢失、验证措辞过强、聚合形式未定位且项目自有更强构造未入文。全部 critical 均为措辞+常数层面可修（数值大概率存活，两条修法组内已复核），唯 coverage 校准需要新实验。R1 明确表示：修复 W1/W2 + W3/W4 引文与定位并给出 coverage 至少一个 arm，可上调 4/5。相对 Round 6（4/4/4.5）的评分下降完全由新增内容的缺陷驱动，非既有内容回归——9 项遗留验证关闭、零回归是本轮的正面事实。距 clear accept 的路径明确：修复 0.186 的三重记账 + 把工件中已有的更紧聚合写进论文 + 补 coverage 校准的最小 arm。

## Detailed Comments（分节）
- **Abstract**: W1(a)(c)、W2、W11 全部落点；权力警示与约定依赖已合规加入（RT-W14 关闭）。
- **§1 Contributions**: 贡献 1 承袭 W1(a)；贡献 2 的 Mmax 闭式未印出（W8）；贡献 4 措辞已随 R6-W5 修复。
- **§2.3**: 三线拆分已与 §6.2 对齐（R6-W6 关闭）。
- **§3.1**: W1 全部三点、W5、W10、W12 落点；floor-vs-measured 段可压缩以腾页。
- **§3.3**: W4（coverage 承认段非研究，第五轮）。
- **§4.2/4.3**: R6-W7/W8 关闭；divisibility 网格 k=20,25 未声明（minor）。
- **§4.4**: 两替换方向已分别陈述（R6-W4 关闭）；Table 2 caption 残留范畴错误（W9）。
- **§5.1**: 匹配约定对照已加（R6-W2 关闭）。
- **§5.5**: 重复过渡句（W14）。
- **§6**: 缺多类下界聚合线（W3）与 WeFDE（W4/引文 1）。
- **附录/Open Science**: 复现材料模板级；Open Science 与 References 不起新页、refs 排附录后非常规（minor）；A.5 硬件披露匿名弱信号（作者权衡）。
- **图件**: 图 2a 转义、图 3b 截断、图 1 尺寸——均为图生成脚本层修复。