---
round: 8
review_mode: fresh
overall_score: "weak accept (4/5, minor revision)"
score_value: 4.0
score_max: 5.0
score_label: "weak accept (4/5, minor revision)"
verdict_canonical: "weak accept"
verdict_raw: "weak accept  , minor revision)"
timestamp: 2026-09-17T22:54:53.578541+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 8 评审汇总报告
**目标会议**: USENIX Security 2027 Cycle 2（Research Track；注册截止 2027-01-19，投稿截止 2027-01-26 AoE，未过期；正文 ≤13 页不含参考文献/附录，双盲，Open Science 附录强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛；唯一评审间分歧（披露句处置）已在交叉阶段以折中方案解决
**评分**: R1 4/5（方法+实验，置信 4/5）· R2 4/5（新颖性+相关工作，置信 4/5）· R3 3.5/5（格式/伦理/复现职责内，置信 4/5）→ **合并 4/5，weak accept（minor revision）**；上轮 3/3/4 → 本轮 4/4/3.5

## Summary
第 8 轮修订实质性修复了 Round 7 的全部四项 critical，且修复路径全部选择了更诚实而非更取巧的表述：floor 0.186 改为期望语义、全 990 对求和明示、i.i.d. 限定回归摘要、εhi 截断声明（29 对触顶）；"consistent with the bound, not evidence for it" 的 DPI 方向修正；LP 聚合对照 0.363 入文并把 4× 松弛分解为聚合项（~1.95×）与信道残余（~2.0×），配合同源推导线披露关闭选择性报告风险；WeFDE 及聚合下界文献补引且区分轴精确；搁置六轮的上侧 coverage 校准首次以测量入文（R4-W7 实质关闭）。R1 复算全部承重数值通过（含 Mmax 闭式独立重导、LP 在 M=2 的归一化检查），无遗留数学错误。本轮唯一阻塞项是**校准与 LP 的可复核性缺口**（判据未印、设计参数与 artifact 双缺失），为文本+注册级修复，无需新实验。

## Strengths（三方一致）
1. **修复纪律与诚实度**：0.05 阈值 "was never pre-registered" 如实印出；同源推导线降权自证；LP 对照主动把自己的 headline 松弛从 4× 揭到 2×；每处修复均可独立复核且复核通过。
2. **clear-accept 门槛（R5-W7）判定达标**（R1、R2 独立收敛）：coverage 校准是测量增量而非措辞修补 + LP 定位 + Mmax 闭式（A.4，推导正确）。R3 附带条件：承担门槛角色的校准必须先补齐 provenance（即本轮 R8-W1）。
3. 正文在净增内容后经实质删减仍恰守 13 页；回归面干净（哈希、时间戳、伦理段逐字符完好）；新增引文 [4][27][45] 在线核实真实准确。
4. WeFDE 区分句把 novelty 声明锚定在可检验的真实差异上（MI 点估计 vs 带水平的双侧区间），novelty boundary 现在是干净的。

## Weaknesses
**[Critical] W1 — 校准与 LP 的可复核性缺口（本轮唯一 critical，三职责合流：R1-N1 ≡ R2-W1 ≡ R3-N2 + R1-W4 ≡ R2-W2）**：
(a) §5.5 的 "breach" 判据未印出，且与自印数字在自然读法下矛盾——被标为"破界"的两个 cell 是 4/200（覆盖 0.980）与 1/200（0.995），点覆盖率**均在名义 0.975 之上**；R1 与 R2 用两种自然读法对同一组数字得出不同判定（R3 指出：这本身就是判据必须印出的最直接证明）。唯一自洽读法是 Clopper–Pearson 95% 下界跌破名义的**确认丢失**（4/200→0.9496；1/200→0.9724；iid 0/200→0.9817 保持）——严格说是 confirmation loss 而非 degradation，且诚实版本对作者更有利。
(b) 设计参数全缺：生成器、TV/n/block 网格、cell 总数、informative 定义。
(c) 功效边界未声明：200 重复对 2–3pp under-coverage 基本无检出力（与 §4.4 自报功效的做法文内不一致）。
(d) provenance 零条目：Open Science 的 worked example 三个哈希与上轮逐字节相同、Released artifacts 未增列；LP floor 0.363 既无印出规格（目标、约束、含 U 与否、求解 M、max-over-weights 有效性一句）也无 artifact。本轮唯二新增承重数字恰好都退出论文自设的溯源标准，artifact evaluation 阶段必暴露。审计补充：§5.5 还遗漏了 B=64 最大 n 处覆盖 0.980 低于名义且 CP 排除名义的 cell——正是正文自己预言的失效方向。
**修复**（纯文本+注册级）：印判据；附录一张校准表（arm × cell：生成器、TV、n、block、出界数/200、CP 区间）；功效一句；LP 规格三行；两个 artifact 注册并列入 Open Science。
**[Warning] W2 — 结论句方向性回退**：§7 "puts an … floor of 0.186 under any classifier on the same services" 丢信道限定——由 DPI 细信道 floor 可低于 0.186，故对细观测检测器它不是有效下界；审计另核结论句同时丢 uniform-prior 与 i.i.d. 限定。§3.1 的 "so the inequality holds for any detector" 是同一缺陷的预演，一并删改。结论句是被引用率最高的句子，必须修。
**[Warning] W3 — 期望语义是标签不是引理**：印出两句失败预算（每对失败概率 ≤0.025、截断限超额 ≤1 ⇒ E[Ŝ]≤S_true+24.75，floor 期望高估 ≤0.012；radius 保守性可使 E[Ŝ]≤S_true 径直成立）即闭合。R1、R2 推导一致。
**[Warning] W4 — M 配对错位**（R1 独有发现，R2/R3 复核确认均自认漏检）：0.186 是 M=46 开集 floor，0.737 是 45 类闭集误差；匹配配对 384.55/1980=0.194、3.79×。保守方向、比较不塌，但 "4×" 中约 4% 来自配对而非聚合/信道。声明配对或双报。
**[Warning] W5 — "nearest margins are far from the boundary" 与自文矛盾**：capped 约定下 (21,23) 的 εlo=0.0498 距阈 0.0002（正是单对翻转对）；full-n 最近 margin 0.0073。删 "far"，印出两约定最小 margin。
**[Critical，R3 职责口径] W6 — 图件五处缺陷连续第二轮未修**：图字节与上轮相同——Fig 2a 主结果图 "33.9\%" 转义泄漏、Fig 3b y 轴截断、Fig 1 打印不可读、Fig 3c 拥挤、y 轴刻度。Open Science 自称 "Scripts rebuilding every figure from its artifact"，五处均为脚本级半小时工作；"承诺修复未执行"的流程回归信号比缺陷本身更重（R1 背书此定性）。
**[Minor 批次]**：[6] Le Cam 排序仍错（源码 brace 未修，连续第二轮；luxemburk 缺 author、4 处缩写未保护——源码未修、渲染无碍的口径已统一）；§2.3/§6.2 近逐字重复（同时是 R8 修复的页数预算捐赠源，压缩可释放 ~0.15–0.2 栏）；R7-W6（M≥2 下侧）、R7-W16（软引用）、R7-W17（k=20,25）、R7-W18（RTX 5090 D）四项连续第二轮无处置，评审组要求明确 disposition（修/说明/wontfix）；Fano 无引文；Table 2 caption accept-H0 影子；"the panel" 先用后定义。

## Reviewer Consensus
全部实质发现三方 [AGREE]；上轮四 critical 的修复确认三方一致（R1 数值复核 + R2 framing 同步核对 + R3 文字面 12 项逐条打勾）。修复清单收敛为六项文本级工作（W1 判据+表+artifact；W2 结论句限定；W3 期望引理；W4 配对声明；W5 margin；W6 图件重生成）。

## Reviewer Divergence（已解决）
唯一分歧：§3.1 "three normalisation errors before they were caught" 披露句——R2 视为诚实资产（关闭虚假三重确认误读，且是其上轮的明确要求），R3 判为内部过程叙事应删。R1 裁决 + R2 附议的折中被三方接受：**保留认识论内容、删除 debug 叙事子句**，改写为 "our stronger constructions share a single derivation line, so their agreement is one route's stability rather than independent confirmation"；构造数值与 artifact 归入 W1 修复（现状"叙事在场、证据缺席"是最差组合——R3）。

## Questions（需作者回应）
1. §5.5 的 breach 判据确认：是 "CP 95% 下界 < 0.975" 吗？请印出；若不是，请解释 4/200 如何构成对名义 0.975 的 breach。
2. 校准的生成器与 TV/n/block 网格？多少 cell 因 cap 排除？校准与 LP 的 artifact 将以何名注册？
3. LP 聚合含 U 类吗？在哪个 M 下求解？三个更强构造的 floor 值为何不印出？
4. 是否愿意印出期望语义引理（W3 的两句版本）？
5. M 配对：声明 0.186/0.737 的配对选择，或双报 0.194/3.79×？
6. 图件重新生成有无阻碍？RTX 5090 D / 主机规格披露：keep 还是 genericize（要求明确决定）？

## Missing References
无新增必引项（上轮三条已全部入文且核实准确）。唯一建议：Fano 不等式补原始引文或 Scarlett–Cevher（"Fano and Henze–Penrose type bounds [4,45]" 中 [4][45] 均为 HP 线）。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
独立视觉检查本轮完成（上轮出错后重派）：1 critical——Table 1 顶置 p8 使双栏参差、右下留白，且这是头条结果表所在页（建议浮动至 p7 首引处或平衡栏高）；2 warning——p3 前无任何图表锚点（Fig 1 在 p1 被引、p3 才出现）、p9 约 55% 为表格读感如数据堆砌；6 info（Fig 1 0.94 栏宽字号偏小——与 R7-W13 重合、refs 起始无分隔等）。已并入追踪器 R8-W9。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：63/63 在线核查（+3 为上轮要求的补引），0 缺失/孤儿/幽灵/撤稿。luxemburk 缺 author 与缩写保护为上轮遗留未修（源码级）；16 条元数据不匹配多为 venue 变体。
- **质量审计完成**：4 critical（2 内容 + 2 源码格式）/ 80 warning / 8 info，较上轮 6 critical 显著改善且无数值级缺陷。2 项内容 critical：结论句丢限定（已由评审裁决，入 W2）、headline 定位漂移（摘要/结论以 floor 领跑 vs 引言埋于 bullet 1 从句——未经评审独立裁决，记 R8-W8 供作者取舍）。审计的 §5.5 低报发现（B=64 最大 n 低于名义 cell 未报）已并入 W1。

## Overall Assessment
**Verdict: weak accept（4/5，置信 4/5，minor revision）**。
Round 7 的全部四项 critical 在一轮内按正确方式修复且经三方独立验证，无遗留数学错误；clear-accept 门槛（R5-W7）由 R1、R2 独立判定达标。相对上轮 borderline 3/5 的上调完全由修复质量驱动。距离 accept 的剩余距离是一个收敛的 minor-revision 清单：核心是 W1（校准判据+设计表+artifact 注册 + LP 规格——文本与注册级，无需新实验，且诚实版本对作者更有利）、W2 结论句一行、W3 引理两句、W4/W5 各一行、W6 图件脚本级重生成。R3 的 3.5 分反映其职责内两项执行性缺口（图件连续未修、provenance 缺席）；其对门槛判定的附带条件（校准 provenance 先行补齐）已纳入 W1。页数预算已有明确方案：§2.3 压缩为捐赠源，校准表入附录不占正文。若下一版完成 W1–W6，评审组预期评分收敛于 accept。

## Detailed Comments（分节）
- **Abstract**: 四要素修复确认（期望语义/990 对/i.i.d./consistent-with）；审计指 "because" 因果搭接与 scarce 措辞两处漂移（R8-W8，作者取舍）。
- **§1 Contributions**: headline 定位（floor 领跑 vs 从句）需二选一（审计，R8-W8）；两 bullet 同节指向。
- **§3.1**: W3（期望引理）、W4（M 配对）、W5（margin）、LP 规格（W1d）、"holds for any detector" 删改（随 W2）、披露句按折中改写（R8-W5）落点。
- **§3.3/§5.5**: R4-W7 六轮后实质关闭；W1 的判据/表/功效/artifact 是本轮核心修复。
- **§4.2**: R7-W6（M≥2 下侧）连续第二轮无处置，要求明确 disposition。
- **§7 Conclusion**: W2 方向性回退，一行修复，最高优先级之一。
- **§2.3 vs §6.2**: 近逐字重复，压缩 §2.3 并作为页数捐赠源。
- **References**: [6] Le Cam brace（第二轮）、luxemburk author 字段、缩写保护、[24] 数学体。
- **图件**: 五处脚本级重生成（W6）+ 视觉检查的 Table 1 浮动与 p9 密度（R8-W9）。
- **附录/Open Science**: 校准表与两行 artifact 条目为 must；RTX 5090 D 处置决定；起新页排布 minor。