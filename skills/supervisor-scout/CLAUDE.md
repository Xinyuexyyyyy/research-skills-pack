---
name: supervisor-scout
description: "导师调研与背调系统。覆盖研招网通知监控、导师信息采集、学术背调、导师评级与套磁建议。触发词：导师、推免、套磁、选导师、研招网、招生简章、复试、调剂、夏令营、导师背调、导师评级。"
type: lightweight
status: experimental
---

# Supervisor Scout — 导师调研与背调系统

## 一句话定位

> 从研招网通知监控到导师学术背调，帮你选到最合适的研究生导师。

## 设计哲学

推免/考研选导师是一个**信息极度不对称**的决策。学生往往只能在招生简章上看到导师名字和一句话简介，对导师的真实学术水平、研究方向、课题组氛围一无所知。本skill的目标是**系统性地降低这个信息差**。

信息链路：
```
研招网通知监控 ──→ 导师名单采集 ──→ 学术背调 ──→ 综合评级 ──→ 套磁建议
     │                  │                │              │             │
   不漏过          不漏人          不漏维度      有依据       有策略
   任何通知        任何导师        任何指标       有比较       有模板
```

---

## 触发条件

- 用户提到"导师"、"推免"、"套磁"、"选导师"
- 用户提到"研招网"、"招生简章"、"复试"、"调剂"、"夏令营"
- 用户提到"背调"、"导师评级"、"导师评价"
- 用户想监控某个学校的研招动态
- 用户需要整理导师信息做决策

## 边界条件

**条件**: 用户只是想了解某个导师的基本信息（一句话）
**处理**: 直接WebSearch回答，不走完整skill流程

**条件**: 用户明确要求爬取非高校网站（如企业招聘）
**处理**: 超出本skill范围，建议用通用爬虫方案

**条件**: 用户需要联系导师（发邮件）
**处理**: 提供套磁信模板和发送策略，但不代发邮件

**条件**: 用户询问的是已毕业的导师评价（过往经验）
**处理**: WebSearch搜集公开评价，标注信息来源和可信度

---

## 工作流

### Step 1: 明确目标学校与阶段

```markdown
## 用户画像确认
- **目标学校**: [北工大 / 北航 / 北理 / 多校并行]
- **申请阶段**: [夏令营 / 预推免 / 九推 / 考研复试]
- **目标学位**: [学硕 / 专硕 / 直博]
- **兴趣方向**: [用户输入，如"氢能燃烧"、"机器学习"]
- **优先级**: [学术产出 / 方向匹配 / 导师人品 / 课题组资源]
```

### Step 2: 研招网监控（信息不漏）

根据用户目标学校，配置爬虫监控研招网关键栏目：

| 监控栏目 | 监控关键词 | 触发动作 |
|----------|-----------|---------|
| 最新通知 | 夏令营、推免、招生简章 | 立即提醒 |
| 硕士招生通知 | 复试、调剂、录取、分数线 | 立即提醒 |
| 博士招生通知 | 申请考核、复试名单、录取 | 立即提醒 |
| 导师队伍 | 导师更新、招生名额 | 汇总提醒 |

**技术实现**: `scripts/crawler.py --config configs/{school}.json --mode monitor`

### Step 3: 导师名单采集（人不漏）

从以下渠道采集目标学院的全部导师：
1. 学校研招网"导师队伍"栏目
2. 学院官网"师资队伍"栏目
3. 招生专业目录中的导师名单

**产出**: `data/processed/{school}/supervisors.json`

### Step 4: 导师学术背调（维度不漏）

对每位候选导师进行多维度背调：

| 维度 | 工具/渠道 | 采集内容 |
|------|----------|---------|
| 学术论文 | Google Scholar | 论文数、h-index、引用数、近年代表作 |
| 中文论文 | 知网CNKI | 中文核心、基金项目、合作网络 |
| 学术社交 | ResearchGate | 活跃度、项目合作、学术影响力 |
| 在研项目 | 学校官网/学院网站 | 纵向/横向项目、经费规模 |
| 学生评价 | 导师评价网/知乎/小红书 | 导师风格、课题组氛围（标注可信度） |

**产出**: `data/processed/{school}/supervisor_profiles.json`

### Step 5: 综合评级与推荐

根据用户偏好权重，对导师进行综合评级：

```
导师总分 = 学术产出(25%) + 学术影响力(20%) + 方向匹配(20%)
         + 招生活跃度(15%) + 学术潜力(15%) + 学生评价(5%)
```

**评级等级**:
| 等级 | 分数 | 建议 |
|------|------|------|
| S | ≥90 | 强烈推荐，优先套磁 |
| A | 80-89 | 推荐，积极联系 |
| B | 70-79 | 备选，保持关注 |
| C | 60-69 | 谨慎考虑 |
| D | <60 | 不建议 |

**产出**: `data/reports/{school}_supervisor_report.md`

### Step 6: 套磁策略与模板

为Top 5-10导师制定个性化套磁策略：

| 导师 | 策略 | 切入点 | 邮件模板 |
|------|------|--------|---------|
| A导师 | 学术共鸣 | 引用其最新论文，提出思考 | 模板1 |
| B导师 | 方向匹配 | 强调研究方向的高度契合 | 模板2 |
| C导师 | 项目驱动 | 表达参与在研项目的兴趣 | 模板3 |

**产出**: `data/reports/{school}_outreach_plan.md`

---

## 命令体系

用户可直接调用以下命令：

| 命令 | 做什么 | 示例 |
|------|--------|------|
| `/scout setup {学校代码}` | 初始化学校配置 | `/scout setup bjut` |
| `/scout monitor {学校代码}` | 启动研招网监控 | `/scout monitor bjut` |
| `/scout collect {学校代码}` | 采集导师名单 | `/scout collect bjut` |
| `/scout profile {导师姓名}` | 单导师背调 | `/scout profile 张红光` |
| `/scout rank {学校代码}` | 生成导师评级报告 | `/scout rank bjut` |
| `/scout outreach {导师姓名}` | 生成套磁方案 | `/scout outreach 张红光` |
| `/scout add-school {学校名} {研招网URL}` | 新增学校适配 | `/scout add-school 北航 https://yzb.buaa.edu.cn` |

---

## 支持的 schools

| 代码 | 学校 | 状态 | 配置 |
|------|------|------|------|
| `bjut` | 北京工业大学 | ✅ 已验证 | `configs/bjut.json` |
| `buaa` | 北京航空航天大学 | ✅ 已验证 | `configs/buaa.json` |
| `bit` | 北京理工大学 | ✅ 已验证 | `configs/bit.json` |
| `bupt` | 北京邮电大学 | ⏳ 规划中 | — |

## 执行方式（AI直接执行）

**核心原则：用户不接触代码，AI在后台执行脚本，只输出结构化结果。**

当用户触发本skill时，Claude Code 自动调用后台脚本执行，过滤掉技术日志，只向用户展示最终数据。

### 后台执行脚本位置

所有脚本位于 `skills/supervisor-scout/scripts/` 目录：
- `scout` — 统一命令入口
- `crawler.py` — 通用爬虫引擎
- `collect_supervisors.py` — 导师名单采集
- `scholar_lookup.py` — 学术信息查询

### 常用执行命令（AI内部使用）

```bash
# 监控通知（北工大/北航/北理）
python3 skills/supervisor-scout/scripts/crawler.py --config configs/{school}.json --mode monitor --max-pages 2

# 采集导师（北工大机械学院）
python3 skills/supervisor-scout/scripts/collect_supervisors.py --school bjut --college jxny

# 采集导师（北理车辆/能动）
python3 skills/supervisor-scout/scripts/collect_supervisors.py --school bit --college me_vehicle
python3 skills/supervisor-scout/scripts/collect_supervisors.py --school bit --college me_energy

# 导师学术画像
python3 skills/supervisor-scout/scripts/scholar_lookup.py --name "导师姓名" --school "学校名"
```

---

## 产出物

| 文件 | 说明 |
|------|------|
| `data/crawled/{school}/{channel}/{date}.json` | 爬取原始数据 |
| `data/crawled/{school}/state.json` | 增量更新状态 |
| `data/reports/alerts/{date}.md` | 监控提醒报告 |
| `data/processed/{school}/supervisors.json` | 导师基础信息表 |
| `data/processed/{school}/supervisor_profiles.json` | 导师完整画像 |
| `data/reports/{school}_supervisor_report.md` | 调研报告 |
| `data/reports/{school}_top_picks.md` | 推荐导师清单 |
| `data/reports/{school}_outreach_plan.md` | 套磁方案 |

---

## 自检清单

- [ ] 目标学校和申请阶段已确认？
- [ ] 研招网监控已配置并运行？
- [ ] 导师名单已完整采集？
- [ ] 学术背调覆盖全部维度？
- [ ] 评级权重符合用户偏好？
- [ ] 套磁方案有个性化切入点？
- [ ] 所有数据来源已标注可信度？

---

## P0 阶段边界

### 做什么
- ✅ 研招网通知爬取与监控（北工大已验证）
- ✅ 配置驱动的通用爬虫引擎
- ✅ 增量更新 + 关键词监控
- ✅ 导师名单采集（从研招网"导师队伍"栏目）
- ✅ 单导师学术信息查询（Google Scholar）
- ✅ 导师评级报告（基础版）

### 不做什么
- ❌ 自动发邮件/微信推送（P1，需用户配置API Key）
- ❌ 批量导师背调（P1，当前为单导师模式）
- ❌ 学生评价聚合（P1，需从多个社交平台抓取）
- ❌ 套磁信自动发送（P1，只生成模板，不代发）
- ❌ WebUI界面（P2）

---

## 借鉴与关联

| Skill | 关系 | 说明 |
|-------|------|------|
| `research-base` | 工具复用 | 复用其WebFetch、WebSearch原子工具 |
| `paper-discovery` | 下游 | 导师背调时的论文检索可复用其通道 |
| `academic-deep-research` | 下游 | 导师学术影响力深度分析可复用其方法 |
| `task-analyze` | 上游 | 用户模糊需求时先走analyze |
