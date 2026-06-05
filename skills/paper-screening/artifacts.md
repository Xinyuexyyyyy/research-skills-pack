# Paper Screening — 产物 schema(本 skill 视角)

> 主 schema 在 `research-base/artifacts.md`。本文件只列**本 skill 实际写入的产物字段子集**与**本 skill 不写的字段**。

## 1. 本 skill 写入的产物

| 文件 | 主 schema | 备注 |
|---|---|---|
| `study_selection.csv` | `research-base/artifacts.md` §4 | 全字段都由本 skill 填 |
| `criteria.json` | 本 skill 自有 | 模板见 `report-template.md` §2 |
| `exclusion_reasons.csv` | 本 skill 自有 | 由 `study_selection.csv` 聚合 |
| `prisma_flow.md` | 本 skill 自有(从 §4 主 csv 聚合) | 模板见 `report-template.md` §5 |
| `screening_audit.json` | 本 skill 自有 | 字段见 `hooks.md` §6.C |
| `screening_summary.md` | 本 skill 自有 | 给用户看的总结 |

## 2. `study_selection.csv` — 本 skill 写入字段全集

按 `research-base/artifacts.md` §4 schema 全字段都要填(必填字段必须不为空):

### 必填(主 schema 强约束)
- `paper_uid`
- `screening_stage`(`title_abstract` / `fulltext` / `final`)
- `selection`(`include` / `exclude` / `uncertain`)
- `selection_reason_code`(从 §4.1 标准原因码)
- `selection_reason_text`(一句话人话理由)
- `confidence`(0-1)
- `decided_by`(`auto` / `active_learning` / `human` / `human_after_uncertain`)
- `decided_at`(ISO8601)
- `prisma_bucket`(`identified` / `screened` / `eligible` / `included` / `excluded`)

### 强烈建议
- `criteria_hits_include`(`;` 分隔的 `INC-X` ID)
- `criteria_hits_exclude`(`;` 分隔的 `EXC-X` ID)
- `fulltext_checked`(`screening_stage=fulltext` 时必填)

### 可写
- `notes`
- `custom_*`(本 skill 推荐用法见 §3)

### 绝对不写
- 任何 evidence 相关字段(`claim` / `quote` / `score` / `tier` / 等)→ 那是 `evidence_table.csv`
- 任何检索相关字段(`db` / `query` / `executed_at` / 等)→ 那是 `source_log.csv`

## 3. `study_selection.custom_*` 推荐用法

- `custom_pico_p_match`:bool / float,记 PICO P 命中度
- `custom_pico_i_match`:bool / float,记 PICO I 命中度
- `custom_pico_o_match`:bool / float,记 PICO O 命中度
- `custom_relevance_score`:float,active learning 给的 0-1 相关性分
- `custom_active_learning_round`:int,这条候选是在 AL 第几轮被决策
- `custom_seed`:bool,是否是用户标的种子

## 4. `criteria.json` 字段约束

- `schema_version`: 必填,`v0`
- `review_type` ∈ {`literature_review`, `systematic_review`, `scoping_review`, `sota`, `gap_finding`}
- `framework` ∈ {`PICO`, `PECO`, `SPIDER`, `none`}
- `include[].id` 必须以 `INC-` 开头
- `exclude[].id` 必须以 `EXC-` 开头
- `exclude[].code` 必须从 `research-base/artifacts.md` §4.1 标准原因码集合里选
- `dedup_key` 必须包含 `doi`,且按主 schema §1.1 的优先级排序

## 5. `exclusion_reasons.csv` 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `reason_code` | ✅ | 从标准原因码集合 |
| `count` | ✅ | 命中本 code 的论文数 |
| `prisma_stage` | ✅ | `title_abstract` / `fulltext` / `total` |
| `examples_paper_uid` | ⭕ | `;` 分隔,≤ 5 条 |

## 6. `screening_audit.json` 字段

字段定义见 `hooks.md` §6.C。

`adequacy_gate.status` 取值:
- `passed`:全部通过
- `warned`:含 warning 但非阻塞(如 fulltext_ratio 略低)
- `failed`:阻塞,**不允许移交 paper-reading**

## 7. 与 research-base 主 schema 的版本

- 本 skill 兼容 `research-base/artifacts.md` v0
- 升版时,本 skill 必须显式声明兼容的最小版本号,在 `screening_audit.schema_version` 里写

## 8. 字段扩展

- 优先放进 `study_selection.custom_*` 或 `criteria.custom`
- 真要提到主 schema → 走 `research-base/artifacts.md` §7 流程
- **绝对不要**新增名字与主 schema 重复的字段
- **绝对不要**用 `study_selection.custom_*` 偷偷塞 evidence(那不是 screening 的事)
