# Paper Discovery — 产物 schema(本 skill 视角)

> 主 schema 在 `research-base/artifacts.md`。本文件只列**本 skill 实际写入的 csv 字段子集**与**本 skill 不写的字段**,避免下游误读。

## 1. 本 skill 写入的产物

| 文件 | 主 schema | 备注 |
|---|---|---|
| `source_log.csv` | `research-base/artifacts.md` §2 | 全字段都由本 skill 填,`custom_*` 仅在 db 返回特殊元数据时使用 |
| `candidate_papers.csv` | `research-base/artifacts.md` §3 | 见下方"本 skill 写入字段子集" |
| `references.bib` | (BibTeX 标准) | 每行候选 1 条 entry,key 含 `% paper_uid:` 注释 |
| `import_manifest.json` | 本 skill 自有 | 字段见 `hooks.md` §5 |
| `search_plan.md` / `search_queries.md` / `missing_papers.md` / `dedup_log.md` | 自有(无强 schema,模板见 `report-template.md`) | |

## 2. `candidate_papers.csv` — 本 skill 写入字段子集

### 必写
- `paper_uid`
- `title`
- `authors`
- `year`
- `landing_url`
- `source_ids`
- `first_seen_at`
- `dedup_status`(`unique` 或 `duplicate_of:<paper_uid>`)

### 强烈建议
- `doi` / `arxiv_id` / `s2_id` / `openalex_id` / `pmid`(至少 1 个)
- `venue`
- `abstract`
- `pdf_url`
- `language`
- `dedup_method`(若 `dedup_status != unique`)

### 可写
- `citation_count`
- `notes`
- `custom_*`

### **绝对不写**(留给 paper-screening)
- `selection`
- `selection_reason_code`
- `selection_reason_text`
- `criteria_hits_*`
- `confidence`(纳排维度的置信)
- `prisma_bucket`
- `fulltext_checked`
- `decided_by`
- `decided_at`
- `screening_stage`

> 注:这些字段不属于 `candidate_papers.csv`(它们在 `study_selection.csv`),本节列出来是为了避免有人把它们错放进本 skill 的产物。

## 3. `source_log.csv` — 本 skill 写入约束

- 同一 query 跑多次只允许有 1 行(用 `executed_at` 区分多日运行)
- `db` 字段只能取学术 db 枚举值(见主 schema §2)
- `notes` 在 round ≥ 2 时必填,说明加这条 query 的理由

## 4. `import_manifest.json` 字段

```json
{
  "schema_version": "v0",
  "discovery_run_id": "string",
  "started_at": "ISO8601",
  "ended_at": "ISO8601",
  "research_question": "string",
  "rounds": 2,
  "dbs_queried": ["arxiv", "semantic_scholar"],
  "hits_by_db": { "arxiv": 128, "semantic_scholar": 210 },
  "before_dedup": 380,
  "after_dedup": 287,
  "candidate_papers_path": "candidate_papers.csv",
  "source_log_path": "source_log.csv",
  "references_bib_path": "references.bib",
  "coverage_check": {
    "min_dbs_met": true,
    "min_rounds_met": true,
    "id_completeness": 0.97,
    "source_ids_intact": true,
    "dedup_consistency": true,
    "warnings": [],
    "status": "passed"
  },
  "next_recommended_skill": "paper-screening"
}
```

## 5. references.bib 命名规则

- key:`{firstauthor_lastname}{year}{first_word}`,全小写,无标点
- 必含 `% paper_uid: <paper_uid>` 注释(单行,在 entry 内)
- 一篇论文有多条 BibTeX 时(arxiv preprint + journal published),只写**一条**,优先取期刊版,paper_uid 仍以主表为准

## 6. 与 research-base 主 schema 的版本

- 本 skill 兼容 `research-base/artifacts.md` v0
- 升版时,本 skill 必须显式声明兼容的最小版本号,在 `import_manifest.schema_version` 字段里写

## 7. 字段扩展

本 skill 真的需要新增字段时:

- 优先放进 `candidate_papers.custom_*`(如 `custom_funder` / `custom_open_access_status`)
- 真的要提到主 schema → 走 `research-base/artifacts.md` §7 的"字段扩展规则"
- **绝对不要**新增名字与主 schema 重复的字段
