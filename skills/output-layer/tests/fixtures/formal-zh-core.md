# OpenClaw 全景扫描报告

> 生成时间：2026-04-29
> 扫描目标：userysys@100.113.27.115 (Tailscale)
> OpenClaw 版本：2026.4.11

---

## 系统概况

| 项目 | 详情 |
|------|------|
| **版本** | 2026.4.11 |
| **运行时间** | 1天5小时 |

## Agents（3个活跃）

**默认主模型**：`kimi-coding/kimi-K2.6-code-preview`，备用 `minimax/MiniMax-M2.7`

**模型路由配置**：
- 默认agent使用 `kimi-coding` 为主模型
- compaction（上下文压缩）模式为 `safeguard`
- heartbeat 每60分钟一次

## 存储架构（KO - Knowledge Object系统）

配置文件：`workspace/config.yaml`

```yaml
storage:
  ko_db:
    type: sqlite
    path: core/ko_store/ko_store.db
  ko_vector_db:
    type: chroma
    persist_directory: ko_vector_db
```
