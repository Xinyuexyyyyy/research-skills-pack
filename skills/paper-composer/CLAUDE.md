---
name: paper-composer
description: 论文写作 / 组装论文 / paper writing / 毕设论文 / 期刊论文。触发词:写论文、组装论文、paper writing、毕设论文、期刊论文、compose paper、论文初稿。
status: draft
---

# Paper Composer — 论文写作

## 一句话定位

把已有的综述、方法和结果材料组装成一篇完整论文初稿。**不是从零写，而是映射、补写、统一风格。**

## 上层契约

- 父级: `method-design`
- 进入条件: 至少有 `literature_review.md` + `methodology.md`
- 离开条件: 产出 `paper_draft.md`，并移交给 `review-loop` 或输出层
- 共享输入: 可选 `results_analysis.md`、`topic_statement.md`、模板要求

## P0 边界

### 做什么
- ✅ 确定论文结构
- ✅ 把已有内容映射到对应章节
- ✅ 补写摘要、引言、讨论、结论等缺失部分
- ✅ 统一术语、引用格式和叙述风格
- ✅ 输出完整初稿与结构说明

### 不做什么
- ❌ 重新做综述或方法设计
- ❌ 代替实验/分析
- ❌ 编造结果
- ❌ 忽略用户给定的论文格式要求

## 输入要求

- 必须至少存在 `literature_review.md`
- 必须至少存在 `methodology.md`
- 若缺失其一，先回到对应上游 skill 补齐
- 若有 `results_analysis.md`，可一并纳入

## 工作流

### Step 1：确定结构
- 判断是期刊、学位还是会议论文
- 按模板或常见结构确定章节

### Step 2：映射已有内容
- 把综述、方法、结果分别归位
- 标出每章已有材料和缺口

### Step 3：补写缺失
- 补摘要、引言、讨论、结论
- 对缺失内容保持与已有材料一致的论证线

### Step 4：统一风格
- 统一术语、缩写、引用格式
- 消除章节之间的重复和断裂

### Step 5：产出初稿
- 输出 `paper_draft.md`
- 输出结构说明和引用清单
- 交接到 `review-loop` 或输出层

## 引用验证协议

1. 硬规则: 永远不从记忆生成 BibTeX 条目。
   - 所有 BibTeX / DOI / arXiv ID / 出版信息必须通过 API 或用户提供材料程序化获取。
   - 不确定的作者、年份、题名、会议/期刊名不得补全为“看似合理”的引用。

2. 查验路径: 优先使用可复现的数据源。
   - Semantic Scholar API: 查论文元数据、DOI、作者、年份、venue。
   - arXiv API: 查 arXiv 论文、版本、题名、作者、摘要。
   - Exa MCP: 若当前环境可用，用于补充检索和交叉验证。
   - 用户已有 bibliography / Zotero / BibTeX 文件可作为输入，但仍需检查格式一致性。

3. 查不到时: 明确降级，不编造。
   - 正文中保留 `[CITATION NEEDED]`。
   - 引用清单中使用 placeholder，并标明缺失字段。
   - `paper_draft.md` 不得把 placeholder 伪装成已验证引用。

4. 告知义务: 交付时必须报告引用风险。
   - 明确告诉用户: “我标记了 X 个引用为 placeholder，需要你手动核实。”
   - 同时列出这些 placeholder 对应的章节、句子或引用键。

## 论文类型适配表

| 类型 | 结构 | 特殊要求 |
|---|---|---|
| 期刊 | Abstract → Intro → Literature → Method → Results → Discussion → Conclusion | 字数、期刊格式、引用规范 |
| 学位 | 摘要 → 绪论 → 文献综述 → 方法 → 实验/分析 → 结果讨论 → 结论 | 学校模板、章节完整性 |
| 会议 | 简化版 Intro → Method → Results → Conclusion | 页数限制、压缩表达 |

## 产出文件列表

| 文件 | 说明 |
|---|---|
| `paper_draft.md` | 完整论文初稿 |
| `paper_structure.md` | 章节结构、来源、完成度说明 |
| `citation_list.md` | 引用清单，与 evidence / bibliography 对齐 |

## 上下游衔接

### 上游
- `method-design` 或 `experiment-runner` 完成后进入
- 衔接提示: "所有素材就绪。下一步可以组装论文，说'写论文'或'组装论文'"

### 下游
- `review-loop`
- 输出层
- 衔接提示: "论文初稿完成。现在进入风格适配。"

## 自检清单

- [ ] `literature_review.md` 和 `methodology.md` 是否都存在？
- [ ] 论文结构是否按类型适配？
- [ ] 已有内容是否映射到正确章节？
- [ ] 缺失部分是否补写完整？
- [ ] 术语、引用、风格是否统一？
- [ ] 是否输出 `paper_draft.md` 和结构说明？
