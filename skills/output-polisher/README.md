# output-polisher

`output-polisher` 是一层很窄的输出后处理。

它不负责写正文，只负责把已经成型的 `article.md` 转成更适合 Obsidian 使用的版本。

如果是在 `video-digest` 这条线上，另外还要遵守一份成稿口径：

- [video-digest-output-polisher.md](./video-digest-output-polisher.md)

这份口径约束的不是全文转排，而是 `report.md` / `learning-brief.md` 这种“整理稿 -> 可读成稿”的层。

## 当前正式口径

- 默认模式：`obsidian-enhanced`
- 默认输出：`article.obsidian.md`
- 手动对比稿：`article.obsidian-clean.md`、`article.obsidian-rich.md`

## 这层不做什么

- 不改 `self-article` 正文
- 不新增事实
- 不扩到别的平台
- 不把模型推断写成视频原话
- 不把低质量转写硬润成完整结论

## 快速验证

```bash
node skills/output-polisher/scripts/polish-markdown.js \
  --mode obsidian \
  --input skills/output-polisher/samples/source.md
```

```bash
node skills/output-polisher/scripts/polish-markdown.js \
  --all \
  --input skills/output-polisher/samples/source.md \
  --outdir /tmp/output-polisher-check
```

第二条命令跑完后，目录里应该只有：

- `obsidian-clean.md`
- `obsidian-enhanced.md`
- `obsidian-rich.md`
