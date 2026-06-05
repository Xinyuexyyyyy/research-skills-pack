# Routing — 学术包命中条件

## 命中决策

满足以下**任一**即命中本包(在 `research-base/router.md` 主路由表内):

### A. 关键词命中
- 中文:综述、文献综述、文献、文献调研、研究空白、SOTA、survey、研究综述
- 英文:literature review / systematic review / meta-analysis / scoping review / state of the art / research gap / survey / PICO / PECO / SPIDER

### B. 渠道命中
- 用户提到 arXiv / Semantic Scholar / PubMed / OpenAlex / Crossref / DBLP / ACL Anthology / NeurIPS / ICML / ACL / EMNLP / NAACL / CVPR / ICCV / ECCV

### C. 输出形态命中
- "请给我一份综述""帮我整理这领域的研究进展"
- "evidence table""research gap"
- 要 references.bib / 要按主题分组

### D. 用户显式指定
- "用学术综述方式""systematic review 流程""PRISMA"

---

## 不命中(让位给其他包)

- 任务核心是产品决策 → comprehensive
- 任务核心是 GTM / 价格 / 竞品 → competitive
- 任务核心是用户痛点 / PRD / MVP wedge → discovery

---

## 冲突处理

### 学术 + 决策(混合)
- 由 router 给 comprehensive,comprehensive 在内部**子调用**学术包做文献部分,本包只产出"学术片段",不产综述全文。

### 学术 + 时效极强(前沿动态)
- 仍走学术,但 `recency` 维度严格;`time_window` 默认 24-36 个月。

### 学术 + 法规 / 政策
- 默认仍走学术,但 hook_extract 多抽一条 `legal_status`(可选,放 custom)。

---

## routing_decision 输出补充

router 输出 `routing_decision.json` 时,若 matched=`research-academic`,本包要求附加字段:

```json
{
  "academic_subtype": "survey | systematic_review | scoping_review | sota | gap_finding",
  "domain_hint": "ml | nlp | cv | medicine | hci | ...",
  "preferred_databases": ["arxiv", "semantic_scholar", "openalex"]
}
```

`academic_subtype` 影响后续 hook_synthesize 的骨架选择:
- `systematic_review` 必出 PRISMA flow
- `sota` 必出 timeline.md
- `gap_finding` research_gaps.md 至少 5 条

---

## 显式覆盖

用户在输入里说:
- "用学术综述方式调研 X" → 强制本包
- "systematic review of X with PRISMA" → 强制本包,subtype=systematic_review
- "做个 SOTA 综述" → 强制本包,subtype=sota

显式覆盖优先级最高,绕过自动判断。
