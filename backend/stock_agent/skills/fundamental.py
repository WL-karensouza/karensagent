"""
基本面分析技能
=============
从财务数据中提取估值水位、盈利能力、成长性信号
数据来源：fetcher._fetch_fundamental()（新浪/东方财富）
纯数据提取 + 分析提示，不做 LLM 分析（LLM 负责解读）
"""
from typing import Any


def fundamental_skill(data: dict) -> dict[str, Any]:
    """基本面分析——财务数据可用时才启用"""

    fund = data.get("fundamental")
    if not fund:
        # fallback：腾讯实时行情里有市盈率
        spot = data.get("spot", {})
        pe_from_spot = spot.get("市盈率", "")
        if pe_from_spot and pe_from_spot != "0" and pe_from_spot != "-":
            return {
                "enabled": True,
                "section": {
                    "title": "基本面",
                    "fields": {"市盈率(TTM)": pe_from_spot},
                    "data_sources": ["腾讯实时行情"],
                    "hint": "仅提供市盈率参考，无完整财务数据。请基于 PE 给出估值水位判断（偏高/合理/偏低）、独立洞察",
                },
            }
        return {"enabled": False, "reason": "基本面数据不可用（PE/PB/ROE 均获取失败）"}

    fields: dict[str, Any] = {}
    data_sources: list[str] = []

    # PE
    pe = fund.get("pe")
    if pe is not None:
        fields["市盈率(TTM)"] = pe
        # 判断 PE 水位（简单规则，具体由 LLM 结合行业解读）
        if pe < 0:
            fields["PE信号"] = "亏损（PE 为负）"
        elif pe > 100:
            fields["PE信号"] = "极高估值区间"
        elif pe > 50:
            fields["PE信号"] = "偏高估值区间"
        elif pe > 20:
            fields["PE信号"] = "合理估值区间"
        else:
            fields["PE信号"] = "偏低估值区间"

    # PB
    pb = fund.get("pb")
    if pb is not None:
        fields["市净率(PB)"] = pb
        if pb < 1:
            fields["PB信号"] = "破净（PB<1），可能存在价值低估"
        elif pb > 8:
            fields["PB信号"] = "高 PB，市场给予高溢价"

    # ROE
    roe = fund.get("roe")
    if roe is not None:
        fields["ROE(加权)"] = f"{roe}%"
        if roe > 20:
            fields["盈利能力"] = "优秀（ROE>20%）"
        elif roe > 10:
            fields["盈利能力"] = "良好（ROE 10-20%）"
        elif roe > 0:
            fields["盈利能力"] = "一般（ROE<10%）"
        else:
            fields["盈利能力"] = "亏损"

    # 成长性
    rev = fund.get("revenue_yoy")
    profit = fund.get("profit_yoy")
    if rev is not None:
        fields["营收增速(同比)"] = f"{rev}%"
    if profit is not None:
        fields["净利润增速(同比)"] = f"{profit}%"
    if rev is not None and profit is not None:
        if rev > 20 and profit > 20:
            fields["成长性"] = "高增长（营收和利润均 >20%）"
        elif rev > 0 and profit > 0:
            fields["成长性"] = "稳健增长"
        elif rev < 0 and profit < 0:
            fields["成长性"] = "双降，需关注经营风险"
        else:
            fields["成长性"] = "营收和利润增速分化"

    # 财务健康
    debt = fund.get("debt_ratio")
    eps = fund.get("eps")
    if debt is not None:
        fields["资产负债率"] = f"{debt}%"
        if debt > 70:
            fields["财务风险"] = "高负债（>70%），需关注偿债压力"
        elif debt > 40:
            fields["财务风险"] = "中等负债"
        else:
            fields["财务风险"] = "低负债，财务稳健"
    if eps is not None:
        fields["基本每股收益"] = eps

    # 数据来源标注
    pe_pb_src = fund.get("pe_pb_source", "")
    fin_src = fund.get("fin_source", "")
    if pe_pb_src:
        data_sources.append(pe_pb_src)
    if fin_src:
        data_sources.append(fin_src)

    return {
        "enabled": True,
        "section": {
            "title": "基本面",
            "fields": fields,
            "data_sources": data_sources or ["腾讯实时行情"],
            "hint": "请基于以上基本面数据给出：估值水位判断、盈利质量评价、成长性展望、独立洞察。注意：不同行业的合理 PE/PB 差异很大，请结合行业特征解读。",
        },
    }
