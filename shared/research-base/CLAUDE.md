---
name: research-base
description: 调研主 skill / 共享工具层。提供原子工具、默认 6 段管线、自动路由、10 维评分、统一 artifact schema。所有调研类 skill(学术、竞品、发现、综合、以及学术细分包 paper-discovery / paper-screening 等)都在本 skill 之上。触发词:调研、研究、research、文献综述、调查、对比、综述、看看、了解、找资料、systematic review、competitor、market、discovery、找论文、纳排、PRISMA、PICO。
status: stable
---

# Research Base — 调研主 skill(共享工具层)

## 一句话定位

不直接做调研,提供**调研所需的共享工具、默认管线、路由器、评分引擎、artifact schema**。具体调研由下游 skill 接管:

- 学术类:`academic-deep-research`(入口层) → 意图澄清后分发到 `paper-discovery` / `paper-screening` / `paper-reading` / `survey-writer`,或继续深度调研
- 其它类(P0 不做):`research-competitive` / `research-discovery` / `research-comprehensive`

## 阅读导航

- 先看 `README.md` 总览结构与改动代价地图
- 再看本文件确认触发条件、默认管线、路由
- 共享 csv schema 看 `artifacts.md`
- 接口契约看 `hooks.md` 与 `scoring.md`
- 原子工具看 `atoms.md`

## 触发条件(三档)

> 抄自 `legal-research-skill` 的三档分流。

### 高优先级(必须触发)
- 明确说"调研""研究""综述""文献综述""systematic review"
- 明确说"对比 X 和 Y""比较产品""竞品分析"
- 明确说"挖一下这个想法""做产品发现""写 PRD"
- 明确说"找论文""导入文献""候选池""纳排""PRISMA""PICO"
- 明确说"看看现在 / 业内 / 市场 / 学术界 X 的现状"

### 中优先级(结合上下文)
- "了解一下 X""看看 X 怎么样"
- "找点资料""有什么参考"
- 用户给出一个开放问题,需要外部信息才能回答

### 不触发
- 仅询问名词解释 / 概念 / 定义
- 仅要求生成内容(写文章、起标题)而无外部信息需求
- 仅要求执行已明确的代码任务

## 默认 6 段管线

```
澄清 → 检索 → 筛选 → 提取 → 综合 → 复核
```

每段都是一个**钩子点**,下游 skill 可任意覆盖。详见 `pipeline.md`。

## 自动路由(一级)

主 skill 根据用户输入,**自动决定调用哪个调研类 skill**:

| 命中 | 调度 |
|---|---|
| 学术 / 论文 / arxiv / 文献综述 / 找论文 / 纳排 / PRISMA / PICO | `academic-deep-research`(入口层) |
| 竞品 / 价格 / battle card / GTM(P0 暂未实现) | `research-competitive` |
| idea / MVP / PRD / 产品发现(P0 暂未实现) | `research-discovery` |
| 跨多类 / 决策级 / 不命中以上(P0 暂未实现) | `research-comprehensive`(fallback) |

学术类命中后直接进入 `academic-deep-research`(入口层),由它做意图澄清后分发到 `paper-discovery` / `paper-screening` / `paper-reading` / `survey-writer`,或继续走深度调研。

详见 `router.md`。

## 评分引擎

每条证据自动打 10 维分,按 4 Tier 决策路由(抄 MetaScreener):

| Tier | 条件 | 处理 |
|---|---|---|
| 0 | 硬性过滤(回链缺失等) | 自动剔除 |
| 1 | 高置信 + 高强度 + 无冲突 | 自动接纳 |
| 2 | 中置信 + 冲突可控 | 接纳但标注 |
| 3 | 低置信 / 高冲突 | 人工复核 |

详见 `scoring.md`。

## 共享 artifact schema

四份核心 csv 的字段定义 / 必填 / 唯一键 / DOI/arXiv/citation 规范统一放在 `artifacts.md`:

- `source_log.csv` — 检索来源日志(检索什么、从哪搜、什么时候)
- `candidate_papers.csv` — 候选池(去重后的可纳排集合)
- `study_selection.csv` — 纳排结论 + 原因码 + PRISMA 留痕
- `evidence_table.csv` — 证据池(每条结论一行,带 score + tier)

下游 skill 不重新发明这些字段,只能在自己的 `artifacts.md` 里**引用**主 schema 并补充本包专用字段。

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口(本文件) |
| `README.md` | 整体读图,人话讲整个体系怎么转 |
| `pipeline.md` | 默认 6 段管线规格 + 钩子点 |
| `atoms.md` | 原子工具签名(检索 / 解析 / 处理 / 评分 / 输出 / 验证) |
| `router.md` | 一级路由规则 + 触发条件细则 |
| `hooks.md` | 下游 skill 覆盖钩子的接口契约 |
| `scoring.md` | 10 维评分 + 4 Tier 决策路由 + 打分样例 |
| `artifacts.md` | 4 份共享 csv schema(P0 新增) |
| `references/` | 外部参考材料(claude-scholar / MetaScreener 等的关键提取) |

## 给下游 skill 作者的 5 条铁律

1. **不重写工具层**,缺工具向主 skill 提议加,不要在自己包里塞另一套。
2. **能用默认管线就别覆盖**,真不合适才覆盖钩子。
3. **必须输出 source_log + evidence_records**,不输出就过不了复核。
4. **每条结论必须挂可回溯的引用**,否则评分引擎自动 Tier 0 剔除。
5. **不替用户决定**,有歧义就走澄清,不要硬猜。

## 自检清单

- [ ] 4 份共享 csv schema 的字段定义完整且无冲突？
- [ ] 6 段管线每段都有明确的钩子点定义？
- [ ] 一级路由的命中条件覆盖高/中/不触发三档？
- [ ] 评分引擎的 10 维分和 4 Tier 决策规则清晰可执行？
- [ ] 下游 skill 引用主 schema 时没有重新定义相同字段？
