"""
基本面及财务分析技能
==================
从 F10 财务数据中提取五维结构化指标：估值/盈利/成长/偿债/现金流
数据来源：东方财富 DataCenter F10 + 腾讯实时行情 PE
纯数据提取 + 分析提示，不做 LLM 分析（LLM 负责解读）
"""
from typing import Any


def fundamental_skill(data: dict) -> dict[str, Any]:
    """基本面及财务分析——五维结构化输出"""

    fund = data.get("fundamental")
    spot = data.get("spot", {})

    # PE/PB 来自腾讯实时行情
    pe_str = spot.get("市盈率", "")
    pe = None
    try:
        pe = float(pe_str)
    except (ValueError, TypeError):
        pass

    if not fund and pe is None:
        return {"enabled": False, "reason": "基本面及财务数据不可用"}

    fields: dict[str, Any] = {}
    data_sources: list[str] = []

    # ── 估值维度 ──
    val_fields: dict[str, Any] = {}
    if pe is not None:
        val_fields["市盈率(PE)"] = pe
        data_sources.append("腾讯实时行情")
    eps = fund.get("eps") if fund else None
    bps = fund.get("bps") if fund else None
    if eps is not None:
        val_fields["每股收益(EPS)"] = eps
    if bps is not None:
        val_fields["每股净资产(BPS)"] = bps
    if val_fields:
        fields["估值"] = val_fields

    # ── 盈利能力 ──
    if fund:
        profit_fields: dict[str, Any] = {}
        gm = fund.get("gross_margin")
        nm = fund.get("net_margin")
        roe = fund.get("roe")
        roic = fund.get("roic")
        if gm is not None:
            profit_fields["毛利率"] = f"{gm}%"
            if gm > 50:
                profit_fields["毛利率评价"] = "高毛利，产品有定价权"
            elif gm > 20:
                profit_fields["毛利率评价"] = "中等毛利"
            else:
                profit_fields["毛利率评价"] = "低毛利，竞争激烈"
        if nm is not None:
            profit_fields["净利率"] = f"{nm}%"
        if roe is not None:
            profit_fields["ROE"] = f"{roe}%"
            if roe > 20:
                profit_fields["盈利能力"] = "优秀（ROE>20%）"
            elif roe > 10:
                profit_fields["盈利能力"] = "良好（ROE 10-20%）"
            elif roe > 0:
                profit_fields["盈利能力"] = "一般（ROE<10%）"
            else:
                profit_fields["盈利能力"] = "亏损"
        if roic is not None:
            profit_fields["ROIC"] = f"{roic}%"
        if profit_fields:
            fields["盈利能力"] = profit_fields

    # ── 成长性 ──
    if fund:
        grow_fields: dict[str, Any] = {}
        rev_yoy = fund.get("revenue_yoy")
        profit_yoy = fund.get("profit_yoy")
        deduct_yoy = fund.get("deduct_profit_yoy")
        if rev_yoy is not None:
            grow_fields["营收增速(同比)"] = f"{rev_yoy}%"
        if profit_yoy is not None:
            grow_fields["净利润增速(同比)"] = f"{profit_yoy}%"
        if deduct_yoy is not None:
            grow_fields["扣非净利增速"] = f"{deduct_yoy}%"
        if rev_yoy is not None and profit_yoy is not None:
            if rev_yoy > 20 and profit_yoy > 20:
                grow_fields["成长性"] = "高增长（营收利润双>20%）"
            elif rev_yoy > 0 and profit_yoy > 0:
                grow_fields["成长性"] = "稳健增长"
            elif rev_yoy < 0 and profit_yoy < 0:
                grow_fields["成长性"] = "双降，需关注经营风险"
            else:
                grow_fields["成长性"] = "营收和利润增速分化，需分析原因"
        if grow_fields:
            fields["成长性"] = grow_fields

    # ── 偿债能力 ──
    if fund:
        debt_fields: dict[str, Any] = {}
        cr = fund.get("current_ratio")
        qr = fund.get("quick_ratio")
        dr = fund.get("debt_ratio")
        ic = fund.get("interest_coverage")
        if cr is not None:
            debt_fields["流动比率"] = cr
            if cr > 2:
                debt_fields["短期偿债"] = "充裕（流动比率>2）"
            elif cr > 1:
                debt_fields["短期偿债"] = "正常"
            else:
                debt_fields["短期偿债"] = "紧张（流动比率<1）"
        if qr is not None:
            debt_fields["速动比率"] = qr
        if dr is not None:
            debt_fields["资产负债率"] = f"{dr}%"
            if dr > 70:
                debt_fields["财务风险"] = "高负债（>70%），需关注偿债压力"
            elif dr > 40:
                debt_fields["财务风险"] = "中等负债"
            else:
                debt_fields["财务风险"] = "低负债，财务稳健"
        if ic is not None:
            debt_fields["利息保障倍数"] = ic
        if debt_fields:
            fields["偿债能力"] = debt_fields

    # ── 现金流质量 ──
    if fund:
        cash_fields: dict[str, Any] = {}
        nco_np = fund.get("nco_netprofit_ratio")
        nco_rev = fund.get("nco_revenue_ratio")
        clr = fund.get("cash_liquidity_ratio")
        eps_c = fund.get("eps_cash")
        if nco_np is not None:
            cash_fields["经营现金流/净利润"] = nco_np
            if nco_np >= 1:
                cash_fields["利润含金量"] = "高（现金流覆盖净利润，利润真实）"
            elif nco_np >= 0.5:
                cash_fields["利润含金量"] = "一般（部分利润为应收）"
            elif nco_np > 0:
                cash_fields["利润含金量"] = "偏低（利润多停留在账面上）"
            else:
                cash_fields["利润含金量"] = "预警（经营现金流为负！）"
        if nco_rev is not None:
            cash_fields["经营现金流/营收"] = nco_rev
        if clr is not None:
            cash_fields["现金流动负债比"] = clr
        if eps_c is not None:
            cash_fields["每股经营现金流"] = eps_c
        if cash_fields:
            fields["现金流"] = cash_fields

    if fund and fund.get("fin_source"):
        data_sources.append(fund["fin_source"])

    return {
        "enabled": True,
        "section": {
            "title": "基本面及财务分析",
            "fields": fields,
            "data_sources": data_sources or ["腾讯实时行情"],
            "hint": "请基于以上五维财务数据（估值/盈利/成长/偿债/现金流）进行财务综合分析。注意：1）不同行业合理毛利率/PE差异大，请结合行业特征解读；2)若某维度数据缺失则跳过该维度；3)重点标注异常信号（如现金流为负、ROE骤降、负债激增）。",
        },
    }
