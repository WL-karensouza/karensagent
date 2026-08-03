"""debate.py 纯函数测试（零 LLM 成本）

钉死 HK2513 实测暴露的崩溃形态：LLM 把 risks/catalysts 输出成对象数组时，
整合层必须哈希安全，绝不能崩。
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.debate import _dedup_items, _rule_merge, _check_consensus, _identify_divergences


def _analysis(score, decision, risks, catalysts):
    return {
        "score": score, "decision": decision,
        "core_points": [{"point": "p", "evidence": "e"}],
        "signal_attribution": [
            {"source": "估值面", "weight": 0.5, "direction": "偏多", "note": "n"},
            {"source": "财务面", "weight": 0.5, "direction": "偏空", "note": "n"},
        ],
        "risks": risks, "catalysts": catalysts,
    }


def test_dedup_dict_items():
    """dict 元素去重（HK2513 崩溃根因：dict 不可哈希）"""
    items = [{"type": "市场风险", "desc": "x"}, {"type": "政策风险", "desc": "y"},
             {"type": "市场风险", "desc": "x"}]  # 第三个与第一个相同
    out = _dedup_items(items)
    assert len(out) == 2, f"应去重为 2 项，实际 {len(out)}"
    print("[OK] dict 元素哈希安全去重")


def test_dedup_mixed_items():
    """字符串与 dict 混合去重不崩溃"""
    items = ["风险A", {"type": "风险B"}, "风险A", {"type": "风险B"}]
    out = _dedup_items(items)
    assert len(out) == 2
    print("[OK] 混合元素去重")


def test_rule_merge_dict_risks_no_crash():
    """整合层：双方 risks 为对象数组时不崩溃（HK2513 实测崩溃形态）"""
    a = _analysis(40, "看空", [{"type": "市场风险", "desc": "x"}], ["催化1"])
    b = _analysis(46, "震荡", [{"type": "市场风险", "desc": "x"}, {"type": "政策风险", "desc": "y"}],
                  [{"name": "催化2"}])  # B 的催化也是对象数组
    merged = _rule_merge(a, b)
    assert len(merged["risks"]) == 2      # 市场风险去重，共 2 项
    assert len(merged["catalysts"]) == 2  # 催化1 + 催化2对象
    assert merged["score"] == 43          # (40+46)/2
    assert merged["decision"] == "震荡"    # 43 ∈ [41, 59]
    print("[OK] 整合层对象数组不崩溃")


def test_check_consensus():
    """共识检测：decision 一致且分差 ≤5"""
    assert _check_consensus({"score": 38, "decision": "震荡"}, {"score": 40, "decision": "震荡"})
    assert not _check_consensus({"score": 38, "decision": "震荡"}, {"score": 40, "decision": "看空"})
    assert not _check_consensus({"score": 30, "decision": "看空"}, {"score": 40, "decision": "看空"})  # 差 10
    print("[OK] 共识检测")


def test_identify_divergences():
    """分歧识别：分差 / 判断 / 维度方向"""
    a = _analysis(35, "震荡", [], [])
    b = _analysis(47, "震荡", [], [])
    b["signal_attribution"][0]["direction"] = "偏空"   # 制造估值面分歧（A 偏多 vs B 偏空）
    divs = _identify_divergences(a, b)
    assert any("综合评分" in d for d in divs)          # 分差 12 > 5
    assert not any("综合判断" in d for d in divs)      # 判断一致（都是震荡）
    assert any("估值面" in d for d in divs)            # 估值面方向分歧
    print("[OK] 分歧识别")
