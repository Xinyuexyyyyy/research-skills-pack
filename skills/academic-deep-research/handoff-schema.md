# Handoff Schema — Skill 间交接合约

> 定义每个 skill 交接时的最低数据要求。下游 skill 在接收上游产出时，先检查合约是否满足；不满足的字段标记为 degraded，降级处理而非阻塞。

## 设计原则

1. **不阻塞，只降级**：合约不满足时不停止流程，而是标记并告知用户
2. **最小字段**：只约束真正影响下游质量的字段，不过度约束
3. **可机器检查**：字段要求明确到"非空""枚举值""数值范围"，不靠语义判断

---

## 合约 1：Discovery → Screening

交接物：`candidate_papers.csv`

| 字段 | 要求 | 不满足时的降级处理 |
|---|---|---|
| paper_uid | 非空、唯一 | 自动生成临时 uid，标记 warn |
| title | 非空 | 该行跳过 screening，标记 skip |
| year | 非空、2019-2026 | 保留但标记 out_of_range |
| abstract | 非空 | 标记 no_abstract，screening 时 confidence 自动降为 low |
| source | 非空、枚举值（semantic_scholar/openalex/arxiv/crossref/web） | 标记 unknown_source |
| doi_or_url | 非空 | 保留但标记 no_identifier |

**交接时输出**：
```
交接检查：candidate_papers.csv
- 总行数：46
- 合约满足：24 篇（全字段完整）
- 降级处理：22 篇（缺 abstract → screening 时 confidence 自动 low）
- 跳过：0 篇
```

---

## 合约 2：Screening → Reading

交接物：`study_selection.csv`

| 字段 | 要求 | 不满足时的降级处理 |
|---|---|---|
| paper_uid | 非空、与 candidate_papers.csv 对应 | 标记 orphan |
| selection | 枚举值（include/exclude/uncertain） | 该行跳过 |
| confidence | 枚举值（high/medium/low） | 默认 medium |
| exclusion_reason | selection=exclude 时非空 | 标记 no_reason，不影响 reading |

**额外传递给 reading 的信息**：
- include 且 confidence=high 的论文：reading 正常抽取
- include 且 confidence=low 的论文：reading 标记为 "limited_extraction"，key_finding 前缀加"基于有限信息"

---

## 合约 3：Reading → Survey

交接物：`evidence_table.csv`

| 字段 | 要求 | 不满足时的降级处理 |
|---|---|---|
| evidence_id | 非空、唯一 | 自动生成 |
| paper_uid | 非空、与 study_selection.csv 对应 | 标记 orphan |
| key_finding | 非空 | 该行不进入 survey 主论据 |
| data_source | 枚举值（abstract/web_supplemented/title_only/fulltext） | 默认 abstract |
| confidence | 枚举值（high/medium/low） | 默认 medium |

**额外传递给 survey 的信息**：
- confidence=high + data_source=abstract/fulltext → 可作为主论据
- confidence=medium → 可作为支撑证据
- confidence=low 或 data_source=title_only → 只能作为旁证，引用时必须加"基于有限信息"

**交接时输出**：
```
交接检查：evidence_table.csv
- 总证据：20 条
- 可作主论据：10 条（high confidence）
- 可作支撑：9 条（medium confidence）
- 仅作旁证：1 条（low confidence）
- survey 可用证据密度：充分 / 勉强 / 不足
```

---

## 合约 4：Survey → 输出层

交接物：`literature_review.md` 或其他文档型产出

| 字段/元信息 | 要求 | 不满足时的降级处理 |
|---|---|---|
| 文件存在 | 非空文件 | 阻塞（无内容无法输出） |
| 字数 | > 500 字 | 标记 too_short，风格适配时提醒"内容可能不够展开" |
| 引用数 | > 0 | 标记 no_citations，风格适配时不做引用格式处理 |
| scene（目标场景） | 由入口层或用户指定 | 默认 academic |
| mode（brief/full） | 由入口层或用户指定 | 默认 full |

---

## 怎么用

1. 每个 skill 完成后，入口层自动做一次交接检查
2. 检查结果以人话输出给用户（如上面的"交接检查"示例）
3. 降级项不阻塞流程，但会影响下游的处理策略
4. 如果降级项过多（如 >50% 缺 abstract），建议用户先补数据再继续

## 与 run_contract.py 的关系

- `run_contract.py` 检查的是"文件是否存在、目录结构是否对"（结构层）
- Handoff Schema 检查的是"文件内容是否满足下游需求"（数据层）
- 两者互补，不重复
