# Research Base — 整体读图

## 这是干什么的

把"调研"这件事**拆成共享的工具层 + 不同类型的模板包**:
- 主 skill(`research-base`,本目录)= 工具 + 流程 + 评分,大家共用
- 子模板包(平行)= 不同调研类型的"分析角度 + prompt + 报告模板"

不再用一个万能 prompt 处理所有调研。

## 推荐阅读顺序

1. `README.md` — 先看整体结构、职责边界、哪些文件改动代价最大
2. `SKILL.md` — 再看触发条件、默认行为、路由关系
3. `atoms.md` / `pipeline.md` — 需要理解共享层怎么跑时再看
4. `hooks.md` / `scoring.md` — 这是最高代价的接口层,改之前先审
5. `references/sources.md` — 想核对"抄了哪儿"时再看

## 用户能看到什么

| 你说 | 系统做什么 |
|---|---|
| "帮我调研一下 RAG 的最新进展" | router 命中 `research-academic` → 跑学术综述管线 → 输出综述 + 证据表 + 研究空白 |
| "看看 Notion 的竞品都有谁" | router 命中 `research-competitive` → 跑竞品情报管线 → 输出竞品矩阵 + 价格表 + 战卡 |
| "我有个想法,想做 X,你帮我挖挖" | router 命中 `research-discovery` → 跑产品发现管线 → 输出 idea brief + MVP wedge + PRD 草稿 |
| "AI Code 这个方向值不值得做" | 多类型混合 → fallback `research-comprehensive` → 跑决策级综合管线 → 输出 decision memo + tradeoff brief |

## 整体结构

```
                   用户输入
                      ↓
          ┌──────────────────────────┐
          │  research-base (主 skill)  │
          │   ├─ router 自动判断类型     │
          │   ├─ 默认 6 段管线           │
          │   ├─ 原子工具集              │
          │   └─ 10 维评分引擎           │
          └─────┬─────────┬─────────┬─┘
                ↓         ↓         ↓
        research-academic  research-competitive  research-discovery  research-comprehensive
            (学术综述)        (竞品市场)         (产品发现)        (综合类 / fallback)
```

子模板包**只覆盖默认管线中需要变的部分**(称为"钩子覆盖"),不重写整套流程。

## 一次调研怎么跑

以"调研 RAG 最新进展"为例:

1. **澄清**(clarify):问用户范围是 22-26 年还是更早?focus 在 evaluation 还是 method?
2. **检索**(retrieve):学术包覆盖此段 → 走 arXiv / Semantic Scholar / ACL Anthology
3. **筛选**(screen):学术包用 PICO + active learning 做纳排
4. **提取**(extract):每篇论文抽 method / dataset / metric / claim 到 `evidence_record`
5. **综合**(synthesize):学术包用"主题分组 + 时间线 + research gaps"
6. **复核**(review):评分引擎给每条结论打 10 维分,Tier 3 的回到人工

每段都是钩子,子包没覆盖就用默认行为(主 skill 提供)。

## 文件清单

```
research-base/
├── SKILL.md         入口,Claude 看这里决定调不调 skill
├── README.md        本文件,整体读图
├── pipeline.md      默认 6 段管线规格 + 钩子点位置
├── atoms.md         原子工具签名(共享给所有子包用)
├── router.md        自动路由规则细则
├── hooks.md         子包覆盖钩子的接口契约
├── scoring.md       10 维评分 + 4 Tier 决策路由
└── references/      外部参考材料(claude-scholar / MetaScreener 摘录)
```

## 改动代价地图

子模板包作者最需要先知道的是:哪些地方能随便改,哪些地方一改就会带崩所有包。

| 代价 | 文件 | 为什么 |
|---|---|---|
| 低 | `README.md`, `references/sources.md` | 只改说明文字,不影响任何接口 |
| 中 | `router.md`, `pipeline.md`, `atoms.md` | 会影响默认行为和路由,但子包通常不用逐个重写 |
| 高 | `hooks.md` | 一改输入输出 schema,所有子包 hook 都要跟着升版 |
| 高 | `scoring.md` | 一改维度或 Tier 规则,所有 evidence_record 的解释和复核门槛都会变 |
| 最高 | `hooks.md` + `scoring.md` 同时改 | 等于把"共享层契约"整体换掉,必须联动验证所有子包 |

一句话记忆:
- 子模板包平时主要改自己的 `routing.md` / `channels.md` / `report-template.md`
- 主 skill 里最不该轻易碰的是 `hooks.md` 和 `scoring.md`

## 怎么加新模板包

1. 在 `./skills/` 下新建 `research-{type}/`,加 `SKILL.md` 含触发词
2. 写 `routing.md`(命中条件)、`channels.md`(检索渠道)、`report-template.md`(报告骨架)
3. 按需在 `hooks.md` 里覆盖部分钩子(没覆盖就用默认)
4. 在主 skill `router.md` 里登记触发关键词

不需要复制工具层、评分引擎或默认管线 — 主 skill 已经给了。

## 抄了哪些成熟方案

| 来源 | 抄什么 |
|---|---|
| `Galaxy-Dawn/claude-scholar` | skills + agents + commands 分工法、6 段流程语义、Progressive disclosure |
| `ChaokunHong/MetaScreener` | 4 层架构(Inference → Rule Engine → Calibrated Aggregation → Decision Router)、4 Tier 决策、calibration 思路 |
| `RefoundAI/lenny-skills` | `skills/{name}/SKILL.md + references/` 目录约定 |
| `Golden2002/legal-research-skill` | 触发条件三档(高 / 中 / 不触发)、检索数据库表 |

## 当前阶段

V1 文档契约 — 已把共享层接口、默认管线和评分规则写清,但**还没有真实可调用的代码 / agent**。

下一步:出 `research-academic` 和 `research-comprehensive` 两个样板,然后跑一次真实小调研验证全链路。
