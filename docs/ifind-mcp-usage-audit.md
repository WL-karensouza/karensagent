# iFinD MCP 使用情况全方位审计报告

> 生成日期：2026-08-01
> 审计范围：对照「官方文档」+「本地 skill 定义（v1.3.0）」+「真实工具清单实证」+「项目代码实际调用」四源
> 结论速览：**项目整体使用方向正确**（服务/工具/参数/限速基本合规），但存在 **3 个值得修正的偏差** 和 **1 个文档不一致点**，详见下文。

---

## 一、审计方法

| 来源 | 说明 | 证据 |
|---|---|---|
| 官方文档 | mcp.51ifind.com 产品介绍/数据范围 | 用户提供（MCP 配置示例 + 数据范围概述） |
| 本地 skill | C:\Users\王磊\.claude\skills\ifind-finance-data（官方发布 v1.3.0） | SKILL.md + 7 个子服务参考文档 |
| 真实清单 | 实际调用 `list_tools()` 拉取 | 本次实证 |
| 项目代码 | backend/stock_agent/ | 逐文件审查 |

**实证记录（本次审计实时执行）：**
- `list_tools('stock')` → 10 个工具，与本地文档完全一致
- `list_tools('global_stock')` → 4 个工具（**本地文档写了 5 个，多一个 `search_global_stocks`**）
- `list_tools('news')` → 2 个工具（**本地文档写了 3 个，多一个 `search_trending_news`**）
- `list_tools('fund')` → 7 个工具，与本地文档一致
- `list_tools('index')` → 3 个工具，与本地文档一致
- `stock_highfreq_quotes` 真实调用 → 返回 `code:1, msg:"success"`，data 含 `tables`/`indicatorMap`，**与项目 `extract_text`/`extract_raw` 的解析逻辑完全吻合**
- `search_news` 真实调用 → 返回结构化新闻数组，**`time_start`/`time_end`/`size` 均为必填，与项目传参一致**
- `search_news` inputSchema 实证 → `query`/`size`/`time_end`/`time_start` 全必填，`size` 默认 5、上限 20
- 北交所代码 `830799.BJ` 走高频行情 → 返回 `code:1` 但 data 提示「未找到相关证券指标」

---

## 二、项目使用全貌（代码证据）

### 调用链路
```
main.py health_check  → call_skill("stock", "stock_highfreq_quotes", ...)
report.py 10维度     → call_skill(server, tool, params)  × N
skill/__init__.py    → from call import call (官方脚本, sys.path 注入)
call.py / call-node.js → POST https://api-mcp.51ifind.com:8643/ds-mcp-servers/{svc}
```

### 使用的服务与工具（report.py DIMENSIONS / HK_DIMENSIONS）
| 服务 | 用到的工具 | 用途 |
|---|---|---|
| stock | get_stock_summary, get_stock_performance, get_stock_financials, get_stock_shareholders, get_risk_indicators, get_esg_data, get_stock_events, stock_highfreq_quotes | A股 8 维度 |
| news | search_news, search_notice | 新闻/公告 |
| global_stock | global_stock_profile, global_stock_quotes, global_stock_financial, global_stock_events | 港股 8 维度 |

---

## 三、异同点逐条核对

### ✅ 完全合规（与官方文档一致）

| # | 对照点 | 官方要求 | 项目实际 | 结论 |
|---|---|---|---|---|
| 1 | 认证方式 | HTTP Header `Authorization: YOUR_MCP_KEY` | call.py 在 headers 里加 `Authorization: AUTH_TOKEN` | ✅ 一致 |
| 2 | 传输协议 | streamablehttp | call.py 用 POST + JSON-RPC（initialize → tools/call） | ✅ 一致 |
| 3 | 服务 URL | `https://api-mcp.51ifind.com:8643/ds-mcp-servers/hexin-ifind-ds-stock-mcp` | call.py 内 base 与 7 个服务路径**逐字一致** | ✅ 一致 |
| 4 | 工具名 | 由各子服务文档定义 | 项目使用的 8 个 stock 工具、2 个 news 工具、4 个 global_stock 工具**全部在真实清单内**（已实证） | ✅ 一致 |
| 5 | 自然语言工具参数 | `{"query": "..."}` | `_build_params` 对非行情工具统一构造 `{"query": ...}` | ✅ 一致 |
| 6 | 高频行情工具参数 | `symbols`/`indicators`/`data_mode`，data_mode 必填 | report.py:94-100 用结构化参数，显式 `data_mode:"real_time"` | ✅ 一致 |
| 7 | news 时间参数 | `time_start`/`time_end`/`size` 必填 | `_news_time_params` 构造，size=5/8（<20 上限） | ✅ 一致 |
| 8 | 并发限速 | 免费版 2 QPS | `RATE_LIMIT_INTERVAL=0.6s` ≈ 1.67 QPS | ✅ 在限内 |
| 9 | 多主体限制 | query 不宜超 5 个主体/指标 | 单维度 query 均单主体 | ✅ 在限内 |
| 10 | 响应解析 | 返回 `{code:1, data:{tables/indicatorMap/...}}` | extract_text/extract_raw 按 tables/answer/data 分支解析 | ✅ 匹配实证 |

### ⚠️ 值得关注的偏差

#### 偏差 1：北交所代码走高频行情工具查不到数据
- **证据**：项目 `_market_suffix`（report.py:156-168）把 8/4 开头判为 `.BJ`；实证 `830799.BJ` 调 `stock_highfreq_quotes` 返回 `code:1` 但 data 提示「未找到相关证券指标」
- **影响**：北交所股票的「实时行情」维度会静默失败（不报错，但无数据），报告缺失行情且无明显提示
- **官方立场**：官方高频行情工具文档（quotes.md）未明确列北交所，但 A 股服务理论上应覆盖；实测不返回数据
- **建议**：北交所代码要么明确在 `_market_suffix` 里走 `get_stock_performance` 等自然语言工具兜底，要么在 UI 标注北交所实时行情不可用

#### 偏差 2：健康检查用高频行情工具做连通性探测
- **证据**：main.py:83-87 调 `stock_highfreq_quotes({"symbols":"600519.SH",...})` 判断 ifind 是否连通
- **官方立场**：SKILL.md「核心函数」与参考文档把高频行情列为「实时/高频」用途，未规定其为连通性探测手段
- **影响**：低频次（健康检查）用高频工具，每次初始化 + tools/list + call，较重；且若用户权限无高频权益，健康检查会误判为「未连接」
- **建议**：改用轻量的 `get_stock_summary` 或 `get_stock_info` 做连通性探测（自然语言单次查询），更贴合权限校验语义

#### 偏差 3：东财兜底数据源（公司名 + OHLCV + 自算指标）
- **证据**：
  - report.py:446-448 公司名提取失败 → `_get_name_eastmoney()`
  - report.py:624-638 OHLCV 优先用东财、失败才 fallback iFinD
  - indicators.py 全套 MA/MACD/BOLL/RSI/KDJ 为项目自算（非 iFinD 提供）
- **官方立场**：iFinD MCP 定位「可直接调用的数据服务」，但官方并未承诺「唯一数据源」；东财免费 HTTP 接口是项目自行引入的补充
- **影响**：**不违背官方规范**（只是多了一个并行的免费数据源），但存在两个隐患：
  1. **数据一致性风险**：东财前复权日K 与 iFinD 数据口径可能有细微差异，报告中同一指标可能两处来源不同
  2. **维护成本**：东财接口无官方 SLA，字段格式变更需人工跟踪
- **建议**：报告页明确标注每段数据来源（东财 / iFinD），或对关键指标统一数据源

### ❌ 本地 skill 文档与真实清单不一致（非项目误用，但影响排障）

| 服务 | 本地参考文档 | 真实清单 | 差异 |
|---|---|---|---|
| global_stock | 5 个（含 `search_global_stocks`） | 4 个 | **文档多写了 `search_global_stocks`** |
| news | 3 个（含 `search_trending_news`） | 2 个 | **文档多写了 `search_trending_news`** |

> 项目**没有**用到这两个不存在的工具，所以不受影响；但如果未来按文档写死这两个工具名会直接报错。SKILL.md 明确说「文档与实际不一致时用 `list_tools` 获取真实清单」，建议排障时优先看真实清单。

---

## 四、结论与建议

**总体评价**：项目对 iFinD MCP 的**使用方向完全正确**——认证、协议、服务 URL、工具名、参数格式、限速、响应解析都与官方规范吻合，没有"用错接口"级别的错误。您感觉"使用错误"的部分，主要是**数据覆盖边界（北交所）**和**数据源混用（东财兜底）**带来的不确定性，而非调用方式错误。

### 建议优先级
1. **P1（功能正确性）**：北交所股票实时行情静默失败 → 加兜底或 UI 标注
2. **P2（可维护性）**：健康检查改用轻量自然语言工具；报告标注数据来源
3. **P3（文档同步）**：本地 global_stock/news 参考文档与实际清单有出入，可在排障时依赖 `list_tools` 而非文档

---

## 五、附：实证脚本与关键行号索引

| 证据 | 位置 |
|---|---|
| DIMENSIONS 定义 | [report.py:23-34](backend/stock_agent/skill/report.py#L23-L34) |
| HK_DIMENSIONS 定义 | [report.py:38-59](backend/stock_agent/skill/report.py#L38-L59) |
| _build_params 参数构造 | [report.py:81-139](backend/stock_agent/skill/report.py#L81-L139) |
| RATE_LIMIT_INTERVAL=0.6 | [report.py:62](backend/stock_agent/skill/report.py#L62) |
| _market_suffix 北交所判定 | [report.py:156-168](backend/stock_agent/skill/report.py#L156-L168) |
| 东财公司名兜底 | [report.py:446-448](backend/stock_agent/skill/report.py#L446-L448) |
| 东财 OHLCV 优先 | [report.py:624-638](backend/stock_agent/skill/report.py#L624-L638) |
| 自算指标 | [indicators.py](backend/stock_agent/skill/indicators.py) |
| 健康检查 | [main.py:77-91](backend/main.py#L77-L91) |
| skill 封装 | [skill/__init__.py:22-39](backend/stock_agent/skill/__init__.py#L22-L39) |
