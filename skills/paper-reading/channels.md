# Paper Reading — Channels(全文获取通路)

> "channels" 在 paper-reading 语境 = **全文获取通路 + abstract 兜底 + 跳过策略**。不是 paper-discovery 的"外部检索源"。

---

## 1. 通路总览

| # | 通路 | 输入 | 输出 | P0/P1/P2 |
|---|---|---|---|---|
| **1** | **abstract-only** | OpenAlex/Crossref 已有 abstract 的论文 | LLM 抽 PICO + method + findings,`extraction_source=abstract+keywords` | ✅ P0 主路径 |
| **2** | **arXiv 预印本下载** | arxiv:* 开头的 paper_uid | PDF → LLM 抽全文,`extraction_source=fulltext` | ✅ P0 实施(b 方案) |
| **3** | **跳过(pending_fulltext)** | 无 abstract + 非 arXiv | 进 pending_fulltext.csv,reason_code=NO_ABSTRACT | ✅ P0 兜底 |
| 4 | Unpaywall OA PDF | 任意 paper_uid → DOI lookup | OA PDF 下载 | ❌ P1 再加 |
| 5 | 学校 CARSI 浏览器手抓 | Elsevier 等闭源 DOI | 用户手动 PDF 上传到 `data/fulltext/` | ❌ P2 再加 |
| 6 | r.jina.ai 反向代理 | 任意 URL | 文本(质量参差) | ❌ P2 再加(本机 451 阻塞,服务器化后可重试) |

---

## 2. 通路 1:abstract-only(P0 主路径)

### 输入
`candidate_papers.csv` 的 abstract + keywords 字段(由 paper-discovery 产出),paper_uid 由 `study_selection.csv` 中 selection=include 行决定。

### 抽取规则(LLM)
- 输入 prompt:`title + abstract + keywords + study_type 候选 enum`
- 输出 13 列字段(见 `artifacts.md` §1)
- 置信度判据:
  - **high** = abstract 直接给出 P/I/O 数值或精确描述
  - **medium** = abstract 描述清晰但缺数值,或 outcome 偏定性(标 `qualitative_only=true`)
  - **low** = abstract 缺关键字段(P/I/Method 任一为空),或仅靠 title+keywords 推测

### 容错
- abstract 长度 < 50 字符 → 视同无 abstract,转通路 3
- abstract 包含 "Available online only" / "subscription required" 等占位 → 同上

---

## 3. 通路 2:arXiv 预印本(P0 b 方案,双子通路)

`paper_uid` 以 `arxiv:` 开头(如 `arxiv:2403.10566`)。**两个子通路按本机能力自动选**:

### 2a. PDF 下载(默认,需要 PDF parser 能力)

```bash
python3 $SKILL_DIR/scripts/fetch_arxiv.py 2403.10566
# 输出: $SKILL_DIR/data/fulltext/arxiv-2403.10566.pdf
```

- 下载成功 → LLM 直接吃 PDF 文本(需要本机有 poppler / pypdf 等 PDF parser,或 LLM agent 自带 PDF 读取能力)
- 优先抽:abstract(对照 OpenAlex 版,看是否更完整)、Methods 段、Results 段、Conclusions 段

### 2b. ar5iv HTML(无 PDF parser 时的 fallback)⭐ 2026-05-08 新增

**触发条件:** 本机/agent 没有 PDF parser(macOS 原生缺 poppler、claude-code Read 工具依赖 poppler 等场景)。

```
URL 模板:https://ar5iv.labs.arxiv.org/html/<arxiv_id>
示例:    https://ar5iv.labs.arxiv.org/html/2403.10566

工具:任何 HTML fetcher(WebFetch / curl / requests)
```

- ar5iv 是 arxiv 的 LaTeX → HTML 渲染服务,**文本质量比 PDF parser 还好**:
  - 公式直接渲染成 mathml,LLM 可读
  - 表格已结构化为 HTML table,免去 PDF 表格解析坑
  - figure 文字描述直接拿到
- 验证:2026-05-08 本轮 P-06(arxiv:2403.10566)实测,信息密度优于 abstract 抽,补出"CQI 主驱动是 feasibility rate 而非温度"等反直觉发现(见 `runs/2026-05-04_battery-thermal-real/reading/fulltext_extraction_comparison.md`)
- 局限:仅对 2007 年后的 arxiv 论文(LaTeX 源可获取);老论文或纯 PDF 投稿可能 ar5iv 渲染失败

### 通路 2 抽取契约(2a / 2b 通用)
- 输出 `extraction_source=fulltext`
- 抽取置信度按字段完整度判定(见 `hooks.md` hook_extract):full PICO + 数值化 outcome + method 流水线 = high

### 通路 2 容错
- **2a 失败**:下载超时 / 404 / PDF 太小(< 1KB)/ 非 PDF 头 → 自动尝试 2b
- **2b 失败**:ar5iv 404(老论文 / 渲染失败)→ 转通路 1(降级用 abstract)
- **abstract 也无**:转通路 3(pending_fulltext)

---

## 4. 通路 3:跳过(pending_fulltext)

### 触发
- 无 abstract(通路 1 失败)
- 非 arXiv(通路 2 不适用)
- P0 阶段无其他通路可用

### 写入 pending_fulltext.csv
```
paper_uid, reason_code=NO_ABSTRACT, suggested_route=unpaywall_or_carsi, notes=<keywords 简述 + 上游决策来源>
```

### 后续路径
- 等 P1 接通路 4(Unpaywall),自动重试
- 或 P2 接通路 5(CARSI 手抓),用户提供 PDF 后回到通路 2 抽取

---

## 5. P1+ 扩展通路(预留接口)

### 通路 4:Unpaywall(P1 实施)
- API: `https://api.unpaywall.org/v2/{doi}?email=research@example.com`
- 命中 OA → 直接拿 PDF URL → 下载 → 抽
- 适用:MDPI / Frontiers / Springer Nature OA / 部分 IEEE OA
- 不适用:Elsevier / Wiley 闭源(命中率 < 5%)

### 通路 5:CARSI 浏览器手抓(P2 实施)
- 流程:用户在浏览器登录学校 SSO → 进出版社页面 → 下 PDF → 上传到 `data/fulltext/`
- 不自动化(需人工 + 学校账号)
- 命中 Elsevier 等闭源出版社的兜底场景

### 通路 6:r.jina.ai(P2 实施,本机 451 阻塞)
- API: `https://r.jina.ai/{url}` → 返回文本
- 质量参差(常常吐 paywall 文案而非全文)
- 服务器化后可重试

---

## 6. 通路选择决策树

```
paper_uid 起头是 arxiv:?
├── 是 → 通路 2(arXiv 下载)→ 下载成功? 是 → fulltext 抽 / 否 → 通路 1
└── 否 → candidate_papers.csv 有 abstract?
    ├── 有 → 通路 1(abstract-only)
    └── 无 → 通路 3(pending_fulltext)
            └── P1+ 后:Unpaywall / CARSI / r.jina 重试
```

---

## 7. P0 通路的覆盖率(基于 dryrun + 真跑)

| 通路 | dryrun 6 样本命中数 | 真跑 6 样本命中数 |
|---|---|---|
| 通路 1(abstract-only) | 5 | 5 |
| 通路 2(arXiv 下载) | 0(dryrun 不跑下载) | 1(P-06 已下,本轮未抽全文) |
| 通路 3(pending_fulltext) | 1(P-03,但 dryrun 没规范化) | 1(P-03 规范化进 csv) |

**P0 实测覆盖率 = 通路 1+2 / total = 5/6 = 83.3%**(过 80% gate)

预测 40 篇 include 全集时:
- 通路 1 ≈ 36/40(无 abstract 4 篇全是 Elsevier)
- 通路 2 ≈ 1-3/40(arXiv 工科)
- 通路 3 ≈ 4/40(Elsevier 无 abstract)
- 总覆盖率 ≈ 90%+
