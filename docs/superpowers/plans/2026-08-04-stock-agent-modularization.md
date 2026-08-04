# stock_agent 目录模块化重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `backend/stock_agent/` 目录按"采集层/分析核心层/数据模型/提示词"分层重组，每个文件职责单一、可查看可维护，严格不改变任何功能。

**Architecture:** 纯搬迁 + 原路径薄 facade re-export。真实现迁入 `core/`（分析核心）与 `skill/` 新文件（采集编排），原 `analyze.py`/`render.py`/`validator.py`/`history.py` 保留为 facade 兼容层，`models.py` 拆为子包。所有函数签名、行为、import 路径保持兼容。

**Tech Stack:** Python 3, pytest, FastAPI

## Global Constraints

- 全程不重写业务逻辑、不改函数签名、不改数据结构
- 每拆一个文件 → 跑一次全量 pytest，保持 191 passed 零回归
- `patch('stock_agent.analyze.OpenAI')` 等 monkeypatch 路径必须继续可解析（facade 显式保留 `OpenAI` import）
- 不动 backend 根目录 `models.py`（数据库 ORM：PushHistory/StockReport/StockWatchlist）
- 不拆分 `prompts/`（28-114 行，内聚度已够）
- 不做 UI 前端相关改动
- 遵循 CLAUDE.md：函数/变量 snake_case、类 CapWords、中文注释

---

### Task 1: 新建 models 子包（拆 models.py）

**Files:**
- Create: `backend/stock_agent/models/base.py`
- Create: `backend/stock_agent/models/market.py`
- Create: `backend/stock_agent/models/shareholders.py`
- Create: `backend/stock_agent/models/news.py`
- Create: `backend/stock_agent/models/risk.py`
- Create: `backend/stock_agent/models/env.py`
- Create: `backend/stock_agent/models/_util.py`
- Create: `backend/stock_agent/models/__init__.py`
- Modify: `backend/stock_agent/models.py` → 删除（改为子包后原单文件删除）

**Interfaces:**
- Produces: `stock_agent.models` 仍可 `from stock_agent.models import DataIncompleteError, IfindRecord, ParsedData, MarketData, FinancialsData, ShareholderData, NewsEventsData, RiskData, MarketEnvData, _iter_fields`
- 内部模块间依赖：`market.py`/`env.py` 依赖 `_util.py`；`base.py` 独立；其余独立

- [ ] **Step 1: 先写 models/_util.py（工具函数）**

从原 `models.py` 第 27-46 行搬 `_TABLE_META_KEYS` + `_iter_fields`：

```python
"""iFind 数据模型 — 内部共享工具

供各领域模型复用元数据列过滤与字段遍历逻辑。
"""
from __future__ import annotations

# iFind markdown 表格通用元数据列（非业务指标）
_TABLE_META_KEYS = frozenset({
    "证券代码", "证券简称", "日期", "股票代码", "股票名称",
    "stock_code", "stock_name", "date",
})


def _iter_fields(records: list[dict], skip_meta: bool = True):
    """遍历 records 列表的所有 key-value，跳过元数据列和空值

    值统一转 str 输出（iFind 可能返回 int/float）；
    判空基于转换后的字符串，故数值 0 / 0.0 作为合法金融数据保留。
    """
    for r in records:
        for k, v in r.items():
            if skip_meta and k in _TABLE_META_KEYS:
                continue
            s = "" if v is None else str(v).strip()
            if not s:
                continue
            yield k, s
```

- [ ] **Step 2: 写 models/base.py（异常 + 基础记录 + 解析包装）**

从原 `models.py` 第 13-122 行搬 `DataIncompleteError` + `IfindRecord` + `ParsedData`（原样，仅去掉模块 docstring 与顶层 import 注释）：

```python
"""iFind 数据模型 — 基础记录与解析包装"""
from __future__ import annotations
from typing import Optional


class DataIncompleteError(Exception):
    """关键数据缺失，拒绝调用 LLM 以防止幻觉"""
    pass


class IfindRecord:
    """一条 iFind 数据记录，字段名动态变化"""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, str]):
        self._data = data

    @classmethod
    def from_dict(cls, data: dict) -> IfindRecord:
        """从 dict 创建记录"""
        return cls(data)

    @property
    def data(self) -> dict[str, str]:
        return self._data

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """安全获取字段值"""
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, str]:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"IfindRecord({self._data})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IfindRecord):
            return NotImplemented
        return self._data == other._data


class ParsedData:
    """封装 unified_parse 返回结果"""

    __slots__ = ("ok", "format", "record_count", "records", "field_names")

    def __init__(
        self,
        ok: bool,
        format: str,
        record_count: int,
        records: list[IfindRecord],
        field_names: list[str],
    ):
        self.ok = ok
        self.format = format
        self.record_count = record_count
        self.records = records
        self.field_names = field_names

    @classmethod
    def from_parse_result(cls, result: dict) -> ParsedData:
        """从 unified_parse 返回的 dict 构造"""
        records = [IfindRecord.from_dict(r) for r in result.get("records", [])]
        return cls(
            ok=result.get("ok", False),
            format=result.get("format", "empty"),
            record_count=result.get("record_count", 0),
            records=records,
            field_names=list(result.get("field_names", [])),
        )

    def __repr__(self) -> str:
        return f"ParsedData(ok={self.ok}, format={self.format}, records={self.record_count})"
```

- [ ] **Step 3: 写 models/market.py（行情 + 财务）**

从原 `models.py` 第 125-207 行搬 `MarketData` + `FinancialsData`，把 `_iter_fields` 引用改为 `from ._util import _iter_fields`：

```python
"""iFind 数据模型 — 行情与技术指标、财务数据"""
from __future__ import annotations
from typing import Optional

from ._util import _iter_fields


class MarketData:
    """行情 + 技术指标 + 摘要"""

    def __init__(self, stock_code: str, records: list[dict], summary: list[dict] | None = None):
        self.stock_code = stock_code
        self._records = records
        self.summary = summary or []
        # 动态 lookup：使用实际字段名作为 key（跳过元数据列）
        self._lookup: dict[str, str] = {}
        for k, v in _iter_fields(records):
            self._lookup[k] = v
        # 摘要也加入 lookup（非覆盖）
        for k, v in _iter_fields(self.summary):
            if k not in self._lookup:
                self._lookup[k] = v

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def summary_count(self) -> int:
        return len(self.summary)

    def get_value(self, indicator: str) -> Optional[str]:
        return self._lookup.get(indicator)

    def to_prompt_context(self) -> str:
        """导出为 LLM prompt 可用的文本"""
        lines = [f"### 行情数据（{self.stock_code}）"]
        for k, v in _iter_fields(self._records):
            lines.append(f"- {k}：{v}")
        if self.summary:
            lines.append("\n**股票摘要**：")
            for k, v in _iter_fields(self.summary):
                lines.append(f"- {k}：{v}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出为前端可渲染的结构化数据"""
        fields = [{"name": k, "value": v, "unit": ""}
                  for k, v in _iter_fields(self._records)]
        summary = [{"name": k, "value": v}
                   for k, v in _iter_fields(self.summary)]
        return {"fields": fields, "summary": summary}


class FinancialsData:
    """财务数据"""

    def __init__(self, stock_code: str, records: list[dict], report_date: str = ""):
        self.stock_code = stock_code
        self._records = records
        self.report_date = report_date
        self._lookup: dict[str, str] = {}
        for k, v in _iter_fields(records):
            self._lookup[k] = v

    @property
    def record_count(self) -> int:
        return len(self._records)

    def get_value(self, indicator: str) -> Optional[str]:
        return self._lookup.get(indicator)

    def to_prompt_context(self) -> str:
        """导出财务数据为 LLM prompt 文本"""
        lines = [f"### 财务数据（{self.stock_code}）"]
        if self.report_date:
            lines.append(f"报告期：{self.report_date}")
        for k, v in _iter_fields(self._records):
            lines.append(f"- {k}：{v}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出财务数据为前端可渲染的结构"""
        fields = [{"name": k, "value": v}
                  for k, v in _iter_fields(self._records)]
        return {"report_date": self.report_date, "fields": fields}
```

- [ ] **Step 4: 写 models/shareholders.py（股东结构）**

从原 `models.py` 第 210-277 行搬 `ShareholderData`（原样，仅改 import）：

```python
"""iFind 数据模型 — 股东结构"""
from __future__ import annotations


class ShareholderData:
    """股东结构"""

    def __init__(self, stock_code: str, records: list[dict], report_date: str = ""):
        self.stock_code = stock_code
        self._records = records
        self.report_date = report_date

    @property
    def record_count(self) -> int:
        return len(self._records)

    def to_prompt_context(self) -> str:
        """导出股东数据为 LLM prompt 文本"""
        lines = [f"### 股东结构（{self.stock_code}）"]
        if not self._records:
            return "\n".join(lines)
        if self.report_date:
            lines.append(f"报告期：{self.report_date}")
        sh = self._records[0]
        # 汇总指标
        for field in ("股东户数(截止日期)", "前十大股东持股比例合计（单位：%）",
                      "机构持股比例合计（单位：%）", "户均持股数量（单位：股）",
                      "户均持股比例（单位：‰）"):
            val = sh.get(field, "")
            if val:
                lines.append(f"- {field}：{val}")
        # 前十大股东
        lines.append("\n**前十大股东**：")
        for rank in range(1, 11):
            name = sh.get(f"股东名称（十大股东排名：第{rank}名）", "")
            ratio = sh.get(f"股东持股比例（十大股东排名：第{rank}名；单位：%）", "")
            if name:
                lines.append(f"- {name}：{ratio}%")
        # 十大流通股东
        lines.append("\n**十大流通股东**：")
        for rank in range(1, 11):
            name = sh.get(f"流通股东名称（十大流通股东排名：第{rank}名）", "")
            ratio = sh.get(f"流通股东持股比例（十大流通股东排名：第{rank}名；单位：%）", "")
            if name:
                lines.append(f"- {name}：{ratio}%")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出股东结构为前端可渲染的结构（取第一条记录，最多10大股东）"""
        result = {"report_date": self.report_date, "fields": [], "top_holders": [], "float_holders": []}
        if not self._records:
            return result
        sh = self._records[0]
        for field in ("股东户数(截止日期)", "前十大股东持股比例合计（单位：%）",
                      "机构持股比例合计（单位：%）", "户均持股数量（单位：股）",
                      "户均持股比例（单位：‰）"):
            val = sh.get(field, "")
            if val:
                result["fields"].append({"name": field, "value": val})
        for rank in range(1, 11):
            name = sh.get(f"股东名称（十大股东排名：第{rank}名）", "")
            ratio = sh.get(f"股东持股比例（十大股东排名：第{rank}名；单位：%）", "")
            if name:
                result["top_holders"].append({"name": name, "ratio": ratio})
        for rank in range(1, 11):
            name = sh.get(f"流通股东名称（十大流通股东排名：第{rank}名）", "")
            ratio = sh.get(f"流通股东持股比例（十大流通股东排名：第{rank}名；单位：%）", "")
            if name:
                result["float_holders"].append({"name": name, "ratio": ratio})
        return result
```

- [ ] **Step 5: 写 models/news.py（新闻公告）**

从原 `models.py` 第 280-356 行搬 `NewsEventsData`（原样，仅改 import 头）：

```python
"""iFind 数据模型 — 新闻、公告与重大事件"""
from __future__ import annotations


class NewsEventsData:
    """新闻 + 公告 + 重大事件"""

    # iFind MCP 新闻类返回字段名映射（兼容多来源字段名差异）
    _NEWS_TITLE_KEYS = ("资讯标题", "title", "新闻标题")
    _NEWS_CONTENT_KEYS = ("资讯内容", "资讯摘要", "content", "description", "摘要")
    _NEWS_TIME_KEYS = ("日期", "time", "date", "发布时间")
    _NOTICE_TITLE_KEYS = ("公告标题", "title", "标题")
    _NOTICE_CONTENT_KEYS = ("公告片段内容", "content", "摘要", "description")
    _NOTICE_DATE_KEYS = ("日期", "date", "time", "发布时间")

    @staticmethod
    def _first_of(record: dict, *keys: str) -> str:
        """从 record 中取第一个非空字段值（兼容非字符串类型，统一转 str）"""
        for k in keys:
            val = record.get(k, "")
            s = "" if val is None else str(val).strip()
            if s:
                return s
        return ""

    def __init__(self, stock_code: str, news: list[dict], notices: list[dict],
                 events: str = ""):
        self.stock_code = stock_code
        self.news = news
        self.notices = notices
        self.events = events  # LLM 总结后的中文描述文本

    @property
    def news_count(self) -> int:
        return len(self.news)

    @property
    def notice_count(self) -> int:
        return len(self.notices)

    @property
    def has_events(self) -> bool:
        return bool(self.events and self.events.strip())

    def to_prompt_context(self) -> str:
        lines = [f"### 近期新闻与公告（{self.stock_code}）"]
        if self.news:
            lines.append("\n**新闻**：")
            for n in self.news:
                title = self._first_of(n, *self._NEWS_TITLE_KEYS)
                content = self._first_of(n, *self._NEWS_CONTENT_KEYS)
                time = self._first_of(n, *self._NEWS_TIME_KEYS)
                lines.append(f"- [{time}] {title}（{content[:80]}...）" if len(content) > 80
                             else f"- [{time}] {title}（{content}）")
        if self.notices:
            lines.append("\n**公告**：")
            for n in self.notices:
                title = self._first_of(n, *self._NOTICE_TITLE_KEYS)
                content = self._first_of(n, *self._NOTICE_CONTENT_KEYS)
                date = self._first_of(n, *self._NOTICE_DATE_KEYS)
                lines.append(f"- [{date}] {title}（{content[:80]}...）" if len(content) > 80
                             else f"- [{date}] {title}（{content}）")
        if self.events:
            lines.append(f"\n**重大事件总结**：\n{self.events}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出新闻事件为前端可渲染的结构"""
        return {
            "news": [{
                "title": self._first_of(n, *self._NEWS_TITLE_KEYS),
                "source": self._first_of(n, *self._NEWS_CONTENT_KEYS),
                "time": self._first_of(n, *self._NEWS_TIME_KEYS),
            } for n in self.news],
            "notices": [{
                "title": self._first_of(n, *self._NOTICE_TITLE_KEYS),
                "type": self._first_of(n, *self._NOTICE_CONTENT_KEYS),
                "date": self._first_of(n, *self._NOTICE_DATE_KEYS),
            } for n in self.notices],
            "events_summary": self.events or "",
        }
```

- [ ] **Step 6: 写 models/risk.py（风险 ESG）**

从原 `models.py` 第 359-418 行搬 `RiskData`（原样，仅改 import 头）：

```python
"""iFind 数据模型 — 风险指标与 ESG"""
from __future__ import annotations
from typing import Optional


class RiskData:
    """风险指标 + ESG"""

    def __init__(self, stock_code: str, risk: list[dict], esg: list[dict]):
        self.stock_code = stock_code
        self.risk = risk
        self.esg = esg
        self._risk_lookup: dict[str, str] = {}
        for r in risk:
            key = r.get("指标", "")
            val = r.get("数值", "")
            if key:
                self._risk_lookup[key] = val

    @property
    def risk_count(self) -> int:
        return len(self.risk)

    @property
    def esg_count(self) -> int:
        return len(self.esg)

    def get_risk_value(self, indicator: str) -> Optional[str]:
        return self._risk_lookup.get(indicator)

    def to_prompt_context(self) -> str:
        lines = [f"### 风险与ESG（{self.stock_code}）"]
        if self.risk:
            lines.append("\n**风险指标**：")
            for r in self.risk:
                name = r.get("指标", "")
                val = r.get("数值", "")
                unit = r.get("单位", "")
                unit_str = f" {unit}" if unit and unit != "-" else ""
                lines.append(f"- {name}：{val}{unit_str}")
        if self.esg:
            lines.append("\n**ESG**：")
            for r in self.esg:
                name = r.get("指标", "")
                val = r.get("数值", "")
                lines.append(f"- {name}：{val}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出风险+ESG为前端可渲染的结构"""
        risk_fields = []
        for r in self.risk:
            unit = r.get("单位", "")
            risk_fields.append({
                "name": r.get("指标", ""),
                "value": r.get("数值", ""),
                "unit": unit if unit and unit != "-" else "",
            })
        esg_fields = []
        for r in self.esg:
            esg_fields.append({
                "name": r.get("指标", ""),
                "value": r.get("数值", ""),
            })
        return {"risk": risk_fields, "esg": esg_fields}
```

- [ ] **Step 7: 写 models/env.py（市场环境）**

从原 `models.py` 第 421-470 行搬 `MarketEnvData`，`_iter_fields`/`_TABLE_META_KEYS` 改从 `_util` 导入：

```python
"""iFind 数据模型 — 市场环境（大盘指数 + 宏观 EDB）"""
from __future__ import annotations

from ._util import _iter_fields, _TABLE_META_KEYS


class MarketEnvData:
    """市场环境 — 大盘指数行情 + EDB 宏观"""

    def __init__(self, stock_code: str, records: list[dict], edb: list[dict]):
        self.stock_code = stock_code
        self._records = records  # 每条 record 含 "name"/"code" + iFind 字段
        self.edb = edb

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def edb_count(self) -> int:
        return len(self.edb)

    def to_prompt_context(self) -> str:
        lines = [f"### 市场环境（大盘指数）"]
        for r in self._records:
            idx_name = r.get("name", "")
            lines.append(f"\n**{idx_name}**：")
            for k, v in r.items():
                if k in ("name", "code") or k in _TABLE_META_KEYS:
                    continue
                s = "" if v is None else str(v).strip()  # 数值安全 + 0 值保留
                if s:
                    lines.append(f"- {k}：{s}")
        if self.edb:
            lines.append("\n**宏观数据（EDB）**：")
            for k, v in _iter_fields(self.edb):
                lines.append(f"- {k}：{v}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出市场环境为前端可渲染的结构 — 每个指数一个分组"""
        indexes = []
        for r in self._records:
            idx_name = r.get("name", "")
            idx_code = r.get("code", "")
            fields = []
            for k, v in r.items():
                if k in ("name", "code") or k in _TABLE_META_KEYS:
                    continue
                s = "" if v is None else str(v).strip()
                if s:
                    fields.append({"name": k, "value": s, "unit": ""})
            indexes.append({"name": idx_name, "code": idx_code, "fields": fields})
        edb = [{"name": k, "value": v}
               for k, v in _iter_fields(self.edb)]
        return {"indexes": indexes, "edb": edb}
```

- [ ] **Step 8: 写 models/__init__.py 并删除原 models.py**

```python
"""iFind 数据模型包

原 models.py（470 行）拆为按领域归类的子模块，对外 re-export 保持
`from stock_agent.models import X` 路径不变（test_models.py 等消费者零改动）。
"""
from .base import DataIncompleteError, IfindRecord, ParsedData
from .market import MarketData, FinancialsData
from .shareholders import ShareholderData
from .news import NewsEventsData
from .risk import RiskData
from .env import MarketEnvData
from ._util import _iter_fields, _TABLE_META_KEYS

__all__ = [
    "DataIncompleteError",
    "IfindRecord",
    "ParsedData",
    "MarketData",
    "FinancialsData",
    "ShareholderData",
    "NewsEventsData",
    "RiskData",
    "MarketEnvData",
    "_iter_fields",
    "_TABLE_META_KEYS",
]
```

删除原文件：`rm backend/stock_agent/models.py`

- [ ] **Step 9: 跑测试验证**

Run: `cd backend && python -m pytest tests/test_models.py tests/test_analyze.py -q`
Expected: PASS（test_models 引 `stock_agent.models.X` 经 `__init__.py` re-export 全部解析）

- [ ] **Step 10: 全量测试 + 提交**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed

```bash
cd d:/karensAgent
git add backend/stock_agent/models/
git add -A backend/stock_agent/models.py
git commit -m "refactor(stock_agent): models.py 拆分为 models 子包（re-export 兼容）"
```

---

### Task 2: 拆分 skill/__init__.py → client.py + extract.py

**Files:**
- Create: `backend/stock_agent/skill/client.py`
- Create: `backend/stock_agent/skill/extract.py`
- Modify: `backend/stock_agent/skill/__init__.py` → 变薄 re-export

**Interfaces:**
- Consumes: 无（不依赖其他任务）
- Produces: `skill/client.py` 导出 `call_skill`/`list_skill_tools`；`skill/extract.py` 导出 `extract_text`/`extract_raw`/`_format_table`/`_format_news`；`skill/__init__.py` re-export 全部

- [ ] **Step 1: 写 skill/client.py（调用层）**

从原 `skill/__init__.py` 第 13-39 行搬 `SKILL_DIR` 注入 + `call_skill` + `list_skill_tools`：

```python
"""iFinD SKILL 调用封装 — 客户端

通过 sys.path 导入 ~/.claude/skills/ifind-finance-data/call.py
不复制文件，密钥配置由 call.py 自行读取同目录下的 mcp_config.json
"""
import sys
from pathlib import Path

# 历史遗留：call.py 曾用 verify=False 并在此压制 SSL 警告。
# 2026-07-29 已启用证书校验（verify=True），警告压制随之移除。

SKILL_DIR = str(Path("~/.claude/skills/ifind-finance-data").expanduser())
if SKILL_DIR not in sys.path:
    # NOTE: 导入期修改全局 sys.path 是加载用户级共享 skill 的既有机制，
    # 改 importlib 作用域加载牵动面大，暂保留（见实施计划"不修清单"第 3 条）
    sys.path.insert(0, SKILL_DIR)

from call import call as _call, list_tools as _list_tools  # noqa: E402


def call_skill(server_type: str, tool_name: str, params: dict) -> dict:
    """调用 iFinD SKILL 的 call 函数

    Args:
        server_type: stock | fund | edb | news | bond | global_stock | index
        tool_name: SKILL 工具名称，详见 references/ 下子服务文档
        params: 请求参数，自然语言工具用 {"query": "..."}，
                高频行情用 {"symbols": "...", "indicators": "...", "data_mode": "..."}

    Returns:
        {"ok": True/False, "status_code": int, "data": dict}
    """
    return _call(server_type, tool_name, params)


def list_skill_tools(server_type: str) -> dict:
    """获取某个服务当前可用的工具清单"""
    return _list_tools(server_type)
```

- [ ] **Step 2: 写 skill/extract.py（响应解析层）**

从原 `skill/__init__.py` 第 42-241 行搬 `extract_text` + `extract_raw` + `_format_table` + `_format_news`（原样，仅保留 `import json`）：

```python
"""iFinD SKILL 响应解析 — 文本提取与结构化提取

统一从 MCP JSON-RPC 包装中解出业务数据，供上层维度处理。
"""
import json


def extract_text(result: dict) -> str:
    """从 SKILL 返回结果中提取文本内容

    SKILL 返回格式为 MCP JSON-RPC 包装：
    data.result.content[0].text → JSON 字符串 → 内层 data 字段

    不同工具的内层格式略有差异，此函数做统一提取。
    """
    if not result.get("ok"):
        err = result.get("error", "未知错误")
        if isinstance(err, dict):
            err = err.get("message", str(err))
        return f"[错误] {err}"

    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return "[无数据]"

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return str(first)

    raw_text = first.get("text", "")
    if not raw_text:
        return "[空响应]"

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return raw_text

    if not isinstance(inner, dict):
        return str(inner)

    # 检查内层 code 字段
    # 约定（Task 2 于 2026-07-29 实证确认）：iFinD 内层 code=0 表示失败/权限不足，
    # 成功响应 code 为 1（msg='success'）。系统正常运行即依赖此约定，勿按"0=成功"的通用惯例改。
    if inner.get("code") == 0:
        return f"[权限不足或无数据] {inner.get('msg', '')}"

    inner_data = inner.get("data")
    if inner_data is None:
        return raw_text

    # 新闻/公告类：data 是 dict，含 "data" 字段（JSON 数组字符串）
    if isinstance(inner_data, dict):
        if "answer" in inner_data:
            answer = inner_data["answer"]
            # 数据范围外应答（如查港股走了 A 股服务）→ 标记为无数据
            if isinstance(answer, str) and "不属于" in answer and "数据范围" in answer:
                return f"[无数据] {answer}"
            return answer
        if "data" in inner_data:
            news_data = inner_data["data"]
            if isinstance(news_data, str):
                try:
                    articles = json.loads(news_data)
                    return _format_news(articles)
                except (json.JSONDecodeError, TypeError):
                    return news_data
            if isinstance(news_data, list):
                return _format_news(news_data)
        # 兜底：返回整个 inner_data 的 JSON
        return json.dumps(inner_data, ensure_ascii=False, indent=2)

    # 实时行情类：data 是 JSON 字符串，内含表格
    if isinstance(inner_data, str):
        try:
            table_data = json.loads(inner_data)
            if isinstance(table_data, dict) and "tables" in table_data:
                return _format_table(table_data)
            return json.dumps(table_data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            # 厂商软错误：外层 code=1 但 data 是非 JSON 错误文本（实证用例见
            # test_extract_text_vendor_soft_error）。本分支契约是行情表格 JSON
            # 字符串，非 JSON 即异常，统一转 [无数据] 供上层判定维度失败。
            # 注：新闻 data 分支的纯文本属合法数据，不适用此规则
            return f"[无数据] {inner_data}"

    return str(inner_data)


def extract_raw(result: dict):
    """从 SKILL 返回结果中提取原始结构化数据（不做 Markdown 格式化）

    返回 typed dict，方便 prose formatter 按维度处理：
      {"type": "table",  "tables": [[...], ...]}     — 表格数据
      {"type": "news",   "articles": [{...}, ...]}    — 新闻/公告列表
      {"type": "answer", "text": "..."}               — 自然语言回答（可能内含表格）
      {"type": "json",   "data": {...}}               — 非表格的结构化 JSON
      {"type": "text",   "text": "..."}               — 纯文本/兜底
      None                                              — 错误或无数据
    """
    if not result.get("ok"):
        return None

    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return None

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return {"type": "text", "text": str(first)}

    raw_text = first.get("text", "")
    if not raw_text:
        return None

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {"type": "text", "text": raw_text}

    if not isinstance(inner, dict):
        return {"type": "text", "text": str(inner)}

    # 检查内层 code 字段
    if inner.get("code") == 0:
        return None

    inner_data = inner.get("data")
    if inner_data is None:
        return {"type": "text", "text": raw_text}

    # 新闻/公告类：data 是 dict
    if isinstance(inner_data, dict):
        if "answer" in inner_data:
            return {"type": "answer", "text": inner_data["answer"]}
        if "data" in inner_data:
            news_data = inner_data["data"]
            if isinstance(news_data, str):
                try:
                    articles = json.loads(news_data)
                    return {"type": "news", "articles": articles}
                except (json.JSONDecodeError, TypeError):
                    return {"type": "text", "text": news_data}
            if isinstance(news_data, list):
                return {"type": "news", "articles": news_data}
        return {"type": "json", "data": inner_data}

    # 表格类：data 是 JSON 字符串
    if isinstance(inner_data, str):
        try:
            table_data = json.loads(inner_data)
            if isinstance(table_data, dict) and "tables" in table_data:
                return {"type": "table", "tables": table_data["tables"]}
            return {"type": "json", "data": table_data}
        except (json.JSONDecodeError, TypeError):
            return {"type": "text", "text": inner_data}

    return {"type": "text", "text": str(inner_data)}


def _format_table(data: dict) -> str:
    """格式化 SKILL 返回的表格数据为 Markdown 表格"""
    tables = data.get("tables", [])
    if not tables:
        return json.dumps(data, ensure_ascii=False, indent=2)

    lines = []
    # tables[0] 是表头，tables[1:] 是数据行
    if len(tables) >= 2:
        headers = tables[0]
        rows = tables[1:]
        # Markdown 表格
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _format_news(articles: list) -> str:
    """格式化新闻/公告列表为 Markdown"""
    if not articles:
        return "[无相关新闻或公告]"

    lines = []
    for i, article in enumerate(articles, 1):
        if isinstance(article, dict):
            title = article.get("资讯标题") or article.get("公告标题") or article.get("title", "无标题")
            date = article.get("日期") or article.get("date", "")
            content = article.get("资讯内容") or article.get("公告片段内容") or article.get("content", "")
            # 截取前 300 字
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"**{i}. {title}**")
            if date:
                lines.append(f"  📅 {date}")
            lines.append(f"  {content}")
            lines.append("")
        else:
            lines.append(f"- {article}")
    return "\n".join(lines)
```

- [ ] **Step 3: 改写 skill/__init__.py 为 re-export**

```python
"""iFinD SKILL 调用封装

client.py 负责调用，extract.py 负责响应解析；本文件对外 re-export 保持
`from stock_agent.skill import call_skill, extract_text, extract_raw` 不变。
"""
from .client import call_skill, list_skill_tools  # noqa: F401
from .extract import extract_text, extract_raw  # noqa: F401

__all__ = ["call_skill", "list_skill_tools", "extract_text", "extract_raw"]
```

- [ ] **Step 4: 跑测试验证**

Run: `cd backend && python -m pytest tests/test_skill_extract.py tests/test_eastmoney.py tests/test_tencent_name.py -q`
Expected: PASS（`from stock_agent.skill import extract_text/extract_raw` 经 `__init__.py` re-export 解析）

> **注意**：`skill/report.py` 目前 `from . import call_skill, extract_text, extract_raw`，改 `__init__.py` 后仍可经 re-export 解析，无需改 report.py。此步骤先不动 report.py，留到 Task 3。

- [ ] **Step 5: 全量测试 + 提交**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed

```bash
cd d:/karensAgent
git add backend/stock_agent/skill/
git commit -m "refactor(stock_agent): skill/__init__ 拆分为 client/extract 两文件"
```

---

### Task 3: 拆分 skill/report.py → collect/parse/format + 门面

**Files:**
- Create: `backend/stock_agent/skill/collect.py`
- Create: `backend/stock_agent/skill/parse.py`
- Create: `backend/stock_agent/skill/format.py`
- Modify: `backend/stock_agent/skill/report.py` → 变薄门面

**Interfaces:**
- Consumes: `skill/client.py` 的 `call_skill`；`skill/extract.py` 的 `extract_text`/`extract_raw`；`skill/indicators.py` 全部；`datasources/eastmoney.py` 的 `_fetch_ohlcv_eastmoney`
- Produces: `skill/collect.py` 导出 `DIMENSIONS`/`HK_DIMENSIONS`/`RATE_LIMIT_INTERVAL`/`_dimensions_for`/`_news_time_params`/`_resolve_summary_query`/`_strip_error_prefix`/`_call_dim_with_retry`/`_build_params`；`skill/parse.py` 导出 `_parse_tsv_sections`/`_raw_to_prose`/`_table_rows_to_prose`/`_format_news_prose`/`_name_from_pipe_table`/`_extract_stock_name`/`_parse_ohlcv_table`/`_clean_header`；`skill/format.py` 导出 `_format_indicators_markdown`/`_enrich_performance`/`_format_sse`/`_market_suffix`/`normalize_stock_code`

- [ ] **Step 1: 写 skill/collect.py（采集编排）**

从原 `report.py` 第 21-191 行搬 `DIMENSIONS` + `HK_DIMENSIONS` + `RATE_LIMIT_INTERVAL` + `_dimensions_for` + `_news_time_params` + `_resolve_summary_query` + `_strip_error_prefix` + `_call_dim_with_retry` + `_build_params`。import 改为：

```python
"""SKILL 采集编排 — 维度配置、参数构建与单维度采集重试"""
import time
from datetime import datetime, timedelta

from ..datasources.eastmoney import (
    _get_name_eastmoney, _get_name_tencent,
)
from . import call_skill, extract_text, extract_raw
from .format import _market_suffix
```

（函数体照搬原 25-191 行，仅顶部 import 换成上述；`_call_dim_with_retry` 用 `_build_params`、`extract_text`、`extract_raw`、`_strip_error_prefix`、`time.sleep`，`_build_params` 用 `_news_time_params`/`_resolve_summary_query`/`_market_suffix`。）

- [ ] **Step 2: 写 skill/parse.py（响应解析）**

从原 `report.py` 第 233-509 行搬 `_clean_header` + `_parse_tsv_sections` + `_table_rows_to_prose` + `_format_news_prose` + `_raw_to_prose` + `_name_from_pipe_table` + `_extract_stock_name`。import 改为：

```python
"""SKILL 响应解析 — TSV/表格/新闻/公司名提取"""
import json
import re

from ..datasources.eastmoney import (
    _get_name_eastmoney, _get_name_tencent,
)
```

（函数体照搬原 233-509 行，仅 import 替换；`_extract_stock_name` 用 `_name_from_pipe_table` 与东财/腾讯兜底。）

- [ ] **Step 3: 写 skill/format.py（指标格式化）**

从原 `report.py` 第 194-221 行（`normalize_stock_code`/`_market_suffix`）+ 223-227（`_format_sse`）+ 610-723（`_format_indicators_markdown`/`_enrich_performance`）搬。import 改为：

```python
"""SKILL 数据格式化 — 股票代码归一化、SSE 事件、技术指标 Markdown"""
import json
import re

from ..datasources.eastmoney import _fetch_ohlcv_eastmoney
from .indicators import (
    _calc_ema, _calc_ma, _calc_macd, _calc_boll, _calc_rsi, _calc_kdj,
    _last_valid,
)
from .parse import _parse_ohlcv_table
```

（函数体照搬；`_enrich_performance` 用 `_fetch_ohlcv_eastmoney`/`_parse_ohlcv_table`/`_calc_*`/`_format_indicators_markdown`。）

- [ ] **Step 4: 改写 skill/report.py 为门面**

保留 `generate_report_sync`（842-912 行）+ `generate_report_stream`（730-835 行），import 改为从新文件引：

```python
"""SKILL 报告编排器 — 门面

collect.py 负责采集、parse.py 负责解析、format.py 负责格式化；
本文件只保留 generate_report_sync / generate_report_stream 两个主入口。
"""
import asyncio
from datetime import datetime

from .collect import (
    DIMENSIONS, HK_DIMENSIONS, RATE_LIMIT_INTERVAL,
    _dimensions_for, _call_dim_with_retry,
)
from .format import _format_sse, _enrich_performance, normalize_stock_code
from .parse import _extract_stock_name, _raw_to_prose
```

（`generate_report_stream` 与 `generate_report_sync` 函数体照搬原样，仅模块级 import 替换为上述。）

- [ ] **Step 5: 跑测试验证**

Run: `cd backend && python -m pytest tests/test_hk_stock_support.py tests/test_report_unit.py tests/test_skill_summary.py tests/test_critical_failure_gate.py -q`
Expected: PASS（`from stock_agent.skill.report import generate_report_sync/...` 与 `from stock_agent.skill import report as rp` 仍解析）

- [ ] **Step 6: 全量测试 + 提交**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed

```bash
cd d:/karensAgent
git add backend/stock_agent/skill/
git commit -m "refactor(stock_agent): skill/report 拆分为 collect/parse/format 三文件"
```

---

### Task 4: 新建 core 子包（parser/repair/validator/render/history）

> **注意（Task 4/5 冲突修正）**：`core/analyze.py` **不建**。analyze 主体因 `patch('stock_agent.analyze.OpenAI')` monkeypatch 约束必须留在 `stock_agent/analyze.py`（Task 5 Step 1）。若 Task 4 建了 core/analyze.py，Task 5 后即无人引用的死代码。core 只承载从 analyze.py 剥离的 parser/repair + 复制的 validator/render/history。

**Files:**
- Create: `backend/stock_agent/core/__init__.py`
- Create: `backend/stock_agent/core/parser.py`
- Create: `backend/stock_agent/core/repair.py`
- Create: `backend/stock_agent/core/validator.py`
- Create: `backend/stock_agent/core/render.py`
- Create: `backend/stock_agent/core/history.py`

**Interfaces:**
- Consumes: `stock_agent.prompts` 的 `build_system_prompt`/`build_user_prompt`；`stock_agent.models` 的 `DataIncompleteError`；`stock_agent.skill.report` 的 `generate_report_sync`（仅 main 入口用，延迟 import）
- Produces: `core/parser.py` 导出 `_parse_json`/`_extract_outermost_json`/`_bracket_completion_suffix`/`_dump_parse_failure`；`core/repair.py` 导出 `_repair_report`/`_add_usage`；`core/validator.py`/`render.py`/`history.py` 导出各自全部符号（与 stock_agent 原文件一致）

- [ ] **Step 1: 建 core/ 目录 + __init__.py**

```python
"""股票分析核心层 — LLM 分析、JSON 解析容错、报告修复、校验、渲染、历史对比"""
```

- [ ] **Step 2: 写 core/parser.py（JSON 解析容错）**

从原 `analyze.py` 第 136-300 行搬 `_dump_parse_failure` + `_extract_outermost_json` + `_bracket_completion_suffix` + `_parse_json`。import 改为：

```python
"""LLM 输出 JSON 容错解析 — DeepSeek Reasoner 偶发非法 JSON 的修复策略"""
import json
from datetime import datetime
from pathlib import Path
```

（`_dump_parse_failure` 的 `Path(__file__).parent / "reports" / "failures"` 需改为 `Path(__file__).resolve().parent.parent / "reports" / "failures"`——因为文件从 `stock_agent/analyze.py` 移到 `stock_agent/core/parser.py`，父级提升一级。）

- [ ] **Step 3: 写 core/repair.py（报告修复闭环）**

从原 `analyze.py` 第 313-316 行（`_add_usage`）+ 318-375 行（`_repair_report`）搬。import 改为：

```python
"""报告违规定点修正 — 校验失败后回传 LLM 修复"""
import json
import os

from .parser import _parse_json
```

（`_repair_report` 函数体照搬；内部用 `_parse_json`、`os.environ`、`OpenAI`。）

- [ ] **Step 4: 复制 validator.py / render.py / history.py 到 core/**

`cp backend/stock_agent/validator.py backend/stock_agent/core/validator.py`
`cp backend/stock_agent/render.py backend/stock_agent/core/render.py`
`cp backend/stock_agent/history.py backend/stock_agent/core/history.py`

原文件**保留不动**（作 facade），后续 Task 5 统一改写为 re-export。先复制成独立文件。

> **注意**：core/validator.py 内部 `from stock_agent.prompts import OUTPUT_SCHEMA` 等相对原路径 import 不变（validator.py 本就 `from stock_agent.prompts import ...`）。core/render.py、core/history.py 同理。复制后需验证 `import stock_agent.core.validator` 不报错。

- [ ] **Step 5: 跑测试验证（先验证 core 包可导入）**

Run: `cd backend && python -c "import sys; sys.path.insert(0,'.'); import stock_agent.core.parser; import stock_agent.core.repair; import stock_agent.core.validator; import stock_agent.core.render; import stock_agent.core.history; print('core OK')"`
Expected: 打印 `core OK`

- [ ] **Step 6: 全量测试 + 提交**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed（原文件仍是真实现，故全量不受影响；core 是新增未接线）

```bash
cd d:/karensAgent
git add backend/stock_agent/core/
git commit -m "refactor(stock_agent): 新建 core 子包承载分析核心（parser/repair/validator/render/history）"
```

---

### Task 5: 原路径文件改薄 facade + 删除 models.py 单文件

**Files:**
- Modify: `backend/stock_agent/analyze.py` → facade
- Modify: `backend/stock_agent/render.py` → facade
- Modify: `backend/stock_agent/validator.py` → facade
- Modify: `backend/stock_agent/history.py` → facade

**Interfaces:**
- Consumes: Task 4 的 `core/` 包
- Produces: 保持 `stock_agent.analyze`/`render`/`validator`/`history` 模块存在，符号经 re-export 指向 core

- [ ] **Step 1（唯一方案）：analyze.py 保留真实现，只把 parser/repair 委派到 core**

> **为什么不能整文件搬成 facade**：`test_analyze.py` 用 `patch('stock_agent.analyze.OpenAI')` 替换 analyze 模块的 `OpenAI` 属性。若 `analyze()` 主体搬进 core，mock 就够不到真调用处 → 测试失败。**故 analyze.py 保留 `analyze`/`analyze_with_validation`/`push_to_feishu`/`main` 主体**（`OpenAI` 属性仍在 analyze 模块，monkeypatch 有效），仅把 6 个解析/修复函数迁到 core/parser、core/repair 并从 core re-export。

`analyze.py` 改写后结构（保留原 env 读取、`FEISHU_WEBHOOK_URL`、import 头，仅顶部加 core re-export 行）：

```python
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ...（保留原 env 读取、FEISHU_WEBHOOK_URL、import 头）

from openai import OpenAI

from stock_agent.models import DataIncompleteError  # noqa: F401
from stock_agent.prompts import build_system_prompt, build_user_prompt
from stock_agent.validator import (
    validate_report, is_collapsed_report, StructuralCollapseError,
)
from stock_agent.render import render_markdown  # noqa: F401 — 保持向后兼容

# 解析/修复逻辑已迁入 core 子包（本文件保留 analyze/analyze_with_validation/push_to_feishu/main 主体）
from stock_agent.core.parser import (  # noqa: F401
    _parse_json, _extract_outermost_json, _bracket_completion_suffix, _dump_parse_failure,
)
from stock_agent.core.repair import (  # noqa: F401
    _repair_report, _add_usage,
)


def analyze(...): ...   # 原样保留（内部 _parse_json/_dump_parse_failure 来自 core re-export）
def analyze_with_validation(...): ...  # 原样保留
def push_to_feishu(...): ...  # 原样保留
def main(): ...  # 原样保留
```

这样 `analyze.py` 从 565 行降到约 250 行（只剩 4 个主函数），`OpenAI` 属性仍在 analyze 模块，monkeypatch 有效，`_parse_json` 等经 re-export 可用。

- [ ] **Step 2: 改写 render.py / validator.py / history.py 为 facade**

`render.py`、`validator.py`、`history.py` 无 monkeypatch 路径（只有 `from ... import X`），可安全改为 facade：

```python
# stock_agent/render.py
"""Markdown 渲染 — 兼容门面（真实现见 stock_agent.core.render）"""
from stock_agent.core.render import render_markdown  # noqa: F401
from stock_agent.core.render import _escape_cell  # noqa: F401
```

```python
# stock_agent/validator.py
"""报告校验 — 兼容门面（真实现见 stock_agent.core.validator）"""
from stock_agent.core.validator import (  # noqa: F401
    validate_report,
    is_collapsed_report,
    StructuralCollapseError,
    REQUIRED_FIELDS,
    VALID_DECISIONS,
)
```

```python
# stock_agent/history.py
"""历史对比 — 兼容门面（真实现见 stock_agent.core.history）"""
from stock_agent.core.history import (  # noqa: F401
    build_history_context,
    sample_history_indices,
    extract_skeleton,
    MAX_HISTORY,
)
```

> **验证**：需先确认 `validator.py` 暴露给外部的全部符号（测试 `from stock_agent.validator import validate_report, is_collapsed_report` 之外，`REQUIRED_FIELDS` 是否被外部引用）。`grep -rn "REQUIRED_FIELDS\|VALID_DECISIONS\|MAX_HISTORY\|extract_skeleton" tests/ routers/ --include="*.py"`。若 `test_validator.py` 直接引用常量，facade 需一并 re-export。执行时先跑 `grep` 确认符号全集，再写 facade。

- [ ] **Step 3: 删除 models.py 单文件（已拆为子包）**

`rm backend/stock_agent/models.py`（Task 1 已建 `models/` 子包，此处删旧单文件，避免两个 models 路径冲突）

- [ ] **Step 4: 跑全量测试**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed（facade 全部 re-export 正确、monkeypatch 路径仍有效）

- [ ] **Step 5: import 冒烟 + 提交**

Run: `cd backend && python -c "from stock_agent.analyze import analyze, _parse_json; from stock_agent.render import render_markdown; from stock_agent.validator import validate_report; from stock_agent.history import build_history_context; from stock_agent.models import MarketData; from stock_agent.skill import call_skill, extract_text; print('SMOKE OK')"`
Expected: `SMOKE OK`

```bash
cd d:/karensAgent
git add -A backend/stock_agent/
git commit -m "refactor(stock_agent): 原路径文件改薄 facade，models 拆子包删单文件"
```

---

### Task 6: 验证 + 收尾

**Files:**
- 无新文件，仅验证

**Interfaces:**
- 无

- [ ] **Step 1: 全量测试**

Run: `cd backend && python -m pytest tests -q`
Expected: 191 passed

- [ ] **Step 2: 残留引用检查**

Run: `cd backend && grep -rn "modular\|reviewer\|ifind_client\|fetchers\." --include="*.py" . | grep -v __pycache__`
Expected: 无输出

- [ ] **Step 3: 生产入口检查**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
# 模拟 routers/stock_api.py 的全部 stock_agent 引用
from stock_agent.skill.report import generate_report_sync, generate_report_stream
from stock_agent.analyze import analyze_with_validation, push_to_feishu, render_markdown
from stock_agent.render import render_markdown as rm2
print('ROUTER SMOKE OK')"`
Expected: `ROUTER SMOKE OK`

- [ ] **Step 4: 目录结构最终确认**

Run: `cd d:/karensAgent && find backend/stock_agent -name "*.py" | sort`
Expected: 见 spec 目标结构（skill/{client,extract,collect,parse,format,indicators,report}.py、core/{analyze,parser,repair,validator,render,history}.py、models/{base,market,shareholders,news,risk,env,_util}.py、prompts/、datasources/）

- [ ] **Step 5: 提交收尾**

```bash
cd d:/karensAgent
git status
git commit -m "chore(stock_agent): 模块化重构完成，全量测试零回归" --allow-empty
```
（若上一步已有未提交改动则直接提交；若全绿无改动，此步可跳过空提交。）

---

## Self-Review 记录

- **Spec 覆盖**：Task 1=spec 4.4 models 拆分；Task 2=spec 4.3 skill/__init__ 拆分；Task 3=spec 4.1 report 拆分；Task 4=spec 4.2 analyze 拆分 + core 新建；Task 5=spec 5.1 facade 方案落地 + models 单文件删除；Task 6=spec 6 验证策略。全部覆盖 ✅
- **Placeholder 扫描**：无 TBD/TODO。函数体"照搬原 X-Y 行"均指明具体行号区间，执行者据此从已读源码复制 ✅
- **Type 一致性**：`analyze`/`analyze_with_validation`/`push_to_feishu`/`_parse_json`/`_repair_report` 等签名跨 Task 4/5 保持一致；`core/analyze.py` 的 `sys.path.insert` 与 `.env` 路径已按目录层级+1 修正 ✅
- **关键风险提示**：Task 5 Step 1 的 monkeypatch 陷阱（`patch('stock_agent.analyze.OpenAI')` 需 `OpenAI` 留在 analyze 模块）已在 Step 1b 修订中显式标注并给出正确做法 ✅
