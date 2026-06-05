# Report Template — 学术综述输出骨架

最终产物 = 一个目录,内含**1 份主报告 + 若干检索/分析附录**。对人类读者,默认入口应当是 `final_report.md`; 其他文件主要用于复核和追证据。如果只有成文层,那只是带引用概述,不是完整文献综述。

## 目录结构

```
{run_dir}/
├── final_report.md         # 默认给人看的总报告: 先读这个
├── research_question.md     # 研究问题、范围、review_mode
├── search_queries.md        # 每轮检索 query / db / filters / hit counts
├── criteria.json            # 纳排标准
├── study_selection.csv      # 候选、去重、纳排、排除理由
├── paper_notes/             # 每篇入选论文的逐篇笔记
├── comparison_matrix.csv    # 跨论文结构化比较
├── theme_outline.md         # 主题、谱系、争议和章节大纲
├── literature_review.md     # 综述主文,不是逐篇摘要,而是跨论文综合
├── reader_guide.md          # 给非专业读者的导读版解释
├── evidence_table.csv       # 每条 evidence_record 一行,带 score + tier
├── research_gaps.md         # 未解决问题 / 矛盾点 / 推荐研究方向
└── references.bib           # BibTeX 库,所有被引用的论文
```

可选扩展(按 `academic_subtype` 加):
- `prisma_flow.md` —— `systematic_review` 必出
- `timeline.md` —— `sota` 必出
- `missing_papers.md` —— 找到但没拿到全文的论文

## 阅读约定

- `final_report.md`:
  - 主报告。把综述结论、给非专业读者的解释、研究空白和下一步建议串成一份连续文本。
- `literature_review.md`:
  - 专业读者版正文。
- 其余文件:
  - 附录 / 工作底稿 / 复核材料。默认不该逼读者逐个打开。

## 落盘约定

- 结果包目录:
  - `./research/{run_dir}/`
- 主报告复制路径:
  - `$CONTENT_DIR/search_report/{run_dir}.md`

---

## adequacy gate

下面这些条件没过时,最终产物最多只能叫:
- `quick_review`
- `scoping_note`

不能叫正式 `literature_review`:

- included papers < 12
- 全文可得比例 < 0.8
- 独立主题 < 3
- 没有 `study_selection.csv`
- 没有 `paper_notes/`
- 没有 `comparison_matrix.csv`
- 没有 `theme_outline.md`

---

## 1. research_question.md

```markdown
# Research Question

- Topic:
- Core question:
- Why this matters:
- Time window:
- Review mode: literature_review / systematic_review / scoping_review / sota / quick_review
- Scope included:
- Scope excluded:
```

---

## 2. search_queries.md

```markdown
# Search Queries

## Round 1 — initial recall
- DB: OpenAlex
- Query:
- Filters:
- Hits:

## Round 2 — gap-driven expansion
- What gap was observed:
- DB:
- Query:
- Hits:
```

---

## 3. criteria.json

```json
{
  "include": ["..."],
  "exclude": ["..."],
  "uncertain_policy": "human review",
  "dedup_key": ["doi", "arxiv_id", "canonical_title"]
}
```

---

## 4. study_selection.csv schema

```csv
material_id,title,db,year,fulltext_available,selection,selection_reason,theme_guess,duplicate_of
M-001,Paper A,openalex,2025,true,include,"multi-hop RAG with full evaluation",retrieval-control,
```

---

## 5. paper_notes/

每篇 included paper 一份笔记,必须是**逐篇读后卡**,不是 metadata dump。

```markdown
# {paper title}

## 1. What problem does it solve?
## 2. Method
## 3. Data / benchmark
## 4. Key numbers
## 5. Why it is new
## 6. Limitations
## 7. Relation to other papers
## 8. Candidate themes
```

---

## 6. comparison_matrix.csv schema

```csv
material_id,paper_title,year,method_family,retrieval_strategy,reasoning_strategy,datasets,main_metric,claimed_gain,limitations,theme
M-001,Paper A,2025,graph-rag,subgraph retrieval,logic pruning,HotpotQA,F1,+3.2,"needs KG quality",graph-based
```

---

## 7. theme_outline.md

在写正文前,先把分析结构写出来。

```markdown
# Theme Outline

## Theme 1 — ...
- Representative papers:
- What these papers agree on:
- What they disagree on:
- What changed over time:

## Theme 2 — ...

## Comparison claims that must appear in final review
- Claim A:
- Claim B:
- Claim C:
```

---

## 8. literature_review.md 骨架

```markdown
# {主题} 综述({time_window})

## 1. 范围与方法
- 调研问题(PICO/PECO/SPIDER)
- 检索数据库 + 关键词 + 时间窗
- 纳排标准
- 检索数 / 去重后 / 入选数(对应 PRISMA 的四档)
- 本次是否通过 adequacy gate

## 2. 主题分组
按 hook_synthesize 的聚类结果,每个主题一个 H2:
- 该主题的代表工作(每条挂引用 [E-XXX],至少 2 篇)
- 方法主线 / 数据集 / 关键指标
- 该路线相对其他路线的优势与短板
- 主要分歧 / 反例 / 失败模式

## 3. 时间线(可选,sota 必出)
按年/季画演进图,标关键拐点。

## 4. 方法比较
- 至少 1 张按方法家族组织的文字比较
- 明确"哪些方法解决了什么问题,代价是什么"

## 5. 共识与分歧
- 已被多源验证的共识(Tier 1 + Tier 2 多源)
- 强冲突点(`conflict=contradictory` 单独列)
- 哪些结论只在特定 benchmark 成立

## 6. 研究空白(指 research_gaps.md)

## 7. 限制声明
- 本综述未覆盖的子方向
- 检索时间窗的影响
- 全文不可获取的论文比例
- 可能的数据库 / venue 偏倚
```

---

## 9. final_report.md 骨架

```markdown
# {主题} 调研总报告

## 1. 先说结论
- 这个方向当前最重要的判断

## 2. 这件事到底是什么
- 面向非专业读者解释核心对象

## 3. 最近两年的主要进展
- 主题化总结,不是逐篇论文罗列

## 4. 哪些结论已经比较稳
- 写清共识

## 5. 哪些地方还没研究清楚
- 直接整合 `research_gaps.md`

## 6. 如果你是研究者 / 产品人,这意味着什么
- 分角色讲影响

## 7. 想深挖时再看什么
- 指向 `literature_review.md`
- 指向 `comparison_matrix.csv`
- 指向 `paper_notes/`
```

---

## 10. reader_guide.md 骨架

这份文件默认写给:
- 小白
- 跨领域读者
- 只想先理解"这事到底怎么回事"的人

```markdown
# 这份调研在讲什么

## 1. 一句话结论
- 用最短的话说明这个方向现在发展到哪了

## 2. 这是什么
- 先解释核心对象是什么
- 避免默认读者已经懂术语

## 3. 为什么重要
- 它解决什么真实问题
- 如果不解决会怎样

## 4. 现在大家主要怎么做
- 路线 A: 是什么 / 怎么做 / 优点 / 缺点
- 路线 B: 是什么 / 怎么做 / 优点 / 缺点
- 路线 C: ...

## 5. 进展到哪了
- 过去两年最大的变化是什么
- 哪些问题已经明显改善
- 哪些问题还只是阶段性结果

## 6. 现在还没解决什么
- 把 research gaps 用人话重写
- 直接解释"研究空白 = 还没被研究清楚的问题"

## 7. 如果你只记 3 件事
- 1.
- 2.
- 3.
```

要求:
- 每节先讲"是什么",再讲"为什么",最后讲"意味着什么"
- 可用术语,但术语第一次出现必须顺手解释
- 禁止把这一份写成正文的压缩复述

---

## 11. evidence_table.csv schema

```
id,material_id,claim,quote,paper_title,authors,year,venue,doi,score_composite,tier,confidence,strength,primacy,recency,authority,coverage,conflict,citation_completeness,tags
E-001,M-...,...,...,...,...,...,...,...,85,1,0.85,0.9,primary,1.0,high,0.6,none,1.0,"method;rag;benchmark"
```

字段对齐主 skill `evidence_record` schema,**不新增字段**,只展开 `score.*`。

---

## 12. research_gaps.md 骨架

`research_gaps.md` 不只是列空白,还要解释**为什么这算空白**、**对谁有影响**。

```markdown
# Research Gaps — {主题}

## 先解释这个词是什么意思
- 研究空白 = 这个方向里,大家还没研究清楚、还没比较明白、或者还缺强证据的地方

## A. 未覆盖的子方向
- [Gap-1] 是什么:
- 为什么算空白:
- 如果补上,会帮助谁:
- 目前证据来自:

## B. 矛盾未解决
- [Gap-2] 冲突点是什么:
- 为什么现在还没法下定论:
- 需要什么证据来解决:

## C. 实证不足的主张
- [Gap-3] 现在有人怎么说:
- 为什么证据还不够:
- 下一步最该补什么实验 / 比较:

## D. 推荐研究方向(按可行性排序)
1. ...
```

---

## 12. references.bib 规范

- 每条 `evidence_record.source.ref` 都对应一个 BibTeX entry
- 主键命名:`{firstauthor}{year}{firstword}` 全小写
- arXiv 用 `@misc { ..., archivePrefix={arXiv}, eprint={...} }`
- 期刊会议用对应 `@article` / `@inproceedings`

示例:

```bibtex
@misc{lewis2020retrieval,
  title={Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks},
  author={Lewis, Patrick and others},
  year={2020},
  archivePrefix={arXiv},
  eprint={2005.11401}
}
```

---

## 13. 复核要求(对接 hook_review)

提交前必须自检:
- [ ] `research_question.md`、`search_queries.md`、`criteria.json`、`study_selection.csv` 已落地
- [ ] `paper_notes/` 非空,且每篇 included paper 都有笔记
- [ ] `comparison_matrix.csv` 和 `theme_outline.md` 已完成
- [ ] 每条 H2/H3 结论都有 [E-XXX] 引用
- [ ] `reader_guide.md` 已完成,且不是正文压缩版
- [ ] evidence_table.csv 的 id 和 .bib 的 key 一一对应
- [ ] research_gaps.md 至少 3 条 Gap
- [ ] Tier 3 证据未直接进入综述主文(只能在 research_gaps 提及)
- [ ] 正文不是逐篇摘要堆叠,而是跨论文比较后的综合
- [ ] systematic_review 子类型必须附 prisma_flow.md
- [ ] sota 子类型必须附 timeline.md
