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
