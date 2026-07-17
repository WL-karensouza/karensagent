# iFind 数据源重构方案

> 用同花顺官方 iFind MCP API 全量替换现有爬虫数据采集层，此次为重构级别改动。

---

## 1. 替换范围

**全量替换，不保留 fallback。**

旧 `fetcher.py` 的多源 fallback 链（K线：腾讯→akshare；新闻：akshare→搜狗微信→百度新闻；基本面：东方财富 F10）全部废弃，统一走 iFind 官方 API。

理由：
- iFind 是付费官方 API，可用性远高于爬虫
- 旧多源 fallback 代码是最大维护负担（解析腾讯文本协议、搜狗 HTML、东方财富字段映射）
- 保留双轨会形成无人维护的旧代码

---

## 2. 数据模型

**新 Pydantic 数据模型替代旧 dict。**

每个职责目录的 `__init__.py` 暴露对应 Pydantic Data 类：

| 职责 | Pydantic 类 | 说明 |
|---|---|---|
| market_data | `MarketData` | 行情+K线+技术指标+资金面 |
| financials | `FinancialsData` | 估值/盈利/成长/偿债/现金流五维 |
| news_events | `NewsEventsData` | 财经新闻+公司公告+热点事件 |
| risk | `RiskData` | 风险定量指标+ESG |
| market_env | `MarketEnvData` | 市场环境/板块关联 |

---

## 3. 目录结构

按职责拆目录，每目录含多文件 + Pydantic 模型 + prompt.py：

```
stock_agent/
├── analyze.py                    # 主入口：遍历 fetcher 采集→组装 prompt→调 LLM→渲染
├── ifind_client.py               # iFind MCP 连接层（封装 call.py 协议）
│
├── fetchers/
│   ├── market_data/              # 行情+K线+技术指标+资金面
│   │   ├── __init__.py           # MarketData 模型 + fetch_market_data()
│   │   ├── kline.py              # K线历史数据
│   │   ├── spot.py               # 实时行情
│   │   └── prompt.py             # 技术面/资金面 system instructions + user prompt 渲染
│   ├── financials/               # 财务数据
│   │   ├── __init__.py           # FinancialsData 模型 + fetch_financials()
│   │   ├── valuation.py          # 估值维度（PE/PB/EPS/BPS）
│   │   ├── profitability.py      # 盈利能力（ROE/ROIC/毛利率/净利率）
│   │   ├── growth.py             # 成长性（营收增速/利润增速）
│   │   ├── solvency.py           # 偿债能力（流动比/速动比/资产负债率）
│   │   ├── cashflow.py           # 现金流质量
│   │   └── prompt.py
│   ├── news_events/              # 新闻+公告+热点事件
│   │   ├── __init__.py
│   │   ├── news.py               # 财经新闻
│   │   ├── notice.py             # 公司公告
│   │   └── prompt.py
│   ├── risk/                     # 风险指标
│   │   ├── __init__.py
│   │   ├── indicators.py
│   │   └── prompt.py
│   └── market_env/               # 市场环境
│       ├── __init__.py
│       ├── sector.py
│       └── prompt.py
│
└── render.py                     # Markdown 报告渲染
```

---

## 4. 去掉 Skills 中间层

旧 6 个 skill 文件（`stock_agent/skills/` 目录）全部删除，原因：
- skills 做的规则预判（ROE>20%="优秀"、RSI>70="超买"）不如 LLM 结合行业特征做的判断
- prompts 组装逻辑分散在 skills 里，不如 Pydantic model_fields 遍历统一处理
- 数据包仅保留 `enabled/disabled` 判断，在 `build_prompt()` 中一句话搞定

新数据流：`iFind API → Pydantic Data Models → build_prompt() → LLM → report`

---

## 5. Prompt 组织方式

**放在各自职责目录下（方案 1）。**

每个 fetcher 目录的 `prompt.py` 暴露：
- `SYSTEM_INSTRUCTION`：该维度的分析指令（注入 LLM system prompt）
- `render_prompt(model) -> str`：把 Pydantic 数据渲染成 user prompt 文本片段

`analyze.py` 的 `build_prompt()` 遍历所有 fetcher 目录的 `prompt.py` 来组装。

---

## 6. `analyze()` 函数签名

```python
def analyze(stock_code: str) -> tuple[dict, dict]
```

内部自己调所有 fetcher 采集数据，调用方（routers）只需传 stock_code，保持现有调用契约不变。

---

## 7. 部分采集失败处理

**跳过失败的维度，整体 status=done。**

- 各维度独立 try/except，某个 tool 超时/失败时跳过该维度
- API 返回 task 结果时附加 `warnings` 字段，status 为 `"partial"`：

```python
{
  "status": "partial",
  "report": {...},
  "warnings": [
    {"dimension": "新闻公告", "reason": "iFind news API 超时(15s)", "impact": "消息面分析跳过"}
  ]
}
```

- 后端接口统一暴露 warnings 信息，前端报告中对用户做出相应解释
- 仅当**连行情数据都拿不到**（market_data 失败）才判定整体失败

---

## 8. LLM 模型

使用 DeepSeek 推理模型（`deepseek-reasoner`），替代原来的 `deepseek-chat`。推理模型在金融分析等需要深度推理的场景下表现更好。

---

## 9. JSON Schema

当前 OUTPUT_SCHEMA 在 `analyze.py:94-130`，需要重新设计，**暂不讨论，后续单独决策。**

---

## 10. iFind 密钥配置

放在 `.env` 文件中，新增一行：

```
IFIND_AUTH_TOKEN=xxx
```

`ifind_client.py` 从环境变量读取，和 `DEEPSEEK_API_KEY` 模式一致。`.env` 已在 `.gitignore` 中，不会泄露。

---

## 11. iFind Server 使用范围

只使用 stock、news、edb 三个 server，**fund（基金）server 不使用。**

| Server | 使用 | 说明 |
|---|---|---|
| `stock` | ✅ | 行情、财务、技术指标、风险、ESG |
| `news` | ✅ | 新闻资讯、公司公告、热点事件 |
| `edb` | ✅ | 宏观经济/行业经济指标（为 market_env 预留） |
| `fund` | ❌ | 本项目不做基金分析 |

---

## 12. 技术指标

iFind 的 `get_stock_info` 直接返回已计算好的 RSI/MACD/MA 等指标，数据精准可靠。项目不再自行实现技术指标计算逻辑，原 `fetcher.py` 中手动计算的 MA/MACD/RSI 代码全部删除。

---

## 13. 资金面

和 market_data 合并，不单独建目录。iFind 可拿到资金流向、换手率等资金面数据，归入行情数据统一管理。

---

## 14. 测试策略

**严格 TDD**：先写测试再写实现。旧 `test_stock_agent.py` 测试的是旧 fetcher + 旧 skills，全部重写。

---

## 15. 开发方式

- **隔离环境**：在 git worktree (`ifind-refactor`) 分支上开发，与主分支完全隔离。worktree 下的所有文件均可直接改动，不需要保留旧文件做"并行共存"。
- **删除清单**（开发过程中直接执行）：
  - `stock_agent/fetcher.py`
  - `stock_agent/skills/` 整个目录（7 个文件）
  - `stock_agent/experiment_a.py`
  - `backend/tests/test_stock_agent.py`（重写）
  - `analyze.py` 中的旧 prompt 常量（`ROLE_DEFINITION`/`CORE_RULES`/`OUTPUT_SCHEMA`/`build_prompt()`/`build_system_prompt()`）
  - `analyze.py` 中的 `render_markdown()`（抽出到 `render.py`）
- 跑通验证后，将 worktree 分支合并回主分支。

---

## 16. 待定事项

- JSON Schema 重新设计（后续单独讨论）
- 开发阶段顺序（后续单独讨论）
- 旧文件删除时机（跑通后再决策）
