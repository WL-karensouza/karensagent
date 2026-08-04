"""港股支持测试

TDD 接缝（已与王磊哥哥确认）：
  1. normalize_stock_code — 港股代码归一化（HK2513 → 2513.HK）
  2. generate_report_sync — 港股路由到 global_stock 服务（mock call_skill 外部边界）
  3. extract_text — "不属于A股股票数据范围" 应识别为失败

fixture 数据来自 2026-07-17 对 iFinD 的真实抓包。
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_normalize_stock_code():
    """港股代码各种写法归一化为 xxxx.HK，A 股代码原样返回"""
    from stock_agent.skill.report import normalize_stock_code

    assert normalize_stock_code("HK2513") == "2513.HK"
    assert normalize_stock_code("hk2513") == "2513.HK"
    assert normalize_stock_code("2513.hk") == "2513.HK"
    assert normalize_stock_code("2513.HK") == "2513.HK"
    assert normalize_stock_code(" HK2513 ") == "2513.HK"
    # A 股代码不受影响
    assert normalize_stock_code("600519") == "600519"
    assert normalize_stock_code("000858") == "000858"
    print("[OK] normalize_stock_code 归一化")


def _envelope(inner_data) -> dict:
    """构造 SKILL 返回的 MCP JSON-RPC 包装（与真实响应结构一致）"""
    inner = {"code": 1, "msg": "success", "subCode": None, "subMsg": None, "data": inner_data}
    return {
        "ok": True,
        "status_code": 200,
        "data": {"result": {"content": [{"text": json.dumps(inner, ensure_ascii=False)}]}},
    }


# 真实抓包：global_stock_profile 对 2513.HK 的应答（含公司中文名称表格）
PROFILE_ANSWER_2513 = (
    "|证券代码|证券简称|所属同花顺行业名称|公司中文名称|主营业务|上市日期|\n"
    "|---|---|---|---|---|---|\n"
    "|2513.HK|智谱|\t|北京智谱华章科技股份有限公司|集团的主要业务为在中国提供大模型相关服务。|20260108|\n"
)


def _patch_report(fake_call):
    """替换采集模块的 call_skill 外部边界并取消限速，返回恢复函数

    拆分后 call_skill 由 collect.py 持有、RATE_LIMIT_INTERVAL 由 report.py 门面持有，
    故两个挂载点分别 patch（collect_mod.call_skill + report_mod.RATE_LIMIT_INTERVAL）。
    """
    import stock_agent.skill.collect as collect_mod
    import stock_agent.skill.report as report_mod

    old_call = collect_mod.call_skill
    old_interval = report_mod.RATE_LIMIT_INTERVAL
    collect_mod.call_skill, report_mod.RATE_LIMIT_INTERVAL = fake_call, 0

    def restore():
        collect_mod.call_skill, report_mod.RATE_LIMIT_INTERVAL = old_call, old_interval

    return restore


def test_hk_code_routes_to_global_stock():
    """港股代码走 global_stock/news 服务，绝不调用 A 股 stock 服务"""
    from stock_agent.skill.report import generate_report_sync

    calls = []

    def fake_call(server, tool, params):
        calls.append((server, tool))
        return _envelope({"answer": PROFILE_ANSWER_2513})

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("HK2513")
    finally:
        restore()

    servers = {s for s, _ in calls}
    assert "stock" not in servers, f"港股不应调用 A 股 stock 服务，实际调用：{servers}"
    assert "global_stock" in servers, f"港股应调用 global_stock 服务，实际调用：{servers}"
    assert "news" in servers, "港股仍应采集新闻/公告"
    # 归一化后的代码贯穿报告与返回值
    assert "（2513.HK）" in result["markdown"], "报告标题应使用归一化代码 2513.HK"
    assert result["stock_code"] == "2513.HK", "返回值应包含归一化后的 stock_code"
    print(f"[OK] 港股路由 — 共 {len(calls)} 次调用，服务集合 {servers}")


def test_extract_text_flags_out_of_scope():
    """"不属于A股股票数据范围" 应被识别为无数据（而不是当成正常数据混入报告）"""
    from stock_agent.skill import extract_text

    # 真实抓包：stock 服务对港股 2513.HK 的应答
    env = _envelope({"answer": "不属于A股股票数据范围"})
    text = extract_text(env)
    assert text.startswith("[无数据]"), f"应以 [无数据] 开头标记失败，实际：{text!r}"
    print("[OK] extract_text 识别 A 股范围外应答为失败")


def test_hk_stock_name_extracted_from_profile_table():
    """港股公司名应从 global_stock_profile 的表格应答中提取（公司中文名称列）"""
    from stock_agent.skill.report import generate_report_sync

    def fake_call(server, tool, params):
        return _envelope({"answer": PROFILE_ANSWER_2513})

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("2513.HK")
    finally:
        restore()

    assert result["stock_name"] == "北京智谱华章科技股份有限公司", \
        f"应提取公司中文名称，实际：{result['stock_name']!r}"
    print(f"[OK] 港股公司名提取 — {result['stock_name']}")


def test_a_share_still_routes_to_stock_server():
    """回归护栏：A 股代码仍走原 stock 服务，不受港股改动影响"""
    from stock_agent.skill.report import generate_report_sync

    calls = []

    def fake_call(server, tool, params):
        calls.append((server, tool))
        return _envelope({"answer": "公司全称：贵州茅台酒股份有限公司，所属行业：白酒。"})

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("600519")
    finally:
        restore()

    servers = {s for s, _ in calls}
    assert "global_stock" not in servers, f"A 股不应调用 global_stock，实际：{servers}"
    assert "stock" in servers, f"A 股应调用 stock 服务，实际：{servers}"
    assert result["stock_code"] == "600519"
    assert result["stock_name"] == "贵州茅台酒股份有限公司"
    print(f"[OK] A 股路由回归 — 服务集合 {servers}")


def test_news_dimensions_carry_time_range():
    """新闻/公告维度必须携带 time_start/time_end（iFinD 必填），港股与 A 股同样适用"""
    import re as _re
    from stock_agent.skill.report import generate_report_sync

    for code in ("2513.HK", "600519"):
        news_params = []

        def fake_call(server, tool, params):
            if server == "news":
                news_params.append((tool, params))
            return _envelope({"answer": PROFILE_ANSWER_2513})

        restore = _patch_report(fake_call)
        try:
            generate_report_sync(code)
        finally:
            restore()

        assert news_params, f"{code} 应调用 news 服务"
        for tool, params in news_params:
            assert "query" in params, f"{code}/{tool} 缺少 query"
            for field in ("time_start", "time_end"):
                assert field in params, f"{code}/{tool} 缺少必填参数 {field}：{params}"
                assert _re.fullmatch(r"\d{4}-\d{2}-\d{2}", params[field]), \
                    f"{code}/{tool} 的 {field} 应为 YYYY-MM-DD：{params[field]!r}"
    print("[OK] 新闻/公告维度携带时间范围（港股 + A 股）")


if __name__ == "__main__":
    test_normalize_stock_code()
    test_hk_code_routes_to_global_stock()
    test_extract_text_flags_out_of_scope()
    test_hk_stock_name_extracted_from_profile_table()
    test_a_share_still_routes_to_stock_server()
    test_news_dimensions_carry_time_range()
