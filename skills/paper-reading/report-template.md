# Paper Reading — Report Template(产物骨架)

> `paper-reading` 现在按**交付包**出结果，而不是默认所有场景都往一个目录里堆文件。
> 本文件给出 3 类交付包的最小骨架,以及各文件模板。
> 基于 Keshav 三遍阅读法:Pass 1(五问扫描) → Pass 2(PICO 抽取) → Pass 3(深度复现,P2)。

---

## 0. 交付包速查

| 交付包 | 用户目标 | 最小必出 | 默认位置 |
|---|---|---|---|
| `reading-only` | 先沉淀证据,暂不写综述 | `evidence_table.csv` + `evidence_audit.md` + `pending_fulltext.csv` + `reading_summary.md` | `<run_dir>/02-reading/` |
| `single-paper-guide` | 先把单篇论文读懂 | `{paper_title}_report.md` + 单篇 `evidence_table.csv` | `essay-analyze/{paper_uid}/` |
| `comparison-ready` | 下一步做对比 / gap 梳理 | `evidence_table.csv` + `evidence_audit.md` + `reading_summary.md(含比较建议)` | `<run_dir>/02-reading/` |

所有交付包都应显式写出:
- `delivery_mode=reading-only`
- `delivery_mode=single-paper-guide`
- `delivery_mode=comparison-ready`

---

## 1. evidence_table.csv(必出,可空)

**文件类型:** UTF-8 CSV,LF 换行,22 列固定,paper_uid 唯一键。

**最小骨架(2 行示例):**
```csv
paper_uid,category,context,correctness_flag,contributions,clarity_score,pass1_verdict,pass1_confidence,population,intervention,comparator,outcome,method,key_finding_1,key_finding_2,key_finding_3,extraction_confidence,extraction_source,qualitative_only,hidden_assumptions,limitations,future_work
doi:10.xxxx/abc.123,review,"电池热管理综述,涵盖空气/液冷/PCM/热电四种方案",valid,"综述四种电池热管理方案及其适用场景",well_written,demote_to_qualitative_only,high,"锂离子电池组","四种热管理技术对比",,,"文献综述+对比分析","空气冷却适合短途EV,液冷适合长途",,,"high","abstract",true,,,
arxiv:2403.10566,empirical_ai,"电池热管理+生成式AI优化",valid,"提出cooling-guided diffusion model优化电池布局;比TabDDPM高效5倍",well_written,proceed_to_pass2,high,"锂电池组","cooling-guided diffusion model(DDPM)","TabDDPM, CTGAN","温度降低(具体数值见原文)","DDPM+classifier guidance+cooling guidance","比TabDDPM有效5倍,比CTGAN有效66倍","position-based classifier保证布局可行性",,"high","abstract+methods",false,,,
```

**列分组:**
- Pass 1(8 列): category → pass1_confidence
- Pass 2(11 列): population → qualitative_only
- Pass 3(4 列): hidden_assumptions → future_work(P2 实施)

**铁律(详见 `artifacts.md` §1):**
- 字段无信息 → 留空,不写 `UNKNOWN`
- `pass1_verdict=skip` → 该行不出现在 evidence_table.csv,进 pending_fulltext.csv
- `pass1_verdict=demote` → `qualitative_only=true`,不抽 PICO 数值字段
- `extraction_confidence=low` → 不进 evidence_table.csv,进 low_confidence_evidence.csv
- `extraction_source=fulltext` ⇒ confidence ∈ {high, medium}
- P/I/Method 任一为空 + qualitative_only=false ⇒ extraction_confidence=low

---

## 2. pending_fulltext.csv(必出,可空)

**文件类型:** UTF-8 CSV,LF 换行,4 列。

**最小骨架:**
```csv
paper_uid,reason_code,suggested_route,pass1_notes
doi:10.1016/j.apenergy.2021.118434,NO_ABSTRACT,unpaywall_or_carsi,"Elsevier 论文 abstract 缺失;keywords 含'Flexible composite PCM'等推断方向但 P/I/O 不可抽"
doi:10.xxxx/timeout.456,ABSTRACT_INSUFFICIENT,arxiv_only,"abstract 仅 2 句,无方法描述"
```

**reason_code 取值:**
- `NO_ABSTRACT` — abstract 字段为空 / 长度 < 50
- `ABSTRACT_INSUFFICIENT` — abstract 有但不足以回答五问(如 < 2 句话)
- `FETCH_FAILED` — 通路 2 下载失败
- `PARSER_FAILED` — PDF/HTML 解析返回空文本

**suggested_route 取值:**
- `unpaywall` — 等 P1 接 Unpaywall
- `carsi` — P2 走 CARSI 浏览器手抓
- `arxiv_only` — 只能去 arXiv 重试
- `give_up` — 已穷尽通路

---

## 3. low_confidence_evidence.csv(条件产出)

**文件类型:** UTF-8 CSV,LF 换行,4 列。

**触发条件:** Pass 2 抽取时 `extraction_confidence=low`。

**最小骨架:**
```csv
paper_uid,low_confidence_reason,partial_evidence,suggested_action
doi:10.xxxx/xyz.789,MISSING_OUTCOME,"{\"population\":\"锂电池\",\"intervention\":\"液冷\"}",fetch_fulltext
doi:10.xxxx/abc.123,ABSTRACT_TOO_SHORT,"{\"population\":\"电池组\"}",demote_to_qualitative
```

---

## 4. evidence_audit.md(必出)

**文件类型:** Markdown,每条 evidence 一段,按 Pass 分层。

**骨架:**
```markdown
# Evidence Audit — <run_name>

> 每条 evidence 的抽取来源 / 字段完整度 / 置信度判据 / Pass 分层记录。

---

## <paper_uid_1> — <title>

### Pass 1 审计
- **五问答案:** category=<X> | context=<Y> | correctness=<Z> | contributions=<N> | clarity=<M>
- **裁决:** <proceed_to_pass2 / demote / skip>
- **置信度:** <high/medium/low> — <一句话判据>

### Pass 2 审计
- **PICO:** P=<...> | I=<...> | C=<...> | O=<...>
- **方法:** <...>
- **发现:** <key_finding_1> | <key_finding_2> | <key_finding_3>
- **抽取来源:** <abstract / fulltext / title_only>
- **置信度:** <high/medium/low> — <为什么>
- **qualitative_only:** <true/false>

### Pass 3 审计(P2)
- **隐藏假设:** <...>
- **局限:** <...>
- **未来方向:** <...>

---

## 跨文件总结

- **Pass 1:** proceed=<n> | demote=<n> | skip=<n>
- **Pass 2 抽取率:** <N>/<proceed_count> = <pct>%
- **置信度分布:** high=<n>, medium=<n>, low=<n>
- **qualitative_only:** <n> 篇
- **跳过原因:** <主要 reason_code>
- **下一轮可优化项:** <bullet 1-3 条>
```

---

## 5. reading_summary.md(必出)

**文件类型:** Markdown,三段式,**用人话写,不堆术语**。若本次交付是 `comparison-ready`,必须补第 4 节“比较建议”。

**骨架:**
```markdown
# Reading Summary — <run_name>

> 基于 Keshav 三遍阅读法的论文证据抽取结果。

delivery_mode=<reading-only | comparison-ready>

---

## 一、Pass 1 扫描结果

**<N> 篇论文扫描完成:**

| 裁决 | 数量 | 说明 |
|------|------|------|
| proceed_to_pass2 | <X> | 进入 Pass 2 深度抽取 |
| demote_to_qualitative_only | <Y> | 只记定性观点,不抽 PICO |
| skip | <Z> | 进 pending_fulltext |

Pass 1 通过率: <X>/<N> = **<pct>%**

---

## 二、Pass 2 抽取结果

**<N> 篇论文 evidence 抽取完成:**

| paper_uid | study_type | extraction_confidence | extraction_source |
|---|---|---|---|
| ... | ... | ... | ... |

- 高置信度(high): <A> 篇
- 中置信度(medium): <B> 篇
- 低置信度(low): <C> 篇 → 进 low_confidence_evidence.csv

抽取率: <A+B>/<X> = **<pct>%**(门槛 80%)

---

## 三、下一步建议

1. **可不可以放下游 survey-writer:** <yes / no + 理由>
2. **pending 论文怎么办:** <建议通路>
3. **low_confidence 论文怎么办:** <建议操作>
4. **Pass 3 候选:** <哪些论文值得深度精读>

---

## 四、比较建议(仅 comparison-ready 必填)

- **推荐纳入比较的论文:** <uid1, uid2, uid3>
- **推荐比较维度:** <method / assumptions / outcome / scenario / data>
- **不建议直接比较的论文:** <uid + 原因>
```

---

## 6. single-paper-guide 报告骨架

**文件类型:** Markdown,默认位于 `essay-analyze/{paper_uid}/{paper_title}_report.md`。

**最小骨架:**
```markdown
# <论文标题> — 单篇导读报告

delivery_mode=single-paper-guide

## 1. 报告导读
- 这篇论文解决什么问题:
- 适合谁读:
- 30 秒结论:

## 2. 主线因果链
<ASCII 流程图>

## 3. Pass 1: 鸟瞰扫描
- Category:
- Context:
- Correctness:
- Contributions:
- Clarity:

## 4. Pass 2: 结构化证据
- Population:
- Intervention:
- Comparator:
- Outcome:
- Method:
- Key findings:

## 5. 这篇论文的局限与边界
- 局限:
- 隐含假设:
- 哪些结论不能外推:

## 6. 以后怎么用这篇论文
- 放综述时可引用哪部分:
- 做 comparison 时应与谁比较:
- 做 gap 盘点时它能支持什么判断:
```

---

## 7. data/fulltext/(条件产出)

**触发:** arXiv PDF 下载或 ar5iv HTML 缓存。

```
data/fulltext/
├── arxiv-2403.10566.pdf      ← fetch_arxiv.py 下载
├── arxiv-2401.12345.pdf
└── ...
```

---

## 8. 自检命令(必跑,见 `hooks.md` hook_review)

```bash
cd <run_dir>/reading

# 行数 + quality gates
et=$(($(wc -l < evidence_table.csv) - 1))
pt=$(($(wc -l < pending_fulltext.csv) - 1))
lc=$(($(wc -l < low_confidence_evidence.csv 2>/dev/null || echo 0) - 1))
total=$((et + pt + lc))
gate1=$(echo "scale=1; ($et+$lc)*100/$total" | bc)
gate2=$(echo "scale=1; $et*100/($et+$lc)" | bc)
echo "evidence: $et, pending: $pt, low_conf: $lc, total: $total"
echo "Gate 1 (Pass 1 proceed ratio): $gate1% (threshold 60%)"
echo "Gate 2 (Pass 2 complete ratio): $gate2% (threshold 80%)"

# 不重叠检查
for f in evidence_table.csv pending_fulltext.csv low_confidence_evidence.csv; do
  [ -f "$f" ] && tail -n +2 "$f" | cut -d',' -f1 | sort > "/tmp/$(basename $f .csv).uids"
done
# 三者交集应为 0
```

**PASS 条件:**
- Gate 1 ≥ 60%
- Gate 2 ≥ 80%
- Gate 3: total == include 总数
- 三者交集 == 0

---

## 9. 各交付包的 Done 条件

### `reading-only`
- 核心 csv/md 文件齐全
- 能明确告诉用户“哪些能继续用、哪些还要补全文”
- `reading_summary.md` 有 `delivery_mode=reading-only`

### `single-paper-guide`
- 单篇报告可独立阅读
- 报告与单篇 `evidence_table.csv` 一致
- 报告头部有 `delivery_mode=single-paper-guide`

### `comparison-ready`
- `reading_summary.md` 有明确比较建议
- 至少点名 2 篇可比论文与 2 个以上比较维度
- `reading_summary.md` 有 `delivery_mode=comparison-ready`
