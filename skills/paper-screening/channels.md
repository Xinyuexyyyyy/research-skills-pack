# Paper Screening — 决策信道(非外部 db)

> 本 skill 不面向外部 db,所以这里的"channels" 不是检索 db,而是**纳排决策的输入信号源**。

## 1. 信道矩阵

| 信道 | 优先级 | 来自 | 何时用 | 备注 |
|---|---|---|---|---|
| `title_abstract` | P0 | `candidate_papers.title` + `abstract` | 第一轮筛选必用 | 大多数 review 90% 决策来自这里 |
| `metadata` | P0 | `candidate_papers.year/venue/authors/citation_count/language` | 第一轮配合 title_abstract | 用于排除 venue blacklist / 时间窗 / 语言过滤 |
| `fulltext` | P1(本 skill 内,非"P1 skill") | `candidate_papers.pdf_url` | review_type ∈ {systematic, scoping} 时启用 | 抓 PDF / HTML 全文,只为做纳排判断,**不抽 evidence** |
| `seed_labels` | P0 | 用户标注的种子论文(`include` / `exclude`) | active learning 启动 | 抄 asreview |
| `human_review` | P0 | 人工对 `uncertain` 的复核 | 4-Tier 第 4 档兜底 | 抄 MetaScreener |
| `external_signal` | ⛔ 不允许 | (留空) | 不允许接入外部网页评论、推特、reddit 影响纳排 | 学术证据主链与开放网页信号必须分层(共识 §3) |

## 2. 信道使用规则

### title_abstract
- 输入:`candidate_papers.title` + `candidate_papers.abstract`
- 处理:LLM 按 `criteria.json` 判定 `selection`
- 缺 abstract:
  - 若 `landing_url` 可得,临时抓 abstract
  - 若仍缺 → `selection=uncertain` + `selection_reason_code=unc_low_confidence` + `notes="abstract missing"`
  - **不允许**仅凭 title 做 `selection=exclude` 之外的强决策(可以 exclude 明显 off-topic,但不能 include)

### metadata
- 用于硬过滤:
  - 时间窗(`year` 不在范围)→ `exc_year_out_of_window`
  - 语言(`language` 不在白名单)→ `exc_language`
  - venue(`venue` 在 blacklist)→ `exc_venue_blacklist`
- 这些都是确定性规则,优先级高于 LLM 主题判断,先过 metadata 再过 title_abstract

### fulltext
- 仅当 `review_type ∈ {systematic_review, scoping_review}` 或用户显式要求时启用
- 抓全文:优先 `pdf_url`,fallback `landing_url`
- 全文不可得 → `selection=exclude` + `selection_reason_code=exc_no_fulltext` + `screening_stage=fulltext`
- 全文可得 → 重新判定 `selection`,新增一行 `screening_stage=fulltext`
- **本 skill 抓全文只为纳排判断;evidence 抽取留给 paper-reading P1**

### seed_labels
- 用户给的"必须包含"或"必须排除"论文
- 在 `study_selection.csv` 中:
  - seed include → `selection=include` + `selection_reason_code=inc_seed` + `decided_by=human`
  - seed exclude → `selection=exclude` + `selection_reason_code=exc_other`(`selection_reason_text` 写"用户预先标注排除")
- 种子论文绕过 LLM 评分,直接进决策

### human_review
- 触发条件(任一):
  - `selection=uncertain`
  - `confidence < 0.7`
  - 用户在 routing 阶段说"我自己人工筛"
- 处理:把候选列出来,等用户回复 `include` / `exclude`,然后改 `decided_by=human_after_uncertain` / `decided_by=human`
- 必填:`decided_at` 写人工决策时间

## 3. 信道融合(决策融合)

当多个信道给出不同信号时,优先级:

1. metadata 硬过滤(确定性规则,exc_year/language/venue)
2. seed_labels(用户预标)
3. human_review(人工复核)
4. fulltext(若启用)
5. title_abstract + LLM
6. active_learning 排序(决定**进入决策的顺序**,不是决策本身)

## 4. 信道 vs 外部 db

- 本 skill 不调任何外部学术 db
- 若发现 candidate_papers.csv 字段缺失需要补齐(如缺 abstract),可调 `atoms.web_fetch(landing_url, ...)` 临时补,但**不能补到 candidate_papers.csv**(那是 paper-discovery 的产物);只能用于本次筛选决策

## 5. 学术 vs 网页信号(铁律)

- 本 skill 的纳排只基于学术信号(title/abstract/metadata/fulltext)
- 不允许把 Twitter / Reddit / 博客评分纳入决策
- 用户提"这个作者口碑不好"等开放网页信号 → 标注在 `notes` 但不进 `criteria_hits_*`
