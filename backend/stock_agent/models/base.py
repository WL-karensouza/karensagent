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
