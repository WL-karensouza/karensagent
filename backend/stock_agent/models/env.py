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
