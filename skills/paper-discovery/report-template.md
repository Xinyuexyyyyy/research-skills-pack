# Paper Discovery — 产物骨架

最终产物是一个目录,包含**检索计划 + 检索日志 + 候选池 + 引用库 + manifest**。如果只产出 `candidate_papers.csv` 而不带 `source_log.csv` 和 `references.bib`,本 skill 视为不完整。

## 1. 目录结构

```
{run_dir}/
├── search_plan.md          # 研究问题 / 关键词 / 时间窗 / 必查 db / 排除 db / 计划轮次
├── search_queries.md        # 每一轮 query / db / filters / hits / 为什么加
├── source_log.csv           # 见 research-base/artifacts.md §2
├── candidate_papers.csv     # 见 research-base/artifacts.md §3
├── references.bib           # BibTeX,所有候选一条 entry
├── import_manifest.json     # 本批导入元信息(见 hooks.md §5)
├── missing_papers.md        # 找不到全文的论文(可空)
└── dedup_log.md             # 去重合并明细(可选)
```

## 2. `search_plan.md`

```markdown
# Search Plan

- Research question:
- Domain hint:
- Time window: [start_year, end_year]
- Output target: candidate_papers.csv (≥ N)
- Subtype hint: literature_review | systematic_review | scoping_review | sota | gap_finding

## Keywords
- Primary: [...]
- Synonyms:
  - Group 1: [a, a', a''] (OR)
  - Group 2: [b, b', b''] (OR)

## DBs
- must_include: [...]
- exclude: [...]

## Recall caps
- per_db: 50
- total: 200

## Planned rounds
- round 1: initial recall on must_include dbs
- round 2: gap-driven expansion based on round 1 misses
- round 3 (optional): P2 fallback if min_candidates not met

## Seed papers (if any)
- DOI / arXiv ID / URL: ...
```

## 3. `search_queries.md`

```markdown
# Search Queries

## Round 1 — initial recall
- DB: arxiv
  - Query: "retrieval augmented generation"
  - Filters: year=2023-2026
  - Hits: 128
  - Imported: 50
- DB: semantic_scholar
  - Query: "retrieval augmented generation"
  - Filters: year=2023-2026
  - Hits: 210
  - Imported: 50

## Round 2 — gap-driven expansion
- Gap observed: round 1 未覆盖 graph-based RAG
- DB: openalex
  - Query: "graph rag multi-hop"
  - Filters: year=2024-2026
  - Hits: 42
  - Imported: 30
```

## 4. `source_log.csv`

直接按 `research-base/artifacts.md` §2 的 schema 写,字段一字不差。最小样例见主 schema 文件。

## 5. `candidate_papers.csv`

直接按 `research-base/artifacts.md` §3 的 schema 写。本 skill 必填字段:

- `paper_uid`(强约束)
- `title` / `authors` / `year` / `landing_url`
- `db` 通过 `source_ids` 间接体现(本表本身没有 `db` 字段;`db` 在 `source_log.csv`)
- `dedup_status` / `dedup_method`
- `source_ids`(`;` 分隔,引用 `source_log.source_id`)
- `first_seen_at`

本 skill 留空(交给 paper-screening 写)的字段:
- 不要写 `selection`、`selection_reason*`、`prisma_bucket`、`fulltext_checked` —— 这些在 `study_selection.csv` 中

> 注:`research-base/artifacts.md` §3 的 schema 已经把"纳排"字段都放在了 `study_selection.csv`,不在 `candidate_papers.csv` 里。本 skill 严格按主 schema 即可,不会越界。

## 6. `references.bib`

- 每候选一条 BibTeX entry
- key 命名:`{firstauthor_lastname}{year}{first_word}` 全小写,无特殊字符
- arXiv 用 `@misc { ..., archivePrefix={arXiv}, eprint={...} }`
- 期刊会议用 `@article` / `@inproceedings`
- 必须能反查回 `paper_uid`(在 entry 注释里写 `% paper_uid: doi:10.xxxx/yyyy`)

示例:

```bibtex
@misc{lewis2020retrieval,
  title={Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks},
  author={Lewis, Patrick and others},
  year={2020},
  archivePrefix={arXiv},
  eprint={2005.11401}
  % paper_uid: arxiv:2005.11401
}
```

## 7. `import_manifest.json`

字段见 `hooks.md` §5。这是**移交给 paper-screening 的"交接单"**:

- `next_recommended_skill = paper-screening`
- `coverage_check.status` 必须 `passed` 或 `warned`,`failed` 时不允许移交

## 8. `missing_papers.md`(可空)

```markdown
# Missing Full Texts

| paper_uid | title | reason | follow-up |
|---|---|---|---|
| arxiv:2305.12345 | ... | PDF 404 | 用 web archive 重试或后续 paper-reading 阶段处理 |
```

## 9. `dedup_log.md`(可选)

```markdown
# Dedup Log

## Merged groups (共 N 组)
- Group A: doi:10.x → arxiv:2305.xxxxx → s2:abcdef
  - Reason: same DOI
  - Kept: doi:10.x
- ...
```

## 10. 自检 checklist(对接 `hook_review`)

提交前必须自检:

- [ ] `search_plan.md` 已落
- [ ] `search_queries.md` 至少 2 轮
- [ ] `source_log.csv` 至少 2 个独立 db,至少 2 轮
- [ ] `candidate_papers.csv` 中 `paper_uid` 唯一,`source_ids` 不空
- [ ] 重复行用 `dedup_status=duplicate_of:<paper_uid>` 标记,主行 `dedup_status=unique`
- [ ] `references.bib` 条数 = `dedup_status=unique` 的行数
- [ ] `import_manifest.json` 写完且 `coverage_check.status ∈ {passed, warned}`
- [ ] **没有任何** `selection` / `prisma_bucket` 字段被本 skill 写入
