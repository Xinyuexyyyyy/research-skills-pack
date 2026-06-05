---
name: research-comprehensive
description: 综合类调研模板包(主 skill 的 fallback)。用于跨多类型 / 决策导向 / 不命中其他特定包的开放问题。围绕"决策问题"组织,产出 decision_memo + evidence_matrix + tradeoff_brief。基于 research-base 主 skill,可子调用其他模板包补片段。触发词:值不值得做、要不要做、怎么选、X 方向调研、调研一下 X、决策、tradeoff、决策备忘、deep research、deep dive、综合调研。
status: draft
---

# Research Comprehensive — 综合类 / 兜底模板包

## 一句话定位

**任何调研需求,不命中专门类型时都走这里**。围绕"决策问题"展开,核心产物不是一篇散文式分析,而是一套**可交付的决策包**:切片计划、证据矩阵、tradeoff、风险与面向非专业读者的导读。

这一包真正负责的是 4 件事:
- 把开放问题收成一句可回答的 `decision_question`
- 把候选选项讲清，而不是只给模糊建议
- 把多源证据装配成一个可复核的决策包
- 在证据不够时，明确降级成 `decision_note`，而不是硬装成正式结论

默认读者不假设是内部研究员。除非用户明确要纯专业版,本包应同时产出:
- 一份给决策者/专业读者的 `decision_memo.md`
- 一份给非专业读者或跨职能读者的 `reader_brief.md`

## 你到底该看哪几个文件

### 只想判断这个包有没有“决策报告味”

1. `SKILL.md` — 看这个包到底解决哪类问题
2. `report-template.md` — 看它是不是在逼“决策包”而不是散文
3. `hooks.md` — 看切片、证据、反向论证有没有被硬性要求

### 其他文件是什么定位

- `channels.md`: 子调用和多渠道取证协议,偏维护者
- `routing.md`: 何时 fallback 到这里,偏维护者

如果你只是审输出深度,先别被 `channels.md` 吸走注意力。

## 你能从这个包里真正收获什么

读完应该带走 4 个判断:
- 综合调研不是“多写一点”,而是围绕决策问题组织证据
- 证据必须显式支持 / 反对某个选项
- 决策报告必须同时写推荐理由和反对理由
- 小白版导读不能只是正文压缩

## 触发条件

### 高优先级(强命中)
- "X 值不值得做""要不要做 Y""Z 方向怎么样"
- "深入调研 X""对 X 做一次综合调研"
- "deep research""deep dive"
- 用户给出**多类混合**问题(学术 + 市场 + 用户痛点)

### 中优先级(fallback 入口)
- 任何调研需求,但不命中 academic / competitive / discovery
- router 不确定时

### 不触发
- 明确单一类型(学术 → academic;竞品 → competitive;产品发现 → discovery)
- 仅询问名词概念

## 进入前先判断

进入本包前，至少先判断 3 件事:

| 问题 | 处理 |
|---|---|
| 用户到底要决定什么 | 先收成一句 `decision_question` |
| 至少有哪几个候选选项 | 没给就先补 `做 / 不做 / 推迟` |
| 这题是不是单一专门问题 | 如果是，应该让位给对应专门包 |

如果这 3 件事说不清，本包不能直接进入正式综合调研。

## 用户可见检查点

### 检查点 1：先确认决策问题

最少要确认:
- 这次到底在决定什么
- 不决定什么
- 时间窗是什么
- 谁是拍板人或主要读者

### 检查点 2：先确认候选选项

不要直接对着空气写建议。至少要把候选选项列出来，让用户看到这次到底在比什么。

### 检查点 3：证据不够时先降级

如果核心选项证据覆盖不够，或者强冲突没处理掉，就应降级为 `decision_note` 或 `needs_human_review`，不要继续包装成正式 `decision_memo`。

## 钩子覆盖

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ | 加 decision_question / stakeholders / horizon / audience_profile 到 custom |
| `hook_retrieve` | ✅ | 多渠道并行 + **可子调用其他包** |
| `hook_screen` | ✅ | 按"是否能影响决策"过滤,不只是相关性 |
| `hook_extract` | ✅ | 每条 evidence 必带 `relates_to_decision_question` |
| `hook_synthesize` | ✅ | 先出 decision_canvas / scorecard,再写 memo + reader brief |
| `hook_review` | ✅ | 强制 conflict_log + 反向论证 + explainability 检查 |

详见 `hooks.md`。

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口(本文件) |
| `routing.md` | fallback 边界 + 与其他包的协作约定 |
| `channels.md` | 多渠道策略 + 子调用其他包的协议 |
| `report-template.md` | 决策包骨架(中间产物 + 决策正文 + 小白导读) |
| `hooks.md` | 钩子覆盖详情 |

一句话记忆:
- `SKILL.md` 看“边界”
- `report-template.md` 看“报告味”
- `hooks.md` 看“有没有硬约束”

## 固定产物层级

### A. 决策 framing 层(必出)
- `decision_question.md`
- `option_set.md`
- `slice_plan.md`
- `source_log.csv`

### B. 分析层(必出)
- `evidence_matrix.csv`
- `decision_scorecard.csv`
- `tradeoff_brief.md`
- `conflict_log.md`

### C. 交付层(必出)
- `decision_memo.md`
- `reader_brief.md`

### D. 稳定入口(至少一个)
- `final_report.md`，或
- 明确以 `decision_memo.md` 作为默认主报告入口

如果只有 `decision_memo.md`,而没有 A/B 层留痕,那更像一篇意见文,不是合格的综合调研包。

## 最小交付规则

只要进入正式综合调研，至少要交出下面 5 类东西:

1. `decision_question.md`
2. `option_set.md`
3. `source_log.csv`
4. `decision_scorecard.csv`
5. `final_report.md` 或 `decision_memo.md`

缺任一项，就不应宣称这轮已经形成正式决策包。

## adequacy gate

本包在 `hook_review` 里增加一层门槛:

- 每个候选选项都必须有最低证据覆盖
- 推荐选项必须有可解释的正反依据
- 非专业读者版导读必须存在(除非用户明确只要 expert)

否则:
- 结果只能降级为 `decision_note`
- 不能叫正式 `decision_memo`

## 推荐阅读顺序

如果是人在审这一包，优先看：
1. `SKILL.md`
2. `report-template.md`
3. `hooks.md`

读完这 3 个文件，应该能回答：
- 什么题该进本包
- 这包最少交什么
- 什么情况下必须降级

## 抄了哪些成熟方案

| 来源 | 抄什么 |
|---|---|
| `assafelovic/gpt-researcher` | 多源并行 + agent + report aggregation |
| `langchain-ai/open_deep_research` | planning → searching → writing 三段、子图协作 |
| Amazon "6-pager" / "PR-FAQ" 风格 | decision memo 骨架 |
| 通用 Pros/Cons + 反向论证(red team) | tradeoff_brief 写法 |

## 对其他包的协作姿态

- 综合类**不重新做学术 / 竞品 / 发现的"专精活儿"**,而是按需子调用对应包,把回来的片段融合进决策备忘
- 子调用契约见 `channels.md` § "跨包子调用"
- 综合类独占 hook_synthesize / hook_review,即使子调用了其他包,最终装配也由本包负责

## 给主 skill 的反向约束

- 综合类需要"跨包子调用"协议;V1 已在本包 `channels.md` 先落地
- 主 skill 目前在 `router.md` / `hooks.md` 只做边界说明,还没把该协议上收成共享强约束
- 若后续主 skill 要正式吸收,以本文件和 `channels.md` 的 V1 协议为基础升版

## 最小验收

手工验收时至少确认 5 件事:

1. 一个“值不值得做”的真实问题，能被收成一句清楚的 `decision_question`
2. 候选选项不是隐含的，而是被显式列在 `option_set.md`
3. `decision_memo.md` 之外，至少还能看到 `source_log.csv` 和 `decision_scorecard.csv`
4. 证据不够时，会明确降级成 `decision_note` 或 `needs_human_review`
5. 若题目其实是单一学术 / 竞品 / 发现问题，本包会让位，不会把所有问题都吃进来
