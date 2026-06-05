# Routing — 竞品包命中条件

## 命中决策

满足以下任一即命中本包:

### A. 关键词命中
- 竞品、竞争对手、市场格局、替代方案、价格、定价、battle card、GTM
- competitor、competitive analysis、pricing、market landscape、reviews、alternatives

### B. 渠道命中
- 用户明确提到 G2 / Capterra / TrustRadius / Product Hunt / pricing page / Reddit / hiring / funding

### C. 输出形态命中
- feature matrix
- pricing landscape
- battle card
- competitor report

### D. 用户显式指定
- "用竞品分析方式做"
- "做一份 battle card"

## 不命中(让位)

- 核心是学术 / 文献综述 → academic
- 核心是用户问题定义 / MVP / PRD → discovery
- 核心是 go/no-go 决策,且明显混合多源 → comprehensive

## routing_decision 输出补充

若 matched=`research-competitive`,额外输出:

```json
{
  "competitive_subtype": "landscape | pricing | battle_card | alternatives",
  "category_hint": "devtools | saas | ai | consumer | ...",
  "priority_channels": ["official_sites", "pricing_pages", "review_sites"]
}
```
