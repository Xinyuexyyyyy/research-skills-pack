# Routing — 综合类命中条件 + 协作约定

## 命中决策

满足以下**任一**即命中本包(主路由表见 `research-base/router.md`):

### A. 决策语气强
- "值不值得做""要不要做""选哪个""X vs Y 该怎么定"
- "深入调研""综合调研""deep research""deep dive"

### B. 多类型混合
- 同时命中 academic / competitive / discovery 中 ≥2 类
- 例:"AI Code 这个方向值不值得做"——既要学术现状又要竞品又要用户需求

### C. 不命中其他三类(兜底)
- router 给不出明确单一类型 → 默认进本包

### D. 用户显式声明
- "用综合类做""做一份决策备忘""帮我出 decision memo"

一句话记忆:
- 混合题、决策题、兜底题 → 本包
- 单一专门题 → 让位

---

## 不命中(让位)

- 用户明确说"只看论文""做文献综述" → academic
- 用户明确说"列竞品""做 battle card" → competitive
- 用户明确说"挖一下这个想法""写 PRD" → discovery

如果题目只是“解释一下 X 是什么”，也不应进入本包。

---

## 跨包协作

### 综合类的特权:可以子调用其他包

fallback 模板的核心责任不是亲自做所有事,而是**按决策问题切片,把切片分配给对应专精包,然后融合**。

### 子调用契约

1. 综合类先做 hook_clarify,产出 `decision_question` + 切片清单
2. 每个切片标注 `slice_type ∈ {academic, competitive, discovery, comprehensive_self}`
3. 对每个切片调对应包的"片段模式"(见 `channels.md` § 跨包子调用)
4. 各包返回的 `evidence_records[]` 合并到本包的全局证据池
5. 本包独占 hook_synthesize / hook_review,统一组装决策备忘

### 退化情形

- 切片只有 1 类 + 用户没强制综合 → router 应当直接给那一类专精包,综合类不接
- 切片虽然多类但都很浅 → 综合类自己跑,不外调
- 子包失败超时 → 综合类继续,缺失部分写到"局限性"

## 进入前的最小判断

正式进入本包前，至少确认:
1. 有一句清楚的 `decision_question`
2. 有最小候选选项集
3. 题目确实不是单一专门问题

如果这 3 条不满足，应先停在 clarify，而不是直接开始综合调研。

---

## routing_decision 输出补充

`routing_decision.json` 中 matched=`research-comprehensive` 时,本包要求附加:

```json
{
  "decision_question": "string",
  "candidate_options": ["做", "不做", "推迟"],
  "slices": [
    {"slice_id": "S1", "type": "academic", "subquery": "..."},
    {"slice_id": "S2", "type": "competitive", "subquery": "..."}
  ],
  "delegation_plan": "self_only | mixed",
  "horizon": "weeks | months | quarters"
}
```

---

## 显式覆盖

用户在输入里说:
- "用综合类做 X" → 强制本包
- "出一份 decision memo" → 强制本包
- "deep research X" → 强制本包

显式覆盖优先级最高。

---

## 与 router.md 的兼容
- 本文件不修改主路由,只补充本包专属字段
- router 仍只输出一次顶层 matched;子调用是本包内部行为,不算二次路由
