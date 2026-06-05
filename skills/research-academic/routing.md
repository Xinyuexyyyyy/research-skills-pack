# Routing — 学术 router 二级路由细则

> 本文件回答 1 件事:**用户给一个学术调研请求,本 router 怎么把它转交给 `academic-deep-research`（入口层）**。

## 1. 路由原则（已变更）

- 一级路由(`research-base/router.md`)负责"是不是学术"
- 二级路由(本 router)负责"转入学术入口层"
- **所有学术请求统一先进 `academic-deep-research`**,由它做意图澄清后再分发到具体下游 skill
- 本 router 不再逐条判断 discovery / screening / reading / writer,分发决策交给入口层

## 2. 默认路由

所有命中 `research-academic` 的请求 → 转入 `academic-deep-research`。

`academic-deep-research` 的 Round 1 会做：
1. 意图清晰 → 直接分发到 `paper-discovery` / `paper-screening` / `paper-reading` / `survey-writer`
2. 意图模糊 → 澄清后分发
3. 开放/决策问题 → 继续走深度调研 Round 2-4

## 3. 保留：各下游 skill 的命中信号（供入口层参考）

以下信号表仍然有效,但不再由本 router 直接判断,而是作为 `academic-deep-research` Round 1 的参考依据。

### → `paper-discovery`

| 信号 | 例子 |
|---|---|
| 关键词 | 找论文、检索、搜文献、导入、候选池、references.bib、查 arxiv、查 semantic scholar、scrape |
| 工件状态 | 用户**没有** `candidate_papers.csv` |
| 输入形态 | 给出 research question / keywords / 时间窗 / 种子论文 / DOI 列表 |
| 输出诉求 | "建立候选池""把相关论文找全" |

### → `paper-screening`

| 信号 | 例子 |
|---|---|
| 关键词 | 纳排、筛选、PRISMA、systematic review、scoping review、criteria、PICO、PECO、SPIDER、include/exclude |
| 工件状态 | 用户**已有** `candidate_papers.csv`,要决定哪些进入下一步 |
| 输入形态 | 给出 review_type、PICO 维度、include/exclude 规则 |
| 输出诉求 | "列出谁纳入谁排除""画 PRISMA flow""留 audit trail" |

### → `paper-reading`

| 信号 | 例子 |
|---|---|
| 关键词 | 读论文、全文问答、证据抽取、比较、矛盾、citation 卡片、单篇精读、做笔记、逐篇整理 |
| 工件状态 | 用户已有 `study_selection.csv` 中的 `included` 集 |
| 输入形态 | 抽取字段、问题列表 |
| 输出诉求 | `paper_notes/`、`evidence_table.csv`、`comparison_matrix.csv`、单篇导读报告 |

**重要**：命中 `paper-reading` 不代表后续一定进入 `survey-writer`。

### → `survey-writer`

| 信号 | 例子 |
|---|---|
| 关键词 | 写综述、写 related work、research gaps、future work |
| 工件状态 | 用户已有 `evidence_table.csv` / `comparison_matrix.csv` |
| 输入形态 | 叙述风格(theme / timeline / method family) |
| 输出诉求 | `literature_review.md` / `related_work.md` / `research_gaps.md` |

### → `academic-deep-research`（继续深度调研）

| 信号 | 例子 |
|---|---|
| 关键词 | 领域扫描、跨主题、学术+网页混合、deep research、领域格局 |
| 工件状态 | 没有现成候选池,问题非常开放 |
| 输入形态 | 决策问题 + 范围 + 时间窗 + 是否允许网页源 |
| 输出诉求 | 多源 brief + subreports + 报告 |

## 4. 子类型识别（仍由入口层负责）

无论分发到哪个下游,入口层都要给一个 `academic_subtype`,供下游知道目标产物的形态:

| subtype | 触发 | 影响 |
|---|---|---|
| `literature_review` | 默认 | 综述写作走标准 theme/方法谱系 |
| `systematic_review` | 用户提到 PRISMA / 严格纳排 / 可复现协议 | screening 必须出 PRISMA flow + audit |
| `scoping_review` | 用户说"先扫一下范围""scoping" | screening 不强求纳排深度,允许快速分类 |
| `sota` | 用户说 SOTA / state of the art / 当前最佳 | discovery + screening 强 recency 过滤 + timeline |
| `gap_finding` | 用户说 research gap / 未解问题 | research_gaps.md 至少 5 条 |
| `unknown` | 不能定 | 反问澄清 |

## 5. 让位规则(命中本 skill 但应转出)

- 任务核心是产品决策 → 退回一级路由,转 `research-comprehensive`
- 任务核心是 GTM / 价格 / 竞品 → `research-competitive`
- 任务核心是用户痛点 / PRD / MVP → `research-discovery`

## 6. 反问澄清

本 router 不再直接反问用户。反问由 `academic-deep-research` Round 1 负责。

## 7. routing_decision.json 字段约定

```json
{
  "matched_layer1": "research-academic",
  "matched_layer2": "academic-deep-research",
  "entry_action": "dispatch | continue_deep_research",
  "dispatch_to": "paper-discovery | paper-screening | paper-reading | survey-writer | null",
  "academic_subtype": "literature_review | systematic_review | scoping_review | sota | gap_finding | unknown",
  "domain_hint": "ml | nlp | cv | medicine | hci | none",
  "confidence": 0.0,
  "reason": "...",
  "alternatives": []
}
```

## 8. 显式覆盖

用户在输入里强制指定时,显式覆盖优先级最高:

- "做个 systematic review of X with PRISMA" → 经入口层,强制 subtype=systematic_review,分发到 discovery/screening
- "我已经有了候选 csv,帮我做纳排" → 经入口层,直接分发到 paper-screening
- "我已经筛完了,帮我逐篇读并整理成证据表/对比表" → 经入口层,直接分发到 paper-reading
- "我已经有 evidence_table.csv,直接写成综述/related work/gaps" → 经入口层,直接分发到 survey-writer

显式覆盖时入口层仍需经过 Round 1,但可以跳过澄清直接分发。
