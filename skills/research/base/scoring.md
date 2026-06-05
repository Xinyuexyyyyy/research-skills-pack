# Scoring — 评分引擎(10 维 + 4 Tier)

## 抄哪儿

直接借用 `MetaScreener` 的 4 层架构思路,把它的"4 Tier 决策路由"挪到通用调研场景。MetaScreener 处理的是论文 include/exclude,我们处理的是任意证据的 accept/flag/reject。

---

## 这份文件回答 3 个问题

1. 每条 evidence 到底看哪 10 维
2. 10 维怎么合成一个稳定的解释性总分
3. 总分和硬规则怎么路由到 Tier 0/1/2/3

---

## 用户能看到什么

每条证据(`evidence_record`)会产出两层结果:

- 一层是 `evidence_score`: 10 维原始评分 + `composite_score`
- 一层是 `tier`: 决定这条证据是剔除、直接接纳、带警告接纳,还是转人工

报告里能看到:
- `{evidence_id, claim, source, tier, composite_score}`
- 若不是 Tier 1,要能看到 `rationale`
- 汇总 `{Tier 0: N, Tier 1: M, Tier 2: K, Tier 3: J}`

---

## `evidence_score` schema

```yaml
confidence: float                # 0-1
selection: include | exclude | uncertain
redundancy: float                # 0-1,高 = 冗余高
strength: float                  # 0-1
primacy: primary | secondary | tertiary
recency: float                   # 0-1
authority: low | mid | high
coverage: float                  # 0-1
conflict: none | partial | contradictory
citation_completeness: float     # 0-1
composite_score: int             # 0-100
rationale: string[]              # 解释为什么是这个分和这个 tier
```

`composite_score` 是**解释性分数**,让复核者一眼看出证据大概站在哪一档。
最终是否接纳,仍由 Tier 规则决定。

---

## 10 维定义

| 维度 | 类型 | 范围 | 含义 |
|---|---|---|---|
| `confidence` | float | 0-1 | 提取者对结论正确性的自信程度 |
| `selection` | enum | include / exclude / uncertain | 是否通过筛选阶段 |
| `redundancy` | float | 0-1 | 与已有证据重复程度(高 = 冗余高) |
| `strength` | float | 0-1 | 证据本身论证强度 |
| `primacy` | enum | primary / secondary / tertiary | 一手 / 二手 / 三手 |
| `recency` | float | 0-1 | 时效性衰减分 |
| `authority` | enum | low / mid / high | 来源权威性 |
| `coverage` | float | 0-1 | 同结论被多少独立源支持 |
| `conflict` | enum | none / partial / contradictory | 是否与证据池冲突 |
| `citation_completeness` | float | 0-1 | 回链完整度 |

---

## 各维度打分指引

### `confidence`(0-1)

- 1.0: 多源一致 + 一手 + 权威源
- 0.8: 多源一致 + 二手权威源,或一手中权威源
- 0.5: 单源一手,或多源二手中权威
- 0.2: 单源二手 / 三手 / 低权威
- 0.0: 只有 AI 总结,没有原文依据

### `selection`

- `include`: 相关且满足 criteria
- `exclude`: 不相关或违反 criteria
- `uncertain`: 边界模糊,需要人工判断

### `redundancy`(0-1)

- 0.0: 全新观点 / 数据
- 0.3: 同观点不同表述
- 0.7: 同观点同来源链
- 1.0: 完全重复

### `strength`(0-1)

- 1.0: 公开 benchmark / 原始实验 / 官方数据 / 可核对的一手事实
- 0.7: 中等样本观察 / 案例研究 / 权威数据库摘要
- 0.4: 专家观点 / 单案例
- 0.1: 猜测 / 无验证

### `primacy`

- `primary`: 论文原文、官方文档、官网、财报、政策原文、用户原始访谈
- `secondary`: 权威媒体、正式数据库、分析机构、顶会落地页
- `tertiary`: 博客、社媒、AI 总结、论坛转载

### `recency`(0-1)

- 学术论文: 近 3 年 = 1.0, 3-5 年 = 0.8, 5-10 年 = 0.5, >10 年 = 0.2
- 竞品 / 市场: 近 3 月 = 1.0, 3-12 月 = 0.7, >12 月 = 0.3, >24 月 = 0.1
- 政策 / 法规: 仍有效 = 1.0, 已失效 = 0
- 默认: 用学术规则

### `authority`

- `high`: 政府 / 官方机构 / 原厂官网 / 原始作者 / 顶级期刊或会议正式页面
- `mid`: 权威媒体、行业协会、二线学术期刊、成熟数据库
- `low`: 个人博客、社媒、内容农场、匿名转载

### `coverage`(0-1)

- 1.0: 至少 3 个独立源且跨类型支持
- 0.6: 2 个独立源支持
- 0.3: 仅 1 个源
- 0.0: 无明确源

### `conflict`

- `none`: 与现有证据一致
- `partial`: 与部分证据有差异,但可能由定义或时间窗造成
- `contradictory`: 与多条现有证据直接冲突

### `citation_completeness`(0-1)

- 1.0: `ref + locator + quote` 全有
- 0.7: `ref + quote`
- 0.4: 仅 `ref`
- 0.0: 无回链

---

## 枚举维度的数值映射

为了合成 `composite_score`,枚举维度先转成数值:

| 枚举 | 映射 |
|---|---|
| `primacy.primary` | 1.0 |
| `primacy.secondary` | 0.7 |
| `primacy.tertiary` | 0.2 |
| `authority.high` | 1.0 |
| `authority.mid` | 0.6 |
| `authority.low` | 0.2 |
| `conflict.none` | 1.0 |
| `conflict.partial` | 0.5 |
| `conflict.contradictory` | 0.0 |

说明:
- `selection` 不参与线性加权,它是路由规则
- `redundancy` 进入合分时使用 `novelty = 1 - redundancy`

---

## 合分规则

### Step 1. 先算解释性总分

```text
novelty = 1 - redundancy
primacy_num = map(primacy)
authority_num = map(authority)
conflict_num = map(conflict)

composite_score =
  round(100 * (
    0.22 * confidence +
    0.20 * strength +
    0.14 * citation_completeness +
    0.12 * coverage +
    0.10 * recency +
    0.08 * primacy_num +
    0.08 * authority_num +
    0.06 * conflict_num +
    0.05 * novelty
  ))
```

解释:
- `confidence + strength + citation_completeness` 权重最高,因为这是能不能写进报告的核心
- `coverage + recency` 决定它是不是“站得住且不过时”
- `primacy + authority + conflict + novelty` 负责校正

### Step 2. 再走硬规则

`composite_score` 再高,只要命中硬规则,也不能直接进高 Tier。

---

## 4 Tier 决策路由

### Tier 0 — 硬性剔除

任一条命中即剔除:

- `citation_completeness < 0.5`
- `selection = exclude`
- `redundancy = 1.0`
- `primacy = tertiary` 且没有更高级来源支持同一 claim

### Tier 1 — 高置信,自动接纳

必须全部满足:

- `composite_score >= 75`
- `confidence >= 0.8`
- `strength >= 0.7`
- `conflict = none`
- `citation_completeness >= 0.7`
- `selection = include`

### Tier 2 — 中置信,接纳但标注

不满足 Tier 1,但全部满足:

- `composite_score >= 50`
- `confidence >= 0.5`
- `conflict in {none, partial}`
- `citation_completeness >= 0.5`
- `selection = include`

### Tier 3 — 低置信 / 高冲突,必须人工复核

其余情况全部进入 Tier 3,典型包括:

- `selection = uncertain`
- `composite_score < 50`
- `confidence < 0.5`
- `conflict = contradictory`

---

## 路由顺序

为了避免歧义,顺序固定为:

```text
Tier 0 hard filters
  -> Tier 1 high confidence
  -> Tier 2 medium confidence
  -> Tier 3 everything else
```

也就是说:
- 先看能不能直接剔除
- 再看够不够格直接接纳
- 再看能不能带警告接纳
- 剩下的全进人工复核

---

## 评分样例

输入证据:

```yaml
id: E-007
claim: RAG 系统在多跳问答上比微调模型更鲁棒
quote: "We observe RAG outperforms fine-tuned baselines on HotpotQA by 4.2 EM..."
source:
  ref: "https://arxiv.org/abs/2305.xxxxx"
  locator: "Section 5.2, Table 3"
extracted_at: 2026-05-03T07:40:00Z
```

主 skill 自动打分:

```yaml
score:
  confidence: 0.85
  selection: include
  redundancy: 0.2
  strength: 0.9
  primacy: primary
  recency: 1.0
  authority: high
  coverage: 0.6
  conflict: none
  citation_completeness: 1.0
  composite_score: 85
  rationale:
    - "原始论文 + 明确表格定位,回链完整"
    - "公开 benchmark,论证强度高"
    - "另有 2 个独立源支持同方向结论"
tier: 1
```

为什么是 Tier 1:

- 没命中 Tier 0
- `composite_score = 85 >= 75`
- `confidence / strength / citation_completeness` 都达线
- 无冲突

---

## 评分如何被使用

1. Stage 4 `extract` 时调 `atoms.score(evidence)` 打分
2. Stage 5 `synthesize` 时按 Tier 决定是否进报告、是否加警告
3. Stage 6 `review` 时汇总 Tier 分布,输出复核意见

---

## 哪些改动最危险

| 改动 | 风险 |
|---|---|
| 改 10 维字段名 | 会直接破坏 `evidence_score` 契约 |
| 改枚举集合 | 会影响子包 prompt、打分解释和 review 模板 |
| 改权重 | 会改变 `composite_score` 分布,需要重校准 |
| 改 Tier 阈值 | 会改变大量证据的接纳边界 |

原则:
- V1 允许补 `rationale` 模板和领域 recency 规则
- V1 不建议改 10 维集合和 4 Tier 顺序

---

## 当前阶段

V1 仍然是接口 + 规则文档,还没有真实评分代码。四个子模板包样板已经落地;后续只要真实运行能稳定产出 `evidence_score` 和 `tier`,就算通过第一轮验证。

---

## 抄哪儿(明示)

- **MetaScreener**: 4 Tier decision router、calibrated confidence 思路
- **claude-scholar / asreview**: 置信度分层 + 不确定条目人工复核
- **V3 共识 §5**: 学术综述类的纳排标准、PICO/PECO/SPIDER
