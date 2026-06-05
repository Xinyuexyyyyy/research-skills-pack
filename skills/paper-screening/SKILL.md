---
name: paper-screening
description: 学术论文纳排 / 系统综述筛选。基于 candidate_papers.csv,定义 criteria(PICO/PECO/SPIDER),做 active learning 排序、标题摘要筛选、全文纳排、PRISMA 留痕。借鉴 asreview / MetaScreener / Parsifal 的成熟实践。**不做检索,不做证据抽取,不做综述写作**。触发词:纳排、筛选、PRISMA、systematic review、scoping review、criteria、PICO、PECO、SPIDER、include/exclude、screening。
status: stable
---

# Paper Screening — 学术论文纳排 + PRISMA 留痕

## 一句话定位

> 把"一堆候选论文"变成"哪些进、哪些出、为什么、怎么留痕"。**只做纳排留痕**,不检索、不抽证据、不写综述。

## 上层契约

- 父级:`research-academic`(router) → `research-base`(工具层)
- 进入条件:`research-academic/routing.md` 把任务定为 `matched_layer2=paper-screening`,且**已有合格 `candidate_papers.csv`**
- 离开条件:产出合格的 `criteria.json` + `study_selection.csv` + `prisma_flow.md`,**移交给 `paper-reading`**(P1)或停在此处供用户使用
- 共享 schema:严格遵守 `research-base/artifacts.md` 的 §3 `candidate_papers.csv`(只读)与 §4 `study_selection.csv`(写)

## P0 边界(必须遵守)

### 做什么
- ✅ 接收 `candidate_papers.csv` 作为唯一候选输入
- ✅ 与用户确认 review_type(systematic / scoping / literature)与 framework(PICO / PECO / SPIDER / none)
- ✅ 落 `criteria.json`(include + exclude + uncertain_policy + dedup_key + custom)
- ✅ 标题摘要筛选(`screening_stage=title_abstract`)
- ✅ 全文纳排(`screening_stage=fulltext`,需要时)
- ✅ 给每条候选写一行 `study_selection.csv`,带 `selection_reason_code` + `confidence`
- ✅ active learning 排序(借鉴 asreview):种子 → 高相关性优先 → uncertain 进人工 → 低相关性 batch exclude
- ✅ 4-Tier 决策(借鉴 MetaScreener):auto-include / auto-exclude / borderline-uncertain / human-required
- ✅ PRISMA 四档聚合,落 `prisma_flow.md`
- ✅ 跨文件一致性自检(对接 `research-base/artifacts.md` §6)

### 不做什么
- ❌ 重新检索 / 扩候选(那是 paper-discovery 的事)
- ❌ 抽证据 / 全文笔记 / 比较矩阵 → `paper-reading`(P1)
- ❌ 写综述 / research gaps → `survey-writer`(P1)
- ❌ 静默丢弃任何候选(`exclude` 也要有一行)
- ❌ 跳过原因码直接给 `selection_reason_text`(必须先选主码)

## 钩子覆盖(对接 `research-base/hooks.md`)

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ 部分 | 补 `framework` / PICO 字段 / `review_type` / `language_filter` 等到 `clarified_question.custom` |
| `hook_retrieve` | ⛔ 不覆盖 | 不检索;输入是 paper-discovery 给的 `candidate_papers.csv` |
| `hook_screen` | ✅ 完全覆盖 | 本 skill 的核心:active learning + PICO 命中 + 4-Tier 决策 |
| `hook_extract` | ⛔ 不覆盖 | 不抽 evidence,只在 `study_selection.csv` 里写决策 |
| `hook_synthesize` | ✅ 轻量覆盖 | 不写综述,只产出 `prisma_flow.md` 与 `screening_summary.md` |
| `hook_review` | ✅ 覆盖 | adequacy gate(对应 review_type)+ 跨文件一致性自检 |

详见 `hooks.md`。

## 必出产物

| 文件 | 说明 |
|---|---|
| `criteria.json` | 纳入 / 排除规则,带规则 ID,可被 `study_selection.criteria_hits_*` 引用 |
| `study_selection.csv` | 见 `research-base/artifacts.md` §4 |
| `exclusion_reasons.csv` | 排除原因码统计(每个原因码一行,带 count) |
| `prisma_flow.md` | PRISMA 四档流程图(text 形式,从 `study_selection.csv` 聚合) |
| `screening_audit.json` | 决策审计(decided_by / decided_at 分布、人工复核条数、active_learning 轮次) |
| `screening_summary.md` | 给用户的"看完一眼就懂"的总结(三段:做了什么 / 结果 / 下一步) |

## 借鉴矩阵

| 来源 | 抄什么 |
|---|---|
| `asreview/asreview` | active learning 优先级队列、duplicate hiding、label audit trail |
| `ChaokunHong/MetaScreener` | criteria-first screening、4-Tier(auto-include / auto-exclude / borderline / human)、confidence routing |
| `vitorfs/parsifal` | planning → conducting → reporting 三段式;criteria 先于 screening 落地 |

## 文件清单

```
paper-screening/
├── SKILL.md            入口(本文件)
├── routing.md          命中条件 + 与 paper-discovery / paper-reading 的让位边界
├── hooks.md            钩子覆盖详情(active learning / 4-Tier / PRISMA)
├── channels.md         "channels" = 决策信道(标题摘要 / 全文 / 元数据 / 人工);非外部 db
├── report-template.md  产物骨架(criteria / selection / prisma_flow / audit / summary)
├── artifacts.md        产物 schema(只列本 skill 实际写入,引用 research-base/artifacts.md)
└── README.md           读图
```

## 给下游 paper-reading 的承诺(P1 才会接)

- `study_selection.csv` 中 `screening_stage=final` 且 `selection=include` 的行就是入选论文
- full 模式下,只有 `final` 行才代表有效最终裁决；`title_abstract` 行只是中间留痕
- 每个入选论文都已经有 `paper_uid` 在 `candidate_papers.csv` 中,且 `dedup_status=unique`
- `prisma_bucket=included` 的 paper_uid 数量等于 `selection=include + screening_stage=final` 的行数(自检铁律)
- 任何"未来才会再补"的字段不会在本 skill 阶段污染产物

## Full 模式执行语义（2026-05-14）

- `screen_batch.py` 负责 title/abstract 批筛与基础 PRISMA 留痕
- `fulltext_locator.py` 负责生成 `fulltext_routes.csv` 与 `human_review_queue.md`
- `fulltext_screen.py` 负责真正的全文判筛：选择全文入口、追加 `screening_stage=fulltext`、回写 `final`
- 若全文不可得，必须写 `exc_no_fulltext`
- `paper-reading` 只读取有效最终 `include`，不会回退去吃 `title_abstract` 中间行

## 自检清单

- [ ] `criteria.json` 包含 include + exclude + uncertain_policy + dedup_key + custom？
- [ ] 每条候选都有一行 `study_selection.csv`，没有静默丢弃？
- [ ] `study_selection.csv` 包含 selection_reason_code + confidence？
- [ ] active learning 排序覆盖了种子 → 高相关 → uncertain → 低相关？
- [ ] 4-Tier 决策有明确规则：auto-include / auto-exclude / borderline / human？
- [ ] PRISMA 四档聚合完整，落 `prisma_flow.md`？
- [ ] `prisma_bucket=included` 数量等于 `selection=include + screening_stage=final` 数量？
