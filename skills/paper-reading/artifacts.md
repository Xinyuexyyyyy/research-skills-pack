# Paper Reading — 产出 Schema

> 本 skill 实际写入的产物 schema。复用 `research-base/artifacts.md` 的 paper_uid 等公共字段;新增 `evidence_table.csv`、`pending_fulltext.csv`、`low_confidence_evidence.csv`。
>
> **设计基于 Keshav 三遍阅读法**：Pass 1 五问 → Pass 2 PICO → Pass 3 深度。字段按 Pass 分层，不强行填充不可得的字段。

---

## 文件清单总览

| 文件 | 类型 | 必出 | 说明 |
|---|---|---|---|
| `evidence_table.csv` | CSV | ✅ | Pass 1+2 抽取成功的论文(每行一篇) |
| `evidence_audit.md` | Markdown | ✅ | 抽取审计 + 置信度判据 + Pass 分层记录 |
| `pending_fulltext.csv` | CSV | ✅(可空) | Pass 1 裁决 skip 的论文(无 abstract/无通路) |
| `low_confidence_evidence.csv` | CSV | 条件 | Pass 2 置信度 low 的论文(不进入主表) |
| `reading_summary.md` | Markdown | ✅ | 给用户的三段式总结 |
| `data/fulltext/arxiv-<id>.pdf` | PDF | 条件 | arXiv 论文全文 PDF |
| `delivery_mode` | enum | ✅(写入 summary / run README) | `reading-only` / `single-paper-guide` / `comparison-ready` |

---

## 交付包定义

> `paper-reading` 的结果按用户目标收成 3 类交付包。
> 同一批 reading 结果可以服务多个下游，但每次交付至少应明确属于哪一类。

### A. `reading-only` 包

**适用场景：**
- 用户要先把证据沉淀好
- 暂时不写综述
- 需要为后续人工写作 / gap 梳理 / 开题准备留底

**最小必出：**
- `evidence_table.csv`
- `evidence_audit.md`
- `pending_fulltext.csv`
- `reading_summary.md`
- `low_confidence_evidence.csv`（若存在 low 置信条目则必出）

**默认落盘：**
- `runs/{YYYY-MM-DD}_{topic}/02-reading/`

**算完成的条件：**
1. `evidence_table.csv` 可直接复用
2. `pending_fulltext.csv` 与 low 置信条目标识清楚
3. `reading_summary.md` 能说明“现在能不能继续往下用”
4. `reading_summary.md` 或 run README 明确写出 `delivery_mode=reading-only`

### B. `single-paper-guide` 包

**适用场景：**
- 用户要“先把这篇论文读懂”
- 用户要导读报告 / 逐篇精读笔记
- 论文会单独沉淀到 `essay-analyze/`

**最小必出：**
- `{paper_title}_report.md`
- `evidence_table.csv`（至少 1 行，对应该 paper）

**推荐产出：**
- `figures/`（若论文含关键图）
- `evidence_audit.md`

**默认落盘：**
- `essay-analyze/{paper_uid}/`

**算完成的条件：**
1. 单篇导读报告可独立阅读
2. 结构化证据与导读报告引用的是同一篇论文
3. 读者不依赖上游 run 也能看懂论文主线、方法、发现和局限
4. 单篇目录的报告头部明确写出 `delivery_mode=single-paper-guide`

### C. `comparison-ready` 包

**适用场景：**
- 用户下一步要做方法对比
- 用户要拉几篇代表性论文并排看
- 用户要做 research gaps，但还不准备写成长综述

**最小必出：**
- `evidence_table.csv`
- `evidence_audit.md`
- `reading_summary.md`

**额外要求：**
- `reading_summary.md` 必须明确写出：
  - 推荐比较的论文集合
  - 推荐比较维度（如 method / population / outcome / assumptions）
  - 哪些论文暂时不适合纳入对比（如 `pending_fulltext` / `qualitative_only`）

**默认落盘：**
- `runs/{YYYY-MM-DD}_{topic}/02-reading/`

**算完成的条件：**
1. 至少有 2 篇及以上论文可比
2. 对比维度已经被明确点名
3. 用户拿到包后，不需要重新读原文就能开始做 comparison / gap 盘点
4. `reading_summary.md` 明确写出 `delivery_mode=comparison-ready`

---

## §1 evidence_table.csv

**22 列**,UTF-8,LF 换行,每行一篇论文,`paper_uid` 唯一键(对齐 `study_selection.csv`)。

列按 Pass 分组:Pass 1 (7 列) → Pass 2 (11 列) → Pass 3 (4 列)。

### Pass 1 — 鸟瞰扫描字段(7 列)

| # | 列 | 类型 | 取值 | 说明 |
|---|---|---|---|---|
| 1 | `paper_uid` | string | doi:* / arxiv:* | 与 study_selection.csv 对齐 |
| 2 | `category` | enum | review / empirical_cfd / empirical_material / empirical_optimization / empirical_ai / theoretical / survey | Keshav 五问之一:什么类型? |
| 3 | `context` | string | 自由文本 | Keshav 五问之一:与哪些论文/理论相关? |
| 4 | `correctness_flag` | enum | valid / questionable / insufficient_info | Keshav 五问之一:假设是否合理? |
| 5 | `contributions` | string | 1-3 句 | Keshav 五问之一:核心贡献(供 survey-writer"研究贡献"章节) |
| 6 | `clarity_score` | enum | well_written / acceptable / poorly_written | Keshav 五问之一:写作质量 |
| 7 | `pass1_verdict` | enum | proceed_to_pass2 / demote_to_qualitative_only / skip | Pass 1 裁决 |
| 8 | `pass1_confidence` | enum | high / medium / low | Pass 1 置信度 |

### Pass 2 — 内容抓取字段(11 列)

| # | 列 | 类型 | 取值 | 说明 |
|---|---|---|---|---|
| 9 | `population` | string | "P" 描述 | PICO 之 P |
| 10 | `intervention` | string | "I" 描述 | PICO 之 I,主要技术/方法 |
| 11 | `comparator` | string | "C" 描述 | 对照/基准,无则空 |
| 12 | `outcome` | string | "O" 描述 | 数值化优先(如 `ΔT ↓6.4K(90.78%)`) |
| 13 | `method` | string | 方法学描述 | 如 `CFD simulation + 9 prototypes` |
| 14 | `key_finding_1` | string | 1-3 句 | 核心发现 1,带数值 |
| 15 | `key_finding_2` | string | 1-3 句 | 核心发现 2,可空 |
| 16 | `key_finding_3` | string | 1-3 句 | 核心发现 3,可空 |
| 17 | `extraction_confidence` | enum | high / medium / low | Pass 2 抽取置信度 |
| 18 | `extraction_source` | enum | abstract / abstract+methods / fulltext / title_only | 抽取来源 |
| 19 | `qualitative_only` | bool | true / false | review 类或 abstract 太泛时 true |

### Pass 3 — 深度复现字段(4 列, P2 实施)

| # | 列 | 类型 | 取值 | 说明 |
|---|---|---|---|---|
| 20 | `hidden_assumptions` | string | 自由文本 | 未明说的假设 |
| 21 | `limitations` | string | 自由文本 | 论文自陈局限 |
| 22 | `future_work` | string | 自由文本 | 作者指出的未来方向 |

### 铁律

- `pass1_verdict == skip` → 该行不出现在 evidence_table.csv,进 pending_fulltext.csv
- `pass1_verdict == demote_to_qualitative_only` → `qualitative_only=true`,不抽 PICO 数值字段
- `extraction_confidence=low` → 该行不进 evidence_table.csv,进 low_confidence_evidence.csv
- `population` / `intervention` / `method` 任一为空 + `qualitative_only=false` → `extraction_confidence=low`
- 不允许出现 `UNKNOWN` 字符串,该写空就写空

---

## §2 pending_fulltext.csv

记录 Pass 1 裁决 skip 的论文。

| # | 列 | 类型 | 取值 | 说明 |
|---|---|---|---|---|
| 1 | `paper_uid` | string | 同上 | 对齐 study_selection.csv |
| 2 | `reason_code` | enum | NO_ABSTRACT / ABSTRACT_INSUFFICIENT / FETCH_FAILED / PARSER_FAILED | 跳过原因 |
| 3 | `suggested_route` | enum | unpaywall / carsi / arxiv_only / give_up | 建议下一轮的获取通路 |
| 4 | `pass1_notes` | string | 自由文本 | Pass 1 扫描时记录的线索(keywords/标题信号) |

---

## §3 low_confidence_evidence.csv

记录 Pass 2 置信度 low 的论文(不进入 evidence_table.csv 主表,但保留供人工复查)。

| # | 列 | 类型 | 说明 |
|---|---|---|---|
| 1 | `paper_uid` | string | 同上 |
| 2 | `low_confidence_reason` | enum | MISSING_OUTCOME / MISSING_METHOD / ABSTRACT_TOO_SHORT / TITLE_ONLY |
| 3 | `partial_evidence` | string | JSON | 已抽到的部分字段(可能只有 P 和 I) |
| 4 | `suggested_action` | enum | fetch_fulltext / demote_to_qualitative / manual_review |

---

## §4 evidence_audit.md(模板)

每条 evidence 一段,按 Pass 分层:

```
## <paper_uid> — <title>

### Pass 1 审计
- 五问答案: category=<X> | context=<Y> | correctness=<Z> | contributions=<N> | clarity=<M>
- 裁决: <proceed_to_pass2 / demote / skip>
- 置信度: <high/medium/low> + 判据: <为什么>

### Pass 2 审计
- PICO: P=<> | I=<> | C=<> | O=<>
- 方法: <>
- 发现: <key_finding_1> | <key_finding_2> | <key_finding_3>
- 抽取来源: <abstract / fulltext / title_only>
- 置信度: <high/medium/low> + 判据: <为什么>
- qualitative_only: <true/false>

### Pass 3 审计(P2)
- 隐藏假设: <>
- 局限: <>
- 未来方向: <>
```

---

## §5 reading_summary.md(模板)

三段式,用人话写。若本次交付包属于 `comparison-ready`,必须再追加“比较建议”一节:

```
# Reading Summary

delivery_mode=<reading-only | comparison-ready>

## 一、Pass 1 扫描结果
<N> 篇论文扫描完成:
- <X> 篇 proceed_to_pass2 → 进入 Pass 2 深度抽取
- <Y> 篇 demote_to_qualitative_only → 只记定性观点
- <Z> 篇 skip → 进 pending_fulltext

## 二、Pass 2 抽取结果
<N> 篇论文 evidence 抽取完成:
- 高置信度(high): <A> 篇
- 中置信度(medium): <B> 篇
- 低置信度(low): <C> 篇 → 进 low_confidence_evidence.csv 供复查
- 抽取率: <N/total> = <X%>

## 三、下一步建议
1. <建议 1>
2. <建议 2>
3. <建议 3>

## 四、比较建议(仅 comparison-ready 必填)
- 推荐纳入比较的论文: <uid1, uid2, uid3>
- 推荐比较维度: <method / assumptions / outcome / scenario / data>
- 暂不建议纳入的论文: <uid + 原因>
```

---

## §6 Quality Gate

| Gate | 条件 | 通过线 | 失败处理 |
|------|------|--------|---------|
| Pass 1 Gate | `proceed_to_pass2` 比例 | ≥ 60% include | screening 阶段过松,需回溯 |
| Pass 2 Gate | evidence 完整抽取率 | ≥ 80% | 扩充全文通路或调 prompt |
| Cross-file Gate | evidence + pending + low_confidence = include 总数 | 100% | 有论文"消失",排查丢失 |

---

## §7 跨文件一致性自检

1. `evidence_table.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
2. `pending_fulltext.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
3. `low_confidence_evidence.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
4. 三者交集为空(evidence ∩ pending = ∅, evidence ∩ low_confidence = ∅, pending ∩ low_confidence = ∅)
5. `evidence.row_count + pending.row_count + low_confidence.row_count = include.row_count`
6. **Pass 1 Gate**: `proceed_count / include_count ≥ 0.60`
7. **Pass 2 Gate**: `evidence.row_count / (evidence.row_count + low_confidence.row_count) ≥ 0.80`
