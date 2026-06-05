---
name: output-polisher
description: 为已通过 self-article 检查的内容做轻量排版与 Obsidian 导出，不改正文，只做输出后处理。
status: stable
---

# Output Polisher

## 定位

这是输出层的后处理环。

它的职责很窄：
- 输入一份已经写好的 `article.md`
- 输出更适合 Obsidian 使用的版本
- 不改正文事实、不改论证结构、不重写文章
- 不处理“去 AI 味 / 改得像我 / 收紧表达”这类表达改造；这些先走 `output-layer` 的 `rewrite-polish` mode

对 `video-digest` 来说，另有一层更重要的约束：
- `report.md` / `learning-brief.md` 这类“中间稿 -> 可读成稿”的整理层，也必须遵守同一份 Output Polisher 口径
- 具体见：`video-digest-output-polisher.md`

## 它做什么

1. 给重点句加轻量强调
2. 把结论、边界、摘要做成更好读的视觉块
3. 产出 Obsidian 可直接落库的不同档位版本

## 支持模式

- `obsidian-clean`: 保守模式；callout + 层级标题 + 重点强调
- `obsidian-enhanced`: 默认模式；原生增强模式，层级感更强，但不依赖插件
- `obsidian-rich`: 实验对比模式；依赖额外社区插件，不能当默认

## 规则

- 不新增事实
- 不重写论证
- 不润色正文表达
- 不把装饰做成噪音
- 先过 `self-article`，再做 polish
- 默认只把 `obsidian-enhanced` 当正式交付口径
- `clean` 和 `rich` 只保留手动模式
- `video-digest` 的整理稿必须像“编辑整理稿”，不是“AI 总结模板”
- 转写质量差时，宁可保守，也不脑补补齐

## 用法

```bash
# 默认别名，等同 obsidian-enhanced
node scripts/polish-markdown.js --mode obsidian --input article.md --output article.obsidian.md

# 显式指定三档
node scripts/polish-markdown.js --mode obsidian-clean --input article.md --output article.obsidian-clean.md
node scripts/polish-markdown.js --mode obsidian-enhanced --input article.md --output article.obsidian-enhanced.md
node scripts/polish-markdown.js --mode obsidian-rich --input article.md --output article.obsidian-rich.md

# 一次导出三档 Obsidian 对比稿
node scripts/polish-markdown.js --all --input article.md --outdir export/
```

## 当前主线约束

- 当前主线只服务 `video-digest -> article.md -> article.obsidian.md`
- 不扩公众号、小红书等别的平台
- 不把 `output-polisher` 变成内容改写器
