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
        # NOTE: 字段名是同花顺官方约定（含第{rank}名排名模板），非随意硬编码；
        # 若 iFind 改版字段命名导致取数静默为空，考虑按模式匹配做动态发现
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
