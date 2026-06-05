# Report Template — 产品发现输出骨架

最终产物不是“把一个 idea 说得很激动人心”,而是 **1 份主报告 + 若干发现底稿**。对人类读者,默认先看 `final_report.md`; 其他文件主要用于看假设、证据和验证计划的细节。

## 目录结构

```text
{run_dir}/
├── final_report.md
├── problem_statement.md
├── target_user.md
├── assumptions_log.md
├── source_log.csv
├── pain_point_map.md
├── workarounds.csv
├── evidence_summary.csv
├── validation_plan.md
├── discovery_report.md
├── mvp_wedge.md
├── prd_outline.md
└── reader_brief.md
```

## 阅读约定

- `final_report.md`:
  - 主报告。把问题、用户、痛点、假设、wedge 和验证计划整成一份连续文本。
- `discovery_report.md`:
  - 专业读者版发现正文。
- 其余文件:
  - 附录 / 工作底稿。默认不该要求读者逐个阅读。

## 落盘约定

- 结果包目录:
  - `./research/{run_dir}/`
- 主报告复制路径:
  - `$CONTENT_DIR/search_report/{run_dir}.md`

## 1. problem_statement.md

```markdown
# Problem Statement

- Core problem:
- Why now:
- Who is affected:
- Current alternatives:
- Desired outcome:
```

## 2. target_user.md

```markdown
# Target User

- Primary user:
- Secondary user:
- Trigger scenario:
- Current workflow:
- Highest-cost pain:
```

## 3. assumptions_log.md

```markdown
# Assumptions Log

| Assumption | Why we believe it | Evidence today | How to validate |
|---|---|---|---|
```

## 4. final_report.md

```markdown
# {idea} 发现总报告

## 1. 先说结论
- 这个方向值不值得继续做

## 2. 想解决什么问题
- 问题定义
- 为什么现在看

## 3. 谁最痛,现在怎么凑合
- 用户
- workaround

## 4. 我们为什么觉得这可能是机会
- 核心证据

## 5. 还只是猜测的地方
- 关键假设

## 6. 最小 wedge 是什么
- 先做什么
- 不做什么

## 7. 接下来怎么验证
- 最便宜的实验

## 8. 想深挖时再看什么
- `assumptions_log.md`
- `pain_point_map.md`
- `validation_plan.md`
```

## 5. discovery_report.md

```markdown
# {idea} Discovery Report

## 一句话结论
- 这个方向值不值得继续收敛

## 1. 这次到底想解决什么问题
- 问题定义
- 为什么现在值得看

## 2. 谁最受这个问题困扰
- 目标用户
- 典型场景
- 触发时刻

## 3. 用户现在怎么凑合
- 当前 workaround
- 为什么现有做法不够好

## 4. 主要痛点
- 高频痛点
- 高成本痛点
- 高情绪摩擦痛点

## 5. 需求证据
- 直接证据
- 间接信号
- 还缺什么证据

## 6. 关键假设
- 哪些已经有证据
- 哪些还只是猜测

## 7. 最小 wedge
- 先做什么
- 故意不做什么
- 为什么这是最小可验证切口

## 8. 下一步验证计划
- 最便宜的实验
- 成功 / 失败信号
- 预计多久能得到反馈

## 9. 主要风险与不确定性
- 需求可能没想象中强
- 用户可能不愿迁移
- 获客或交付成本可能过高
```

## 6. mvp_wedge.md

- 先做什么
- 不做什么
- 为什么这是最小可行切口
- 用户愿意为它切换 / 付费的理由
- 若假设错了,最先会错在哪里

## 7. prd_outline.md

- 用户
- 场景
- 核心任务
- 成功指标
- 非目标
- 最小事件流
- 首轮不做的能力

## 8. reader_brief.md

```markdown
# 这份产品发现调研在讲什么

## 1. 这个 idea 想解决什么问题
## 2. 谁最痛
## 3. 他们现在怎么凑合
## 4. 为什么这个机会可能存在
## 5. 现在哪些还只是猜测
- 用人话解释 assumption

## 6. 最小可做版本是什么
- 用人话解释 wedge

## 7. 接下来最该先验证什么

## 8. 如果你只记 3 件事
```

## 9. 复核要求

- [ ] pain points >= 3
- [ ] assumptions >= 3
- [ ] validation_plan.md 已完成
- [ ] reader_brief.md 已完成
- [ ] 每个关键 assumption 都映射到证据或验证动作
- [ ] 术语都对非专业读者解释过
