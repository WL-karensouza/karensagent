"""关键维度失败"关门"逻辑测试

TDD 接缝：
  generate_report_sync 返回值应包含 has_critical_failure 标志 ——
  关键维度（实时行情 quotes / 基本信息 summary，critical=True）失败时为 True，
  供上层（_run_analysis / invest SSE）据此硬终止，避免拿失败数据调 DeepSeek。

mock 策略与 test_hk_stock_support.py 一致：替换 call_skill 外部边界 + 取消限速。
"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _envelope(inner_data) -> dict:
    """构造 SKILL 返回的 MCP JSON-RPC 包装（与真实响应结构一致）"""
    inner = {"code": 1, "msg": "success", "data": inner_data}
    return {
        "ok": True,
        "status_code": 200,
        "data": {"result": {"content": [{"text": json.dumps(inner, ensure_ascii=False)}]}},
    }


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


def test_sync_flags_critical_failure():
    """全部维度失败时 has_critical_failure=True，markdown 含警告，sections 标记失败"""
    from stock_agent.skill.report import generate_report_sync

    def fake_call(server, tool, params):
        raise RuntimeError("模拟 iFinD 不可用")

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("600519")
        assert result["has_critical_failure"] is True
        assert "关键数据维度获取失败" in result["markdown"]
        # 失败维度的客观陈述应为失败提示（_raw_to_prose(None) 统一返回，断一条即代表）
        assert result["sections"]["quotes"] == "⚠️ 数据获取失败。"
    finally:
        restore()


def test_sync_no_flag_when_only_noncritical_fail():
    """仅非关键维度失败时 has_critical_failure=False（保持容错语义）"""
    from stock_agent.skill.report import generate_report_sync

    # 关键维度应答：quotes 走 tables 结构，summary 走 answer 文本（含公司全称避免东财兜底 HTTP）
    QUOTES_TABLES = json.dumps({"tables": [["最新价", "涨跌幅"], ["1680.00", "+1.2%"]]})
    SUMMARY_ANSWER = "公司全称：贵州茅台酒股份有限公司，所属行业：白酒，估值水平合理。"

    def fake_call(server, tool, params):
        if tool == "stock_highfreq_quotes":
            return _envelope(QUOTES_TABLES)
        if tool == "get_stock_summary":
            return _envelope({"answer": SUMMARY_ANSWER})
        raise RuntimeError("模拟非关键维度失败")

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("600519")
        assert result["has_critical_failure"] is False
        assert "关键数据维度获取失败" not in result["markdown"]
        assert result["stock_name"] == "贵州茅台酒股份有限公司"
        # 关键维度 sections 正常产出
        assert "1680.00" in result["sections"]["quotes"]
    finally:
        restore()


def test_sync_flags_critical_failure_on_vendor_soft_error():
    """厂商软错误（北交所场景）经 extract_text 转换后应触发关键维度失败标志"""
    from stock_agent.skill.report import generate_report_sync

    SUMMARY_ANSWER = "公司全称：测试股份有限公司，所属行业：测试。"

    def fake_call(server, tool, params):
        if tool == "stock_highfreq_quotes":
            # 北交所实证响应：code=1 但 data 是错误文本字符串
            return _envelope("未找到相关证券指标,请检查代码")
        if tool == "get_stock_summary":
            return _envelope({"answer": SUMMARY_ANSWER})
        raise RuntimeError("模拟非关键维度失败")

    restore = _patch_report(fake_call)
    try:
        result = generate_report_sync("830799")
        # quotes 是关键维度，软错误转换后应 raise → has_critical_failure=True
        assert result["has_critical_failure"] is True
        assert result["sections"]["quotes"] == "⚠️ 数据获取失败。"
    finally:
        restore()
