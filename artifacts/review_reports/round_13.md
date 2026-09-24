---
round: 13
review_mode: fresh
overall_score: "3.7/5 — accept on the science; submission NOT cleared pending five must-fix items (panel spread: R1 4, R2 4, R3 3 out of 5)"
score_value: 3.7
score_max: 5.0
score_label: "accept on the science; submission NOT cleared pending five must-fix items (panel spread: R1 4, R2 4, R3 3 out of 5)"
verdict_canonical: "weak accept"
verdict_raw: "accept on the science; submission NOT cleared pending five must-fix items (panel spread: R1 4, R2 4, R3 3 out of 5)"
timestamp: 2026-09-20T05:40:45.594714+00:00
reviewer_ids: [1, 2, 3]
cross_response_reviewer_ids: [1, 2, 3]
force_resubmit: False
---

# Round 13 评审汇总报告
**目标会议**: USENIX Security 2027 Cycle 2, Research Track（注册截止 2027-01-19，投稿截止 2027-01-26 AoE，均未过期；正文 ≤13 页不含参考文献/附录；USENIX 模板；双盲；Open Science 附录强制）
**评审组**: 3 位评审独立评审 + 全量交叉互评，1 轮收敛；三方在全部事实层判定上收敛
**评分**: R1 4、R2 4、R3 3（满分 5；置信度均 4）——合并 3.7
**合并判定**: **科学判定三方一致 = accept；提交资格判定 = 未通过**（卡在两处提交阻断缺陷）。采纳 R2 提出的记账口径，使机械缺陷不被读成科学退步、格式侧阻断也不被科学侧乐观稀释。

## Summary
本轮是十三轮评审中**科学增量最大**的一次，且三方独立复算全部通过：新增的无字母表界式 (9)（单集合 Hoeffding 路线）推导完整正确，与式 (6) 的常数一致性是代数恒等（½√(2ln(2/α)/n) = √(ln(2/α)/(2n))）；2.9× 比值（0.081557/0.028018）逐位吻合；**Table 3 与 Table 5 的二十格交叉验证逐格一致**，证明两表出自同一 ledger；LP 的均匀可行点本轮修正为 1/[2(K−1)]（正确——R10 时期写作 1/[2(M−1)] 是错的），并显式给出两种正常化的比值 (M−1)/(K−1)=45/44 与 "about 2%"；规划推论的 C=2ln(2/α_law)=8.764 与"线性套用低估 2.96×"均正确。科学上最有价值的产出是**两机制分工**：粗端由字母表价格束缚、细端由 btv 饱和束缚（k=30 时 597/820 对 ≥0.99、中位数 0.9979），从而得出"移除字母表价格并不溶解视野"——R1 称此为十三轮最强的一次自我修正，且与 Security Measurement Studies 的定位高度契合。
**但同一轮改版引入了一组机械缺陷，其中两处为提交阻断级**：五处交叉引用在渲染 PDF 中完全为空，以及 Open Science 强制附录内一个未填的仓库 URL 占位符。另有两处新内容与论文自己的表格直接冲突（"from M=8 on 为零"被 Table 5 证伪；§3.1 的"阈值不敏感"被同段新增的 Table 6 反驳），以及一处三方会核新发现的等式方向错误（LP 行和恒等式应为不等式）。

## Strengths（三方一致）
1. **科学增量且全部经独立验证**：式 (9) 的推导、常数恒等式、2.9×、Table 3↔Table 5 二十格交叉验证、LP 可行点修正、阈值敏感性表、依赖感知半径、覆盖机制段——R1 逐项复算，R2/R3 复核无异议。
2. **自我修正的诚实延续**：主动写"We first attributed this to the radius, and that attribution was wrong"（R1 明确为其辩护：这是作者自己的假设史，先说出读者最自然的猜测再证伪，是本稿一贯手法，应保留）；§5.5 明写"未在真实流量上测覆盖"；§4.3 的新内容明言 (9) 是"route choice, not a new theorem"且不换掉 (6) 做 headline。
3. **覆盖研究从"缺口"升级为"机制"**：400 重复阶梯把失覆盖定位为加厚的左尾而非中心偏移（阈值 0.339–0.374 对真值 0.400 亏空 6–15%、中位数保持 ≥0.400；n=60k 后覆盖平台于 0.9825 而半径仍在缩 0.0352→0.0263），据此给出"修半径无用、需改估计器"的结构性结论。
4. **§4.4 新增独立性告诫**（R1 多次要求的"检验与功效必须诚实"落地）：明说 340 对当独立抽样不成立（43 个服务、最大对度 27），p 值因此反保守。
5. **溯源面、伦理面、匿名面在改版后保持完好**（7 对哈希 + 2 内联哈希 + 新增构造 note 条目 + Seeds 段）；R3 确认无匿名违规。
6. **§6.1 对 Liu et al. [31] 的三表面同步修正**执行干净（把"i.i.d. 才成立"的过强论断改为"其推论才需条件独立"），且仍守住与本文的区分。

## Weaknesses
### 提交阻断级（P0，必须提交前修复）
**C1 — Open Science 未填占位符**（三方独立发现）：p15 印出 "...will additionally be made available through an anonymous repository at **[ANONYMOUS-REPO-URL-TO-INSERT]**"。Open Science 是 USENIX '27 强制附录，占位符落在其中是硬性提交缺陷。方向注记：上一轮该句是"不提供匿名 URL 以保双盲"，本轮改为承诺提供（方向正确，USENIX 鼓励），但承诺的是占位符。二选一：填入真实匿名仓库（anonymous.4open.science，会议 ID "SEC27" 是 USENIX 推荐路径），或回退到不依赖外部 URL 的表述（仅投稿系统内提供）。
**C2 — 五处交叉引用渲染为空**（三方独立发现，位置与目标一致）：§3.7→A.5、§3.9→A.8、§4.1→A.3、§4.5→A.5、§5.2→A.5（且缺右括号）。非 "??" 而是节号完全缺失；成因是附录整体重编号为 A.1–A.9 未回传。属 M153 缺陷类（构建不报错、PDF 看似正常、读者才看得到破损）；R11 一处、R12 零处、本轮五处。**验收须做全量扫描**（"Section|Table|Figure + 空格 + 标点"），而非只补这五处——重编号历史上会留下"能解析但指向错误"的第六处。

### 陈述-数据冲突（P1，读者可自行核对）
**W1 — "from M=8 on 为零" 过宽，被 Table 5 证伪**（三处同现：摘要、贡献 2、§4.3 "at every k"）：Table 5 的式 (9) 列 M=8 为 94/6/0/0、M=16 为 80/5/0/0（k=5,10,15,30）。R1 的精化（R2 采纳）：实质主张对 k=15 的 frontier 延伸为真（k=15 列为 18/4/1/0/0，从 M=8 起为零），错的只是限定语 "at every k"。R1 另指一处反向风险：按字面读 "the advantage does not generalize in M" **低估**了 (9)（固定 k 下优势随 M 强烈存在——M=8,k=5 时 (9) 认证 94 对而 (6) 为 0）。修法："the extension at k≥15 does not generalize in M"。R2 的警示值得记录：R3（职责不在此）此前已把这句当优点复述过——"一句错误的自谦式限定同样会被读者接受，这恰恰是它必须改的理由"。
**C3 — §3.4 / §4.2 / Table 3 标题三面对 M≥2 下侧的三方矛盾**（R1-N3 = R2-W4）：§3.4 称 M≥2 是"a computation we have not run"；§4.2 报 M=2 下侧行为（"both counts are 127"、"the smallest lower bound among the 127 is 0.0755"）；Table 3 标题称 "joint gate is defined at M=1 only"。至多一真。**R1 的更锐利诊断（R2 采纳并撤回自己较温和的表述）**：§4.2 那句**混用了两条路线且未标注**——127 = 式 (9)@(M=2,k=5)（而 Table 3 同格式 (6) upper 是 47）、98 = 式 (9)@(M=1,k=10)（而式 (9)@(M=2,k=10) 是 20）；排比句会让读者把 98 读成 M=2/k=10。R1 的支撑证据："the smallest lower bound among the 127 is 0.0755" 只有真在 M=2 上算了下侧才可能得到（M=1 的最小值是 0.0151）。**这同时是 R7-W6 四轮悬案的答案**：下侧确在 M≥2 算过，§3.4 与 Table 3 标题都未跟上。修复须一次性完成三件事：逐句标注路线、对齐表标题、对齐 §3.4 范围声明。
**W2 — §3.1 "阈值不敏感" 被同段新增的 Table 6 反驳**（R2 独有捕获，R3 称其为"本轮最尖锐的文本-数据冲突"，R1 降级为 should-fix 因同段末句已自带更正）："The 336/990 and 340/990 counts are insensitive to small threshold movements" 与紧随的 "113 to 748 across 0.30–0.80" 并置冲突（Table 6：0.5→0.6 使计数 336→454，+35%；0.4→0.5 使 221→336）。真正惰性的只有下侧阈值在其邻域（0.01–0.10 内 ≤20）。修法：删去陈旧从句，保留正确表述。

### 三方会核新发现
**W3 — LP 行和恒等式印成了等式，应为不等式**（R2 提请、R1 会核确认、R3 从渲染文本独立佐证）：印出的约束 r_i = Σ_{j≠i}(w_ij+w_ji) = 1（K 个已知类）、0（未知类）。于是 Σ_{i≠j} w_ij(err_i+err_j) = Σ_{i∈known} err_i，而 M·E[err] = Σ_{all} err_i = Σ_{known} + err_U。故印出的 "= M E[err]" 成立**当且仅当 err_U = 0**，而 err_U ≥ 0 一般不为零——这正是式 (3) "丢弃未知类项只削弱界"所承认的。**正确关系是不等式**：Σ_{known} err_i ≤ M·E[err]；a-fortiori 论证在该方向下完好，**LP 的有效性与 0.363 值均不受影响**，只是印出的理由句写成了等式。R1 的家族定位值得记录：这与 R9 的 "no smaller/no larger" 属同一缺陷家族，且是 R12 那次修复（把 U 类行和从"未言明"改为"显式 =0"）引入的新不一致——旧版含糊，反而没暴露这个等号问题。修法：一个符号（= → ≤）+ 半句（复用式 (3) 已有的弃项论证）。

### 其余应修（P2/P3）
**W4** A.7 的 "that 0.0029 gap" 先行词不明且与其归因互斥（0.9809−0.975=0.0059 是设计目标−名义；0.9809−0.9780=0.0029 含一分覆盖亏空，与"design 的属性、非覆盖失效"的归因矛盾）。
**W5** A.7 两条"不同"半径形式（z- vs Studentized t）给出逐位相同的覆盖区间 0.9780 [0.9669,0.9862]（1000 重复）——相同成功数导致相同 CP 区间是必然的，但两个不同半径形式产生完全相同的成功数需解释；论文三十行前刚为 0.363 的相等给出"派生独立但输入共享"的 hedge，此处标准不一致。
**W6** §4.4 "43 distinct services" 与全文 45 services/990 pairs 未调和（43 是 informative stratum 覆盖的服务数）。
**W7 [provenance 退化，R3 独有]** 本轮多个新定量载荷脱离论文自设的 manifest 标准（§5.5 的 400 重复阶梯、A.7 的三条依赖半径与 5000 重复随访、A.7 规划网格、A.6 阈值表、§4.3 "3000 draws"）——对照 Table 5 的 (9) 网格已接链，"同一轮新增的载荷里有的接了链、有的没接"；与 R8 报告的同类缺口是同一模式重演。
**W8** §A.4 是空壳节（标题 p17、表浮动到 p20，连一句引导语都没有）。
**W9 [自足性]** 正文 p1–13 已无任何表格、仅含 Figure 1，主结果表 Table 3 落 §A.4(p20)——对测量论文是结构性弱点；表号非单调且按出现顺序而非重要性编号（正文遇 "Table 1" 实为附录边界对表）。建议主结果表关键行回正文、主表优先编号。
**W10** fd1598（LP artifact，正文引用）未列入 Open Science 清单；且同一对象在 §3.1 称 "the four-construction note"、在 Open Science 称 "Aggregation-constructions note"——两名一物。
**W11 批次**：(a) §1 把 Cherubin 压缩为 "bound its sign" 定性不准（是量化界，且是全稿唯一一处把最近先例说得比实际更弱——与本文"宁可把先例说强"的纪律相反）；(b) A.7 "A follow-up asked…" 与 "the obvious objection" 在首次投稿中无指代对象（R3 确认不构成匿名违规，因未点名任何场域），改读者向表述；(c) **R1 部分反驳**：§4.3 "We first attributed this to the radius, and that attribution was wrong" **应保留**（作者自身假设史，本稿一贯手法）；(d) §4.4 "the cell above" 点名；(e) 摘要 "two-point" vs §4.4 "two- or three-point" 统一；(f) §4.3 "3000 draws" 无设计说明与 artifact；(g) 总 23 页，camera-ready 需削 3 页——R3 排序方案（A.7 与 §5.5 重叠段合并省约 0.8–1 页、A.6 压缩、主表精简版回正文、文献压缩），投稿阶段附录不限长故不阻断，但应书面定案；(h) Open Science 的 "no adversarial risk" 与 §5.6 dual-use 自述并列时自相矛盾，限定为"发布这些 artifact 本身无对抗风险"。
**W12 [solver 固定再现，R1 独有]** Seeds 段只 pin 了 random_state=0，未 pin solver 与 penalty——而本项目已确认（L8-W2/C052）未固定的 sklearn solver/penalty 曾使 593/990 行跨代变化而中位数与 gate 计数不变。§4.2 新增的 "both counts are 127" 正是"两侧计数相等"这一曾证明脆弱的判据形态。建议把 sklearn 版本/solver/penalty 记入 ledger 与 gate artifact（增量记录，不动任何已发表数字）。
**W13 [引用依赖的 novelty 声明]** §2.2/§6.1 对 Liu et al. [31] 的重新定性（"其假设允许相关与非平稳，条件独立只入其推论"）是 novelty boundary 的论据之一，须随提交做一次全文级 refs 核对。
**W14** 式 (9) 的两事件偏离论证无引文（全稿归因纪律在此断链），建议指 Tsybakov [52] 并连一句 closeness-testing [6,12]。

## Reviewer Consensus
全部 P0/P1 项三方 [AGREE]。三处三方互证：C2 的位置与目标映射三方独立一致；W1 的取证三方一致（R1 与 R2 均引 M=8,k=5=94）；W3 由 R2 提请、R1 会核、R3 从渲染文本佐证。R3 的 U1（W7 溯源退化）为三方中唯一覆盖该项的发现；R2 的 W2（阈值不敏感句）为另两位漏检；R1 的 W3 会核结论与 W12（solver 固定）为独有。**唯一的评审间分歧**（W11c）由 R1 部分反驳 R2 对 "We first attributed…" 的批评，R2 在交叉回应中已接受。

## Reviewer Divergence（已解决）
评分谱 R1 4、R2 4、R3 3 **不构成实质分歧**：R3 的 3 全由其职责内两个硬阻断项驱动，而 R3 自己亦写明"accept 方向"；R1/R2 的 4 反映科学内容经复核全部通过。R2 提出的记账口径被采纳：**科学判定三方一致 = accept；提交资格判定 = 未通过，卡在 C1/C2**。

## Questions（须作者在修复中回答）
1. C1：匿名仓库最终采用真实 URL 还是回退为"仅投稿系统内提供"？
2. C1 附带：紧邻的 "no adversarial risk" 表述如何与 §5.6 dual-use 自述调和？
3. C2：五处空引用是标签重编号导致还是目标被删？修复后请做全量扫描（防第六处）。
4. C3：下侧究竟在哪些 (M,k) 上算过、是否注册了 artifact？§3.4/§4.2/表标题三者以谁为准？
5. W5：两条半径是共享实现还是巧合？
6. W12：solver/penalty 是否可记入 ledger？
7. W13：[31] 的假设表述是否有全文级依据？

## Missing References
无新增必引（64 条完整）。唯一建议是**归因补引**（不新增文献）：式 (9) 的两事件偏离路线可指向已在库的 Tsybakov [52]，并把 (9) 与已在库的 closeness-testing 线 [6,12] 连一句。

## External Review (Stanford Agentic Reviewer)
本项目未配置外部评审。

## Visual Layout Check（非计分）
本轮视觉检查代理首次派出以错误退出，已重派；截至汇总尚无结果。其覆盖缺口的实质内容（图表位置、浮动、页边界）已由三位评审从渲染 PDF 逐页核验并记入 W9/W8/C2 等条目。

## Paper Audit & Reference Verification（非计分）
- **引用核验（full）完成**：64/64，0 缺失/孤儿/幽灵；源码级仍报 luxemburk 两条缺 author 字段与 4 处缩写未加花括号（持续多轮，渲染与双盲始终无碍），建议作为 camera-ready bib 卫生处理，不再单独追踪。
- **质量审计**：本轮审计内容与视觉两条子任务均超时/出错，仅返回"编译成功、23 页"；无实质发现可并入。历史口径仍适用：审计结果以提交 PDF 为唯一权威，逐条对照评审验证后采信。

## Overall Assessment
**Verdict: accept on the science; submission not cleared this round。**
本轮的科学内容是十三轮中最强的一次且经三方独立复算全部通过——式 (9) 的无字母表界、两机制分工、阈值敏感性、依赖感知半径与更深的覆盖分析共同构成一篇成熟的测量论文。但同一轮改版引入的机械缺陷（两处提交阻断：占位符、五处空引用）与两处陈述-数据冲突（"from M=8 on"、"阈值不敏感"）使本版**不能进入正式评审**。五项提交前必做（按优先级）：
① **填/撤 Open Science 占位符**（C1，阻断）；
② **修五处空引用并做全量扫描**（C2，阻断）；
③ **一次性定案 M≥2 下侧并同步 §3.4 / §4.2 / Table 3 标题**（C3）；
④ **三处 "from M=8 on" 补 "at k≥15" 限定**（W1）；
⑤ **删除 §3.1 陈旧从句**（W2）并**把 LP 行和等式改为不等式 + 弃项半句**（W3）。
另有 W4–W14 随同批处理。R1 言明上述①–⑥完成后支持 5/5；R2 言明完成前不建议提交；R3 言明修复后再评分。距截止 2027-01-26 时间充裕，建议以一次内部编辑校对全部收尾，届时可考虑一轮最终确认。

## Detailed Comments（分节）
- **Abstract**: "from M=8 on" 三处之一待限定；双口径比值与四限定词保持完好（前几轮修复无回潮）。
- **§1**: 对 Cherubin 的压缩句待修（W11a）；贡献 2 含 "from M=8 on"。
- **§2.2 / §6.1**: [31] 重新定性待 refs 全文核对（W13）。
- **§3.1**: "阈值不敏感" 陈旧从句（W2）；LP 等式改不等式（W3）；fd1598 命名一致性（W10）。
- **§3.4 / §3.7 / §3.9**: 空引用（C2）；M=1-only 范围声明待定案（C3）。
- **§4.1**: 空引用（C2）。
- **§4.2**: 路线混用与 127/98 标注（C3）；主结果表回正文建议（W9）。
- **§4.3**: "at every k"（W1）；"We first attributed…" **保留**（W11c）；"3000 draws"（W11f）。
- **§4.4**: 独立性告诫（好）；"43 services"（W6）；"the cell above"（W11d）。
- **§4.5 / §5.2**: 空引用（C2）。
- **§5.5**: 400 重复阶梯（科学强项）但待命名 artifact（W7）；与 A.7 重叠可合并省页。
- **§7 / 摘要**: 两机制结论已进结论（好）。
- **附录 A.4–A.9**: 空节（W8）、两条半径同区间（W5）、"0.0029 gap"（W4）、"follow-up" 措辞（W11b）、规划推论（验证正确）。
- **Open Science**: 占位符（C1）、fd1598 缺失与两名一物（W10）、"no adversarial risk"（W11h）。
- **表/图**: 全表入附录与编号语义（W9）；Table 3↔Table 5 二十格交叉验证（正面证据）。