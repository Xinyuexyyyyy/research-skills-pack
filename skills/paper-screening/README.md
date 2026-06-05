# Paper Screening — 读图

## 这是干什么的

> 把"一堆候选论文"变成"哪些进、哪些出、为什么、怎么留痕"。

只做这一件事:**criteria → 决策 → PRISMA 留痕**。

## 用户能看到什么

| 你说 | 系统做什么 | 你最终拿到 |
|---|---|---|
| "做个 systematic review 的纳排" | router → 本 skill → criteria → AL → 全文 → PRISMA | `study_selection.csv` + `prisma_flow.md` + `criteria.json` |
| "我已经有 candidate_papers,先做轻量 scoping" | router → 本 skill → 仅 title_abstract | 简化版 `study_selection.csv` + `prisma_flow.md` |
| "顺便帮我读一下 included 的论文" | **本 skill 拒绝**,转 `paper-reading`(P1) | (转交) |
| "再去找几篇补一下" | **本 skill 拒绝**,转 `paper-discovery` | (转交) |

## 整体结构

```
candidate_papers.csv (来自 paper-discovery)
              ↓
      ┌────────────────────┐
      │  paper-screening    │
      │  ├─ criteria.json    │  (PICO/PECO/SPIDER + include/exclude rules)
      │  ├─ active learning  │  (asreview-like ranking + batch decision)
      │  ├─ 4-Tier 决策       │  (auto-include / auto-exclude / borderline / human)
      │  ├─ title/abstract  │  (LLM + criteria 命中)
      │  └─ fulltext        │  (review_type ∈ {systematic, scoping} 时)
      └────────┬───────────┘
              ↓
   study_selection.csv + criteria.json + prisma_flow.md
   + exclusion_reasons.csv + screening_audit.json + screening_summary.md
              ↓
       移交给 paper-reading(P1)
```

## 跟主 skill 的关系

- 本 skill 是 `research-academic` 二级路由后的下游之一
- 工具来自 `research-base/atoms.md`(`web_fetch` 用于补 abstract / fulltext;`score` 不直接用,但 confidence 字段对齐 scoring)
- 默认管线和评分来自 `research-base/pipeline.md` + `scoring.md`
- 产物 schema 来自 `research-base/artifacts.md`(`study_selection.csv` 主)
- 评分维度对齐主 skill 的 4 Tier(但本 skill 是"决策 4 档",不是 evidence 4 档)

## 边界铁律

1. 不重新检索(那是 paper-discovery)
2. 不抽 evidence(那是 paper-reading P1)
3. 不写综述(那是 survey-writer P1)
4. 不静默丢弃任何候选(每个 candidate 都至少有 1 行决策)
5. 不允许把外部网页信号(twitter / reddit / 博客)纳入决策
6. PRISMA bucket 数字必须自洽

## 文件清单

```
paper-screening/
├── SKILL.md
├── routing.md
├── hooks.md
├── channels.md       (注:这里的 channel 是决策信道,不是外部 db)
├── report-template.md
├── artifacts.md
└── README.md
```

## 工具状态

| 文件 | 干什么 | 状态 |
|---|---|---|
| `tools/screen_batch.py` | 读取 `candidate_papers.csv` → 批量生成 `study_selection.csv`；full 模式附带 `criteria.json` / `prisma_flow.md` / `screening_audit.json` | ✅ |
| `tools/fulltext_locator.py` | 对 full 模式已纳入论文探测 `pdf_url / arXiv / Unpaywall / landing_url`，写 `fulltext_routes.csv` + `human_review_queue.md` | ✅ |
| `tools/fulltext_screen.py` | 基于 `fulltext_routes.csv` 选择全文入口，追加 `screening_stage=fulltext/final`，对无全文条目写 `exc_no_fulltext`；默认 dry-run 副本执行 | ✅ |

当前 P0 主链已经从“文档定义”推进到“脚本可跑”。剩余短板不再是 title/abstract 批筛本身，而是全文判筛在真实 run 上的持续校准与更强审计。

## 借鉴矩阵

| 来源 | 抄什么 |
|---|---|
| `asreview/asreview` | active learning 优先级队列、batch decision、stop criterion |
| `ChaokunHong/MetaScreener` | 4-Tier 决策(auto-include / auto-exclude / borderline / human-required)、confidence routing |
| `vitorfs/parsifal` | planning → conducting → reporting,criteria 先于 screening |

## 移交标准

`screening_audit.adequacy_gate.status ∈ {passed, warned}` 且 跨文件一致性自检通过 时可以移交 `paper-reading`(P1)。`failed` 时不允许移交,要求重跑或人工介入。

P0 阶段 `paper-reading` 暂未实现,移交动作变成"产物就绪,等 P1 接手"。

## 未来 P1+ 扩展(不在本 skill P0 范围)

- 真正的在线 active learning 模型(P0 用启发式 + LLM 评分)
- retraction check(撤稿过滤)
- 多人独立筛选 + Cohen kappa 一致性
- 跨语言纳排(目前 P0 走 `language_filter` 简单过滤)
