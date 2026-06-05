# Channels — 学术检索渠道

> 所有渠道都通过主 skill 的 `atoms.web_fetch` / `atoms.academic_search` 调用,**不要在本包里造新的 fetch**。

## 优先级矩阵

| 优先级 | 渠道 | 适用域 | 入口 | 备注 |
|---|---|---|---|---|
| P0 | arXiv | CS / 物理 / 数学 / 统计 | `https://arxiv.org/search/?query=...` | 预印本主战场,RAG/LLM 等 ML 必查 |
| P0 | Semantic Scholar | 跨学科 | `https://www.semanticscholar.org/search?q=...` | 引用关系 + TLDR 摘要 |
| P0 | OpenAlex | 跨学科,开放元数据 | `https://api.openalex.org/works?search=...` | 引用图、机构、资助 |
| P1 | PubMed | 医学 / 生物 | `https://pubmed.ncbi.nlm.nih.gov/?term=...` | 医学顶库 |
| P1 | Crossref | 跨学科,DOI 元数据 | `https://api.crossref.org/works?query=...` | DOI 解析、引用元数据 |
| P1 | DBLP | CS 顶会期刊 | `https://dblp.org/search?q=...` | CS 作者 + 会议 |
| P1 | ACL Anthology | NLP 顶会 | `https://aclanthology.org/search/?q=...` | NLP 全文开放 |
| P2 | Google Scholar | 跨学科兜底 | `https://scholar.google.com/scholar?q=...` | 易被反爬,仅作兜底 |
| P2 | bioRxiv / medRxiv | 生物 / 医学预印本 | `https://www.biorxiv.org/search/...` | 医学预印本 |

---

## 调用约定

### 1. 检索顺序
- 先 P0(arXiv + Semantic Scholar + OpenAlex),覆盖 80% 场景
- 再按 `domain_hint` 调对应 P1
- P2 仅当 P0/P1 召回不足或要交叉验证

至少要跑 **2 个独立学术源**,否则只能叫 quick review,不能叫 literature review。

### 2. 查询构造
- 主关键词 + 同义词 OR 组(由 hook_clarify 输出的 PICO 拼)
- `time_window` 转换成各库的过滤参数
- 单库召回不超过 50 条,跨库总召回不超过 200 条(避免上下文爆炸)
- 每轮检索都要落到 `search_queries.md`:查询串、数据库、日期、过滤条件、召回数
- 至少跑 2 轮检索:主查询一轮 + 缺口回补一轮

### 3. 元数据完整性
每条材料抽完必须含:
- `paper_id`(DOI / arXiv ID / Semantic Scholar ID 任一)
- `title`, `authors`, `year`, `venue`, `abstract`
- `url`(可访问全文或摘要的稳定链接)

### 4. 全文获取
- arXiv:抓 PDF → `atoms.pdf_parse`
- ACL Anthology:抓 PDF → `atoms.pdf_parse`
- 不公开全文的:只用摘要 + 引用上下文,在 `evidence_record.score.confidence` 上 -0.2

若 included papers 中全文可得比例 < 0.8:
- 标记为 coverage risk
- review 阶段默认不能 `passed as literature review`

### 5. 失败处理
- 反爬 / 限流:换库或降级到 P2,**不重试同一 URL 三次以上**
- 找不到的论文:写入 `missing_papers.md`,不阻塞主流程
- 某主题召回明显偏薄:必须新开一轮 gap-driven query,不能直接进入成文

---

## 与主 skill 的关系

- 本文件**不重新定义 fetch 协议**,只指定渠道和构造
- 调用一律走 `atoms.academic_search(query, db)` + `atoms.web_fetch(url, prompt)`
- 抓完必须 `atoms.source_log()` 落库

---

## 子调用模式(被 comprehensive 调用)

当本包是被综合类子调用时:

- 只跑 `hook_retrieve` + `hook_extract`
- 不跑 `hook_synthesize` / `hook_review`
- 返回 `evidence_records_partial[]`,id 用 slice 前缀(E-S?-XXX)
- 接收的 budget(max_records / max_minutes)严格遵守
- 被子调用时允许跳过 `paper_notes/` 全量展开,但至少要返回 `comparison_matrix_partial.csv` 或等价的结构化笔记
