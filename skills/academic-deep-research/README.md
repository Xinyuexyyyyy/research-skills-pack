# Academic Deep Research — 读图

## 这个 skill 在哪

```
research-base（共享层）
    ↓
research-academic（学术路由器 — 桥接）
    ↓
[academic-deep-research] ← 你在这里（学术科研入口层）
    ↓
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ paper-       │ paper-       │ paper-       │ survey-      │ 继续深度      │
│ discovery    │ screening    │ reading      │ writer       │ 调研 R2-4    │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## 双重角色

1. **入口层**：所有学术请求先进来,Round 1 做意图澄清,意图明确的直接分发到下游 skill
2. **深度调研**：开放/决策问题留在本 skill,继续走 Round 2-4 多轮迭代

## 改动代价地图

| 改动 | 影响范围 | 代价 |
|---|---|---|
| 调整 Round 1 分发逻辑 | 本 skill 的 SKILL.md | 低 |
| 新增轮次 | 本 skill 的 report-template.md | 低 |
| 修改检索源 | 本 skill（无下游影响） | 低 |
| 修改报告结构 | 本 skill 的 report-template.md | 低 |
| 修改分发目标 | 本 skill + research-academic/routing.md | 中 |

## 和谁通信

- **上游**：`research-academic`（桥接层,统一转入）
- **下游（分发）**：`paper-discovery` / `paper-screening` / `paper-reading` / `survey-writer`
- **下游（自执行）**：无进一步下游 skill,深度调研产出直接给用户消费
- **旁路**：如果深度调研中需要学术文献支撑,可调用 `paper-discovery` 作为子流程

## 一句话

学术科研的统一入口。先澄清意图,再决定是分发到主链路还是自己做深度调研。
