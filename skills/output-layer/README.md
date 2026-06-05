# output-layer

`output-layer` 是一个基于 agent 的公共输出层能力。

它不负责内容理解，不负责原始资料处理，也不负责阅读编辑界面。

它只负责一件事：

把已经确认可用的 Markdown 内容，按规则做成正式成品。

工作区统一输出入口是 `output/README.md`。如果找不到某轮成品或想判断哪些历史 run 可以清理，先运行：

```bash
python3 scripts/output-inventory.py
```

这个索引只登记和提示冗余候选，不会移动或删除文件。

如果要看更严格的归档预演，再运行：

```bash
python3 scripts/prune-output-runs.py
```

默认只会产出 `output/output-prune-plan.md`，不会移动或删除文件。

也可以显式使用子命令和过滤：

```bash
python3 scripts/prune-output-runs.py plan --topic-contains openclaw-system-overview
```

现在在正式成品化之前，管线里会先经过一层可配置的 `style-correction`：

- 默认只做解释型风格纠偏
- 不重写全文
- 规则来自独立 preset，可继续演化
- 可以先只出报告，再决定要不要正式导出

## 当前第一版范围

- `clean markdown`
- `style corrected markdown`
- `obsidian-enhanced markdown`
- `docx`
- `pdf`（P1，已接入引擎探测；需本机安装 PDF 引擎）
- `ppt`（通过 `ppt-master-bridge` 接成上游交接包）

## 默认定位

- `Obsidian`：人和 agent 交互成品
- `docx`：人和人交互成品
- `clean markdown`：标准化中间稿

## 快速试跑

```bash
python3 skills/output-layer/scripts/render_quick.py
```

如果这轮想显式关掉风格校正：

```bash
python3 skills/output-layer/scripts/render_markdown_output.py \
  skills/output-layer/samples/source.md \
  --profile formal-zh \
  --to markdown \
  --style-correction off
```

如果想切到另一个风格 preset：

```bash
python3 skills/output-layer/scripts/render_markdown_output.py \
  skills/output-layer/samples/source.md \
  --profile formal-zh \
  --to markdown \
  --style-correction explainer-zh-v1
```

如果只想先看文风诊断，不继续生成 `clean markdown / obsidian / docx / pdf`：

```bash
python3 skills/output-layer/scripts/render_markdown_output.py \
  skills/output-layer/samples/source.md \
  --profile formal-zh \
  --to markdown,obsidian,docx,pdf \
  --style-correction-report only
```

这时会保留：

- `output.corrected.md`
- `style_correction_report.json`
- `style_correction_report.md`
- `manifest.json`

并把其他正式产物标记为 `skipped`。

`style_correction_report.md` 是给人看的诊断单。`style_correction_report.json` 里重点看三块：

- `summary`：发现数量、最高优先级问题、建议先处理的动作
- `findings`：按严重度和处理顺序排好的具体问题
- `finding_rules`：本次实际使用的诊断规则，方便回溯 preset / profile 是否生效

当前可用 preset：

- `explainer-zh-v1`：默认解释型纠偏
- `plain-explainer-zh-v1`：更朴素、少评论腔
- `business-commentary-zh-v1`：更强调判断和评论口气

## PPT 输出

先看说明：

- 协议说明：`skills/output-layer/docs/ppt-output-protocol.md`
- 新手教程：`skills/output-layer/docs/ppt-output-quickstart.md`

如果这轮不是要出 `docx`，而是要把一个主题走成 PPT 上游交接包，可以直接走：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "本科生怎么写专利" \
  --audience "本科生" \
  --goal "先生成可进入 ppt-master 的上游交接包" \
  --core-message "先把为什么写专利、什么是专利、怎么写清楚" \
  --stage upstream \
  --mode research-deck \
  --research-kind intro-share
```

如果你不想每次手填模式参数，也可以直接用预设：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "AI 助手路演" \
  --preset pitch
```

当前预设：

- `pitch`：路演 / 融资 / 对外说服
- `research-academic`：学术汇报
- `research-weekly`：组会周报
- `research-intro`：介绍类分享 / 教学类分享

预设只负责补默认值：

- `mode`
- `research-kind`
- `page-count`
- `goal`

如果你手动传了这些参数，手动值优先，不会被预设覆盖。

默认会在 `skills/ppt-master/projects/` 下初始化或复用项目，然后调用 `ppt-master-bridge` 产出：

- `consensus.md`
- `research.md`
- `storyboard.md`
- `handoff.md`
- `bridge_manifest.json`

阶段说明：

- `--stage upstream`
  只生成 bridge 上游交接包，这是默认模式
- `--stage full`
  如果项目已经具备 `design_spec.md / spec_lock.md / svg_output/`，则继续串行执行下游：
  `total_md_split.py -> finalize_svg.py -> svg_to_pptx.py`
  并把最终 `pptx` 路径也写进 `manifest.json`
  如果这些前置条件不满足，会明确标记 `blocked`，不会假装成功

同时它也会像 `render_markdown_output.py` 一样，在 `output/output-layer/` 下落一个独立运行目录，里面至少有：

- `manifest.json`
- `index.md`
- `request.md`

这个运行目录负责记录：

- 本轮请求参数
- 复用或新建的 bridge 项目路径
- 5 个上游交接文件路径
- 当前输出状态

最小回归测试：

```bash
python3.11 -m unittest skills/output-layer/tests/test_render_ppt_output_smoke.py
```

注意：

- 这里接入的是 `ppt-master-bridge` 上游，不是最终 `pptx` 导出
- 如果要继续生成 SVG / `pptx`，再进入 `skills/ppt-master/skills/ppt-master/`

## 当前默认排版口径

- 总标题：黑体小二，居中
- 正文：仿宋GB2312，小四，固定28磅，首行缩进2字符
- 一级标题：`#`，三号，加粗，编号 `一、二、三、`
- 二级标题：`##`，编号 `1. 2. 3.`
- 页码：仅 `docx` 启用
- 列表 / 引用：默认跟正文走
- 代码块：默认等宽字体，小一档

## DOCX 标准模板

标准参考模板固定为：

```text
templates/docx/formal-zh-reference.docx
```

默认 `formal-zh` 导出会先把这份模板复制到本轮 run 目录，再交给 Pandoc 作为 `--reference-doc` 使用；`manifest.json` 的 `docx_reference.mode` 会标记为 `template`。如果本轮传了 `--rules` 临时覆盖排版，才会基于这份标准模板临时生成本轮专用 reference doc，并标记为 `generated`。

当前标准模板来自 Daily Work 历史 run：

```text
output/output-layer/20260520-192132-010051-openclaw-system-overview/formal-zh-reference.docx
```

## PDF 现状

- `output-layer` 现在会自动探测本机可用的 PDF 引擎。
- 优先顺序：`xelatex -> lualatex -> pdflatex -> wkhtmltopdf -> weasyprint`
- 当前本机已可直接产出 `pdf`，主链可验证。

## formal-zh 固定口径

- 这套 profile 的核心原则是：只有纯正文吃“首行缩进 2 字符”。
- 下列内容默认豁免首行缩进：总标题、一级/二级/三级标题、元数据说明块、列表项、表格单元格、代码块、引用块、分割线、`配置文件：...` 这类结构化说明行。
- 如果源文档只有一个总标题 `#`，后面主体章节都是 `##`，输出层会自动把这些章节提升成正式一级标题，按 `一、二、三、` 编号。
- “标签 + 列表”结构会被自动拆开，避免在 `docx` 里压成一整段。例如 `模型路由配置：` 后面的 `- xxx` 会保留成独立列表。
- 开头连续引用元数据会自动拆成独立段落，不再合并成一整段。
- 代码块在 `docx` 中默认走统一代码区样式：等宽字体、灰底、边框、无正文首行缩进。
- `Body Text` 和 `Compact` 已分离：前者是普通说明段，后者是紧凑列表项，不再共用同一套正文观感。

## 回归集

- `skills/output-layer/samples/source.md`
- `skills/output-layer/samples/formal-report.md`
- `skills/output-layer/samples/meeting-note.md`
- `skills/output-layer/tests/fixtures/formal-zh-core.md`
- `skills/output-layer/tests/fixtures/formal-zh-structure.md`

验证命令：

```bash
python3.11 -m unittest discover -s skills/output-layer/tests -p 'test_*.py'
```
