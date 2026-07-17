"""
iFind 数据模型 — 基于动态 key-value 模式

设计原则:
  - 不硬编码字段名（iFind 字段按查询动态返回）
  - 提供类型安全的包装层
  - 支持 LLM prompt 上下文的文本导出
"""
from __future__ import annotations
from typing import Optional, Any


# ═══════════════════════════════════════════
# 公共异常
# ═══════════════════════════════════════════

class DataIncompleteError(Exception):
    """关键数据缺失，拒绝调用 LLM 以防止幻觉"""
    pass


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

# iFind markdown 表格通用元数据列（非业务指标）
_TABLE_META_KEYS = frozenset({
    "证券代码", "证券简称", "日期", "股票代码", "股票名称",
    "stock_code", "stock_name", "date",
})


def _iter_fields(records: list[dict], skip_meta: bool = True):
    """遍历 records 列表的所有 key-value，跳过元数据列和空值"""
    for r in records:
        for k, v in r.items():
            if skip_meta and k in _TABLE_META_KEYS:
                continue
            if not v or not v.strip():
                continue
            yield k, v


# ═══════════════════════════════════════════
# 基础记录
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 解析结果包装
# ═══════════════════════════════════════════

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


# ═══════════════════════════════════════════
# 领域模型
# ═══════════════════════════════════════════

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
        """从 record 中取第一个非空字段值"""
        for k in keys:
            val = record.get(k, "")
            if val and val.strip():
                return val
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
                if v and v.strip():
                    lines.append(f"- {k}：{v}")
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
                if v and v.strip():
                    fields.append({"name": k, "value": v, "unit": ""})
            indexes.append({"name": idx_name, "code": idx_code, "fields": fields})
        edb = [{"name": k, "value": v}
               for k, v in _iter_fields(self.edb)]
        return {"indexes": indexes, "edb": edb}
