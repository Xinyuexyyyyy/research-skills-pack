---
name: rigor-reviewer
description: 投稿前自审 / 逻辑审查 / 认识论审查 / rigor review。对论文初稿、综述文本、研究笔记做 6 维研究严谨性审查，找证据、scope、方法和论证漏洞。触发词：自审、rigor review、帮我审一下、投稿前检查、逻辑审查、认识论审查。
status: stable
commands: [自审, rigor review, 帮我审一下, 投稿前检查, 逻辑审查, 认识论审查]
---

# Rigor Reviewer — 投稿前自审

## 定位

对论文初稿、综述文本、研究笔记做认识论审查，找 claim、证据、方法和结论之间的逻辑漏洞。它面向投稿前或交导师前的自审，目标是发现“研究是否站得住”，不是把文本改得更漂亮。

## 与其他 skill 的边界

### 做什么
- 审查证据是否真的支撑 claim
- 审查结论是否可验证、可反驳
- 审查 scope 是否过度泛化
- 审查问题、方法、结果、结论之间的逻辑链
- 审查失败、局限、替代解释是否被诚实记录
- 审查实验设计、baseline、ablation 和报告是否足够严谨

### 不做什么
- 不查排版、拼写、语法润色
- 不查引用格式、BibTeX 格式、期刊模板
- 不替代 `output-style-checker`
- 不替代 `paper-composer` 或 `survey-writer` 写正文
- 不重新做实验、统计分析或文献检索

## 上下游关系

- 上游: `paper-composer` 完成论文初稿后调用
- 上游: `survey-writer` 完成综述文本后调用
- 输入: markdown / LaTeX 文本、论文草稿、综述、研究笔记
- 输出: 6 维评分表、逐维分析、总评、改进建议清单
- 不依赖 ARA schema，直接审查文本本身

## 6 维评审框架

每个维度给 1-5 分，并附 `strengths / weaknesses / suggestions`。

| 维度 | 评审问题 |
|---|---|
| D1 证据相关性 | 引用、数据、案例是否真的支持对应 claim？ |
| D2 可证伪性 | 核心结论是否可以被验证、反驳或复现？ |
| D3 Scope 校准 | claim 是否说得比证据支持的范围更大？ |
| D4 论证连贯性 | 问题、方法、结果、讨论、结论是否形成通顺链条？ |
| D5 探索完整性 | 是否诚实记录失败、局限、替代方案和负结果？ |
| D6 方法论严谨性 | 是否有合理 baseline、ablation、控制变量和结果报告？ |

## 评分标准

| 分数 | 含义 |
|---|---|
| 5 | 严谨，主要 claim 有直接证据支撑，风险很低 |
| 4 | 基本可靠，有少量需要补充或澄清的地方 |
| 3 | 可用但有明显薄弱点，投稿前应修补 |
| 2 | 存在关键漏洞，可能影响主结论可信度 |
| 1 | 严重不足，claim 与证据或方法明显脱节 |

总评级必须从以下选项中选择一个：Strong Accept / Accept / Weak Accept / Borderline / Weak Reject / Reject。

## 流程

### Step 1：确定审查对象
- 确认文本类型: 论文初稿、综述、研究笔记或章节片段
- 确认用户目标: 投稿前自审、导师前预审、修改前诊断

### Step 2：抽取核心 claim
- 列出 3-8 条最重要的研究 claim
- 标出每条 claim 所在章节和依赖的证据
- 文本太长时，优先审查摘要、引言、方法、结果、讨论和结论

### Step 3：逐维评分
- 对 D1-D6 分别给 1-5 分
- 每维必须写 strengths、weaknesses、suggestions
- 尽量指向具体段落、句子、表格或实验设置

### Step 4：给出总评与建议
- 给出总评级和 3-5 句依据
- 明确最影响投稿风险的 1-3 个问题
- 按 Must fix / Should fix / Optional 输出改进建议

## 产出格式

```markdown
## Rigor Review

### 6 维评分表
| 维度 | 分数 | 核心判断 |
|---|---:|---|

### 逐维度分析
#### D1 证据相关性
- Strengths:
- Weaknesses:
- Suggestions:

### 总评
- Rating:
- Rationale:
- Highest-risk issues:

### 改进建议清单
- Must fix:
- Should fix:
- Optional:
```

## 自检清单

- [ ] 是否只审查研究严谨性，而不是格式和语言？
- [ ] 是否覆盖 D1-D6 六个维度？
- [ ] 每个维度是否都有分数、strengths、weaknesses、suggestions？
- [ ] 总评级是否与六维评分一致？
- [ ] 改进建议是否具体到可执行动作？
