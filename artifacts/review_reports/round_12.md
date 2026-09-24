---
round: 12
review_mode: fresh
overall_score: "strong accept (5/5, release for submission)"
score_value: 5.0
score_max: 5.0
score_label: "strong accept (5/5, release for submission)"
verdict_canonical: "strong accept"
verdict_raw: "strong accept  , release for submission)"
timestamp: 2026-09-18T14:23:00.807565+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 12 评审汇总报告（must-fix 核验轮 / 投稿放行轮）
**目标会议**: USENIX Security 2027 Cycle 2，Security Measurement Studies（注册截止 2027-01-19，投稿截止 2027-01-26 AoE，未过期；正文 ≤13 页，20 页上限仅 camera-ready，双盲，Open Science 强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛，零分歧
**评分**: R1 5/5 · R2 5/5 · R3 5/5（置信度均 4/5）→ **合并 5/5，strong accept——十二轮以来首次三方一致满分**
**轨迹**: R7 3/3/4 → R8 4/4/3.5 → R9 4/4.5/4.5 → R10 4.5/5/4.5 → R11 4.5/4.5/4.5 → **R12 5/5/5**

## Summary
Round 11 的三项投稿前 must-fix 在本轮 PDF 中全部落地，其中两处**超出议定范围**：
- **M1**（悬空引用 + 浮动漂移）：空 \ref 修复为 "in §A.4"（目标即上轮三方推测）；图序重排后全部浮动体位于 References 起点之前，A.4 增设 Fig 4/5 显式指引句，Fig 5 的附录归属与正文软引一致——正文自足性恢复。
- **M2**（摘要 power caveat）：恢复且位置使 "gross" 重获语义支撑，四限定词齐备；**超额**：摘要主动纳入组合支配披露（"That floor is not the tightest available… we keep the uniform form for its per-pair confidence semantics, not its tightness"）——R2："没有任何审稿人能提出作者未先自陈的质疑"。
- **M3**（两处轮间反转的工件裁决）：① 构造关系保留"结构互异/ceiling"版本，f27ba9+fd1598 哈希锚定，共同输入 hedge **超出要求**（额外披露 LP 权重本身由 εhi 计算——最紧构造与输入耦合最深）；② 下侧输入保留 one-hot 版本（双射论证成立），"no M to vary" 主动降格为诚实的 scope condition（"a computation we have not run, not one the construction rules out"——对 R7-W6 处置的第二次自我修正，每次朝更弱更准确移动）；③ §1 与 §4.5 逐词同步（§4.5 保留的 "i.i.d. null" 经 R1 辨析为嵌套比较零假设、不同对象、保留正确）。
**R3 档案比对（本轮关键增量）**：败方文本的四个短语（"share a single derivation line" / "one route's stability" / "three normalisation errors" / "operates on the classifier's features rather than"）在本轮 PDF 全文检索**零命中**——十一轮反复出现的"修复未回传/半更新表面"惯性模式首次被完整破除。R1 与 R3 的验证方向互补（新版到位 × 旧版清尽），M3 关闭完备。
另有两项长期追踪同轮清偿：结论校准句（第四轮）补齐，"certification-grade" 证据链在摘要-正文-结论贯通；摘要组合从句（可选项）超额采纳。R1 数值回归扫描零异常（含图重编号后逐处引用核对）。

## Strengths（三方一致）
1. **修复品质**：每项 must-fix 都选择最完整而非最省事的版本；§3.4 的修正轨迹（"合理理由"→"构造性论证"→"诚实的范围声明"）被 R1 称为"十二轮评审最有说服力的质量信号"。
2. **摘要终局形态**：headline 数字之后紧跟"不是最紧的、被一行论证支配、保留只为置信语义"——测量论文摘要自我限定的完整范本。
3. **溯源与回归面**：7 对哈希 + 2 内联哈希 + Seeds 段逐字符稳定；回归面连续五轮干净；裁决措辞无任何评审流程泄漏。
4. **十二轮终局状态**：每个承重数字可从文内推导或已注册工件复核；每个已知散文-数学分歧已闭合；每次修复朝对作者更不利的方向收敛。

## Weaknesses（全部一词/一句级 camera-ready 项，无阻塞）
(a) Fig 3 处理不对称（R1 发现，R2/R3 采纳）：正文承重图漂移至附录页 p17 但无 A.4 lead-in——加一句或浮动微调回正文页（R3 边界说明：它是"漂移的正文图"非"附录图"，两法均可）；视觉检查另记 Fig 4 首引 p8 印于 p17 的九页漂移，同一次浮动调参可一并处理。
(b) §3.4 两句 "evaluated at M=1 only" 轻度冗余——合并。
(c) §3.1 段内自引 "the LP of Section 3.1"——改 "below"。
(d) R3 备忘：最终版式若再动浮动，提交前重跑"浮动位置 vs References 起点"目检（此类缺陷对重排敏感）。
(e) 源码级 bib 卫生口径（主席裁定 R11/R12 记录差异）：自动核验持续报 luxemburk 缺 author 字段与 4 处缩写未加 brace（源码级）；R3 上轮"清零"记录系渲染层核验（样式掩盖源码缺陷，渲染与双盲始终无碍）。作为 camera-ready bib 卫生备忘，非缺陷。
(f) 留档的弃追踪美观项：Fig 1 尺寸（六轮）、y 轴刻度、p14 半页余白、p3 前无图表。

## Reviewer Consensus
全部裁定三方 [AGREE]，零分歧。M1–M3 关闭由三种互补方法共同支撑：R1 的修复文本与议定措辞对应性核验 + 全表面一致性核查、R2 的 framing 三件套裁决（artifact 锚定/hedge/限定）、R3 的档案比对（败方文本零残留）。R2 特别附议 R1 对 §4.5 "i.i.d. null" 的保留辨析——"防止了同步修复被过度应用到不该改的地方"。

## Reviewer Divergence
无。

## Questions
无阻塞性问题。仅向作者移交 camera-ready 清单 (a)–(e) 与备忘 (d)。

## Missing References
无新增必引。64 条完整渲染，0 幽灵（历史误报均确证为 API 瞬态）。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
本轮完成：0 critical / 5 warning / 8 info。warning 均为既知或美观类：p1–2 无图表锚点、Fig 1 图内文字偏小（caption 已重复其内容，可删图内字或放大）、p14 半页余白、Fig 4 九页浮动漂移（并入 camera-ready (a)）。info 含正面确认：Table 1 位置合理且 "–" 使用正确、参考文献 [1]–[64] 连续无 [?]、无页边溢出。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：64/64，0 缺失/孤儿/幽灵；luxemburk/缩写源码级标记见 camera-ready (e) 口径；其余为既知 venue 变体噪声。
- **质量审计**：截至汇总未返回本轮报告；若迟到到达，按既定规则（提交 PDF 唯一权威、逐条对照评审验证后采信）并入记录。

## Overall Assessment
**Verdict: strong accept（5/5，置信 4/5）——评审组一致决定：放行投稿，无需再核验轮。**
十二轮评审的完整弧线：从 Round 7 的三项 critical（floor 记账语义、信道条件性、聚合定位）与连续多轮的"散文快于证据"缺陷模式，经八轮迭代收敛至本轮零缺陷、零新漂移、败方文本零残留。这份稿件的最终状态在三个职责维度（方法可靠性/新颖性与框架/格式伦理复现）同时达到提交标准，其核心品质——每次修复都朝对作者更不利、更准确的方向移动——正是 Security Measurement Studies 评审池最看重的特质。剩余六项一词/一句级编辑随 camera-ready 处理，不影响投稿。距截止 2027-01-26 时间充裕；建议按 CFP 完成注册（2027-01-19 前，含 ORCID 与固定作者列表）后提交。

## Detailed Comments（分节）
- **Abstract**: 四限定词齐备 + 双口径 + 组合支配自陈——终局形态。
- **§1**: 负结果段与 §4.5 逐词同步；贡献 4 条支撑齐全。
- **§3.1**: hedge 三件套（artifact 锚定/共同输入/family 限定）落地；(c) 段内自引待改。
- **§3.4**: scope condition 降格到位；(b) 冗余句待并。
- **§4.5**: 空引用修复；"i.i.d. null" 保留正确。
- **§7**: 校准句补齐，三表面证据链贯通。
- **A.4/附录**: Fig 4/5 lead-in 在场；(a) Fig 3 不对称待齐。
- **References/Open Science**: 64 条完整；provenance 逐字符稳定；(e) 源码 bib 卫生随 camera-ready。