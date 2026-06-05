---
name: idea-to-research
description: 当用户只有一个模糊想法，还没决定后面该走 GitHub 借鉴、产品调研还是社会调研时使用。它先做路线判断和边界对齐，再进入对应调研层；如果输入太模糊或多条路线打平，就先停在待澄清层，不硬闯下游。
status: draft
---

# Idea To Research

## 定位

把“我有个想法，但还不知道后面该怎么研究”先收成一轮路线判断，再把人送去合适的下游。
如果当前信号太弱，先停在 `needs-clarification`，只补 1 到 3 个缩边界问题。

先看什么：
1. 先看本文件，确认什么时候该用 `idea-to-research`
2. 再看 [README.md](README.md)，看主入口、产物和验收方式
3. 排错时再看 `skill.py`、`idea_to_research/pipeline.py` 和 `tests/`

## 什么时候用

- 用户说“我有个想法，先帮我判断该走哪条调研路线”
- 用户还没决定后面是抄 GitHub、做产品调研，还是做社会/行业研究
- 用户先要对齐边界、对象、非目标，再进入下游调研层
- 用户想把一条模糊想法先沉成 `route-decision / idea-brief / research-prompt`

## 不什么时候用

- 用户已经明确知道要抄 GitHub 项目，直接走 `harvest-tool`
- 用户已经明确要做产品调研、竞品调研或论文综述，直接进对应 research 子层
- 用户只是要写文案、起标题、生成成稿，而不是做路线判断
- 用户已经有完整研究方案，不需要再做前置对齐

## 默认工作方式

不要让用户自己手敲命令。用户只需要讲目标，你在内部做路线判断并落盘。

## 主流程

```text
Step 1: Align   -> 读用户原话，判断主题和意图
Step 2: Route   -> 优先判断 github-build / product-research / social-research；信号不够就先停在 needs-clarification
Step 3: Brief   -> 把目标、约束、非目标、待确认问题沉成 idea brief
Step 4: Prompt  -> 生成 route-specific research prompt
Step 5: Confirm -> 先给用户看推荐路线和待确认问题
Step 6: Run     -> 用户确认后，再正式落盘到共识目录
```

## 用户可见检查点

### 检查点 1：先确认路线，不直接进下游

先给用户看：
- 推荐路线是什么
- 为什么这样判断
- 还差哪几个确认问题

用户确认前，不直接跑重下游。

### 检查点 2：如果改路，先显式切换

如果用户不同意推荐路线，要先确认改走哪条：
- `github-build`
- `product-research`
- `social-research`

如果当前是 `needs-clarification`，先回答缩边界问题，再决定是否切到正式路线。

### 检查点 3：正式落盘前先确认目录和目标

在 `run` 前先确认：
- 这轮要不要正式写入指定目录
- 当前产物是只做前置对齐，还是已经准备进入下一层

如果当前还是 `needs-clarification`，`run` 只会落前置对齐文件，不会生成正式下游包。

## Action

### `align`

```bash
python3 skill.py align "用户原话"
```

只做路线判断，适合先看推荐路线和理由。

### `brief`

```bash
python3 skill.py brief "用户原话"
```

生成 `idea brief`，把目标、约束、非目标和待确认问题压出来。

### `prompt`

```bash
python3 skill.py prompt "用户原话" [--route github-build|product-research|social-research]
```

生成 route-specific research prompt。只有用户明确要求改路时，才手动覆写 `--route`。

### `run`

```bash
python3 skill.py run "用户原话" [--slug my-topic] [--route github-build|product-research|social-research] [--output-root /tmp/my-run]
```

正式跑完整前置对齐流程，并把产物写到指定目录；不传 `--output-root` 时默认写到 `task_draft/consensus/`。

如果路线是 `github-build`，`run` 会继续调用 `harvest-tool` 相关依赖。

## 路由规则

### `github-build`

- 适用：用户想抄 GitHub 成熟项目，后面接实现
- 行为：会进入 GitHub 借鉴链路，并继续落 `candidates / harvest-results`

### `product-research`

- 适用：用户想先定义问题、用户、需求、MVP 和验证路径
- 行为：只做前置对齐和 research brief，不默认进 GitHub harvest

### `social-research`

- 适用：用户想研究行业、社会现象、公众态度、趋势或分群
- 行为：做前置对齐，并补完整社会调研包，不默认抓 GitHub 项目

### `needs-clarification`

- 适用：用户输入太模糊，或者多条路线信号打平
- 行为：只做前置澄清，不进入正式 GitHub / 产品 / 社会调研包

## 产物

统一落到 `task_draft/consensus/<slug>/`，至少包含：

- `route-decision.md`
- `idea-brief.md`
- `research-prompt.md`
- `analysis.md`
- `consensus.md`
- `consensus.json`
- `run-summary.json`

按路线不同，还会补对应 route layer 文件。

如果走 `github-build`，还会额外包含：

- `candidates.md`
- `harvest-results.json`

如果走 `product-research`，还会额外包含：

- `product-route.md`
- `product-research-brief.md`
- `problem-statement.md`
- `target-user.md`
- `assumptions-log.md`
- `validation-plan.md`
- `mvp-wedge.md`
- `prd-outline.md`
- `reader-brief.md`
- `discovery-report.md` 或竞品扫描文件
- `final-report.md`

如果走 `social-research`，还会额外包含：

- `social-route.md`
- `social-research-brief.md`
- `research-scope.md`
- `population-or-case-definition.md`
- `evidence-log.md`
- `uncertainty-and-bias.md`
- `reader-brief.md`
- `final-report.md`

如果走 `needs-clarification`，还会额外包含：

- `clarification-brief.md`

## 边界条件

### 情况 1：用户目标太模糊

**条件**：只有一个想法标题，没有目标、对象或想研究什么。
**处理**：进入 `needs-clarification`，先问 1 到 3 个缩边界问题；即使 `run`，也只落前置对齐文件。
**对用户怎么说**：这件事我可以先帮你判断路线，但还得先知道你后面是准备接开发、产品定义，还是行业研究。

### 情况 2：用户已经明确路线

**条件**：用户已经明确说“我要抄 GitHub 项目”或“我就是做产品调研”。
**处理**：不要再兜一大圈；先确认是否还需要前置对齐，不需要就直接下放到对应 skill。
**对用户怎么说**：你这轮路线已经很明确，如果不需要再对齐边界，我可以直接进下游。

### 情况 3：用户不同意推荐路线

**条件**：系统推荐了一条路线，但用户明确要走另一条。
**处理**：允许改路，但要显式记录 route override，不要偷偷替用户改。
**对用户怎么说**：可以改走这条路，我会按你的决定继续，但会保留当前推荐理由供回看。

### 情况 4：GitHub 路线依赖不可用

**条件**：当前判断为 `github-build`，但 `harvest-tool` 依赖不可用或 GitHub 搜索失败。
**处理**：先保留 `route-decision / brief / prompt`，把下游 harvest 标为未完成，不编造仓库结论。
**对用户怎么说**：路线已经判断出来了，但 GitHub 借鉴链路这轮没跑通，我先把前置对齐结果给你，仓库层稍后补。

### 情况 5：用户只想看路线，不想正式落盘

**条件**：用户只想先看判断结果，不想写共识目录。
**处理**：只跑 `align / brief / prompt`，不要直接 `run`。
**对用户怎么说**：这轮我先给你路线判断和 brief，不正式写入目录，等你确认再落盘。

### 情况 6：指定了 `--output-root`

**条件**：用户或调用方显式指定输出目录。
**处理**：只往指定目录写，不额外双写回默认 `task_draft/consensus/`。
**对用户怎么说**：这轮产物只会写到你指定的位置，不会再额外落一份默认目录。

## Tool 依赖

- `skill.py`：CLI 入口
- `idea_to_research/pipeline.py`：主流程实现
- `tests/test_pipeline_smoke.py`：最小烟雾测试
- 目录：`task_draft/consensus/`
- 下游依赖：`harvest-tool`（仅在 `github-build` 路线进入）

### harvest-tool 依赖说明

**安装位置要求：**
- 默认位置：`<workspace>/skills/harvest-tool/`
- 自定义位置：设置环境变量 `HARVEST_TOOL_PATH=/path/to/harvest-tool`

**安装方法：**
```bash
# 如果 harvest-tool 在 skills/ 目录下
cd <workspace>/skills/
git clone <harvest-tool-repo-url> harvest-tool

# 或者设置环境变量指向其他位置
export HARVEST_TOOL_PATH=/path/to/your/harvest-tool
```

**版本兼容性：**
- harvest-tool 必须包含 `scripts/discover.py` 和 `scripts/harvest.py`
- 需要提供 `search_github_repos(query: str, count: int)` 函数
- 需要提供 `harvest_repo(url: str, name: str)` 函数

**降级行为：**
- 如果 harvest-tool 不存在，`github-build` 路线会抛出 ImportError 并给出清晰提示
- 其他路线（`product-research`、`social-research`、`needs-clarification`）不受影响

### 工作区结构要求

**默认结构：**
```
<workspace>/
├── shared-skills/
│   └── idea-to-research/     # 本 skill 位置
├── skills/
│   └── harvest-tool/         # harvest-tool 默认位置
└── task_draft/
    ├── consensus/            # 默认输出目录
    └── idea_sessions/        # session 输出目录
```

**环境变量配置：**
- `WORKSPACE_ROOT`：覆盖工作区根目录（默认通过相对路径向上 3 层推断）
- `HARVEST_TOOL_PATH`：覆盖 harvest-tool 位置（默认 `<workspace>/skills/harvest-tool`）

## 最小验收

```bash
python3 skills/idea-to-research/skill.py align "我想抄 GitHub 上成熟的 skill，后面直接接开发实现"
python3 skills/idea-to-research/skill.py brief "我有个新功能想法，想先定义用户、需求和 MVP，再决定做不做"
python3 skills/idea-to-research/skill.py run "我想研究年轻人为什么越来越抗拒职场升职，这更像社会趋势还是分群差异，先帮我做社会调研" --output-root /tmp/idea-to-research-check
python3 skills/idea-to-research/skill.py run "我有个新想法，先帮我看看下一步怎么研究比较合适" --output-root /tmp/idea-to-research-check
python3 -m unittest skills.idea-to-research.tests.test_pipeline_smoke
```

验收通过标准：
- `align` 能输出清晰路线判断
- `brief` 能输出结构化 brief
- `social-research` 能落完整社会调研包
- 模糊输入会停在 `needs-clarification`，不误闯下游
- smoke test 通过，说明主流程最小链路没断
