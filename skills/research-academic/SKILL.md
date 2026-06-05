---
name: research-academic
description: 学术研究 router。命中学术类任务后,统一转入 academic-deep-research（入口层）做意图澄清和分发。本 skill 不再承担具体的路由判断,只做一级→二级的桥接。触发词:文献综述、systematic review、找论文、纳排、PRISMA、PICO、SOTA、研究空白、survey、literature review、scoping review、meta-analysis。
status: deprecated
---

# Research Academic — 学术研究 router

## 一句话定位

> ⚠️ 本 skill 已废弃。所有学术请求直接由 `academic-deep-research` 接收，不再经过本桥接层。

> 接到学术类调研任务后,**统一转入 `academic-deep-research`（入口层）**。入口层负责意图澄清和下游分发。本 skill 只做桥接,不做具体路由判断。

## 上层契约

- 父级:`research-base`(共享工具层)
- 进入条件:`research-base/router.md` 已经把任务分到 `research-academic`(一级路由)
- 离开条件:转入 `academic-deep-research`,由它决定后续流向
- 共享 schema:`research-base/artifacts.md`(`source_log.csv` / `candidate_papers.csv` / `study_selection.csv` / `evidence_table.csv`)

## 下游 skill 矩阵

| 下游 skill | 状态 | 干什么 |
|---|---|---|
| `academic-deep-research` | ✅ 入口层 | 接收所有学术请求,Round 1 澄清后分发或继续深度调研 |
| `paper-discovery` | ✅ 已落地 | 检索 + 导入 + 去重 + 建候选池 |
| `paper-screening` | ✅ 已落地 | criteria + 标题摘要筛选 + 全文纳排 + PRISMA 留痕 |
| `paper-reading` | ✅ 已落地 | 全文问答 / 证据抽取 / 论文对比 / 单篇导读 |
| `survey-writer` | ✅ 已完成 | 综述 / related work / research gaps |

## 路由流程（已简化）

```
research-base (一级路由: 是学术类?)
    ↓
research-academic (本 skill: 桥接)
    ↓
academic-deep-research (入口层: Round 1 意图澄清)
    ↓
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ paper-       │ paper-       │ paper-       │ survey-      │ 继续深度      │
│ discovery    │ screening    │ reading      │ writer       │ 调研 R2-4    │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## 触发条件(本 skill 该被进入的情形)

### 高优先级(强命中)
- "文献综述""系统综述""做个 survey"
- "research gap""SOTA""state of the art"
- 用户明确指定 arXiv / PubMed / Semantic Scholar / OpenAlex / Crossref / DBLP / ACL Anthology
- 提到 PICO / PECO / SPIDER 框架
- 明确说"找论文""导入文献""建候选池""纳排"

### 中优先级(结合上下文)
- "近 N 年关于 X 的研究有哪些"
- "X 这个领域有哪些主要方法"
- 输出形态是综述 / 论文表格 / references.bib

### 让位条件(命中本 skill 但应转出)
- 任务核心是产品决策 → 退回 `research-comprehensive`
- 任务核心是 GTM / 价格 / 竞品 → `research-competitive`
- 任务核心是用户痛点 / PRD / MVP → `research-discovery`

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口(本文件) |
| `routing.md` | 二级路由细则(已简化为统一转入入口层) |
| `README.md` | 读图,人话讲学术 router 跟下游 skill 的关系 |

## 自检清单

- [ ] 所有学术请求都统一经过 `academic-deep-research` 入口层？
- [ ] 本 router 不再做具体的 discovery/screening/reading/writer 判断？
- [ ] 让位条件明确：何时退回 comprehensive/competitive/discovery？
- [ ] `routing_decision.json` 的字段与入口层一致？
