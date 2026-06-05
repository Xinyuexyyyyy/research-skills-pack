# Paper Discovery — 钩子覆盖

> 接口契约见 `research-base/hooks.md`。本文件只描述本 skill 在每个 hook 上做什么、不做什么。

## 0. 覆盖矩阵

| 钩子 | 覆盖 | 主要工作 |
|---|---|---|
| `hook_clarify` | 部分 | 补 search_plan / 必查 db / 排除 db / 时间窗 |
| `hook_retrieve` | 完全 | 走 `channels.md` 的多 db 多轮检索 |
| `hook_screen` | 仅去重 | **不做纳排**,只做 dedup;不写 `selection` |
| `hook_extract` | 仅 metadata | 补 abstract / authors / venue / year / pdf_url 等 metadata,不抽 evidence |
| `hook_synthesize` | 候选池产出 | 输出 `candidate_papers.csv` + `references.bib` + `import_manifest.json` |
| `hook_review` | 完整性自检 | 检查 source_log ↔ candidate_papers 的引用完整性 |

## 1. `hook_clarify`

### 输入
`research-academic/routing.md` 给出的 routing_decision(含 `academic_subtype`、`domain_hint`、`preferred_databases`),以及用户原始输入。

### 必填字段(在 `clarified_question.custom`)
```yaml
custom:
  research_question: string         # 一句话研究问题
  keywords:
    primary: [string]               # 主关键词
    synonyms:                        # 同义词组
      - [string]                    #   每组一个 OR 集合
  time_window: [start_year, end_year]
  must_include_dbs: [string]        # 至少 2 个学术 db
  exclude_dbs: [string]
  preferred_pdf_source: arxiv | publisher | none
  domain_hint: string               # 同 routing_decision
  seed_papers:                       # 可选,用户给的必含论文
    - paper_uid | doi | arxiv_id | url
  per_db_recall_cap: int            # 单库召回上限,默认 50
  total_recall_cap: int             # 总召回上限,默认 200
```

### 反问规则
- 没有 `research_question` → 必反问
- `must_include_dbs` 数量 < 2 → 自动补到 ≥ 2(P0:`arxiv` + `semantic_scholar` 默认双开)
- 时间窗缺 → 默认 24 个月,且在 `notes` 里说明
- domain 不明 → 跟 router 给的 domain_hint 走;router 也不明则视为 `none`

## 2. `hook_retrieve`

### 行为
- 严格按 `channels.md` 的 P0/P1/P2 矩阵执行
- 至少 2 个独立学术源 + 至少 2 轮检索(初始 + gap-driven 回补)
- 每条命中产出 1 行 `source_log.csv` 与 1 行(可能合并的)`candidate_papers.csv`
- 单 db 召回 ≤ `per_db_recall_cap`,总召回 ≤ `total_recall_cap`(避免上下文爆炸)

### 输出
- `raw_materials[]`(主 skill 标准结构)
- `source_log.csv`(强制落,见 `research-base/artifacts.md` §2)
- `search_plan.md`(把 clarified_question.custom 落到文件)
- `search_queries.md`(每一轮 query 的明细,可与 search_plan 合并)

### 元数据完整性
每条 `raw_materials[i].metadata` 必须含:
```yaml
paper_id: string                 # 优先 DOI,其次 arxiv,其次 s2/openalex/pmid
title: string
authors: [string]
year: int
venue: string
abstract: string                 # 若 db 返回
pdf_url: string                  # 若可获取
landing_url: string              # 必填
citation_count: int              # 若 db 返回
```

`source_type` 固定为 `paper`。

## 3. `hook_screen`(只做去重,不做纳排)

### 行为
- 去重优先级:`doi → arxiv_id → s2_id → openalex_id → pmid → title fingerprint`
- title fingerprint 见 `research-base/artifacts.md` §1.4
- 重复合并时:保留**第一个被命中**的行作为主行,其余行 `dedup_status="duplicate_of:<paper_uid>"` 留在 csv 里
- 同一篇被多 db 命中时,在主行的 `source_ids` 里以 `;` 分隔合并

### 不做
- 不写 `selection`(`include` / `exclude` / `uncertain`)
- 不写 `prisma_bucket`
- 不写 `selection_reason_code`
- 不评估论文质量

### 产出
- 更新后的 `candidate_papers.csv`(`dedup_status` / `dedup_method` / `source_ids` 字段填好)
- `dedup_log.md`(可选,但合并行数 ≥ 10 时建议产出)

## 4. `hook_extract`(只补 metadata,不抽 evidence)

### 行为
- 对每个候选,补齐 `candidate_papers.csv` 中可空字段:
  - 若 db 没给 `abstract`,尝试从 landing_url 抓
  - 若 db 没给 `pdf_url`,尝试从 arxiv / publisher 推断
  - 标准化 authors / venue 格式
  - 写 `references.bib` 中对应的 BibTeX entry
- `evidence_records[]` **不产出**(本 skill 输出空数组)
- 任何"我读了摘要总结一下"都不允许进入本 skill 的产物

### 产出
- `candidate_papers.csv` 字段更全
- `references.bib`(每候选一条 BibTeX)
- `evidence_records[]: []`(空数组,合规)

## 5. `hook_synthesize`(只产出候选池工件)

### 行为
- 产出 `import_manifest.json`(总结本批导入)
- 产出 `missing_papers.md`(若有找不到全文的)
- 不写综述、不写 theme outline、不写 reader guide

### `import_manifest.json` 字段
```json
{
  "discovery_run_id": "string",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "research_question": "string",
  "rounds": 2,
  "dbs_queried": ["arxiv", "semantic_scholar", "openalex"],
  "hits_by_db": { "arxiv": 128, "semantic_scholar": 210, "openalex": 42 },
  "before_dedup": 380,
  "after_dedup": 287,
  "candidate_papers_path": "candidate_papers.csv",
  "source_log_path": "source_log.csv",
  "references_bib_path": "references.bib",
  "coverage_check": {
    "min_dbs_met": true,
    "min_rounds_met": true,
    "min_unique_candidates": 287,
    "warnings": []
  },
  "next_recommended_skill": "paper-screening"
}
```

## 6. `hook_review`(候选池完整性自检)

### 必检项(任一不通过都要在 manifest 的 warnings 里登记)
- `min_dbs_met`:`source_log.csv` 中 distinct(`db`) ≥ 2
- `min_rounds_met`:`source_log.csv` 中 max(`round`) ≥ 2
- `id_completeness`:`candidate_papers.csv` 中,无稳定 ID(DOI/arxiv/s2/openalex/pmid 全空)的比例 ≤ 5%,且这些都在 `notes` 里说明
- `source_ids_intact`:`candidate_papers.csv` 中所有 `source_ids` 引用都能在 `source_log.csv` 中找到
- `dedup_consistency`:`dedup_status=duplicate_of:<X>` 中的 X 必须在同表中以 `unique` 出现

### 状态
- 全通过 → `coverage_check.status = passed`,直接 manifest 标记 `next_recommended_skill = paper-screening`
- 有 warning 但非阻塞(如 `min_dbs_met=true` 但 `min_rounds_met=false`)→ `coverage_check.status = warned`,manifest 列出 warnings,仍可移交但下游应注意
- 阻塞性失败(`min_dbs_met=false` 或 `id_completeness < 95%`)→ `coverage_check.status = failed`,**不允许直接移交 paper-screening**,要求重跑或人工介入

### 产出
- `coverage_check` 字段写入 `import_manifest.json`
- 阻塞性失败时另写 `discovery_review_notes.md`,人话列出问题与建议

## 7. 不覆盖说明

本 skill 不接管 `paper-screening` / `paper-reading` / `survey-writer` 的工作。任何"顺便做一下"都不允许。
