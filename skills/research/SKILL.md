---
name: research
description: 当用户明确要做调研、研究、综述、竞品分析、产品发现或综合决策备忘时使用。它是唯一对外暴露的调研总入口，负责先路由再进入对应模板包；不替用户硬猜方向，也不在信息需求很弱时滥触发。
status: draft
---

# Research

## 一句话定位

这是调研体系的唯一总入口。先判断用户到底要哪一类调研，再把问题送进对应模板包，而不是用一个万能 prompt 糊所有问题。

这一层真正负责的是 5 件事:
- 判断这题值不值得进正式调研
- 先把研究问题缩到能回答
- 在 4 个模板包里做单一路由
- 固定 3 个用户可见检查点
- 确保最后交的是“结果包”,不是一段临时分析

## 先看什么

1. 先看本文件，确认 `research` 什么时候该用
2. 再看 [README.md](README.md)，看整体结构、产物和代价地图
3. 只有在改协议时，再去看 `base/hooks.md` 和 `base/scoring.md`

## 什么时候用

- 用户明确说“调研”“研究”“综述”“文献综述”“systematic review”
- 用户要做竞品分析、价格带、battle card、替代方案判断
- 用户要做产品发现、MVP wedge、PRD outline、方向验证
- 用户面对一个开放问题，需要外部信息才能回答
- 用户要做跨多类证据的综合决策备忘

## 不什么时候用

- 用户只是问名词解释、概念、定义
- 用户只是要写文案、起标题、改措辞
- 用户已经明确该走某个下游 skill，而且不需要总入口再分流
- 用户的问题主要是执行型代码任务，而不是信息收集和判断

## 进入前先判断

进入 `research` 前必须先做一次轻判断:

| 情况 | 处理 |
|---|---|
| 明确要正式调研，且需要外部证据 | 直接进入 `research` |
| 题目太大、太散、研究问题不清 | 先问 1 到 2 个缩边界问题，再进入 |
| 用户只想快速了解 | 降级成轻量概览，不跑完整调研链 |
| 只是概念解释或写作润色 | 不进入 `research` |

如果连“要回答什么问题”都说不出来，就不能直接开跑。

## 默认工作方式

不要一上来就把所有文档倒给用户。先判断问题类型，再按 route 进入一个模板包。

## 主流程

```text
Step 0: Gate       -> 判断要不要进正式调研
Step 1: Clarify    -> 缩边界，确认研究问题、范围、非目标
Step 2: Route      -> academic / competitive / discovery / comprehensive 四选一
Step 3: Retrieve   -> 按 route 取证并留 source log
Step 4: Screen     -> 去噪、筛证据、标强弱
Step 5: Synthesize -> 产出 route-specific 结果包和主报告
Step 6: Review     -> 做复核、标争议、决定正式结论还是保守结论
```

## 用户可见检查点

### 检查点 1：先确认研究问题

如果题目太大、太散，先给用户看你理解的研究问题和范围，再继续检索。

最少要说清：
- 这轮要回答什么问题
- 不回答什么
- 时间范围或对象范围是什么

### 检查点 2：路由后先确认调研类型

先告诉用户准备走哪条路：
- `research-academic`
- `research-competitive`
- `research-discovery`
- `research-comprehensive`

如果用户不同意，先确认 override，再继续。

### 检查点 3：证据冲突或信息不足时先停

在综合结论前，先告诉用户：
- 证据是否冲突
- 当前能不能下结论
- 是继续补证据，还是先输出保守结论

不要把“证据还不够”包装成确定答案。

## 最小交付规则

只要进入正式调研，就至少要交 4 类东西:

1. `research-question`
   说明这轮到底回答什么、范围是什么、非目标是什么。
2. `routing-decision`
   说明为什么走这个包，而不是另一个包。
3. `source-log`
   说明证据从哪里来，哪怕这轮最后结论偏保守。
4. `final-report`
   给人直接看的主报告；名字可因包而异，但必须有稳定入口。

如果连这 4 类东西都没有，这轮只能叫“临时分析”，不能叫正式调研包。

## Action

### `research-academic`

- 适用：论文、arXiv、文献综述、systematic review
- 产物：`literature_review`、`reader_guide`、`research_gaps`

### `research-competitive`

- 适用：竞品、市场格局、价格带、battle card、替代方案
- 产物：`feature_matrix`、`pricing_landscape`、`battle_cards`、`reader_brief`

### `research-discovery`

- 适用：idea、MVP、PRD、用户痛点、方向验证
- 产物：`discovery_report`、`mvp_wedge`、`prd_outline`、`reader_brief`

### `research-comprehensive`

- 适用：跨多类证据、决策备忘、tradeoff、fallback
- 产物：`decision_memo`、`tradeoff_brief`、`reader_brief`

## 路由规则

| 命中 | 调度 |
|---|---|
| 学术 / 论文 / arxiv / 文献综述 | `research-academic` |
| 竞品 / 价格 / battle card / GTM | `research-competitive` |
| idea / MVP / PRD / 产品发现 | `research-discovery` |
| 跨多类 / 决策级 / 不命中以上 | `research-comprehensive` |

补充判断:
- 明确“找论文 / 文献综述 / arXiv / systematic review”优先走 `academic`
- 明确“竞品 / 市场格局 / 定价 / 用户评价”优先走 `competitive`
- 明确“想法收敛 / PRD / MVP / 痛点验证”优先走 `discovery`
- 同时命中两类以上，或核心问题是“值不值得做 / 怎么选”，优先走 `comprehensive`

## 边界条件

### 情况 1：用户意图太模糊

**条件**：既没说明调研类型，也没说明想回答什么问题。
**处理**：先问 1 到 2 个缩边界问题，不直接走 fallback 灌水。
**对用户怎么说**：我可以帮你调研，但得先知道你是想看论文、竞品、产品方向，还是做综合判断。

### 情况 2：路由命中不稳

**条件**：一个问题同时命中多个模板包。
**处理**：先说明当前推荐路线和备选路线，等用户确认后再继续。
**对用户怎么说**：这题既像竞品，也像产品发现。我建议先走 X；如果你更关心 Y，我们可以改路。

### 情况 3：检索无结果或工具失败

**条件**：外部检索为空、超时或取证渠道失败。
**处理**：先重试或换渠道；仍失败就停在当前层，明确标注“检索未完成”。
**对用户怎么说**：这轮证据还不够，我先不给硬结论，先把已拿到的部分整理给你。

### 情况 4：证据冲突或质量不够

**条件**：同一问题下多源结论矛盾，或所有证据都偏弱。
**处理**：保留冲突和不确定性，不替用户强行拍板。
**对用户怎么说**：现在能看到两种相反说法，我可以先给你争议地图，但不建议把它写成确定结论。

### 情况 5：用户只想快速了解，不要重调研

**条件**：用户只要一个轻量概览，不值得跑完整调研链。
**处理**：降级成轻量摘要，明确说明这不是完整研究包。
**对用户怎么说**：这轮更适合先给你一个轻量概览，不必直接上完整调研包。

## Tool 依赖

- `README.md`：总览
- `base/`：默认 6 段管线、原子工具、router、hooks、scoring
- `packages/`：academic / competitive / discovery / comprehensive
- 结果包目录：`./research/{run_dir}/`
- 主报告副本：`$CONTENT_DIR/search_report/{run_dir}.md`

## 最小验收

手工验收时至少确认 6 件事：

1. `README.md` 能讲清楚总入口、共享层和模板包分工
2. `base/router.md` 的 4 类路由和本文件一致
3. 当前问题先能判断“该不该进正式调研”，而不是逢问题就开跑
4. 任取一个真实问题，能清楚判断为 academic / competitive / discovery / comprehensive 之一
5. 任一路由都能说清至少一个稳定主报告名和一组必出中间产物
6. 当证据不足时，体系会停在“保守结论”而不是硬给确定答案

如果这 6 件事做不到，就说明这个总入口还不够像“默认工作流”。
