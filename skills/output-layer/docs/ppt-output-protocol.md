# PPT Output Protocol

## 这是什么

这是 `output-layer` 对 `ppt-master-bridge` 的统一接入协议。

它解决的是两件事：

1. 用户给一个主题后，`output-layer` 这一层到底会产出什么
2. 什么情况下算成功，什么情况下只能停在 `blocked`

## 适用范围

当前这条协议只覆盖：

- `render_ppt_output.py`
- 上游 `ppt-master-bridge`
- 可选下游 `ppt-master` 串行导出

它不覆盖：

- `ppt-master` 内部视觉设计规范
- SVG 质量细修
- 单页美观打磨

## 输入协议

最小必填：

- `--topic`

常用补充：

- `--audience`
- `--goal`
- `--core-message`
- `--preset`
- `--stage`
- `--project-path`

模式相关：

- `--mode`
- `--research-kind`
- `--research-route`
- `--page-count`

## 预设协议

如果传 `--preset`，会先补一组默认值：

- `pitch`
- `research-academic`
- `research-weekly`
- `research-intro`

预设只会补这 4 项默认值：

- `mode`
- `research-kind`
- `page-count`
- `goal`

如果用户手动传了这些参数，手动值优先。

## 输出协议

每次运行都会先写一个独立 run 目录，位置默认在：

`output/output-layer/<timestamp-topic>/`

目录内至少有：

- `request.md`
- `manifest.json`

其中：

- `request.md` 是人读的请求摘要
- `manifest.json` 是给程序和其他 skill 读的正式状态单

## 上游产物协议

无论 `stage=upstream` 还是 `stage=full`，都会先要求 bridge 产出：

- `consensus.md`
- `research.md`
- `storyboard.md`
- `handoff.md`
- `bridge_manifest.json`

`manifest.json` 里会把这些文件路径统一写到 `artifacts` 字段。

当进入 `stage=full` 时，还会额外尝试准备：

- `downstream_kickoff.md`
- `sources/bridge_briefing.md`
- `strategist_seed.md`
- `design_spec_starter.md`
- `spec_lock_starter.md`
- `downstream_confirmations.md`

注意：

- 这两个 `starter` 只是确认前草稿
- 不能替代正式 `design_spec.md / spec_lock.md`
- 也不代表已经跳过 `Eight Confirmations`
- `downstream_confirmations.md` 是给人确认和修改的，不是正式 spec

## 阶段协议

### `stage=upstream`

只要求 bridge 上游成功。

成功标志：

- `statuses.ppt_bridge_upstream.status = written`

此时不承诺有最终 `pptx`。

### `stage=full`

会在上游成功后继续尝试下游串行步骤：

1. `total_md_split.py`
2. `finalize_svg.py`
3. `svg_to_pptx.py`

但它不是无条件全自动。

必须先满足下游前置：

- `design_spec.md`
- `spec_lock.md`
- `svg_output/`

## 状态协议

当前主状态值有：

- `written`
- `skipped`
- `blocked`
- `failed`

含义如下：

- `written`：这一步成功写出了预期产物
- `skipped`：这一步当前可以跳过，不算失败
- `blocked`：当前不满足继续条件，所以明确停下
- `failed`：已经尝试执行，但执行本身失败

每个状态建议同时读取：

- `code`
- `reason`
- `details`

## `blocked` 协议

`full` 阶段最常见的 `blocked` 原因是：

- 缺 `design_spec.md`
- 缺 `spec_lock.md`
- 缺 `svg_output/`

这类情况会体现在：

- `statuses.ppt_master_full.status = blocked`
- `statuses.ppt_master_full.code = missing_downstream_prerequisites`
- `statuses.ppt_master_full.reason = ...`
- `statuses.ppt_master_full.details.missing_required = [...]`
- `next_step = ...`

同时会在 run 目录里写出：

- `downstream_readiness.md`

也就是说，这个入口不会假装“已经导出完成”。

## 成功协议

### 上游成功

满足以下条件即可视为上游成功：

- `statuses.ppt_bridge_upstream.status = written`
- `artifacts` 中 5 个 bridge 文件路径已写入
- `request.md / manifest.json` 已写入 run 目录

### 全链成功

满足以下条件即可视为当前 `full` 成功：

- `statuses.ppt_master_full.status = written`
- `statuses.ppt_export.status = written`
- `artifacts.pptx` 存在

## Manifest 关键字段

最值得外部读取的字段有：

- `tool`
- `stage`
- `preset`
- `mode`
- `research_kind`
- `project_path`
- `artifacts`
- `statuses`
- `request`
- `next_step`

推荐读取顺序：

1. 先看 `statuses`
2. 再看 `artifacts`
3. 最后看 `next_step`

## 当前边界

这条协议已经能稳定记录：

- 主题是什么
- 走了哪种 PPT 模式
- 上游有没有写完
- 下游为什么没继续
- 最终 `pptx` 有没有产出

但它现在还不是“从主题直接一键出最终 PPT”的完整产品协议。

当前更准确的说法是：

`output-layer` 已经把 PPT 接成“可记录、可复用、可追踪状态”的统一输出入口。
