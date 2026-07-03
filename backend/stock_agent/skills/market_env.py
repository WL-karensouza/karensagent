"""
市场环境技能
=============
分析个股所处的市场环境：大盘趋势、风格偏好、板块表现、相对强弱

数据来源：
- 大盘指数（通过 fetcher 采集或独立获取）
- 板块数据（akshare 概念板块）
- 已有技术数据的"相对强弱"推导

此技能帮助 LLM 将个股分析置于更大的市场背景中，
避免孤立地只看个股数据。
"""
from typing import Any


def market_env_skill(data: dict) -> dict[str, Any]:
    """市场环境分析——结合大盘和板块数据，始终可提供基本判断"""

    fields: dict[str, Any] = {}

    # ── 从实时行情推导相对大盘强弱 ──
    pct_5d = data.get("pct_5d")
    pct_20d = data.get("pct_20d")
    spot = data.get("spot", {})
    latest_close = data.get("latest_close")
    stock_name = data.get("stock_name", data.get("stock_code", ""))

    # 大盘背景（通过 LLM 知识填充具体数值，这里提供分析框架）
    fields["分析框架"] = "将个股置于市场大背景中，避免孤立分析"

    # 个股近期表现
    perf: dict[str, Any] = {}
    if pct_5d is not None:
        perf["5日涨跌"] = f"{pct_5d:+.2f}%"
    if pct_20d is not None:
        perf["20日涨跌"] = f"{pct_20d:+.2f}%"
    if spot:
        总市值 = spot.get("总市值", "")
        if 总市值 and 总市值 != "0":
            try:
                mv = float(总市值) / 1e8
                perf["总市值"] = f"{mv:.0f}亿"
                if mv > 1000:
                    perf["市值风格"] = "大盘股（>1000亿），走势通常与大盘指数高度相关"
                elif mv > 100:
                    perf["市值风格"] = "中盘股（100-1000亿），兼具成长性和稳定性"
                else:
                    perf["市值风格"] = "小盘股（<100亿），波动大，受资金面影响显著"
            except (ValueError, TypeError):
                pass
        市盈率 = spot.get("市盈率", "")
        if 市盈率 and 市盈率 != "0" and 市盈率 != "-":
            try:
                pe_val = float(市盈率)
                if pe_val < 0:
                    perf["估值风格"] = "亏损（无 PE 参考），市场定价依赖于预期反转"
                elif pe_val > 50:
                    perf["估值风格"] = "成长/题材风格（高 PE），市场愿意给高溢价"
                elif pe_val > 20:
                    perf["估值风格"] = "合理成长（中等 PE）"
                else:
                    perf["估值风格"] = "价值风格（低 PE），市场定价偏保守"
            except (ValueError, TypeError):
                pass

    fields["个股特征"] = perf

    # ── 趋势强弱信号 ──
    closes_for_trend = []
    bars = data.get("recent_bars", [])
    if bars:
        closes_for_trend = [b["close"] for b in bars]
        # 计算近5日 vs 近20日均线偏离，判断短期强弱
        if len(closes_for_trend) >= 20:
            ma20_recent = sum(closes_for_trend[-20:]) / 20
            ma5_recent = sum(closes_for_trend[-5:]) / 5
            if ma5_recent > ma20_recent * 1.03:
                fields["相对强弱"] = "短期强于中期趋势（MA5 > MA20 * 1.03），处于强势区间"
            elif ma5_recent < ma20_recent * 0.97:
                fields["相对强弱"] = "短期弱于中期趋势（MA5 < MA20 * 0.97），处于弱势区间"
            else:
                fields["相对强弱"] = "短期与中期趋势基本一致，处于均衡区间"

    # ── 识别可能的板块/题材属性（通过名称关键词，供 LLM 补充）──
    theme_hints = []
    name_lower = stock_name.lower() if stock_name else ""
    # 简单的关键词映射，帮助 LLM 定位行业
    keyword_map = {
        "茅台": "白酒/消费", "五粮液": "白酒/消费", "宁德": "新能源/电池",
        "比亚迪": "新能源/汽车", "海澜": "服装/消费", "美的": "家电/消费",
        "格力": "家电/消费", "平安": "金融/保险", "招商": "银行/金融",
        "恒瑞": "医药/创新药", "京东方": "面板/电子", "海康": "安防/AI",
        "隆基": "光伏/新能源", "中信": "券商/金融", "万科": "地产",
        "伊利": "食品/消费", "长江电力": "电力/公用事业", "中芯": "芯片/半导体",
    }
    for kw, theme in keyword_map.items():
        if kw in name_lower:
            theme_hints.append(theme)
    if theme_hints:
        fields["可能关联板块"] = "、".join(theme_hints)

    return {
        "enabled": True,
        "section": {
            "title": "市场环境",
            "fields": fields,
            "hint": (
                "请基于以上个股特征和你的大盘知识给出："
                "1）当前市场风格是否有利于该股（如价值/成长/题材切换）；"
                "2）该股所属板块近期表现及资金关注度；"
                "3）个股相对大盘的强弱判断。"
                "注意：如果你不知道近期大盘具体表现，请如实说明'基于 LLM 训练数据的判断'，不要编造今日大盘数据。"
            ),
        },
    }
