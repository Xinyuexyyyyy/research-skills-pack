# Paper Discovery — 读图

## 这是干什么的

> 把"我要研究 X"翻译成"这是 X 主题的候选论文集"。

只做这一件事:**找全 + 去重 + 登记**。

## 用户能看到什么

| 你说 | 系统做什么 | 你最终拿到 |
|---|---|---|
| "帮我找一下 RAG 最新论文" | router → 本 skill → 双 db 双轮检索 | `candidate_papers.csv`(去重) + `source_log.csv` + `references.bib` |
| "我有这 20 个 DOI,帮我建候选池" | router → 本 skill → seed 模式 + 扩展 | 候选池 + manifest |
| "把 graph-based RAG 这部分补一下" | router → 本 skill → 仅 gap-driven round | source_log 新增一轮 + candidate_papers 增量 |
| "顺便帮我筛一下" | **本 skill 拒绝**,转 `paper-screening` | (转交) |

## 整体结构

```
研究问题 / 关键词 / 时间窗 / 种子
              ↓
      ┌────────────────────┐
      │  paper-discovery    │
      │  ├─ search plan      │
      │  ├─ multi-db search  │
      │  ├─ dedup            │
      │  └─ metadata fill    │
      └────────┬───────────┘
              ↓
   candidate_papers.csv + source_log.csv
   + references.bib + import_manifest.json
              ↓
       移交给 paper-screening
```

## 跟主 skill 的关系

- 本 skill 是 `research-academic` 二级路由后的下游之一
- 工具来自 `research-base/atoms.md`
- 默认管线和评分来自 `research-base/pipeline.md` + `scoring.md`
- 产物 schema 来自 `research-base/artifacts.md`(`source_log.csv` / `candidate_papers.csv`)
- 本 skill 不重写主 skill 已经定义的任何东西

## 依赖与配置

### 必需依赖

- **research-academic** skill（二级路由器）
- **research-base** skill（工具层：`atoms.md` 提供 `academic_search` / `web_fetch`，`artifacts.md` 定义 CSV schema，`hooks.md` 定义钩子接口）
- **abstract_pipeline.py**（工作区 `tools/` 目录）：批量 abstract 补全工具

### 可选依赖

- **ELSEVIER_API_KEY** 环境变量：提升 Elsevier 期刊 abstract 覆盖率（~50% → 100%），申请地址：https://dev.elsevier.com/
- **elsevier_fetch.py**（工作区 `tools/` 目录）：由 `abstract_pipeline.py` 自动调用

**配置方式**：参考 `.env.example` 文件，在工作区根目录创建 `.env` 并填入真实 API key。

### 下游依赖

- **paper-screening** skill：消费 `candidate_papers.csv` 进行纳排判断
- **paper-reading** skill：消费 PDF 和 abstract 进行全文阅读

## 边界铁律

1. 不做纳排(`selection` 字段不写)
2. 不抽证据(`evidence_records[]` 留空)
3. 不写综述
4. 不混普通网页源进 `candidate_papers.csv`
5. 任何候选必须能追溯到 `source_log.csv` 中至少一条记录

## 文件清单

```
paper-discovery/
├── SKILL.md
├── routing.md
├── hooks.md
├── channels.md
├── report-template.md
├── artifacts.md
└── README.md
```

## 移交标准

`import_manifest.json` 中 `coverage_check.status ∈ {passed, warned}` 时可以移交 `paper-screening`。`failed` 时不允许移交,要求重跑或人工介入。

## 未来 P1+ 扩展(不在本 skill P0 范围)

- 接 Zotero / Obsidian 自动同步
- 自动批量 PDF 下载(目前只记录 url,留给 paper-reading)
- 引文图扩展(给定一篇,沿 references 拉 N 跳)
- 反爬 / proxy 池接入
