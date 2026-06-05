# Hooks — 产品发现包钩子覆盖

> 接口契约见 `../../base/hooks.md`。

## 覆盖矩阵

| 钩子 | 覆盖 | 改动幅度 |
|---|---|---|
| `hook_clarify` | ✅ | 加 problem / user / assumptions / audience_profile |
| `hook_retrieve` | ✅ | 内部输入优先,外部验证为辅 |
| `hook_screen` | ✅ | 按痛点强度 / 频率 / 可验证性筛选 |
| `hook_extract` | ✅ | 抽 pain / workaround / demand signal / assumption |
| `hook_synthesize` | ✅ | 先出 discovery canvas,再出 report / wedge / PRD |
| `hook_review` | ✅ | 检查 assumptions 和 validation plan |

## 1. `hook_clarify`

```yaml
clarified_question:
  topic: ...
  scope: ...
  time_window: [start, end]
  output_form: discovery_report
  constraints: [...]
  custom:
    problem_statement: string
    target_user: string
    audience_profile: beginner | mixed | expert
    current_workaround: string
    key_assumptions: [string]
    desired_outcome: string
```

必须落:
- `problem_statement.md`
- `target_user.md`
- `assumptions_log.md`

## 2. `hook_retrieve`

- 内部输入优先
- 外部只做轻验证,不追求 exhaustive search

## 3. `hook_screen`

保留标准:
- 痛点是否高频
- 痛点是否高成本
- 是否已有 workaround
- 是否能被最小实验验证

## 4. `hook_extract`

`evidence_record.custom` 必填:

```yaml
custom:
  pain_type: frequency | severity | frustration | switching_cost
  workaround: string
  assumption_link: string
  demand_signal: string
  explain_for_reader: string
```

必须生成:
- `pain_point_map.md`
- `workarounds.csv`
- `evidence_summary.csv`
- `validation_plan.md`

## 5. `hook_synthesize`

Stage 5A:
- 补齐 pain / workaround / assumptions / validation plan

Stage 5B:
- `discovery_report.md`
- `mvp_wedge.md`
- `prd_outline.md`
- `reader_brief.md`

写作约束:
- 先讲用户问题是什么
- 再讲用户现在怎么解决
- 再讲为什么值得做
- 最后讲最小 wedge 是什么
- 每个关键判断都要回答:
  - 这是什么问题
  - 为什么这个问题重要
  - 目前证据支持到什么程度
  - 下一步最便宜的验证动作是什么

## 6. `hook_review`

adequacy gate:
- pain points >= 3
- assumptions >= 3
- 有 validation_plan.md
- 有 reader_brief.md(除非 audience_profile=expert)

否则只能降级为 `idea_note`

explainability gate:
- `reader_brief.md` 若没有把 pain point / workaround / wedge / assumption 这些词讲成非专业读者能懂的人话 → `needs_human_review`
- 任一关键 assumption 若既没有 supporting evidence,也没有对应验证动作 → `needs_human_review`
