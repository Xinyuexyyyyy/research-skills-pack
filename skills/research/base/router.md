# Router — 自动路由规则

## 路由原则

主 skill 根据用户输入,**自动判断**调用哪个子模板包。判断只发生一次,在 Stage 1 (clarify) 之后、Stage 2 (retrieve) 之前。

不命中任何特定类型 → fallback 到 `research-comprehensive`(综合类)。

路由目标不是“猜得越花越好”,而是把问题稳定送进**一个主包**。除 `research-comprehensive` 的跨包子调用外,顶层不要同时起多个主包。

---

## 判定流程

```
用户输入
   ↓
Stage 1: Clarify(完成 clarified_question 后)
   ↓
Router 判断
   ↓
┌─────────────┬──────────────────────────────────┐
│ 命中类型      │ 调用                              │
├─────────────┼──────────────────────────────────┤
│ 学术综述      │ research-academic                │
│ 竞品市场      │ research-competitive             │
│ 产品发现      │ research-discovery               │
│ 多类混合 / 不确定 │ research-comprehensive (fallback) │
└─────────────┴──────────────────────────────────┘
```

判断方式:**用户显式声明 + 任务结构 + 关键词**,三者综合。

优先级固定如下:
1. 用户显式声明
2. 任务结构
3. 关键词

不要只因为一句模糊关键词,就把整题送错包。

---

## 路由表

### 1. 命中 `research-academic`(学术综述)

**关键词**:
- 中文:综述、文献综述、学术、论文、研究空白、引用、文献、研究、survey
- 英文:literature review、systematic review、meta-analysis、state of the art、survey、research gap、PICO、PECO、SPIDER

**任务结构**:
- 输出形态是"综述 / evidence table / research gaps"
- 输入提到"找论文""arxiv""pubmed""semantic scholar"

### 2. 命中 `research-competitive`(竞品市场情报)

**关键词**:
- 中文:竞品、对手、市场、价格、定价、评价、评论、用户反馈、招聘、融资、增长、GTM、战卡
- 英文:competitor、competitive、market、pricing、battle card、GTM、go-to-market、reviews、Capterra、G2

**任务结构**:
- 要求列出 X 的对手 / 替代方案 / 竞争格局
- 涉及"价格表 / feature 矩阵 / 用户评价 / 增长信号"

### 3. 命中 `research-discovery`(产品发现)

**关键词**:
- 中文:想法、idea、挖一下、产品发现、需求、痛点、PRD、MVP、用户访谈
- 英文:idea、discovery、MVP、PRD、user interview、problem definition、user pain、wedge

**任务结构**:
- 输入是"我有个想法,你帮我挖挖"
- 输出形态是 idea brief / discovery notes / PRD / MVP wedge

### 4. Fallback `research-comprehensive`(综合类)

命中条件(任一):
- **多类型混合**:同时命中以上 ≥2 类(如"学术 + 市场",决策级问题)
- **决策导向**:"X 值不值得做""要不要做""怎么选"
- **不命中以上任何一类**:任何调研需求,默认走综合类

## Tie-break 规则

当多个包同时命中时,按下面规则裁决:

1. 明确要论文、综述、学术证据优先 `academic`
2. 明确要竞品集合、价格带、评论、市场格局优先 `competitive`
3. 明确要定义问题、缩 MVP、列假设、做验证计划优先 `discovery`
4. 如果用户真正要回答的是“值不值得做 / 该怎么选 / 混合多类证据”,优先 `comprehensive`

一句话记忆:
- 单一专门问题 → 去专门包
- 决策题、混合题、不稳定题 → 去综合包

---

## 三档触发条件(决定要不要进 skill)

> 抄 `legal-research-skill` 三档分流。

### 高优先级(必须触发本 skill)
- 明确说"调研""研究""综述""systematic review""综述"
- 明确说"对比 X 和 Y""比较产品""竞品分析"
- 明确说"挖一下这个想法""做产品发现"
- "看看现在 / 业内 / 市场 / 学术界 X 的现状"

### 中优先级(结合上下文)
- "了解一下 X""X 怎么样""有什么参考"
- 用户给出开放问题,需要外部信息才能答

### 不触发
- 仅询问名词解释 / 概念
- 仅要求生成内容(写文章、起标题)无外部信息需求
- 仅是已明确的代码任务

如果只是“先给我大概讲讲”,默认先给轻量概览,不要自动升级成完整调研。

---

## 显式覆盖

用户可以在输入里**强制指定**类型,绕过自动判断:

```
"帮我用学术综述方式调研 RAG 的最新进展"  → 强制 research-academic
"用综合类做一下 AI Code 方向的决策"       → 强制 research-comprehensive
```

显式覆盖优先级最高。

但即使显式覆盖,如果用户问题本身仍然太散,也要先做 clarify,不能跳过缩边界。

---

## 路由失败兜底

如果三种特定类型都不像,但触发条件命中 → 直接走 `research-comprehensive`,**不要拒绝**。综合类的存在就是为了兜底。

---

## 路由判断输出

router 必须输出 `routing_decision.json`:

```json
{
  "matched": "research-academic",
  "confidence": 0.85,
  "reason": "用户输入含 'literature review' 和 'arxiv',输出形态是综述",
  "fallback_used": false,
  "alternatives": ["research-comprehensive"]
}
```

`alternatives` 列出次高分,供子包内部需要跨包补充时使用(综合类调用时常用)。

补充约束:
- `reason` 必须同时引用至少一个“任务结构”或“显式声明”,不能只写关键词命中
- `confidence < 0.7` 时,默认进入“检查点 2: 路由确认”
- `fallback_used=true` 时,必须说明为什么三个专门包都不够贴

---

## 跨包协作约定(V1)

综合类作为 fallback,常常需要**调起其他子包的能力**(查学术 + 查市场 + 查需求)。

V1 约定如下:
- 只有 `research-comprehensive` 可以发起跨包子调用
- 子调用只跑被调用包的 `hook_retrieve` / `hook_extract`,不接管其 `hook_synthesize` / `hook_review`
- 片段协议、预算字段、partial 返回格式统一以 `research-comprehensive/channels.md` § "跨包子调用" 为准

本文件只负责"顶层路由到哪个包"。一旦 matched=`research-comprehensive`,包内再决定是否切片、是否子调用其他包。
