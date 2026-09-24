---
round: 11
review_mode: fresh
overall_score: "accept (4.5/5, pre-submission must-fix list)"
score_value: 4.5
score_max: 5.0
score_label: "accept (4.5/5, pre-submission must-fix list)"
verdict_canonical: "accept"
verdict_raw: "accept  , pre-submission must-fix list)"
timestamp: 2026-09-18T13:26:15.385049+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 11 评审汇总报告（重构稿评审）
**目标会议**: USENIX Security 2027 Cycle 2，Security Measurement Studies（经核实为 CFP 主题域，提交规则同主 CFP；注册截止 2027-01-19，投稿截止 2027-01-26 AoE，未过期；正文 ≤13 页，20 页上限仅约束 camera-ready，双盲，Open Science 附录强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛；交叉阶段含两名评审的坦承自我修正（R2 两处、R3 一处），证据链质量高
**评分**: R1 4.5/5 · R2 4.5/5 · R3 4.5/5（置信度均 4/5）→ **合并 4.5/5，accept，附一张投稿前 must-fix 短清单**
**轨迹**: R7 3/3/4 → R8 4/4/3.5 → R9 4/4.5/4.5 → R10 4.5/5/4.5 → R11 4.5/4.5/4.5

## Summary
Round 10 后稿件经历实质性重构：摘要 408→330 词（双口径比值 3.97×–4.47×/3.79×–4.27× 与 LP 2.0× 警示前置入摘要）；贡献列表 6→4 正项 + 独立"Negative results we report"段；总页数 21→20 达标；Table 6 折叠（账目完整，R1 逐格核对 3+15+2=20 枚举完备互斥）；新增组合下界段（error ≥ 1−m/C，0.289/0.304，R1 独立验证成立）——作者主动陈述自己的 headline floor 在最粗档被一行类计数论证支配，并把价值主张正确重述为"带置信水平的逐对证书，而非更小的数"，被 R1 称为"十一轮里最有力的一次诚实自审"；M153 参考文献回归（中间构建曾静默丢失全部文献表）在提交 PDF 中确认修复（64 条全渲染、零未解析）；第四轮源级引文残留全部清零；§3.8 新增 Seeds and replicates 段使确定性声明范围精确（bootstrap/校准明确排除在外）。R1 的承重数字全量回归扫描零陈旧零异常。重构同时引入一组**编辑级新缺陷**（无一触及数值），构成本轮 must-fix 清单，其中最重要的是两处"轮间事实性反转"需以工件裁决。

## Strengths（三方一致）
1. **组合下界的自我披露**：主动印出被一行论证支配的事实并正确迁移卖点——测量论文自我审计的范本（R1 验证数学成立；R2 评为"本轮最佳新增"）。
2. **重构响应了此前审计的每一条而无一处稀释**：摘要双口径以对作者不利方向前置；贡献瘦身把"界定主张边界的发现"与"贡献"显式分栏（"bound the paper's claims rather than extend them"）。
3. **溯源链条完整收尾**：7 对文件名+哈希（含 9821af mislabel 修复）、fd1598/f27ba9 内联哈希、seeds 段、Table 6 折叠格逐一列名、非连续标签文档化。
4. **Track fit 范本级**（R2 专项）：预注册、校准表、内容寻址、负结果显式——为 Security Measurement Studies 评审池而生的论文。
5. 大改版下回归面依然干净（哈希、时间戳、伦理、匿名、GPU 泛化全部完好）——"这并非默认结果"（R3）。

## Weaknesses — 投稿前 must-fix（全部句级，不动任何数字）
**M1 — 悬空引用 + 浮动漂移包（同一次未完成改写的两半，三方同见）**：§4.5 p10 "(… the full control figure is Figure 5a, in Section )." 空 \ref + 孤立括号（M153 同类静默构建缺陷）；同时 Fig 4（§5.1 主要证据）与 Fig 5（负结果图示）漂移至参考文献起始页（p17）之后的 p18，Table 6 在 p19 夹于文献页间——承重图落在评审"不必阅读"区，损害正文自足性（R3 论证，R1 交叉后从 minor 升级采纳）。修法：\FloatBarrier 收拢或将 Fig 5 明确定位为附录图并软化正文引用；p14 Ethics 页约 53% 空白（视觉检查量化）是现成吸收空间。
**M2 — 摘要 power caveat 被删（RT-W14 部分回归，R1 捕获）**：Round 9/10 摘要的 "and the test has limited power to detect a two- or three-point excess" 在 330 词重写中消失；且删除后存留的 "no **gross** violation" 中 "gross" 失去语义支撑，快读者会读成 "no violation"（R2 补充论证并坦承其核对清单漏检）。恢复半句。
**M3 — Provenance 唯一化包：两处轮间事实性反转须以工件裁决**（本轮最重的实质项）：
 ① **构造关系反转**：R8–R10 议定文本"三构造同源单路径，一致性是单路径稳定性而非独立确认"→ 本轮"三构造结构互异（LP 权重优化/混合联合界/先验因子论证），0.363 相等是值的巧合，聚簇于 0.37 是该证书族天花板的证据"。两定性互斥，反转方向对作者有利。须由 f27ba9（four-construction note，哈希 0ace3222 已印）裁决；若新读法成立，须加共同输入 hedge——三构造消费同一 εhi 向量，共享输入误差驱动的一致性无法排除（推导独立 ≠ 输入独立）。
 ② **下侧输入描述反转**（R1 独有发现）：R10 文本（R7-W6 wontfix 被接受的依据）"下侧作用于分类器特征**而非**打包符号字母表"→ 本轮"计算于上侧所消费的**同一**打包符号的 one-hot 编码，(4) 的两端点陈述同一对象"。互斥；以 ledger 实际特征列为准。若新读法成立，同段保留的 "no M to vary on it" 辩护存在张力（M 变⇒符号变⇒one-hot 变），需一次性理顺。
 ③ §1 负结果段与 §4.5 修正后的定性同步："heterogeneous-i.i.d. **null** … emits **independent** bits" 在 §4.5 新读法（条件独立但边际不独立，Var(θ)>0；是依赖的替代机制而非排除它的 null）下是错误陈述——一词+一短语修复。
 评审组注记：两处反转很可能是**修正**（新文本内部更强），但在 R9-W5 快照争议的先例之后，"轮间朝有利方向改变的散文"必须由工件裁决而非信任；两个仲裁物都已在溯源链内，response letter 应直接引工件内容作答。R3 为此收回了自己"按澄清升级关闭"的记录（自我修正在案）。

## Shepherding 级（非阻塞）
结论校准句（第三轮缺席——"certification-grade" 的实测支撑在 §7 零出现）；§3.1 段内自引；可选摘要组合下界从句（预先解除最自然的审稿人质疑）；视觉检查项（p14 半空页、p3 前无图表、p11/p18 图堆叠且 caption 相邻易误读、Table 6 caption 长于表格）。
**Fig 1 处置**：五轮追踪后按评审组决议记 **wontfix**（美观项不再占用追踪器；作者可在 camera-ready 自行放大——视觉检查仍会标记）。

## Reviewer Consensus
全部实质发现三方 [AGREE]；must-fix 四项均为三方并集且修法收敛。交叉阶段三处自我修正记录在案：R2 坦承摘要限定词清单漏检 power caveat、坦承对 §3.4 只评估了新文内部质量未做轮间 diff；R3 收回构造关系句的关闭改记待裁决——"改写方向有利于作者时，恰恰是最需要对照前轮文本与工件的时刻"。

## Reviewer Divergence
无未决分歧。Fig 4/5 漂移的定级差（R1 minor → 交叉后采纳 R3 的 warning 论证）以 R1 被说服升级告终。

## Questions（须作者在修复中回答）
1. f27ba9 的 four-construction note 记录的是"同源单路径"还是"三个结构互异的论证"？（M3① 的裁决问题。）
2. ledger 中下侧的实际输入特征列是什么——分类器特征还是 packed symbol 的 one-hot？（M3② 的裁决问题。）
3. 摘要 power caveat 是否恢复？§1 "null" 是否同步？
4. 悬空引用的本意目标（推测 A.4）与 Fig 5 的最终归属（正文收拢 vs 附录图）？

## Missing References
无新增必引。64 条覆盖完整；本轮 0 幽灵（上轮 3 条 "not found" 确证为 API 瞬时误报）。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
本轮完成：0 critical / 4 warning / 4 info。warning：p14 仅 47% 填充（\clearpage 所致，是 M1 浮动收拢的现成空间）、p1–2 无任何图表锚点（首图迟至 p3）、p11 与 p18 图对堆叠且 caption 相邻易误归属。info：摘要块偏长、式 (2)(3) 排版局促、Table 6 caption 长于表格。全部并入 M1/shepherding。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：64/64 在线核查，0 缺失/孤儿/幽灵；luxemburk/缩写等源级项本轮已全部修复（第四轮清零）；17 条元数据不匹配均为既知 venue 变体噪声。
- **质量审计**：本轮未返回新报告（截至汇总时）。历史口径注记：R9/R10 审计均曾消费非提交快照，本轮评审全程以提交 PDF 为唯一权威对象；若迟到审计到达，其发现将按既定规则由评审对照提交 PDF 裁决后并入记录。

## Overall Assessment
**Verdict: accept（4.5/5，置信 4/5，附投稿前 must-fix 短清单）**。
重构的净方向是十一轮中最有力的诚实性增强：组合下界自我披露、负结果独立成段、双口径摘要、溯源链完整收尾，且数值层三方复核零缺陷。剩余工作是"把重构的最后三处断头接完"（R2）：M1 悬空引用+浮动收拢（一次改写）、M2 power 半句、M3 两处反转的工件裁决与唯一化（本轮唯一实质项——不是因为新文本可疑，而是因为轮间有利方向的改写在本项目的先例下必须以工件为准）。全部修复句级、一次小编辑可完成。评审组一致建议：**accept；完成 M1–M3 后即可投稿**。距截止 2027-01-26 时间充裕。

## Detailed Comments（分节）
- **Abstract**: 双口径+LP 警示+certified-or-not 到位；M2 power 半句恢复；可选组合下界从句。
- **§1**: 贡献 4+负结果段结构正确、支撑齐全；M3③ "null/independent bits" 同步。
- **§3.1**: 组合下界段（验证通过）与双哈希内联为本轮亮点；M3① 构造关系裁决 + hedge；段内自引微修。
- **§3.4**: M3② 下侧输入唯一化 + "no M to vary" 张力理顺。
- **§3.8**: Seeds 段——确定性声明范围精确，实质增强。
- **§4.5**: 异质 arm 的数学修正方向正确（Var(θ)>0）；M1 悬空引用在此。
- **§5.5/Table 6**: 折叠账目完整（枚举经逐格核对）；Table 6 浮动位置随 M1 收拢。
- **§7**: 校准句第三轮缺席（shepherding）。
- **References/Open Science**: 64 条完整渲染（M153 关闭）；7 对哈希正确；provenance 链完整。
- **图件**: Fig 4/5 收拢（M1）；Fig 1 记 wontfix 终结五轮追踪。