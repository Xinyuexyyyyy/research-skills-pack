# Hooks — 竞品包钩子覆盖

> 接口契约见 `../../base/hooks.md`。本文件只描述竞品包的覆盖。

## 覆盖矩阵

| 钩子 | 覆盖 | 改动幅度 |
|---|---|---|
| `hook_clarify` | ✅ | 加 category / competitors scope / audience_profile |
| `hook_retrieve` | ✅ | 替换为竞品情报渠道 |
| `hook_screen` | ✅ | direct / adjacent / workaround 分层 |
| `hook_extract` | ✅ | 抽 feature / pricing / positioning / sentiment / GTM |
| `hook_synthesize` | ✅ | 先出 matrix 和 pricing,再写报告 |
| `hook_review` | ✅ | 覆盖、时效、引用合规检查 |

## 1. `hook_clarify`

```yaml
clarified_question:
  topic: ...
  scope: ...
  time_window: [start, end]
  output_form: competitors_report
  constraints: [...]
  custom:
    category: string
    decision_context: string
    audience_profile: beginner | mixed | expert
    target_geography: string
    direct_competitor_definition: string
    adjacent_definition: string
    must_include_companies: [string]
```

必须落:
- `market_question.md`
- `competitor_scope.md`

## 2. `hook_retrieve`

- 渠道按 `channels.md`
- 必须记录 `search_log.md`
- 必须优先抓官网 / pricing page

## 3. `hook_screen`

筛选后保留层次:
- direct
- adjacent
- status_quo
- manual_workaround

必须生成:

```csv
competitor_id,name,bucket,why_included,primary_sources
```

## 4. `hook_extract`

`evidence_record.custom` 必填:

```yaml
custom:
  competitor_id: string
  feature_area: string
  pricing_model: string
  user_segment: string
  positioning: string
  sentiment: positive | mixed | negative
  gtm_signal: string
  explain_for_reader: string
```

必须生成:
- `competitor_list.csv`
- `feature_matrix.csv`
- `pricing_landscape.csv`
- `sentiment_summary.md`
- `gtm_signals.md`

## 5. `hook_synthesize`

Stage 5A:
- 补齐 competitor list / feature matrix / pricing landscape

Stage 5B:
- `competitors_report.md`
- `battle_cards.md`
- `reader_brief.md`

写作约束:
- 先讲市场格局是什么
- 再讲每类玩家怎么分
- 再讲功能、价格、评价、GTM 分别差在哪
- `reader_brief.md` 必须解释“direct / adjacent / workaround”是什么意思
- 每个关键判断都要回答:
  - 这是什么现象
  - 为什么这件事重要
  - 对我们意味着什么
  - 哪些判断只是弱信号,不能说太满

## 6. `hook_review`

adequacy gate:
- direct competitors >= 3
- 有 pricing_landscape.csv
- 有 feature_matrix.csv
- 有 reader_brief.md(除非 audience_profile=expert)

否则只能降级为 `quick_landscape`

explainability gate:
- `reader_brief.md` 若只是正文压缩版,没有把 direct / adjacent / workaround / packaging 这些术语讲人话 → `needs_human_review`
- 若 `competitors_report.md` 没写清本次范围、时间窗和缺失数据 → `needs_human_review`
