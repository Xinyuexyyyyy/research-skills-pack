# PPT Output Quickstart

## 先记一句话

如果你现在只想“给一个主题，先收一版可进 PPT 的上游包”，就用：

`stage=upstream`

如果你已经在 `ppt-master` 项目里把下游准备好了，才用：

`stage=full`

## 三种最常见用法

### 1. 介绍类分享

适合：

- 教学类
- 科普类
- 介绍类
- 新手入门分享

命令：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "本科生怎么写专利" \
  --audience "本科生" \
  --preset research-intro
```

你会拿到：

- `consensus.md`
- `research.md`
- `storyboard.md`
- `handoff.md`
- `bridge_manifest.json`

### 2. 路演 / 对外说服

适合：

- 路演
- 融资 deck
- 对外方案
- 商务陈述

命令：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "AI 助手路演" \
  --preset pitch
```

默认会切到：

- `mode = pitch-deck`
- `page_count = 10`

### 3. 学术 / 组会

学术汇报：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "某篇论文汇报" \
  --preset research-academic
```

组会周报：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "本周实验进展" \
  --preset research-weekly
```

## 什么时候该用 `--stage full`

只有在你已经有这些文件时再用：

- `design_spec.md`
- `spec_lock.md`
- `svg_output/`

示例：

```bash
python3 skills/output-layer/scripts/render_ppt_output.py \
  --topic "本科生怎么写专利" \
  --preset research-intro \
  --stage full \
  --project-path "<workspace>/skills/ppt-master/projects/<your-project>"
```

如果这些前置没齐，结果不会报喜不报忧，而是明确写成 `blocked`。
同时 run 目录里会多一个 `downstream_readiness.md`，直接告诉你缺什么、下一步怎么补。
项目目录里还会多一个 `downstream_kickoff.md`，把八项确认前该读什么、确认后怎么继续跑收成一页。
另外还会给出 `design_spec_starter.md / spec_lock_starter.md` 两个确认前草稿，方便你直接起正式稿，但它们不是最终定稿。
如果你要先给用户看一版可确认内容，还会多一份 `downstream_confirmations.md`。

## 跑完去哪里看

默认去看：

`output/output-layer/<timestamp-topic>/`

先看两个文件：

- `request.md`
- `manifest.json`

如果你是人自己看，先读 `request.md`。

如果你是想判断这轮到底成功没成功，直接看 `manifest.json` 里的：

- `statuses`
- `artifacts`
- `next_step`

## 最容易踩的坑

### 坑 1：以为 `upstream` 就会出最终 `pptx`

不会。

`upstream` 只负责 bridge 上游包。

### 坑 2：以为 `full` 一定会自动成功

不会。

`full` 只有在下游前置齐全时才会继续。

### 坑 3：以为预设会覆盖手动参数

不会。

你手动传的值优先。

## 最短判断法

如果你不确定现在该怎么跑，就按这个顺序选：

1. 只是有主题，先跑 `--preset ... --stage upstream`
2. 已经在 `ppt-master` 里做完设计和 SVG，再跑 `--stage full`
3. 如果结果写了 `blocked`，先补前置，不要误判成工具坏了
