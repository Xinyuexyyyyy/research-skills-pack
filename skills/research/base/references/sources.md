# Sources — 抄了哪些成熟方案

> 用户铁律:**抄别人的成型项目,不要觉得自己写的更好**。本文件追溯每一处具体抄了什么,方便后续核对。

---

## 1. `Galaxy-Dawn/claude-scholar`

**抄了**:
- Skills + Agents + Commands + Rules + Hooks 五件套分工法 → 反映在 `README.md` "怎么加新模板包" 的引导
- Progressive disclosure:SKILL.md 是入口,子文档拆分 → 整个 `research-base/` 目录就是这个范式
- 6 段研究流程的语义(ideation / 文献 / notes / KB / 实验 / 分析 / 报告 / 写作)→ 收敛到 `pipeline.md` 的 6 段
- "human decision-making stays at the center" → 反映在 Tier 3 必须人工复核

**未抄**:
- Zotero / Obsidian 整合(超出 V1 范围)
- 完整的 86 个 skill 列表(非通用)

**原始 harvest**:`<workspace>/skills/harvest-tool/data/harvest_Galaxy-Dawn_claude-scholar.json`

---

## 2. `ChaokunHong/MetaScreener`

**抄了**:
- HCN 4 层架构(Inference → Rule Engine → Calibrated Aggregation → Decision Router)→ 主 skill 的"管线 + 评分 + 路由"分层
- 4 Tier Decision Router(Tier 0 硬规则 / Tier 1 高置信 / Tier 2 中置信 / Tier 3 人工)→ 完全照搬到 `scoring.md`
- 多模型集成 + 校准的"calibrated confidence"思想 → 反映在 confidence 维度定义
- 评估指标系列(WSS@95、AUROC、Brier 等)→ 暂不进 V1,但接口预留

**未抄**:
- Python + FastAPI + Vue 3 实现栈(我们是 prompt 优先,不写代码)
- 4+ LLM 投票(Claude Code 单模型,暂用提取一致性代替)

**原始 harvest**:`<workspace>/skills/harvest-tool/data/harvest_ChaokunHong_MetaScreener.json`

---

## 3. `RefoundAI/lenny-skills`

**抄了**:
- `skills/{kebab-case-name}/SKILL.md + references/` 目录约定 → 整个 research-base/ 就照这个形态
- frontmatter description 含触发词的写法 → SKILL.md 头部
- 86 个 skill 平铺、Claude 自动选 skill 的解耦思路 → 反映在子模板包**平行**而非嵌套的设计

**未抄**:
- 86 个 skill 的内容(它是 PM 领域,我们是调研领域)

**原始 harvest**:`<workspace>/skills/harvest-tool/data/harvest_RefoundAI_lenny-skills.json`

---

## 4. `Golden2002/legal-research-skill`

**抄了**:
- 触发条件三档(高优先级 / 中优先级 / 不触发)→ 直接照搬到 `SKILL.md` 和 `router.md`
- 工作流五步骨架(问题解析 → 系统检索 → 冲突分析 → 时效梳理 → 输出文档)→ 收敛到 6 段管线
- 检索数据库表的呈现方式 → 用在 `atoms.md` 的 `academic_search(db?)` 参数列表

**未抄**:
- 中国法律领域知识(超出范围)
- 严格法条引用格式(普通调研用 BibTeX / Markdown 即可)

**原始 harvest**:`<workspace>/skills/harvest-tool/data/harvest_Golden2002_legal-research-skill.json`

---

## 5. `asreview/asreview`

**抄了**:
- active learning 优先级排序(top N 自动 include / 中段 uncertain / 尾部 exclude)→ `research-academic/hooks.md` 的 hook_screen
- PRISMA flow 四档 → `research-academic/hooks.md` hook_review 的 PRISMA 输出
- "human-in-the-loop"边界:不确定的回到人工 → 与主 skill Tier 3 一致

**未抄**:
- ASReview 的具体模型选择(我们走 LLM 启发式)
- 完整 GUI 与协作功能

**原始 harvest**:V1 暂未 harvest,需要时再补到 `harvest-tool/data/`

---

## 6. `assafelovic/gpt-researcher`

**抄了**:
- 多源并行 + agent 编排 → `research-comprehensive/channels.md` 的"跨包子调用"
- report aggregation 思路 → `research-comprehensive/hooks.md` hook_synthesize

**未抄**:
- Python + LangChain 实现栈
- 默认报告模板(我们用 decision memo 而非通用 report)

**原始 harvest**:V1 暂未 harvest,需要时再补

---

## 7. `langchain-ai/open_deep_research`

**抄了**:
- planning → searching → writing 三段、子图协作 → 综合类的"切片设计 + 子调用 + 装配"
- "supervisor + worker" agent 拓扑思路 → 综合类 fallback 的协作姿态

**未抄**:
- LangGraph 状态机实现(我们是 prompt + skill 体系)

**原始 harvest**:V1 暂未 harvest,需要时再补

---

## 8. Amazon "6-pager" / "PR-FAQ" 风格

**抄了**:
- decision memo 八段骨架(背景 / 选项 / 证据 / 对比 / 风险 / 推荐 / 落地 / 局限)→ `research-comprehensive/report-template.md`
- "推荐 + 反对证据"并列模式

**原始来源**:Amazon 内部公开写作规范、各类 staff/PM 写作手册总结(无单一仓库)

---

## 9. V3 共识文档(用户自定的)

**位置**:`<workspace>/task_draft/consensus/research-task-system-v3-20260503-035800/`

**抄了**:
- 四类模板的边界与定位
- 统一共性 4 个(澄清 / 来源记录 / 证据回链 / 复核)→ 直接进 `pipeline.md` 默认行为
- 学术综述产物清单 → `research-academic/report-template.md` 的 `research_question.md` / `study_selection.csv` / `comparison_matrix.csv` / `literature_review.md` / `reader_guide.md` / `research_gaps.md`
- 竞品调研产物清单 → `research-competitive/report-template.md` 的 `competitor_list.csv` / `feature_matrix.csv` / `pricing_landscape.csv` / `competitors_report.md` / `battle_cards.md` / `reader_brief.md`
- 产品发现产物清单 → `research-discovery/report-template.md` 的 `pain_point_map.md` / `workarounds.csv` / `validation_plan.md` / `discovery_report.md` / `mvp_wedge.md` / `reader_brief.md`
- 综合调研产物清单 → `research-comprehensive/report-template.md` 的 `decision_question.md` / `decision_scorecard.csv` / `tradeoff_brief.md` / `decision_memo.md` / `reader_brief.md`
- 评分维度灵感:置信度 + 一手二手 + 时效性 + 权威性 + 冲突标记

---

## 后续如要加新参考

在 `harvest-tool/data/` 里 harvest 新项目后,记一条到本文件:
- 项目名、url
- 抄了什么(具体到哪个文件 / 哪段)
- 未抄什么(避免误用)
- 原始 harvest 路径

---

## 没抄的(用户铁律 §3 之外的)

下列东西**没参考任何成熟项目,是我们独立设计的**(用户审核时重点看):

- 钩子接口契约(`hooks.md` 的 6 个 hook 输入输出 schema)
- 10 维评分的具体维度组合(用户参与定的,但合分规则部分自创)
- 主 skill 与子包的"覆盖优先级"模型(类比 React hooks 的思路)

如发现这些设计**比成熟方案更糟**,直接换掉即可。
