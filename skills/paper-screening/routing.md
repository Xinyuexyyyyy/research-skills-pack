# Paper Screening — 命中条件与让位规则

## 1. 命中本 skill

本 skill 由 `research-academic/routing.md` 二级路由决定进入。命中信号:

### 强命中
- 用户说"纳排""筛选""systematic review""scoping review""criteria""PRISMA""inclusion / exclusion"
- 用户说 "PICO" / "PECO" / "SPIDER"
- 用户已有 `candidate_papers.csv`(由 `paper-discovery` 产出 或 用户自带),要决定哪些进入下一步

### 中命中
- 用户说"逐篇判断""标题摘要先过一轮""全文纳排"
- 用户说"画 PRISMA flow""留 audit trail"

### 不命中(让位)
- 用户没有 `candidate_papers.csv` → `paper-discovery`
- 用户已有 `study_selection.csv` 的 `included` 集且要做对比 / 抽证据 → `paper-reading`(P1)
- 用户要直接写综述 → `survey-writer`(P1)

## 2. 与 paper-discovery 的边界

| 维度 | paper-discovery | paper-screening(本 skill) |
|---|---|---|
| 主要动作 | 检索 / 导入 / 去重 / 元数据 | criteria / 标题摘要筛选 / 全文纳排 / PRISMA |
| `selection` 字段 | **不写** | 必写 |
| `prisma_bucket` 字段 | **不写** | 必写 |
| 全文获取 | 仅记录 `pdf_url` | 必要时拉全文做纳排 |
| 输出文件 | `candidate_papers.csv` / `source_log.csv` / `references.bib` | `study_selection.csv` / `criteria.json` / `prisma_flow.md` |

铁律:**screening 的输入只有 candidate_papers.csv,绝不重新触发检索**。如果发现候选池不足,**回退到 paper-discovery**,不在本 skill 内补检索。

## 3. 与 paper-reading 的边界(P1)

| 维度 | paper-screening | paper-reading(P1) |
|---|---|---|
| 主要动作 | 决定哪些论文进 | 读全文、抽证据、做对比 |
| 输出 | `study_selection.csv`(决策) | `evidence_table.csv` / `paper_notes/` / `comparison_matrix.csv` |
| 全文获取 | 用于做纳排判断 | 用于做证据抽取 |

铁律:**screening 不抽证据**。即使用户在筛选过程中说"这篇看着很关键,顺便给我做个笔记",也要拒绝并提示"那是 paper-reading 的工作"。

## 4. 与 research-base 默认管线的边界

| 默认段 | screening 怎么走 |
|---|---|
| clarify | ✅ 部分:补 PICO / framework / review_type / language_filter |
| retrieve | ⛔ **不做**(输入是 candidate_papers.csv) |
| screen | ✅ 全量覆盖:active learning + PICO + 4-Tier |
| extract | ⛔ 不抽 evidence |
| synthesize | ✅ 轻量:仅产出 PRISMA flow + screening summary |
| review | ✅ 覆盖:adequacy gate + 跨文件一致性自检 |

## 5. 显式覆盖

- 用户说"按 PRISMA 严格做" → 强制 review_type=systematic_review
- 用户说"先做个 scoping review" → 强制 review_type=scoping_review
- 用户说"我已经有 criteria.json" → 跳过 criteria 起草,直接进 active learning
- 用户说"我自己人工筛,你只负责留痕" → `decided_by=human_only`,本 skill 不做 active learning,只做 criteria + audit

## 6. 反问澄清(只问 1 个最关键的)

- **没有 candidate_papers.csv** → "你有候选论文 csv 吗?发我路径,或者我先去 paper-discovery 帮你建。"
- **review_type 不明** → "你想要严格 PRISMA(systematic review)还是先做轻量分类(scoping)?"
- **没有 framework** → "你的研究问题适合 PICO(干预)还是 PECO(暴露)还是 SPIDER(质性)?或者用 'none' 直接按主题相关性筛?"
- **min_included 不明** → "你期望最终入选多少篇论文?(决定 active learning 的停止条件)"

不要一次问多个。已知 review_type 就别问 framework;已知 framework 就别问 review_type。

## 7. P0 阶段不做

- 不做 active learning 的真正在线模型训练(P0 用启发式 + LLM 评分代替,后续 P2 接 asreview-py 等真实 AL 框架)
- 不做 retraction check / 撤稿过滤(留给 paper-reading P1)
- 不做 venue 影响因子加权(留给后续打分体系扩展)
