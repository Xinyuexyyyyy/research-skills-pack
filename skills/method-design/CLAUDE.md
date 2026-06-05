---
name: method-design
description: 方法设计 / methodology / 研究方法 / 实验方案 / 研究设计。触发词:方法设计、methodology、研究方法、实验方案、怎么做这个研究、design method、方法论、研究设计。
status: draft
---

# Method Design — 方法设计

## 一句话定位

基于已定题目和已有文献的方法脉络，设计一套能回答研究问题的具体方案。**只做方法方案与章节初稿，不替实验执行。**

## 上层契约

- 父级: `topic-framing`
- 进入条件: 已有合格 `topic_statement.md`
- 离开条件: 产出 `methodology.md` + `method_comparison.md`，并移交给 `experiment-runner` 或 `paper-composer`
- 共享输入: `evidence_table.csv`、可选 `literature_review.md`

## P0 边界

### 做什么
- ✅ 提取已有方法、变量、假设和评估方式
- ✅ 对比现有方法路线，找可复用、可改造、可创新部分
- ✅ 推荐一套主方法和备选方法
- ✅ 在用户确认后，写方法论章节初稿
- ✅ 如果需要，写实验/分析方案骨架

### 不做什么
- ❌ 重新选题
- ❌ 代替用户确认技术路线
- ❌ 真正跑实验或分析数据
- ❌ 直接写完整论文全文

## 输入要求

- 必须存在 `topic_statement.md`
- 若没有该文件，先回到 `topic-framing`
- 若有 `evidence_table.csv`，优先从中抽取方法信息
- 若缺少 `evidence_table.csv`，只做基于 topic 的方法框架草案，并提示补齐

## 工作流

### Step 1：提取已有方法
- 抽出研究设计、数据来源、变量、模型、验证方式
- 标注哪些方法是主流、哪些是变体、哪些是空白

### Step 2：方法对比
- 按研究问题匹配可用方法
- 区分直接可用、需要改造、需要新建三类
- 形成方法比较表

### Step 3：推荐方案
- 给出主方法 + 备选方案
- 说明为什么推荐、风险在哪里、代价是什么
- 明确哪些部分需要用户确认

### Step 4：用户确认
- 用户确认后冻结方法路线
- 若用户改方向，回到对比表重新评估

### Step 5：写章节
- 写 `methodology.md`
- 按需写 `experiment_design.md`
- 交接到 `experiment-runner` 或直接进入 `paper-composer`

## 产出文件列表

| 文件 | 说明 |
|---|---|
| `method_comparison.md` | 现有方法对比 + 推荐方案 |
| `methodology.md` | 方法论章节初稿 |
| `experiment_design.md` | 实验/分析方案骨架（适用时） |

## 上下游衔接

### 上游
- `topic-framing` 完成后进入
- 衔接提示: "方法论章节可以开始设计了。下一步可以说'设计方法'或'方法论'"

### 下游
- `experiment-runner`
- `paper-composer`
- 衔接提示: "方法论章节完成。下一步：如果有实验/分析要做，先做实验；如果是纯综述型，可以直接组装论文。"

## 自检清单

- [ ] `topic_statement.md` 是否存在？
- [ ] 是否提取了已有方法并做对比？
- [ ] 是否给出主方法和备选方案？
- [ ] 是否标出需要用户确认的点？
- [ ] 方法章节是否能直接接到论文写作？
- [ ] 输出是否能移交给后续实验或写作环节？
