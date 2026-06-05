# Report Template — 竞品 / 市场情报输出骨架

最终产物不是“列一串竞品名字”,而是 **1 份主报告 + 若干竞争情报附录**。对人类读者,默认先看 `final_report.md`; 其他文件只在想看矩阵、价格表、战卡时再打开。

## 目录结构

```text
{run_dir}/
├── final_report.md
├── market_question.md
├── competitor_scope.md
├── search_log.md
├── source_log.csv
├── competitor_list.csv
├── feature_matrix.csv
├── pricing_landscape.csv
├── sentiment_summary.md
├── gtm_signals.md
├── competitors_report.md
├── battle_cards.md
└── reader_brief.md
```

## 阅读约定

- `final_report.md`:
  - 主报告。把市场结论、分层、价格带、用户信号和行动含义串成一份连续文本。
- `competitors_report.md`:
  - 专业读者版竞争情报正文。
- 其余文件:
  - 附录 / 工作底稿。默认不该要求读者逐个阅读。

## 落盘约定

- 结果包目录:
  - `./research/{run_dir}/`
- 主报告复制路径:
  - `$CONTENT_DIR/search_report/{run_dir}.md`

## 1. market_question.md

```markdown
# Market Question

- Core question:
- Why this market / category matters:
- Decision context:
- Geography:
- Time window:
- Audience:
```

## 2. competitor_scope.md

```markdown
# Competitor Scope

## 本次算进来的玩家
- Direct:
- Adjacent:
- Status quo / workaround:

## 本次不算进来的玩家
- Who:
- Why excluded:
```

## 3. final_report.md

```markdown
# {category} 竞品调研总报告

## 1. 先说结论
- 市场最值得记住的判断

## 2. 这次到底比较了什么
- 范围
- 时间窗
- 为什么看这批玩家

## 3. 市场怎么分层
- direct
- adjacent
- workaround

## 4. 差别主要在哪里
- 功能
- 价格
- 用户反馈
- GTM

## 5. 这对我们意味着什么
- 哪些位置很挤
- 哪些位置仍有空位

## 6. 如果只想继续深挖
- `feature_matrix.csv`
- `pricing_landscape.csv`
- `battle_cards.md`
```

## 4. competitors_report.md

```markdown
# {category} Competitive Report

## 一句话结论
- 这个市场当前最值得记住的判断是什么

## 1. 这次调研在看什么
- 市场问题是什么
- 为什么现在看
- 本次范围与时间窗

## 2. 我们怎么做这次调研
- 用了哪些渠道
- 哪些信息是一手,哪些是二手
- 哪些地方数据缺失

## 3. 竞争集合怎么划分
- Direct
- Adjacent
- Status quo / workaround
这里要解释:
- 每一类为什么被分到这里
- 这三类差别为什么重要

## 4. 功能差异
- 核心能力
- 缺失能力
- 差异是否真的影响购买决策

## 5. 定价差异
- 套餐结构
- 价格带
- 隐性门槛(座席、用量、企业版)

## 6. 用户评价差异
- 用户最常夸什么
- 用户最常骂什么
- 哪些评价是高频、哪些只是个例

## 7. GTM / 战略信号
- 上新节奏
- 重点人群
- 招聘 / 融资 / 渠道动作

## 8. 这对我们意味着什么
- 哪些位置已经很挤
- 哪些差异化还存在空位
- 如果要进入,最可能从哪打

## 9. 结论
- 谁最强
- 谁最贵
- 谁最容易替代
- 哪些空位还没人占
```

## 5. battle_cards.md

每个 direct competitor 一张卡:
- 它是谁
- 主要卖给谁
- 主打什么
- 为什么用户会选它
- 强项
- 弱项
- 价格 / 套餐提醒
- 最近动向
- 应对话术

## 6. reader_brief.md

```markdown
# 这份竞品调研在讲什么

## 1. 一句话结论
## 2. 这次到底在比较什么
- 用人话解释 category 和范围

## 3. 这个市场里主要有哪些玩家
- direct 是什么
- adjacent 是什么
- workaround 是什么

## 4. 它们差别主要在哪里
- 功能
- 价格
- 口碑

## 5. 为什么这些差别重要
- 对买家意味着什么
- 对我们意味着什么

## 6. 还有哪些地方别下结论太早
- 数据缺口
- 噪声来源

## 7. 如果你只记 3 件事
```

## 7. 复核要求

- [ ] direct competitors >= 3
- [ ] pricing 必须有官方来源
- [ ] feature matrix / pricing landscape 已落地
- [ ] reader_brief.md 已完成
- [ ] 每个关键判断都能回答“这意味着什么”
- [ ] 术语都对非专业读者解释过
