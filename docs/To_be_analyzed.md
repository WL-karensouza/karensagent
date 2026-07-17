# 待分析：get_stock_info 无法获取的指标

> 以下指标在 get_stock_info 中丢失或不稳定，需要找到正确的 iFinD MCP 接口来获取。

## 多周期均线

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| MA5/MA10/MA20/MA60 | 只返回 MA5 | 一个 query 只能指定一个周期，多周期需多次调用或换接口 |

## 多周期涨跌幅

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| 5日涨跌幅 / 10日涨跌幅 / 20日涨跌幅 | 只返回一个 N日涨跌幅 | 600398 返回了 5日，688221 数据解析错位，不稳定 |

## RSI

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| RSI 相对强弱指标 | get_stock_info 将 "RSI" 映射为 "RC变化率指数" | RC（Rate of Change）和 RSI 是完全不同指标，含义完全错误 |

## BOLL 布林线（完整）

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| BOLL 上轨 / 下轨 | 只返回 BOLL 中轨（MID） | 缺压力位和支撑位参考 |

## MACD（完整）

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| DIF / DEA | 只返回 MACD 柱状值 | 金叉死叉判断需要 DIF 和 DEA 的交叉关系 |

## KDJ（完整）

| 需求指标 | 当前状态 | 问题 |
|---|---|---|
| KDJ K/D/J 三值 | 只返回 K 值 | 缺 D 值和 J 值，无法判断超买超卖交叉 |

---

## get_stock_summary 多表解析错位

| 问题 | 说明 |
|---|---|
| parse_markdown_to_records 无法正确处理多张独立表格 | get_stock_summary 固定返回 5 张表（基本信息/行业分类/市值规模/估值水平/IPO信息），各表列名不同，当前解析器只取第一张表的列名作为 header，后续表的值被塞入错误字段 |
| 修复方向 | fetcher 改用 `call_raw_text` 拿原始 markdown 直接喂给 LLM，不走 parser 拆成 dict |

---

## get_stock_financials ✅ 已完成

| 特点 | 说明 |
|---|---|
| 默认取 MRQ | 指标默认取"最新一期(MRQ)"报告期，若最新季报未发布则字段为空 |
| TTM 指标不受报告期限制 | 带 `(TTM)` 后缀的指标（如 ROE(TTM)、毛利率(TTM)）始终有值，因 TTM 滚动计算不依赖单季报 |
| 多报告期返回 | 一次查询返回 3 个报告期（最新→次新→最早），最早报告期通常数据最全 |
| 母公司后缀不可用 | 带 `-母公司` 后缀的字段永远空值，A 股上市公司通常不单独披露母公司报表指标 |
| 取值策略 | ~~取第一条非全空行~~ → **改为跨报告期合并（_merge_records）：每个字段取所有行中第一条非空值，TTM 取最新期，MRQ 取最早已发布财报期** |
| to_prompt_context 适配 | 财务字段以 `field_name: value` 形式直存 dict，渲染时遍历所有非 meta 键值对；股东数据按十大股东排名分组输出 |
| 最终 query | `净资产收益率ROE(TTM)、总资产净利率ROA(TTM)、销售毛利率(TTM)、销售净利率(TTM)、归属母公司股东的净利润同比增长率、营业总收入同比增长率、资产负债率、流动比率、速动比率、经营活动产生的现金流量净额(TTM)、每股企业自由现金流量、基本每股收益、每股净资产、股息率` |
| 合并后覆盖 | 600398: 16 字段（覆盖盈利/成长/偿债/现金流/估值五维度）；688221: 16 字段 |

---

## 排查方向

- iFinD stock server 是否有专用的技术指标接口（如 `get_technical_indicators`）
## get_stock_shareholders ✅ 已完成

| 特点 | 说明 |
|---|---|
| 关键词敏感 | query 关键词决定返回哪些字段（与 get_stock_summary 不同），精简 query 会丢失机构持股/流通股东等字段 |
| MRQ 空值 | 与 get_stock_financials 相同：最新报告期汇总字段为空，但中间报告期可能有占位垃圾值（如机构持股 0.0002） |
| 占位值陷阱 | 20260630 的「机构持股比例合计」= 0.0002，`_merge_records` 正序遍历会把占位值当作"第一条非空"，导致真实数据被忽略 |
| 解决方案 | 复用 `_merge_records()`，但**反转记录顺序**（最旧→最新），确保完整真实值先写入，新报告期空值/占位值不覆盖 |
| 流通股占比 | ❌ 无效关键词，改用"流通股"触发十大流通股东字段 |
| 十大流通股东 | ❌ 不触发，"流通股东"单独用会产生 101+ 条记录异常，"流通股"组合用正常 |
| 最终 query | `{stock_code} 前十大股东持股比例 机构持股比例 流通股 股东人数 户均持股` |
| to_prompt_context | 汇总指标（股东户数/前十大持股/机构持股/户均持股）+ 十大股东 + 十大流通股东 |

---

## 报告期（report_date）识别 ✅ 已完成

### 背景

`get_stock_financials` 和 `get_stock_shareholders` 的数据完整性依赖财报的正式发布时间。只有季报/年报正式发布后，MRQ（Most Recent Quarter）字段才有值。因此后端必须向模型实例写入正确的报告期日期（如 `20260331`），供前端展示"数据截止到哪个季度"。

### 核心问题：预览期 vs 正式发布期

iFind 返回的记录按日期倒序排列（最新→最旧），但最新的 1~2 条记录通常是**预览期**——上市公司已披露部分快报数据但尚未正式发布完整财报：

```
get_stock_financials（600519）各期非空字段数：
  [0] date=20260930  非空=4/29   ← 预览期（三季报未发布，仅 TTM 字段有值）
  [1] date=20260630  非空=4/29   ← 预览期（中报未发布）
  [2] date=20260331  非空=15/29  ← ✅ 一季报已正式发布

get_stock_shareholders（600519）各期汇总字段：
  [0] date=20260930  前十大持股=空   机构持股=空     ← 预览期
  [1] date=20260630  前十大持股=空   机构持股=0.0002 ← 预览期（0.0002 为占位垃圾值）
  [2] date=20260331  前十大持股=68.51 机构持股=72.60 ← ✅ 已正式发布
```

如果直接取 `records[0]["日期"]` 会得到 `20260930`（预览期），这明显是错的——当前是 7 月，最新正式发布的是 2026 年一季报 `20260331`。

### 方案探索（均已验证不可行）

| 尝试 | 做法 | 结论 |
|---|---|---|
| query 中加"报告期"关键词 | 如 `{stock_code} 报告期 ROE 资产负债率` | ❌ 无新增字段，接口无此语义 |
| query 中加"发布时间/公告日期/披露日期" | 六种日期相关说法全试 | ❌ 均无新增字段 |
| query 中加"截止日期/报表日期/会计期间" | 继续尝试补充 | ❌ 均无新增字段 |
| query 中加"已披露/定期报告/最新财报"过滤 | 想只返回正式发布的数据 | ❌ 无过滤效果 |
| query 中加"最近一期" | 想直接拿到最新发布的 | ❌ 只返回 1 条，恰好是预览期 |
| 非空字段占比阈值法 | 以 max_filled × 95% 为门槛判断正式发布 | ⚠️ 可行但过度设计，threshold 和 ratio 参数需要调参 |

**结论：`get_stock_financials` 和 `get_stock_shareholders` 均不支持按"发布时间"过滤，也没有"报告期名称"字段。只能靠算法从返回结果中推断。**

### 最终方案：marker 字段探测法

```python
def _find_report_date(records: list[dict], marker: str) -> str:
    """从最新往旧遍历，第一条 marker 字段有值的记录就是最近正式发布期。"""
    for r in records:
        val = r.get(marker, "")
        if val and val.strip():
            return r.get("日期", "")
    return ""
```

**算法逻辑（3 步）：**

1. iFind 返回多条记录，最新日期在最前（`records[0]` 是最近期），最旧在最后
2. 从最新往旧遍历每条记录，检查 `marker` 字段是否有非空值：
   - 有值 → 说明该期财报已正式发布，返回日期
   - 空值 → 该期为预览期，继续往前找
3. 全部为空 → 说明所有记录都是预览期（如小公司只返回 1 条预览数据），返回 `""`

**marker 字段选择策略：**

| 接口 | marker 字段 | 选择理由 |
|---|---|---|
| `get_stock_financials` | `基本每股收益（单位：元）` | MRQ 类指标，季报正式发布后才会有值，预览期必然为空 |
| `get_stock_shareholders` | `前十大股东持股比例合计（单位：%）` | 季报正式发布后才统计，预览期为空；不选"机构持股比例合计"因为它在 20260630 有占位垃圾值 `0.0002` |

**marker 选取原则（3 条铁律）：**

1. **必须是被 query 触发的字段**：不同 query 关键词下字段名不同，marker 字段名必须与实际 query 返回的完全一致
2. **必须是 MRQ 类字段（非 TTM）**：TTM 字段（如"净资产收益率ROE(TTM)"）在预览期也有值，不能作为正式发布的判断依据
3. **必须不会有占位垃圾值**：如 shareholders 的"机构持股比例合计"在 20260630 有占位值 `0.0002`，会误判为已发布，所以选"前十大股东持股比例合计"（同期为空）

**容错设计：**

- `records` 全部为预览期（如 688221 financials 仅返回 1 条记录且 MRQ 字段全空）→ `_find_report_date` 返回 `""`，`FinancialsData.report_date` 为 `""`，前端展示"暂无"
- `records` 为空列表 → `_find_report_date` 返回 `""`
- marker 字段名因 query 变化而不同 → 每条 fetcher 独立传入自己的 marker，互不影响

### 实际验证

```
600519: financials.report_date → 20260331 ✅
        (预览 20260930 EPS 空 → 跳过, 预览 20260630 EPS 空 → 跳过)
        shareholders.report_date → 20260331 ✅
        (预览 20260930 前十大空 → 跳过, 预览 20260630 前十大空 → 跳过)

688221: financials.report_date → "" ✅
        (仅 1 条 20261231 预览记录，基本每股收益字段不存在，返回空)
        shareholders.report_date → 20260331 ✅
```

### 与 _merge_records 的配合

`_find_report_date`（取最新正式发布期日期）和 `_merge_records`（跨报告期合并字段值）各司其职：

- `report_date` 告诉前端"这是哪一季度的数据"——取最**新**的一个已发布期的日期
- `_merge_records` 告诉 LLM"这只股票财务全貌如何"——正序遍历取最新 TTM + 反向兜底取最早 MRQ 值

---

## get_edb_data ✅ 已完成

### 接口特征

- EDB server 仅一个工具：`get_edb_data`
- 返回 markdown 时间序列表（`日期 | 指标名(单位)`），每行一个时间点
- 与 `get_stock_performance` 不同，没有"模式切换"问题，始终是时间序列
- 关键词越多，返回行数越少（不同指标发布频率不同，按最短的交集截断）

### 核心发现：行业关键词"霸权"行为

行业关键词一旦与宏观关键词共存于同一条 query，必有一方被吞并：

| 合并 query | 结果 |
|---|---|
| `半导体行业景气度 中国PMI M2增速` | PMI、M2 全丢，只剩费城半导体指数（4列） |
| `白酒行业景气度 中国PMI M2增速` | 白酒被吞，只剩 PMI 和综合PMI |
| `社会融资规模 M2增速` | 社融被吞，只剩 M2 |
| `中国PMI M2增速` | ✅ 稳定共存 |
| `中国PMI M2增速 社会融资规模 CPI` | ✅ 四项全有效（37行） |

### 单关键词验证（11个全有效）

| 关键词 | 返回列 | 行数 |
|---|---|---|
| 中国PMI | 制造业PMI(%) | 60 |
| M2增速 | M2同比(%) | 60 |
| 社会融资规模 | 社会融资规模(元) | 24 |
| CPI | CPI | 36 |
| GDP增速 | GDP同比(%) | 36 |
| 工业增加值 | 工业增加值(元) | 27 |
| 半导体行业景气度 | 半导体销售额:全球:当月同比(%) | 60 |
| 白酒行业景气度 | 白酒价格指数 | 60 |
| 行业景气度 | 降级为制造业PMI | 60 |
| 美国GDP | 美国GDP(美元) | 36 |
| 美联储利率 | 联邦基金利率(%) | 60 |

### 最终方案：两次独立调用

```python
# 调用1：核心宏观（始终调用，4指标共存37行）
"中国PMI M2增速 社会融资规模 CPI"

# 调用2：行业专项（仅有行业时调用，与宏观分离避免互相吞并）
"{industry}行业景气度"
```

### 设计理由

1. 行业关键词是"贪婪"的 — 会展开成多列并排挤掉宏观指标
2. `社会融资规模` 单独和 M2 共存时会被吞，但四项一起就能共存
3. 分离调用后各 query 关键词在各自领域内，不会互相竞争

### 实施文件

- [market_env/fetcher.py](backend/stock_agent/fetchers/market_env/fetcher.py) — 拆分两次调用
- 探查脚本：[probe_edb_v1.py](backend/tests/probe_edb_v1.py)、[probe_edb_v2.py](backend/tests/probe_edb_v2.py)、[probe_edb_v3.py](backend/tests/probe_edb_v3.py)
- 探查结果：[probe_results/edb_v1_*.json](backend/tests/probe_results/)、[probe_results/edb_v2_*.json](backend/tests/probe_results/)

---

## get_stock_performance ✅ 已完成

### 接口特征

- 内部有"模式切换"行为：日频关键词（收盘价/涨跌幅/成交额/成交量）触发多行日序列模式，区间关键词（近一年涨跌幅）触发单行汇总模式
- 混合两类关键词会导致不可预测的行为（列错位、空返回等）

### 不稳定关键词（全部失败）

融资余额、融券余额、今年以来涨跌幅、近一月涨跌幅、相对大盘涨跌幅、年化收益率、年化波动率、年化夏普比率、最大回撤、MA5/10/20/60、DIF、DEA、RSI

### 最终 query

```python
"{stock_code} 收盘价 涨跌幅 成交额 成交量 近一年涨跌幅"
```

5 字段，1 次调用，5 只股票（600519/688981/002371/600905/300369）全部无窜行。

### 迁移到 market_data

已从 `market_env/fetcher.py` 迁移到 `market_data/fetcher.py` 作为独立函数 `fetch_stock_performance()`，与 `fetch_market_data()`、`fetch_stock_summary()` 并列管理。

---

## get_stock_events ✅ 已完成

### 接口特征

- **关键词切换型接口**：不同关键词触发完全不同的表结构（比 EDB 的模式切换更极端），不像 EDB 那样尝试合并列
- **"赢家通吃"行为**：多关键词共存时，某个关键词"胜出"占据整个返回结构，其他关键词的字段全部丢弃
  - 关键词越多，丢失越严重
  - 与 EDB 不同：EDB 是某些关键词被"吞并"，这里是只有一方存活
- 返回 markdown 表格 + 字段参数 JSON 元数据

### 三种 query 格式对比

| 格式 | 示例 | 结果 |
|---|---|---|
| 空格分隔 | `600519 分红 增发 回购` | 1 张表，仅 1 个关键词胜出 |
| 管道分隔 | `600519 分红送转\|回购\|增发` | 2 张表，56 字段 |
| **自然语言 prompt** | `请返回600519的重大事件综合数据，包括…` | **2 张表，61 字段 🥇** |

### 单关键词验证（Round 1，24 个 keyword × 3 只股票）

**数据丰富型（≥3 行）：** 分红、回购、股权激励、业绩快报、股东减持、股东增持、限售解禁、股权质押、违规处罚、重大诉讼、关联交易、送转、现金分红

**稀疏型（1 行）：** 增发、重大资产重组、业绩预告、配股、可转债、大宗交易、监管函、停牌、投资者调研

**错配/无效：** 重大合同→返回"是否重大资产重组"（字段错配）；对外担保→仅代码+简称（无实际数据）

### 组合关键词验证（Round 2，7 组组合 × 1 只股票）

| 组合 | 关键词数 | 返回 | 实际触发的模式 |
|---|---|---|---|
| baseline_6 (原方案) | 6 | 9 行 / 8 字段 | 回购 + 少量分红 |
| rich_only | 13 | 1 行 / 8 字段 | 仅分红方案（其余 12 个丢失） |
| all_valid | 22 | 10 行 / 5 字段 | 仅分红送转（其余 20 个丢失） |
| dividend_group | 3 | 1 行 / 5 字段 | 分红 |
| buyback_incentive | 2 | 1 行 / 3 字段 | 回购制度（丢了股权激励） |
| regulatory_group | 3 | 1 行 / 11 字段 | 违规处罚（丢了诉讼+监管函） |
| mixed_rich_sparse | 2 | 7 行 / 6 字段 | 回购（丢了增发） |

**结论：每个关键词有独立 schema，多关键词=互斥，无法通过单次关键词组合覆盖。**

### Prompt 格式 A/B 对比

| 格式 | 表数 | 总字段数 |
|---|---|---|
| 纯自然语言 | 2 | **61** |
| 自然语言+管道 | 2 | 57 |
| 纯管道分隔 | 2 | 56 |
| 纯空格分隔 | 2 | 20 |

**纯自然语言胜出。**

### 最终方案：1 次调用 + LLM 总结

```
架构:
  get_stock_events(prompt 自然语言) → raw markdown（2 张表 / 61 字段）
       ↓
  _summarize_events() → DeepSeek Chat 纯数据转述（非投资分析）
       ↓
  NewsEventsData.events = "贵州茅台近年实施了…"（中文总结文本）
       ↓
  to_prompt_context() → 拼入主分析 prompt
```

**最终 query：**
```python
EVENTS_QUERY_TPL = (
    "请返回{stock_code}的重大事件综合数据，包括分红送转、回购、增发、"
    "股权激励、股东减持、股东增持、限售解禁、股权质押、"
    "违规处罚、重大诉讼、关联交易、"
    "业绩快报、大宗交易"
)
```

**LLM 总结层设计要点：**

1. 模型：DeepSeek Chat（轻量），temperature=0，max_tokens=2048
2. 系统 prompt 明确约束：只转述数据事实，不做投资分析、不判断利好利空、不给出买卖建议
3. 容错：无 API key 时降级返回原始 markdown；LLM 调用失败时降级返回原始文本
4. 事件采集异常不阻塞新闻和公告（外层 try/except pass）

**数据流变更：**
- `fetch_events()`：改用 `call_raw_text` 返回原始 markdown 文本
- `NewsEventsData.events`：从 `list[dict]` 改为 `str`（LLM 总结文本）
- `event_count` 属性 → `has_events` 属性
- `to_prompt_context()`：直接输出总结文本，不再遍历 dict 列表

### 实施文件

- [events.py](backend/stock_agent/fetchers/news_events/events.py) — prompt query + call_raw_text
- [__init__.py](backend/stock_agent/fetchers/news_events/__init__.py) — 集成 `_summarize_events()` LLM 总结层
- [models.py](backend/stock_agent/models.py) — NewsEventsData.events 改为 str
- 探查脚本：[probe_events_v1.py](backend/tests/probe_events_v1.py)、[probe_events_v2.py](backend/tests/probe_events_v2.py)、[probe_events_ab.py](backend/tests/probe_events_ab.py)、[probe_events_prompt.py](backend/tests/probe_events_prompt.py)
- 探查结果：[probe_results/events_v1_*.json](backend/tests/probe_results/)、[probe_results/events_v2_*.json](backend/tests/probe_results/)

---

## search_news ✅ 已完成

> 2026-07-12 探查完成，确定最优 query 格式为自然语言 prompt

### 接口特征

- **固定上限接口**：无论传什么参数，最多返回约 10 条新闻，接口有硬上限
- **size 参数无效**：设为 20/50/100/200 均返回同样数量，接口内部统一控制
- **时间范围参数无效**：7 天/30 天/90 天/180 天/365 天均返回同样数量
- **不同股票均返回约 10 条**：茅台/五粮液/中芯/宁德/北方华创结果一致
- 每条新闻固定 5 个字段：`资讯标题` / `资讯内容` / `日期` / `URL` / `备注`
- 返回格式：JSON 数组字符串，末尾附带一条 `备注` 对象说明数据截取策略
- `备注` 内容：`"出于对LLM上下文以及用户token资源的保护，本工具仅输出与查询内容强相关的资讯片段，而非资讯全文…"`

### Query 格式对比

| 格式 | 示例 | 条数 | 内容质量 |
|---|---|---|---|
| 代码 | `600519` | 10 | 碎片化事件 |
| 名称 | `贵州茅台` | 10 | 碎片化事件 |
| 代码+名称 | `600519 贵州茅台` | 10 | 碎片化事件 |
| 代码+关键词 | `600519 财报 分红 回购` | 10 | 碎片化事件 |
| **自然语言 prompt** | `请查询贵州茅台(600519)近30天的重要财经新闻…` | 10 | **多维度覆盖 🥇** |

### Prompt vs Keyword 内容差异

- **keyword 版**：返回关键词命中结果，偏向碎片化事件（分红、招聘、股东会）
- **prompt 版**：返回主题覆盖结果，主动覆盖 prompt 描述的维度（市场化改革→经营动态；行业筑底→机构观点；段永平加仓→股东动态；融资买入→市场数据）

**结论：条数无法突破（都是 ~10 条），但 prompt 让返回内容质量更高、覆盖维度更广。这和 `get_stock_events` 逻辑一致——prompt 不增加数量，而是控制"选什么"。**

### 最终方案

```python
NEWS_QUERY_TPL = (
    "请查询{stock_name}({stock_code})近30天的重要财经新闻与公告，重点关注以下维度："
    "财报业绩（季报年报、业绩预告、业绩快报）、"
    "分红送转（分红方案、除权除息）、"
    "资本运作（回购、增发、并购重组、股权激励）、"
    "股东动态（增减持、质押、解禁）、"
    "经营动态（重大合同、项目进展、新产品、研发突破）、"
    "风险事件（违规处罚、诉讼仲裁、监管问询）、"
    "机构观点（券商研报、评级调整、调研纪要）"
)
```

### 实施文件

- [news.py](backend/stock_agent/fetchers/news_events/news.py) — 新增 `NEWS_QUERY_TPL`，`fetch_news` 签名改为 `(client, stock_code, stock_name)`
- [__init__.py](backend/stock_agent/fetchers/news_events/__init__.py) — 调用方对齐新签名

---

## search_notice ✅ 已完成

> 2026-07-12 探查完成，确定 **不支持 prompt/关键词组合，纯股票代码为最优方案**

### 接口特征

- **不支持自然语言 prompt**：传 prompt 返回空（"搜索内容参数过长或表述过于具体"）
- **不支持多关键词过滤**：代码后加任何额外词（如 `601127 财务披露 分红融资`、管道分隔 `601127|财务披露|…`）均返回空
- **名称+具体词会大幅削减结果**：`赛力斯 担保 回购 股东会…` 只返回 1 条
- **代码为最精准的过滤器**：纯股票代码返回最多（9 条）
- 返回格式与 `search_news` 相同：JSON 数组 + 末尾 `备注` 对象

### Query 格式对比（赛力斯 601127）

| 格式 | 条数 | 结论 |
|---|---|---|
| `601127`（纯代码） | 9 | ✅ **最优** |
| `赛力斯`（纯名称） | 7 | 含代码没有的产销快报，但总数更少 |
| `601127 赛力斯`（代码+名称） | 9 | ✅ |
| `601127 财务披露 分红融资…` | 0 ❌ | 空 |
| `601127\|财务披露\|分红融资\|…` | 0 ❌ | 空 |
| 自然语言 prompt | 0 ❌ | 空 |
| `赛力斯 担保 回购…` | 1 | 被削减到只剩 1 条 |

### 最终方案

**现有实现已是最优，无需修改。** `query: stock_code` 纯代码即可拿到最多公告。

### 实施文件

- [notice.py](backend/stock_agent/fetchers/news_events/notice.py) — 保持现状不变

---

### news / notice / events 三接口对比总结

| 维度 | search_news | search_notice | get_stock_events |
|---|---|---|---|
| **服务器** | news | news | stock |
| **prompt 支持** | ✅ 提升内容质量 | ❌ 空结果 | ✅ 触发多表模式 |
| **多关键词** | 无效 | ❌ 空结果 | ❌ 赢家通吃 |
| **最优 query** | NL prompt | 纯代码 | NL prompt |
| **返回上限** | ~10 条 | ~9 条 | 2 表 60+ 字段 |
| **返回格式** | JSON 数组 | JSON 数组 | markdown 表格 |

---

## get_risk_indicators ✅ 已完成

> 2026-07-12 探查完成，确定 prompt 触发双表模式 + 手动提取汇总表

### 接口特征

- **"赢家通吃"关键词切换**：多关键词共存时只有一个指标族占据返回结构（与 `get_stock_events` 相同行为）
- **prompt 触发双表模式**：传自然语言 prompt 返回 2 张独立 markdown 表格——日频时间序列 + 汇总快照
- 返回 markdown 表格 + JSON 元数据（指标参数说明）
- 关键词模式下只有单张表，字段覆盖不完整

### 四种 query 格式对比（贵州茅台 600519）

| 格式 | 表数 | 字段覆盖 |
|---|---|---|
| `600519 贝塔 夏普比率 波动率 最大回撤` (keyword) | 1 | 单一指标族，其余丢失 |
| 自然语言 prompt（长） | **2** | **Beta + Sharpe + 波动率 + 最大回撤 + Alpha + 年化收益率 + 下行风险 🥇** |
| 自然语言 prompt（偏 Beta） | 1 | 偏 Beta，其余少 |
| 自然语言 prompt（偏评级） | 1 | 字段很少 |

### 双表结构

prompt 返回的 2 张表结构不同：

- **表1 — 日频时间序列**：`证券代码 | 证券简称 | 日期 | 年化收益率(24个月) | 年化收益率(100周)`，多行按日期排列
- **表2 — 汇总快照**：`证券代码 | 证券简称 | 区间下跌天数 | Sharpe | Beta_Alpha | 区间最大回撤 | Beta | 波动率(年化)`，单行汇总值

### 核心问题：多表解析错位

`parse_markdown_to_records` 无法正确处理多张独立表格（同 `get_stock_summary` 已知问题）——两张表列名不同，解析器把表2 的值塞入表1 的字段名，结果全部乱码。

### 解决方案：call_raw_text + 手动提取

```python
def _extract_summary_table(raw_text: str) -> list[dict]:
    """从 raw markdown 中定位表2（汇总快照），手动解析为 指标/数值 格式"""
```

- `call_and_parse` → 改为 `call_raw_text` 拿原始 markdown
- 按 `\n\n` 分块，逐块扫描表头特征（含 `Sharpe` 或 `Beta` 的 `|证券代码|` 行）
- 手动 `split("|")` 解析表头和数值行，不依赖 parser
- 通过 `_SUMMARY_FIELD_MAP` 映射为标准指标名（如 `Beta` → `贝塔`）

### 表头单位后缀清洗

iFind 在汇总表表头中附加单位提示：`区间最大回撤（单位：%）`、`波动率(年化)（单位：%）`。需要正则 `（[^）]*单位[^）]*）$` 去除后才能与 field map 匹配。

### 最终方案

```python
RISK_QUERY_TPL = (
    "请返回{stock_name}({stock_code})的完整风险指标，需要同时包含："
    "贝塔系数(Beta)、夏普比率(Sharpe)、波动率、最大回撤、"
    "Alpha、年化收益率、下行风险"
)

# 汇总表字段映射
_SUMMARY_FIELD_MAP = {
    "Beta": "贝塔", "Sharpe": "夏普比率",
    "区间最大回撤": "最大回撤", "波动率(年化)": "波动率",
    "Beta_Alpha": "Alpha",
    "年化收益率(100周)": "年化收益率(100周)",
    "年化收益率(24个月)": "年化收益率(24个月)",
    "下行风险": "下行风险",
    "平均收益率（期间年化）": "平均收益率(年化)",
    "区间下跌天数": "区间下跌天数",
}
```

### 数据流

```
get_risk_indicators(prompt) → call_raw_text → 2 张 markdown 表
     ↓
_extract_summary_table() → 定位表2 → 字段映射 → 去单位后缀
     ↓
[{"指标": "贝塔", "数值": "1.40"}, {"指标": "夏普比率", "数值": "0.10"}, ...]
     ↓
RiskData.risk → _risk_lookup → get_risk_value("贝塔") → "1.40"
```

### 实施文件

- [fetcher.py](backend/stock_agent/fetchers/risk/fetcher.py) — `RISK_QUERY_TPL` + `_SUMMARY_FIELD_MAP` + `_UNIT_SUFFIX_RE` + `_extract_summary_table()` + `fetch_risk_indicators()`
- 探查脚本：[backend/tests/_probe_risk.py](backend/tests/_probe_risk.py)

---

## get_esg_data ✅ 已完成

> 2026-07-12 探查完成，确定 **关键字模式几乎空返回，必须用 prompt**

### 接口特征

- **关键字模式无效**：传纯股票代码 `"601127"` 只返回 `证券代码 | 证券简称` 两列，无任何 ESG 评分数据
- **prompt 触发时间序列**：传自然语言 prompt 返回 10 个季度的 E/S/G 三维度评分 + 总评分
- 每季度一条记录，按日期倒序（最新→最旧）
- 预览期季度（最新季报未发布）E/S/G 字段为空值，需跳过取第一条有数据的记录
- 返回 markdown 表格 + JSON 元数据

### Query 格式对比（赛力斯 601127）

| 格式 | records | 字段 | ESG 数据 |
|---|---|---|---|
| `601127` (关键字) | 1 | 证券代码、证券简称 | ❌ 无任何评分 |
| **自然语言 prompt** | **10** | **ESG环境管理得分 + ESG社会争议得分 + ESG治理争议得分 + 同花顺ESG总评分** | **✅ 10 个季度 🥇** |

### Prompt vs Keyword 原始返回

- **keyword**：`|证券代码|证券简称|\n|601127.SH|赛力斯|` — 只有两列，JSON 元数据为空 `{}`
- **prompt**：返回完整 10 行季度数据，JSON 元数据含 4 个指标的参数说明和单位

### 核心问题：预览期空值

时间序列中最新 1~2 条记录可能处于预览期（与 financials/shareholders 同问题），E/S/G 字段为空：

```
[0] 20260930  E=空     S=空       G=空        ← 预览期（季报未发布）
[1] 20260630  E=空     S=89.676   G=86.2685   ← 预览期（中报未发布）
[2] 20250930  E=75.73  S=92.195   G=89.998    ← ✅ 已正式发布
```

### 解决方案：取最新有数据记录

```python
def _latest_esg_snapshot(records: list[dict]) -> list[dict]:
    """从 ESG 时间序列中提取最新一条有数据的记录，转为 指标/数值 格式"""
    for rec in records:
        snapshot = []
        for field, label in _ESG_FIELD_MAP.items():
            val = rec.get(field, "")
            if val and val.strip():
                snapshot.append({"指标": label, "数值": val})
        if snapshot:
            return snapshot  # 第一条有任意非空 ESG 指标的记录即返回
    return []
```

正序遍历 records（最新在前），第一份有任意 ESG 字段非空的记录就是最新正式发布季度的 ESG 快照。

### 最终方案

```python
ESG_QUERY_TPL = (
    "请返回{stock_name}({stock_code})的ESG评级数据，"
    "包括ESG综合评级、环境(E)、社会(S)、治理(G)各维度评分"
)

_ESG_FIELD_MAP = {
    "ESG环境管理得分": "环境管理得分(E)",
    "ESG社会争议得分": "社会争议得分(S)",
    "ESG治理争议得分": "治理争议得分(G)",
    "同花顺ESG总评分": "ESG总评分",
}
```

### 数据流

```
get_esg_data(prompt) → call_and_parse → 10 条时间序列
     ↓
_latest_esg_snapshot() → 取最新有数据记录 → 字段映射
     ↓
[{"指标": "环境管理得分(E)", "数值": "75.73"},
 {"指标": "社会争议得分(S)", "数值": "92.20"},
 {"指标": "治理争议得分(G)", "数值": "89.99"},
 {"指标": "ESG总评分", "数值": "82.15"}]
     ↓
RiskData.esg → to_prompt_context() → 拼入分析 prompt
```

### 实施文件

- [fetcher.py](backend/stock_agent/fetchers/risk/fetcher.py) — `ESG_QUERY_TPL` + `_ESG_FIELD_MAP` + `_latest_esg_snapshot()` + `fetch_esg()`
- 探查脚本：[backend/tests/_probe_esg.py](backend/tests/_probe_esg.py)

---

## risk 领域双接口对比总结

| 维度 | get_risk_indicators | get_esg_data |
|---|---|---|
| **服务器** | stock | stock |
| **关键字模式** | 单指标族，其余丢失 | ❌ 空（仅代码+简称） |
| **prompt 支持** | ✅ 触发双表 | ✅ 触发时间序列 |
| **最优 query** | NL prompt | NL prompt |
| **返回结构** | 2 表（日序列 + 汇总快照） | 1 表（10 季度时间序列） |
| **调取方式** | `call_raw_text` + 手动提取表2 | `call_and_parse` |
| **后处理** | 定位汇总表 → 字段映射 → 去单位后缀 | 遍历取最新有数据记录 → 字段映射 |
| **输出格式** | `[{"指标": "贝塔", "数值": "1.40"}, ...]` | `[{"指标": "环境管理得分(E)", "数值": "75.73"}, ...]` |
| **共同模型** | `RiskData.risk` | `RiskData.esg` |

---

## search_stocks 🔧 待修复

> 2026-07-13 探查完成，确定 **简短 prompt 最优**，但当前 `extract_raw_text` 无法解析其响应格式，线上已损坏

### 接口特征

- **用户驱动的接口**：query 内容来自前端用户输入（如"半导体设备行业"），不像其他 5 大领域 fetcher 有固定模板，后端无法预知查询条件
- **prompt 描述粒度决定返回质量**：太少（纯关键词）字段窄，太多（详细限定）直接空返回，**简短 prompt 最优**
- **MCP 响应格式与其他接口不同** — 这是当前线上 bug 的根因

### 关键 Bug：响应格式不兼容

`search_stocks` 的 MCP 响应结构与其他所有接口不同：

```
# 其他接口（标准结构）
inner.data → {"answer": "markdown表格..."}   ← dict，可直接 .get("answer")

# search_stocks（特殊结构）  
inner.data → "{\"answer\": \"markdown表格...\"}"  ← JSON 字符串！需要二次 json.loads()
```

`extract_raw_text` 对 `data_obj` 直接调 `.get("data")` / `.get("answer")`，当 `data_obj` 是字符串时抛 `AttributeError`，异常在 `except` 里被静默吞掉，最终返回 `{"type": "empty", "text": ""}`。**当前 `fetch_stock_screener` 在生产环境中永远返回空列表。**

修复方向：`extract_raw_text` 新增路径 4 —— 当 `data_obj` 是字符串时，`json.loads(data_obj)` 后再取 `answer`。

### Query 格式对比

#### Round 1: 半导体设备

| 格式 | 示例 | records | fields |
|---|---|---|---|
| 关键字 | `"半导体设备"` | 25 | 3 (代码/简称/行业) |
| prompt | `"请筛选出A股市场中半导体设备行业的上市公司，包括刻蚀、薄膜沉积…"` | 0 ❌ | — |

#### Round 2: 白酒

| 格式 | 示例 | records | fields |
|---|---|---|---|
| 关键字 | `"白酒"` | 19 | 3 (代码/简称/行业) |
| prompt | `"请筛选出A股市场中白酒行业的上市公司，包括高端白酒、次高端…"` | 0 ❌ | — |

#### Round 3: 同主题精细对比（半导体芯片）

| 格式 | 示例 | records | fields | 结论 |
|---|---|---|---|---|
| 简单关键字 | `"芯片"` | 0 ❌ | — | 太宽泛 |
| 多关键字 | `"集成电路 芯片设计 晶圆代工 封装测试"` | 0 ❌ | — | 多关键词无效 |
| **简短 prompt** | `"请筛选出A股市场中的半导体芯片上市公司"` | **50** | **6** (代码/简称/产品名称/相关系数/溯源分析/市场类型) | **✅ 最优 🥇** |
| 详细 prompt | `"请筛选出…需要包含：IC设计、晶圆代工、半导体设备…"` | 0 ❌ | — | 过度描述失效 |

### 行为规律

1. **简短 prompt 胜出**：字段从 3 → 6，多了"相关产品名称""相关系数""溯源分析""股票市场类型"，记录数从 25 → 50
2. **prompt 越详细越差**：加了"需要包含：…"等限定条件就空返回，**"用最少的话说清概念"就是最优**
3. **多关键词无效**：空格分隔或管道分隔的多关键词均返回空，与 `get_stock_events` 的"赢家通吃"行为类似
4. **429 限流**：连续调用需间隔 ≥2 秒，否则返回 `"用户请求过于频繁，请稍后重试"`

### 架构定位：发现层 vs 深挖层

`search_stocks` 与 5 大领域 fetcher 是不同层次的能力：

```
┌─────────────────────────────────────────────┐
│  发现层（search_stocks）                      │
│  用户输入 → 筛选股票 → 返回候选列表            │
│  例: "半导体设备行业" → [北方华创, 中微, …]    │
└──────────────────┬──────────────────────────┘
                   │ 用户点击选择
                   ▼
┌─────────────────────────────────────────────┐
│  深挖层（5 领域 fetcher）                     │
│  股票代码 → 行情/财务/股东/新闻/风险/ESG       │
│  例: "002371" → 完整分析报告                  │
└─────────────────────────────────────────────┘
```

- `search_stocks` 不需要接入 `fetch_stock_data` 编排链，它是独立的前置步骤
- query 参数源自前端用户输入，无法像其他 fetcher 那样写死 `QUERY_TPL`
- 需要独立 API 端点：`POST /api/screener/search`，body 透传用户输入

### 当前代码状态

| 组件 | 状态 |
|---|---|
| `fetch_stock_screener()` | ⚠️ 函数存在，但因 `extract_raw_text` 解析 bug 永远空返回 |
| API 路由 | ❌ 未接入任何路由（routers 里无引用） |
| 编排链 | ❌ 未接入 `fetch_stock_data`（无需接入） |
| 前端 | ❌ 无搜索界面 |
| 测试 | ✅ `test_stock_screener_fetch` + `test_stock_screener_empty` 两个 mock 测试通过 |

### 待办

- [ ] 修复 `extract_raw_text` 新增字符串路径
- [ ] 设计独立 API 端点 `POST /api/screener/search`
- [ ] 前端搜索交互（输入框 + 结果列表 + 加入关注）

### 实施文件

- 探查脚本：[backend/tests/_probe_search_stocks.py](backend/tests/_probe_search_stocks.py)

---

## 排查方向

- iFinD stock server 是否有专用的技术指标接口（如 `get_technical_indicators`）
- 是否有 `get_stock_history` 等历史行情接口可计算多周期均线
- 获取 stock server 完整工具列表（`list_tools("stock")`）对比分析
