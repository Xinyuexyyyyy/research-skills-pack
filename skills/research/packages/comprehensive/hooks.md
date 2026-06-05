# Hooks — 综合类钩子覆盖

> 接口契约见 `../../base/hooks.md`。本文件描述综合类的覆盖。

## 覆盖矩阵

| 钩子 | 覆盖 | 改动幅度 |
|---|---|---|
| `hook_clarify` | ✅ | 加 decision_question / stakeholders / horizon / audience_profile |
| `hook_retrieve` | ✅ | 多渠道 + 跨包子调用 |
| `hook_screen` | ✅ | 按决策相关性而非通用相关性 |
| `hook_extract` | ✅ | 每条 evidence 必带"对哪个选项支持/反对" |
| `hook_synthesize` | ✅ | 先出 decision canvas / scorecard,再出 memo + reader brief |
| `hook_review` | ✅ | 强制反向论证 + conflict_log + explainability |

---

## 1. `hook_clarify`

### 必须补的 custom

```yaml
clarified_question:
  topic: ...
  scope: ...
  time_window: [start, end]
  output_form: decision_memo
  constraints: [...]
  custom:
    decision_question: string         # 一句话决策问题
    candidate_options: [string]       # 候选选项,默认含"不做 / 推迟"
    decision_owner: string            # 谁拍板
    stakeholders: [string]            # 谁会被影响
    horizon: weeks | months | quarters
    audience_profile: beginner | mixed | expert
    success_criteria: [string]        # 决策好的标志
    constraints_hard: [string]        # 不可妥协约束(预算 / 时间 / 合规)
    slices:                           # 由 router 或本钩子产出
      - slice_id: S1
        type: academic | competitive | discovery | self
        subquery: string
```

### 反问规则

- 若用户没给 candidate_options,本钩子至少自动补 ["做", "不做", "推迟"] 三个,再问用户要不要加
- 若用户没给 horizon,默认 `quarters`,但要确认
- 若 decision_question 含糊(如"看看 X 怎么样"),先问"你最终要决定的是什么?"再继续
- 若用户没说明读者,默认 `audience_profile=mixed`

### 必须额外落 3 个 framing 产物

- `decision_question.md`
- `option_set.md`
- `slice_plan.md`

---

## 2. `hook_retrieve`

### 行为

按 `slices[]` 派发:
- `type=academic` → 子调用 research-academic(片段模式)
- `type=competitive` → 子调用 research-competitive(片段模式)
- `type=discovery` → 子调用 research-discovery(片段模式)
- `type=self` → 用本包 `channels.md` 的直接渠道

### 子调用契约见 `channels.md` § 跨包子调用

### 输出

合并的 `raw_materials[]`,每条带 `slice_id` 字段(写到 `metadata.slice_id`)。

### 失败处理

- 子包失败:slice 标 `incomplete`,综合类继续;decision_memo "局限性"必须显式列
- 子包超时:budget 用尽即停,已抓到的部分照用

---

## 3. `hook_screen`

### 默认筛选规则被替换为"决策相关性优先"

筛选标准:
1. **影响决策的能力**:能否支持/反对某个 candidate_option?能 → include
2. **关键事实层级**:是不是 success_criteria 关心的事实?
3. **去重**(主 skill 默认行为)
4. **时效**:在 horizon 内仍然成立?

### `criteria.custom`

```yaml
custom:
  decision_relevance_threshold: float  # 0-1,默认 0.6
  options_coverage_min: int            # 每个选项至少要有几条 evidence,默认 3
  hard_filter_off_topic: bool          # 默认 true
```

### 不达标处理

- 某个选项 evidence 不足 `options_coverage_min` → 反向触发新增 slice 或扩大检索
- 全部选项都不足 → review 阶段会降级为 `needs_human_review`

### 必须在筛选后更新 `decision_scorecard.csv` 初版

至少保留:

```csv
option_id,option_label,evidence_count,high_weight_evidence_count,main_open_questions
```

---

## 4. `hook_extract`

### evidence_record.custom 必填

```yaml
custom:
  slice_id: string
  relates_to_decision_question: string  # 关联到具体子问题
  supports_options: [string]            # 支持哪些 Opt
  against_options: [string]             # 反对哪些 Opt
  fact_type: stat | trend | quote | example | benchmark | policy
  decision_weight: low | mid | high     # 这条对决策的权重(主观)
  explain_for_reader: string            # 用人话解释这条证据为什么重要
```

### 一条材料拆多条 evidence 的规则

- 每条 evidence 一个独立 claim
- 每条只能关联一个 `relates_to_decision_question`(关联多个就拆)
- 同一条 evidence 可以同时支持多个选项 / 反对多个选项

---

## 5. `hook_synthesize`

### 改为两段式综合

#### Stage 5A. 先出决策分析骨架
- `decision_scorecard.csv`
- `tradeoff_brief.md`
- `conflict_log.md`

#### Stage 5B. 再出交付物
- `decision_memo.md`
- `reader_brief.md`
- `evidence_matrix.csv`

### `summary_claims[]` 必须包含:
- 推荐选项的 1 句话表述
- 推荐选项的 3 条主依据(每条引用)
- 至少 3 条反向论点(每条引用)
- 强冲突列表(若有)
- 至少 3 条给非专业读者的 explainability claims

### Tier 处理
- Tier 1 / Tier 2 → 进 decision_memo + tradeoff_brief
- Tier 3 → 仅在 conflict_log 或"局限性"提及
- 推荐选项的核心依据**至少 1 条 Tier 1**,否则降级为"暂缓 / 推迟"或主动反问用户

### 选项排序
- 按证据强度 + 决策相关性综合排,推荐选项放第一
- 不要刻意"凑够 5 个"——每个选项必须有真实证据支撑

### 写作约束
- `decision_memo.md` 默认给专业读者 / 决策者
- `reader_brief.md` 默认给非专业读者 / 跨职能读者
- 每个关键判断都要回答:
  - 这是什么判断
  - 为什么这么判断
  - 代价是什么
  - 如果判断错了会怎样

---

## 6. `hook_review`

### 在主 skill 默认复核之上,加:

#### A. adequacy gate

要被允许叫 `decision_memo`,至少满足:
- 每个 candidate_option 都有 evidence >= `options_coverage_min`
- 已落 `decision_question.md` / `option_set.md` / `slice_plan.md`
- 已落 `decision_scorecard.csv`
- 已落 `reader_brief.md`(除非 `audience_profile=expert`)

否则:
- 只能降级叫 `decision_note`

#### B. 反向论证检查(必)
- 推荐选项的"魔鬼代言"必须 ≥ 3 条
- 任一反对论点 Tier 1 ≥ 2 条 → 状态降级为 `needs_human_review`

#### C. 选项覆盖检查
- 每个 candidate_option 的 evidence ≥ `options_coverage_min`
- 不足 → 列入 review_notes.gaps

#### D. 强冲突检查
- conflict_log 中"强冲突"未给出处理倾向 → `needs_human_review`

#### E. 切片完整性
- 任何 slice 标 `incomplete` 而 decision_memo 未在"局限性"说明 → `failed`

#### F. 推荐稳健性
- 推荐选项的核心依据 0 条 Tier 1 → `needs_human_review`
- 反对推荐选项的 Tier 1 多于支持的 → `needs_human_review`

#### G. explainability 检查
- 若 `reader_brief.md` 只是正文压缩版,而不是面向非专业读者重写 → `needs_human_review`

---

## 不覆盖的钩子
(全部覆盖,无未覆盖项)

---

## 与子包的契约约束

- 综合类调用其他包时,**不允许子包返回未打分的 evidence**
- 子包传回的 evidence_records_partial 必须已经经过主 skill scoring
- 综合类不二次打分,以子包提交的为准(避免漂移)
- 综合类只对"装配阶段"负责,不对"切片阶段"重做评分
