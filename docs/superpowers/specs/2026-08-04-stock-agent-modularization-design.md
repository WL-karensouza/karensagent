# stock_agent 目录模块化重构设计

日期：2026-08-04
状态：已批准
范围：`backend/stock_agent/` 目录结构与代码拆分，不影响任何功能

## 1. 背景与目标

`stock_agent/` 目录当前有 16 个 .py 文件共约 3489 行，其中几个文件严重过载、职责混杂：

| 文件 | 行数 | 问题 |
|---|---|---|
| `skill/report.py` | 912 | 20 个函数身兼 5 职：维度配置/数据采集/文本解析/指标格式化/主入口 |
| `analyze.py` | 565 | 9 个函数混含：LLM 分析主流程/JSON 解析容错/报告修复/飞书推送 |
| `models.py` | 470 | 6 个领域模型 + 1 异常 + 工具函数混杂在单文件 |
| `skill/__init__.py` | 241 | 混含 client 调用 + 响应解析 + 格式化 |

**目标**：按"采集层/分析核心层/数据模型/提示词资产"分层重组目录，让每个文件职责单一、可查看可维护且美观，**同时严格不改变任何对外行为**。

## 2. 设计原则

- **分层**：datasources → skill(采集) → core(分析) → models/prompts(资产)，单向依赖，无循环
- **兼容红线**：外部 import 路径全部保持不变（通过 `__init__.py` re-export），路由/测试/数据库代码零改动
- **函数归属**：以现有函数调用依赖图为唯一依据，不重写逻辑、不改变签名
- **YAGNI**：不做无业务价值的额外抽象，models 的 `_util` 只为消除跨模块重复引用

## 3. 目标目录结构

```
backend/stock_agent/
├── __init__.py              # 包入口 + 公开 API re-export（路由/外部引用唯一入口）
│
├── datasources/             # ── 外部数据源 ──
│   ├── __init__.py
│   └── eastmoney.py         # _get_name_eastmoney/_get_name_tencent/_fetch_ohlcv_eastmoney（原样）
│
├── skill/                   # ── 采集层：iFinD SKILL ──
│   ├── __init__.py          # re-export call_skill/extract_text/extract_raw
│   ├── client.py            # 原 skill/__init__.py 拆出：SKILL_DIR 注入 + call_skill + list_skill_tools
│   ├── extract.py           # 原 skill/__init__.py 拆出：extract_text/extract_raw/_format_table/_format_news
│   ├── indicators.py        # 技术指标计算（原样保留）
│   ├── collect.py           # report.py 拆出：DIMENSIONS/采集编排/_call_dim_with_retry/_build_params/_resolve_summary_query/_dimensions_for/_news_time_params/_strip_error_prefix
│   ├── parse.py             # report.py 拆出：_parse_tsv_sections/_raw_to_prose/_table_rows_to_prose/_format_news_prose/_name_from_pipe_table/_extract_stock_name/_parse_ohlcv_table/_clean_header
│   ├── format.py            # report.py 拆出：_format_indicators_markdown/_enrich_performance/_format_sse/_market_suffix/normalize_stock_code
│   └── report.py            # 门面：generate_report_sync/generate_report_stream（只留采集编排+SSE流）
│
├── core/                    # ── 分析核心层 ──
│   ├── __init__.py
│   ├── analyze.py           # 原 analyze.py 精简：analyze/analyze_with_validation/push_to_feishu
│   ├── parser.py            # analyze.py 拆出：_parse_json/_extract_outermost_json/_bracket_completion_suffix/_dump_parse_failure
│   ├── repair.py            # analyze.py 拆出：_repair_report/_add_usage
│   ├── validator.py         # 校验（原样迁移）
│   ├── render.py            # Markdown 渲染（原样迁移）
│   └── history.py           # 历史对比（原样迁移）
│
├── models/                  # 原 models.py（470行）拆成子包
│   ├── __init__.py          # re-export 全部公开符号（DataIncompleteError/6类/_iter_fields）
│   ├── base.py              # DataIncompleteError + IfindRecord + ParsedData
│   ├── market.py            # MarketData + FinancialsData
│   ├── shareholders.py      # ShareholderData
│   ├── news.py              # NewsEventsData
│   ├── risk.py              # RiskData
│   ├── env.py               # MarketEnvData
│   └── _util.py             # _iter_fields / _TABLE_META_KEYS
│
└── prompts/                 # ── 提示词资产（原样保留）──
    ├── __init__.py
    ├── role_definition.py
    ├── core_rules.py
    └── output_schema.py
```

## 4. 拆分映射

### 4.1 skill/report.py（912 行）→ skill 包 4 文件

| 原函数 | 新位置 |
|---|---|
| `DIMENSIONS` / `HK_DIMENSIONS` / `RATE_LIMIT_INTERVAL` / `_dimensions_for` / `_news_time_params` / `_resolve_summary_query` / `_strip_error_prefix` / `_call_dim_with_retry` / `_build_params` | `skill/collect.py` |
| `_parse_tsv_sections` / `_clean_header` / `_table_rows_to_prose` / `_format_news_prose` / `_raw_to_prose` / `_name_from_pipe_table` / `_extract_stock_name` / `_parse_ohlcv_table` | `skill/parse.py` |
| `_format_indicators_markdown` / `_enrich_performance` / `_format_sse` / `_market_suffix` / `normalize_stock_code` | `skill/format.py` |
| `generate_report_sync` / `generate_report_stream` | `skill/report.py`（门面） |

**模块内 import 变更**：`report.py` 原 `from ..datasources.eastmoney import ...` 与 `from .indicators import ...` 保留在 `collect.py`/`parse.py`/`format.py` 中，`report.py` 改为 `from .collect import _call_dim_with_retry, _dimensions_for, ...` 等。

### 4.2 analyze.py（565 行）→ core 包 3 文件

| 原函数 | 新位置 |
|---|---|
| `analyze` / `analyze_with_validation` / `push_to_feishu` | `core/analyze.py` |
| `_parse_json` / `_extract_outermost_json` / `_bracket_completion_suffix` / `_dump_parse_failure` | `core/parser.py` |
| `_repair_report` / `_add_usage` | `core/repair.py` |

`core/analyze.py` 从 `core/parser.py`、`core/repair.py`、`core/validator.py`、`core/render.py`、`core/history.py` import；保留原 analyze.py 的 `.env` 读取与 `FEISHU_WEBHOOK_URL`、`build_system_prompt`/`build_user_prompt`（来自 prompts 包）。

### 4.3 skill/__init__.py（241 行）→ client.py + extract.py

| 原函数 | 新位置 |
|---|---|
| `SKILL_DIR` 注入 / `call_skill` / `list_skill_tools` | `skill/client.py` |
| `extract_text` / `extract_raw` / `_format_table` / `_format_news` | `skill/extract.py` |

`skill/__init__.py` 改为 re-export：`from .client import call_skill, list_skill_tools`、`from .extract import extract_text, extract_raw`。

### 4.4 models.py（470 行）→ models 子包

| 原类/函数 | 新位置 |
|---|---|
| `DataIncompleteError` / `IfindRecord` / `ParsedData` | `models/base.py` |
| `MarketData` / `FinancialsData` | `models/market.py` |
| `ShareholderData` | `models/shareholders.py` |
| `NewsEventsData` | `models/news.py` |
| `RiskData` | `models/risk.py` |
| `MarketEnvData` | `models/env.py` |
| `_iter_fields` / `_TABLE_META_KEYS` | `models/_util.py` |

`models/__init__.py` re-export 全部符号；各模型模块从 `.util import _iter_fields, _TABLE_META_KEYS`（或 `.base import` 基础类）。

## 5. import 兼容策略

### 5.1 外部消费者（零改动）

所有现存外部引用路径保持不变，靠目标模块 `__init__.py` re-export 承接：

| 外部引用 | 承接模块 |
|---|---|
| `from stock_agent.analyze import analyze/analyze_with_validation/push_to_feishu/_parse_json/_repair_report/...` | `stock_agent/__init__.py` re-export 自 core 包 |
| `from stock_agent.render import render_markdown` | `stock_agent/__init__.py` re-export 自 core/render |
| `from stock_agent.validator import validate_report/...` | `stock_agent/__init__.py` re-export 自 core/validator |
| `from stock_agent.history import ...` | `stock_agent/__init__.py` re-export 自 core/history |
| `from stock_agent.skill.report import generate_report_sync/...` | `skill/report.py`（门面） |
| `from stock_agent.skill import call_skill/extract_text/extract_raw` | `skill/__init__.py` re-export |
| `from stock_agent.skill.indicators import _calc_*` | `skill/indicators.py`（原样） |
| `from stock_agent.skill import report as rp` | `skill/report.py`（门面） |
| `from stock_agent.datasources.eastmoney import ...` | `datasources/eastmoney.py`（原样） |
| `from stock_agent.models import ...` | `models/__init__.py` re-export |
| `from stock_agent.prompts import ...` | `prompts/__init__.py`（原样） |

> **注意**：`analyze.py` 原有的 `from stock_agent.render import render_markdown  # noqa: F401 — 保持向后兼容` 一行，拆分后 render 移入 core，该 re-export 需在 `stock_agent/__init__.py` 或保留在 core/analyze.py 中补回，确保 `from stock_agent.analyze import render_markdown` 仍可用（若有代码依赖此兼容路径）。

### 5.2 测试兼容

- `tests/test_models.py` 的 `from stock_agent.models import _iter_fields` 等 —— 由 `models/__init__.py` re-export `_iter_fields`
- `tests/test_skill_extract.py` 的 `from stock_agent.skill import extract_text/extract_raw` —— 由 `skill/__init__.py` re-export
- 其余测试对 `skill.report`/`analyze`/`render`/`validator`/`history`/`indicators` 的引用 —— 路径不变

## 6. 验证策略

1. **全量 pytest**：`cd backend && python -m pytest tests -q` 需 191 passed 零回归
2. **残留引用检查**：`grep -rn "modular\|reviewer\|ifind_client\|fetchers\." --include="*.py" .` 应为空（无旧残留）
3. **import 冒烟**：`python -c "from stock_agent.analyze import analyze; from stock_agent.skill.report import generate_report_sync; from stock_agent.models import MarketData; from stock_agent.skill import call_skill, extract_text; print('OK')"`
4. **生产入口检查**：`routers/stock_api.py`、`main.py` 对 stock_agent 的引用全部仍可解析

## 7. 非目标（明确不做）

- 不重写任何业务逻辑、不改变任何函数签名与行为
- 不动 backend 根目录 `models.py`（数据库 ORM：PushHistory/StockReport/StockWatchlist）
- 不拆分 `prompts/`（28-114 行，内聚度已够）
- 不做 UI 前端相关改动
