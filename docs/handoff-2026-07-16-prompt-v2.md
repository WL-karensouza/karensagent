# 交接文档：投研报告 Prompt v2 重构

**日期**：2026-07-16
**分支**：ifind-refactor worktree
**状态**：后端 Prompt + Render 已完成并测试通过，前端待适配

---

## 一、需求目的

将 LLM 分析层的投研报告从"按分析学科组织的 6 维度"改为"按散户阅读场景组织的 9 模块"。

需求文档来源：`D:\Desktop\新建 文本文档 (3).txt`

### 核心变化

| | 旧版 | 新版 |
|---|------|------|
| 组织方式 | 按分析学科（技术面/基本面/风险面...） | 按散户阅读场景（公司干嘛的→赚钱吗→主力在干嘛→怎么买卖） |
| 输出 JSON | `summary` + `sections ×5` + 辅助字段 | **9 个独立模块** + 保留 `score`/`decision`/`signal_attribution` |
| 语言规范 | "说人话"一句话带过 | **三步思考链**（数据事实化→逻辑推演化→散民口语化）+ 术语禁令 |
| 覆盖维度 | ESG/股东/北向资金被忽略 | **全部覆盖**，数据不可用则标注 |

### 数据采集层不变

iFinD SKILL 的 10 个维度（`report.py`）完全不变，只改 LLM 分析层的 Prompt。

---

## 二、9 模块新 Schema

```
模块1  核心结论与操作建议    rating_sentence + core_logic[] + reference_prices
模块2  公司画像与估值定位    business + valuation {pe_level, pb_level, analysis}
模块3  财务健康状况          profitability + key_indicators[] + risk_alerts[]
模块4  股价走势与资金动向    trend + capital_flow {margin_trading, main_force}
模块5  北向资金/主力拆解     available + trend + interpretation（数据不可用则标注）
模块6  股东结构与筹码集中度  major_moves[] + chip_analysis
模块7  催化剂与近期舆情      positive[] + negative[] + sentiment + sentiment_reason
模块8  风险评估与ESG表现     risk_level + risks[] + esg
模块9  散户实战操作指南      buy_strategy + stop_loss + take_profit + holding_period

保留字段：
  score (0-100)
  decision (看多/震荡/看空)
  signal_attribution[]
```

---

## 三、已完成的修改

### 1. `backend/stock_agent/analyze.py` — Prompt 三层重写

| Layer | 变化 |
|-------|------|
| Layer 1 角色定义 | 新增三步思考链定义 + 9 模块表格（含 iFinD 数据对应关系） |
| Layer 2 核心原则 | 新增规则3"三步思考链铁律"、规则4"术语禁令"、规则5强化"不给出买卖指令" |
| Layer 3 输出 Schema | 从旧 5-section JSON 改为 9-module JSON（约 100 行 Schema） |

**顺带修复的 Bug**：
- `main()` 中 `--json` 模式保存文件时 `UnboundLocalError: md` → 已修复
- `main()` 中 `analyze(data_md)` 应为 `analyze(data_md["markdown"])` → 已修复

### 2. `backend/stock_agent/render.py` — Markdown 渲染完全重写

- 废弃旧的 sections 遍历逻辑
- 改为逐模块渲染：一→九章 + 信号归因
- 表格、emoji 状态指示、引用块格式化

### 3. `backend/database.py` — 新增 `_extract_summary()`

```python
def _extract_summary(report: dict) -> str:
    """从报告 JSON 中提取摘要文本，兼容新旧两种格式"""
    m1 = report.get("module_1_核心结论", {})
    if m1 and m1.get("rating_sentence"):
        return m1["rating_sentence"]
    return report.get("summary", "")
```

- `save_stock_report()` 的 `summary` 字段改用此函数

### 4. 测试结果

✅ `600398`（海澜之家）端到端测试通过：
- 9 个模块全部输出，内容质量好
- 三步思考链在输出中清晰可见（"数据显示...分析认为..."）
- 数据不可用字段正确标注（融资融券、主力资金）
- 北向资金创意地从股东结构提取（外资减持分析）
- signal_attribution 权重和为 1.0

---

## 四、待办事项

### 高优先级 — 前端适配

| 文件 | 改动 |
|------|------|
| `frontend/src/views/agent/StockReport.vue` | 重写，适配 9 模块 JSON，废弃旧的 `orderedSections` |
| `frontend/src/stores/stock.js` | 如有前端解析逻辑需同步更新 |
| 10 个 `frontend/src/components/report/*.vue` | 大部分需要重写或新增以匹配新 Schema |

**前端模板建议**（等 Prompt 确认后再做）：

```
StockReport.vue
├── ScoreGauge.vue            — 保留，读 score
├── DecisionBadge.vue         — 保留，读 decision
├── Module1CoreConclusion.vue — 新增：rating_sentence + core_logic + prices
├── Module2CompanyProfile.vue — 新增：business + valuation
├── Module3FinancialHealth.vue — 新增：profitability + 指标表格 + alerts
├── Module4PriceTrend.vue     — 新增：trend + margin/main_force
├── Module5Northbound.vue     — 新增：北向资金动向
├── Module6Shareholders.vue   — 新增：增减持列表 + 筹码分析
├── Module7Catalysts.vue      — 可复用 CatalystList（改结构）
├── Module8RiskESG.vue        — 可复用 RiskWarningList + 新增 ESG
├── Module9Playbook.vue       — 可复用 HoldingAdviceCard（改结构）
├── SignalAttribution.vue     — 保留，结构不变
└── ReportMeta.vue            — 保留，不变
```

### 中优先级 — 后端测试更新

| 文件 | 说明 |
|------|------|
| `backend/tests/test_render.py` | 用旧 schema 的测试数据需更新 |
| `backend/tests/e1_field_completeness.py` | 字段检查列表需更新为新模块字段 |
| `backend/tests/test_analyze.py` | Prompt 内容断言需更新 |
| `backend/tests/probe_ifind_reasoner.py` | 旧 schema 断言行需更新 |

### 低优先级 — 其他

- `backend/probe_688221_full.py` — 用旧 sections 的探针脚本
- iFinD 3 个失败维度（实时行情/近期新闻/公司公告）权限排查

---

## 五、相关文件索引

| 文件 | 角色 |
|------|------|
| `D:\Desktop\新建 文本文档 (3).txt` | 需求规格文档 |
| `backend/stock_agent/skill/report.py` | 数据采集层（**未改动**） |
| `backend/stock_agent/analyze.py:60-133` | LLM Prompt（**本次改动核心**） |
| `backend/stock_agent/render.py` | Markdown 渲染（**本次改动**） |
| `backend/database.py:432-449` | 数据库摘要提取（**本次改动**） |
| `docs/discovery-frontend-report-optimization.md` | 之前的 Discovery Plan |
| `docs/handoff-2026-07-16-prompt-v2.md` | 本文档 |
