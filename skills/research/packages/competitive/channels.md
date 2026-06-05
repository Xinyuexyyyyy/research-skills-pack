# Channels — 竞品 / 市场情报渠道

## 优先级矩阵

| 优先级 | 渠道 | 适用 | 备注 |
|---|---|---|---|
| P0 | 官网 / 产品页 / 帮助中心 | 定位、功能、ICP | 一手 |
| P0 | 定价页 / 结账页 | pricing / packaging | 一手 |
| P1 | G2 / Capterra / TrustRadius | 用户评价 | 二手,需交叉验证 |
| P1 | Product Hunt / 官网 changelog | 上新节奏 | 早期信号 |
| P1 | 招聘页 / 招聘 JD | GTM / 产品方向 | 间接信号 |
| P1 | 融资新闻 / 官方 blog | 资源与战略 | 间接信号 |
| P2 | Reddit / HN / X / Indie Hackers | 真实反馈与吐槽 | 噪声高 |
| P2 | Wayback | 历史价格 / 历史定位 | 时间线对照 |

## 调用约定

- 至少覆盖 3 类渠道,否则只能降级为 `quick_landscape`
- 价格信息必须优先来自官方 pricing page
- 评论站结论不能单独成结论,必须与官网或论坛交叉验证
- 所有时间敏感信息必须记录抓取日期

## 最低要求

- direct competitors >= 3
- 至少 1 个 adjacent competitor
- 至少 1 个 status quo 或 manual workaround

## 被 comprehensive 子调用时

- 允许只返回 `competitor_list.csv` + `feature_matrix_partial.csv` + `evidence_records_partial[]`
- 不强制完整 `battle_cards.md`
