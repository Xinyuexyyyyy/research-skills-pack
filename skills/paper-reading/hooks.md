# Paper Reading — Hooks(钩子覆盖详情)

> 对接 `research-base/hooks.md` 的 6 大钩子。本 skill 覆盖 3 个,其他让位。
> 抽取核心基于 **Keshav 三遍阅读法 + PICO 框架 + AlpaPICO ICL 策略**。

---

## 钩子执行顺序

```
study_selection.csv (selection=include 行)
   ↓
[hook_retrieve] arxiv:* 论文 → fetch_arxiv.py → data/fulltext/*.pdf
   ↓
[hook_extract_pass1] 每篇论文 → LLM Pass 1 扫描 → pass1_verdict
   ↓        ├─ skip → pending_fulltext.csv
   ↓        ├─ demote → evidence_table.csv (qualitative_only=true, 无 PICO)
   ↓        └─ proceed → [hook_extract_pass2]
   ↓
[hook_extract_pass2] 每篇 proceed 论文 → LLM Pass 2 抽取 → evidence_table.csv
   ↓        ├─ extraction_confidence ∈ {high, medium} → evidence_table.csv
   ↓        └─ extraction_confidence=low → low_confidence_evidence.csv
   ↓
[hook_review] Quality gate × 3 + 跨文件一致性 → 全过则 PASS
   ↓
evidence_table.csv + pending_fulltext.csv + low_confidence_evidence.csv + reading_summary.md
```

**收尾要求：**
- `reading_summary.md` 必须显式写 `delivery_mode=reading-only|comparison-ready`
- 若是单篇导读通路,单篇报告头部必须写 `delivery_mode=single-paper-guide`
- 若本次在 run 包内执行,应同步更新顶层 `README.md` 的：
  - `current_layer=reading`
  - `delivery_mode=<...>`
  - `next_step=<go_survey|go_comparison|go_gap_analysis|fetch_fulltext|stop_here>`

---

## hook_retrieve(部分覆盖)

### 范围
仅对 `paper_uid` 起头是 `arxiv:` 的论文执行 PDF 下载。其他论文走 abstract-only 路径或进 pending_fulltext。

### 实施
- 工具:`scripts/fetch_arxiv.py`(纯 stdlib,无第三方依赖)
- 入口:`python3 fetch_arxiv.py <arxiv_id1> [<arxiv_id2> ...]`
- 输出位置:`data/fulltext/arxiv-<id>.pdf`
- 容错:超时(30s)/ 404 / 非 PDF 头 / 文件过小(< 1KB)→ 记录为失败,转 ar5iv HTML 或 abstract-only

### ar5iv HTML fallback
```
https://ar5iv.labs.arxiv.org/html/<arxiv_id>
```
- 公式渲染为 mathml,LLM 可读
- 表格结构化为 HTML table
- 局限:仅 2007 年后 arxiv 论文(LaTeX 源可获取)

---

## hook_extract_pass1(完全覆盖)— Keshav 五问扫描

### 目标
5-10 分钟/篇(实际 LLM 调用一次),回答 Keshav 五问,产出 Pass 1 裁决。

### LLM Prompt 模板(Few-shot ICL)

```
你是学术论文分析助手,严格遵循 Keshav "How to Read a Paper" 的 Pass 1 方法。
你的任务是从论文的 title + abstract + keywords 中回答五问,并给出 Pass 1 裁决。

## 铁律
1. 只从输入文本抽,不外推,不编造
2. 字段无信息就写 null,不要写 "UNKNOWN" / "N/A"
3. contributions 必须 1-3 条,每条一句话,直接摘自文本
4. 回答五问后才能给 verdict,不能凭感觉

## 五问定义
1. Category: 这是什么类型的论文?
   候选: review(综述) / empirical_cfd(计算流体力学实验) / empirical_material(材料实验)
         / empirical_optimization(优化实验) / empirical_ai(AI/ML 实验)
         / theoretical(理论推导) / survey(调查研究)

2. Context: 与哪些论文/理论相关?属于哪个研究方向?
   从 keywords 和 abstract 第一句/最后一句推断

3. Correctness: 论文的假设是否合理?
   valid(合理) / questionable(有疑问) / insufficient_info(信息不足)

4. Contributions: 论文的 1-3 条核心贡献(一句话每条)
   直接摘自 abstract 的贡献声明句

5. Clarity: 论文写作质量如何?
   well_written(结构清晰,逻辑通顺)
   / acceptable(能看懂,有小问题)
   / poorly_written(结构混乱,难以理解)

## Pass 1 裁决规则
- proceed_to_pass2: 五问中 ≥4 问有明确答案,且 contributions ≥1 条
- demote_to_qualitative_only: review/survey 类论文,或 abstract 只有方向描述无具体方法
- skip: abstract 完全无法回答 ≥3 问(如 abstract < 50 字符或纯占位符)

## 输出格式
严格 JSON:
{
  "category": "...",
  "context": "...",
  "correctness_flag": "valid|questionable|insufficient_info",
  "contributions": ["贡献1", "贡献2", "贡献3"],
  "clarity_score": "well_written|acceptable|poorly_written",
  "pass1_verdict": "proceed_to_pass2|demote_to_qualitative_only|skip",
  "pass1_confidence": "high|medium|low",
  "pass1_reason": "一句话说明为什么给这个 verdict"
}

## 示例 1 — 综述类(应 demote)
Input: Title="Review of battery thermal management..."
      Abstract="This paper reviews how heat is generated..."
      Keywords=["Battery", "Thermal management", "Electric vehicle"]
Output: {
  "category": "review",
  "context": "电池热管理综述,涵盖空气冷却/液冷/相变材料/热电四种方案",
  "correctness_flag": "valid",
  "contributions": ["综述四种电池热管理方案及其适用场景"],
  "clarity_score": "well_written",
  "pass1_verdict": "demote_to_qualitative_only",
  "pass1_confidence": "high",
  "pass1_reason": "综述类论文,abstract 只有方向描述无具体实验方法,适合定性引用"
}

## 示例 2 — 实验类(应 proceed)
Input: Title="Cooling performance optimization of air-cooled BTMS"
      Abstract="Abstract Air-cooled BTMS is usually employed... a new method was introduced..."
Output: {
  "category": "empirical_cfd",
  "context": "空气冷却电池热管理系统的 CFD 优化研究",
  "correctness_flag": "valid",
  "contributions": [
    "提出平行板安装方法改善电池组气流分布",
    "模拟比较 9 种原始 BTMS 的冷却性能"
  ],
  "clarity_score": "well_written",
  "pass1_verdict": "proceed_to_pass2",
  "pass1_confidence": "high",
  "pass1_reason": "abstract 明确给出方法(平行板)和结果(温度降低 3.42K/6.4K)"
}

## 待分析论文
Title: {title}
Abstract: {abstract}
Keywords: {keywords}
```

### Pass 1 自检
- `pass1_verdict=skip` → 写入 pending_fulltext.csv,不进入 Pass 2
- `pass1_verdict=demote` → 写入 evidence_table.csv,但 `qualitative_only=true`,不抽 PICO
- `pass1_verdict=proceed` → 进入 Pass 2,但需 `pass1_confidence ∈ {high, medium}`
- `pass1_confidence=low` → 视为 "proceed_with_caution",Pass 2 抽取后强制标 medium

---

## hook_extract_pass2(完全覆盖)— PICO + 方法 + 发现

### 目标
从可用文本中抽 PICO + method + key_findings。仅对 Pass 1 verdict=proceed 的论文执行。

### LLM Prompt 模板(Few-shot ICL)

```
你是学术论文证据抽取助手。基于以下输入,抽出 PICO + 方法 + 关键发现。

## 铁律
1. 只从输入文本抽,不外推,不编造
2. 字段无信息就写 null,不要写 "UNKNOWN" / "N/A"
3. outcome 优先数值化(如 "ΔT ↓6.4K(90.78%)")
4. key_finding 必须带支撑证据(数值/对比/实验结果),不能只是作者声称

## 抽取字段
- population: P — 研究对象/场景/电池类型
- intervention: I — 主要技术/方法/干预手段
- comparator: C — 对照/基准(如有)
- outcome: O — 结果指标,数值化优先
- method: 方法学描述(技术路线/实验设计/CFD 设置)
- key_finding_1/2/3: 1-3 条核心发现,每条 1-3 句,带数值

## 置信度判据
- high: P/I/O/Method 全有,且 outcome 数值化或 abstract 直接给出精确结果
- medium: P/I/M 全有但 outcome 偏定性,或缺一项次要字段(C 或 key_finding_3)
- low: P/I/M 任一为空,或仅靠 title+keywords 推测,或 abstract 完全无方法描述

## 输出格式
严格 JSON:
{
  "population": "...",
  "intervention": "...",
  "comparator": "...",
  "outcome": "...",
  "method": "...",
  "key_finding_1": "...",
  "key_finding_2": "...",
  "key_finding_3": "...",
  "extraction_confidence": "high|medium|low",
  "extraction_source": "abstract|abstract+methods|fulltext|title_only"
}

## 示例 — 完整实验类
Input: Title="Cooling performance optimization of air-cooled BTMS"
      Abstract="... a new method was introduced... The results showed that compared to the typical Z-type BTMS, the maximum temperature... were reduced by 3.42 K (6.26%) and 6.4 K (90.78%)..."
Output: {
  "population": "锂离子电池组,空气冷却 BTMS",
  "intervention": "平行板安装方法改善气流分布",
  "comparator": "典型 Z 型 BTMS",
  "outcome": "最高温度降低 3.42K(6.26%),温差降低 6.4K(90.78%)",
  "method": "CFD 模拟,比较 9 种原始 BTMS",
  "key_finding_1": "平行板安装能有效改善电池组气流分布",
  "key_finding_2": "最优方案相比 Z 型 BTMS 最高温度降低 3.42K(6.26%)",
  "key_finding_3": "温差降低 6.4K,改善幅度达 90.78%",
  "extraction_confidence": "high",
  "extraction_source": "abstract"
}

## 待分析论文
Title: {title}
Abstract: {abstract}
Keywords: {keywords}
Fulltext(如有): {fulltext}
```

### Pass 2 自检
- `extraction_confidence=low` → 不进 evidence_table.csv,进 low_confidence_evidence.csv
- `population` / `intervention` / `method` 任一为空 + `qualitative_only=false` → 强制 `extraction_confidence=low`
- `extraction_source=fulltext` 必须配 `extraction_confidence ∈ {high, medium}`

---

## hook_review(覆盖)— 三层 Quality Gate

### Gate 1 — Pass 1 Gate
```
proceed_count / include_count ≥ 0.60
```
- 失败:screening 阶段过松,大量 include 论文 Pass 1 就 skip
- 处理:回溯 paper-screening,收紧纳排标准

### Gate 2 — Pass 2 Gate
```
evidence_table.row_count / (evidence_table.row_count + low_confidence_evidence.row_count) ≥ 0.80
```
- 失败:大量论文 Pass 2 置信度 low
- 处理:扩全文通路(P1 接 Unpaywall)或调 prompt

### Gate 3 — 跨文件完整性
```
evidence_table.row_count + pending_fulltext.row_count + low_confidence_evidence.row_count
== study_selection.where(selection=include).row_count
```
- 失败:有论文"消失"(既不在 evidence 也不在 pending)
- 处理:排查丢失

### 自检 5 条(额外)
1. `evidence_table.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
2. `pending_fulltext.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
3. `low_confidence_evidence.paper_uid ⊆ study_selection.where(selection=include).paper_uid`
4. evidence ∩ pending ∩ low_confidence = ∅(三者无交集)
5. `evidence.extraction_source=fulltext` ⇒ `extraction_confidence ∈ {high, medium}`

### Quick check 脚本
```bash
cd <run_dir>
et=$(($(wc -l < evidence_table.csv) - 1))
pt=$(($(wc -l < pending_fulltext.csv) - 1))
lc=$(($(wc -l < low_confidence_evidence.csv 2>/dev/null || echo 0) - 1))
total=$((et + pt + lc))
rate=$(echo "scale=1; $et*100/($et + $lc)" | bc)
echo "evidence: $et, pending: $pt, low_conf: $lc, total: $total, gate2: $rate%"
# 检查交集
for f in evidence_table.csv pending_fulltext.csv low_confidence_evidence.csv; do
  [ -f "$f" ] && tail -n +2 "$f" | cut -d',' -f1 | sort > "/tmp/$(basename $f .csv).uids"
done
# 三者交集应为空
```

### delivery_mode 决策规则

- 用户目标是"先沉淀证据,暂不写综述" → `delivery_mode=reading-only`
- 用户目标是"逐篇读懂 / 导读报告 / essay-analyze" → `delivery_mode=single-paper-guide`
- 用户目标是"下一步做方法对比 / gaps 梳理" → `delivery_mode=comparison-ready`
- 若准备直接进入 writer,reading 层仍要先写 `delivery_mode=reading-only` 或 `comparison-ready`,再在 run README 的 `next_step` 写 `go_survey`

---

## 不覆盖的钩子(让位)

### hook_clarify ⛔
不澄清 PICO/framework — 上游 paper-screening 已澄清。本 skill 内只读 `study_selection.csv`。

### hook_screen ⛔
不重做纳排。即使发现某篇 include 论文 abstract 太烂,也只能打 pending,不改 selection。

### hook_synthesize ⛔
不写综述/比较矩阵 — 那是 survey-writer 的事。
