# research-skills-pack

一套可共享的科研 + 任务管理 skill 包，给课题组用。仿 OpenCove 范式做成**自包含拓展包**：
克隆下来跑一个命令就知道能不能用，所有事实写死在 `MANIFEST.md`，不依赖维护者脑子里的上下文。

## 这是什么

7 个已清理（无密钥、无个人数据、无硬编码路径）的 skill：

| 场景 | Skill | 一句话 |
|---|---|---|
| 学术 | **research** | 调研总入口，最稳，建议从这起步 |
| 学术 | **paper-discovery** | 把"我要研究 X"变成候选论文集 |
| 学术 | **paper-reading** | 论文精读 + 结构化证据抽取 |
| 学术 | **survey-writer** | 基于证据写综述 / related work |
| 学术 | **supervisor-scout** | 导师调研与背调（保研/考研选导师） |
| 任务 | **idea-to-research** | 模糊想法路由到调研 |
| 任务 | **closeout** | 任务收尾，输出 6 段总结 |

## 30 秒上手

```bash
git clone <repo_url> research-skills-pack
cd research-skills-pack
python3 doctor.py          # 自检：绿了就能用
```

`doctor.py` 会告诉你：7 个 skill 齐不齐、地基依赖在不在、哪些环境变量没配（**全可选，缺了只降级**）、爬虫依赖装没装。

## 接入工作区

把需要的 skill 软链进自己的 Claude Code / Codex 工作区：

```bash
ln -s "$(pwd)/skills/research" ~/your-workspace/skills/research
```

详细接入步骤、依赖矩阵、清理记录全在 **[MANIFEST.md](MANIFEST.md)**（锁死的事实层）。

## 设计原则（为什么这么做）

- **一键自检**：对标 opencove 的 `status` / `verify`，课题组不用读维护者的上下文，跑 `doctor.py` 就知道现状。
- **锁死事实层**：对标 opencove 的 `topology.md`，所有"接入要什么"写死在 MANIFEST，改包先改它。
- **API key 各填各的**：包里零真实密钥，每人 `cp .env.example .env` 填自己的。
- **数据隔离**：`data/` 是空骨架，谁跑谁的数据落自己目录，互不污染。

## 出问题怎么办

贴 `python3 doctor.py` 的输出。**红色行 = 缺口**，按提示补即可。
