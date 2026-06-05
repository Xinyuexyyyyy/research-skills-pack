# MANIFEST — 锁死的事实层

> 这份文档对标 opencove 的 `references/topology.md`：把"接入这套包需要的所有事实"钉死，
> 不依赖任何人脑子里的上下文。改动这套包时，先改这里。

## 一、包里有什么

```
research-skills-pack/
├── doctor.py            一键自检：跑它就知道装好没、缺什么
├── MANIFEST.md          本文件（锁死的事实层）
├── README.md            人看的入口：这是什么、怎么接入
├── skills/              7 个 skill（已清理，可共享）
│   ├── paper-discovery/     论文检索 + 候选池建立
│   ├── paper-reading/       论文精读 + 证据抽取
│   ├── survey-writer/       综述撰写
│   ├── supervisor-scout/    导师调研与背调
│   ├── research/            调研总入口（最稳，建议起步）
│   ├── idea-to-research/    模糊想法 → 调研路由
│   └── closeout/            任务收尾 + 锚点
├── shared/
│   └── research-base/       地基：学术 skill 的 schema 底座
└── tools/                   跨 skill 复用的工具
    ├── abstract_pipeline.py     批量 abstract 补全
    ├── elsevier_fetch.py        Elsevier API 抓取
    └── evidence_extractor.py    证据抽取
```

## 二、依赖矩阵（每个 skill 要什么）

| Skill | 必需依赖 | 可选依赖 | 相关环境变量 |
|---|---|---|---|
| paper-discovery | research-base, tools/abstract_pipeline.py | ELSEVIER_API_KEY | 无 |
| paper-reading | research-base, tools/evidence_extractor.py | ELSEVIER / S2 KEY | STUDY_RESEARCH_ROOT |
| survey-writer | research-base, evidence_table.csv（上游产出） | — | 无 |
| supervisor-scout | bs4, lxml, requests | pypinyin | 无 |
| research | base/, packages/（包内自带） | — | CONTENT_DIR |
| idea-to-research | 无 | harvest-tool | WORKSPACE_ROOT, HARVEST_TOOL_PATH |
| closeout | 无 | 锚点池脚本 | ANCHOR_POOL_DIR |

## 三、接入步骤（锁死，照做即可）

```bash
# 1. 克隆
git clone <repo_url> research-skills-pack
cd research-skills-pack

# 2. 自检（立刻知道缺什么）
python3 doctor.py

# 3. 装 supervisor-scout 的爬虫依赖（用到才装）
pip3 install beautifulsoup4 lxml requests pypinyin

# 4. 把 skills 软链进自己的 Claude Code / Codex 工作区
ln -s "$(pwd)/skills/research"        ~/your-workspace/skills/research
ln -s "$(pwd)/skills/paper-discovery" ~/your-workspace/skills/paper-discovery
# ……按需链接其余 skill

# 5. 需要 Elsevier 全量 abstract 时（可选）
cd skills/paper-discovery && cp .env.example .env   # 填入自己申请的 key
```

**关键事实**：
- 所有环境变量**都可选**。一个都不配也能跑，只是部分功能降级（见上表）。
- API key **各自申请、各填各的**。包里不含任何真实 key。
- `data/` 目录是空的（只有 `.gitkeep`）——课题组跑出来的数据落在自己的 `data/`，互不污染。

## 四、清理记录（这套包对原版做了什么，便于追溯）

| 处理 | 内容 |
|---|---|
| 删真实数据 | supervisor-scout 的 343 个文件（含真实导师背调档案 `*_profile.md`、研招网爬取数据）已清空，只留目录骨架 |
| 删全文 PDF | paper-reading/data 下载的论文 PDF 已删 |
| 抽 API key | Elsevier / Semantic Scholar key 抽到各 skill 的 `.env.example`，正文不含真实值 |
| 路径通用化 | 所有 `/Users/sure/` 硬编码改为 `<workspace>` / 环境变量 |
| 删个人记忆 | closeout 对个人记忆文件的 `[[...]]` 引用已删，核心规则内联 |
| 删缓存 | `__pycache__` / `*.pyc` / `.DS_Store` 全部清除 |

## 五、维护约定

- 改这套包：**先改 MANIFEST，再改文件**，保证事实层和实际一致。
- 加新 skill：拷进 `skills/`，在 `doctor.py` 的 `SKILLS` 列表加一行，更新本文件依赖矩阵。
- 课题组反馈"装不上"：让他们贴 `python3 doctor.py` 的输出，红色行就是缺口。

