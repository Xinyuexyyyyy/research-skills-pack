# 一致性检查

## 检查项

| 项目 | 结果 | 说明 |
|---|---|---|
| `scripts/render_markdown_output.py` | 通过 | 文件存在 |
| `scripts/render_ppt_output.py` | 通过 | 文件存在 |
| `scripts/render_quick.py` | 通过 | 文件存在 |
| `scripts/output_entry.py` | 通过 | 新增统一入口 |
| `scripts/output-inventory.py` | 通过 | 新增最小实现 |
| `scripts/prune-output-runs.py` | 通过 | 新增最小实现 |
| `output/README.md` 中提到的输出入口 | 通过 | 与当前脚本一致 |
| `SKILL.md` 中提到的脚本路径 | 通过 | 与当前脚本一致 |

## 结论

- 目前文档引用的脚本路径已补齐。
- 其中 `output-inventory.py` 和 `prune-output-runs.py` 为最小可用实现，满足索引和预演需求。
- 后续如果要扩展归档治理，再继续增强这两个脚本即可。
