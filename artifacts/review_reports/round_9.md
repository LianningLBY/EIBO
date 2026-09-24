---
round: 9
review_mode: fresh
overall_score: "accept (4.5/5, shepherding-level revisions)"
score_value: 4.5
score_max: 5.0
score_label: "accept (4.5/5, shepherding-level revisions)"
verdict_canonical: "accept"
verdict_raw: "accept  , shepherding-level revisions)"
timestamp: 2026-09-18T01:07:09.470159+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 9 评审汇总报告
**目标会议**: USENIX Security 2027 Cycle 2（Research Track；注册截止 2027-01-19，投稿截止 2027-01-26 AoE，未过期；正文 ≤13 页不含参考文献/附录，双盲，Open Science 附录强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛，零分歧
**评分**: R1 4/5（方法+实验，置信 4/5）· R2 4.5/5（新颖性+相关工作，置信 4/5）· R3 4.5/5（格式/伦理/复现职责内，置信 4/5）→ **合并 4.5/5，accept（shepherding 级修订）**；轨迹：R7 3/3/4 → R8 4/4/3.5 → R9 4/4.5/4.5
**里程碑**: 九轮以来**首次无任何一方持 critical**。

## Summary
Round 9 修订将 Round 8 的唯一 critical 簇（校准+LP 可复核性）六个子项全部落地：§5.5 印出判据（双侧 95% Clopper–Pearson 下端点 < 名义 0.975，并明示这是对作者更严的方向）、"breaches" 改为诚实的 "loses confirmation" 框架、Table 6 完整校准表（生成器、污染率、B/TV/n 全网格、每格 200 重复与 CP 端点、trivial 格显式标注——R1 称"教科书级"）、功效边界声明、先前漏报的最大 n 格补报、LP 完整规格入 A.5（0.363 变为可复解）、两个校准 artifact 注册。连续三轮未修的图件与 Le Cam 排序本轮也修复。R1 全量重算（含 Beta CDF 反解 CP 端点、LP 可行点还原式 (3)、期望预算 0.012）与 R3 抽样复核全部吻合。剩余问题全部为一词至一段级，其中最重要的是新入文文本中的三处"散文与数学不符"方向词错误——构造与数值全部正确、论证句印反，是本项目的惯性缺陷模式。

## Strengths（三方一致）
1. **校准证据链完整闭环**：判据、全表、功效、双 artifact——R4-W7 六轮长跑以领域少见的规格收官；单侧/双侧保守方向声明经复算正确。
2. **修复始终选择对自己更不利的诚实表述**：margins 从 "far from the boundary" 改为带符号距离并点名 −0.0349 的越线对；"breach" 降格为 "confirmation loss"（更弱地指示问题）；期望预算引理把 "expectation-form" 从标签变为可复核的两句数学。
3. **执行率对比鲜明**：R8 清单 6 主项 5 个完全落地；图件、Le Cam、GPU 泛化等积压执行项一次清空；回归面连续三轮干净（哈希、时间戳、伦理、匿名）。
4. **四表面一致性成立**（R2 专项）：标题/摘要/引言/结论对 "certification-grade" 的表述现一致且有实测支撑；floor 定位漂移消除。
5. 视觉检查本轮 0 critical（历轮最佳）；64 条引文 0 缺失/幽灵，Fano [17] 补齐后聚合线归因准确。

## Weaknesses（全部 shepherding 级，无 critical）
**[W1 — 本轮最重，warning-high] 三处散文-数学方向词印反**（R1 发现，R2/R3 从 PDF 逐句确认；R2 交叉时的正确转述恰证明缺陷是散文级）：
① A.5 LP 有效性论证："each 1−εhi is no **smaller** than the 1−TV it stands for, so the objective can only undershoot"——应为 no **larger**（εhi≥TV ⇒ 1−εhi≤1−TV）；前提与同句正确结论矛盾。
② A.5 约束 "=1 for each of the **M** classes" 与 "U 类对不加权"（行和恒 0）不相容——应为 "each known class =1, unknown =0"。
③ §3.1 预算引理 "each term ŝ fails to **upper-bound** its 1−TV"——ŝ 是下界，应为 lower-bound。
三处均一词/一句修复，camera-ready 必修。
**[W2] §5.5 括注 "(0.9496, the only one below nominal)" 与自印判据矛盾**（三方独立发现）：按 CP 判据两格均低于 0.975、按点覆盖率零格；仅有的两种使其为真的读法（对照 per-law 0.9875 / 对照 CP 水平 0.95）均与 Table 6 声明的名义矛盾。删括注或改 "(the lower of the two)"。
**[W3] 溯源收尾三件套**：LP 求解 artifact 未注册；两个新校准条目缺 content_sha256（旧条目均有，风格自破）；Table 6 缺 seed。注册级工作。
**[W4] Table 6 '–' 标记不自洽 + camera-ready 页数**：trivial 性由 (TV,n) 决定、与 arm 无关（caption 自称两 arm 共用同一 radius），但 '–' 只标 i.i.d. 列，B 列同格印 200/200——把确定性事件呈现为信息性测量。同时总页数 21 超 camera-ready 20 页限 1 页（提交阶段合规）。**一次修复协同解决**：四列同标 '–' + 折叠 17 行全同 200/200 行（回收约半页）。
**[W5] M 配对第三轮未声明**：0.186（M=46）对 0.737（45 类闭集）；匹配配对 0.194/3.79×。一句话，列为 shepherding 硬项。
**[W6] 披露句议定改写第二轮未执行**："carried three normalisation errors before they were caught" 逐字保留；评审组议定折中（保留同源降权的认识论内容、删 debug 叙事）未实施；mixture+metric/exclude-U 构造数值仍未印（至少入 artifact）。
**[Minor 批次]**：结论缺 uniform-prior/i.i.d. 限定且未提校准结果（六轮收官证据在结论零出现）；Fig 1 尺寸第三轮未放大（标签 <8pt）；y 轴 1.2/1.4；R7-W6（M≥2 下侧）与 R7-W17（k=20,25 来源）第三轮无 disposition——评审组要求明确 fix/wontfix 记录；luxemburk author/缩写保护第三轮源码未修（渲染无碍）；[24] l1 数学体；References 不起新页。

## Reviewer Consensus
全部发现三方 [AGREE]，交叉零分歧。R8 修复确认三方独立核验一致；本轮新问题清单由三方互补构成（R1：方向词与 '–' 不自洽；R3：页限与哈希/seed；三方共有：括注）。合并 shepherding 清单（优先级）：①方向词三处 ②删括注 ③Table 6 折叠+'–' 统一 ④溯源三件套 ⑤M 配对 ⑥披露句改写。

## Reviewer Divergence
无。唯一的评分差（R1 4/5 vs R2/R3 4.5/5）非立场分歧：R1 明示方向词错误落在其 soundness 职责内、修复确认前不上调，清单落实即支持无保留接收。

## Questions（需作者回应）
1. W1 三处修正是否接受？（smaller→larger；U 类约束改写；upper→lower。）
2. §5.5 括注本意是哪一级名义？（建议直接删。）
3. LP artifact、两个哈希、seed 是否补齐？
4. camera-ready 1 页削减计划？（Table 6 折叠是最低成本路径。）
5. M 配对声明与披露句议定改写为何两轮未执行？请给明确 disposition。
6. R7-W6（M≥2 下侧）、R7-W17（k=20,25）第三轮：fix 还是 wontfix？

## Missing References
无新增必引（64 条覆盖完整；Fano [17] 本轮补齐）。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
本轮完成，历轮最佳：0 critical / 2 warning / 10 info。两处 warning：Table 1 字号低于正文（建议 table*）；p14 Ethics 后约三分之二空白。Fig 1 单栏内标签 <8pt（建议 figure*）。引用渲染全部干净、无公式错误、无溢出。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：64/64 在线核查，0 缺失/孤儿/幽灵/撤稿；luxemburk author 与缩写保护为第三轮源码级遗留（渲染无碍）。
- **质量审计：本轮口径异常，降权为参考**。审计在提交后继续演化的工作树上运行（该树编译失败），其内容发现与提交 PDF 多处矛盾（如称 M 配对声明已在正文——三位评审从提交 PDF 核验为未修）。主席裁定：提交 PDF 为本轮唯一权威对象。审计的两条独立观察（摘要 336/340/990 指代邻近歧义；"destroying the certificate" 在 M≥2 仅测上侧的超测表述）未经评审裁决，记入追踪器待下轮（如有）从提交 PDF 裁决。流程注记：后续轮次审计输入应为提交快照。

## Overall Assessment
**Verdict: accept（4.5/5，置信 4/5，shepherding 级修订）**。
九轮评审轨迹在本轮收于三方一致的 accept：R8 唯一 critical 簇六子项全部落地并经独立重算验证，clear-accept 门槛（R5-W7）的 provenance 附带条件（R3）已由 Table 6 + 双 artifact 实质兑现。剩余清单无一影响任何数值结论——最重的 W1 是"构造正确、论证句印反"的三处一词修复；其余为括注、折叠、注册、一句话声明与两项 disposition 记录。评审组建议：以 shepherd 条件形式接收，条件清单即上文 ①–⑥ 加 camera-ready 页数计划。对投稿时点的提示：截止 2027-01-26，时间充裕；luxemburk/缩写等源码级引文卫生与 Fig 1 尺寸应在提交前一并清空，避免遗留三轮以上的执行项进入正式评审视野。

## Detailed Comments（分节）
- **Abstract**: 四要素与定位一致性均已到位；审计的两条观察（336/340 指代、"destroying the certificate" 措辞）待裁决（R9-W7）。
- **§3.1**: 预算引理入文（③方向词待修）；margins 带符号化超预期；披露句折中改写与 M 配对声明两项 disposition 待执行。
- **§5.5 + Table 6**: 判据/全表/功效/artifact 四件套落地；括注删除（W2）；'–' 四列统一 + 折叠（W4）；补 seed（W3）。
- **A.5**: LP 全规格入文（①②方向词/约束修正）；LP artifact 注册（W3）。
- **§7 Conclusion**: 信道限定已恢复；补 prior/i.i.d. 限定与一句校准结果。
- **§4.2**: R7-W6 第三轮，要求 disposition。
- **References**: Le Cam 三轮后关闭；luxemburk/缩写/[24] 源码卫生收尾。
- **图件**: 主缺陷修复；Fig 1 尺寸（第三轮）与 y 轴为最后残留。
- **Open Science**: 校准双 artifact 注册到位；哈希两条 + LP 条目补全后溯源纪律完整闭环。