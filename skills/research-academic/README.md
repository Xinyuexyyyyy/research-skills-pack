# Research Academic — 读图

## 这是干什么的

学术研究 router。**只做识别和分发,不做实际工作**。

## 用户能看到什么

| 你说 | router 做什么 | 你最终拿到 |
|---|---|---|
| "帮我找一下 RAG 最新论文" | 二级路由 → `paper-discovery` | 候选池 csv + 检索来源 + bib |
| "我有候选 csv,做一下纳排" | 二级路由 → `paper-screening` | 纳排 csv + PRISMA flow |
| "读这几篇论文,做对比"(P1) | P0 暂未支持,先回 screening 或 reading 留空 | (P1)笔记 + 对比矩阵 + 证据表 |
| "先把这些论文逐篇读懂,先别写综述"(P1) | P0 暂未支持,先回 screening 或 reading 留空 | (P1)单篇导读报告 + 证据表 |
| "写一份综述"(P1) | P0 暂未支持,先回 discovery → screening | (P1)综述 + research gaps |
| "深入调研 X 方向"(P2) | P0 暂未支持 | (P2)deep research 报告 |

## 整体结构

```
                    用户输入
                        ↓
          ┌─────────────────────────────┐
          │  research-base(共享工具层)    │ 一级路由(是不是学术)
          └─────────────┬───────────────┘
                        ↓
          ┌─────────────────────────────┐
          │  research-academic(本 skill) │ 二级路由(学术里的哪一步)
          └──┬───────┬───────┬─────┬────┘
             ↓       ↓       ↓     ↓
         paper-  paper-  paper-  survey-      academic-
         discovery  screening  reading  writer        deep-research
         (P0)       (P0)       (P1)     (P1)          (P2)
```

## 为什么要二级路由

旧版 `research-academic` 是一个"大包",一个 SKILL.md 想接管整个学术综述链路:检索 + 筛选 + 抽取 + 写作 + 复核。问题是:

- 找论文、做纳排、读全文、写综述这四件事的输入输出模板差异很大
- 一个大包做完不容易回头改;改一段就动全链路
- 用户经常只想做其中一步(只想找论文,不想做完整综述)

新版只做路由。每一步交给一个独立 skill,边界清晰、产物明确,可以独立维护和迭代。

## P0 范围

- ✅ `research-base`(共享工具层 + artifacts schema)
- ✅ `research-academic`(本 router)
- ✅ `paper-discovery`(检索 + 候选池)
- ✅ `paper-screening`(纳排 + PRISMA)
- ⏳ P1: `paper-reading` / `survey-writer`
- ⏳ P2: `academic-deep-research`

## 跟旧"大包"的关系

旧版 Daily Work 工作区的 research-academic 仍然保留作为参考,但本工作区的新版**不继承**它的 channels / hooks / report-template:

- 检索渠道 → `paper-discovery/channels.md`
- 筛选规则 → `paper-screening/hooks.md`
- adequacy gate → `paper-screening` + `survey-writer`(P1)
- 综述骨架 → `survey-writer`(P1)
- 全文笔记 + 比较矩阵 → `paper-reading`(P1)

## 文件清单

```
research-academic/
├── SKILL.md     入口,定义触发与让位
├── routing.md   二级路由细则 + P0 临时收敛规则
└── README.md    本文件,读图
```

## 该看哪个文件

- 想知道"我说的话会被路由到哪里" → `routing.md`
- 想知道"这个 router 跟其他 skill 是什么关系" → 本文件
- 想知道"路由完之后下游 skill 怎么干活" → 进入对应下游 skill 看它自己的 `SKILL.md`
