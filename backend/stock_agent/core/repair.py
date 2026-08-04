"""报告违规定点修正 — 成本累加工具

_repair_report 因内部调用 OpenAI、受 patch('stock_agent.analyze.OpenAI')
monkeypatch 约束，保留在 stock_agent/analyze.py 本地定义（见 analyze.py 顶部注释）。
本文件只承载 _add_usage。
"""


def _add_usage(a: dict, b: dict) -> dict:
    """两份 usage 成本字典逐项累加（保持 prompt/completion/total 可观测）"""
    return {k: a.get(k, 0) + b.get(k, 0) for k in ("prompt", "completion", "total")}
