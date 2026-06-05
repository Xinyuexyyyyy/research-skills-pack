# Channels — 产品发现渠道

## 优先级矩阵

| 优先级 | 渠道 | 适用 | 备注 |
|---|---|---|---|
| P0 | 用户给定输入 | idea / 场景 / 约束 | 第一手 |
| P0 | 内部反馈 / support / sales | 用户痛点 | 第一手 |
| P1 | 竞品产品页 / onboarding / pricing | workaround 与替代 | 轻外部验证 |
| P1 | 社区讨论 / Reddit / HN / forum | 真实吐槽 | 噪声高 |
| P2 | 招聘 / 行业报告 / blog | 方向验证 | 间接 |

## 调用约定

- discovery 默认先用内部输入,再做轻外部验证
- 不要求像 academic 那样大规模召回
- 每条关键假设都至少要有 1 条 supporting evidence 或 1 个待验证计划

## 最低要求

- 至少定义 1 个 target user
- 至少定义 3 个关键 pain points
- 至少列出 3 条关键 assumptions

## 被 comprehensive 子调用时

- 允许只返回 `pain_point_summary.md` + `evidence_records_partial[]`
