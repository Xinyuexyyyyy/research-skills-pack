---
name: survey-writer
description: 基于 evidence_table.csv 写学术综述 / Related Work / Research Gaps / Future Work。接收 paper-reading 的结构化证据，按学术标准生成综述文本，支持按主题聚类、方法对比、脉络梳理、空白识别。触发词：写综述、related work、research gaps、future work、literature review、综述写作。
status: stable
---

# Survey Writer — 学术综述写作

## 一句话定位

把 `evidence_table.csv` 变成学术综述文本。**只做写作编排**，不做检索、不做纳排、不做证据抽取。

## 上层契约

- 父级:`research-academic`(router) → `research-base`(工具层)
- 进入条件:`research-academic/routing.md` 把任务定为 `matched_layer2=survey-writer`,且**已有合格 `evidence_table.csv`**
- 离开条件:按调用模式产出合格的综述包（见下方“交付模式与完成定义”）
- 共享 schema:严格遵守 `research-base/artifacts.md` 的 `evidence_table.csv`(只读)

## 综述类型

| 类型 | 触发词 | 长度 | 用途 |
|---|---|---|---|
| **literature_review** | "写文献综述""做个 survey" | 3000-8000 字 | 独立文献综述 |
| **related_work** | "写 related work""相关工作" | 1000-3000 字 | 放在论文里的章节 |
| **research_gaps** | "研究空白""gaps""还有什么没做" | 800-2000 字 | 识别未被充分研究的方向 |
| **future_work** | "未来方向""future work" | 500-1500 字 | 基于 gap 提出下一步建议 |

默认类型：`literature_review`。用户没指定时，先反问确认。

## P0 边界

### 做什么
- ✅ 读取 `evidence_table.csv`，按主题/方法/年份分组
- ✅ 提取每篇论文的核心贡献（`contributions` 字段）
- ✅ 按主题聚类，识别研究脉络（谁→谁→谁的延伸关系）
- ✅ 对比不同方法，突出差异（表格 + 文字）
- ✅ 识别 gap（已有方法未覆盖的场景、未被验证的假设）
- ✅ 生成结构化综述文本（带章节标题、过渡句、小结）
- ✅ 每条引用都挂 `paper_uid`，产出 `citation_table.csv`
- ✅ `qualitative_only=true` 的论文只作定性观点，不作定量证据
- ✅ `extraction_confidence=low` 的论文标注"低置信"

### 不做什么
- ❌ 重新检索/扩候选（paper-discovery 的事）
- ❌ 重新纳排/改 selection（paper-screening 的事）
- ❌ 重新读论文/补抽取（paper-reading 的事）
- ❌ 编造不存在的引用或数据
- ❌ 把 `pending_fulltext.csv` 中的论文写进综述

## 写作方法论：人类写综述的精髓

> 综述不是"论文摘要的串联"，而是**用论文当砖块，砌出一条有论证力的故事线**。核心是"讲一个关于这个领域的故事"——它从哪来、现在在哪、要去哪。

### 核心原则：叙事先行

动笔前，先确定**综述的核心论点**（thesis）。所有内容都围绕这个论点展开。

| 不是... | 而是... |
|---|---|
| "这个领域有很多方法" | "这个领域正在从试错法向 AI 驱动设计转型，但物理约束的引入仍不成熟" |
| "论文A做了X，论文B做了Y" | "尽管X和Y在各自场景有效，但它们共同忽视了Z这一关键约束" |

**确定核心论点的方法**：
1. 看 evidence_table 中**最频繁出现的关键词/方法**
2. 看 **年份分布**：近几年密集出现的是什么方向？
3. 看 **矛盾点**：哪些论文的结论相互冲突？冲突往往意味着核心论点

---

### Step 1: 故事弧映射（Story Arc）

不是按方法分类，而是画一条**领域发展线**：

```
[起源] 谁最早提出了这个核心思路？
    ↓
[发展] 这个思路被怎么扩展、改进、挑战？
    ↓
[分岔] 出现了哪些不同的技术路线？它们为什么分歧？
    ↓
[融合] 最近有没有出现"把不同路线合起来"的尝试？
    ↓
[前沿] 现在最热的前沿是什么？有什么正在萌芽的方向？
```

**从 evidence_table 中提取故事弧**：
- `year` + `method` → 识别"什么时候出现了什么"
- `contributions` → 识别"谁在谁的肩膀上"
- `key_finding` → 识别"突破性的结果是什么"

---

### Step 2: 分组与脉络（不是分类，是叙事结构）

分组服务于**故事线**，不是服务于"整齐的类别"。

**分组原则**：
1. **时间递进组**：同一思路的演进（早期 → 中期 → 最新）
2. **竞争路线组**：解决同一问题的不同思路（路线A vs 路线B）
3. **应用场景组**：同一思路在不同场景的迁移（主场景 → 边缘场景）

**识别奠基工作**：
- 年份最早，提出了后来被反复引用的核心思路
- contributions 里说"首次提出XX框架"

**识别关键挑战者**：
- 直接反驳/质疑奠基工作的论文
- contributions 里说"与XX不同，我们发现..."
- 这类论文需要**深入批判**，不是一笔带过

---

### Step 3: 批判性综合（Critical Synthesis）

**不是描述，是评价**。

**批判性词汇表**：

| 中性表达 | 批判性表达 | 暗示 |
|---|---|---|
| "found that" | "reported that" | 只是报告，未必可靠 |
| "proposed" | "advocated" | 有立场，可能有偏见 |
| "used" | "adopted" / "employed" | 选择性的，可能不是最优 |
| "showed" | "claimed" | 声称，待验证 |
| "demonstrated" | "attempted to demonstrate" | 尝试证明，可能不成功 |

**综合句型模板**（不是 list-and-summarize）：

```
❌ Study A found X. Study B found Y. Study C found Z.

✅ Several studies have found that [pattern] (Author 1; Author 2), 
   although this finding is complicated by evidence that [nuance] (Author 3; Author 4).
   
✅ While early work focused on [early approach] (Author 1; Author 2), 
   recent efforts have shifted toward [new approach], driven by [reason] (Author 3; Author 4).
   
✅ [Method A] has been widely adopted for [scenario] (Author 1; Author 2); 
   however, its reliance on [assumption] has led researchers to explore [Method B] (Author 3).
```

---

### Step 4: 层次化递进（趋势预判 + 边界探索）

**章节内部不是并列，而是递进**。

**每节的结构**：

```
[段落 1：主线概述]
"这个方向的核心思路是什么"

[段落 2：演进脉络]
"从早期到近期的关键转变"

[段落 3：趋势提炼] ⬅️ 关键
"值得注意的是，该方向内部正出现向 XX 的明显趋势"
识别信号：
- 同一方法变体在 1-2 年内密集出现
- 从传统方法向某个新方法的大规模迁移
- 评估指标从单一向多维转变

[段落 4：边界探索] ⬅️ 关键
"该方向正在被拓展到 C、D 等相邻场景"
识别信号：
- population/scene 字段出现主场景之外的值
- 方法思路相同但应用领域不同的论文群

[段落 5：小结]
"这个方向的位置、优势、局限"
```

**趋势预判句型**：
- "值得注意的是，2023 年以来该领域出现了明显的范式转移..."
- "一个正在形成的共识是..."
- "与早期工作不同，最近的研究开始..."

**边界探索句型**：
- "除了上述主线工作，部分研究者开始将该思路应用于..."
- "该方法的适用范围正在从 XX 拓展到 YY..."
- "一个新兴的交叉方向是..."

---

### Step 5: 对比分析（批判性视角）

对比不是为了"谁更好"，而是为了**揭示不同选择背后的权衡**。

| 对比维度 | 问什么 |
|---|---|
| 核心思路 | 这个方法的本质假设是什么？ |
| 关键假设 | 它假设了什么条件？如果不成立会怎样？ |
| 优势场景 | 在什么情况下它表现好？为什么？ |
| 主要局限 | 作者自己承认了什么不足？有没有被低估的局限？ |
| 可扩展性 | 换个数据集/场景还能用吗？需要什么修改？ |

**对比表格示例**：

| 方法 | 核心思路 | 关键假设 | 优势场景 | 主要局限 |
|---|---|---|---|---|
| TabDDPM | 扩散模型生成表格数据 | 数据分布可学习 | 结构化数据生成 | **无物理约束** — 工程场景难以直接用 |
| CTGAN | 对抗生成网络 | 生成器和判别器能平衡 | 小型表格 | **训练不稳定**，工程约束难以编码 |
| Cooling-Guided DDPM | 扩散模型 + 物理引导 | 物理模型可近似 | 工程约束优化 | **泛化性未验证** — 仅验证单一电池类型 |

**对比后的批判性解读**：
> "上述对比揭示了一个核心张力：生成式方法（TabDDPM/CTGAN）擅长学习数据分布，但难以嵌入物理约束；而 Cooling-Guided DDPM 通过引入物理引导解决了这一问题，但其代价是方法的高度特化——从 2170 电池换到 4680 电池，整个框架需要重新训练。这一张力暗示了该领域的一个根本挑战：如何在'数据驱动'和'物理可解释'之间取得平衡。"

---

### Step 6: Gap 识别（从证据中推导，不是凭空想象）

**Gap 必须能从 evidence_table 的数据中推导出来**。

| Gap 类型 | 识别方法 | 示例 |
|---|---|---|
| **场景空白** | population 字段的覆盖范围 | "所有论文都在 2170 电池上验证，4680 大圆柱电池没人做" |
| **方法空白** | method 字段的组合缺失 | "扩散模型+物理引导有人做，但 GAN+物理引导、VAE+物理引导没人做" |
| **评估空白** | key_finding 的指标单一 | "所有论文只用温度一个指标，没考虑成本、寿命、制造可行性" |
| **理论空白** | hidden_assumptions 未验证 | "假设替代模型误差可忽略，但测试 R²=0.81 意味着 19% 方差未解释" |

**Gap 的表述格式**：
```
[Gap]：[具体空白]
[证据]：基于 evidence_table 中 N 篇论文的 XX 数据
[影响]：如果补上这个 gap，能带来什么价值
[为什么现在没人做]：是技术门槛、数据缺失、还是评估困难？
```

---

### Step 7: 过渡句设计（章节之间的逻辑连接）

**不是"第3章讲完了，第4章开始讲对比"**。

**而是**：
> "了解了各类方法的设计思路后，一个自然的问题是：它们在实际应用中的表现如何？更重要的是，它们在什么条件下会失效？接下来我们从方法对比转向评估维度的讨论。"

**过渡句模板**：
- "了解了 XX 后，一个自然的问题是..."
- "上述方法虽然在 XX 上有效，但面临 YY 挑战，因此研究者开始探索..."
- "然而，方法设计的差异只是问题的一面。在实际应用中，评估标准的选择同样关键..."
- "这些方法的发展揭示了一个更深层的趋势..."

---

### Step 8: 文本生成（按类型输出）

**literature_review 结构**（8 段式，每段服务核心论点）：
```
1. 引言（研究背景 + 核心论点预告）
2. 问题定义（为什么这个问题重要 + 现有方法的共同挑战）
3. 方法分类（按故事线分节，不是按方法字母顺序）
4. 方法对比（揭示核心张力/权衡）
5. 数据集与评估（评估标准的演进 = 另一个故事线）
6. 研究空白（从证据推导的 gap，每个 gap 都有"为什么现在没人做"的分析）
7. 未来方向（基于 gap + 趋势预判）
8. 总结（一句话领域现状 + 最关键发现 + 你的核心论点收尾）
```

**related_work 结构**（精简版，服务"本文工作"）：
```
1. 问题背景（1-2 段，建立语境）
2. 相关工作分节（按故事线，每节结尾点出与本文的关系）
3. 与本文工作的关系（1 段，明确本文填补了哪个 gap / 解决了哪个张力）
```

**research_gaps 结构**：
```
1. 现有方法概览（按故事线简要回顾，不是列表）
2. 空白分类（每个 gap 都有证据支撑 + 影响分析 + "为什么没人做"）
3. 优先级建议（最值得先补的 gap，以及理由）
```

**future_work 结构**：
```
1. 基于 gap 的具体建议（每条建议对应一个 gap）
2. 可行性评估（短期/中期/长期）
3. 预期影响（如果做了，领域会怎样改变）
```

## 引用格式

每条引用格式：
```
作者 et al. (年份) 提出了……[paper_uid]
```

或在表格中：
```
| 方法 | 作者 (年份) [uid] | 核心结果 |
```

**规则**：
- 首次出现写全称：`Sung et al. (2024) [arxiv-2403.10566]`
- 后续出现可缩写：`Sung et al.`（如果不会歧义）
- 同一处引用多篇：`[uid1, uid2, uid3]`

## 交付模式与完成定义

### 模式 1：brief（auto-research brief）

**最小必出：**

| 文件 | 必出 |
|---|---|
| `<review_type>.md` | 是 |
| `citation_table.csv` | 否（推荐） |
| `review_audit.md` | 否（推荐） |
| `method_comparison_table.csv` | 否 |

**算完成的条件：**
- 主综述文件完成，且有清晰主线，不是“论文 A/B/C 流水账”
- 正文只消费 `evidence_table.csv`
- 若用了 `extraction_confidence=low` 或 `qualitative_only=true` 的条目，正文或附注中有明确标识
- 不引用 `pending_fulltext.csv` 中的论文

### 模式 2：full（auto-research full）

**必出：**

| 文件 | 必出 |
|---|---|
| `<review_type>.md` | 是 |
| `citation_table.csv` | 是 |
| `review_audit.md` | 是 |
| `method_comparison_table.csv` | 条件（正文含对比则必出） |

**算完成的条件：**
- 所有核心论点都能回链到 `citation_table.csv`
- `review_audit.md` 统计引用覆盖度、低置信比例、`qualitative_only` 比例
- `extraction_confidence=low` 不承载核心论点
- 每个 gap 都能追溯到 `evidence_table.csv` 的具体条目

### 模式 3：独立调用（用户直接说“写综述”）

若不在 auto-research 包内调用，默认按 **full 的写作要求** 写正文，但产物可先最小落为：

| 文件 | 默认 |
|---|---|
| `<review_type>.md` | 必出 |
| `citation_table.csv` | 推荐 |
| `review_audit.md` | 推荐 |

若用户明确说“只先给我文稿”，可暂不补 CSV / audit；否则应按 full 要求补齐。

## 必出产物

| 文件 | 说明 |
|---|---|
| `<review_type>.md` | 主综述文本 |
| `citation_table.csv` | 引用清单：paper_uid + 在综述中出现的位置（章节/段落）+ 引用次数；full 必出，brief 推荐 |
| `review_audit.md` | 审计：用了多少篇论文、覆盖了多少个主题、有多少低置信引用、有多少 qualitative_only 引用；full 必出，brief 推荐 |
| `method_comparison_table.csv` | 方法对比表（如综述中包含对比）；正文含对比时必出 |

## 保存规则

**保存路径**（在 auto-research 流程中）：
- 主路径：`<workspace>/runs/{YYYY-MM-DD}_{主题关键词}/03-survey/`
- Obsidian 同步：`<obsidian_vault>/Research/{YYYY-MM-DD}_{主题关键词}/03-survey/`

**独立调用时**（用户直接说"写综述"）：
- 保存到当前工作目录，文件名为 `<review_type>.md`
- 同时询问用户是否需要保存到研究包目录中

## 文件清单

```
survey-writer/
├── SKILL.md            入口(本文件)
├── routing.md          命中条件 + 综述类型选择
├── report-template.md  四种综述类型的章节骨架
├── artifacts.md        产物 schema
└── README.md           读图
```

## 给上游 paper-reading 的承诺

- 我会消费 `evidence_table.csv` 中所有 `extraction_confidence ∈ {high, medium}` 的行
- `extraction_confidence=low` 的行会在 `review_audit.md` 中标注，但尽量不用于核心论点
- `qualitative_only=true` 的行只作为"观点引用"，不当作"证据引用"
- `pending_fulltext.csv` 中的论文不会出现在任何输出中
- 每条引用都挂 `paper_uid`，方便回溯

## 自检清单

### 基础质量
- [ ] 综述中每条引用都有 `paper_uid`，可在 `citation_table.csv` 中回溯？
- [ ] `extraction_confidence=low` 的引用被标注且不用于核心论点？
- [ ] `qualitative_only=true` 的引用只作观点引用，不作证据引用？
- [ ] 综述长度符合类型定义（literature_review 3000-8000 / related_work 1000-3000）？
- [ ] `review_audit.md` 统计了引用覆盖度、低置信比例、qualitative_only 比例？

### 叙事质量（人类写综述的精髓）
- [ ] **核心论点明确**：读者读完第一段就知道这篇综述在论证什么？
- [ ] **故事弧完整**：有起源→发展→分岔→融合→前沿的脉络？
- [ ] **不是 list-and-summarize**：用了批判性综合句型（While/Several studies have found/However）？
- [ ] **非中性语言**：用了批判性词汇（attempted/advocated/claimed/employed）？
- [ ] **层次化递进**：每节有"主线→演进→趋势→边界探索"的递进？
- [ ] **趋势预判**：识别了方向内部的演变趋势（"值得注意的是..."）？
- [ ] **边界探索**：指出了主方向之外的场景拓展（"此外，研究者开始探索..."）？
- [ ] **过渡句自然**：章节之间有逻辑连接，不是硬切换？
- [ ] **关键来源深入批判**：奠基工作和挑战者被深入分析，不是一笔带过？
- [ ] **Gap 有证据支撑**：每个 gap 都能追溯到 evidence_table 的具体数据？
- [ ] **对比揭示张力**：对比表格后有一段批判性解读，不只是罗列数据？
