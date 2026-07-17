"""
TDD Step 3: Pydantic 数据模型测试

测试目标:
  1. IfindRecord — 动态 key-value 记录，不写死字段
  2. ParsedData — 包装 unified_parse 结果，提供类型安全
  3. 序列化/反序列化往返
  4. 各领域模型结构验证
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_ifind_record_from_dict():
    """IfindRecord: 从动态 dict 创建（不硬编码字段名）"""
    from stock_agent.models import IfindRecord

    # 模拟 iFind 返回的行情记录
    record = IfindRecord.from_dict({"指标": "收盘价", "数值": "56.80", "单位": "元"})
    assert record.data["指标"] == "收盘价"
    assert record.data["数值"] == "56.80"
    assert record.data["单位"] == "元"
    print("[OK] IfindRecord.from_dict 动态字段")


def test_ifind_record_get():
    """IfindRecord.get: 安全获取字段，支持默认值"""
    from stock_agent.models import IfindRecord

    record = IfindRecord.from_dict({"PE": "25.3", "ROE": "15.8"})
    assert record.get("PE") == "25.3"
    assert record.get("ROE") == "15.8"
    assert record.get("MISSING") is None
    assert record.get("MISSING", "N/A") == "N/A"
    print("[OK] IfindRecord.get 默认值")


def test_ifind_record_to_dict():
    """IfindRecord: 序列化往返"""
    from stock_agent.models import IfindRecord

    original = {"指标": "MACD", "数值": "0.15", "单位": "-"}
    record = IfindRecord.from_dict(original)
    restored = record.to_dict()
    assert restored == original
    print("[OK] IfindRecord 序列化往返")


def test_parsed_data_from_unified_parse():
    """ParsedData: 从 unified_parse 结果创建"""
    from stock_agent.models import ParsedData, IfindRecord

    # 模拟 unified_parse 返回
    mock_parse_result = {
        "ok": True,
        "format": "markdown",
        "record_count": 3,
        "records": [
            {"指标": "收盘价", "数值": "56.80", "单位": "元"},
            {"指标": "PE", "数值": "25.3", "单位": "倍"},
            {"指标": "ROE", "数值": "15.8", "单位": "%"},
        ],
        "field_names": ["指标", "数值", "单位"],
    }

    parsed = ParsedData.from_parse_result(mock_parse_result)
    assert parsed.ok is True
    assert parsed.format == "markdown"
    assert parsed.record_count == 3
    assert len(parsed.records) == 3
    assert isinstance(parsed.records[0], IfindRecord)
    assert parsed.records[0].get("指标") == "收盘价"
    print("[OK] ParsedData.from_parse_result")


def test_parsed_data_empty():
    """ParsedData: 空结果处理"""
    from stock_agent.models import ParsedData

    empty_result = {"ok": False, "format": "empty", "record_count": 0, "records": [], "field_names": []}
    parsed = ParsedData.from_parse_result(empty_result)
    assert parsed.ok is False
    assert parsed.record_count == 0
    assert len(parsed.records) == 0
    print("[OK] ParsedData 空结果")


def test_market_data_model_with_summary():
    """MarketData: 支持 summary 摘要数据（来自 get_stock_summary）"""
    from stock_agent.models import MarketData

    records = [{"指标": "最新收盘价", "数值": "56.80", "单位": "元"}]
    summary = [
        {"指标": "公司全称", "数值": "贵州茅台酒股份有限公司"},
        {"指标": "所属行业", "数值": "白酒"},
        {"指标": "总市值", "数值": "2.1万亿", "单位": "元"},
    ]

    data = MarketData(stock_code="600519", records=records, summary=summary)
    assert data.summary_count == 3
    ctx = data.to_prompt_context()
    assert "公司全称" in ctx, "to_prompt_context 应包含摘要数据"
    assert "白酒" in ctx
    print(f"[OK] MarketData with summary: {data.summary_count} summary records")


def test_financials_data_model():
    """FinancialsData: 财务数据领域模型"""
    from stock_agent.models import FinancialsData

    records = [
        {"净资产收益率ROE(TTM)（单位：%）": "12.15"},
        {"销售毛利率(TTM)（单位：%）": "44.52"},
        {"资产负债率（单位：%）": "41.86"},
    ]

    data = FinancialsData(stock_code="000858", records=records, report_date="20260331")
    assert data.stock_code == "000858"
    assert data.record_count == 3
    assert data.report_date == "20260331"
    ctx = data.to_prompt_context()
    assert "20260331" in ctx, "to_prompt_context 应包含报告期"
    assert "ROE" in ctx
    assert "毛利率" in ctx
    print(f"[OK] FinancialsData: {data.record_count} records, report_date={data.report_date}")


def test_shareholder_data_model():
    """ShareholderData: 股东结构领域模型（含十大股东+十大流通股东+汇总指标）"""
    from stock_agent.models import ShareholderData

    records = [{
        "股东户数(截止日期)": "63064",
        "前十大股东持股比例合计（单位：%）": "66.83",
        "机构持股比例合计（单位：%）": "72.60",
        "户均持股数量（单位：股）": "5150",
        "户均持股比例（单位：‰）": "0.0041",
        "股东名称（十大股东排名：第1名）": "测试控股集团",
        "股东持股比例（十大股东排名：第1名；单位：%）": "36.77",
        "股东名称（十大股东排名：第2名）": "测试投资公司",
        "股东持股比例（十大股东排名：第2名；单位：%）": "23.06",
        # 十大流通股东
        "流通股东名称（十大流通股东排名：第1名）": "北向资金",
        "流通股东持股比例（十大流通股东排名：第1名；单位：%）": "5.20",
        "流通股东名称（十大流通股东排名：第2名）": "社保基金",
        "流通股东持股比例（十大流通股东排名：第2名；单位：%）": "3.10",
    }]

    data = ShareholderData(stock_code="000858", records=records, report_date="20260331")
    assert data.record_count == 1
    assert data.report_date == "20260331"
    ctx = data.to_prompt_context()
    assert "20260331" in ctx, "to_prompt_context 应包含报告期"
    # 汇总指标
    assert "63064" in ctx
    assert "72.60" in ctx
    # 十大股东
    assert "测试控股集团" in ctx
    assert "36.77%" in ctx
    # 十大流通股东
    assert "北向资金" in ctx
    assert "5.20%" in ctx
    assert "十大流通股东" in ctx
    print(f"[OK] ShareholderData: {data.record_count} records, report_date={data.report_date}")


def test_news_events_data_model():
    """NewsEventsData: 新闻+公告领域模型"""
    from stock_agent.models import NewsEventsData

    news_records = [
        {"title": "中芯国际Q2财报超预期", "source": "东方财富", "time": "2026-07-10"},
        {"title": "半导体政策利好", "source": "同花顺", "time": "2026-07-09"},
    ]
    notice_records = [
        {"title": "中芯国际：2026年半年度业绩预告", "type": "业绩预告", "date": "2026-07-08"},
    ]

    data = NewsEventsData(
        stock_code="688981",
        news=news_records,
        notices=notice_records,
    )
    assert data.news_count == 2
    assert data.notice_count == 1
    ctx = data.to_prompt_context()
    assert "Q2财报超预期" in ctx
    assert "业绩预告" in ctx
    print(f"[OK] NewsEventsData: {data.news_count} news + {data.notice_count} notices")


def test_news_events_data_model_with_events():
    """NewsEventsData: 支持重大事件总结（LLM 总结后的中文文本）"""
    from stock_agent.models import NewsEventsData

    news_records = [{"title": "新闻1", "source": "东财", "time": "2026-07-10"}]
    notice_records = [{"title": "公告1", "type": "业绩预告", "date": "2026-07-08"}]
    events_summary = "贵州茅台近年实施了多次分红，最近一次为10派5元；暂无增发和回购记录。"

    data = NewsEventsData(
        stock_code="600519",
        news=news_records,
        notices=notice_records,
        events=events_summary,
    )
    assert data.news_count == 1
    assert data.notice_count == 1
    assert data.has_events is True
    ctx = data.to_prompt_context()
    assert "重大事件总结" in ctx, "to_prompt_context 应包含重大事件总结"
    assert "10派5元" in ctx
    print(f"[OK] NewsEventsData with events summary")


def test_risk_data_model():
    """RiskData: 风险+ESG 领域模型"""
    from stock_agent.models import RiskData

    risk_records = [
        {"指标": "贝塔", "数值": "1.15", "单位": "-"},
        {"指标": "波动率", "数值": "28.5", "单位": "%"},
        {"指标": "夏普比率", "数值": "0.85", "单位": "-"},
        {"指标": "最大回撤", "数值": "-35.2", "单位": "%"},
    ]
    esg_records = [
        {"指标": "ESG评级", "数值": "BBB", "单位": "-"},
    ]

    data = RiskData(stock_code="002371", risk=risk_records, esg=esg_records)
    assert data.risk_count == 4
    assert data.esg_count == 1
    assert data.get_risk_value("贝塔") == "1.15"
    ctx = data.to_prompt_context()
    assert "贝塔" in ctx
    print(f"[OK] RiskData: {data.risk_count} risk + {data.esg_count} esg")


def test_market_env_data_model():
    """MarketEnvData: 市场环境+EDB 领域模型"""
    from stock_agent.models import MarketEnvData

    records = [
        {"指标": "相对大盘强弱", "数值": "1.2", "单位": "-"},
        {"指标": "板块排名", "数值": "15/120", "单位": "-"},
    ]
    edb_records = [
        {"指标": "全球半导体月度销售额", "数值": "52.3", "单位": "十亿美元"},
    ]

    data = MarketEnvData(stock_code="688981", records=records, edb=edb_records)
    assert data.record_count == 2
    assert data.edb_count == 1
    ctx = data.to_prompt_context()
    assert "半导体" in ctx
    print(f"[OK] MarketEnvData: {data.record_count} records + {data.edb_count} edb")


if __name__ == "__main__":
    print("=" * 50)
    print("TDD Step 3: Pydantic 数据模型测试")
    print("=" * 50)

    print("\n── IfindRecord ──")
    test_ifind_record_from_dict()
    test_ifind_record_get()
    test_ifind_record_to_dict()

    print("\n── ParsedData ──")
    test_parsed_data_from_unified_parse()
    test_parsed_data_empty()

    print("\n── 领域模型 ──")

    test_market_data_model_with_summary()
    test_financials_data_model()
    test_shareholder_data_model()
    test_news_events_data_model()
    test_news_events_data_model_with_events()
    test_risk_data_model()
    test_market_env_data_model()

    print("\n" + "=" * 50)
    print("[OK] All tests would fail (models not yet created)")
