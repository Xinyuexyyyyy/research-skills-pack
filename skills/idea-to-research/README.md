# Idea To Research

## 一句话

`idea-to-research` 用来处理“想法还太模糊，先判断后面该走哪条调研路线”的阶段。
如果输入太模糊，它会先停在待澄清层，不会硬选一条路。

## 先看效果

你给一句原话，比如：

- “我有个想法，先帮我判断该走哪条调研路线”
- “这个东西是先抄 GitHub，还是先做产品调研更合适”
- “先和我对齐边界，再决定后面怎么研究”

系统内部会按这条顺序跑：

1. align 判断路线
2. brief 压出目标、约束、非目标
3. prompt 生成 route-specific research prompt
4. 如果信号不够，就先进入 `needs-clarification`
5. 先等你确认路线
6. 确认后再 run，正式落盘

## 四个主入口

调试或验收时可以直接运行：

```bash
python3 skills/idea-to-research/skill.py align "我想抄 GitHub 上成熟的 skill，后面直接接开发实现"
python3 skills/idea-to-research/skill.py brief "我有个新功能想法，想先定义用户、需求和 MVP，再决定做不做"
python3 skills/idea-to-research/skill.py prompt "我想研究一个 AI 能力秘书产品，先看看该怎么调研"
python3 skills/idea-to-research/skill.py run "我想做一个面向年轻人的新产品，先帮我定义问题和目标用户"
python3 skills/idea-to-research/skill.py run "我想研究年轻人为什么越来越抗拒职场升职，这更像社会趋势还是分群差异，先帮我做社会调研" --output-root /tmp/idea-to-research-check
python3 skills/idea-to-research/skill.py run "我有个新想法，先帮我看看下一步怎么研究比较合适" --output-root /tmp/idea-to-research-check
```

## 什么时候该停

- 用户目标太模糊时先停，先补边界
- 用户目标太模糊或多条路线信号打平时，会进入 `needs-clarification`
- 用户已经明确要走下游 skill 时先停，不要重复兜圈
- 用户不同意推荐路线时先停，先确认 override
- GitHub 路线依赖没跑通时先停，只保留前置对齐结果
- 用户只想看路线判断时先停，不直接落盘

## 关键目录

- `skills/idea-to-research/idea_to_research/`
  主流程实现
- `skills/idea-to-research/tests/`
  最小烟雾测试
- `<workspace>/task_draft/consensus/`
  默认落盘位置；如果传 `--output-root`，就只写到指定目录
- `<workspace>/task_draft/idea_sessions/`
  session 模式的输出目录

### 工作区结构要求

本 skill 默认假设以下目录结构：

```
<workspace>/
├── shared-skills/
│   └── idea-to-research/     # 本 skill 必须安装在此位置
│       ├── skill.py
│       ├── idea_to_research/
│       └── tests/
├── skills/
│   └── harvest-tool/         # harvest-tool 依赖（仅 github-build 路线需要）
└── task_draft/
    ├── consensus/            # 默认输出目录
    └── idea_sessions/        # session 输出目录
```

**路径自定义：**
- 设置环境变量 `WORKSPACE_ROOT` 可覆盖工作区根目录
- 设置环境变量 `HARVEST_TOOL_PATH` 可覆盖 harvest-tool 位置
- 使用 `--output-root` 参数可指定自定义输出目录

**示例：**
```bash
# 使用默认路径
python3 skill.py run "我的想法"

# 自定义工作区根目录
export WORKSPACE_ROOT=/path/to/my/workspace
python3 skill.py run "我的想法"

# 自定义输出目录
python3 skill.py run "我的想法" --output-root /tmp/my-output

# 自定义 harvest-tool 位置（仅 github-build 路线需要）
export HARVEST_TOOL_PATH=/path/to/harvest-tool
python3 skill.py run "我想抄 GitHub 项目"
```

## 最小验收

```bash
python3 skills/idea-to-research/skill.py align "我想抄 GitHub 上成熟的 skill，后面直接接开发实现"
python3 skills/idea-to-research/skill.py brief "我有个新功能想法，想先定义用户、需求和 MVP，再决定做不做"
python3 -m unittest skills.idea-to-research.tests.test_pipeline_smoke
```

看到路线判断正常、`social-research` 能落完整包、模糊输入会停在待澄清层，且 smoke test 通过，就说明这条前置对齐链是通的。

## 配置说明

### 环境变量

本 skill 支持通过环境变量自定义路径：

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，设置自定义路径
# WORKSPACE_ROOT=/path/to/your/workspace
# HARVEST_TOOL_PATH=/path/to/harvest-tool

# 加载环境变量
source .env
```

参考 `.env.example` 查看完整配置项说明。

### 依赖检查

运行以下命令检查依赖是否就绪：

```bash
# 检查工作区结构
ls <workspace>/shared-skills/idea-to-research/
ls <workspace>/skills/harvest-tool/  # 仅 github-build 路线需要

# 如果 harvest-tool 不存在，可以跳过（仅影响 github-build 路线）
# 其他路线（product-research、social-research、needs-clarification）不受影响
```
