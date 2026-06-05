# Survey Writer — 产物 Schema

## 本 skill 写入的产物

| 产物 | 格式 | 必出 | 说明 |
|---|---|---|---|
| `<review_type>.md` | Markdown | 是 | 主综述文本 |
| `citation_table.csv` | CSV | full 必出 / brief 推荐 | 引用清单 |
| `review_audit.md` | Markdown | full 必出 / brief 推荐 | 审计记录 |
| `method_comparison_table.csv` | CSV | 条件 | 方法对比表（如综述中包含对比） |

## 按模式的完成要求

| 模式 | 必须满足 |
|---|---|
| `brief` | 1 篇主综述 + 只消费 `evidence_table.csv` + 低置信/定性证据有标识 |
| `full` | 主综述 + `citation_table.csv` + `review_audit.md` + gap 可回链到 evidence |
| `direct` | 至少交付主综述；若用户未要求“只看文稿”，默认补齐 full 的审计产物 |

## citation_table.csv

记录每条引用在综述中的使用情况。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `paper_uid` | string | 是 | 论文唯一标识 |
| `first_appearance` | string | 是 | 首次出现位置（章节标题） |
| `appearances` | int | 是 | 总出现次数 |
| `contexts` | string | 是 | 出现语境，逗号分隔：introduction/methods/comparison/gaps |
| `confidence` | enum | 是 | evidence_table 中的 extraction_confidence |
| `qualitative_only` | bool | 是 | evidence_table 中的 qualitative_only |

## review_audit.md

审计综述的覆盖度和质量。

```markdown
# 综述审计

## 统计概览
- **综述类型**：
- **总字数**：
- **引用论文数**：
- **高置信度引用**：
- **中置信度引用**：
- **低置信度引用**：（标注位置）
- **qualitative_only 引用**：（标注位置）

## 主题覆盖
| 主题 | 覆盖论文数 | 占比 |
|---|---|---|
| | | |

## 时间分布
| 年份段 | 论文数 | 占比 |
|---|---|---|
| | | |

## 质量标注
- [ ] 存在低置信度引用用于核心论点
- [ ] 存在 qualitative_only 引用当作定量证据
- [ ] 存在 pending_fulltext 论文被引用
```

## method_comparison_table.csv

方法对比表（如综述中包含）。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `method_name` | string | 是 | 方法名称 |
| `paper_uid` | string | 是 | 来源论文 |
| `core_idea` | string | 是 | 核心思路（一句话） |
| `data_scenario` | string | 是 | 数据/场景 |
| `key_result` | string | 是 | 关键结果（带数值） |
| `limitation` | string | 是 | 作者自陈的局限 |
| `applicability` | string | 否 | 适用场景 |
