---
name: research-academic
description: 学术综述类调研模板包,用于做 literature review / systematic review / meta-analysis / state-of-the-art 综述 / research gaps 分析。基于 research-base 主 skill,覆盖学术专属的检索渠道、PICO 筛选、提取字段、综述骨架。触发词:文献综述、系统综述、survey、SOTA、research gap、literature review、systematic review、meta-analysis、PICO、PECO、SPIDER、arxiv、pubmed、semantic scholar。
status: draft
---

# Research Academic — 学术综述类模板包

## 一句话定位

学术综述场景的"分析角度 + 检索渠道 + 提取字段 + 报告骨架"。目标不是写一篇带引用的概述,而是逼出**可审计的文献综述工作流**:检索、纳排、逐篇笔记、比较矩阵、主题大纲、再到综述成文。**工具层、管线、评分都用主 skill 默认**。

默认读者不再假设是领域专家。除非用户明确要求纯学术口径,本包应优先产出:
- 一份给专业读者的综述正文
- 一份给非专业读者的解释版导读

## 你到底该看哪几个文件

### 只想判断这个包有没有“综述味”

1. `SKILL.md` — 看这包到底承诺什么
2. `report-template.md` — 看最终产物是不是像文献综述,还是只是概述
3. `hooks.md` — 看它有没有把检索、纳排、提取、综合真拆开

### 其他文件是什么定位

- `routing.md`: 什么时候该让位给其他包
- `channels.md`: 具体去哪找论文

如果你不是在改检索渠道,这两个都不是首读文件。

## 你能从这个包里真正收获什么

读完这个包,最应该带走的不是“又多了几份 md”,而是 4 个判断:
- 合格的文献综述不该只输出正文,还要有纳排和逐篇笔记留痕
- 主题分组必须先于成文,不能直接边读边写
- `reader_guide.md` 说明默认读者不再只是假设专家
- `research_gaps.md` 应该解释“哪里还没被解决”而不只是摆术语

## 触发条件

### 高优先级(强命中)
- "文献综述""系统综述""做个 survey"
- "RAG / Transformer / LLM 安全 / X 的最新进展"
- "research gap""SOTA""state of the art"
- 用户明确指定 arXiv / PubMed / Semantic Scholar / OpenAlex
- 提到 PICO / PECO / SPIDER 框架

### 中优先级(结合上下文)
- "近 N 年关于 X 的研究有哪些"
- "X 这个领域有哪些主要方法"
- 输出形态是综述 / 论文表格

### 不触发(交回 router 兜底)
- 与产品决策 / 市场情报 / 竞品 / 用户痛点强相关 → fallback 到 comprehensive

详见 `routing.md`。

## 钩子覆盖

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ | 补 PICO/PECO/SPIDER 字段到 `clarified_question.custom` |
| `hook_retrieve` | ✅ | 用 arXiv / Semantic Scholar / PubMed / OpenAlex / Crossref / ACL Anthology,并落检索式与检索轮次 |
| `hook_screen` | ✅ | PICO 筛选 + active learning 排序(抄 ASReview) + DOI 去重 + study_selection 日志 |
| `hook_extract` | ✅ | 抽 method / dataset / metric / result / limitation / contribution,并生成逐篇笔记与比较矩阵 |
| `hook_synthesize` | ✅ | 先出主题大纲和比较框架,再写综述正文 + gaps + bib |
| `hook_review` | ✅ | 加 adequacy gate、PRISMA flow + 引用合规 |

详见 `hooks.md`。

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口(本文件) |
| `routing.md` | 命中条件细则 + 与其他包冲突时的让位规则 |
| `channels.md` | 学术检索渠道清单 + 调用约定 |
| `report-template.md` | 综述输出骨架(中间产物 + 最终综述产物 + adequacy gate) |
| `hooks.md` | 钩子覆盖详情(每个 hook 的覆盖说明) |

一句话记忆:
- `SKILL.md` 看“承诺”
- `report-template.md` 看“交付”
- `hooks.md` 看“真不真”

## 固定产物层级

### A. 检索与纳排层(必出)
- `research_question.md`
- `search_queries.md`
- `criteria.json`
- `study_selection.csv`
- `source_log.csv`(主 skill 强制)

### B. 阅读与分析层(必出)
- `paper_notes/`
- `comparison_matrix.csv`
- `theme_outline.md`

### C. 成文层(必出)
- `literature_review.md`
- `reader_guide.md`
- `research_gaps.md`
- `references.bib`

其中:
- `literature_review.md` 面向专业读者,重比较、分歧、方法谱系
- `reader_guide.md` 面向非专业读者,重解释"这是什么 / 为什么重要 / 现在进展到哪 / 你该怎么理解"

如果只产出 C 层里的一篇正文,而没有 A/B 层和受众分层,那叫**带引用的概述**,不叫合格的文献综述。

## adequacy gate

本包在 `hook_review` 里增加一层门槛:

- 不满足检索覆盖、纳排留痕、逐篇笔记、主题覆盖等最低要求时
- 产物只能降级叫 `quick_review` 或 `scoping_note`
- **不能**直接叫 `literature review`

这条是为了避免再出现"只摘几篇论文就直接总结"的薄输出。

## 抄了哪些成熟方案

| 来源 | 抄什么 |
|---|---|
| `Galaxy-Dawn/claude-scholar` | 6 段流程语义、综述 + KB + 写作的产物分层 |
| `ChaokunHong/MetaScreener` | active learning + 4 Tier 决策(主 skill 已抄,本包按学术口径用) |
| `asreview/asreview` | active learning 优先级排序、PRISMA flow |
| `Golden2002/legal-research-skill` | 5 步骨架适配学术 |

## 给主 skill 的反向约束

- 学术包不需要的字段不进入主 schema(如 `feature_pricing`)
- 若学术包出现需要主 skill 加新原子工具的情况,必须先到 `research-base/references/missing-atoms.md` 提议
