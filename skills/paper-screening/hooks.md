# Paper Screening — 钩子覆盖

> 接口契约见 `research-base/hooks.md`。本文件描述本 skill 在每个 hook 上做什么。

## 0. 覆盖矩阵

| 钩子 | 覆盖 | 主要工作 |
|---|---|---|
| `hook_clarify` | 部分 | 补 framework / review_type / criteria_seed / language_filter / min_included |
| `hook_retrieve` | ⛔ 不覆盖 | 不检索 |
| `hook_screen` | 完全 | criteria → active learning → 4-Tier → 标题摘要 → 全文 |
| `hook_extract` | ⛔ 不覆盖 | 不抽 evidence |
| `hook_synthesize` | 轻量 | PRISMA flow + screening summary |
| `hook_review` | 完全 | adequacy gate + 跨文件一致性自检 |

## 1. `hook_clarify`

### 必填字段(在 `clarified_question.custom`)
```yaml
custom:
  review_type: literature_review | systematic_review | scoping_review | sota | gap_finding
  framework: PICO | PECO | SPIDER | none
  pico:                                 # framework=PICO 必填
    population: string
    intervention: string
    comparison: string
    outcome: string
  peco:                                 # framework=PECO 必填
    population: string
    exposure: string
    comparison: string
    outcome: string
  spider:                               # framework=SPIDER 必填
    sample: string
    phenomenon_of_interest: string
    design: string
    evaluation: string
    research_type: string
  language_filter: [en, zh, ...]
  exclude_venue_types: [workshop, position, demo]   # 可选
  min_included: int                     # 期望入选数,影响 active learning 停止
  fulltext_required: bool               # 是否必须看全文,默认按 review_type 决定
  decided_by_default: auto | human | hybrid    # 默认决策模式,默认 hybrid
  active_learning:
    initial_seeds: int                  # 用户标注的种子数,默认 5
    batch_size: int                     # 每轮批次,默认 20
    stop_after_batches_without_include: int   # 连续 N 批无新 include 则停止,默认 3
```

### 反问规则(继承自 `routing.md` §6)
- 缺 `review_type` → 必反问
- `framework=none` 时,跳过 PICO/PECO/SPIDER,改为主题相关性筛选(基于研究问题 + keywords)
- `min_included` 缺 → 默认按 review_type 推断:
  - systematic_review: 12
  - scoping_review: 20(范围更广)
  - literature_review: 15
  - sota: 10
  - gap_finding: 8

## 2. `hook_retrieve`(不覆盖)

不检索。输入由上一阶段的 `paper-discovery` 提供 `candidate_papers.csv`(`dedup_status=unique` 行)。

若候选池不足以做严格 review,本 skill 不补检索,而是在 `screening_summary.md` 写"候选池规模不足,建议回到 paper-discovery 加 N 轮 gap-driven 检索"。

## 3. `hook_screen`(完全覆盖,核心)

### Step A — 起草 `criteria.json`

```json
{
  "schema_version": "v0",
  "review_type": "systematic_review",
  "framework": "PICO",
  "include": [
    { "id": "INC-1", "rule": "population matches: ...", "type": "PICO_P" },
    { "id": "INC-2", "rule": "intervention matches: ...", "type": "PICO_I" },
    { "id": "INC-3", "rule": "outcome matches: ...", "type": "PICO_O" },
    { "id": "INC-T", "rule": "topic relevant", "type": "topic" }
  ],
  "exclude": [
    { "id": "EXC-1", "rule": "wrong population", "code": "exc_wrong_pop" },
    { "id": "EXC-2", "rule": "year out of window", "code": "exc_year_out_of_window" },
    { "id": "EXC-3", "rule": "language not in [en, zh]", "code": "exc_language" },
    { "id": "EXC-4", "rule": "venue is workshop/position", "code": "exc_venue_blacklist" }
  ],
  "uncertain_policy": {
    "borderline_pico_threshold": 2,
    "human_review_required_when": ["selection=uncertain", "confidence<0.7"]
  },
  "dedup_key": ["doi", "arxiv_id", "s2_id", "openalex_id", "pmid", "title_fingerprint"]
}
```

每条 rule 必须有 `id`,以便 `study_selection.criteria_hits_*` 字段引用。

### Step B — Title/Abstract 筛选(`screening_stage=title_abstract`)

#### 决策逻辑(对每个 paper_uid)
1. 用 LLM + criteria.json 判定 → 输出 `selection ∈ {include, exclude, uncertain}` + `confidence` + `criteria_hits_*`
2. 命中 4-Tier 决策路由:
   - **Tier 1(auto-include)**:`confidence ≥ 0.85` 且 `selection=include` 且至少命中 2 条 include rule → `decided_by=auto`
   - **Tier 2(auto-exclude)**:`confidence ≥ 0.85` 且 `selection=exclude` 且命中明确 exclude rule → `decided_by=auto`
   - **Tier 3(borderline)**:`0.5 ≤ confidence < 0.85` 或 PICO 部分命中 → `selection=uncertain` + `decided_by=active_learning`(进入下一轮)
   - **Tier 4(human-required)**:`confidence < 0.5` 或冲突信号 → `selection=uncertain` + `decided_by=human_after_uncertain`,等用户复核

#### Active Learning 排序(借鉴 asreview)
1. 用户标注 `initial_seeds` 篇种子(可由 routing 阶段提供)
2. LLM 给所有候选打 `relevance_score`(0-1)
3. 按 score 降序排队
4. 每轮取 top `batch_size` 进入决策
5. 若连续 `stop_after_batches_without_include` 轮无新 include,停止
6. 剩余未触达的批量打 `selection=exclude` + `selection_reason_code=exc_off_topic`(active learning 兜底)

#### 落 `study_selection.csv`(必须每个 candidate 一行)
- 同一 paper_uid 在 title_abstract 阶段一行
- `prisma_bucket`:
  - title_abstract `selection=exclude` → `prisma_bucket=excluded`
  - title_abstract `selection=include` 或 `uncertain` → `prisma_bucket=screened`(后续到 fulltext 阶段再更新)

### Step C — Full-text 筛选(`screening_stage=fulltext`,可选)

仅当 `review_type ∈ {systematic_review, scoping_review}` 或用户显式要求时启动。

1. 对 title_abstract 阶段 `selection != exclude` 的论文,拉全文(`pdf_url` 优先)
2. 全文不可得 → `selection=exclude` + `selection_reason_code=exc_no_fulltext`
3. 全文可得 → 重新判定 `selection`,新增一行 `screening_stage=fulltext`
4. `prisma_bucket`:
   - 进入 fulltext 即 `prisma_bucket=eligible`
   - fulltext `selection=include` → 同 paper_uid 加一行 `screening_stage=final`,`prisma_bucket=included`
   - fulltext `selection=exclude` → `prisma_bucket=excluded`

### Step D — Final 阶段(`screening_stage=final`)

- 把所有最终入选(fulltext include 或 review_type=literature_review 时直接以 title_abstract include 为准)的论文加一行 `screening_stage=final`,`selection=include`,`prisma_bucket=included`
- 这是 `paper-reading`(P1)的输入

## 4. `hook_extract`(不覆盖)

不抽 evidence。`evidence_records[]` 输出空数组。

任何"我读了摘要做个笔记"都不允许进入本 skill。

## 5. `hook_synthesize`(轻量覆盖)

仅产出:
- `prisma_flow.md`:从 `study_selection.csv` group by `prisma_bucket` 聚合
- `screening_summary.md`:三段:做了什么 / 结果 / 下一步
- `exclusion_reasons.csv`:每个 exclude 原因码 1 行,带 count

不写综述、不写 theme outline、不写 reader_guide。

### `prisma_flow.md` 模板

```markdown
# PRISMA Flow

## Identification
- Records identified: {count where prisma_bucket=identified} (from candidate_papers.csv)

## Screening
- Records after dedup: {count distinct paper_uid in candidate_papers where dedup_status=unique}
- Records screened (title/abstract): {count where screening_stage=title_abstract}
- Records excluded after title/abstract: {count where screening_stage=title_abstract & selection=exclude}

## Eligibility
- Full-text assessed: {count where screening_stage=fulltext}
- Full-text excluded:
  | reason_code | count |
  | exc_no_fulltext | N1 |
  | exc_wrong_pop | N2 |
  | ... | ... |

## Included
- Studies included in final synthesis: {count where screening_stage=final & selection=include}
```

## 6. `hook_review`(完全覆盖)

### A. adequacy gate(对应 review_type)

| review_type | 最小要求 |
|---|---|
| systematic_review | included ≥ 12;PRISMA flow 必出;每个 exclude 都有 reason_code;fulltext_checked 比例 ≥ 0.8 |
| scoping_review | included ≥ 20;允许 broader 主题分类;不强求 fulltext_checked |
| literature_review | included ≥ 15;允许 abstract-only 决策 |
| sota | included ≥ 10;recency 强制(`year ≥ now - time_window`) |
| gap_finding | included ≥ 8 |

不达标 → `screening_summary.status = warned`,且在 `screening_summary.md` 明确写"不达 systematic review 要求,降级为 X"。

### B. 跨文件一致性自检(对接 `research-base/artifacts.md` §6)

必检:
1. `study_selection.csv` 中所有 `paper_uid` 必须在 `candidate_papers.csv` 中且 `dedup_status=unique`
2. 同一 `(paper_uid, screening_stage)` 不允许重复行
3. PRISMA bucket 数字自洽:`identified ≥ screened ≥ eligible ≥ included`,且 `excluded` 与累积排除一致
4. `screening_stage=final & selection=include` 的 paper_uid 集合 = `prisma_bucket=included` 的 paper_uid 集合

不通过 → `coverage_check.status=failed`,**不允许移交 paper-reading**。

### C. 决策审计

落 `screening_audit.json`:

```json
{
  "schema_version": "v0",
  "review_type": "systematic_review",
  "framework": "PICO",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "candidates_in": 287,
  "title_abstract_decisions": {
    "auto_include": 12,
    "auto_exclude": 198,
    "uncertain_to_human": 24,
    "human_after_uncertain_resolved": { "include": 18, "exclude": 6 }
  },
  "fulltext_decisions": {
    "fulltext_assessed": 30,
    "fulltext_unavailable": 5,
    "include": 22,
    "exclude": 3
  },
  "final_included": 22,
  "active_learning": {
    "initial_seeds": 5,
    "batches_run": 8,
    "batch_size": 20,
    "stopped_reason": "3 consecutive batches without new include"
  },
  "adequacy_gate": {
    "min_included_met": true,
    "fulltext_ratio": 0.83,
    "status": "passed"
  },
  "next_recommended_skill": "paper-reading"
}
```

## 7. 不覆盖说明

- 不接管 paper-discovery 的检索任务
- 不接管 paper-reading 的证据抽取任务
- 不接管 survey-writer 的写作任务
