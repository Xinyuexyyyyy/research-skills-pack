# Paper Screening — 产物骨架

最终产物是一个目录,包含**criteria + 选择决策 + 排除原因 + PRISMA 流 + 审计 + 总结**。

## 1. 目录结构

```
{run_dir}/
├── criteria.json                 # 纳入 / 排除规则,带规则 ID
├── study_selection.csv           # 见 research-base/artifacts.md §4
├── exclusion_reasons.csv         # 排除原因码统计(每码一行)
├── prisma_flow.md                # PRISMA 四档流程(text)
├── screening_audit.json          # 决策审计(decided_by 分布、AL 轮次)
├── screening_summary.md          # 给用户的"看完一眼就懂"的总结
└── (可选)human_review_queue.md   # 等待人工复核的论文列表
```

## 2. `criteria.json` 模板

```json
{
  "schema_version": "v0",
  "review_type": "systematic_review",
  "framework": "PICO",
  "framework_fields": {
    "population": "...",
    "intervention": "...",
    "comparison": "...",
    "outcome": "..."
  },
  "include": [
    { "id": "INC-1", "rule": "population matches PICO P", "type": "PICO_P" },
    { "id": "INC-2", "rule": "intervention matches PICO I", "type": "PICO_I" },
    { "id": "INC-3", "rule": "outcome matches PICO O", "type": "PICO_O" },
    { "id": "INC-4", "rule": "study type ∈ {RCT, cohort}", "type": "design" }
  ],
  "exclude": [
    { "id": "EXC-Y", "rule": "year not in [2020, 2026]", "code": "exc_year_out_of_window" },
    { "id": "EXC-L", "rule": "language not in [en, zh]", "code": "exc_language" },
    { "id": "EXC-V", "rule": "venue ∈ {workshop, position, demo}", "code": "exc_venue_blacklist" },
    { "id": "EXC-P", "rule": "wrong population", "code": "exc_wrong_pop" },
    { "id": "EXC-I", "rule": "wrong intervention", "code": "exc_wrong_intervention" },
    { "id": "EXC-O", "rule": "wrong outcome", "code": "exc_wrong_outcome" }
  ],
  "uncertain_policy": {
    "borderline_pico_threshold": 2,
    "human_review_required_when": ["selection=uncertain", "confidence<0.7"]
  },
  "dedup_key": ["doi", "arxiv_id", "s2_id", "openalex_id", "pmid", "title_fingerprint"],
  "active_learning": {
    "initial_seeds": 5,
    "batch_size": 20,
    "stop_after_batches_without_include": 3
  },
  "min_included": 12
}
```

## 3. `study_selection.csv`

直接按 `research-base/artifacts.md` §4 的 schema 写,字段一字不差。

特别提示:
- 同一 `paper_uid` 可有多行(title_abstract / fulltext / final 各一行)
- `selection_reason_code` 必须从 `research-base/artifacts.md` §4.1 的标准原因码里选
- `criteria_hits_include` / `criteria_hits_exclude` 引用 `criteria.json` 的 `id`,以 `;` 分隔

## 4. `exclusion_reasons.csv`

```csv
reason_code,count,prisma_stage,examples_paper_uid
exc_off_topic,180,title_abstract,arxiv:2301.12345;doi:10.x;...
exc_year_out_of_window,12,title_abstract,arxiv:1801.99999;...
exc_no_fulltext,5,fulltext,doi:10.zzzz/yyy
exc_wrong_pop,3,fulltext,doi:10.aaaa/bbb
```

`examples_paper_uid` 限制 ≤ 5 条,避免 csv 单元过长。

## 5. `prisma_flow.md` 模板

```markdown
# PRISMA Flow

## Identification
- Records identified: {N1} (from candidate_papers.csv)
  - arxiv: {n_a}
  - semantic_scholar: {n_s}
  - openalex: {n_o}
  - other: {n_x}

## Screening
- After dedup: {N2}
- Title/Abstract screened: {N3}
- Excluded after title/abstract: {N4}
  - Top reasons:
    - exc_off_topic: {n_off}
    - exc_year_out_of_window: {n_year}
    - exc_language: {n_lang}

## Eligibility
- Full-text assessed: {N5}
- Excluded after full-text: {N6}
  - exc_no_fulltext: {n_nofull}
  - exc_wrong_pop: {n_pop}
  - ...

## Included
- Studies included in final synthesis: {N7}
- Pass adequacy gate: yes/no(若 review_type 要求)
```

## 6. `screening_audit.json`

字段见 `hooks.md` §6.C。**移交给 paper-reading 的"交接单"**:

- `next_recommended_skill = paper-reading`(P1 接)
- `adequacy_gate.status` 必须 `passed` 或 `warned`,`failed` 时不允许移交

## 7. `screening_summary.md`(给用户)

```markdown
# Screening Summary

## 我做了什么
- review_type: systematic_review
- framework: PICO
- 候选总数: 287(来自 paper-discovery)
- 跑了 8 轮 active learning,batch=20
- 标题摘要决策: 自动 include 12 / 自动 exclude 198 / 人工复核 24
- 全文阶段: 评估 30,排除 8(含 5 篇全文不可得),最终 included 22

## 结果
- 最终入选: 22 篇
- 通过 adequacy gate: 是(systematic_review 要求 ≥ 12)
- PRISMA flow: 见 `prisma_flow.md`
- 完整决策表: `study_selection.csv`

## 下一步
- 移交给 paper-reading(P1)做证据抽取与对比
- P0 阶段 paper-reading 暂未实现,你可以:
  - 自己阅读 22 篇 included 论文
  - 等 P1 落地后再用 paper-reading 跑

## 风险与提示
- 全文可得比例 0.83(略低于 systematic review 推荐的 0.9)
- 5 篇全文不可得论文已写入 `human_review_queue.md`,建议人工补全或后续 paper-reading 再处理
```

## 8. (可选)`human_review_queue.md`

```markdown
# Human Review Queue

## 待复核(`selection=uncertain` 或 `confidence<0.7`)

| paper_uid | title | year | reason | suggested_action |
|---|---|---|---|---|
| arxiv:2305.... | ... | 2026 | borderline PICO match | 看一下 abstract 里 outcome 部分 |
| ... | ... | ... | ... | ... |

## 全文不可得

| paper_uid | title | year | last known url | follow-up |
|---|---|---|---|---|
| doi:10.zzzz/yyy | ... | 2024 | publisher 404 | 联系作者 / web archive |
```

## 9. 自检 checklist(对接 `hook_review`)

提交前必须自检:

- [ ] `criteria.json` 已落,所有 rule 都有 `id` 和 `code`
- [ ] `study_selection.csv` 每个 candidate_papers `dedup_status=unique` 行都至少有 1 行决策
- [ ] `study_selection.csv` 中所有 `paper_uid` 在 `candidate_papers.csv` 中找得到
- [ ] 同一 `(paper_uid, screening_stage)` 不重复
- [ ] PRISMA bucket 数字自洽(`identified ≥ screened ≥ eligible ≥ included`,`excluded` 累加一致)
- [ ] `selection_reason_code` 都在标准原因码集合里
- [ ] `screening_stage=final & selection=include` 的 paper_uid 集合 = `prisma_bucket=included` 集合
- [ ] adequacy_gate 已落 `passed/warned/failed`
- [ ] `next_recommended_skill` 写好(P0 写 `paper-reading`,标注 P1 才会真正接)
