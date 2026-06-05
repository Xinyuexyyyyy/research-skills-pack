# Atoms — 原子工具签名

## 定义

原子工具是**主 skill 提供给所有子模板包共享的标准动作**。子模板包**不重写这些**,只组合调用。

每个工具说明:
- **签名**:输入 / 输出
- **默认实现**:底层用 Claude Code 的什么工具或什么 prompt 模板
- **何时用**:在管线哪一段调用

---

## A. 检索类(Retrieve)

### `web_fetch(url, prompt)`
- **输入**:url(string) + prompt(对内容的提取要求)
- **输出**:`{url, fetched_at, content, raw_excerpt}`
- **默认实现**:Claude Code 的 `WebFetch` 工具
- **何时用**:Stage 2 检索单页

### `web_search(query, allowed_domains?, blocked_domains?)`
- **输入**:query(string),可选过滤域名
- **输出**:`[{title, url, snippet}]`
- **默认实现**:Claude Code 的 `WebSearch` 工具
- **何时用**:Stage 2 开放检索

### `academic_search(query, db?)`
- **输入**:query + db(arxiv / semantic_scholar / pubmed / openalex / crossref)
- **输出**:`[{paper_id, title, authors, abstract, year, doi}]`
- **默认实现**:对应 db 的公开搜索 URL,通过 `web_fetch` 拉取页面再解析
- **何时用**:学术包 Stage 2

### `wayback_get(url, snapshot_date?)`
- **输入**:目标 url + 可选时间点
- **输出**:历史快照内容
- **默认实现**:`web_fetch("https://web.archive.org/web/{date}/{url}")`
- **何时用**:竞品包 Stage 2(历史定价、版本变化)

---

## B. 解析类(Parse)

### `pdf_parse(path)`
- **输入**:本地 / 远程 PDF 路径
- **输出**:`{full_text, sections, references}`
- **默认实现**:Claude Code 的 `Read` 工具(支持 PDF)
- **何时用**:学术包 Stage 4 全文提取

### `html_parse(html, schema)`
- **输入**:html 字符串 + 抽取 schema
- **输出**:按 schema 结构化数据
- **默认实现**:LLM prompt 提取(用主 skill 的提取模板)
- **何时用**:Stage 4 任意子包

### `transcript_parse(text)`
- **输入**:访谈 / 视频字幕文本
- **输出**:`{speakers, turns, key_quotes}`
- **默认实现**:LLM prompt 提取
- **何时用**:产品发现包 Stage 4

---

## C. 处理类(Process)

### `dedup(records, key?)`
- **输入**:记录列表 + 可选去重键
- **输出**:去重后列表 + 重复组日志
- **默认实现**:LLM 启发式判断 + url/doi/title 哈希
- **何时用**:Stage 3 筛选前

### `normalize(records, schema)`
- **输入**:杂乱记录 + 目标 schema
- **输出**:标准化记录
- **默认实现**:LLM prompt 重写
- **何时用**:Stage 4 提取

### `cluster(records, by?)`
- **输入**:记录 + 聚类维度(主题 / 时间 / 来源)
- **输出**:聚类组
- **默认实现**:LLM 主题归并
- **何时用**:Stage 5 综合(主题分组)

---

## D. 评估类(Score)

### `score(evidence)`
- **输入**:一条 evidence_record
- **输出**:`{ score: evidence_score, tier }`
- **默认实现**:见 `scoring.md`
- **何时用**:Stage 4 提取后立刻打分

### `classify(record, taxonomy)`
- **输入**:记录 + 分类体系
- **输出**:命中的分类标签
- **默认实现**:LLM prompt 多选分类
- **何时用**:Stage 3 / 4 任意

---

## E. 输出类(Output)

### `cite_back(claim, source)`
- **输入**:结论 + 来源记录
- **输出**:标准引用格式 `(Author, Year)` 或 `[1]` + bib 条目
- **默认实现**:LLM prompt 套用引用模板
- **何时用**:Stage 5 综合

### `source_log(records, path)`
- **输入**:记录列表 + 输出路径
- **输出**:写入 `source_log.csv`(url / title / fetched_at / type)
- **默认实现**:Claude Code 的 `Write`
- **何时用**:Stage 2 之后必须调用一次

### `evidence_card(evidence, path?)`
- **输入**:evidence_record + 可选输出路径
- **输出**:`{id, claim, quote, source, score, tier}` 写入 markdown
- **默认实现**:模板渲染
- **何时用**:Stage 4 之后

---

## F. 验证类(Verify)

### `cross_check(claim, evidence_pool)`
- **输入**:某条结论 + 全部证据池
- **输出**:`{supporting, conflicting, neutral}` 引用列表
- **默认实现**:LLM 检索 + 对比
- **何时用**:Stage 6 复核

### `gap_check(report, criteria)`
- **输入**:草稿报告 + 任务标准
- **输出**:遗漏点列表
- **默认实现**:LLM 对照 criteria 检查覆盖
- **何时用**:Stage 6 复核

---

## 调用约定

- 所有原子工具的输入输出都有**显式 schema**,子包不要传混乱字段。
- 失败时返回 `{error, message}`,不要静默吞错。
- 涉及外部访问(web/学术 db)的,必须落 `source_log`,**不落不算成功**。
- 涉及打分的,必须把 `score + tier` 挂在记录上,**不挂不算 extract 完成**。

---

## 缺工具怎么办

**不要在子包里造同名工具**。流程:
1. 在 `references/missing-atoms.md` 提议(待建)
2. 用户审 → 批准 → 加到本文件
3. 子包再用

这条是为了避免每个子包都自带一套不同的 `web_fetch`,造成回归地狱。
