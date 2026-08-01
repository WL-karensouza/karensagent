"""历史报告采样与骨架提取 — E1 历史对比记忆

采样规则（用户确认，高优先级）：
  N=0  → 不注入
  N≤2  → 全取最近 [1..N]
  N≥3  → 取奇数位 [1, 3, 5, ...]，最多 5 份
  （序号按时间倒序，最新一份 = 1；近期密集、远期稀疏）

注入形态：只提取骨架字段（score/decision/rating_sentence/core_logic/
signal_attribution），非全文，5 份骨架约 1~2k tokens。
数据源：DB stock_reports 表 report_json 字段（database.get_recent_reports）。
"""
import json

MAX_HISTORY = 5  # 注入上限


def sample_history_indices(n: int) -> list[int]:
    """按确认规则返回采样序号（1-based，最新 = 1）

    >>> sample_history_indices(0)
    []
    >>> sample_history_indices(2)
    [1, 2]
    >>> sample_history_indices(5)
    [1, 3, 5]
    >>> sample_history_indices(100)
    [1, 3, 5, 7, 9]
    """
    if n <= 0:
        return []
    if n <= 2:
        return list(range(1, n + 1))
    # N≥3：奇数位，封顶 MAX_HISTORY 份
    return list(range(1, n + 1, 2))[:MAX_HISTORY]


def extract_skeleton(report: dict) -> dict:
    """提取报告骨架（控制注入 token，不注入全文）"""
    m1 = report.get("module_1_核心结论") or {}
    if not isinstance(m1, dict):
        m1 = {}
    return {
        "score": report.get("score"),
        "decision": report.get("decision"),
        "rating_sentence": m1.get("rating_sentence", ""),
        "core_logic": m1.get("core_logic", []),
        "signal_attribution": report.get("signal_attribution", []),
    }


def build_history_context(rows: list[dict]) -> str:
    """将 DB 报告记录转为可注入 prompt 的历史上下文段落

    Args:
        rows: database.get_recent_reports 的返回（按 id 倒序，最新在前）

    Returns:
        Markdown 格式历史上下文；无可用历史时返回空字符串
    """
    indices = sample_history_indices(len(rows))
    if not indices:
        return ""

    sections = []
    for pos in indices:
        row = rows[pos - 1]
        raw = row.get("report_json", "")
        try:
            report = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue  # 坏行跳过，不影响其他历史
        if not isinstance(report, dict):
            continue
        sk = extract_skeleton(report)
        logic = json.dumps(sk["core_logic"], ensure_ascii=False)
        sections.append(
            f"### {row.get('created_at', '未知时间')} · 评分 {sk['score']} · {sk['decision']}\n"
            f"一句话评级：{sk['rating_sentence']}\n"
            f"核心逻辑：{logic}"
        )

    if not sections:
        return ""
    return (
        "## 历史报告回顾（该股票此前的分析结论，供对比参考）\n\n"
        + "\n\n".join(sections)
    )
