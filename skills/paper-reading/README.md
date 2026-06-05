# Paper Reading

> 学术论文证据抽取 skill。基于 **Keshav 三遍阅读法 + PICO 框架 + AlpaPICO ICL 策略**。
>
> **输入** = `study_selection.csv` 中 selection=include 行
> **输出** = `evidence_table.csv`(22 列) + `evidence_audit.md` + `pending_fulltext.csv` + `reading_summary.md`

---

## 一句话定位

把"哪些论文进了"变成"每篇论文说了什么"。**只做证据抽取**,不检索 / 不纳排 / 不写综述。

---

## 核心设计

```
论文输入
   ↓
[Pass 1] 鸟瞰扫描 — Keshav 五问(5-10 min)
   ↓ 裁决: proceed / demote / skip
[Pass 2] 内容抓取 — PICO + 方法 + 发现 (~30 min)
   ↓ 质量门: ≥80% 完整抽取
[Pass 3] 深度复现 — 虚拟实现 + 质疑假设 (4-5 hrs, P2)
   ↓
evidence_table.csv (22 列)
```

**Keshav 五问:**
1. **Category** — 什么类型?
2. **Context** — 与哪些论文/理论相关?
3. **Correctness** — 假设是否合理?
4. **Contributions** — 核心贡献?
5. **Clarity** — 写作质量?

---

## 上下游

```
paper-discovery → paper-screening → paper-reading(本 skill)
                                          ↓
                        evidence_table.csv / 单篇报告 / 对比输入 / gap 输入
                                          ↓
               survey-writer | 手动写作 | comparison | essay-analyze
```

- 上游 `paper-screening` 给 `study_selection.csv`(只读) + `candidate_papers.csv`(只读 abstract/keywords)
- `survey-writer` 只是可能的一个下游，不是唯一去向
- `evidence_table.csv` 也可以直接给单篇精读、方法对比、research gaps 盘点或用户手动写作使用

---

## 文件清单

| 文件 | 干什么 | 何时读 |
|---|---|---|
| `SKILL.md` | 主入口:契约 + 三遍法框架 + 边界 | LLM 进 skill 第一站 |
| `routing.md` | 命中条件 + 与 screening/writer 的让位边界 | 判断"该不该接这个任务" |
| `channels.md` | 全文获取通路:abstract-only / arXiv PDF / ar5iv HTML / pending | 决定怎么取全文 |
| `hooks.md` | Pass 1/2 prompt 模板 + 三层 Quality Gate + 自检 | 真跑时执行 |
| `artifacts.md` | 产物 schema:22 列定义 + 铁律 + 跨文件一致性 | 写产物前对照 |
| `report-template.md` | 4 个产物的最小骨架 + 自检命令 | 复制骨架填字段 |
| `config.json` | 默认配置:阈值 / 通路开关 / P0 边界 | 初始化时加载 |
| `README.md` | 你正在看 | 入门读图 |

**代码文件(P0):**
| 文件 | 干什么 | 状态 |
|---|---|---|
| `scripts/prepare.py` | 读取输入 CSV → 生成 Pass 1 prompt JSONL + extraction_plan.csv | ✅ |
| `tools/evidence_extractor.py` | 读取 `pass1_inputs.jsonl` → 批量生成 `pass1_results.json` / `pass2_results.json`（OpenAI-compatible / mock）。**注意**：该工具位于 `$STUDY_RESEARCH_ROOT/tools/` 而非本 skill 目录下 | ✅ |
| `scripts/collect.py` | 读取 LLM 输出(JSON) → 写入 evidence_table.csv + pending + audit + summary | ✅ |
| `scripts/gate.py` | 运行三层 Quality Gate → PASS/FAIL 报告 | ✅ |
| `scripts/fetch_arxiv.py` | arXiv PDF 下载(已有) | ✅ |

**工作流(P0):**
```
1. python3 prepare.py <run_dir>
   → reading/pass1_inputs.jsonl (36 条 prompt 上下文)
   → reading/extraction_plan.csv (通路分配)

2. python3 $STUDY_RESEARCH_ROOT/tools/evidence_extractor.py <run_dir>
   → reading/pass1_results.json
   → reading/pass2_results.json

3. python3 collect.py <run_dir>
   → reading/evidence_table.csv (22 列)
   → reading/pending_fulltext.csv
   → reading/low_confidence_evidence.csv
   → reading/evidence_audit.md
   → reading/reading_summary.md

4. python3 gate.py <run_dir>
   → 三层 gate 报告
```

---

## 真跑产出

### 第一次真跑(2026-05-08, 6 样本)

```
~/study-research/runs/2026-05-04_battery-thermal-real/reading/
├── evidence_table.csv                    5 行(22 列)
├── pending_fulltext.csv                  1 行(P-03 Elsevier 无 abstract)
├── low_confidence_evidence.csv           0 行
├── evidence_audit.md                     5 篇逐条审计(Pass 1+2)
├── reading_summary.md                    "抽多少 / 跳多少 / 下一步"
└── fulltext_extraction_comparison.md     P-06 abstract vs ar5iv 全文对比
```

**Quality Gate:**
- Gate 1 (Pass 1 proceed): 6/6 = **100%** ✅ (门槛 60%)
- Gate 2 (Pass 2 complete): 5/6 = **83.3%** ✅ (门槛 80%)

---

## 通路速查

| # | 触发 | 通路 | 工具 | P0/P1/P2 |
|---|---|---|---|---|
| 1 | 有 abstract | abstract-only | LLM 直接抽 | ✅ P0 主路径 |
| 2a | `arxiv:*` + 有 PDF parser | arXiv PDF 下载 | `scripts/fetch_arxiv.py` | ✅ P0 |
| 2b | `arxiv:*` + 无 PDF parser | ar5iv HTML | WebFetch / curl | ✅ P0 |
| 3 | 无 abstract / 非 arXiv | pending_fulltext | 写 csv 等 P1 | ✅ P0 兜底 |
| 4 | OA DOI | Unpaywall | API lookup | ❌ P1 |
| 5 | Elsevier 等闭源 | CARSI 浏览器手抓 | 用户人工 | ❌ P2 |

---

## 三层 Quality Gate

```
Gate 1: Pass 1 proceed_ratio ≥ 60%
Gate 2: Pass 2 evidence_complete_ratio ≥ 80%
Gate 3: evidence + pending + low_confidence = include 总数(100%)
```

详见 `hooks.md` hook_review。

---

## 依赖说明

### Python 依赖

本 skill 使用 Python 标准库，无需额外安装第三方包：

- `csv` - CSV 文件读写
- `json` - JSON 数据处理
- `pathlib` - 路径操作
- `urllib` - HTTP 请求（arXiv PDF 下载）
- `collections` - 数据结构工具
- `sys` - 系统参数和函数

### 环境变量配置（可选）

复制 `.env.example` 为 `.env` 并配置以下 API keys：

| 环境变量 | 用途 | 是否必需 | 申请地址 |
|---------|------|---------|---------|
| `ELSEVIER_API_KEY` | 获取 Elsevier 期刊论文 abstract（如 Fuel/IJHE/Energy/RSER） | 可选，强烈推荐 | https://dev.elsevier.com/ |
| `SEMANTIC_SCHOLAR_API_KEY` | Abstract enrichment 备选数据源 | 可选 | https://www.semanticscholar.org/product/api |
| `STUDY_RESEARCH_ROOT` | 工作区根目录（默认 `~/study-research`） | 可选 | - |

**注意**：
- Elsevier API 对 `10.1016/` 前缀的 DOI 有 100% 命中率（2026-05-12 验证）
- Semantic Scholar API 申请审批已收紧（2026-05-12 起）
- 无 API key 时可使用 WebSearch 降级通路（详见 `channels.md`）

### 外部工具依赖（P0 阶段无需）

以下工具仅在 P1/P2 阶段需要：

- **PDF parser**（P1）：`poppler` / `pypdf` / `pymupdf` - 用于本地 PDF 文本提取
- **GROBID**（P2）：结构化 PDF 解析服务 - 用于表格/图表抽取

---

## 怎么用

**典型流程:**

1. paper-screening 跑完,产出 `study_selection.csv`
2. 读 `SKILL.md` 了解三遍法契约
3. 读 `routing.md` 确认任务该接
4. 读 `channels.md` 决定通路
5. 读 `hooks.md` 按 Pass 1 → Pass 2 顺序执行
6. 按 `report-template.md` 骨架写产物
7. 跑自检命令,PASS 后按用户目标分流：可移交 `survey-writer`，也可停在 reading 层交付

**最快入口:** 看 `report-template.md`,复制骨架,从空白 csv/md 填起。

---

## 状态

| 阶段 | 状态 |
|------|------|
| Skill 文档(7 个 .md + 1 个 .json) | ✅ 完成 |
| 代码实体(Python scripts) | ✅ P0 主链已落地 |
| 40 篇全集真跑 | ⏳ 待跑 |
| P1 扩展(Unpaywall + Pass 3) | ⏳ 待实施 |
| P2 深度(CARSI + GROBID) | ⏳ 待实施 |

**当前:** P0 已从文档闭环推进到脚本闭环；`study_selection.csv` 已兼容 multi-stage screening，默认只读取有效最终 `include`。当前短板转为全文判筛在真实专题上的持续校准。
