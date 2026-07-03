"""
技术面分析技能
=============
从K线数据中提取：趋势判断、均线状态、MACD/RSI信号、关键价位
纯数据提取，不做LLM分析（LLM负责解读）
"""
from typing import Any


def technical_skill(data: dict) -> dict[str, Any]:
    """技术面数据提取——始终可用（只要有K线数据）"""
    bars = data.get("recent_bars", [])
    if not bars:
        return {"enabled": False, "reason": "无K线数据"}

    # 构建结构化技术摘要
    indicators: dict[str, Any] = {}

    # 均线
    mas = {}
    for p in [5, 10, 20, 60]:
        key = f"ma{p}"
        if key in data:
            mas[f"MA{p}"] = data[key]
    if mas:
        indicators["均线"] = mas
        # 多头/空头排列判断
        vals = list(mas.values())
        if all(vals[i] > vals[i + 1] for i in range(len(vals) - 1)):
            indicators["均线排列"] = "多头排列（看涨）"
        elif all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
            indicators["均线排列"] = "空头排列（看跌）"
        else:
            indicators["均线排列"] = "交叉/缠绕（震荡）"

    # RSI
    rsi = data.get("rsi")
    if rsi is not None:
        indicators["RSI(14)"] = rsi
        if rsi > 70:
            indicators["RSI信号"] = "超买区域"
        elif rsi < 30:
            indicators["RSI信号"] = "超卖区域"
        else:
            indicators["RSI信号"] = "中性"

    # MACD
    for k in ["macd_dif", "macd_dea", "macd_bar"]:
        if k in data:
            indicators[k.replace("macd_", "MACD ").upper()] = data[k]
    if "macd_bar" in data and "macd_dif" in data:
        bar = data["macd_bar"]
        dif = data["macd_dif"]
        if bar > 0 and dif > 0:
            indicators["MACD信号"] = "金叉/多头"
        elif bar < 0 and dif < 0:
            indicators["MACD信号"] = "死叉/空头"
        else:
            indicators["MACD信号"] = "走平/方向不明"

    # 量比
    vr = data.get("volume_ratio")
    if vr is not None:
        indicators["量比"] = vr
        if vr > 1.5:
            indicators["量能信号"] = f"放量（量比{vr}）"
        elif vr < 0.5:
            indicators["量能信号"] = f"缩量（量比{vr}）"
        else:
            indicators["量能信号"] = "正常"

    # 涨跌幅
    for key, label in [("pct_5d", "5日"), ("pct_10d", "10日"), ("pct_20d", "20日")]:
        if key in data:
            indicators[f"{label}涨跌幅"] = f"{data[key]:+.2f}%"

    # 关键价位（近20日高低点 + 均线）
    if bars:
        highs = [b["high"] for b in bars]
        lows = [b["low"] for b in bars]
        indicators["近期最高"] = max(highs)
        indicators["近期最低"] = min(lows)

    return {
        "enabled": True,
        "section": {
            "title": "技术面",
            "fields": indicators,
            "hint": "请基于以上技术指标给出：趋势判断、关键支撑/压力位、指标综合信号（偏多/中性/偏空）、独立洞察",
        },
    }
