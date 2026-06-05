# Paper Reading — 命中条件与让位规则

> 基于 Keshav 三遍阅读法 + PICO 框架的论文证据抽取 skill。

---

## 1. 命中本 skill

本 skill 由 `research-academic/routing.md` 二级路由决定进入。命中信号:

### 强命中
- 用户说"抽证据""读论文""evidence extraction""systematic review reading""key findings"
- 用户说 "PICO 抽取" / "PECO 抽取" / 抽 method / 抽 outcome
- 用户说"三遍阅读""Keshav""How to Read a Paper""论文精读"
- 用户已有 `study_selection.csv`(由 `paper-screening` 产出 或 用户自带),要从入选论文中抽证据

### 中命中
- 用户说"逐篇看摘要做笔记""把每篇的方法和发现整理成表"
- 用户说"我要写综述章节,需要每篇论文的关键数据"
- 用户说"帮我读这几篇论文""分析这些文献"
- 用户说"单篇精读""给我讲明白这篇论文""做导读报告"

### 不命中(让位)
- 用户没有 `study_selection.csv` 或没有 selection=include 行 → `paper-screening`
- 用户已有 `evidence_table.csv` 要写综述 → `survey-writer`(P1)
- 用户要做的是检索新论文 → `paper-discovery`
- 用户说"帮我找关于XX的论文" → `paper-discovery`

---

## 2. 与 paper-screening 的边界

| 维度 | paper-screening | paper-reading(本 skill) |
|---|---|---|
| 主要动作 | criteria / 标题摘要筛选 / 全文纳排 / PRISMA | Pass 1 五问扫描 + Pass 2 PICO/method/findings 抽取 |
| `selection` 字段 | 必写 | **不写**(只读) |
| `pass1_verdict` | 不产出 | 必产出(proceed/demote/skip) |
| `evidence_table.csv` | 不产出 | 必产出(22 列) |
| `pending_fulltext.csv` | 不产出 | 必产出(可空) |
| `low_confidence_evidence.csv` | 不产出 | 条件产出 |

铁律:**reading 不重做纳排**。即使发现某篇 include 的论文 abstract 太烂、应该 exclude,也不在本 skill 里改 selection,而是打 `pending_fulltext` + 在 `evidence_audit.md` 备注。

---

## 3. 与 survey-writer 的边界(P1)

| 维度 | paper-reading | survey-writer(P1) |
|---|---|---|
| 主要动作 | 抽证据 + 标置信度 + 标 qualitative_only + Pass 1 五问 | 把证据组合成可读综述章节 |
| 输出 | `evidence_table.csv`(22 列) / `evidence_audit.md` / `pending_fulltext.csv` / `low_confidence_evidence.csv` / 单篇导读报告 | `survey.md` / `comparison_matrix.csv` / `gaps.md` |
| 全文获取 | 用于做证据抽取 | 不下载,只用 evidence_table 引用 |
| 下游输入 | `contributions` 字段是 survey-writer"研究贡献"章节核心 | 接收 evidence_table.csv |

铁律:**reading 不写综述**。即使用户在抽证据过程中说"这几篇结合起来就是一段综述",也要拒绝并提示"那是 survey-writer 的工作"。

补充: **reading 可以独立结束**。如果用户目标是单篇吃透、证据沉淀、方法对比或后续手动写作,本 skill 交付 reading 产物后即可结束,不强制转 writer。

---

## 4. 与 research-base 默认管线的边界

| 默认段 | reading 怎么走 |
|---|---|
| clarify | ⛔ **不做**(上游 paper-screening 已澄清) |
| retrieve | ✅ 部分:仅 arXiv PDF/ar5iv 下载(其他通路 P1+) |
| screen | ⛔ **不做** |
| extract | ✅ 完全覆盖:Pass 1 五问 + Pass 2 PICO + method + findings + confidence + source |
| synthesize | ⛔ **不做** |
| review | ✅ 覆盖:三层 quality gate + 跨文件一致性自检 |

---

## 5. 显式覆盖

- 用户说"全文抽取" → 强制 `extraction_source=fulltext`,无全文则进 pending
- 用户说"只要 Pass 1" → 只跑 Pass 1 五问,跳过 Pass 2 PICO
- 用户说"我已经有 evidence_table.csv,只是想补 audit" → 跳过抽取,只产出 `evidence_audit.md`
- 用户说"我要做 review-only(只综述)" → reject,引导回 survey-writer
- 用户说"逐篇做精读笔记" → 接；产出单篇导读报告 + 结构化证据
- 用户说"只用 Keshav 五问" → 只跑 Pass 1,不跑 Pass 2 PICO

---

## 6. 反问澄清(只问 1 个最关键的)

- **没有 study_selection.csv** → "你有 study_selection.csv 吗?发我路径,或者我先去 paper-screening 帮你建。"
- **没有 selection=include 行** → "study_selection.csv 里没有 include 行 — 是 paper-screening 没跑完,还是全部 exclude 了?"
- **不确定要不要全文** → "你想 abstract-only 抽(快但 16% 论文进 pending),还是 arXiv 部分走全文(工科覆盖率 +10-20%)?"
- **不确定读多深** → "你要 Pass 1 五问扫描(快),还是 Pass 1+2 全套抽取(标准)?"

不要一次问多个。

---

## 7. P0 阶段不做

- 不做 PDF parser 实体接入(arXiv PDF 下完后直接 LLM 吃文本,P1 再选 GROBID/nougat)
- 不做 Pass 3 批量跑(P0 只验证单条)
- 不做 Self-consistency 多轮投票(P1 加)
- 不做 retraction check / 撤稿过滤(留给 P1)
- 不做 figure / table / 公式结构化抽取(只读文本)
- 不做 citation graph 分析(P2)
- 不做 LLM-as-a-Judge 自评(confidence 由抽取时即写)
