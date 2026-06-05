---
name: paper-reading
description: 学术论文证据抽取。基于 study_selection.csv 中 selection=include 的论文，按 Keshav 三遍阅读法分层抽取结构化证据，产出 evidence_table.csv 供下游任务复用（如 survey-writer / 单篇精读 / 对比分析 / gap 梳理）。**不做检索，不做纳排，不做综述写作**。触发词：抽证据、读论文、PICO 抽取、evidence extraction、reading、systematic review reading、key findings、文献抽取、综述抽取、three-pass、Keshav。
status: stable
---

# Paper Reading — 学术论文证据抽取

## 一句话定位

> 把"哪些论文进了"变成"每篇论文说了什么"。**只做证据抽取**，不检索、不纳排、不写综述。

## 设计哲学

本 skill 融合三套方法论：

| 来源 | 贡献 | 应用场景 |
|------|------|---------|
| **Keshav (2007)** 三遍阅读法 | Pass 1/2/3 分层策略 + 五问 (Five Cs) | 核心阅读框架，决定"读多深" |
| **PICO 框架** | Population / Intervention / Comparator / Outcome | 结构化证据的学术标准 |
| **AlpaPICO (2024)** | In-Context Learning (ICL) + biomedical 微调 | LLM 抽取策略，few-shot prompt |

**阅读策略不是"读一遍抽全部"，而是"按 Pass 分层，该浅就浅，该深才深"。**

---

## 上层契约

- 父级:`research-academic`(router) → `research-base`(工具层)
- 进入条件:`research-academic/routing.md` 把任务定为 `matched_layer2=paper-reading`,且**已有合格 `study_selection.csv`(含 selection=include 行)**
- 离开条件:产出合格的 `evidence_table.csv` + `evidence_audit.md` + `pending_fulltext.csv`,交给**用户指定的下游任务**（如 `survey-writer` / 单篇报告 / 方法对比 / gap 分析）
- 共享 schema:严格遵守 `research-base/artifacts.md` 的 `study_selection.csv`(只读),并新增 `evidence_table.csv`(写)

---

## 三遍阅读框架（核心）

```
论文输入
   ↓
[Pass 1] 鸟瞰扫描 (5-10 min/paper) → 五问 → 决定 Pass 2 命运
   ↓ 判断: 保留 / 降级 / 跳过
[Pass 2] 内容抓取 (~30 min/paper) → PICO + 方法 + 关键发现
   ↓ 判断: 够做下游任务 / 需深度 / 证据不足
[Pass 3] 深度复现 (可选, P2) → 虚拟复现 + 质疑假设
   ↓
evidence_table.csv / 单篇导读报告 / 对比输入
```

### Pass 1 — 鸟瞰扫描（abstract + title + keywords）

**目标**: 5-10 分钟/篇，回答 Keshav 五问，决定该论文是否值得进入 Pass 2。

**抽取字段**（全部从 abstract 可得）：

| 字段 | 说明 | 来源 |
|------|------|------|
| `category` | 论文类型: review / empirical_cfd / empirical_material / empirical_optimization / empirical_ai / theoretical / survey | abstract + title |
| `context` | 理论基础/相关论文/属于哪个研究方向 | abstract |
| `correctness_flag` | 假设是否合理: valid / questionable / insufficient_info | abstract |
| `contributions` | 1-3 条核心贡献(一句话每条) | abstract |
| `clarity_score` | 写作质量: well_written / acceptable / poorly_written | abstract |
| `pass1_verdict` | Pass 1 裁决: **proceed_to_pass2** / **demote_to_qualitative_only** / **skip** | 五问综合 |
| `pass1_confidence` | high / medium / low | — |

**Pass 1 Quality Gate**: 
- `pass1_verdict == proceed_to_pass2` 的论文 ≥ 60% 的 include 总数（否则说明 screening 阶段纳排过松）
- `pass1_confidence ∈ {high, medium}` 才能进 Pass 2

**demote_to_qualitative_only**: review 类论文或 abstract 太泛的论文，不抽 PICO 数值，只记定性观点。

**skip**: abstract 完全不足以判断 → 进 `pending_fulltext.csv`。

### Pass 2 — 内容抓取（abstract + 图表描述 + 方法段落）

**目标**: 30 分钟/篇，从可用文本中抽出 PICO + 方法 + 关键发现。

**抽取字段**：

| 字段 | 说明 | 来源 |
|------|------|------|
| `population` | P — 研究对象/场景 | abstract |
| `intervention` | I — 干预/方法/技术 | abstract |
| `comparator` | C — 对照/基准 | abstract(optional) |
| `outcome` | O — 结果/指标 | abstract |
| `method` | 方法学描述(技术路线/实验设计) | abstract + 方法段 |
| `key_finding_1` | 核心发现 1(带数值) | abstract |
| `key_finding_2` | 核心发现 2(带数值, optional) | abstract |
| `key_finding_3` | 核心发现 3(带数值, optional) | abstract |
| `extraction_confidence` | high / medium / low | — |
| `extraction_source` | abstract / abstract+methods / title_only | — |
| `qualitative_only` | true(仅定性) / false(有数值) | — |
| `figures_count` | 文中图表数量(如有全文) | PDF |

**Pass 2 Quality Gate**:
- include 论文中 evidence 完整抽取率 ≥ 80%（dryrun 实测 5/6 = 83%）
- `extraction_confidence=low` 的论文不进入 evidence_table 主表，单独记 `low_confidence_evidence.csv`

### Pass 3 — 深度复现（全文 + 可选, P2）

**目标**: 深度理解，虚拟复现，质疑假设。

**抽取字段**（P2 实施）：

| 字段 | 说明 |
|------|------|
| `hidden_assumptions` | 作者未明说的假设 |
| `limitations` | 论文自陈的局限 |
| `future_work` | 作者指出的未来方向 |
| `reproducibility_notes` | 虚拟复现时发现的问题 |
| `critical_score` | 1-10，综合评估论文质量 |

**触发条件**: 仅对 Pass 2 中 `extraction_confidence=high` 且用户标记"重点论文"的条目执行。

---

## 报告产出模式:小白自学手册(2026-05-13 增补)

> **定位升级**:paper-reading 的产出不只是"机器读的 csv + audit + summary 三件套",还包括**给科研小白看的 markdown 报告**——一份完整、可自学、可反复查的"论文自学导航仪"。

### 双产出原则

- **结构化产出**(机器读,给下游任务复用):`evidence_table.csv` + `evidence_audit.md` + `pending_fulltext.csv`(见 §"必出产物")
- **导读产出**(给人读,单篇精读笔记):`{论文标题}_report.md`,按下述 10 项导航元素组织

两类产出**职责分离**:csv 是数据,md 报告是学习材料。**不要混合**——csv 字段不应承担"教读者"的责任,md 报告不应放在"机器消费"的预期上。

这里的"下游任务"**不只等于 `survey-writer`**。`evidence_table.csv` 也可以直接服务于：
- 单篇精读归档
- 多篇方法对比
- research gaps 梳理
- 开题前证据盘点
- 用户手动继续写作

### md 报告的 10 项导航必备元素

1. **报告导读**(最顶层):本报告怎么读 / 适合谁读 / 30 秒应急通道 / 本文核心问题(4 个分项)
2. **主线因果链**(独立段,置于 Pass 1 与 Pass 2 之间):用 ASCII 流程图把论文论证的"骨架"画出来,让读者读 Pass 2 之前先建立心智模型
3. **每遍开头加"本遍阅读目标"**(Pass 1 解决理解 / Pass 2 结构化记录 / Pass 3 质疑推演——三遍各自不同)
4. **每遍末尾加"读到这里你应该明白"**(自测式列表,让读者验证自己是否真的吸收了本遍内容)
5. **图表逐一解读**(每张图独立 H4 小节,4 段:图说什么 / 读图能得出 / 论证作用 / 解释意义;外加一段 **"以后看到类似图怎么读"** —— 把"读这一篇"升级为"教你读这类")
6. **定量表附"数据来源"标注**(每张表前明确说明:抄自论文 Table X / 多源合并 / 散文抽数。避免读者怀疑"是不是你编的")
7. **每张表附"这张表以后怎么用"**(说明这张表在综述写作 / 开题报告 / 跨论文对比中的应用)
8. **术语表分三层**(A 必懂 6 / B 方法层 / C 进阶):避免"词典墙",按渐进学习需求分层
9. **Pass 3 问题分级**(A 类影响结论解释 / B 类影响推广 / C 类优化空间):避免读者把"硬伤"和"未来工作"等同对待
10. **末尾加"最终学习验收"**(清单 + 核心资产表 + 下次该读什么):闭环让读者知道"读完后应该能做什么"

### 风格契约

- **文风**:通俗但工整的科普文。不堆缩写也不卖萌(不"坑/抖了/猛踩油门")。类比可以保留但要工整("暖气全天开启 vs 室温过低才启动"可以,"暖气一直开 vs 冷了才开"太家常)
- **术语注解**:第一次出现时配括号注解一句人话(如"COV_IMEP,衡量缸内每次燃烧循环一致性的指标,数值越低代表燃烧越稳定"),不单设额外的"内联词表"——独立的术语表只在 Pass 2 §2 出现
- **小白提示框**:节制使用,3-5 个分布在关键节点(迟滞带、权衡 vs 最优、质疑的意义、A/B/C 级别意义、术语表查法),不要每段都加
- **等深度原则**:同一文档内并列章节(图 vs 表 / 不同子节)的分析厚度必须一致。如果一段用了五段细分,所有同级段都要五段细分

### 截图规范

如果论文有图,**默认截图入库**(放 `figures/` 子目录,300 DPI PNG):
- 用 pymupdf(`import fitz`)而非 poppler——后者在 mac 上常未装
- 用 `page.search_for("Fig. N.")` 精确定位 caption rect,反推图边界
- **跨页图**(如多子图论文常见):用 numpy.vstack 拼接两页内容(无需 PIL)
- 算法陷阱:caption 上方"最近 text block"会被子图内部 a/b/c/d 标签污染,Fig.1 这种页顶图直接用 y=60 作上边界
- 多子图论文(如"4 子图"实为 12 子图 4×3)**必须看图核实**,不要从摘要文字推断

详见 `essay-analyze/jfue-d-26-03086/figures/` 与 `lessons.md` 2026-05-13 条目。

### 触发条件

- **单篇精读模式**(用户传入单个 PDF / paper_uid 时):必须输出 md 导读报告 + csv 结构化数据
- **批量模式**(study_selection.csv 含 ≥ N 条 include):默认只产 csv 三件套;md 导读报告对每条单篇按需触发(用户用 `/read <uid>` 单独命中)

### 下游分流规则

reading 完成后,默认**不假设一定进入 `survey-writer`**。按用户目标分流：

- 用户要"写综述 / related work / research gaps" → `survey-writer`
- 用户要"把几篇方法拉出来对比" → 直接基于 `evidence_table.csv` 做 comparison
- 用户要"单篇吃透 / 给我讲明白" → 留在 `essay-analyze/` 单篇导读通路
- 用户要"先把证据沉淀好,写作以后再说" → 只交付 reading 产物,不进入 writer

### 输出位置

- 单篇 md 报告:`essay-analyze/{paper_uid}/{论文标题简化}_report.md` + `essay-analyze/{paper_uid}/figures/`(截图) + `essay-analyze/{paper_uid}/evidence_table.csv`
- 批量 csv 三件套:`runs/{YYYY-MM-DD}_{主题}/02-reading/`
- Obsidian 同步路径:详见 `workspace-map.md` § Obsidian 同步路径

### 案例参照

- `essay-analyze/Cooling-Guided Diffusion Model for Battery Cell Arrangement_report.md` — 早期参照样本(三遍结构 + 大白话风格已成型)
- `essay-analyze/jfue-d-26-03086/Smart On-Demand Hydrogen Assist for SI Engine_report.md` — **2026-05-13 完整版"小白自学手册"**,含全部 10 项导航元素 + 5 张图截取(Fig.4/5 跨页拼接) + 25 字段 csv。**新文档直接参照此版本结构**

---

## 全文获取通路

| 通路 | 覆盖 | Pass 1 | Pass 2 | Pass 3 |
|------|------|--------|--------|--------|
| **abstract-only** | OpenAlex/Crossref 已有 abstract | ✅ | ✅(主路径) | ❌ |
| **arXiv 预印本** | arxiv:* paper_uid | ✅ | ✅ | ✅(PDF 全文) |
| **Unpaywall OA PDF** | OA 出版社 | ❌ | P1 加 | P1 加 |
| **学校 CARSI** | Elsevier 等闭源 | ❌ | ❌ | P2 加 |

详见 `channels.md`。

---

## Abstract 缺失降级链（2026-05-12 增补，2026-05-12 修订）

工程类论文（尤其 Elsevier：Fuel / IJHE / Energy / RSER）经常 OpenAlex 返回 metadata 但 `abstract_inverted_index` 为空。**禁止基于 title 裸推断 abstract**——会产生与原文严重偏离的虚假证据（实测会让综述出现张冠李戴）。降级顺序：

1. **Elsevier API**（**优先级最高**，对 Elsevier DOI 100% 命中）
   - 触发条件：`ELSEVIER_API_KEY` 环境变量存在 + DOI 前缀 `10.1016/`（Elsevier）
   - Endpoint：`https://api.elsevier.com/content/article/doi/<DOI>?apiKey=<KEY>`，`Accept: application/json`
   - 返回 `full-text-retrieval-response.coredata.dc:description` 即完整 abstract（实测 13/13 Elsevier 论文 = 100%，2026-05-12 验证）
   - **不要**用 `/content/abstract/doi/...` 端点（`dc:description` 经常为空，且 `view=FULL` 返回 AUTHORIZATION_ERROR）
   - 标 `extraction_source=Elsevier API`，`extraction_confidence=high`
   - **配置说明**：需在 `.env` 文件中配置 `ELSEVIER_API_KEY=your_key_here`。申请地址：https://dev.elsevier.com/
2. **OpenAlex** (`api.openalex.org/works/doi:<DOI>`) — 检查 `abstract_inverted_index`，重建 abstract
3. **SS no-key DOI** (`api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=abstract`)
4. **Crossref** (`api.crossref.org/works/<DOI>` → `message.abstract`)
5. **WebSearch** with query: `"<title 前 5-8 词>" <第一作者姓> <期刊> <年份> abstract`
   - 接受搜索引擎合成 abstract（常含原文具体数值）
   - 必填 `extraction_source=WebSearch` + `extraction_confidence`：
     - `high` = 含具体数值 / 被多个站点确认
     - `medium` = 同作者邻近论文佐证
     - `low` = 独立检索找不到匹配（疑似 OpenAlex 索引超前 / 引用错误）
6. **全部失败** → `pending_fulltext.csv`，标 `pending_fulltext=true`，不进 `evidence_table.csv`

**SS API Key 持有用户**：环境变量 `SEMANTIC_SCHOLAR_API_KEY` 存在时，可在 step 2-3 之间插入 SS search/batch 端点。但 2026-05-12 申请被拒（SS 收紧审批），优先依赖 Elsevier API。
   - **配置说明**：需在 `.env` 文件中配置 `SEMANTIC_SCHOLAR_API_KEY=your_key_here`。申请地址：https://www.semanticscholar.org/product/api

**实测记录**：
- 氢辅助 SI（9/13 缺）+ 氨燃料 SI（6/13 缺）= 15 篇缺
- **Elsevier API（2026-05-12 接入后）**：13/15 成功获取（剩 2 篇是非 Elsevier 期刊：SAE 1 + Frontiers 1）
- 改用 Elsevier API 前 WebSearch 降级链：11/15 成功（high 9 / medium 1 / low 1 / 全失败 4）

**禁止行为**：
- ❌ 在 abstract 字段填入"AI 基于 title 推断"的内容
- ❌ 把 WebSearch 合成 abstract 标为 `extraction_source=abstract`（必须显式标 `WebSearch`）
- ❌ 在没有任何来源支持时硬抽 PICO 字段
- ❌ 用 `https://api.elsevier.com/content/abstract/...` 端点（除非确认有 view=FULL 权限）

### 脚本实现（2026-05-13 增补）

降级链 Step 1-4 已封装为 `tools/abstract_pipeline.py`（综合工具）：

```bash
# 单点查 1 个 DOI
python3 $STUDY_RESEARCH_ROOT/tools/abstract_pipeline.py <DOI>

# 批量查 candidate_papers.csv 全部
python3 $STUDY_RESEARCH_ROOT/tools/abstract_pipeline.py \
    --batch <csv> --out <json> --verbose
```

返回 `{status, source, abstract, attempted[]}`。`status="needs_websearch"` 时由 paper-reading 自己在 reading 阶段调 WebSearch 补 Step 5。

详见 `tools/abstract_pipeline.py` 模块 docstring 与 `paper-discovery/SKILL.md` "Abstract Enrichment Pipeline" 章节。

---

## 命令体系（借鉴 articlefeed）

本 skill 支持以下命令，用户可直接调用：

| 命令 | 做什么 | 输入 | 产出 |
|------|--------|------|------|
| `/read <paper_uid>` | 单篇论文 Pass 1+2 抽取 | paper_uid | 单条 evidence |
| `/read --batch` | 批量处理全部 include | study_selection.csv | evidence_table.csv |
| `/recap` | 阅读进度全局视图 | evidence_table.csv | reading_summary.md |
| `/compare <uid1> <uid2>` | 两篇论文对比 | 两个 paper_uid | 对比表格 |
| `/deep <paper_uid>` | Pass 3 深度分析 | paper_uid + 全文 | Pass 3 字段 |

---

## LLM 抽取策略（借鉴 AlpaPICO）

### Prompt 设计原则

1. **Few-shot ICL**: 每个 Pass 配 2-3 个示例（正例 + 边界例），示例从 dryrun 的 6 条样本中选
2. **Structured output**: 强制 JSON 格式，避免自由文本漂移
3. **Chain-of-thought**: 先让 LLM 写推理过程，再给出结论（提高准确率）
4. **Self-consistency**: 关键字段抽 3 次取多数投票（P2 实施，P0 先不做）

### Prompt 模板结构

```
[系统角色]
你是学术论文分析助手。你的任务是从论文 abstract 中抽取结构化信息。
严格遵循以下规则：没有的信息留空，不猜测，不编造。

[任务定义]
用 Keshav 三遍阅读法的 Pass 1 五问 + PICO 框架分析以下论文。

[示例 1 — 综述类]
Input: <abstract>
Output: { "category": "review", "context": "...", ... }

[示例 2 — 实验类]
Input: <abstract>
Output: { "category": "empirical_cfd", "population": "...", ... }

[示例 3 — 边界例(abstract 不足)]
Input: <abstract>
Output: { "pass1_verdict": "skip", "reason": "abstract 仅 2 句，无方法描述" }

[待分析论文]
Title: {title}
Abstract: {abstract}
Keywords: {keywords}

[输出格式]
严格按照以下 JSON schema 输出：
{schema}
```

---

## P0 边界（必须遵守）

### 做什么
- ✅ Pass 1 五问 + Pass 2 PICO，两层全部走通
- ✅ arXiv 论文走 PDF 全文 Pass 3（P0 只验证可行性，不批量跑）
- ✅ 无 abstract 论文打 `pending_fulltext=true`，不硬抽
- ✅ review 类标记 `qualitative_only=true`
- ✅ Quality gate: Pass 1 ≥60% proceed + Pass 2 ≥80% complete
- ✅ 跨文件一致性自检（evidence_table.paper_uid ⊆ study_selection.include）

### 不做什么
- ❌ 重新检索/扩候选（paper-discovery 的事）
- ❌ 重新纳排/改 selection（paper-screening 的事）
- ❌ 写综述/比较矩阵（survey-writer 的事）
- ❌ Pass 3 批量跑（P0 只验证单条）
- ❌ Self-consistency 多轮投票（P1 再加）

---

## 按交付包的产物定义

### `reading-only`

用于“先沉淀证据,暂不写综述”。

| 文件 | 说明 |
|------|------|
| `evidence_table.csv` | 主证据表。字段见 artifacts.md §1 |
| `evidence_audit.md` | 审计记录：每条论文的 Pass 1/2/3 状态、抽取来源、置信度 |
| `pending_fulltext.csv` | 因无 abstract/无全文通路而跳过的论文 |
| `low_confidence_evidence.csv` | extraction_confidence=low 的论文（不进入主表） |
| `reading_summary.md` | 给用户的三段式总结：抽了多少/跳了多少/质量分布；显式写 `delivery_mode=reading-only` |

### `single-paper-guide`

用于“先把单篇论文读懂”。

| 文件 | 说明 |
|------|------|
| `{paper_title}_report.md` | 单篇导读报告；头部显式写 `delivery_mode=single-paper-guide` |
| `evidence_table.csv` | 该论文对应的单行/单篇结构化证据 |
| `figures/` | 条件产出；论文含关键图时截图入库 |

### `comparison-ready`

用于“下一步做方法对比 / gaps 梳理,但还不进入 writer”。

| 文件 | 说明 |
|------|------|
| `evidence_table.csv` | 可比较论文的结构化证据池 |
| `evidence_audit.md` | 比较前的证据可靠性说明 |
| `reading_summary.md` | 必须包含推荐比较论文与比较维度,并显式写 `delivery_mode=comparison-ready` |

## 必出产物(按批量主链)

| 文件 | 说明 |
|------|------|
| `evidence_table.csv` | 主证据表。字段见 artifacts.md §1 |
| `evidence_audit.md` | 审计记录：每条论文的 Pass 1/2/3 状态、抽取来源、置信度 |
| `pending_fulltext.csv` | 因无 abstract/无全文通路而跳过的论文 |
| `low_confidence_evidence.csv` | extraction_confidence=low 的论文（不进入主表） |
| `reading_summary.md` | 给用户的三段式总结：抽了多少/跳了多少/质量分布 |

---

## 借鉴矩阵

| 来源 | 抄什么 |
|------|--------|
| Keshav "How to Read a Paper" (2007) | 三遍阅读框架 + 五问(Category/Context/Correctness/Contributions/Clarity) + 分层策略 |
| AlpaPICO (Ghosh et al., 2024) | Few-shot ICL prompt 设计 + structured JSON output + CoT 推理 |
| articlefeed (Okayamasenko) | 命令体系 (/read /recap /compare) + 阅读追踪 + 持久记忆 |
| didi-skills paper-proofread | 四层渐进思想(30秒→骨架→深度→连接) + 视觉化输出理念 |
| LLM-assisted SR review (2024) | Quality gate 阈值(precision 83%/recall 86% 为基线) + 人类评审不可缺 |
| dryrun (2026-05-05) | 12 列 evidence schema + extraction_confidence + qualitative_only + 5/6=83% 通过率 |

---

## 给下游任务的承诺

- `evidence_table.csv` 每行 paper_uid 都在 `study_selection.csv` 中且 `selection=include`
- `extraction_confidence ∈ {high, medium}` 的行可直接用于综述、比较、gap 梳理
- `extraction_confidence=low` 的行下游应显式标注"低置信"
- `qualitative_only=true` 的行只能作为定性观点，不能当定量证据
- `pending_fulltext.csv` 中的论文不出现在 `evidence_table.csv`
- **Pass 1 的 `contributions` 字段是综述写作与方法对比的核心输入之一**

---

## P0 阶段不做

- 不做 Self-consistency 多轮投票（P1 加）
- 不做 retraction check（P1 加）
- 不做 figure/table 结构化抽取（只读文本）
- 不做 citation graph 分析（P2）
- 不做 Pass 3 批量跑（P0 只验证单条 arXiv 全文）

## 自检清单

- [ ] Pass 1 五问（Category/Context/Correctness/Contributions/Clarity）每篇都有答案？
- [ ] Pass 1 verdict 分布：proceed ≥ 60% include 总数，confidence 为 high/medium？
- [ ] Pass 2 PICO 字段（Population/Intervention/Comparator/Outcome）抽取率 ≥ 80%？
- [ ] `extraction_confidence=low` 的论文进 `low_confidence_evidence.csv`，不进主表？
- [ ] `evidence_table.csv` 的 paper_uid 都是 `study_selection.csv` 中 selection=include 的？
- [ ] `pending_fulltext.csv` 中的论文不在 `evidence_table.csv` 中？
- [ ] `qualitative_only=true` 的 review 类论文被正确标记？
