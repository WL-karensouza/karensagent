"""
TDD Step 6: render.py 测试（适配 2026-07-16 9 模块 Schema）

测试目标:
  1. render_markdown 从 analyze.py 迁移到 render.py
  2. 函数签名和输出格式适配新 9 模块 JSON
  3. 综合评分、各模块、信号归因均能正确渲染
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_render_markdown_exists():
    """render_markdown 存在于 render.py"""
    from stock_agent.render import render_markdown
    assert callable(render_markdown)
    print("[OK] render_markdown 函数存在")


def test_render_markdown_basic():
    """基本报告渲染：包含评分、判断、核心结论"""
    from stock_agent.render import render_markdown

    report = {
        "score": 75,
        "decision": "看多",
        "module_1_核心结论": {
            "rating_sentence": "这是一份测试报告的概要内容。",
            "core_logic": ["核心要点1", "核心要点2"],
            "reference_prices": {},
        },
    }
    usage = {"prompt": 100, "completion": 50, "total": 150}

    md = render_markdown("600519", report, usage)

    assert "600519" in md
    assert "75" in md
    assert "看多" in md
    assert "测试报告" in md
    print(f"[OK] 基本报告渲染: {len(md)} chars")


def test_render_markdown_all_modules():
    """所有 9 模块的渲染"""
    from stock_agent.render import render_markdown

    report = {
        "score": 68,
        "decision": "震荡",
        "module_1_核心结论": {
            "rating_sentence": "多空博弈焦灼，短期方向不明。",
            "core_logic": ["业绩稳定增长", "估值处于合理区间", "资金面中性"],
            "reference_prices": {
                "support": "55.0元附近（60日均线）",
                "resistance": "62.0元附近（前期高点）",
            },
        },
        "module_2_公司画像": {
            "business": "公司主要从事半导体芯片制造，靠代工赚钱。",
            "valuation": {
                "pe_level": "偏高",
                "pb_level": "合理",
                "analysis": "PE高于行业均值但PB合理，整体估值不算便宜。",
            },
        },
        "module_3_财务健康": {
            "profitability": "越赚越多，营收和净利润双增。",
            "key_indicators": [
                {"name": "毛利率", "value": "35.2%", "trend": "连续上升", "verdict": "产品竞争力提升"},
                {"name": "ROE", "value": "15.8%", "trend": "稳定", "verdict": "股东回报尚可"},
                {"name": "资产负债率", "value": "42.1%", "trend": "下滑", "verdict": "财务杠杆降低"},
                {"name": "经营现金流/净利润", "value": "1.2", "trend": "改善", "verdict": "利润含金量高"},
            ],
            "risk_alerts": ["应收账款增速较快——钱没收回来，利润可能是纸面富贵"],
        },
        "module_4_股价走势": {
            "trend": "近期放量突破前期平台，短期强势特征明显。",
            "capital_flow": {
                "margin_trading": "融资余额持续上升，杠杆资金正在加仓看多",
                "main_force": "近5日主力净流入1.2亿，主力在悄悄吸筹",
            },
        },
        "module_5_北向资金": {
            "available": True,
            "trend": "北向资金连续3日净买入，累计净流入5.8亿",
            "interpretation": "外资在逢低捡便宜，说明这个价位机构认可",
        },
        "module_6_股东筹码": {
            "major_moves": [
                {"entity": "高管张三", "action": "减持10万股", "date": "2026-07-01", "signal": "偏空", "reason": "高管套现，注意信号"},
            ],
            "chip_analysis": "股东户数连续减少，筹码趋于集中，主力可能在吸筹。",
        },
        "module_7_催化舆情": {
            "positive": ["芯片需求复苏，行业景气度提升"],
            "negative": ["收到监管问询函，需关注合规问题"],
            "sentiment": "中性",
            "sentiment_reason": "近期新闻多空交织，舆论无明显偏向",
        },
        "module_8_风险ESG": {
            "risk_level": "中",
            "risks": [
                {"type": "市场风险", "level": "中", "desc": "换手率偏高，短期波动风险"},
                {"type": "政策风险", "level": "低", "desc": "行业政策环境稳定"},
            ],
            "esg": "公司在环保方面表现尚可，治理方面大股东持股稳定。",
        },
        "module_9_操作指南": {
            "buy_strategy": "建议分2-3批在55.0-58.0元区间关注",
            "stop_loss": "跌破52.0元需警惕，中期趋势可能转弱",
            "take_profit": "62.0-65.0元附近遇阻可考虑分批止盈",
            "holding_period": {
                "type": "中短线波段",
                "reason": "公司基本面扎实但短期涨幅已大，适合波段操作",
            },
        },
        "signal_attribution": [
            {"source": "估值面", "weight": 0.20, "direction": "偏多", "note": "PE处于历史低位"},
            {"source": "财务面", "weight": 0.25, "direction": "偏多", "note": "营收净利润双增"},
            {"source": "资金面", "weight": 0.15, "direction": "偏空", "note": "主力资金净流出"},
            {"source": "情绪面", "weight": 0.15, "direction": "中性", "note": "多空交织"},
            {"source": "风险面", "weight": 0.10, "direction": "偏空", "note": "短期涨幅过大"},
            {"source": "筹码面", "weight": 0.15, "direction": "偏多", "note": "筹码集中"},
        ],
    }
    usage = {"prompt": 500, "completion": 300, "total": 800}

    md = render_markdown("688981", report, usage)

    # 评分条
    assert "68" in md
    assert "震荡" in md

    # 9 个模块标题
    assert "核心结论" in md
    assert "公司画像" in md
    assert "财务健康" in md
    assert "股价走势" in md
    assert "北向资金" in md
    assert "股东结构" in md
    assert "催化剂" in md
    assert "风险评估" in md
    assert "操作指南" in md

    # 关键价位
    assert "55.0" in md
    assert "52.0" in md
    assert "62.0" in md

    # 信号归因
    assert "信号归因" in md
    assert "20%" in md or "20 %" in md

    # 排雷提示
    assert "应收账款" in md

    # 北向资金
    assert "5.8亿" in md

    print(f"[OK] 全模块报告渲染: {len(md)} chars")


def test_render_markdown_minimal():
    """最小输入不崩溃"""
    from stock_agent.render import render_markdown

    report = {"score": 50, "decision": "震荡"}
    usage = {"total": 100}

    md = render_markdown("000001", report, usage)
    assert len(md) > 0
    assert "000001" in md
    print(f"[OK] 最小输入渲染: {len(md)} chars")


def test_render_northbound_unavailable():
    """北向资金数据不可用时的渲染"""
    from stock_agent.render import render_markdown

    report = {
        "score": 60,
        "decision": "震荡",
        "module_5_北向资金": {
            "available": False,
            "trend": "北向资金数据暂不可用",
            "interpretation": "北向资金数据暂不可用",
        },
    }
    usage = {"total": 100}

    md = render_markdown("000001", report, usage)
    assert "数据暂不可用" in md
    print(f"[OK] 北向资金不可用渲染")


def test_render_markdown_float_score():
    """浮点评分（如 85.5）应按比例渲染进度条，而不是空条"""
    from stock_agent.render import render_markdown

    report = {"score": 85.5, "decision": "看多"}
    md = render_markdown("600519", report, {"total": 100})
    # int(85.5 / 100 * 20) = 17 格
    assert "█" * 17 + "░" * 3 in md, "浮点评分应渲染 17 格进度条"


def test_render_markdown_numeric_string_score():
    """字符串数字评分（如 LLM 偶发返回 "85"）也应正常渲染"""
    from stock_agent.render import render_markdown

    report = {"score": "85", "decision": "看多"}
    md = render_markdown("600519", report, {"total": 100})
    assert "█" * 17 + "░" * 3 in md


def test_render_markdown_invalid_score_empty_bar():
    """非数字评分（N/A）渲染空条且不崩溃"""
    from stock_agent.render import render_markdown

    report = {"score": "N/A", "decision": "震荡"}
    md = render_markdown("600519", report, {"total": 100})
    assert "░" * 20 in md


def test_render_markdown_pipe_escaped():
    """模块3 表格字段含管道符时应转义，避免破坏 Markdown 表格布局"""
    from stock_agent.render import render_markdown

    report = {
        "score": 60,
        "decision": "震荡",
        "module_3_财务健康": {
            "key_indicators": [
                {"name": "毛利率|扣非口径", "value": "89%|同比", "trend": "稳定", "verdict": "良好"},
            ],
        },
    }
    md = render_markdown("600519", report, {"total": 100})
    assert "毛利率\\|扣非口径" in md
    assert "89%\\|同比" in md


def test_render_markdown_usage_footer():
    """页脚应渲染 token 消耗（usage 参数不再是死参数）"""
    from stock_agent.render import render_markdown

    report = {"score": 75, "decision": "看多"}
    md = render_markdown("600519", report, {"prompt": 5000, "completion": 2000, "total": 7000})
    assert "7000" in md
    assert "Token" in md


if __name__ == "__main__":
    print("=" * 50)
    print("TDD Step 6: render.py 测试 (v2 9模块)")
    print("=" * 50)

    test_render_markdown_exists()
    test_render_markdown_basic()
    test_render_markdown_all_modules()
    test_render_markdown_minimal()
    test_render_northbound_unavailable()

    print("\n" + "=" * 50)
    print("[OK] All tests passed")
