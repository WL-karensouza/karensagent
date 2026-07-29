"""
Markdown 报告渲染

将 analyze() 返回的 report dict 渲染为 Markdown 格式。
适配 2026-07-16 新版 9 模块 JSON Schema。
"""
from datetime import datetime


def _escape_cell(value) -> str:
    """转义 Markdown 表格单元格中的管道符，防止破坏表格布局"""
    return str(value).replace("|", "\\|")


def render_markdown(stock_code: str, report: dict, usage: dict, stock_name: str = "") -> str:
    """渲染为 Markdown 报告

    Args:
        stock_code: 股票代码
        report: analyze() 返回的分析结果 dict（9 模块格式）
        usage: token 用量信息（渲染到报告页脚）
        stock_name: 股票名称（可选），为空时用 stock_code 兜底
    """
    name = stock_name or stock_code
    code = stock_code
    score = report.get("score", "N/A")
    decision = report.get("decision", "N/A")

    # 评分条（兼容 int / float / 数字字符串；非法值渲染空条）
    bar_len = 20
    try:
        filled = int(float(score) / 100 * bar_len)
        filled = max(0, min(bar_len, filled))  # 越界评分钳制到 [0, bar_len]
    except (ValueError, TypeError):
        filled = 0
    bar = "█" * filled + "░" * (bar_len - filled)

    out = []
    out.append(f"# {name}（{code}）分析报告")
    out.append("")
    out.append("```")
    out.append(f"综合评分：{score}/100  [{bar}]")
    out.append(f"综合判断：{decision}")
    out.append("```")
    out.append("")

    # ── 模块1: 核心结论 ──
    m1 = report.get("module_1_核心结论", {})
    if m1:
        rating = m1.get("rating_sentence", "")
        core_logic = m1.get("core_logic", [])
        prices = m1.get("reference_prices", {})
        out.append("## 一、核心结论")
        out.append("")
        out.append(f"> **{rating}**")
        if core_logic:
            out.append("")
            for i, point in enumerate(core_logic, 1):
                out.append(f"{i}. {point}")
        if prices:
            support = prices.get("support", "")
            resistance = prices.get("resistance", "")
            if support:
                out.append("")
                out.append(f"- 支撑位：{support}")
            if resistance:
                out.append(f"- 压力位：{resistance}")

    # ── 模块2: 公司画像 ──
    m2 = report.get("module_2_公司画像", {})
    if m2:
        business = m2.get("business", "")
        valuation = m2.get("valuation", {})
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 二、公司画像与估值定位")
        if business:
            out.append("")
            out.append(f"> {business}")
        if valuation:
            pe = valuation.get("pe_level", "N/A")
            pb = valuation.get("pb_level", "N/A")
            analysis = valuation.get("analysis", "")
            out.append("")
            out.append(f"- PE 估值水位：**{pe}**")
            out.append(f"- PB 估值水位：**{pb}**")
            if analysis:
                out.append(f"- {analysis}")

    # ── 模块3: 财务健康 ──
    m3 = report.get("module_3_财务健康", {})
    if m3:
        profitability = m3.get("profitability", "")
        indicators = m3.get("key_indicators", [])
        alerts = m3.get("risk_alerts", [])
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 三、财务健康状况")
        if profitability:
            out.append("")
            out.append(f"> **{profitability}**")
        if indicators:
            out.append("")
            out.append("| 指标 | 数值 | 趋势 | 解读 |")
            out.append("|------|------|------|------|")
            for ind in indicators:
                name = ind.get("name", "")
                val = ind.get("value", "")
                trend = ind.get("trend", "")
                verdict = ind.get("verdict", "")
                out.append(f"| {_escape_cell(name)} | {_escape_cell(val)} | {_escape_cell(trend)} | {_escape_cell(verdict)} |")
        if alerts:
            out.append("")
            out.append("**⚠️ 财务排雷：**")
            for alert in alerts:
                out.append(f"- {alert}")

    # ── 模块4: 股价走势 ──
    m4 = report.get("module_4_股价走势", {})
    if m4:
        trend = m4.get("trend", "")
        cf = m4.get("capital_flow", {})
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 四、股价走势与资金动向")
        if trend:
            out.append("")
            out.append(f"> {trend}")
        if cf:
            mt = cf.get("margin_trading", "")
            mf = cf.get("main_force", "")
            if mt:
                out.append("")
                out.append(f"- **融资融券**：{mt}")
            if mf:
                out.append(f"- **主力资金**：{mf}")

    # ── 模块5: 北向资金 ──
    m5 = report.get("module_5_北向资金", {})
    if m5:
        available = m5.get("available", False)
        trend = m5.get("trend", "")
        interpretation = m5.get("interpretation", "")
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 五、北向资金/主力拆解")
        if available:
            if trend:
                out.append("")
                out.append(f"> {trend}")
            if interpretation:
                out.append("")
                out.append(f"{interpretation}")
        else:
            out.append("")
            out.append("> ⚠️ 北向资金数据暂不可用")

    # ── 模块6: 股东筹码 ──
    m6 = report.get("module_6_股东筹码", {})
    if m6:
        moves = m6.get("major_moves", [])
        chip = m6.get("chip_analysis", "")
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 六、股东结构与筹码集中度")
        if moves:
            out.append("")
            out.append("**重要增减持动向：**")
            out.append("")
            for mv in moves:
                entity = mv.get("entity", "")
                action = mv.get("action", "")
                date = mv.get("date", "")
                signal = mv.get("signal", "")
                reason = mv.get("reason", "")
                sig_emoji = {"偏多": "🟢", "偏空": "🔴", "中性": "⚪"}.get(signal, "")
                out.append(f"- {sig_emoji} {entity}：{action}（{date}）—— {reason}")
        if chip:
            out.append("")
            out.append(f"> {chip}")

    # ── 模块7: 催化舆情 ──
    m7 = report.get("module_7_催化舆情", {})
    if m7:
        positive = m7.get("positive", [])
        negative = m7.get("negative", [])
        sentiment = m7.get("sentiment", "")
        sentiment_reason = m7.get("sentiment_reason", "")
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 七、催化剂与近期舆情")
        if sentiment:
            out.append("")
            out.append(f"**整体舆情：{sentiment}** — {sentiment_reason}")
        if positive:
            out.append("")
            out.append("**🟢 利好催化：**")
            for p in positive:
                out.append(f"- {p}")
        if negative:
            out.append("")
            out.append("**🔴 利空预警：**")
            for n in negative:
                out.append(f"- {n}")

    # ── 模块8: 风险ESG ──
    m8 = report.get("module_8_风险ESG", {})
    if m8:
        risk_level = m8.get("risk_level", "")
        risks = m8.get("risks", [])
        esg = m8.get("esg", "")
        out.append("")
        out.append("---")
        out.append("")
        out.append(f"## 八、风险评估与 ESG 表现（风险等级：{risk_level}）")
        if risks:
            out.append("")
            for r in risks:
                rtype = r.get("type", "")
                rlevel = r.get("level", "")
                rdesc = r.get("desc", "")
                level_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(rlevel, "")
                out.append(f"- {level_emoji} **{rtype}**（{rlevel}）：{rdesc}")
        if esg:
            out.append("")
            out.append(f"> **ESG 解读**：{esg}")

    # ── 模块9: 操作指南 ──
    m9 = report.get("module_9_操作指南", {})
    if m9:
        buy = m9.get("buy_strategy", "")
        stop = m9.get("stop_loss", "")
        profit = m9.get("take_profit", "")
        period = m9.get("holding_period", {})
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 九、散户实战操作指南")
        if buy:
            out.append("")
            out.append(f"- **建仓策略**：{buy}")
        if stop:
            out.append(f"- **止损参考**：{stop}")
        if profit:
            out.append(f"- **止盈参考**：{profit}")
        if period:
            ptype = period.get("type", "")
            preason = period.get("reason", "")
            out.append(f"- **持有期建议**：{ptype} —— {preason}")

    # ── 信号归因 ──
    attributions = report.get("signal_attribution", [])
    if attributions:
        out.append("")
        out.append("---")
        out.append("")
        out.append("## 信号归因")
        out.append("")
        for a in attributions:
            src = a.get("source", "")
            w = a.get("weight", 0)
            d = a.get("direction", "")
            note_text = a.get("note", "")
            d_emoji = {"偏多": "🟢", "偏空": "🔴", "中性": "⚪"}.get(d, "")
            out.append(f"{d_emoji} {src} · {w*100:.0f}% · {d} → {note_text}")

    out.append("")
    out.append("---")
    out.append(f"*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    # token 消耗（dogfooding 阶段跟踪成本用）
    total_tokens = usage.get("total") if isinstance(usage, dict) else None
    if total_tokens is not None:
        out.append(f"*Token 消耗：{total_tokens}*")
    out.append("*以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。*")

    return "\n".join(out)
