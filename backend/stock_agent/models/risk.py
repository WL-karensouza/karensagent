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
