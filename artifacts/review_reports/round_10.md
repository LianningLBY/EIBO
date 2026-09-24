---
round: 10
review_mode: fresh
overall_score: "accept (4.7/5, camera-ready conditions only)"
score_value: 4.7
score_max: 5.0
score_label: "accept (4.7/5, camera-ready conditions only)"
verdict_canonical: "accept"
verdict_raw: "accept  , camera-ready conditions only)"
timestamp: 2026-09-18T02:52:53.807283+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 10 评审汇总报告（投稿前确认轮）
**目标会议**: USENIX Security 2027 Cycle 2（Research Track；注册截止 2027-01-19，投稿截止 2027-01-26 AoE，均未过期；正文 ≤13 页不含参考文献/附录，双盲，Open Science 附录强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛，零分歧
**评分**: R1 4.5/5（方法+实验，置信 4/5）· R2 5/5（新颖性+相关工作，置信 4/5——十轮首个 strong accept）· R3 4.5/5（格式/伦理/复现职责内，置信 4/5）→ **合并 4.7/5，accept（仅剩 camera-ready 条件）**
**轨迹**: R7 3/3/4 → R8 4/4/3.5 → R9 4/4.5/4.5 → R10 4.5/5/4.5；连续第二轮零 critical，本轮零新增缺陷。

## Summary
Round 10 将 Round 9 的 shepherding 清单以 8/8 的执行率落地：三处散文-数学方向词修正（LP "no larger"、U 类约束改写并显式论证弃项性质保持、预算引理指称与失败事件重写自洽）、§5.5 歧义括注删除、M 配对双报入文（0.194/3.79× matched 与 0.186/3.97× open-set 并列透明呈现）、披露句按 Round 8 议定折中逐字执行（debug 叙事删、同源降权保留、构造值 0.363/0.372 印出并注册）、校准 artifact 补齐 64-hex 哈希与 seed、Table 6 '–' 四列一致化、两个四轮悬案获书面 disposition（M=1 下侧为 reasoned-wontfix——下侧作用于特征空间、M 非其自变量；k=20,25 声明为链式实验网格的扩展）。R1 对 Table 6 '–' 落位用式 (6) 半径闭式逐格复算验证一致——校准表"不仅可复核，且已被复核"。三方一致：零 critical、零新缺陷，建议 **accept 并放行提交**，剩余四项为 camera-ready 条件。

## 快照争议的无责关闭（本轮程序性要点）
Round 9 报告与研究方就 M 配对句是否在文中存在分歧。本轮三方独立裁定完全一致：**Round 10 PDF 含**双报句（§3.1 p4，三方引文逐字相同，算术三方复算通过：384.55/1980=0.19422、3.795、4.274）；**Round 9 提交 PDF 不含**（三方各自的 Round 9 文本提取互为印证）。研究方所据为领先于 Round 9 快照的工作树。两边记录均忠实于各自读到的对象——按"提交 PDF 唯一权威"规则关闭，**不追责任何一方**。程序教训已记录：审计与评审的输入必须是提交快照。

## Strengths（三方一致）
1. **十轮收敛的终点是一份每个数字都可从文内或已注册 artifact 复核的测量论文**：判据、预算引理、LP 规格、构造阶梯（0.186/0.194/0.363/0.372）、校准全表（seed+哈希）、带符号 margins——"certification-grade" 的自我定义在文内自洽兑现（R2）。
2. **修复纪律完整闭环**：Round 8–9 议定的每一项（含对作者不利的方向词修正、4× 收窄为 3.79× 的 M 配对并报、debug 叙事删除但认识论内容保留）逐字落实，无一以稀释诚实性为代价。
3. **增量验证**：R1 的 Table 6 半径逐格复算（n=2791/10988/50953 → 0.163/0.0822/0.0382，与 '–' 边界完全吻合）补足校准链最后一环；披露句折中的执行同时消除了最后一处内部流程弱信号（R3）。
4. **Novelty boundary 干净**（R2）："不声明构件新颖、只声明组合与保证结构新颖，并把与最近先例的区分轴逐一写明"。
5. 交叉互评自我纠错在场：R2 主动撤回其 k=20,25 误报并具名自我批评（tracker 滞后于文本），三方证据链质量高。

## Weaknesses（无阻塞项，全部 camera-ready 级）
**(a) 页数计划**：总 21 页 > camera-ready 20 页限（提交合规）。唯一不触碰承重内容的削减路径：折叠 Table 6 的 15 行全同 200/200 行 + 文献微压。投稿前应内部记录方案，避免录用后仓促改动。
**(b) 溯源最后一毫米**：fd1598/f27ba9 两条 artifact 未印哈希——本轮新增的 "only the cited chain needs to be content-addressed" 自设标准恰好把被正文引用的 0.363/0.372 划进必须带哈希的范围（R3 的反衬论证，三方采纳）。并需一个从句澄清 LP 0.363 与 mixture 0.363 是同一对象还是巧合相等（三方独立同问；答案决定 LP 是否还缺独立 artifact 条目）。
**(c) 排版**：p15 一条 companion 哈希被断行机制渲染成逐字符空格（"7 c b 2 8 e f 9…"，视觉如损坏哈希）；[24] l1 数学体、luxemburk author 字段与 4 处缩写花括号（第四轮源码级遗留，渲染始终无碍）；References 起新页可选。
**(d) 可选改进**：图 1 放大——视觉检查本轮量化实测图内文字仅 2.1–5.1pt（对 10pt 正文），核心概念图打印下不可读（figure*/整栏 + ≥7pt 标签）；p14 近空页吸收；Table 1 table* 置放；结论加一句校准结果；摘要 "certified or not" 半句；y 轴范围。

## Reviewer Consensus
全部实质判定三方 [AGREE]，交叉零分歧。两条 Round 9 审计遗留观察均**裁决关闭**：(i) 摘要 336/340/990 指称——各有明确系词、§1 有调和句，至多低优先级 clarity；(ii) "destroying the certificate"——R1 与 R2 独立给出同一合取逻辑论证（上侧为空 ⇒ 联合 gate 必空，且句子主语本就是 "the upper-side set"），**无 over-claim，无需修改**。交叉阶段的三处小勘误（R2 的 k=20,25 误报撤回；Table 6 '–' 行数 3 非 5；可折叠行数 15 非 14）均为计数级，不影响任何结论。

## Reviewer Divergence
无。评分谱 4.5/5/4.5 无事实分歧，差异仅在剩余 minor 的职责计权（R1 明示页数计划与 LP 澄清落在其"提交就绪"门槛内侧，属信任作者完成级，不阻塞 accept 共识）。

## Questions（camera-ready 阶段向作者）
1. LP 解与 mixture 构造是否同一对象？（一个从句；决定 LP artifact 是否需单列。）
2. 21→20 页的削减方案是否已内部确定？（Table 6 折叠为首选。）
3. fd1598/f27ba9 哈希与 p15 哈希排版会一并处理吗？

## Missing References
无新增必引。本轮自动核验的 3 条"疑似幽灵"（eriksson2026unseen 等）经主席甄别与历轮多重在线验证记录比对，判定为外部 API 瞬时失败的误报，非论文缺陷。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
本轮完成：1 critical——图 1 图内文字实测 2.1–5.1pt，打印不可读（与评审组四轮的图 1 尺寸意见一致，首次量化）；4 warning——p14 近空页、Table 1 单栏挤压、p11 三图堆叠、首个图表迟至 p3；5 info（booktabs 规范、caption 自含、无溢出、无未解引用；参考文献 URL 边缘 +2pt 微出）。全部并入 camera-ready 条件 (d)。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：64/64，0 缺失/孤儿；3 条"not found"判定为瞬时误报（见上）；luxemburk/缩写为第四轮源码级遗留（渲染无碍），入 camera-ready 条件 (c)。
- **质量审计**：本轮未收到新的内容审计报告（上轮审计因输入过期工作树被降权；其两条遗留观察本轮已由评审从提交 PDF 裁决关闭，见 Consensus）。

## Overall Assessment
**Verdict: accept（4.7/5，置信 4/5，仅 camera-ready 条件）**。
十轮评审轨迹完整收敛：从 Round 7 的三项 critical（floor 记账、信道条件性、聚合定位）与 Round 8 的可复核性簇，经 Round 9 的零 critical，到本轮零新增缺陷、shepherding 清单 8/8 落地、快照争议无责关闭、审计遗留观察全部裁决。方法与严谨性侧无任何未决实质项；格式/伦理/复现侧具备提交条件。**评审组一致建议：accept，放行投稿**，附四点 camera-ready 条件——(a) 页数削减方案（投稿前书面确定）、(b) 两条哈希 + LP/mixture 一从句澄清、(c) 哈希排版与源码级引文卫生、(d) 图 1 放大等可选改进。距投稿截止（2027-01-26）时间充裕，建议在提交前顺手完成 (b)(c) 与图 1，使进入正式评审的版本不携带任何已知缺陷。

## Detailed Comments（分节）
- **Abstract**: 指称裁决关闭；可选半句（"certified or not"）。
- **§3.1**: M 配对双报、预算引理、披露句折中、margins——全部落地并三方复核；LP/mixture 关系一从句待澄清。
- **§3.4**: M=1 下侧 reasoned-wontfix 在场且被接受。
- **§4.3**: k=20,25 网格来源声明在场（R2 误报已撤回）。
- **§5.5 + Table 6**: 括注删除；'–' 四列一致并经半径闭式逐格验证；seed 印出；折叠待 camera-ready。
- **§7 Conclusion**: 信道/uniform prior/i.i.d. 三限定齐备；可选加一句校准。
- **A.5**: LP 方向词与约束修正在场；fd1598/f27ba9 补哈希待办。
- **Open Science**: "cited chain" 边界声明诚实；四条校准 artifact 带哈希；p15 一条哈希排版待修。
- **图件**: 图 1 放大是 camera-ready 首要视觉项（2.1–5.1pt 实测）；其余图缺陷保持已修状态。