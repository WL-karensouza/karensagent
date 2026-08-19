"""chat_agent.tools 工具层测试 —— execute_tool_call 的 ok 判定（防假成功）"""
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def test_execute_tool_call_flags_no_data_as_fail(monkeypatch):
    """get_stock_financials 返回"未返回有效结果"（成功包装）时 ok 应为 False

    实证（2026-08-19）：query 缺证券实体名时 iFinD 内层 code=1 success 但
    answer 为"未返回有效结果"——extract_text 已转 [无数据]，execute_tool_call
    应据此置 ok=False，消除"假成功"（避免误导 LLM 反复重试同一工具）。
    """
    from chat_agent import tools as tools_mod

    def fake_call_skill(server, tool_name, params):
        return {"ok": True, "data": {"result": {"content": [
            {"type": "text", "text": json.dumps({
                "code": 1, "msg": "success",
                "data": json.dumps({"answer": "抱歉，本次数据查询未返回有效结果"}, ensure_ascii=False)
            }, ensure_ascii=False)}
        ]}}}

    monkeypatch.setattr(tools_mod, "call_skill", fake_call_skill)
    out = tools_mod.execute_tool_call("get_stock_financials", {"query": "最近一期营收"})
    assert out["ok"] is False
    assert "[无数据]" in out["text"]


def test_execute_tool_call_normal_data_ok_true(monkeypatch):
    """正常数据返回时 ok 仍为 True（不误伤）"""
    from chat_agent import tools as tools_mod

    def fake_call_skill(server, tool_name, params):
        return {"ok": True, "data": {"result": {"content": [
            {"type": "text", "text": json.dumps({
                "code": 1, "msg": "success",
                "data": json.dumps({"answer": "销售毛利率：36.39%"}, ensure_ascii=False)
            }, ensure_ascii=False)}
        ]}}}

    monkeypatch.setattr(tools_mod, "call_skill", fake_call_skill)
    out = tools_mod.execute_tool_call("get_stock_financials", {"query": "川宁生物毛利率"})
    assert out["ok"] is True
    assert "36.39%" in out["text"]
