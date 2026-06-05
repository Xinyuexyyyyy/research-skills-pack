# Paper Discovery — 命中条件与让位规则

## 1. 命中本 skill

本 skill 由 `research-academic/routing.md` 二级路由决定进入。命中信号:

### 强命中
- 用户说"找论文""检索""搜文献""导入文献""building candidate set""references.bib"
- 给出 research_question + 关键词 + 时间窗,且**没有** `candidate_papers.csv`
- 给出种子论文 / DOI 列表,要求扩展候选

### 中命中
- 用户问"X 方向最近有哪些论文"
- 输出诉求是"列一份候选论文表"
- 用户提到具体学术 db(arxiv / semantic_scholar / openalex / pubmed / dblp / acl anthology)

### 不命中(让位)
- 用户已经有 `candidate_papers.csv`,只想做纳排 → `paper-screening`
- 用户要全文阅读 / 抽证据 → `paper-reading`(P1)
- 用户要写综述 → `survey-writer`(P1)
- 用户要做开放领域扫描(学术+网页) → `academic-deep-research`(P2)

## 2. 与 paper-screening 的边界

| 维度 | paper-discovery(本 skill) | paper-screening |
|---|---|---|
| 主要动作 | 检索 / 导入 / 去重 / 元数据 | criteria / 标题摘要筛选 / 全文纳排 / PRISMA |
| `selection` 字段 | **不写**(只填 `dedup_status`) | 必写 `include` / `exclude` / `uncertain` |
| `prisma_bucket` 字段 | **不写** | 必写 `identified` 以下 |
| 产出文件 | `candidate_papers.csv` / `source_log.csv` / `references.bib` | `study_selection.csv` / `prisma_flow.md` / `criteria.json` |
| 全文获取 | 仅记录 `pdf_url`,不下载 | 必要时拉全文做纳排判断 |

铁律:**discovery 完成后 candidate_papers.csv 不应有 `selection` 字段或 `prisma_bucket` 字段填充**。如果用户在 discovery 阶段直接说"顺便筛掉低质量的",必须显式拒绝并提示"这是 paper-screening 的工作"。

## 3. 与 research-base 默认管线的边界

`research-base/pipeline.md` 默认 6 段管线为 `clarify → retrieve → screen → extract → synthesize → review`。本 skill 的对应:

| 默认段 | discovery 怎么走 |
|---|---|
| clarify | ✅ 部分:补 search_plan、必查 db、排除 db |
| retrieve | ✅ 全量覆盖:走 `channels.md` |
| screen | ⛔ **本 skill 不做**(等 paper-screening) |
| extract | ⛔ 不抽证据,只补 metadata 与 abstract |
| synthesize | ⛔ 不写综述,只输出候选池 + bib + manifest |
| review | ✅ 仅做候选池完整性自检 |

## 4. 显式覆盖

- 用户说"把这些 DOI 直接做成候选池" → 强制本 skill,db=`manual`/`seed`
- 用户说"补一下 X 主题的论文" → 强制本 skill,执行 gap-driven 回补轮次
- 用户说"已经有候选 csv,直接帮我做纳排" → **不命中本 skill**,转 `paper-screening`

显式覆盖必须在 routing_decision 里说明。

## 5. 反问澄清(只问 1 个最关键的)

仅在以下情形发起澄清,且一次只问 1 个:

- **没有 research_question** → "用一句话说你的研究问题是什么?(我会基于这个生成检索式)"
- **时间窗模糊** → "近 X 年这部分,你说的是 3 年还是 5 年?"
- **多领域** → "这个方向横跨 ML 和医学,你更想覆盖哪边?(决定我先查哪个 db)"
- **没说有种子** → "你有没有几篇'必须包含'的论文?有的话发 DOI / arXiv ID 给我作为种子。"

不要一次抛多个问题。如果用户已经给出研究问题、时间窗、领域,直接开干,**不要再问"你是不是要做综述"** —— 那是 router 该判断的事。
