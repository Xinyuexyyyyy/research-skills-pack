# Hooks — 学术包钩子覆盖

> 接口契约见 `../../base/hooks.md`。本文件只描述**学术包覆盖了什么 + 怎么覆盖**。

## 覆盖矩阵

| 钩子 | 覆盖 | 改动幅度 |
|---|---|---|
| `hook_clarify` | ✅ | 加 custom 字段,不改主字段 |
| `hook_retrieve` | ✅ | 替换检索渠道 |
| `hook_screen` | ✅ | 替换筛选规则 |
| `hook_extract` | ✅ | 在 evidence_record.custom 加学术字段 |
| `hook_synthesize` | ✅ | 替换报告骨架 |
| `hook_review` | ✅ | 加 adequacy gate、PRISMA + 引用合规检查 |

---

## 1. `hook_clarify`

### 在主字段基础上,要补充 `custom`:

```yaml
clarified_question:
  topic: ...
  scope: ...
  time_window: [start, end]    # 默认 24-36 个月,可由用户改
  output_form: literature_review | systematic_review | scoping_review | sota | gap_finding
  constraints: [...]
  custom:
    framework: PICO | PECO | SPIDER | none
    pico:                       # framework=PICO 时填
      population: string
      intervention: string
      comparison: string
      outcome: string
    peco:                       # framework=PECO 时填
      population: string
      exposure: string
      comparison: string
      outcome: string
    spider:                     # framework=SPIDER 时填
      sample: string
      phenomenon_of_interest: string
      design: string
      evaluation: string
      research_type: string
    domain_hint: string         # ml/nlp/cv/medicine/hci/...
    must_include_dbs: [...]     # 用户强制要查的库
    exclude_dbs: [...]
    review_mode: quick_review | literature_review | systematic_review | scoping_review | sota | gap_finding
    audience_profile: beginner | mixed | expert
    minimum_depth:
      min_included_papers: int
      min_fulltext_ratio: float
      min_themes: int
```

### 反问规则
- 若用户没给 framework,默认 `none`(不强求 PICO)
- `output_form=systematic_review` 必须问 PICO/PECO 之一
- `output_form=sota` 必须问 `time_window`(SOTA 没时间窗没意义)
- 若用户说"做文献综述",默认 `review_mode=literature_review`,不是 quick_review
- 若用户只说"帮我看看最新进展",默认先按 `quick_review` 起步,除非用户明确要正式综述
- 若用户没说明读者是谁,默认 `audience_profile=mixed`

### 深度默认值

```yaml
custom:
  review_mode: literature_review
  audience_profile: mixed
  minimum_depth:
    min_included_papers: 12
    min_fulltext_ratio: 0.8
    min_themes: 3
```

---

## 2. `hook_retrieve`

### 替换为学术渠道
按 `channels.md` 的优先级矩阵跑。

### 除 `raw_materials[]` 外,必须落 2 个中间产物:

- `research_question.md` — 把调研问题、范围、时间窗、review_mode 写死
- `search_queries.md` — 记录每一轮 query / db / 过滤条件 / 召回数 / 为什么加这一轮

### 输出 `raw_materials[]` 时,`metadata` 必须含:

```yaml
metadata:
  paper_id: string             # DOI / arXiv ID / S2 ID
  authors: [string]
  year: int
  venue: string                # 会议 / 期刊名
  abstract: string
  citation_count: int          # 若库返回
  pdf_url: string              # 若可获取
```

`source_type` 取值固定为 `paper`。

### 最低要求
- 至少 2 个独立 DB
- 至少 2 轮检索(初始检索 + gap-driven 回补)
- 若只跑单库单轮,后续最高只能降级为 `quick_review`

---

## 3. `hook_screen`

### 默认筛选规则被替换为:

1. **DOI / arXiv ID 去重**(优先于 title 哈希)
2. **PICO/PECO 命中检查**(若 clarify 给了 framework)
3. **active learning 排序**:把候选按 `relevance_score` 排序,top N 自动 include,中段进 uncertain,尾部 exclude(抄 asreview)
4. **abstract-only 三档**:确定相关 / 模糊 / 确定无关
5. uncertain 走人工(主 skill 默认行为)

### 必须生成 `study_selection.csv`

每条候选都保留:

```csv
material_id,title,db,selection,selection_reason,fulltext_available,theme_guess,duplicate_of
```

这份日志是学术综述和“简单概述”的分水岭。没有它,review 直接降级。

### `criteria.custom` 扩展:

```yaml
custom:
  pico_threshold: int          # 至少命中几个 PICO 维度才算 include
  active_learning:
    initial_seeds: int         # 用户标注的种子论文数,默认 5
    batch_size: int            # 每轮 active 学习批次,默认 20
  language_filter: [en, zh, ...]
  exclude_venue_types: [workshop, position]   # 可选
```

---

## 4. `hook_extract`

### 每篇论文的 evidence_record 必须填:

```yaml
custom:
  method: string               # 方法名 / 模型名
  dataset: [string]            # 用了什么数据集
  metric: [{name, value}]      # 关键指标
  result: string               # 主要结论
  limitation: string           # 作者声明的限制
  contribution: string         # 论文自己宣称的贡献
  reproducibility:             # 可选,代码 / 数据是否开源
    code_url: string
    data_url: string
```

### 除 evidence_record 外,必须生成 2 类分析产物

#### A. `paper_notes/`
每篇 included paper 一份笔记,文件名建议 `{material_id}.md`,至少包含:

```markdown
# {paper title}

- Research question
- Method / system design
- Data / benchmarks
- Key metrics
- Main contribution
- Author-stated limitations
- This paper matters because ...
- Fits which theme(s)
- Supports / contradicts which other papers
```

#### B. `comparison_matrix.csv`
按 paper 粒度对比,至少含:

```csv
material_id,paper_title,year,method_family,retrieval_strategy,reasoning_strategy,datasets,main_metric,claimed_gain,limitations,theme
```

如果没有 `paper_notes/` 和 `comparison_matrix.csv`,synthesize 不得直接开始。

### 拆分规则
一篇论文可能拆成多条 evidence_record(一条声明一个 claim),但 `material_id` 相同,`id` 不同。

### 引用规范
- 全文可获取:`source.locator` 必填到 section + table/figure 编号
- 仅摘要:`source.locator` 写 `"abstract"`,confidence 自动 -0.2

---

## 5. `hook_synthesize`

### 改为两段式综合

#### Stage 5A. 先出分析骨架
- `theme_outline.md`
- `comparison_matrix.csv` 补齐或修正
- 冲突簇 / 方法谱系 / 时间线草稿(若适用)

#### Stage 5B. 再出最终成文
- `literature_review.md`
- `reader_guide.md`
- `evidence_table.csv`
- `research_gaps.md`
- `references.bib`

没有 5A,就不应该直接开始 5B。

### `summary_claims[]` 必须包含:
- 至少 3 条主题级共识
- 至少 1 条强冲突点(若有)
- 至少 3 条 research gap
- 至少 3 条 comparison-driven claim(不是单篇论文摘要,而是跨论文比较后的判断)

### Tier 处理
- Tier 1 / Tier 2 → 直接进 literature_review
- Tier 3 → 只进 research_gaps,标 ⚠
- Tier 0 → 不进任何输出

### 写作约束
- 主文默认按**主题 / 方法谱系 / 争议点**组织,不是按论文顺序流水账
- 每个主题段落至少要引用 2 篇论文,否则该主题不够稳
- 必须显式写"哪些论文代表这条路线""哪些论文在反驳或修正这条路线"
- 至少保留 1 节"方法比较"而不是纯 narrative summary

### 受众约束
- `literature_review.md` 默认写给专业读者
- `reader_guide.md` 默认写给非专业读者或跨领域读者
- 若 `audience_profile=mixed`,两份都必须出
- `reader_guide.md` 必须解释:
  - 这个方向在解决什么问题
  - 为什么值得关心
  - 现在主流做法有哪些(不用术语堆叠)
  - 进展到哪了
  - 还有哪些地方没解决(研究空白 = 还没被研究清楚的问题)

### subtype 分支
- `systematic_review` → 加 prisma_flow.md
- `sota` → 加 timeline.md
- `gap_finding` → research_gaps.md ≥ 5 条

---

## 6. `hook_review`

### 在主 skill 默认复核之上,加:

#### A. adequacy gate(先于其他检查)

要被允许叫 `literature_review`,至少满足:

- included papers >= `minimum_depth.min_included_papers`
- full-text ratio >= `minimum_depth.min_fulltext_ratio`
- 独立主题数 >= `minimum_depth.min_themes`
- 已落 `study_selection.csv`
- 已落 `paper_notes/`
- 已落 `comparison_matrix.csv`
- 已落 `theme_outline.md`

否则:
- `status` 不能是 `passed as literature review`
- 必须降级标记为 `quick_review` 或 `scoping_note`

#### B. PRISMA flow(systematic_review 必出)

```
Identification: N1 records
   ↓
Screening:      N2 after dedup
   ↓
Eligibility:    N3 full-text reviewed
   ↓
Included:       N4 in synthesis
```

落到 `prisma_flow.md`。

#### C. 引用合规
- evidence_table.csv 的 id ↔ references.bib 的 key 一一对应
- literature_review.md 的所有 [E-XXX] 都能在表里找到
- 缺一即 `status=needs_human_review`

#### D. 时效检查
- 若 `time_window` 是"最近"且 80% 以上证据 >36 个月 → 警告

#### E. 顶会偏倚检查
- 若所有证据 100% 来自单一会议(如全 NeurIPS) → 警告"来源单一"

#### F. 结构深度检查
- 若正文主要是单篇摘要堆叠,缺少 comparison-driven claims → `needs_human_review`
- 若没有明确的 negative / limitation cluster → 警告"综述过于顺滑,可能分析不足"
- 若没有 `reader_guide.md` 且 `audience_profile != expert` → `needs_human_review`

---

## 不覆盖的钩子

(本包覆盖全部 6 个,无未覆盖项)

---

## 与 schema 的兼容性

- 本包**只在 `custom` 加字段**,不改主字段名 / 含义
- 若未来需要主 skill 加字段,走 `../../base/references/breaking-changes.md` 流程(待建)
