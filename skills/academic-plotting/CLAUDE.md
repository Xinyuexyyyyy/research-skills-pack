---
name: academic-plotting
description: 论文配图 / academic figure / plot / Figure / 架构图 / 实验图。为学术论文生成出版级配图，包括架构图、流程图、系统图和数据图，产出可嵌入 LaTeX 的 PDF/PNG、代码、caption。触发词：画图、论文配图、Figure、架构图、实验图、plot、academic figure、画个图。
status: stable
commands: [画图, 论文配图, Figure, 架构图, 实验图, plot, academic figure, 画个图]
---

# Academic Plotting — 论文配图

## 定位

为学术论文生成出版级配图，覆盖两类 Figure：架构图/流程图/系统图，以及折线、柱状、散点、热力图、ablation 等数据图。目标是产出可直接进入论文写作链路的图文件、代码、LaTeX 片段和 caption 建议。

## 与 drawio-diagram-agent 的边界

### 做什么
- 为论文、综述、实验章节生成可投稿的 Figure
- 优先输出 PDF/SVG 等矢量图，必要时补 PNG
- 为数据图生成可复现的 matplotlib / seaborn Python 代码
- 为架构图生成 TikZ / draw.io / AI 图像生成提示或草图方案
- 输出 LaTeX `\includegraphics` 片段和 caption 建议

### 不做什么
- 不做通用白板流程图，不以 `.drawio` 为唯一交付
- 不做工程计算绘图，不替代 `engineering-calc-plot`
- 不做装饰性插画、海报、封面图
- 不伪造实验数据，不用手绘曲线冒充真实结果
- 不把方法对比表硬画成图；适合表格时使用 booktabs

## 上下游关系

- 上游: `paper-composer` 写到需要配图时调用
- 平级: `drawio-diagram-agent` 做通用流程图，本 skill 做学术 Figure
- 输入: 论文段落、方法描述、实验数据表、CSV、JSON、LaTeX 草稿
- 输出: 图代码、图文件、LaTeX 插入片段、caption 文案建议
- 产物应能直接嵌入 LaTeX 论文或投稿模板

## Step 0：Context Analysis

先从上下文判断“要画什么”，再选路径。

| 输入类型 | 提取内容 | 路径判断 |
|---|---|---|
| 论文段落 | 任务、贡献、关键对象、需要解释的机制 | 多为路径 A |
| 方法描述 | 模块、数据流、训练流程、输入输出关系 | 多为路径 A |
| 实验数据表 | 指标、方法、数据集、分组、显著差异 | 多为路径 B |
| CSV / JSON | 数值轴、类别、时间步、实验条件、误差范围 | 多为路径 B |

必须提取: 关键实体、输入输出/依赖/对比关系、x/y 轴与误差等数据维度、方法组/数据集组/ablation 组等分组结构。

## 路径 A：架构图 / 流程图 / 系统图

适用对象：模型架构、系统 pipeline、训练流程、数据处理流程、模块关系图。

可选实现: TikZ 用于最终矢量图；draw.io 用于快速结构草图并导出 PDF/SVG；Gemini / DALL-E 只用于概念草图或视觉参考。

执行要点: 抽取模块、箭头、输入输出和层级；先画最小结构；用一致形状、线宽、字号和配色表示语义；导出 PDF/SVG，必要时附 PNG 预览。

## 路径 B：数据图

适用对象：折线图、柱状图、散点图、热力图、箱线图、训练曲线、ablation 图。

默认实现: 使用 Python 生成 matplotlib / seaborn 代码；数据来自用户提供的 CSV / JSON / 表格，不凭空生成结果；PDF 优先，PNG 作预览或投稿补充。

执行要点: 整理数据列；选择图型并写可复现脚本；设置色盲友好 palette、字号、线宽、图例和轴标签；保存 `figures/<figure_name>.pdf` 和必要的 `.png`。

## 图表类型选择指南

| 情况 | 推荐产物 |
|---|---|
| 有数值轴、误差、趋势或分布 | matplotlib / seaborn，路径 B |
| 有框、箭头、模块、数据流 | TikZ / draw.io / AI 草图，路径 A |
| 训练曲线、loss、accuracy、reward | matplotlib 折线图，路径 B |
| ablation、多方法多指标对比 | matplotlib 柱状/点图，路径 B |
| attention、相关性、混淆矩阵 | seaborn heatmap，路径 B |
| 方法对比表、实验设置表 | LaTeX booktabs 表格，不画成图 |

## 学术规范清单

- 矢量图优先: PDF/SVG 优先，PNG 只作补充
- 色盲友好: 使用 colorblind-safe palette，避免只靠红绿区分
- 字体大小: 图内文字不小于论文正文字号
- 极简视觉: 无 3D 效果、无阴影、无渐变背景、无装饰图标
- 坐标清晰: 轴标签、单位、图例、误差条必须可读
- 可复现: 数据图必须保留生成代码和数据来源说明
- Caption: 自包含、描述性、不重复正文，说明图中最重要的观察

## 产出格式

```markdown
## Academic Figure

### Context Analysis
- Figure goal:
- Extracted entities:
- Relations / data dimensions:
- Selected path: A / B

### Artifacts
- Code: `figures/<name>.py` 或 TikZ 片段
- Figure: `figures/<name>.pdf`
- Preview: `figures/<name>.png`（如需要）

### LaTeX
\begin{figure}[t]
  \centering
  \includegraphics[width=\linewidth]{figures/<name>.pdf}
  \caption{...}
  \label{fig:<name>}
\end{figure}

### Caption Suggestion
[自包含、描述性、不重复正文的 caption]
```

## 自检清单

- [ ] 是否先做 Context Analysis，再选路径？
- [ ] 是否区分架构图路径 A 和数据图路径 B？
- [ ] 数据图是否有可复现 Python 代码？
- [ ] 是否优先输出 PDF/SVG？
- [ ] 是否满足色盲友好、字号、无装饰元素要求？
- [ ] 是否提供 LaTeX 片段和 caption 建议？
