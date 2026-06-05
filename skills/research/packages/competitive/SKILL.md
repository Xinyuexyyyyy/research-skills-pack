---
name: research-competitive
description: 竞品 / 市场情报类调研模板包。用于做竞争格局、替代方案、价格、用户评价、GTM 信号与战卡。基于 research-base 主 skill,覆盖竞品专属渠道、筛选规则、比较矩阵和报告骨架。触发词:竞品、竞争对手、市场格局、定价、价格、battle card、替代方案、GTM、评论、用户反馈、Capterra、G2、pricing、competitive intelligence。
status: draft
---

# Research Competitive — 竞品 / 市场情报模板包

## 一句话定位

竞品调研场景的"渠道 + 分析框架 + 报告骨架"。目标不是列名字,而是做出**可交付的竞争情报包**:竞争集合、证据矩阵、价格带、差异点、风险和面向非专业读者的导读。

## 你到底该看哪几个文件

### 只想判断这个包是不是“真竞品调研”

1. `SKILL.md` — 看这包到底承诺做什么
2. `report-template.md` — 看交付是不是矩阵、价格带、战卡,而不只是概述
3. `hooks.md` — 看有没有 direct / adjacent / workaround 的强制分层

### 其他文件是什么定位

- `channels.md`: 具体去哪里抓官网、价格页、评论站
- `routing.md`: 什么时候该交给其他包

如果你不是在审取证渠道,这两个先可以不看。

## 你能从这个包里真正收获什么

读完最该带走的是:
- 竞品调研不等于列产品名单
- 没有 `pricing_landscape` 和 `feature_matrix` 就很难叫竞争情报
- `direct / adjacent / workaround` 是为了讲清威胁层级,不是故作术语
- `reader_brief.md` 的存在说明结果要给非专业读者也能读懂

## 触发条件

### 高优先级(强命中)
- "竞品有哪些""竞争对手是谁""市场上谁在做这个"
- "做个 competitive analysis / battle card / pricing landscape"
- "看看用户怎么评价这些产品"
- 提到 G2 / Capterra / Product Hunt / TrustRadius / pricing

### 中优先级(结合上下文)
- "X 的替代方案有什么"
- "这个市场值得进吗"
- "列一下 direct / adjacent competitors"

### 不触发
- 明确只看论文或学术进展 → academic
- 明确是产品定义 / PRD / 用户访谈主导 → discovery
- 明确是跨多类型决策题 → comprehensive

## 钩子覆盖

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ | 加 market question / category / audience_profile |
| `hook_retrieve` | ✅ | 走官网、价格页、评论站、论坛、招聘、融资、Wayback |
| `hook_screen` | ✅ | 按 direct / adjacent / status quo / workaround 分层 |
| `hook_extract` | ✅ | 抽 feature / pricing / positioning / sentiment / GTM |
| `hook_synthesize` | ✅ | 先出 competitor set / matrix,再写报告与 reader brief |
| `hook_review` | ✅ | 强制竞争集合覆盖、引用合规、时间敏感性检查 |

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口(本文件) |
| `routing.md` | 命中条件与边界 |
| `channels.md` | 情报渠道、优先级与取证约定 |
| `report-template.md` | 竞争情报包骨架 |
| `hooks.md` | 钩子覆盖详情 |

一句话记忆:
- `SKILL.md` 看“做不做得到位”
- `report-template.md` 看“像不像正式战情包”
- `hooks.md` 看“分层和复核有没有落地”

## 固定产物层级

### A. framing 层(必出)
- `market_question.md`
- `competitor_scope.md`
- `search_log.md`
- `source_log.csv`

### B. 分析层(必出)
- `competitor_list.csv`
- `feature_matrix.csv`
- `pricing_landscape.csv`
- `sentiment_summary.md`
- `gtm_signals.md`

### C. 交付层(必出)
- `competitors_report.md`
- `battle_cards.md`
- `reader_brief.md`

如果只写一篇竞品概述,而没有竞争集合、矩阵和价格带,那不算合格的 competitive package。
