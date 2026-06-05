# Output Layer Core Reference

## Formal-zh Rules

- 只有纯正文默认吃 `首行缩进 2 字符`。
- 下列内容默认豁免首行缩进：标题、元数据说明块、列表项、表格单元格、代码块、引用块、分割线、结构化说明行。
- 如果源文档是“一个总标题 `#` + 多个 `##` 章节”，输出层会自动把后续 `##` 提升成一级标题，并编号为 `一、二、三、`。
- `标签：- 列表` 结构会自动拆开，避免在 `docx` 里压成一行。
- 开头连续引用说明会自动拆成独立段落。
- 代码块在 `docx` 中使用统一代码区样式，不走正文缩进。
- `Body Text` 是普通说明段，`Compact` 是紧凑列表项。

## Workflow Details

概述：读取 Markdown 输入，按需做风格校正，按 profile 渲染为多格式成品，最后写 manifest 和索引。

1. **解析输入与配置**
   - 输入：源 Markdown 文件路径、`--profile`（默认 formal-zh）、`--style-preset`（可选）
   - 输出：resolved_profile（目标格式列表 + 排版规则）、run_id（时间戳目录）

2. **风格校正（可选）**
   - 输入：源 Markdown、style-preset 名称
   - 输出：`output.corrected.md`、`style_correction_report.json`
   - 如传 `--style-correction-report only`，本步后直接终止，不进入渲染

3. **多格式渲染**
   - 输入：clean/corrected Markdown、resolved_profile
   - 输出：按 profile 顺序生成 `output.clean.md` → `output.obsidian.md` → `output.docx` → `output.pdf.html`
   - PDF 引擎探测失败时自动跳过，不影响其他格式

4. **落盘与索引**
   - 输入：所有已生成文件
   - 输出：`manifest.json`（文件清单 + 元数据）、`index.md`（人类可读索引）
   - 写入 `output/output-layer/{run_id}/`

## Action Routes

| 调用方式 | 对应脚本 / Skill | 适用场景 |
|---|---|---|
| 完整渲染 | `scripts/render_markdown_output.py` | 正式输出，全格式 |
| 快速验证 | `scripts/render_quick.py` | 本地试跑，默认走正式报告样例 |
| PPT 上游包 | `scripts/render_ppt_output.py` | 生成 bridge 交接包，不进 docx/pdf |
| draw.io 图表 | `drawio-diagram-agent` | 生成 `.drawio` 流程图 / 路线图 / 架构图 |
| 仅诊断 | `--style-correction-report only` | 只出纠偏报告，不渲染 |
| 更新索引 | `scripts/output-inventory.py` | 重建 output 目录索引 |

## Dependencies

### External Tools

| 工具 | 用途 | 安装方式 |
|---|---|---|
| Python 3.11+ | 运行环境 | `brew install python@3.11` 或官网下载 |
| pandoc | docx/pdf 渲染引擎 | `brew install pandoc` |
| wkhtmltopdf | pdf 导出（HTML → PDF） | `brew install wkhtmltopdf` |

### Python Packages

```bash
pip install python-docx pyyaml
```

## Core Files

| 文件 | 作用 |
|---|---|
| `profiles/formal-zh.yaml` | 中文正式报告排版规则（缩进、标题编号、样式映射） |
| `profiles/style-correction/*.yaml` | 风格校正预设（explainer / plain-explainer / business-commentary） |
| `templates/pdf/formal-zh.css` | PDF 导出时的中文排版样式 |
| `templates/output-report-template.md` | 输出报告模板 |

## Existing References

- `docs/style-adapt-spec.md` — 风格适配规格
- `docs/style-correction-v1.md` — 解释风格矫正规约
- `docs/ppt-output-protocol.md` — PPT 上游包协议
- `docs/ppt-output-quickstart.md` — PPT 输出快速入口
- `docs/consistency-check.md` — 脚本路径与文档一致性检查

## Regression Set

- `samples/source.md`
- `tests/fixtures/formal-zh-core.md`
- `tests/fixtures/formal-zh-structure.md`

Validation:

```bash
python3.11 -m unittest discover -s skills/output-layer/tests -p 'test_*.py'
```

PPT smoke:

```bash
python3.11 -m unittest skills/output-layer/tests/test_render_ppt_output_smoke.py
```
