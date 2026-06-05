# Survey Writer — 读图

## 这个 skill 在哪

```
research-base（共享层）
    ↓
research-academic（学术路由器）
    ↓
paper-reading（证据抽取）→ evidence_table.csv
    ↓
[survey-writer] ← 你在这里
```

## 改动代价地图

| 改动 | 影响范围 | 代价 |
|---|---|---|
| 新增综述类型 | 本 skill + research-academic/routing.md | 低 |
| 修改引用格式 | 本 skill 的 report-template.md | 低 |
| 修改章节结构 | 本 skill 的 report-template.md | 低 |
| 修改对比维度 | 本 skill 的 artifacts.md（method_comparison_table） | 中 |
| 要求消费 comparison_matrix.csv | paper-reading + 本 skill | 中（需要上游产出） |

## 和谁通信

- **上游**：`paper-reading` 产出的 `evidence_table.csv`
- **下游**：用户直接消费综述文本，无进一步下游 skill（P2 可能有 `academic-deep-research` 引用）

## 一句话

把结构化证据变成人话综述。核心是"怎么组织"而不是"写什么内容"——内容来自 evidence_table，组织方式由综述类型决定。

## 依赖说明

### 必需依赖

1. **evidence_table.csv**
   - 来源：`paper-reading` skill 的输出
   - 位置：通常在 `<workspace>/runs/{date}_{topic}/02-reading/evidence_table.csv`
   - 说明：包含论文的结构化证据（方法、结论、贡献等）
   - Schema 定义：参考 `research-base/artifacts.md`

2. **research-base/artifacts.md**
   - 来源：共享 schema 定义文件
   - 位置：`research-base` skill 中
   - 说明：定义 `evidence_table.csv` 的字段规范

### 可选依赖

1. **pending_fulltext.csv**
   - 来源：`paper-reading` skill
   - 说明：待处理论文清单（本 skill 不会引用其中内容）

### 获取依赖

如果缺少 `evidence_table.csv`，需要先执行：
1. 使用 `paper-discovery` 检索相关论文
2. 使用 `paper-screening` 筛选论文
3. 使用 `paper-reading` 提取证据

或直接通过 `research-academic` 路由器启动完整调研流程。
