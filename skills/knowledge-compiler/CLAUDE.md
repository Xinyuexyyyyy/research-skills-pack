---
name: knowledge-compiler
description: 多源知识聚合 / knowledge compile / 整理成知识包 / 聚合证据。把多篇论文证据、实验笔记、研究日志、代码结果和对话 claims 编译成有层级、有链接、有证据溯源的结构化 knowledge-pack。触发词：编译知识、knowledge compile、整理成知识包、聚合证据、compile、把这些论文整理一下。
status: stable
commands: [编译知识, knowledge compile, 整理成知识包, 聚合证据, compile, 把这些论文整理一下]
---

# Knowledge Compiler — 多源知识聚合

## 定位

把多源研究输入编译成结构化知识包，让 claims 之间有链接、有层级、有证据溯源。它取 ARA 的核心思想，但不照搬完整 schema，只产出轻量、可遍历、可继续写作和审查的 `knowledge-pack/`。

## 与 paper-reading / survey-writer / rigor-reviewer 的边界

### 做什么
- 聚合多篇论文、实验笔记、代码结果和对话中的 claims
- 抽取 concepts、claims、heuristics 和 evidence source
- 建立 claim 之间的支持、矛盾、前提关系
- 标注置信度和证据来源，保留可追溯链路
- 产出可供 `survey-writer` 或 `rigor-reviewer` 使用的知识包

### 不做什么
- 不做单篇论文阅读；那是 `paper-reading` 的事
- 不重新抽取 PDF 全文证据；缺证据时回到上游补
- 不写综述正文；那是 `survey-writer` 的事
- 不做认识论审查；那是 `rigor-reviewer` 的事
- 不采用完整 ARA schema，不生成重型知识库工程

## 上下游关系

- 上游: `paper-reading` 的 `evidence_table.csv`
- 上游: 实验笔记、研究日志、代码仓库 README / 结果文件
- 上游: 对话中产生的 claims、heuristics、探索树记录
- 下游: `rigor-reviewer` 可审查知识包的逻辑和证据强度
- 下游: `survey-writer` 可从知识包生成综述、related work 或 gap
- 平级: `closeout` 研究模式记录单次会话；本 skill 聚合多次会话和多源材料

## 输入类型

| 输入 | 用途 | 处理方式 |
|---|---|---|
| `evidence_table.csv` | 论文证据主表 | 抽取 paper_uid、contribution、method、finding、confidence |
| 实验笔记 / 研究日志 | 记录尝试、失败、结果和观察 | 抽取 experiment claim、dead end、heuristic |
| 代码仓库 README | 记录方法、接口、复现条件 | 抽取 system claim、implementation note |
| 结果文件 | 记录指标、图表、ablation | 抽取 empirical claim 和 evidence |
| 对话 claims / heuristics | 记录本轮推理和经验法则 | 标注 provenance 为 conversation |
| 任意 markdown 材料 | 研究备忘、草稿、分析 | 抽取 claim / concept / evidence block |

## 产出结构

```text
knowledge-pack/
  README.md                 # 知识包入口：范围、输入、如何遍历
  claims.yml                # claim 节点、置信度、证据和关联
  concepts.yml              # 概念词表、定义、别名、层级
  evidence_sources.yml      # 论文、实验、代码、对话等来源索引
  relations.yml             # claim 间 support / contradict / prerequisite
  heuristics.md             # 经验法则、适用条件、反例
  open_questions.md         # 未解决问题、低置信 claim、待补证据
```

## claim 格式

每个 claim 必须是一句话断言，并能追溯到证据来源。

```yaml
- id: C001
  claim: 一句话断言内容
  confidence: high|medium|low
  evidence:
    - source_id: paper:smith2024
      locator: evidence_table.csv:paper_uid=...
      note: 证据如何支持该断言
  related_claims:
    supports: [C002]
    contradicts: [C003]
    prerequisites: [C004]
```

## 置信度与关系规则

- `high`: 多个来源支持，或单个高质量来源直接给出强证据
- `medium`: 有明确来源支持，但证据范围有限或只来自单一材料
- `low`: 来源间接、证据不足、来自对话推断，或需要后续核实
- `supports`: A 为 B 提供证据、机制或例子
- `contradicts`: A 与 B 的结论、范围或条件冲突
- `prerequisites`: A 是理解或成立 B 的前提
- 低置信 claim 不删除，放入 `open_questions.md`，关系必须尽量指向 claim id。

## 流程

### Step 1：收集输入
- 接收材料路径或文本，列出类型、来源、时间和可信度线索；缺材料时先产出待补清单。

### Step 2：提取 claims / concepts / heuristics
- 提取一句话 claim、关键 concepts、别名、上下位关系和可复用 heuristic。

### Step 3：建立关联
- 合并重复 claim，保留来源列表，标注 supports / contradicts / prerequisites。

### Step 4：标注置信度和证据来源
- 为每个 claim 标注 high / medium / low，并区分论文证据、实验结果、代码结果、对话推断。

### Step 5：产出 knowledge-pack/
- 写出目录结构文件，在 `README.md` 说明输入材料、生成日期、遍历方式和下游入口。

## 产出格式

```markdown
## Knowledge Compile

### 输入材料
| source_id | type | path / locator | note |
|---|---|---|---|

### 产出目录
`knowledge-pack/`

### 摘要
- claims: N
- concepts: N
- relations: N
- low-confidence claims: N

### 下一步
- 逻辑审查: `rigor-reviewer`
- 综述写作: `survey-writer`
```

## 自检清单

- [ ] 是否聚合了多源材料，而不是重做单篇阅读？
- [ ] 每个 claim 是否是一句话断言？
- [ ] 每个 claim 是否有证据来源或待核实标记？
- [ ] 是否建立 supports / contradicts / prerequisites 关系？
- [ ] 是否区分 high / medium / low 置信度？
- [ ] 是否产出轻量 `knowledge-pack/`，而不是完整 ARA schema？
