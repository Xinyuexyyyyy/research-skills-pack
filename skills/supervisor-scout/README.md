# Supervisor Scout — 导师调研与背调系统

## 一句话简介

从研招网通知监控到导师学术背调，帮你选到最合适的研究生导师。

## 适用场景

- 🎯 **推免准备**：夏令营、预推免、九推阶段选导师
- 📝 **考研复试**：复试前了解导师、准备套磁
- 👨‍🏫 **导师背调**：对目标导师做全方位学术画像
- 📢 **信息监控**：不错过任何招生动态（简章发布、复试通知、调剂信息）

## 快速开始

### 1. 安装依赖

```bash
pip3 install beautifulsoup4 lxml requests pypinyin
```

**依赖说明**：
- `beautifulsoup4`, `lxml`, `requests` — 必需，用于网页爬取和解析
- `pypinyin` — 可选，用于中文姓名转拼音（`layer2_batch_profiles.py` 中使用），若缺失会自动跳过拼音生成功能

### 2. 监控研招网通知（北工大示例）

```bash
cd <workspace>/study-research/skills/supervisor-scout

# 增量更新 — 只获取新公告
python3 scripts/crawler.py --config configs/bjut.json --mode incremental

# 关键词监控 — 关注"复试"、"调剂"、"录取"
python3 scripts/crawler.py --config configs/bjut.json --mode monitor --keywords 复试 调剂 录取 夏令营 推免

# 爬取全文 — 获取公告完整内容
python3 scripts/crawler.py --config configs/bjut.json --mode full --max-pages 2
```

### 3. 采集导师名单

```bash
python3 scripts/crawler.py --config configs/bjut.json --mode supervisors
```

### 4. 单导师学术背调

```bash
python3 scripts/scholar_lookup.py --name "张红光" --school "北京工业大学"
```

### 5. 生成导师评级报告

```bash
python3 scripts/report_gen.py --school bjut --interest "氢能燃烧"
```

## 支持的学校

| 学校 | 代码 | 状态 |
|------|------|------|
| 北京工业大学 | `bjut` | ✅ 已验证 |
| 北京航空航天大学 | `buaa` | 🔄 待验证 |
| 北京理工大学 | `bit` | 🔄 待验证 |

## 添加新学校

1. 复制配置模板：
   ```bash
   cp configs/template.json configs/myschool.json
   ```

2. 编辑 `configs/myschool.json`，填写学校信息和CSS选择器：
   - `base_url`: 研招网首页地址
   - `channels`: 需要监控的栏目（通知公告、招生章程等）
   - `selectors`: 列表页和详情页的CSS选择器

3. 验证配置：
   ```bash
   python3 scripts/crawler.py --config configs/myschool.json --mode list --max-pages 1
   ```

## 目录结构

```
supervisor-scout/
├── configs/              # 学校配置文件
│   ├── bjut.json
│   ├── buaa.json
│   ├── bit.json
│   └── template.json
├── scripts/              # 可执行脚本
│   ├── crawler.py        # 通用爬虫引擎
│   ├── scholar_lookup.py # 学术信息查询
│   └── report_gen.py     # 报告生成
├── data/                 # 运行时数据（gitignored）
│   ├── crawled/          # 爬取原始数据
│   ├── processed/        # 处理后数据
│   └── reports/          # 输出报告
├── SKILL.md              # Skill定义
└── README.md             # 本文件
```

## 定时自动监控

### Mac/Linux (cron)

```bash
crontab -e

# 每天上午9点和下午6点执行增量更新
0 9,18 * * * cd $HOME/study-research/skills/supervisor-scout && python3 scripts/crawler.py --config configs/bjut.json --mode incremental >> data/crawler.log 2>&1
```

### 推送通知（可选）

监控到新公告时，可通过以下方式推送：
- **钉钉机器人**：配置webhook地址
- **企业微信**：配置企业ID和应用凭证
- **邮件**：配置SMTP服务器

（P1阶段支持，当前版本需在报告产出后手动查看）

## 常见问题

**Q: 爬虫会被封IP吗？**
A: 不会。已内置1-3秒随机延迟，且高校网站通常没有严格的反爬机制。

**Q: 可以监控多个学校吗？**
A: 可以。为每个学校创建配置，分别运行即可。

**Q: Google Scholar查询需要翻墙吗？**
A: 需要。国内网络访问Google Scholar不稳定，建议配置代理或使用镜像站。

**Q: 导师评价信息从哪里来？**
A: 目前主要来自公开渠道（Google Scholar、学校官网、知网）。学生评价需要用户自行补充（导师评价网、知乎等）。

## 更新日志

- **v0.1.0** (2026-05-13): MVP版本
  - 通用爬虫引擎（配置驱动）
  - 北工大研招网完整监控
  - 增量更新 + 关键词监控
  - 多高校配置模板

## License

仅供个人学习研究使用。爬取数据请勿用于商业用途。
