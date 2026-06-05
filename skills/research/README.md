# Research — 整体读图

## 这是干什么的

把"调研"这件事**拆成共享的工具层 + 不同类型的模板包**:
- `research/`(本目录) = 唯一入口
- `base/` = 工具 + 流程 + 评分,大家共用
- `packages/` = 不同调研类型的内部模板包

不再用一个万能 prompt 处理所有调研。

## 先说结论

如果你是人来审这套东西,**不用把整个目录都读完**。这个目录真正想让你确认的只有 3 件事:
- 主 skill 到底提供了哪些共享能力
- 默认 6 段管线是怎么跑的
- 打分与钩子契约哪些地方最贵、最不能乱改

换句话说,这里不是“8 篇都各有独立价值”的目录,而是“1 个入口 + 2 个高代价契约 + 若干低频参考”。

从执行角度看,这套东西的最低目标也只有一句话:
- 把一次调研稳定收成“问题 -> 路由 -> 取证 -> 结果包”

## 推荐阅读顺序

### 只想快速判断值不值得看

1. `README.md` — 看整体结构、职责边界、代价地图
2. `hooks.md` — 看子包改起来到底贵不贵
3. `scoring.md` — 看这套东西是否真的有“复核门槛”

### 你要改体系设计时

1. `README.md`
2. `SKILL.md`
3. `pipeline.md`
4. `hooks.md`
5. `scoring.md`

### 其他文件是什么定位

- `atoms.md`: 共享工具签名,偏维护者
- `router.md`: 路由细则,偏维护者
- `references/sources.md`: 追溯“抄了哪儿”,偏审核者

如果你不是在改协议,其实**不需要逐个读完**。

## 用户能看到什么

| 你说 | 系统做什么 |
|---|---|
| "帮我调研一下 RAG 的最新进展" | `research` 入口调用 `packages/academic` → 输出 `literature_review` + `reader_guide` + `research_gaps` |
| "看看 Notion 的竞品都有谁" | `research` 入口调用 `packages/competitive` → 输出 `feature_matrix` + `pricing_landscape` + `battle_cards` + `reader_brief` |
| "我有个想法,想做 X,你帮我挖挖" | `research` 入口调用 `packages/discovery` → 输出 `discovery_report` + `mvp_wedge` + `prd_outline` + `reader_brief` |
| "AI Code 这个方向值不值得做" | `research` 入口调用 `packages/comprehensive` → 输出 `decision_memo` + `tradeoff_brief` + `reader_brief` |

## 用户可见检查点

1. 先确认研究问题和范围，别一上来就把题目放太大
2. 先确认路由结果，再进 academic / competitive / discovery / comprehensive
3. 证据冲突或不够时先停，明确告诉用户现在只能给保守结论

这 3 个检查点是这套体系最值钱的部分。没有它们,再多模板也容易变成“直接搜一圈然后写一篇”。

## 产物路径约定

从现在开始,所有调研结果包统一用下面的落盘规则:

- 结果包目录:
  - `./research/{run_dir}/`
- 主报告副本:
  - `$CONTENT_DIR/search_report/{run_dir}.md`

其中:
- `{run_dir}` 是一次调研运行的目录名
- 如果该轮做了统一包装,目录内默认先读 `final_report.md`
- 如果还没做统一包装,V1 允许直接以包内主报告作为稳定入口
- 复制到 `$CONTENT_DIR/search_report/` 的文件,优先取 `final_report.md`;没有就取包内主报告

这样做的目的不是多存一份,而是把:
- 完整结果包
- 给人直接看的主报告

分成两个稳定入口。

### 环境变量配置

使用前需配置以下环境变量:
- `CONTENT_DIR`: 内容输出目录的根路径（例如 `~/content` 或 `/path/to/content`）

## 最小结果包契约

只要进入正式调研,目录里至少要有下面 4 类东西:

| 类别 | 默认文件 | 作用 |
|---|---|---|
| 问题定义 | `research_question.md` 或同义文件 | 说明这轮在回答什么 |
| 路由判断 | `routing_decision.json` | 说明为什么走这个包 |
| 证据留痕 | `source_log.csv` | 说明证据从哪里来 |
| 主报告入口 | `final_report.md` 或包内主报告 | 给人直接读 |

然后每个包再补自己的专属必交件:

| 路由 | 必交主报告 | 必交中间产物 |
|---|---|---|
| `academic` | `literature_review.md` | `study_selection.csv`、`comparison_matrix.csv`、`theme_outline.md` |
| `competitive` | `competitors_report.md` | `competitor_list.csv`、`feature_matrix.csv`、`pricing_landscape.csv` |
| `discovery` | `discovery_report.md` | `assumptions_log.md`、`pain_point_map.md`、`validation_plan.md` |
| `comprehensive` | `decision_memo.md` | `option_set.md`、`evidence_matrix.csv`、`decision_scorecard.csv` |

没有这些,就不是“可回看调研包”,只是一次性回答。

## 什么时候该停

- 用户只是问概念，不值得进完整调研链时先停
- 路由不稳时先停，先让用户确认调研类型
- 外部证据失败或过弱时先停，不强行产结论
- 用户只要轻量概览时先停，不默认升级成完整研究包

## 整体结构

```
                   用户输入
                      ↓
          ┌──────────────────────────┐
          │   research/ (单入口)        │
          │   ├─ base/router 自动判断类型 │
          │   ├─ base/ 默认 6 段管线     │
          │   ├─ base/ 原子工具集        │
          │   └─ base/ 10 维评分引擎     │
          └─────┬─────────┬─────────┬─┘
                ↓         ↓         ↓
         packages/academic packages/competitive packages/discovery packages/comprehensive
            (学术综述)         (竞品市场)         (产品发现)         (综合类 / fallback)
```

子模板包**只覆盖默认管线中需要变的部分**(称为"钩子覆盖"),不重写整套流程。

## 一次调研怎么跑

以"调研 RAG 最新进展"为例:

0. **Gate**:先判断这是不是正式调研题,还是轻量概览就够
1. **澄清**(clarify):问用户范围是 22-26 年还是更早?focus 在 evaluation 还是 method?
2. **路由**(route):确定这题是 academic,不是 comprehensive fallback
3. **检索**(retrieve):学术包覆盖此段 → 走 arXiv / Semantic Scholar / ACL Anthology
4. **筛选**(screen):学术包用 PICO + active learning 做纳排
5. **提取**(extract):每篇论文抽 method / dataset / metric / claim 到 `evidence_record`
6. **综合**(synthesize):学术包用"主题分组 + 时间线 + research gaps"
7. **复核**(review):评分引擎给每条结论打 10 维分,Tier 3 的回到人工

每段都是钩子,子包没覆盖就用默认行为(主 skill 提供)。

## 文件清单

```text
research/
├── SKILL.md
├── README.md
├── base/
│   ├── pipeline.md
│   ├── atoms.md
│   ├── router.md
│   ├── hooks.md
│   ├── scoring.md
│   └── references/
└── packages/
    ├── academic/
    ├── competitive/
    ├── discovery/
    └── comprehensive/
```

## 文件分层

| 层级 | 文件 | 你能获得什么 |
|---|---|---|
| 入口 | `README.md`, `SKILL.md` | 唯一用户入口和整体结构 |
| 高代价契约 | `base/hooks.md`, `base/scoring.md` | 哪些 schema / 规则一改就会带崩所有子包 |
| 运行机制 | `base/pipeline.md`, `base/router.md`, `base/atoms.md` | 默认怎么跑、怎么分流、有哪些共享工具 |
| 内部模板包 | `packages/*` | academic / competitive / discovery / comprehensive 的专属逻辑 |
| 追溯参考 | `base/references/sources.md` | 抄了哪儿、没抄哪儿 |

## 改动代价地图

子模板包作者最需要先知道的是:哪些地方能随便改,哪些地方一改就会带崩所有包。

| 代价 | 文件 | 为什么 |
|---|---|---|
| 低 | `README.md`, `base/references/sources.md` | 只改说明文字,不影响任何接口 |
| 中 | `base/router.md`, `base/pipeline.md`, `base/atoms.md` | 会影响默认行为和路由,但子包通常不用逐个重写 |
| 高 | `base/hooks.md` | 一改输入输出 schema,所有子包 hook 都要跟着升版 |
| 高 | `base/scoring.md` | 一改维度或 Tier 规则,所有 evidence_record 的解释和复核门槛都会变 |
| 最高 | `base/hooks.md` + `base/scoring.md` 同时改 | 等于把"共享层契约"整体换掉,必须联动验证所有子包 |

一句话记忆:
- 子模板包平时主要改自己的 `packages/*/routing.md` / `channels.md` / `report-template.md`
- 主 skill 里最不该轻易碰的是 `base/hooks.md` 和 `base/scoring.md`

## 现在这套文档的真实问题

如果你觉得“文件不少,但一口气看下来收获没那么大”,这个判断基本准确。当前版本已经解决了**契约从空到有**的问题,但还没完全解决两个问题:
- 人类阅读路径还不够收敛
- 个别文件的信息密度还不够高

所以更合适的阅读姿势不是“把所有 md 当成同权文档读”,而是把它们当成:
- 入口说明
- 高代价协议
- 低频参考

来看。

## 怎么加新模板包

1. 在 `./skills/research/packages/` 下新建 `{type}/`
2. 写 `SKILL.md`、`routing.md`、`channels.md`、`report-template.md`
3. 按需在该包的 `hooks.md` 里覆盖部分钩子(没覆盖就用默认)
4. 在 `base/router.md` 里登记触发关键词

不需要复制工具层、评分引擎或默认管线 — 主 skill 已经给了。

## 依赖清单

### 工具依赖
- Claude Code 的 WebFetch 工具（用于网页抓取和内容提取）
- Claude Code 的 WebSearch 工具（用于网络搜索）
- Claude Code 的 Read 工具（支持 PDF 阅读）
- Claude Code 的 Write 工具（用于文件写入）

### 外部服务依赖
- 学术数据库访问：arXiv / Semantic Scholar / PubMed / OpenAlex / Crossref / ACL Anthology
- 网络归档服务：Wayback Machine API (web.archive.org)
- 评论站点访问：G2 / Capterra / Product Hunt / TrustRadius

### 运行时依赖
- LLM 推理能力（用于打分、分类、提取、综合）

## 抄了哪些成熟方案

| 来源 | 抄什么 |
|---|---|
| `Galaxy-Dawn/claude-scholar` | skills + agents + commands 分工法、6 段流程语义、Progressive disclosure |
| `ChaokunHong/MetaScreener` | 4 层架构(Inference → Rule Engine → Calibrated Aggregation → Decision Router)、4 Tier 决策、calibration 思路 |
| `RefoundAI/lenny-skills` | `skills/{name}/SKILL.md + references/` 目录约定 |
| `Golden2002/legal-research-skill` | 触发条件三档(高 / 中 / 不触发)、检索数据库表 |

## 当前阶段

V1 以**文档契约 + 模板包样板**为主,重点是把共享层接口、默认管线、评分规则和子包边界写清。

当前已落地 4 个内部模板包:
- `packages/academic`
- `packages/comprehensive`
- `packages/competitive`
- `packages/discovery`

当前验证状态:
- `research-academic` 已跑过一次真实小调研验证
- `research-comprehensive` 已跑过一次真实小调研验证
- `research-competitive` 已补一份真实竞品 exemplar
- `research-discovery` 已补一份真实发现 exemplar

样例导航:
- `research/README.md`

如果后续继续推进,更适合做两件事:
- 继续提高 exemplar 的一手访谈 / 一手数据占比
- 视需要补最小自动执行代码,把文档契约变成半自动工作流

当前这一轮收口的重点不是再长更多文档,而是先把下面 4 件事钉死:
- 什么题值得进正式调研
- 分流依据是什么
- 用户在哪 3 个地方必须看见检查点
- 每条路最少要交哪些文件

## 最小验收

当前没有独立 CLI，这个总入口先按文档契约验收：

1. 打开 `README.md`，能在 1 分钟内说清 `research`、`base/`、`packages/` 三层分工
2. 打开 `SKILL.md`，能看出什么时候该进正式调研、什么时候该停、什么时候该降级成轻量概览
3. 任取一个真实问题，能明确分到 academic / competitive / discovery / comprehensive 之一
4. 打开对应 package 的 `SKILL.md`，边界不和总入口打架
5. 任一路由都能说出“主报告名 + 至少 3 个必交中间产物”
6. 读者能从结果包中回看到“研究问题、路由理由、证据来源、最终结论”
