---
name: academic-deep-research
description: 学术科研工具入口层。所有学术类请求（找论文、纳排、读论文、写综述、深度调研）统一由本 skill 接收，通过 Round 1 澄清用户意图后分发到正确的下游 skill；如果是开放/决策问题则继续走多轮深度调研。触发词：deep research、领域扫描、跨主题研究、学术+网页混合、决策调研、深度调研、找论文、检索、纳排、筛选、读论文、写综述、research gap、SOTA、systematic review、literature review。
status: stable
---

# Academic Deep Research — 学术科研入口层 + 深度调研

## 一句话定位

**学术科研工具的统一入口**。所有学术请求先进入本 skill 做意图澄清,再决定：
- 分发到下游 skill（discovery / screening / reading / writer）
- 或继续走本 skill 的多轮深度调研

## 双重角色

### 角色 1：入口层（所有学术请求）
- 接收用户的任意学术类请求
- Round 1 做意图澄清 + 快速判断
- 如果意图明确且属于主链路（找论文/纳排/读论文/写综述），直接分发到对应 skill，本 skill 退出
- 分发后不干预下游 skill 的执行

### 角色 2：深度调研执行层（开放/决策/混合问题）
- Round 1 判断为开放/决策/混合问题时，继续走 Round 2-4
- 支持学术+网页混合源
- 每轮产出 subreport，最终合并为完整报告

## 上层契约

- 父级:`research-base`(共享层,一级路由直接命中本 skill)
- 进入条件:所有学术类请求（一级路由判断为学术后直接进入）
- 离开条件 A（分发）:Round 1 完成后，分发到下游 skill（见完整路由表）
- 离开条件 B（深度调研）:产出 `deep_research_report.md` + `subreports/` + `research_brief.md`
- 共享 schema:复用 `research-base/artifacts.md` 的 source_log / evidence_table,但允许扩展非学术源

## Step 0：状态感知（自动执行，不需用户操作）

进入本 skill 后，**第一件事**是扫描当前工作目录下的工件，判断用户处于哪个阶段：

| 检测到的工件 | 判断阶段 | 默认建议 |
|---|---|---|
| 什么都没有 | 起点 | 从 research question 开始,走 discovery |
| `search_plan.md` 但无 `candidate_papers.csv` | 检索中 | 继续 discovery |
| `candidate_papers.csv` | 候选池已建 | 下一步做 screening |
| `study_selection.csv`（含 included） | 纳排已完成 | 下一步做 reading |
| `evidence_table.csv` | 证据已抽取 | 下一步做 survey-writer |
| `literature_review.md` / `related_work.md` | 综述已写 | 流程完成,或做 gaps/future work |

**状态感知的作用**：
1. 帮助 Round 1 快速判断用户在哪一步,减少反问
2. 如果用户说"继续"或"下一步",直接根据当前状态推进
3. 如果用户的请求和当前状态矛盾（如已有 evidence_table 但说"找论文"），主动确认

## Round 1：意图澄清 + 分发决策

**这是所有学术请求的必经步骤。**

### Step 1 — 快速判断：能否直接分发？

以下情况**不需要反问，直接分发**：

| 用户意图 / 信号 | 分发到 | 说明 |
|---|---|---|
| "找论文""检索""搜文献""建候选池" + 有明确关键词/研究问题 | `paper-discovery` | 意图清晰，直接走 |
| "纳排""筛选""PRISMA" + 已有 `candidate_papers.csv` | `paper-screening` | 意图清晰，直接走 |
| "读论文""抽证据""做对比" + 已有 included 论文 | `paper-reading` | 意图清晰，直接走 |
| "写综述""related work""research gaps" + 已有 `evidence_table.csv` | `survey-writer` | 意图清晰，直接走 |
| "想 idea""brainstorm""发散""有什么方向" | `research-ideation` | 创意发散阶段 |
| "选题""gap 分析""可行性""开题" | `topic-framing` | 选题定位阶段 |
| "聚合知识""编译知识包""知识整理" | `knowledge-compiler` | 知识编译 |
| "设计方法""实验方案""方法论""methodology" | `method-design` | 方法设计阶段 |
| "写论文""组装论文""draft paper" | `paper-composer` | 论文组装阶段 |
| "画图""论文配图""figure""plot" | `academic-plotting` | 学术绘图 |
| "自审""逻辑审查""rigor check" | `rigor-reviewer` | 严谨性审查 |
| "去 AI 味""humanize""润色去痕迹" | `humanizer` | 去 AI 痕迹 |
| 模糊想法，只有方向没有具体问题 | 本 skill 继续 Round 1 澄清 | 吸收 idea-to-research 逻辑 |
| 开放/决策/混合问题 | 本 skill 继续 Round 2-4 深度调研 | 多轮调研 |

### Step 2 — 需要澄清时：问 1-2 个缩边界问题

意图不明确时，**只问 1-2 个最关键的问题**（吸收 idea-to-research 的逻辑）：

- 不知道用户在哪个阶段 → "你现在手里有什么：研究问题？候选论文集？还是已经筛完的论文？"
- 不知道是主链路还是开放问题 → "你想做的是围绕一个明确主题找论文/做综述，还是想对一个开放问题做深度调研？"
- 用户只给了一个模糊方向（如"我想研究 AI 教育"），没有具体问题 → 先问缩边界问题：
  - "你关注的是哪个层面？比如：技术实现、教学效果、政策影响？"
  - "你的目标产出是什么？选题报告、文献综述、还是只想先了解这个领域？"
- 缩边界后再决定分发到哪个下游 skill（通常是 `research-ideation` 或 `topic-framing`）

### Step 3 — 分发或继续

- 澄清后意图属于主链路 → 分发到对应下游 skill，本 skill 结束
- 澄清后意图属于开放/决策问题 → 继续走 Round 2-4

### 分发输出

分发时必须输出 `routing_decision.json`：

```json
{
  "entry_point": "academic-deep-research",
  "action": "dispatch | continue_deep_research",
  "dispatch_to": "paper-discovery | paper-screening | paper-reading | survey-writer | research-ideation | topic-framing | knowledge-compiler | method-design | paper-composer | academic-plotting | rigor-reviewer | humanizer | null",
  "reason": "...",
  "clarification_used": true
}
```

## 多轮研究项目支持（Research Project Mode）

当用户明确说“这是一个研究项目”，或多轮对话持续围绕同一研究问题推进时，建议激活 Research Project Mode。

它不把本 skill 改成全自动运行，不依赖 `/loop`，也不改变“入口层 + 路由”的定位；只提供项目 workspace 和节奏规则。

建议 workspace 模板：

```text
{project}/
├── research-state.yaml    # 当前状态：研究问题、活跃假设、已验证/已否定
├── research-log.md        # 决策时间线：什么时候做了什么决定
├── findings.md            # 演进中的发现叙述，不断更新综合理解
├── literature/            # 论文笔记
└── experiments/           # 实验记录
```

循环节奏规则：
- 内循环: 每次只做一个具体动作，如读一篇论文、跑一个查询、分析一个结果。
- 外循环: 每 5-10 次内循环后停下来综合，更新 `findings.md`。
- 外循环自问: “我现在知道了什么？还缺什么？方向要不要调？”
- 非线性研究观: 随时可以回到文献，随时可以 pivot，不强制线性流水线。
- 用户未确认创建 workspace 前，只建议结构，不主动落盘。

`research-state.yaml` 最小结构：

```yaml
question: "核心研究问题"
status: exploring|converging|writing
hypotheses:
  - text: "假设内容"
    status: active|validated|rejected
    evidence: ["来源1", "来源2"]
next_actions:
  - "下一步要做什么"
```

## Round 2-4：深度调研（仅限开放/决策问题）

> 以下流程只在 Round 1 判断为"继续深度调研"时执行。

```
第2轮：假设验证 → 深度检索 → 证据收集
第3轮：证据整合 → 冲突分析 → 方案对比
第4轮：综合判断 → 风险评估 → 最终建议
```

**每轮产出**：`subreports/round-N.md`
**轮次控制**：默认 3-4 轮,用户可喊停或要求加轮

### Round 1（深度调研模式）: 问题澄清 + 快速扫描

**目标**：把模糊问题转化为可调研的结构化问题。

**步骤**：
1. 反问用户 1-3 个澄清问题（每次只问一个）
2. 基于澄清后的问题,做快速扫描：
   - 学术源：arXiv/S2/OpenAlex 关键词检索（每源上限 20 条）
   - 网页源：行业报告/新闻/博客（上限 10 条）
3. 产出 `subreports/round-1.md`：问题定义 + 初步假设 + 已知/未知

### Round 2: 假设验证 + 深度检索

**目标**：验证 Round 1 的假设,收集支撑/反驳证据。

**步骤**：
1. 列出 Round 1 的所有假设
2. 对每个假设,分别检索支持证据和反驳证据
3. 学术源：深入检索（每源上限 50 条）
4. 网页源：针对性检索（上限 20 条）
5. 产出 `subreports/round-2.md`：假设验证结果 + 证据清单 + 置信度评估

### Round 3: 证据整合 + 冲突分析

**目标**：整合多源证据,分析冲突,形成方案对比。

**步骤**：
1. 按主题聚类证据
2. 识别证据冲突（学术 vs 网页、A 论文 vs B 论文）
3. 分析冲突原因（方法论差异、数据差异、时间差异）
4. 形成 2-3 个备选方案/观点
5. 产出 `subreports/round-3.md`：方案对比表 + 冲突分析 + 各方案优劣

### Round 4: 综合判断 + 风险评估

**目标**：给出最终判断和建议。

**步骤**：
1. 基于 Round 3 的方案对比,给出推荐方案
2. 评估关键风险（如果推荐错了,代价是什么）
3. 给出"如果条件变了,建议怎么调整"
4. 产出 `subreports/round-4.md`：最终建议 + 风险评估 + 条件触发器

## P0 边界

### 做什么
- ✅ 多轮迭代（默认 3-4 轮,每轮有明确目标）
- ✅ 混合源检索（学术+网页,学术优先）
- ✅ 每轮产出 `subreports/round-N.md`
- ✅ 最终合并为 `deep_research_report.md`
- ✅ `research_brief.md`：1 页摘要（给决策者看的）
- ✅ 每轮结束问用户"是否继续"或"聚焦某个方向"

### 不做什么
- ❌ 替代学术主链路（如果问题是纯学术的,导回 paper-discovery）
- ❌ 编造数据或引用
- ❌ 替用户做最终决策（只给建议,用户拍板）
- ❌ 超过 5 轮（防止无限迭代）

## 必出产物

| 文件 | 说明 |
|---|---|
| `research_brief.md` | 1 页决策摘要（问题/结论/建议/风险） |
| `deep_research_report.md` | 完整深度报告（整合所有 subreports） |
| `subreports/round-1.md` | 第 1 轮：问题澄清 + 快速扫描 |
| `subreports/round-2.md` | 第 2 轮：假设验证 + 深度检索 |
| `subreports/round-3.md` | 第 3 轮：证据整合 + 冲突分析 |
| `subreports/round-4.md` | 第 4 轮：综合判断 + 风险评估（如需要） |
| `source_log.csv` | 见 `research-base/artifacts.md` §2 |
| `evidence_table.csv` | 见 `research-base/artifacts.md` §4（扩展：允许非学术源） |

## 文件清单

```
academic-deep-research/
├── SKILL.md            入口(本文件)
├── README.md           读图
└── report-template.md  subreport 和最终报告的模板
```

## 衔接提示（分发后 + 下游完成后）

### 分发时：告诉用户去了哪里

分发到下游 skill 时，用一句人话说明：
- 你现在在哪一步
- 这一步做完会产出什么
- 做完后下一步是什么

**模板**：
```
当前阶段：[阶段名]
本步产出：[具体文件]
完成后下一步：[下一个 skill 能做什么]
```

### 下游完成后：衔接提示

每个下游 skill 完成后，必须输出以下衔接信息：

| 刚完成的 skill | 产出物 | 下一步 |
|---|---|---|
| `paper-discovery` | `candidate_papers.csv` + `references.bib` | "候选池已建好（N 篇）。下一步做纳排筛选。" → 自动进入 screening |
| `paper-screening` | `study_selection.csv` + `prisma_flow.md` | "纳排完成（纳入 N 篇）。下一步逐篇精读抽证据。" → 自动进入 reading |
| `paper-reading` | `evidence_table.csv` + `paper_notes/` | "证据抽取完成（N 条证据）。下一步写综述。" → 自动进入 survey-writer |
| `survey-writer` | `literature_review.md` | "综述初稿完成。现在进入风格适配。" → **默认进入输出层**（用户说"跳过"才跳过） |
| `topic-framing` | `topic_statement.md` + `opening_report.md` | "选题已定。下一步可以设计研究方法，说'设计方法'或'方法论'" → 自动进入 method-design |
| `method-design` | `methodology.md` + `method_comparison.md` | "方法论章节完成。下一步：如果有实验/分析要做，先做实验；如果是纯综述型，可以直接组装论文。" |
| `paper-composer` | `paper_draft.md` | "论文初稿完成。现在进入风格适配。" → **默认进入输出层** |
| `paper-reading`（产出 reading_summary） | `reading_summary.md` | "阅读总结完成。现在进入风格适配。" → **默认进入输出层** |

### "继续"和"下一步"的快捷响应

当用户只说"继续""下一步""接着做"时：
1. 读取 Step 0 的状态感知结果
2. 直接分发到当前阶段的下一个 skill
3. 不需要反问

## 自检清单

- [ ] Step 0 状态感知：进入时自动扫描工件,判断用户阶段？
- [ ] 用户说"继续/下一步"时,能根据状态直接推进不反问？
- [ ] 分发时有人话说明当前阶段 + 产出 + 下一步？
- [ ] 下游完成后有衔接提示（产出物 + 下一步建议）？
- [ ] 每轮都有明确的目标和产出？
- [ ] 每轮结束后都问用户"是否继续/聚焦/喊停"？
- [ ] 学术源和网页源严格分层,不混用？
- [ ] 证据冲突被明确标注,不强行调和？
- [ ] 最终建议附带"如果错了的代价"和"条件触发器"？
- [ ] 总轮次不超过 5 轮？
- [ ] `research_brief.md` 控制在 1 页内,给决策者直接看？
