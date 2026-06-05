# Routing — 产品发现包命中条件

## 命中决策

满足以下任一即命中:

- idea / 想法 / MVP / PRD / 产品发现 / 用户痛点
- "帮我把这个方向收窄"
- "需求到底是不是真的"
- "用户现在怎么解决这个问题"

## 不命中(让位)

- 核心是市场格局与竞品列表 → competitive
- 核心是文献、论文、研究进展 → academic
- 核心是跨多源最终决策 → comprehensive

## routing_decision 输出补充

```json
{
  "discovery_subtype": "idea_clarification | problem_validation | mvp_definition | prd_seed",
  "target_user_hint": "developers | consumers | ops | founders | ...",
  "preferred_channels": ["internal_inputs", "support_feedback", "light_external_validation"]
}
```
