# Hooks — 钩子接口契约

## 定位

子模板包通过**覆盖钩子**来扩展默认管线。不需要的段落,什么都不写,默认实现接管。

本文件定义的是**共享层契约**。一旦发布,改起来代价很大,因为所有子包都要跟着改。

---

## 先记住 3 条硬约束

1. 6 个 hook 的名字和先后顺序固定: `clarify -> retrieve -> screen -> extract -> synthesize -> review`
2. 每个 hook 都必须保留主 skill 规定的核心字段,子包只能在 `custom` 一类扩展位里加字段
3. 所有外部来源最终都必须能回溯到 `source.ref + locator + quote`,否则 Stage 6 会打回

---

## 钩子点总表

| 钩子名 | 输入 | 输出 | 子包最常改什么 |
|---|---|---|---|
| `hook_clarify` | `raw_input: string` | `clarified_question` | 加领域专用澄清字段 |
| `hook_retrieve` | `clarified_question` | `raw_materials[]` | 改检索渠道和搜索策略 |
| `hook_screen` | `raw_materials[], criteria` | `filtered_materials[]` | 改纳排规则 |
| `hook_extract` | `filtered_materials[]` | `evidence_records[]` | 改抽取字段 |
| `hook_synthesize` | `evidence_records[], report_structure` | `draft_report` | 改产物和报告骨架 |
| `hook_review` | `draft_report, evidence_records[]` | `verified_report` 或 `review_notes` | 加更严格复核 |

---

## 标准 schema

### `clarified_question`
```yaml
topic: string                    # 调研主题
scope: string                    # 范围(对象 / 地域 / 维度)
time_window: [start, end]        # 时间窗,允许 open-ended
output_form: string              # 期望输出形态
constraints: string[]            # 用户明确约束
custom: object                   # 子包扩展字段,只能往这里加
```

### `criteria`
```yaml
include: string[]                # 纳入条件
exclude: string[]                # 排除条件
uncertain_policy: string         # 边界项怎么处理
dedup_key: string[]              # url / doi / canonical_title ...
custom: object                   # 子包扩展规则
```

### `raw_materials[]`
```yaml
- material_id: string
  source_type: string            # web | paper | repo | review | forum | wayback | internal | ...
  url: string
  title: string
  content_snippet: string
  fetched_at: ISO8601
  raw_excerpt: string            # 不超过 2000 字
  artifact_ref: string           # 完整正文或截图落到运行产物目录后的引用
  metadata: object               # doi / authors / domain / language / snapshot_date ...
```

### `filtered_materials[]`
```yaml
- material_id: string
  source_type: string
  url: string
  title: string
  content_snippet: string
  fetched_at: ISO8601
  raw_excerpt: string
  artifact_ref: string
  metadata: object
  selection: include | exclude | uncertain
  selection_reason: string
  criteria_hits:
    include: string[]
    exclude: string[]
    notes: string[]
```

说明:
- `filtered_materials[]` 是**筛选后的全量记录**,不是只保留 `include`
- Stage 4 默认只消费 `include`,若要消费 `uncertain`,必须在 `selection_reason` 里写清理由

### `evidence_score`
```yaml
confidence: float                # 0-1
selection: include | exclude | uncertain
redundancy: float                # 0-1,高 = 冗余高
strength: float                  # 0-1
primacy: primary | secondary | tertiary
recency: float                   # 0-1
authority: low | mid | high
coverage: float                  # 0-1
conflict: none | partial | contradictory
citation_completeness: float     # 0-1
composite_score: int             # 0-100,解释性总分
rationale: string[]              # 打分理由,至少 1 条
```

### `evidence_records[]`
```yaml
- id: string                     # E-001, E-002, ...
  material_id: string
  claim: string                  # 一句话结论
  quote: string                  # 原文摘录
  source:
    ref: string                  # url / doi url / file path
    locator: string              # 页码 / section / table / timestamp
  context: string
  extracted_at: ISO8601
  score: evidence_score
  tier: 0 | 1 | 2 | 3
  tags: string[]
  custom: object
```

### `report_structure`
```yaml
report_type: string
required_sections:
  - id: string
    heading: string
    must_include: string[]
optional_sections:
  - id: string
    heading: string
artifacts:
  - type: string                 # csv | md | bib | canvas | json
    path: string
    purpose: string
custom: object
```

### `draft_report`
```yaml
title: string
sections:
  - id: string
    heading: string
    body_markdown: string
    citations: string[]          # E-001, E-002, ...
artifacts:
  - path: string
    type: string
    desc: string
summary_claims: string[]         # 便于 review 做 claim-level 回链检查
custom: object
```

### `review_notes`
```yaml
status: needs_human_review | failed
blocking_issues: string[]
unsupported_claims: string[]
conflicts_to_resolve: string[]
gaps: string[]
recommended_actions: string[]
```

### `verified_report`
```yaml
report: draft_report
review_summary:
  total_evidence: int
  tier_breakdown: { "0": int, "1": int, "2": int, "3": int }
  unresolved_conflicts: string[]
  unsupported_claims: string[]
  gaps: string[]
status: passed | needs_human_review | failed
```

---

## 每个 hook 的稳定约束

### `hook_clarify`

- 必须返回 5 个核心字段: `topic / scope / time_window / output_form / constraints`
- 领域专用字段只能写进 `custom`
- 如果用户信息不够,允许先反问,但最终落地对象还是 `clarified_question`

### `hook_retrieve`

- 必须为每条材料生成稳定的 `material_id`
- 必须记录 `fetched_at`
- 完整正文、截图、PDF 或转录文本不能只塞在 `raw_excerpt`,要放到 `artifact_ref`

### `hook_screen`

- 不能静默丢记录;排除项也要保留在 `filtered_materials[]`
- `selection_reason` 不能为空
- 去重属于筛选的一部分,但被合并的来源仍要能追溯

### `hook_extract`

- 每条 `evidence_record` 必须能回到 `material_id`
- `score` 和 `tier` 是必填,否则 extract 不算完成
- 一个材料可以拆成多条 evidence,但不要把多个独立 claim 混成一条

### `hook_synthesize`

- 所有最终结论都必须引用 `evidence_records[]`
- `summary_claims` 必须列出报告中真正要被复核的关键结论
- 子包可以增加产物,但不能少掉主任务要求的核心产物

### `hook_review`

- 通过时返回 `verified_report`
- 不通过时返回 `review_notes`
- 只要存在无回链结论或未处理的强冲突,默认不能 `passed`

---

## 覆盖示例

子模板包 `research-academic` 的 hook 文件示例:

```markdown
# research-academic / hooks

## 覆盖

hook_clarify: 默认 + 补 PICO/PECO/SPIDER 字段到 custom
hook_retrieve: 改用 arXiv/Semantic Scholar/PubMed/OpenAlex,并落 search_queries.md
hook_screen: 用 PICO + active learning + dedup by DOI,并生成 study_selection.csv
hook_extract: 抽 method/dataset/metric/limitation,并生成 paper_notes/ + comparison_matrix.csv
hook_synthesize: 先出 theme_outline.md / comparison_matrix.csv,再写 literature_review.md + evidence_table.csv + research_gaps.md + references.bib
hook_review: 加 adequacy gate + PRISMA flow 图

## 不覆盖

(其他钩子都用主 skill 默认)
```

---

## 优先级

```
子包钩子覆盖 > 默认管线行为
```

主 skill 调用时,逻辑伪代码:

```text
for stage in [clarify, retrieve, screen, extract, synthesize, review]:
    if subpackage.has_hook(stage):
        result = subpackage.hook[stage](input)
    else:
        result = base.default[stage](input)
    input = result
```

---

## 改钩子接口的代价

| 改动类型 | 代价 | 原因 |
|---|---|---|
| 只加 `custom` 子字段 | 低 | 不破坏主字段 |
| 新增可选字段 | 中 | 主 skill 和子包都要补认知 |
| 修改字段含义 | 高 | 老子包会产生语义漂移 |
| 修改字段名 / 删除字段 / 改输入输出顺序 | 最高 | 所有子包都要升版 |

如果未来必须改:
1. 在 `references/breaking-changes.md` 写理由 + 影响面(待建)
2. 跑过所有子包 + 至少一次真实小调研验证
3. 每个子包对应升级 PR / 改动

---

## V1 边界

- 跨包子调用的片段协议已先在 `research-comprehensive/channels.md` 落地;共享层暂不把它上收成全局必选字段。
- 跨钩子的全局运行态 schema 目前只约定了 `artifact_ref` 和 `material_id`,够 V1 用。
- 异步 / 并行钩子(Stage 2 多渠道并行检索)仍未进入共享默认行为。当前默认串行,子包若要并行,自行在本包文档里约定。
