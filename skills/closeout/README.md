# closeout

任务结束时收尾、总结、建议写记忆。

## 依赖说明

### 必需依赖

#### 1. 工作区记忆文件结构

本 skill 假设工作区使用以下记忆文件结构（通常位于 `<workspace>/.claude/memory/`）：

- `timeline.md` — 时间线记录，追加式写入
- `current-position.md` — 当前焦点和待办，覆盖式写入
- `decisions.md` — 决策记录，追加式写入
- `lessons.md` — 复盘记录，追加式写入

如果你的工作区没有这些文件，closeout 仍可输出 6 段总结，但记忆更新建议部分将无法使用。

#### 2. 锚点池（Anchor Pool）

本 skill 的锚点扫描功能依赖外部的 `anchor-pool` 目录及其脚本：

**必需文件**：
- `$ANCHOR_POOL_DIR/README.md` — 锚点池使用说明
- `$ANCHOR_POOL_DIR/ANCHOR_TEMPLATE.md` — 锚点文件的 schema 模板
- `$ANCHOR_POOL_DIR/update-index.sh` — 刷新跨工作区索引
- `$ANCHOR_POOL_DIR/validate.sh` — 验证锚点文件格式
- `$ANCHOR_POOL_DIR/review-ideas.sh` — ideas 发酵期检查

**配置方式**：
```bash
# 在 ~/.zshrc 或 ~/.bashrc 中设置
export ANCHOR_POOL_DIR="$HOME/anchor-pool"
```

**如果没有 anchor-pool**：
- 锚点扫描部分会跳过
- ideas 回看功能会跳过
- 不影响核心的 6 段收尾总结

**参考样本**：
- `$ANCHOR_POOL_DIR/seeds/wechat_writing_anchors-2026-05-25.md` — 真实锚点文件示例

### 可选依赖

- `observations.md` — 用于沟通切片功能，检测用户疲惫信号时可能调用

## 使用场景

详见 `SKILL.md` 中的完整说明。
