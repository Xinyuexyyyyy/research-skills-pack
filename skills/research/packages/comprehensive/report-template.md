# Report Template — 综合类输出骨架

最终产物 = 一个目录,包含 **1 份主报告 + 若干分析附录**。对人类读者,默认先看 `final_report.md`; 其他文件用于追依据、看选项细节和复核。目标不是把读者扔进一堆 md,而是给一份连续可读的决策报告,再附底稿。

这份骨架的核心不是“写长文”，而是让读者能按下面顺序回看：
- 这次到底在决定什么
- 比了哪些选项
- 证据为什么支持这个推荐
- 哪些地方其实还不确定

## 目录结构

```
{run_dir}/
├── final_report.md         # 默认给人看的总报告: 先读这个
├── decision_question.md     # 决策问题、背景、时间窗
├── option_set.md            # 候选选项定义
├── slice_plan.md            # 切片与委派计划
├── source_log.csv           # 已合并(主 skill 强制)
├── evidence_matrix.csv      # 全部证据 + slice_id + tier
├── decision_scorecard.csv   # 各选项证据覆盖和核心判断
├── tradeoff_brief.md        # 主选项的 pros/cons 矩阵 + 反向论证
├── conflict_log.md          # 强冲突 / 矛盾 evidence 单独梳理
├── decision_memo.md         # 面向专业读者 / 决策者
└── reader_brief.md          # 面向非专业读者 / 跨职能读者
```

可选扩展:
- `decision_tree.md` — 决策路径图
- `risk_register.md` — 风险登记
- `next_steps.md` — 落地下一步

---

## 阅读约定

- `final_report.md`:
  - 主报告。把 recommendation、关键证据、tradeoff、风险和下一步合并成一份连续文本。
- `decision_memo.md`:
  - 专业读者版决策正文。
- `reader_brief.md`:
  - 非专业读者导读。
- 其余文件:
  - 附录 / 工作底稿 / 复核材料。默认不该要求逐个阅读。

如果本轮还没统一包装 `final_report.md`，V1 允许直接把 `decision_memo.md` 当默认主入口，但必须在目录里讲清楚。

## 落盘约定

- 结果包目录:
  - `./research/{run_dir}/`
- 主报告复制路径:
  - `$CONTENT_DIR/search_report/{run_dir}.md`

优先级规则:
- 有 `final_report.md` → 复制它
- 没有 `final_report.md` → 复制 `decision_memo.md`

---

## 1. decision_question.md

```markdown
# Decision Question

- Background:
- Core question:
- Why now:
- Horizon:
- Decision owner:
- Stakeholders:
```

---

## 2. option_set.md

```markdown
# Option Set

- Opt-A:
  - What it means:
  - Why it exists:
- Opt-B:
...
```

---

## 3. slice_plan.md

```markdown
# Slice Plan

## Slice S1
- Type:
- Subquestion:
- Why this slice matters:

## Slice S2
...
```

---

## 4. final_report.md 骨架

```markdown
# {decision_question} 总报告

## 1. 先说结论
- 推荐什么
- 为什么

## 2. 这次到底在决定什么
- 背景
- 时间窗
- 不做决定的代价

## 3. 我们比较了哪几个选项
- 每个选项一句话解释

## 4. 最关键的证据是什么
- 按 3-5 条讲清,每条点明“意味着什么”

## 5. 为什么推荐这个,不推荐另外那个
- 直接写取舍

## 6. 主要风险和反对理由
- 明确列出最强反例

## 7. 接下来做什么
- 30 / 60 / 90 天

## 8. 想深挖时再看什么
- `decision_memo.md`
- `tradeoff_brief.md`
- `conflict_log.md`
```

---

## 5. decision_memo.md 骨架

抄 Amazon 6-pager / PR-FAQ + 经典决策备忘:

```markdown
# {decision_question}

## 一句话回答
{推荐选项 + 一行依据}

## 1. 背景与决策问题
- 业务 / 个人 / 项目背景
- 决策问题原文(来自 hook_clarify 的 custom.decision_question)
- 决策时间窗(horizon)

## 2. 候选选项
按"做 / 不做 / 推迟 / 替代"列出,每个选项标 [Opt-X]

## 3. 关键证据
按 slice 列重要证据(每条挂 [E-S?-XXX]):
### 3.1 学术 / 技术现状(slice S1)
### 3.2 市场 / 竞品(slice S2)
### 3.3 用户需求 / 痛点(slice S3)
### 3.4 自有 / 内部信号(若有)

## 4. 选项对比(指 tradeoff_brief.md)

## 5. 主要风险(指 conflict_log.md / risk_register.md)

## 6. 推荐 + 理由
- 推荐: [Opt-X]
- 主依据(3 条,每条挂证据 ID)
- 反对证据(为什么仍然推荐)

## 7. 落地下一步(若推荐做)
- 30 / 60 / 90 天 milestones
- 验证假设的最便宜实验

## 8. 局限性
- 切片不全 / 切片失败的部分
- 依赖的强假设
- 时间窗内可能变化的因素
```

---

## 6. reader_brief.md 骨架

```markdown
# 这份决策调研在讲什么

## 1. 一句话建议
- 推荐做什么 / 不做什么

## 2. 这次到底在决定什么
- 用人话解释 decision question

## 3. 为什么这个决定重要
- 不做会怎样
- 做错会怎样

## 4. 现在有哪几个选择
- 每个选择分别是什么

## 5. 我们为什么更倾向某个选择
- 最重要的 3 个理由

## 6. 还有哪些风险和不确定性
- 用人话解释 conflict / gaps

## 7. 如果你只记 3 件事
- 1.
- 2.
- 3.
```

---

## 7. evidence_matrix.csv schema

```
id,slice_id,material_id,claim,quote,source_ref,source_type,score_composite,tier,relates_to_decision_question,supports_options,against_options,tags
E-S1-001,S1,M-...,...,...,arxiv:...,paper,82,1,Q1,"Opt-A;Opt-C","Opt-B","method;rag"
```

字段说明:
- `slice_id` 标明哪个切片
- `relates_to_decision_question` 关联具体子问题
- `supports_options` / `against_options` 显式标该证据支持哪个选项、反对哪个

---

## 8. decision_scorecard.csv schema

```csv
option_id,option_label,evidence_count,tier1_count,main_benefit,main_cost,key_open_question,current_stance
Opt-A,Do X,12,4,"...", "...", "...",recommended
```

---

## 9. tradeoff_brief.md 骨架

```markdown
# Tradeoff — {decision_question}

## 选项对照

| 维度 | Opt-A: ... | Opt-B: ... | Opt-C: 不做 |
|---|---|---|---|
| 关键收益 | ... | ... | ... |
| 关键成本 | ... | ... | ... |
| 时间到价值 | ... | ... | ... |
| 强依赖 | ... | ... | ... |
| 主要风险 | ... | ... | ... |
| 证据强度 | Tier 分布 | Tier 分布 | Tier 分布 |

## 每个选项的 pros / cons(挂证据)

### Opt-A
**Pros**
- [E-S1-007] ...
- [E-S2-014] ...

**Cons**
- [E-S2-022] ...

### Opt-B
...

## 反向论证

对推荐选项做"魔鬼代言":列 3 个最有力的反对论点(必挂证据)。

- 若反对论点缺乏可靠证据,说明推荐稳定
- 若反对论点 Tier 1 多,说明推荐有风险,review 会把状态降级
```

---

## 10. conflict_log.md 骨架

```markdown
# Conflict Log — {decision_question}

## 强冲突(两条以上 Tier ≤ 2 证据直接矛盾)
- [Conf-1] [E-S1-012] vs [E-S2-008]:在"X"的关键指标上结论相反
  - 已采取的处理:倾向 [E-S1-012],因为 ...
  - 未解决的部分:...

## 部分冲突(语义有差,可能定义不同)
- ...

## 单方主张未被反驳(可能 Tier 3 风险)
- ...
```

---

## 11. 复核要求(对接 hook_review)

提交前必须自检:
- [ ] `decision_question.md`、`option_set.md`、`slice_plan.md` 已落地
- [ ] `decision_scorecard.csv` 已完成
- [ ] decision_memo 每条主张都有 [E-X] 引用
- [ ] `reader_brief.md` 已完成,且不是正文压缩版
- [ ] tradeoff_brief 每个选项至少 3 条 pros + 3 条 cons
- [ ] 反向论证至少 3 条
- [ ] conflict_log 列出所有 Tier ≤ 2 间的冲突
- [ ] 切片失败 / 数据不全已在"局限性"显式说明
- [ ] 推荐选项的核心依据,至少 1 条 Tier 1
- [ ] 候选选项至少 3 个(默认含"不做 / 推迟")

---

## 12. adequacy gate 对应的最小目录检查

正式交付前，至少检查下面 6 项:
- [ ] `decision_question.md` 已明确问题、时间窗和拍板人
- [ ] `option_set.md` 已显式列出候选选项
- [ ] `source_log.csv` 已落地
- [ ] `decision_scorecard.csv` 已有每个选项的证据覆盖
- [ ] `conflict_log.md` 已说明主要冲突或明确写“无强冲突”
- [ ] `final_report.md` 或 `decision_memo.md` 已能独立阅读

缺任一项时:
- 结果应降级为 `decision_note`
- 不应对外声称“已经形成正式 decision memo”
