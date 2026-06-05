# Channels — 综合类多渠道 + 跨包子调用

## 直接渠道(本包自跑)

当切片不需要专精包时,本包用以下通用渠道:

| 优先级 | 渠道 | 适用 | 入口 |
|---|---|---|---|
| P0 | 主流搜索引擎 | 通用问题 | `atoms.web_search()` |
| P0 | 行业权威媒体 / 报告 | 趋势 / 数据 | `atoms.web_fetch()` 已知 URL |
| P1 | 官方文档 / 财报 / 招股书 | 一手数据 | `atoms.web_fetch()` |
| P1 | 标杆个人 / 团队博客 | 一线观点 | `atoms.web_fetch()` |
| P2 | 论坛 / 社媒(HN / Reddit / X) | 实时反馈 | `atoms.web_search()` 限定域 |
| P2 | YouTube / 播客摘要 | 多媒体 | 转录后 `atoms.transcript_parse()` |

### 调用约定
- 单查询召回 ≤ 30,跨查询去重后 ≤ 100
- 任何外部访问必须 `atoms.source_log()`
- 论坛 / 社媒来源 `primacy` 默认 `tertiary`,`authority` 默认 `low`,需要靠交叉验证升档

---

## 跨包子调用(本包独有)

### 协议总览

```
comprehensive (本包)
   │
   ├── slice S1 (academic)    ──→  research-academic 的 hook_retrieve + hook_extract
   │       └─ 返回 evidence_records_partial[]
   │
   ├── slice S2 (competitive) ──→  research-competitive 的 hook_retrieve + hook_extract
   │       └─ 返回 evidence_records_partial[]
   │
   └── slice S3 (discovery)   ──→  research-discovery  的 hook_retrieve + hook_extract
           └─ 返回 evidence_records_partial[]

最终 evidence_records[] = 合并所有 partial,标注 slice_id
```

### 子调用接口(对子包的输入)

```yaml
sub_invocation:
  caller: research-comprehensive
  slice_id: S1
  subquery: "RAG 在多跳问答上的最新进展"
  scope: paper                # 限定本次只跑哪些 stage
  hops_allowed: [retrieve, extract]
  budget:
    max_records: 30
    max_minutes: 5
  return_format: evidence_records_partial
```

### 子调用接口(子包的返回)

```yaml
sub_response:
  slice_id: S1
  caller: research-comprehensive
  evidence_records_partial:
    - id: E-S1-001          # 注意 id 用 slice 前缀,合并不冲突
      ...
  source_log_partial:
    - ...
  notes: "未抓到的 5 篇见 missing_papers.md"
  status: ok | partial | failed
```

### 合并到本包全局池

- evidence_records 全部前缀化(E-S1-XXX / E-S2-XXX),冲突归零
- source_log 合并写入本包 `source_log.csv`
- 子包失败 → 本包标该 slice 为 `incomplete`,在 decision_memo 的"局限性"显式说明

### 限制

- 子调用**不会触发子包的 hook_synthesize / hook_review**(那两段始终归综合类)
- 子调用 budget 由综合类全局分配,避免单切片吃掉全部上下文
- 子调用最多 2 层深(子包再子调用主 skill 默认行为,不能再调本包)

---

## 切片设计指引

### 一个好的切片
- 关联且仅关联一个 `slice_type`
- 子查询 ≤ 1 行可表达
- 预期 evidence ≤ 30 条
- 直接关联 `decision_question` 的某一面

### 反例(不要这样切)
- 一个切片同时要查论文和竞品(应拆成 2 切片)
- "了解 X" 这种没收敛的切片(应该改成"X 的 Y 在 Z 时间窗内的情况")
- 一个切片要 200 条 evidence(应当拆细或降召回)

---

## 与主 skill 的关系
- 跨包子调用本身**不绕过主 skill 的钩子契约**:子包仍按主 skill 的 hooks.md 工作,只是被调用形态而非顶层主路由
- 评分仍统一走主 skill `scoring.md`,不允许子包自定义 Tier 阈值
- 子调用协议是本包目前独有,但若主 skill 后续正式吸收,以本文件为基础升版
