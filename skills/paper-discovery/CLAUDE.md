---
name: paper-discovery
description: 学术论文检索 / 导入 / 去重 / 候选池建立。覆盖 arXiv / Semantic Scholar / OpenAlex / PubMed / Crossref / DBLP / ACL Anthology 等学术源,产出 search_plan.md / source_log.csv / candidate_papers.csv / references.bib / import_manifest.json。**不做纳排,不做综述写作**。触发词:找论文、检索、搜文献、import、候选池、references.bib、查 arxiv、查 semantic scholar、build candidate set。
status: stable
---

# Paper Discovery — 学术论文检索 + 候选池建立

## 一句话定位

> 把"我要研究 X"翻译成"这是 X 主题的候选论文集"。**只做"找全 + 去重 + 登记"**,绝不做纳排、抽取、综述。

## 依赖与配置

### 核心依赖

| 依赖项 | 类型 | 说明 |
|---|---|---|
| `research-academic` | skill | 二级路由器，提供 `routing_decision` 和任务分派 |
| `research-base` | skill | 工具层：`atoms.md` 提供 `academic_search` / `web_fetch`；`artifacts.md` 定义 `source_log.csv` / `candidate_papers.csv` schema；`hooks.md` 定义钩子接口 |
| `paper-screening` | skill | 下游接收方，消费 `candidate_papers.csv` 进行纳排判断 |
| `paper-reading` | skill | 下游可选，消费 PDF 和 abstract 进行全文阅读和证据抽取 |

### 工作区工具依赖

| 工具 | 位置 | 必需性 | 说明 |
|---|---|---|---|
| `abstract_pipeline.py` | `<workspace>/tools/` | 必需 | 批量 abstract 补全工具，综合降级链（Elsevier → OpenAlex → SS → Crossref），依赖 Python 标准库 `requests` / `csv` / `json` |
| `elsevier_fetch.py` | `<workspace>/tools/` | 可选 | Elsevier 专用 abstract 抓取，由 `abstract_pipeline.py` 自动调用 |

**降级处理**：如果 `abstract_pipeline.py` 不存在，Discovery 阶段会跳过批量 abstract 补全步骤，仅记录元数据（title / DOI / landing_url），abstract 留空，由下游 `paper-screening` 或 `paper-reading` 按需抓取（降级为单点模式）。

### 环境变量配置

#### ELSEVIER_API_KEY（可选）

用于提升 Elsevier 期刊（Fuel / IJHE / Energy / RSER 等）的 abstract 覆盖率（从 OpenAlex 的 ~50% 提升到 100%）。

**申请地址**：https://dev.elsevier.com/

**配置方式**：
1. 在工作区根目录创建 `.env` 文件（如 `<workspace>/.env`）
2. 写入 `ELSEVIER_API_KEY=your_actual_key_here`
3. 确保 `.env` 已加入 `.gitignore`，避免泄漏

**使用示例**：
```bash
# 在调用 abstract_pipeline.py 前加载环境变量
source $WORKSPACE_ROOT/.env
python3 $WORKSPACE_ROOT/tools/abstract_pipeline.py --batch ...
```

**注意**：如果未配置此环境变量，`abstract_pipeline.py` 会自动降级到 OpenAlex / Semantic Scholar / Crossref 通路，Elsevier 论文的 abstract 覆盖率会下降，但不影响其他 publisher。

## 上层契约

- 父级:`research-academic`(router) → `research-base`(工具层)
- 进入条件:`research-academic/routing.md` 把任务定为 `matched_layer2=paper-discovery`
- 离开条件:产出合格的 `candidate_papers.csv` + `source_log.csv` + `references.bib` + `import_manifest.json`,**移交给 `paper-screening`**(或停在此处供用户使用)
- 共享 schema:严格遵守 `research-base/artifacts.md` 的 §2 `source_log.csv` 与 §3 `candidate_papers.csv`

## P0 边界(必须遵守)

### 做什么
- ✅ 把研究问题转成检索式
- ✅ 至少 2 个独立学术源 + 至少 2 轮检索(初始 + gap-driven 回补)
- ✅ 元数据登记(`paper_uid` / DOI / arxiv_id / s2_id / openalex_id / pmid / title / authors / year / venue / abstract / pdf_url / landing_url)
- ✅ 去重(DOI → arxiv_id → s2_id → openalex_id → pmid → title fingerprint)
- ✅ 学术源 vs 普通网页源**严格分层**(普通网页不写入本 skill 的 csv)
- ✅ 产出 `references.bib`(BibTeX),所有候选都写一条
- ✅ 输出 `import_manifest.json`(本批导入的元信息)

### 不做什么
- ❌ 纳排判断(`include` / `exclude` / `uncertain`)→ `paper-screening`
- ❌ 抽取证据 / 全文阅读 → `paper-reading`(P1)
- ❌ 写综述 → `survey-writer`(P1)
- ❌ 把网页摘要、新闻、博客混进 `candidate_papers.csv`
- ❌ 无 `source_id` 的论文偷偷进候选池(任何论文都必须能追溯到一条 `source_log` 记录)

## 源策略（topic-aware）— 2026-05-12 增补

> 不同学科默认源不同。本节为 2026-05-12 后的硬约束，**避免对工程类 topic 误用 arXiv 主力策略**（实测氢辅助 SI 与氨燃料 SI 两次连续 arXiv 0 召回）。

| Topic 类型 | 主力源 | 辅助源 | 兜底 |
|---|---|---|---|
| CS / Math / Physics / Stats / EE | **arXiv** | Semantic Scholar | OpenAlex |
| Engineering (mech / elec / chem / material / energy) | **OpenAlex** | Crossref | arXiv (常 0 召回) |
| Life Sciences (clinical / medical) | **PubMed** | OpenAlex | Semantic Scholar |
| Social Sciences | OpenAlex | Semantic Scholar | — |
| 跨学科 / 不确定 | OpenAlex + arXiv 并行 | Semantic Scholar | Crossref |

**判断流程**：从 `clarified_question.subject` 或 `domain_hint` 推断。涉及内燃机 / 电池 / 材料 / 化学 / 机械 → Engineering 类。

**Semantic Scholar `search` 端点限流**：2026-05-12 实测连续 429，API Key 已申请待审批。审批前默认禁用 SS search，SS 仅作为 DOI 单点查询（`/paper/DOI:<DOI>`）使用，避免触发 search 配额耗尽。

**brief 模式特殊约定**：单主力源 + 单兜底源即可（无需 ≥2 源硬约束）；目的是 10 分钟看懂方向，而非全面查全。

**Engineering 类 Abstract 补充通路（2026-05-12 修订）**：Elsevier 期刊（Fuel / IJHE / Energy / RSER 等）的 abstract 在 OpenAlex 覆盖仅 ~50%。如果配置了 `ELSEVIER_API_KEY` 环境变量（配置方法见下文"依赖与配置"章节），建议在 metadata enrichment 阶段调用 Elsevier API（`/content/article/doi/<DOI>`）补全 abstract，**实测 13/13 Elsevier 论文 = 100%**，比 WebSearch 合成（73%）准确且包含具体数值数据。详细降级链见 `paper-reading/SKILL.md` "Abstract 缺失降级链" 章节。

### Abstract Enrichment Pipeline — 具体实施（2026-05-12 增补 / 2026-05-13 升级）

Discovery 阶段完成 `candidate_papers.csv` 后，**立即**调用 `tools/abstract_pipeline.py` 批量补全所有候选论文的 abstract（综合降级链：Elsevier → OpenAlex → SS no-key → Crossref → needs_websearch），把抓到的内容写回 `candidate_papers.csv` 的 `abstract` 列。下游 `paper-screening`（看 abstract 决定筛入/排）和 `paper-reading`（抽 evidence）直接消费已经齐全的 abstract，无需二次抓取。

**为什么用 `abstract_pipeline.py` 而不是只调 `elsevier_fetch.py`**：
- `elsevier_fetch.py` 只覆盖 Elsevier 论文（DOI 前缀 `10.1016/*`）
- `abstract_pipeline.py` 自动处理所有 publisher：Elsevier 走 API（100%），非 Elsevier（MDPI / SAE / Frontiers / IJER / Wiley 等）走 OpenAlex / SS / Crossref 降级链
- 实测对今天氨燃料 SI 的 20 篇候选（混合 publisher）= **100% 命中**（Elsevier API 14 / OpenAlex 6）

**具体命令**：

```bash
# 假设工作区根目录为 $WORKSPACE_ROOT（如 <workspace>）
source $WORKSPACE_ROOT/.env  # 加载 ELSEVIER_API_KEY（如已配置）

python3 $WORKSPACE_ROOT/tools/abstract_pipeline.py \
    --batch <run>/00-discovery/candidate_papers.csv \
    --out <run>/00-discovery/abstracts_pipeline.json \
    --id-col id --doi-col doi --verbose
```

**产出**：
- `abstracts_pipeline.json` — 每个 `paper_id` 对应 `{status, source, abstract, abstract_chars, title, venue, year, attempted}`
- `status` ∈ `{"ok", "needs_websearch", "no_doi"}`
- `source` ∈ `{"Elsevier API", "OpenAlex", "SS no-key", "Crossref", null}` (null = needs_websearch)
- `attempted` 字段保留降级链尝试记录（用于审计）

**写回 candidate_papers.csv（推荐）**：

```bash
python3 -c "
import csv, json
from pathlib import Path
run = Path('<run>')
abstracts = json.load(open(run / '00-discovery' / 'abstracts_pipeline.json'))
with open(run / '00-discovery' / 'candidate_papers.csv') as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())
for r in rows:
    a = abstracts.get(r['id'], {})
    if a.get('status') == 'ok':
        r['abstract'] = a['abstract']
with open(run / '00-discovery' / 'candidate_papers.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
"
```

**单点用法**（调试时）：

```bash
python3 $WORKSPACE_ROOT/tools/abstract_pipeline.py 10.1016/j.fuel.2024.133091
python3 $WORKSPACE_ROOT/tools/abstract_pipeline.py 10.3390/en15228583 --json   # MDPI 走 OpenAlex
```

**位置**：`tools/abstract_pipeline.py` 是工作区级工具（位于 `<workspace>/tools/` 目录），跨 run 复用。

## 钩子覆盖(对接 `research-base/hooks.md`)

| 钩子 | 是否覆盖 | 干什么 |
|---|---|---|
| `hook_clarify` | ✅ 部分覆盖 | 接收 `research-academic` 给的子类型与 domain_hint,补"检索式 / 时间窗 / 必查 db / 排除 db" 到 `clarified_question.custom` |
| `hook_retrieve` | ✅ 完全覆盖 | 走 `channels.md` 的优先级矩阵,调 `atoms.academic_search` + `atoms.web_fetch`,落 `source_log.csv` |
| `hook_screen` | ⛔ 不覆盖 | 仅做**去重**(不是纳排)。所有 `selection / criteria` 留给 `paper-screening` |
| `hook_extract` | ⛔ 不覆盖 | 不抽证据。本 skill 的"提取"等价于"补 metadata 与 abstract" |
| `hook_synthesize` | ⛔ 不覆盖 | 不写综述。本 skill 的"综合"等价于"输出候选池 + bib + manifest" |
| `hook_review` | ✅ 轻量覆盖 | 自检候选池完整性,而不是综述 adequacy |

详见 `hooks.md`。

## 必出产物

| 文件 | 说明 |
|---|---|
| `search_plan.md` | 把 research_question 翻译成结构化检索计划(关键词、同义词、时间窗、必查 db、排除 db、计划轮次) |
| `source_log.csv` | 见 `research-base/artifacts.md` §2,记录每一轮每一 db 的检索 |
| `candidate_papers.csv` | 见 `research-base/artifacts.md` §3,候选池 |
| `references.bib` | BibTeX,每条候选一个 entry,key = `paper_uid` 改写后的安全字符串 |
| `import_manifest.json` | 本批导入的元信息(开始/结束时间、轮次数、各 db 命中数、去重前后规模、coverage_check 结果) |
| `missing_papers.md` | 找不到全文的论文列表(可空) |
| `dedup_log.md` | 重复合并的明细(可空,但若 `dedup_status != unique` 的行 ≥10 条建议产出) |

## 文件清单

```
paper-discovery/
├── SKILL.md            入口(本文件)
├── routing.md          命中条件细则 + 与 paper-screening 的让位边界
├── hooks.md            钩子覆盖详情
├── channels.md         学术检索渠道清单 + 调用约定 + 失败处理
├── report-template.md  产物骨架(search_plan / source_log / candidate_papers / bib / manifest)
├── artifacts.md        产物 schema(只列本 skill 实际写入的 csv,引用 research-base/artifacts.md 主 schema)
└── README.md           读图
```

## 抄哪了

| 来源 | 抄什么 |
|---|---|
| `Galaxy-Dawn/claude-scholar` | Zotero / 全文导入流程、PDF 入库、元数据补齐 |
| `Future-House/paper-qa` | metadata + index 准备、retraction check 思路 |
| 旧 `research-academic/channels.md` | 学术 db 优先级矩阵直接挪过来,不重写 |

## 给下游 paper-screening 的承诺

- `candidate_papers.csv` 中只保留 `dedup_status=unique` 的行作为正式候选(重复行也保留以供回溯,但 screening 不消费)
- 每行至少有 1 个稳定 ID(DOI / arxiv / s2 / openalex / pmid)或在 `notes` 里注明"无稳定 ID"
- `source_ids` 字段不为空(任意候选必须能追溯到 `source_log.csv` 中至少一条记录)
- `landing_url` 必填,以便 screening 阶段需要时能直接打开看摘要

## 自检清单

- [ ] 至少 2 个独立学术源被检索？
- [ ] 至少 2 轮检索（初始 + gap-driven 回补）？
- [ ] 去重逻辑覆盖 DOI → arxiv_id → s2_id → openalex_id → pmid → title fingerprint？
- [ ] `source_log.csv` 记录了每轮每库的检索详情？
- [ ] `candidate_papers.csv` 中每条都有至少 1 个稳定 ID 或 notes 说明？
- [ ] `references.bib` 包含所有候选的 BibTeX 条目？
- [ ] `import_manifest.json` 包含去重前后规模和 coverage_check 结果？
