"""
资金面分析技能（实验C核心验证）
==============================
数据来源优先级：
  1. akshare 主力资金流（eastmoney可用时）
  2. 量价关系推导（始终可用）

新增此技能只需：
  ① 写此文件（~50行业务逻辑）
  ② 在 __init__.py 加一行注册
  ③ 不改调度器、不改analyze.py核心逻辑
"""
from typing import Any


def capital_skill(data: dict) -> dict[str, Any]:
    """资金面分析——多数据源自适应"""

    fund_fields: dict[str, Any] = {}
    data_sources: list[str] = []

    # ── 来源1：akshare 主力资金流 ──
    fund_flow = data.get("fund_flow_recent_5d")
    if fund_flow:
        data_sources.append("akshare主力资金流")
        # 计算5日累计主力净流入
        total_main = 0
        total_super = 0
        for f in fund_flow:
            try:
                total_main += float(f.get("主力净流入-净额", 0) or 0)
                total_super += float(f.get("超大单净流入-净额", 0) or 0)
            except (ValueError, TypeError):
                pass
        fund_fields["5日主力累计净流入(万)"] = f"{total_main:+.0f}"
        fund_fields["5日超大单累计净流入(万)"] = f"{total_super:+.0f}"

        # 流向方向判断
        if total_main > 0:
            direction = "主力净流入，偏多"
        elif total_main < 0:
            direction = "主力净流出，偏空"
        else:
            direction = "主力资金平衡"
        fund_fields["主力方向"] = direction

        # 近5日逐日明细
        daily = []
        for f in fund_flow:
            daily.append({
                "date": str(f.get("日期", "")),
                "主力净流入": f.get("主力净流入-净额", "N/A"),
                "超大单": f.get("超大单净流入-净额", "N/A"),
                "大单": f.get("大单净流入-净额", "N/A"),
            })
        fund_fields["逐日明细"] = daily

    # ── 来源2：量价关系推导（始终可用）──
    bars = data.get("recent_bars", [])
    vr = data.get("volume_ratio")
    pct_5d = data.get("pct_5d")
    latest_close = data.get("latest_close")

    if bars:
        data_sources.append("量价关系推导")

        # 量价配合判断
        if vr is not None and pct_5d is not None:
            if vr > 1.2 and pct_5d > 0:
                fund_fields["量价配合"] = "放量上涨（资金主动买入）"
            elif vr > 1.2 and pct_5d < 0:
                fund_fields["量价配合"] = "放量下跌（资金主动卖出）"
            elif vr < 0.8 and pct_5d > 0:
                fund_fields["量价配合"] = "缩量上涨（上行动力不足）"
            elif vr < 0.8 and pct_5d < 0:
                fund_fields["量价配合"] = "缩量下跌（恐慌性抛售减弱）"
            else:
                fund_fields["量价配合"] = "量价正常配合"

        # 换手率
        spot = data.get("spot", {})
        turnover = spot.get("换手率", "")
        if turnover:
            try:
                t = float(turnover)
                fund_fields["换手率"] = f"{t:.2f}%"
                if t < 0.5:
                    fund_fields["活跃度"] = "极低（无人问津）"
                elif t < 1.5:
                    fund_fields["活跃度"] = "偏低"
                elif t < 4:
                    fund_fields["活跃度"] = "正常"
                elif t < 8:
                    fund_fields["活跃度"] = "活跃"
                else:
                    fund_fields["活跃度"] = "高度活跃（警惕出货）"
            except (ValueError, TypeError):
                pass

    if not fund_fields:
        return {"enabled": False, "reason": "资金流数据不可用，且量价数据不足"}

    return {
        "enabled": True,
        "section": {
            "title": "资金面",
            "fields": fund_fields,
            "data_sources": data_sources,
            "hint": "请基于以上资金面数据给出：资金情绪（积极/中性/谨慎）、独立洞察、主力动向分析",
        },
    }
