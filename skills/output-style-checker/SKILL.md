---
name: output-style-checker
description: 为 self-article 提供最小规则检查与评测闸门。先抓硬伤，不负责主生成。
status: draft
---

# Output Style Checker

## 定位

这是统一输出层的检查环，不是写作环。

它负责三件事：

1. 查明显坏味道
2. 给出失败原因
3. 决定能不能进入主输出

它不负责改写。发现 AI 腔、模板腔、表达松散时，只给诊断和下一步建议；表达改造交给 `output-layer` 的 `rewrite-polish` mode。

当前优先抓两类硬伤：

- 自说自话的 AI 腔
- 像“这一段主要围绕……继续展开”这种模板脚手架

## 第一版范围

- 只检查 `self-article`
- 只抓已经明确出现过的坏模式
- 不做复杂文风美化
- 不直接改文

## 失败后的去向

| 问题 | 建议 |
|---|---|
| AI 腔、模板腔 | 进入 `output-layer` rewrite-polish mode |
| 事实缺失或论证不成立 | 回到内容生成/调研环节，不直接润色 |
| 只是排版不好 | 进入 `output-polisher` |

## 当前链路

```text
candidate article
  -> textlint
  -> promptfoo
  -> pass/fail
```

## 最小验收

```bash
cd skills/output-style-checker
npm install
npm run lint:samples
npm run lint:regression
npm run eval:samples
```
