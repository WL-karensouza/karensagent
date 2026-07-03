"""
风险面分析技能
=============
综合已有各维度数据，识别和归类风险信号
纯 LLM 推理，不引入额外数据源——利用已有数据做风险评估

输出结构化风险清单，区分：
- 技术风险（破位/死叉/放量跌）
- 资金风险（主力出逃/融资下降）
- 基本面风险（高估值/业绩下滑/高负债）
- 消息面风险（利空新闻/政策风险）
"""
from typing import Any


def risk_skill(data: dict) -> dict[str, Any]:
    """风险面分析——基于已有数据推导风险信号，始终可用"""

    risk_indicators: dict[str, Any] = {}
    risk_count = 0

    # ── 技术面风险信号 ──
    rsi = data.get("rsi")
    pct_5d = data.get("pct_5d")
    pct_20d = data.get("pct_20d")

    tech_risks: list[str] = []
    if rsi is not None:
        risk_indicators["RSI(14)"] = rsi
        if rsi > 80:
            tech_risks.append("RSI>80 极度超买，回调风险高")
            risk_count += 1
        elif rsi > 70:
            tech_risks.append("RSI>70 超买区域")
            risk_count += 1
        elif rsi < 20:
            tech_risks.append("RSI<20 极度超卖，但下跌趋势可能延续")
            risk_count += 1

    # 均线排列
    mas = {}
    for p in [5, 10, 20, 60]:
        key = f"ma{p}"
        if key in data:
            mas[f"MA{p}"] = data[key]
    if mas:
        risk_indicators["均线"] = mas
        vals = list(mas.values())
        if len(vals) >= 2 and vals[0] < vals[1]:
            tech_risks.append("短期均线下穿中期均线（死叉风险）")
            risk_count += 1
        if len(vals) >= 3 and all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            tech_risks.append("均线空头排列，趋势偏弱")
            risk_count += 1

    # MACD
    macd_bar = data.get("macd_bar")
    macd_dif = data.get("macd_dif")
    if macd_bar is not None and macd_dif is not None:
        risk_indicators["MACD_DIF"] = macd_dif
        risk_indicators["MACD_BAR"] = macd_bar
        if macd_bar < 0 and macd_dif < 0:
            tech_risks.append("MACD 死叉运行中")
            risk_count += 1

    # 短期跌幅
    if pct_5d is not None and pct_5d < -5:
        tech_risks.append(f"近5日跌幅 {pct_5d}%，短期下行压力大")
        risk_count += 1
    if pct_20d is not None and pct_20d < -15:
        tech_risks.append(f"近20日跌幅 {pct_20d}%，中期趋势走弱")
        risk_count += 1

    # 量价背离
    vr = data.get("volume_ratio")
    if vr is not None and pct_5d is not None:
        risk_indicators["量比"] = vr
        if vr > 1.5 and pct_5d < -2:
            tech_risks.append("放量下跌，资金出逃信号")
            risk_count += 1

    if tech_risks:
        risk_indicators["技术风险"] = tech_risks

    # ── 资金面风险信号 ──
    fund_flow = data.get("fund_flow_recent_5d")
    capital_risks: list[str] = []
    if fund_flow:
        total_main = 0
        for f in fund_flow:
            try:
                total_main += float(f.get("主力净流入-净额", 0) or 0)
            except (ValueError, TypeError):
                pass
        if total_main < -5000:
            capital_risks.append(f"近5日主力累计净流出 {total_main/10000:.1f}亿，主力持续减仓")
            risk_count += 1
        elif total_main < -1000:
            capital_risks.append(f"近5日主力净流出 {abs(total_main/10000):.1f}亿")
            risk_count += 1

    # 换手率异常
    spot = data.get("spot", {})
    turnover = spot.get("换手率", "")
    if turnover:
        try:
            t = float(turnover)
            if t > 10:
                capital_risks.append(f"换手率 {t}% 异常高，警惕对倒出货")
                risk_count += 1
        except (ValueError, TypeError):
            pass

    if capital_risks:
        risk_indicators["资金风险"] = capital_risks

    # ── 基本面风险信号 ──
    fund = data.get("fundamental")
    fundamental_risks: list[str] = []
    if fund:
        pe = fund.get("pe")
        if pe is not None and pe < 0:
            fundamental_risks.append("公司处于亏损状态（PE 为负）")
            risk_count += 1
        elif pe is not None and pe > 100:
            fundamental_risks.append(f"PE={pe}，估值处于极高区间")
            risk_count += 1

        debt = fund.get("debt_ratio")
        if debt is not None and debt > 70:
            fundamental_risks.append(f"资产负债率 {debt}%，财务杠杆偏高")
            risk_count += 1

        rev = fund.get("revenue_yoy")
        profit = fund.get("profit_yoy")
        if rev is not None and profit is not None:
            if rev < 0 and profit < 0:
                fundamental_risks.append(f"营收增速{rev}%、利润增速{profit}%，双双下滑")
                risk_count += 1
            elif rev < -10 or profit < -30:
                fundamental_risks.append("营收或利润出现明显下滑")
                risk_count += 1

    if fundamental_risks:
        risk_indicators["基本面风险"] = fundamental_risks

    # ── 消息面风险信号 ──
    news = data.get("news")
    news_risks: list[str] = []
    if news:
        negative_keywords = ["下滑", "减持", "亏损", "处罚", "警告", "诉讼", "退市",
                            "跌停", "业绩预减", "负面", "风险提示", "调查", "冻结"]
        for n in news[:10]:
            title = str(n.get("title", ""))
            for kw in negative_keywords:
                if kw in title:
                    news_risks.append(title)
                    risk_count += 1
                    break
    if news_risks:
        risk_indicators["消息面风险信号"] = news_risks[:5]

    # ── 风险等级 ──
    if risk_count >= 5:
        level = "高"
        level_desc = "多个维度出现风险信号，需高度警惕"
    elif risk_count >= 2:
        level = "中"
        level_desc = "存在部分风险信号，需要持续跟踪"
    elif risk_count >= 1:
        level = "低"
        level_desc = "整体风险可控，个别信号值得关注"
    else:
        level = "低"
        level_desc = "未检测到明显风险信号"

    risk_indicators["风险信号计数"] = risk_count
    risk_indicators["风险等级"] = f"{level}（{level_desc}）"

    return {
        "enabled": True,
        "section": {
            "title": "风险面",
            "fields": risk_indicators,
            "hint": (
                "请基于以上风险信号给出：总体风险评估、最需要警惕的风险点（Top 3）、"
                "风险是否已被市场定价（股价已反映还是尚未反映）、"
                "不同持仓状态下的应对建议（即 position_advice: no_position 和 has_position 分别给建议）。"
                "注意：这是风险评估而非买卖建议，请用'关注''警惕''建议观察'等措辞。"
            ),
        },
    }
