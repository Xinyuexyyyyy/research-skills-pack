---
name: research-discovery
description: 产品发现类调研模板包。用于把模糊 idea、需求或方向收敛成问题定义、关键假设、用户痛点、MVP wedge 和验证计划。基于 research-base 主 skill,覆盖 discovery 专属澄清、轻外部验证、发现式报告骨架。触发词:idea、想法、产品发现、PRD、MVP、用户痛点、需求验证、problem discovery、user interview、assumptions。
status: draft
---

# Research Discovery — 产品发现模板包

## 一句话定位

产品发现不是“先搜资料再总结”,而是**先把问题问对**,再用内部输入和轻外部验证把模糊方向收敛成可执行的 wedge。

## 你到底该看哪几个文件

### 只想判断这个包是不是“真产品发现”

1. `SKILL.md` — 看这包的边界
2. `report-template.md` — 看交付是不是问题、假设、验证计划,而不是空洞 PRD
3. `hooks.md` — 看关键假设和验证动作有没有被强制要求

### 其他文件是什么定位

- `channels.md`: 发现阶段优先看哪些输入
- `routing.md`: 什么时候它应该让位给其他包

如果你只是关心有没有产品发现的方法论,这两个不是首读文件。

## 你能从这个包里真正收获什么

读完应该能明确:
- discovery 不是“把 idea 说得更动人”
- 没有 `assumptions_log` 和 `validation_plan` 的都不算合格发现包
- `wedge` 的意义是故意缩小,不是功能不全
- 小白版导读要把 assumption / workaround / wedge 讲成人话

## 触发条件

### 高优先级(强命中)
- "我有个想法,帮我挖挖"
- "做产品发现""帮我定义 MVP"
- "写一版 PRD 草稿"
- "用户痛点到底是什么"

### 中优先级
- "这个方向有没有需求"
- "值不值得先做个小版本"
- "怎么把想法收窄"

### 不触发
- 明确只做竞品格局 → competitive
- 明确只做学术综述 → academic
- 明确是多源决策备忘 → comprehensive

## 钩子覆盖

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ | 加 problem statement / audience / assumptions |
| `hook_retrieve` | ✅ | 以内部输入为主,加轻外部验证 |
| `hook_screen` | ✅ | 按痛点强度、可验证性、频率筛选 |
| `hook_extract` | ✅ | 抽 pain / workaround / demand signal / assumption |
| `hook_synthesize` | ✅ | 先出 discovery canvas,再出 PRD / reader brief |
| `hook_review` | ✅ | 强制关键假设、验证计划和风险留痕 |

## 文件清单

| 文件 | 干什么 |
|---|---|
| `SKILL.md` | 入口 |
| `routing.md` | 命中条件与边界 |
| `channels.md` | 发现渠道与轻外部验证方式 |
| `report-template.md` | 发现包骨架 |
| `hooks.md` | 钩子覆盖详情 |

一句话记忆:
- `SKILL.md` 看“范围”
- `report-template.md` 看“是不是在逼验证”
- `hooks.md` 看“有没有防止自嗨”

## 固定产物层级

### A. framing 层(必出)
- `problem_statement.md`
- `target_user.md`
- `assumptions_log.md`
- `source_log.csv`

### B. 分析层(必出)
- `pain_point_map.md`
- `workarounds.csv`
- `evidence_summary.csv`
- `validation_plan.md`

### C. 交付层(必出)
- `discovery_report.md`
- `mvp_wedge.md`
- `prd_outline.md`
- `reader_brief.md`
