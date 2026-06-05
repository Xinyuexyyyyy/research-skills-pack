# Artifacts — 共享产物 schema

> 这是所有学术类 skill 共享的 4 份核心 csv 的字段契约。`paper-discovery` / `paper-screening` / 后续 P1 的 `paper-reading` / `survey-writer` 都必须按本文件的字段约定产出,**不允许各自发明字段名**。
>
> 一句话规则:**ID 用本文件第 1 节定义的统一标识符,字段名用本文件后续节定义的 csv schema,自定义字段必须放在 `custom_*` 列里**。

## 0. 总览

| 文件 | 谁产出 | 谁消费 | 唯一键 | 必出 |
|---|---|---|---|---|
| `source_log.csv` | `paper-discovery` 强制;主 skill 默认管线兜底 | 任何下游 skill 做来源回链 | `source_id` | ✅ |
| `candidate_papers.csv` | `paper-discovery` | `paper-screening` 作为输入 | `paper_uid` | ✅ |
| `study_selection.csv` | `paper-screening` | `paper-reading` 作为输入(P1) | `paper_uid` | ✅ |
| `evidence_table.csv` | `paper-reading`(P1)/ 任何下游 skill 抽证据 | `survey-writer`(P1)、复核 | `evidence_id` | ✅(凡是有 extract 阶段就必出) |

P0 阶段实际写入 csv 的只有前 3 个(`paper-discovery` 出 `source_log` / `candidate_papers`,`paper-screening` 出 `study_selection`)。`evidence_table.csv` 的 schema 在本文件先固化,P0 不强制产出,等 P1 `paper-reading` 落地时直接用。

## 1. 统一标识符规范

### 1.1 论文统一 ID(`paper_uid`)

任何论文级记录都使用一个**单字段** `paper_uid`,生成规则按优先级:

```
1. 有 DOI       → paper_uid = "doi:" + 小写 + 去前缀(去掉 "https://doi.org/" 等)
2. 否则有 arXiv ID → paper_uid = "arxiv:" + 不带版本号(2305.12345 而不是 2305.12345v3)
3. 否则有 Semantic Scholar paper ID → paper_uid = "s2:" + ID
4. 否则有 OpenAlex Work ID → paper_uid = "openalex:" + 去掉 https 前缀(W12345 这种)
5. 否则有 PubMed ID  → paper_uid = "pmid:" + ID
6. 否则             → paper_uid = "title:" + canonical_title_hash(见 1.4)
```

> 同一篇论文跨不同 db 命中时,`paper_uid` 必须保持一致。先按优先级 1 解析 DOI;DOI 为空才往下走。

### 1.2 DOI 规范

- 一律小写,去掉协议头与 doi.org 前缀,只保留前缀/后缀两段:`10.xxxx/yyyy`
- 不在 csv 里写 `https://doi.org/...` 这种带域名的形式
- 字段名固定为 `doi`(可空)

### 1.3 arXiv ID 规范

- 一律不带版本号(去掉 `vN`),去掉 `arXiv:` 前缀
- 老式格式(`cs/0606102`)按原样保留
- 字段名固定为 `arxiv_id`(可空)

### 1.4 canonical_title_hash 规范

仅当 DOI / arXiv / S2 / OpenAlex / PubMed 全无时才用,生成步骤:

1. 取 `title`,小写
2. 删除非字母数字字符(只保留 `[a-z0-9 ]`)
3. 单空格化,trim
4. 取前 120 字 + 加上 `+ "|" + 第一作者 last name 小写 + "|" + year`
5. 取 sha1 前 12 位

### 1.5 citation 规范

- 任何引用 evidence 的地方,只能用 `evidence_id`(`E-001` 形态),禁止用 paper title 或 paper_uid 直接引用
- 任何引用 paper 的地方,只能用 `paper_uid`,禁止用 raw url
- references.bib 的 BibTeX key 必须能反查回 `paper_uid`(详见各 skill 的 `report-template.md`)

## 2. `source_log.csv` — 检索来源日志

记录"什么时候、用什么 query、在哪个数据库、命中多少条"。这是 PRISMA 的 Identification 与 Search 阶段最低留痕。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_id` | string | ✅ | 唯一键。建议 `S-{round}-{db}-{seq}`,例如 `S-1-arxiv-001` |
| `round` | int | ✅ | 第几轮检索(初始 = 1,gap-driven 回补 = 2,...) |
| `db` | enum | ✅ | `arxiv` / `semantic_scholar` / `openalex` / `pubmed` / `crossref` / `dblp` / `acl_anthology` / `google_scholar` / `biorxiv` / `medrxiv` / `manual` / `seed` |
| `query` | string | ✅ | 实际检索字符串 |
| `filters` | string | ⭕ | 时间窗 / venue / language 等过滤,JSON 字符串 |
| `executed_at` | ISO8601 | ✅ | 检索时间 |
| `hits_count` | int | ✅ | 数据库返回的命中数(不是入候选池数) |
| `imported_count` | int | ✅ | 实际导入到 `candidate_papers.csv` 的条数 |
| `query_url` | string | ⭕ | 可复现的检索 URL(若可生成) |
| `notes` | string | ⭕ | 这一轮加这条 query 的理由(尤其是 gap-driven 回补) |
| `custom_*` | any | ⭕ | 下游 skill 专用字段一律以 `custom_` 前缀 |

唯一键:`source_id`。
建议索引:`(round, db)`。

最小可用样例:

```csv
source_id,round,db,query,filters,executed_at,hits_count,imported_count,query_url,notes
S-1-arxiv-001,1,arxiv,"retrieval augmented generation","{\"year\":\"2023-2026\"}",2026-05-03T08:01:00Z,128,50,"https://arxiv.org/search/?query=retrieval+augmented+generation&start=0","initial recall"
S-1-s2-001,1,semantic_scholar,"retrieval augmented generation","{\"year\":\"2023-2026\"}",2026-05-03T08:05:00Z,210,50,,"initial recall"
S-2-openalex-001,2,openalex,"graph rag multi-hop","{\"year\":\"2024-2026\"}",2026-05-03T08:30:00Z,42,30,,"gap-driven: round 1 missed graph-based RAG"
```

## 3. `candidate_papers.csv` — 候选池

记录"导入了什么、是否已去重、metadata 是否完整"。**`paper-discovery` 的最终交付物**。这一层只负责候选池建立,**不带纳排结论**。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `paper_uid` | string | ✅ | 见 §1.1。唯一键 |
| `title` | string | ✅ | 论文题目原文 |
| `authors` | string | ✅ | `;` 分隔的作者列表(`Lastname, Firstname` 格式) |
| `year` | int | ✅ | 发表年份(预印本取 first version) |
| `venue` | string | ⭕ | 会议 / 期刊名,预印本写 `arXiv` |
| `doi` | string | ⭕ | 见 §1.2 |
| `arxiv_id` | string | ⭕ | 见 §1.3 |
| `s2_id` | string | ⭕ | Semantic Scholar paper ID |
| `openalex_id` | string | ⭕ | OpenAlex Work ID(`W` 开头) |
| `pmid` | string | ⭕ | PubMed ID |
| `abstract` | string | ⭕ | 原文摘要(若可获取) |
| `citation_count` | int | ⭕ | 库返回的引用数(以最近一次抓取为准) |
| `pdf_url` | string | ⭕ | 全文 PDF 稳定链接 |
| `landing_url` | string | ✅ | 论文落地页(用于回链) |
| `source_ids` | string | ✅ | 命中本论文的 `source_id` 列表,`;` 分隔(同一篇可由多 db 命中) |
| `first_seen_at` | ISO8601 | ✅ | 第一次进入候选池的时间 |
| `language` | string | ⭕ | ISO 639-1(`en` / `zh` / ...) |
| `dedup_status` | enum | ✅ | `unique` / `duplicate_of:<paper_uid>` |
| `dedup_method` | enum | ⭕ | `doi` / `arxiv_id` / `s2_id` / `openalex_id` / `title_fingerprint`(若 dedup_status != unique) |
| `fulltext_available` | bool | ⭕ | 全文是否可获取(P0 可空,留给下游) |
| `notes` | string | ⭕ | 任何不进 metadata 的备注 |
| `custom_*` | any | ⭕ | 下游 skill 专用字段 |

唯一键:`paper_uid`(且只保留 `dedup_status=unique` 的行作为后续 skill 输入)。
完整性约束:
- `doi` / `arxiv_id` / `s2_id` / `openalex_id` / `pmid` 至少有 1 个非空,**否则 `paper_uid` 必须以 `title:` 前缀生成**,并在 `notes` 写明"无稳定 ID"
- `source_ids` 不允许为空(任何论文都必须有引入它的检索路径,否则降级到 `db=manual` / `db=seed` 也得登记)
- 学术源 vs 普通网页源:`db` 字段约束只允许学术 db 枚举值;若是网页线索请走 `research-comprehensive`(P1+)的 `web_log`,**不得污染本表**

## 4. `study_selection.csv` — 纳排结论 + PRISMA 留痕

`paper-screening` 的最终交付物。每个候选都要有一行,**不允许静默丢弃**。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `paper_uid` | string | ✅ | 必须能在 `candidate_papers.csv` 找到 |
| `screening_stage` | enum | ✅ | `title_abstract` / `fulltext` / `final` |
| `selection` | enum | ✅ | `include` / `exclude` / `uncertain` |
| `selection_reason_code` | string | ✅ | 见下方原因码表;一行只能有 1 个主码 |
| `selection_reason_text` | string | ✅ | 一句话人类可读理由 |
| `criteria_hits_include` | string | ⭕ | `;` 分隔,命中的 include 规则 ID |
| `criteria_hits_exclude` | string | ⭕ | `;` 分隔,命中的 exclude 规则 ID |
| `confidence` | float | ✅ | 0-1,筛选置信度。`< 0.7` 必须进 uncertain 或人工复核 |
| `decided_by` | enum | ✅ | `auto` / `active_learning` / `human` / `human_after_uncertain` |
| `decided_at` | ISO8601 | ✅ | 决策时间 |
| `prisma_bucket` | enum | ✅ | `identified` / `screened` / `eligible` / `included` / `excluded`(对应 PRISMA 四档) |
| `fulltext_checked` | bool | ⭕ | 是否真的看了全文(`screening_stage=fulltext` 必填) |
| `notes` | string | ⭕ | 任何额外说明 |
| `custom_*` | any | ⭕ | 下游 skill 专用字段(如 PICO 命中分维度) |

唯一键(逻辑):`(paper_uid, screening_stage)`。也就是同一篇可以在 title_abstract 阶段一行 + fulltext 阶段一行 + final 一行。

### 4.1 标准原因码(主码)

include:
- `inc_pico_match` — PICO/PECO/SPIDER 全维度命中
- `inc_topic_relevant` — 主题相关且无明显排除项
- `inc_seed` — 由用户标为种子论文
- `inc_high_relevance` — active learning 高相关性自动接纳

exclude:
- `exc_off_topic` — 主题不符
- `exc_wrong_pop` — 人群不符(PICO P)
- `exc_wrong_intervention` — 干预/方法不符(PICO I)
- `exc_wrong_outcome` — 结局不符(PICO O)
- `exc_wrong_design` — 研究设计不符(SPIDER D)
- `exc_language` — 语言不在白名单
- `exc_year_out_of_window` — 时间窗外
- `exc_venue_blacklist` — venue 在排除名单(如 workshop / position paper)
- `exc_duplicate` — 重复(应已在 `candidate_papers` 去重,这里是补漏)
- `exc_no_fulltext` — `screening_stage=fulltext` 时全文不可得
- `exc_low_quality` — 质量评估不达标
- `exc_other` — 其它(`selection_reason_text` 必须详细说明)

uncertain:
- `unc_borderline_pico` — PICO 部分维度命中
- `unc_low_confidence` — 模型置信不足
- `unc_conflicting_signals` — 标题摘要冲突
- `unc_needs_fulltext` — 标题摘要无法判断,等全文

### 4.2 PRISMA 四档对应

```
identified  ← 在 candidate_papers.csv 中被引入(由 paper-discovery 决定)
screened    ← title_abstract 阶段已被看过
eligible    ← title_abstract 阶段 selection != exclude(进入 fulltext)
included    ← final 阶段 selection = include
excluded    ← 任意阶段 selection = exclude
```

聚合 `prisma_flow.md` 时,从本 csv 直接 group by `prisma_bucket`。

## 5. `evidence_table.csv` — 证据池

P0 阶段不强制产出,但 schema 先固化,供 P1 `paper-reading` 直接用。每条 evidence 一行,**严禁拿候选池或筛选结论冒充 evidence**。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `evidence_id` | string | ✅ | 唯一键。`E-` 前缀,顺序编号(`E-001` ...) |
| `paper_uid` | string | ✅ | 必须能在 `candidate_papers.csv` / `study_selection.csv` 中找到,且其 `prisma_bucket=included` |
| `claim` | string | ✅ | 一句话结论 |
| `quote` | string | ✅ | 原文摘录(不允许"我自己总结") |
| `source_ref` | string | ✅ | 稳定可访问的 url 或 doi url |
| `source_locator` | string | ✅ | 页码 / section / table / figure 编号(摘要级证据写 `abstract`,confidence 自动 -0.2) |
| `extracted_at` | ISO8601 | ✅ | 抽取时间 |
| `score_composite` | int | ✅ | 0-100,见 `scoring.md` |
| `tier` | int | ✅ | 0/1/2/3,见 `scoring.md` |
| `confidence` | float | ✅ | 0-1 |
| `selection` | enum | ✅ | `include` / `exclude` / `uncertain`(评分用) |
| `redundancy` | float | ⭕ | 0-1 |
| `strength` | float | ⭕ | 0-1 |
| `primacy` | enum | ⭕ | `primary` / `secondary` / `tertiary` |
| `recency` | float | ⭕ | 0-1 |
| `authority` | enum | ⭕ | `low` / `mid` / `high` |
| `coverage` | float | ⭕ | 0-1 |
| `conflict` | enum | ⭕ | `none` / `partial` / `contradictory` |
| `citation_completeness` | float | ✅ | 0-1。`< 0.5` 必入 Tier 0 |
| `tags` | string | ⭕ | `;` 分隔的主题标签 |
| `paper_title` | string | ✅ | 冗余字段,方便人类阅读 |
| `authors` | string | ⭕ | 冗余字段,方便人类阅读 |
| `year` | int | ⭕ | 冗余字段,方便人类阅读 |
| `venue` | string | ⭕ | 冗余字段,方便人类阅读 |
| `doi` | string | ⭕ | 冗余字段,方便引用 |
| `custom_*` | any | ⭕ | 下游专用字段(如 method / dataset / metric) |

唯一键:`evidence_id`。
强约束:
- `paper_uid` 必须对应一篇 `study_selection.csv` 里 `screening_stage=final` 且 `selection=include` 的论文,否则评分引擎自动 Tier 0
- `source_locator` 不允许为空字符串。仅摘要级证据可写 `abstract`,但要在 `custom_full_text_seen=false`

## 6. 跨文件一致性自检

下游 skill 在 review 阶段必须跑这套自检(P0 由 `paper-screening` 在 `prisma_flow` 阶段顺手做,P1 由 `paper-reading` / `survey-writer` 接手):

1. `candidate_papers.csv` 中所有 `source_ids` 引用的 ID 必须能在 `source_log.csv` 找到
2. `study_selection.csv` 中所有 `paper_uid` 必须能在 `candidate_papers.csv` 找到(且 `dedup_status=unique`)
3. `study_selection.csv` 中同一 `(paper_uid, screening_stage)` 不允许重复行
4. 若有 `evidence_table.csv`,所有 `paper_uid` 必须在 `study_selection.csv` 中以 `final + include` 出现
5. PRISMA bucket 数字必须自洽:`identified ≥ screened ≥ eligible ≥ included` 且 `excluded` 与三者之和等于 `identified`

发现违例的处理:
- 缺源 / 缺 paper / 缺 evidence:打回上一个 skill,不允许"自己补"
- bucket 数字不自洽:`paper-screening` 必须重跑 PRISMA 聚合

## 7. 字段扩展规则

下游 skill 真的要加新字段时:

1. **能塞进 `custom_*` 就别动主 schema**(如 `custom_method` / `custom_dataset` / `custom_pico_population`)
2. 真的要把字段提到主 schema:
   - 在 `research-base/references/` 下加一份 `breaking-changes.md` 写理由 + 影响面
   - 用户审过 → 改本文件 + 升版本号(目前是 v0,改完写 v1)
   - 升版后所有下游 skill 必须显式在自己的 `artifacts.md` 里声明兼容版本
3. **任何情况下都不允许**:同义字段重复(如同时有 `paper_uid` 和 `paper_id`)、用 raw url 代替 ID、把 csv 改成 json 但不更新本文件

## 8. 版本

- 当前 schema 版本:`v0`(P0 首版)
- 文件格式:UTF-8、`,` 分隔、`"` 引号转义、首行表头、空值留空(不要写 `null` / `NA`)
