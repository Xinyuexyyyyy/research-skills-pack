---
name: workspace-init
description: 在当前工作区一键搭好约定的一级目录结构（基于调研/任务/输出三层范式）。只新建不覆盖。触发词：初始化工作区、init workspace、搭目录、建工作区结构、workspace-init。
status: stable
---

# Workspace Init — 工作区目录初始化

## 定位

在一个空的或新建的工作区，一条命令搭出**约定好的一级目录结构** + 一份说明。
解决"每个新工作区都要手动建目录、而且建得乱"的问题。

**目录约定的唯一事实源**：`../workspace-layout.md`，本 skill 严格按它建。

## Outcome Contract

- **产出**：约定的 7 个一级目录 + 根目录一份 `WORKSPACE.md`（说明每个目录放什么）
- **完成标准**：用户在当前目录能看到这套结构，且**已有的东西一个没动**
- **证据**：建了哪些、跳过哪些（已存在的），明确列出

## 红线（必须遵守）

- **只新建，绝不覆盖**：已存在的目录/文件一律跳过
- **在当前目录建**，不猜路径、不去别的地方建
- 不删除、不移动任何已有文件（那是 `/workspace-tidy` 的事）

## 工作流

### Step 1：确认位置
- 先 `pwd` 确认当前在哪，告诉用户"将在这里初始化"
- 如果当前目录已经有大量内容（>10 个一级项），提示用户："这看起来是个已用过的工作区，init 只会补缺失的目录；要整理已有的乱目录请用 `/workspace-tidy`"

### Step 2：读约定
- 读 `../workspace-layout.md` 的「一级目录约定」表，拿到要建的目录清单

### Step 3：建目录（只补缺）
对约定里的每个目录：
- 已存在 → 跳过，记一笔"已存在"
- 不存在 → `mkdir`，记一笔"新建"

```bash
for d in research projects output docs resources data archive; do
  if [ -d "$d" ]; then echo "跳过(已存在): $d/"; else mkdir -p "$d" && echo "新建: $d/"; fi
done
```

### Step 4：放说明文件
- 若根目录无 `WORKSPACE.md`，生成一份，内容来自 `workspace-layout.md` 的目录约定表（让用户一眼知道每个目录放什么）
- 已有 `WORKSPACE.md` → 跳过，不覆盖

### Step 5：报告
打印一张表：
```
目录          状态
research/     新建 / 已存在
projects/     ...
...
WORKSPACE.md  新建 / 已存在
```
并提示下一步：东西多了乱了，用 `/workspace-tidy` 整理。

## 它在防什么坑

- 新工作区目录靠手建，每次都不一样、还乱
- 一键塞满目录、把用户已有东西覆盖掉
- 在错的路径（猜的路径）建目录

## 什么时候用

- 刚建一个新工作区，想要规整的起点
- 现有工作区缺某些约定目录，想补齐

## 不什么时候用

- 工作区已经有内容、只是乱 → 用 `/workspace-tidy`
- 想收尾任务 / 更新记忆 → 用 `closeout`（那是任务维度，不是目录维度）

## 与其他 skill 的边界

- `workspace-tidy`：init 搭骨架（只新建），tidy 整理已有的乱（会移动，需确认）
- `closeout`：管任务收尾 + 记忆，不碰文件目录
