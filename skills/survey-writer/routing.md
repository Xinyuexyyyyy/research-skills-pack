# Survey Writer — 命中条件 + 让位边界

## 命中条件

### 高优先级（必须触发）
- "写综述""写文献综述""做个 survey"
- "写 related work""相关工作怎么写"
- "研究空白是什么""gaps""还有什么没做"
- "未来方向""future work"
- 用户已有 `evidence_table.csv`，要求"基于这些论文写点什么"

### 中优先级（结合上下文）
- "这些论文说明了什么"
- "帮我总结一下这些研究"
- "这些方法有什么异同"

### 不触发
- 没有 `evidence_table.csv`，也没有提到综述
- 仅要求整理文件/目录（那是通用任务，不是综述写作）
- 仅要求翻译（translation，不是 synthesis）

## 综述类型识别

命中后，按以下顺序判断类型：

1. **literature_review** — 命中任一：
   - "文献综述""survey""systematic review"
   - 没有指定具体章节
2. **related_work** — 命中任一：
   - "related work""相关工作"
   - "放在论文里"
3. **research_gaps** — 命中任一：
   - "研究空白""gaps""还有什么没做"
   - "局限""不足"
4. **future_work** — 命中任一：
   - "未来方向""future work""下一步"
   - "建议"
5. **未指定** — 反问："你想写哪种类型的综述？文献综述 / 相关工作 / 研究空白 / 未来方向"

## 让位条件

| 情形 | 让位给 |
|---|---|
| 没有 `evidence_table.csv` | 先让用户去 `paper-reading` 完成抽取 |
| `evidence_table.csv` 为空或只有 low 置信度 | 提示"证据不足，建议先去 paper-discovery + paper-screening" |
| 用户要"找更多论文来充实综述" | 导回 `paper-discovery` |
| 用户要"重新筛选一下论文" | 导回 `paper-screening` |

## 与上游 paper-reading 的边界

- survey-writer **不读取** `pending_fulltext.csv` 中的论文
- survey-writer **不修改** `evidence_table.csv` 中的任何数据
- survey-writer 只读取 `extraction_confidence` 和 `qualitative_only` 做标注，不改值
