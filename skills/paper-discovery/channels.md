# Paper Discovery — 检索渠道

> 所有渠道都通过 `research-base/atoms.md` 的 `academic_search` / `web_fetch` 调用,**不要在本 skill 里造新的 fetch**。
>
> 本文件按 P0 边界精简，聚焦学术源优先级矩阵和检索顺序规则。

## 1. 优先级矩阵

| 优先级 | 渠道 | 适用域 | 入口 | 备注 |
|---|---|---|---|---|
| P0 | arXiv | CS / 物理 / 数学 / 统计 | `https://arxiv.org/search/?query=...` | 预印本主战场,RAG/LLM 等 ML 必查 |
| P0 | Semantic Scholar | 跨学科 | `https://www.semanticscholar.org/search?q=...` 或 API | 引用关系 + TLDR 摘要 |
| P0 | OpenAlex | 跨学科,开放元数据 | `https://api.openalex.org/works?search=...` | 引用图、机构、资助 |
| P1 | PubMed | 医学 / 生物 | `https://pubmed.ncbi.nlm.nih.gov/?term=...` | 医学顶库 |
| P1 | Crossref | 跨学科,DOI 元数据 | `https://api.crossref.org/works?query=...` | DOI 解析、引用元数据 |
| P1 | DBLP | CS 顶会期刊 | `https://dblp.org/search?q=...` | CS 作者 + 会议 |
| P1 | ACL Anthology | NLP 顶会 | `https://aclanthology.org/search/?q=...` | NLP 全文开放 |
| P2 | Google Scholar | 跨学科兜底 | `https://scholar.google.com/scholar?q=...` | 易被反爬,仅作兜底 |
| P2 | bioRxiv / medRxiv | 生物 / 医学预印本 | `https://www.biorxiv.org/search/...` | 医学预印本 |

## 2. 检索顺序

### Step 1 — 初始检索(round=1)
- 默认双开 P0 中两个独立 db(`arxiv` + `semantic_scholar`)
- 若 `domain_hint` 是医学方向,改为 `pubmed` + `semantic_scholar`
- 若 `domain_hint` 是 NLP/CS 方向,加 `acl_anthology` 或 `dblp`
- 单 db 召回 ≤ 50,总召回 ≤ 100(本轮)
- 落 `source_log.csv` 与 `search_queries.md`

### Step 2 — gap-driven 回补(round=2)
- 看 round=1 的命中,识别"主题未覆盖 / 时间段未覆盖 / 重要 venue 未命中"
- 增加专用 query 或新 db
- 落 `source_log.csv` 中 `notes` 必填:为什么加这一轮

### Step 3 — 兜底(round=3,可选)
- 仅当 round=1+2 后,候选总数 < `minimum_depth.min_candidates`(默认 20)且没有合理理由时启动
- 走 P2 渠道

至少要跑 **2 个独立学术源** + **2 轮检索**,否则 `coverage_check.min_dbs_met` 或 `min_rounds_met` 失败。

## 3. 查询构造

- 主关键词 + 同义词 OR 组(由 `clarified_question.custom.keywords` 拼)
- 时间窗 → 各库的 filter 参数
- 单库召回 ≤ `per_db_recall_cap`(默认 50),总召回 ≤ `total_recall_cap`(默认 200)
- 每轮检索都要落 `search_queries.md`:查询串、数据库、日期、过滤条件、召回数、为什么加
- 不允许"同 db 同 query 跑 3 次以上"——若反爬,换库或换 query

## 4. 元数据补齐

每条候选必须含(详见 `research-base/artifacts.md` §3):

- `paper_uid`(按 §1.1 优先级生成)
- `title`、`authors`、`year`、`venue`(若可)、`landing_url`(必填)
- `abstract`(尽量补,若 db 不给则从 landing_url 抓)
- `pdf_url`(若可获取)
- 至少 1 个稳定 ID(DOI / arxiv / s2 / openalex / pmid)

无稳定 ID 的论文比例 > 5% 时 → coverage_check 警告。

## 5. 全文获取(P0 仅记录,不下载)

- 本 skill **只记录** `pdf_url`,**不批量下载**(留给 paper-reading P1)
- 若 db 已返回 PDF 链接,验证可达性即可
- 若 PDF 不公开,在 `missing_papers.md` 登记
- arXiv:`pdf_url = https://arxiv.org/pdf/{arxiv_id}.pdf`
- ACL Anthology:landing 页通常带 PDF 链接,直接抓
- Crossref/OpenAlex 通常给 publisher landing,不一定有公开 PDF —— 记录即可

## 6. 失败处理

- 反爬 / 限流 → 换 db 或降级到 P2,**不重试同一 URL 三次以上**
- 找不到的种子论文 → 写入 `missing_papers.md`,不阻塞主流程
- 某主题召回明显偏薄 → 必须新开一轮 gap-driven query,不能直接结束

## 7. 学术源 vs 普通网页源

- 本 skill 只接受 `db ∈ {arxiv, semantic_scholar, openalex, pubmed, crossref, dblp, acl_anthology, google_scholar, biorxiv, medrxiv, manual, seed}`
- 用户在输入里给的"博客 / 新闻 / 推文"链接 **不写入 candidate_papers.csv**;若用户坚持要包括,建议转 `research-comprehensive`(P2)的 web 通道,本 skill 不污染学术主链路

## 8. 与 research-base 的关系

- 本文件**不重新定义 fetch 协议**,只指定渠道与构造
- 调用一律走 `atoms.academic_search(query, db)` + `atoms.web_fetch(url, prompt)`
- 抓完必须 `atoms.source_log()` 落库
