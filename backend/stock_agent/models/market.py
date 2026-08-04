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
