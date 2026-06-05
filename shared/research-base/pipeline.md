# Default Pipeline — 默认 6 段管线

## 总览

```
clarify → retrieve → screen → extract → synthesize → review
  澄清     检索        筛选     提取       综合         复核
```

每段都是**钩子点**。子模板包按需覆盖任何一段或全部,未覆盖则用默认行为(主 skill 提供)。

钩子接口签名见 `hooks.md`。原子工具见 `atoms.md`。

---

## Stage 1 — Clarify(澄清)

**做什么**:把模糊问题变成可调研问题。

**默认行为**:
- 抽出输入里的"关键名词、范围、时间窗、目标输出形态"
- 缺任一项就反问用户(一次只问 1 个最关键的,抄 `product-idea-excavator` 的"一次只问一个强问题")
- 输出标准化 `clarified_question.json`

**输入**:用户原始输入(任意自然语言)
**输出**:`clarified_question` — 含 topic / scope / time_window / output_form / constraints

**典型钩子覆盖**:
- 学术包:补 PICO/PECO/SPIDER 维度
- 产品发现包:走 5 轮深度访谈而不是只问一次

---

## Stage 2 — Retrieve(检索)

**做什么**:按渠道获取一手材料。

**默认行为**:
- 调用 `atoms.web_fetch` / `atoms.web_search` 等原子工具
- 渠道默认通用(搜索引擎 + 公开网页)
- 每条结果落 `source_log.csv`(必须含 url / title / fetched_at / source_type)
- 完整原文 / 截图 / PDF 必须另存并回填 `artifact_ref`

**输入**:`clarified_question`
**输出**:`raw_materials` — 列表,每项至少含 {material_id, source_type, url, content_snippet, fetched_at, artifact_ref}

**典型钩子覆盖**:
- 学术包:替换为 arXiv / Semantic Scholar / Crossref / OpenAlex 等
- 竞品包:替换为 G2 / Capterra / Wayback / 招聘页 / Reddit
- 产品发现包:替换为内部 input(用户故事、销售反馈)+ 轻外部验证

---

## Stage 3 — Screen(筛选)

**做什么**:按纳排标准过滤材料。

**默认行为**:
- 默认筛选规则:去重 + 排除明显无关 + 排除回链不全的
- 每条材料标 include / exclude / uncertain
- uncertain 走人工复核(标注后转 include 或 exclude)

**输入**:`raw_materials` + `criteria`(默认通用,子包可改)
**输出**:`filtered_materials`,标注 `selection` 状态

**典型钩子覆盖**:
- 学术包:PICO/PECO/SPIDER + active learning(抄 MetaScreener)
- 竞品包:Direct / Adjacent / Status quo / Manual workaround 分层
- 综合包:按"决策问题"过滤,而非通用相关性

---

## Stage 4 — Extract(提取)

**做什么**:从筛选后的材料里抽出结构化证据。

**默认行为**:
- 每条材料抽 1-N 条 `evidence_record`
- evidence_record 标准字段:claim / source / quote / context / extracted_at
- 自动调 `atoms.score()`(见 `scoring.md`)给每条生成 `score + tier`

**输入**:`filtered_materials`
**输出**:`evidence_records` — 列表,每条已带 `score.composite_score` 和 `tier`

**典型钩子覆盖**:
- 学术包:抽 method / dataset / metric / result / limitation
- 竞品包:抽 feature / pricing / sentiment / GTM signal
- 产品发现包:抽 user pain / current workaround / evidence of demand

---

## Stage 5 — Synthesize(综合)

**做什么**:把证据整合成最终输出物。

**默认行为**:
- 按子模板包提供的 `report-template.md` 骨架填充
- 每条结论必挂引用回链
- Tier 3(低置信 / 高冲突)证据单独标注 ⚠

**输入**:`evidence_records` + `report_structure`
**输出**:`draft_report`(Markdown / 多文件包)

**典型钩子覆盖**:
- 学术包:综述 + evidence_table + research_gaps + references.bib
- 竞品包:competitive_matrix + battle_cards/ + pricing_landscape
- 综合包:按"决策问题"组织,evidence_matrix + tradeoff_brief

---

## Stage 6 — Review(复核)

**做什么**:自检和验证。

**默认行为**:
- 跑评分引擎汇总:多少条 Tier 0/1/2/3?
- 检查每条结论是否有引用回链
- 检查冲突证据是否被显式处理
- 输出 `review_notes.md`,列出遗漏 / 风险 / 建议补充

**输入**:`draft_report` + `evidence_records`
**输出**:`verified_report`(若复核通过)或 `review_notes`(列出问题)

**典型钩子覆盖**:
- 学术包:加 PRISMA flow 图、引用合规性检查
- 综合包:加 conflict_log.md,显式列冲突证据

---

## 钩子覆盖优先级

```
子模板包钩子(若提供) > 默认管线行为
```

子包不提供钩子 = 用默认行为,**不需要任何额外代码**。

钩子接口签名见 `hooks.md`。
