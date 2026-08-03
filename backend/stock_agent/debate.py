"""E4 实验原型：双模型中立辩论（v3 双报告合并版，不接入生产管线，仅供 e4 实验调用）

架构（用户设计）：
  阶段1 双方各产出完整 9 模块投研报告（与单次分析同款的完整报告）：
        顾问A = DeepSeek（复用生产 analyze 链路，带容错与 validator）
        顾问B = 千问（同一套三层 system prompt，千问 anthropic 端点）
  阶段2 结论层比对 + 分歧点驳论（程序化识别分歧，仅分差>5 或判断不一致才辩，≤6 轮共识即停）：
        约束 = 证据原文引用 + 数据仲裁（证据充分者胜）+ 允许修正 + 评分-判断自洽
  阶段3 执笔者合并两份完整报告（逐模块取双方之长，并集纪律：任一方独有数据点不得遗漏）

为何执笔素材用"两份完整报告"而非"结论层论据原文"：
  实测 6888825(矿机题材)结论层论据原文会触发 DeepSeek 内容安全静默拒绝（空 text），
  而完整报告正文是模型自律后的合规措辞——合并两份报告既实现并集合并，又天然脱敏。
两个模型都走各自端点：DeepSeek 生产链路(OpenAI) / 千问 anthropic 端点，SDK 统一 anthropic + OpenAI。
"""
import json
import sys
import time

import anthropic

from stock_agent.validator import validate_report

# ═══════════════════════════════════════════
# 参数
# ═══════════════════════════════════════════

MAX_DEBATE_ROUNDS = 6           # 驳论硬上限
SCORE_CONSENSUS_TOLERANCE = 5   # 共识阈值：|score 差| ≤ 5 且 decision 一致（用户确认保持 5）
BULLISH_FLOOR = 60              # score→decision 映射
BEARISH_CEIL = 40
THINKING_BUDGET = 4096          # 千问无 thinking；DeepSeek 辩论/执笔调用 thinking 预算


# ═══════════════════════════════════════════
# 统一 LLM 调用（anthropic 兼容协议，千问侧 + 辩论/执笔侧 DeepSeek）
# ═══════════════════════════════════════════

def _model_config() -> dict:
    """双模型配置，全部来自 .env（经 analyze 模块的 env_vars 解析）"""
    from stock_agent.analyze import env_vars
    return {
        "model_a": {  # DeepSeek（anthropic 端点，辩论/执笔调用用；报告生成走生产 analyze）
            "api_key": env_vars.get("DEEPSEEK_API_KEY", ""),
            "base_url": env_vars.get("LLM_BASE_URL", "https://api.deepseek.com/anthropic"),
            "model": env_vars.get("LLM_MODEL_ID", "deepseek-v4-flash"),
            "thinking": True,
            "label": "顾问A(DeepSeek)",
        },
        "model_b": {  # 千问（百炼 anthropic 端点）
            "api_key": env_vars.get("QWEN_API_KEY", ""),
            "base_url": env_vars.get("QWEN_BASE_URL", ""),
            "model": env_vars.get("QWEN_MODEL_ID", "qwen3.8-max-preview"),
            "thinking": False,
            "label": "顾问B(千问)",
        },
    }


def _call_llm(cfg: dict, system: str, user: str, max_tokens: int = 8192) -> tuple[str, dict]:
    """anthropic 协议调用，返回 (text, usage)。空 text 自动重试（端点间歇性行为防御）。"""
    client = anthropic.Anthropic(api_key=cfg["api_key"], base_url=cfg["base_url"])
    kwargs = {}
    if cfg.get("thinking"):
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": min(THINKING_BUDGET, max_tokens - 1)}
        kwargs["temperature"] = 1

    def _do_call():
        r = client.messages.create(
            model=cfg["model"], max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], **kwargs)
        t = "".join(block.text for block in r.content if getattr(block, "type", "") == "text")
        return r, t

    resp, text = _do_call()
    empty_retries = 0
    while not text.strip() and empty_retries < 2:
        empty_retries += 1
        print(f"[debate] ⚠️ {cfg['model']} 返回空 text（端点间歇性行为），重试 {empty_retries}", file=sys.stderr)
        resp, text = _do_call()
    if not text.strip():
        raise RuntimeError(f"{cfg['model']} 重试 2 次仍返回空 text（stop={resp.stop_reason}）")
    usage = {
        "prompt": resp.usage.input_tokens,
        "completion": resp.usage.output_tokens,
        "total": resp.usage.input_tokens + resp.usage.output_tokens,
        "finish_reason": resp.stop_reason,
    }
    return text, usage


def _to_json(text: str) -> dict:
    """剥离 markdown 包裹 + 复用 _parse_json 全部容错策略；失败时落诊断（原文头尾）"""
    from stock_agent.analyze import _parse_json
    raw = (text or "").strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    raw = raw.strip()
    try:
        return _parse_json(raw)
    except Exception:
        print(f"[debate] ❌ JSON 解析失败，原文 {len(raw)} 字符", file=sys.stderr)
        print(f"[debate]    头部 300: {raw[:300]!r}", file=sys.stderr)
        print(f"[debate]    尾部 300: {raw[-300:]!r}", file=sys.stderr)
        raise


# ═══════════════════════════════════════════
# Prompt 定义（v3）
# ═══════════════════════════════════════════

# 阶段2：分歧点驳论（中立 + 证据原文 + 数据仲裁 + 允许修正）
REBUTTAL_PROMPT = """你是一位资深投资顾问（{label}），正在与另一位独立给出分析的顾问进行报告互审。当前第 {round}/{max_rounds} 轮。

你的报告结论（结论层）：
{own_analysis}

对方的报告结论（结论层）：
{other_analysis}

双方分歧点（程序比对识别）：
{divergence_list}

请针对分歧点逐一回应，并更新你的结论。强制行为约束：
1. 证据原文引用（核心纪律）：你的每条论据必须【直接引用数据报告原文】（原样摘录数据语句，不得转述、不得概括）；
   找不到数据支持的论点不准提，更不准编造数据——没有证据的驳论等于瞎扯；
2. 数据仲裁原则：每个分歧点上，能引用数据报告具体数据支持观点的一方占理；
   如果对方的证据确实更充分，你应当承认并修正自己的结论——修正不是认输，是向事实靠拢；
3. 修正格式：采纳对方观点时写明"采纳对方X点，依据数据【原文引用】，将我的评分从A修正为B / 判断修正为C"；
4. 评分-判断自洽：revised_score 必须与 revised_decision 匹配（≥60 看多 / ≤40 看空 / 41-59 震荡）。

输出严格纯 JSON：
{{
  "responses": [
    {{"divergence": "针对哪个分歧点", "my_evidence": "数据报告原文引用", "verdict": "坚持己见/采纳对方", "reason": "判断理由"}}
  ],
  "revised_score": 0-100的整数,
  "revised_decision": "看多/震荡/看空",
  "remaining_disagreements": ["仍保留的分歧（无则空数组）"]
}}
只输出纯 JSON。"""

# 阶段3：执笔者合并两份完整报告
WRITER_MERGE_TEMPLATE = """## 原始数据报告
{data}

## 顾问A 的完整投研报告
{report_a}

## 顾问B 的完整投研报告
{report_b}

## 双顾问辩论最终结论（合并报告必须立足此结论）
- 综合评分：{score}
- 综合判断：{decision}
- 结论形成方式：{merged_by}
- 信号归因（整合后）：{attribution}

## 辩论过程概要
{summary}

## 合并纪律（强制）
1. 逐模块合并两份报告的各自所长：每个模块取双方中分析更充分、数据更扎实的一方内容为主干；
2. **任何一方报告中独有的数据点（另一方未提及的具体数字/日期/事件）不得遗漏**，必须并入相应模块；
3. 最终结论（评分/判断/信号归因）已定，不得推翻；各模块分析须与最终结论自洽；
4. module_1 的 core_logic 每条直接用大白话行文（口语化、通俗自然），**禁止出现"大白话：""数据：""分析认为："这类标签式前缀**——三步思考链内化为表达，不拆成标签。

请基于以上最终结论、原始数据报告与两份顾问报告，按系统提示的 9 模块 schema 产出合并后的完整报告 JSON。
只输出纯 JSON。"""


# ═══════════════════════════════════════════
# 结论层提取 / 分歧识别 / 共识检测 / 整合
# ═══════════════════════════════════════════

def _extract_conclusion(report: dict) -> dict:
    """从完整 9 模块报告提取结论层（用于分歧识别与辩论）"""
    m1 = report.get("module_1_核心结论") or {}
    if not isinstance(m1, dict):
        m1 = {}
    m7 = report.get("module_7_催化舆情") or {}
    if not isinstance(m7, dict):
        m7 = {}
    m8 = report.get("module_8_风险ESG") or {}
    if not isinstance(m8, dict):
        m8 = {}
    return {
        "score": report.get("score"),
        "decision": report.get("decision"),
        "core_points": m1.get("core_logic") or [],
        "signal_attribution": report.get("signal_attribution") or [],
        "risks": m8.get("risks") or [],
        "catalysts": m7.get("positive") or [],
    }


def _signal_map(analysis: dict) -> dict:
    """signal_attribution 转 source→item 映射"""
    out = {}
    for item in analysis.get("signal_attribution") or []:
        if isinstance(item, dict) and item.get("source"):
            out[item["source"]] = item
    return out


def _identify_divergences(a: dict, b: dict) -> list:
    """程序化比对两份结论层，返回分歧点描述列表（空 = 无分歧）"""
    divs = []
    try:
        sa, sb = float(a.get("score", 50)), float(b.get("score", 50))
        if abs(sa - sb) > SCORE_CONSENSUS_TOLERANCE:
            divs.append(f"综合评分：A={a.get('score')} vs B={b.get('score')}（差 {abs(sa - sb):.0f} 分）")
    except (TypeError, ValueError):
        pass
    if a.get("decision") != b.get("decision"):
        divs.append(f"综合判断：A={a.get('decision')} vs B={b.get('decision')}")
    sa_a, sa_b = _signal_map(a), _signal_map(b)
    for src, item_a in sa_a.items():
        item_b = sa_b.get(src)
        if item_b and item_a.get("direction") != item_b.get("direction"):
            divs.append(f"{src}方向：A={item_a.get('direction')}（{item_a.get('note', '')}）"
                        f" vs B={item_b.get('direction')}（{item_b.get('note', '')}）")
    return divs


def _check_consensus(a: dict, b: dict) -> bool:
    """共识 = decision 一致 ∧ |score 差| ≤ 容差"""
    try:
        return (a.get("decision") == b.get("decision")
                and abs(float(a.get("score", 0)) - float(b.get("score", 0))) <= SCORE_CONSENSUS_TOLERANCE)
    except (TypeError, ValueError):
        return False


def _citation_hit_rate(conclusion: dict, data_md: str) -> float:
    """结论层论据的证据原文命中率：论据是否有 ≥8 字连续片段出现在数据报告中（观测指标）"""
    texts = []
    for cp in conclusion.get("core_points") or []:
        if isinstance(cp, dict):
            texts.append(str(cp.get("point", "")) + str(cp.get("evidence", "")))
        else:
            texts.append(str(cp))
    hits, total = 0, 0
    for t in texts:
        if len(t) < 8:
            continue
        total += 1
        if any(t[i:i + 8] in data_md for i in range(0, max(1, len(t) - 7), 4)):
            hits += 1
    return round(hits / total, 2) if total else -1  # -1 = 无可检查论据


def _dedup_items(items: list) -> list:
    """并集去重（哈希安全）：字符串直接去重，dict 元素按序列化形式去重。"""
    seen, out = set(), []
    for it in items:
        key = it if isinstance(it, str) else json.dumps(it, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def _rule_merge(a: dict, b: dict) -> dict:
    """规则整合兜底：score 五五平均，decision 按均值映射，signal 按维度均值并重归一"""
    score = round((float(a.get("score", 50)) + float(b.get("score", 50))) / 2)
    if score >= BULLISH_FLOOR:
        decision = "看多"
    elif score <= BEARISH_CEIL:
        decision = "看空"
    else:
        decision = "震荡"

    by_source: dict[str, list] = {}
    for sa in (a.get("signal_attribution") or []) + (b.get("signal_attribution") or []):
        if isinstance(sa, dict) and sa.get("source"):
            by_source.setdefault(sa["source"], []).append(sa)
    attribution = []
    for src, items in by_source.items():
        weight = sum(float(i.get("weight", 0)) for i in items) / len(items)
        bull = sum(1 for i in items if "多" in str(i.get("direction", "")))
        bear = sum(1 for i in items if "空" in str(i.get("direction", "")))
        direction = "偏多" if bull > bear else ("偏空" if bear > bull else "中性")
        attribution.append({"source": src, "weight": round(weight, 3), "direction": direction,
                            "note": "双顾问均值整合"})
    total_w = sum(x["weight"] for x in attribution) or 1.0
    for x in attribution:
        x["weight"] = round(x["weight"] / total_w, 2)

    def _points(analysis):
        return [cp.get("point", cp) if isinstance(cp, dict) else cp for cp in analysis.get("core_points") or []]

    return {
        "score": score,
        "decision": decision,
        "signal_attribution": attribution,
        "a_points": _points(a),
        "b_points": _points(b),
        "risks": _dedup_items((a.get("risks") or []) + (b.get("risks") or [])),
        "catalysts": _dedup_items((a.get("catalysts") or []) + (b.get("catalysts") or [])),
    }


# ═══════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════

def _accumulate(acc: dict, usage: dict) -> None:
    for k in ("prompt", "completion", "total"):
        acc[k] = acc.get(k, 0) + usage.get(k, 0)
    acc["calls"] = acc.get("calls", 0) + 1


def debate_analyze(markdown_report: str, stock_code: str = "", on_progress=None) -> tuple[dict, dict, dict]:
    """E4 生产入口（v3 双报告合并版）

    阶段1 双方各产出完整 9 模块报告（A=DeepSeek 生产链路 / B=千问同 prompt）
    阶段2 结论层比对 → 分差>5 或判断不一致才驳论（≤6 轮，共识即停）
    阶段3 执笔者合并两份完整报告（并集纪律）

    Args:
        markdown_report: SKILL 数据报告
        stock_code: 传入则自动载入 E1 历史记忆（奇数位历史骨架注入双方分析）
        on_progress: 进度回调 on_progress(stage, info)，阶段 = advisor_a/advisor_b/debate/merge

    Returns:
        (report, usage_by_model, stats)
        usage_by_model = {"model_a": {...}, "model_b": {...}}
    """
    from stock_agent.prompts import build_system_prompt
    from stock_agent.analyze import analyze

    def _progress(stage, info=None):
        if on_progress:
            on_progress(stage, info)

    t0 = time.time()
    cfg = _model_config()
    usage = {"model_a": {"prompt": 0, "completion": 0, "total": 0, "calls": 0},
             "model_b": {"prompt": 0, "completion": 0, "total": 0, "calls": 0}}
    stats = {"rounds": 0, "consensus": False, "consensus_round": None,
             "initial": {}, "final": {}, "issues": [], "citation_hit": {}, "round_traces": []}

    # 载入历史记忆（E1）：按 stock_code 自动取奇数位历史骨架，失败不阻塞
    history_context = ""
    if stock_code:
        try:
            from database import get_recent_reports
            from stock_agent.history import build_history_context
            history_context = build_history_context(get_recent_reports(stock_code))
        except Exception as e:
            print(f"[debate] ⚠️ 历史报告加载失败，按无历史继续: {e}", file=sys.stderr)

    system_prompt = build_system_prompt()
    data_block = f"## 数据报告\n{markdown_report}"
    if history_context:
        data_block += f"\n\n{history_context}"

    def call_a(system, user, max_tokens=8192):
        text, u = _call_llm(cfg["model_a"], system, user, max_tokens)
        _accumulate(usage["model_a"], u)
        return _to_json(text)

    def call_b(system, user, max_tokens=8192):
        text, u = _call_llm(cfg["model_b"], system, user, max_tokens)
        _accumulate(usage["model_b"], u)
        return _to_json(text)

    # ── 阶段 1：双方各产出完整报告 ──
    # 顾问A：复用生产 analyze 链路（容错 + validator，成熟稳定）
    _progress("advisor_a", "顾问A（DeepSeek）正在生成报告")
    report_a, u_a = analyze(markdown_report, history_context)
    _accumulate(usage["model_a"], u_a)
    # 顾问B：同一套三层 system prompt，千问端点
    _progress("advisor_b", "顾问B（千问）正在生成报告")
    report_b = call_b(system_prompt, data_block, max_tokens=16384)

    # ── 阶段 2：结论层比对 + 分歧点驳论 ──
    state_a = _extract_conclusion(report_a)
    state_b = _extract_conclusion(report_b)
    stats["initial"] = {"a_score": state_a.get("score"), "a_decision": state_a.get("decision"),
                        "b_score": state_b.get("score"), "b_decision": state_b.get("decision")}
    stats["citation_hit"] = {"a": _citation_hit_rate(state_a, markdown_report),
                             "b": _citation_hit_rate(state_b, markdown_report)}
    print(f"[debate] 双方报告结论: A {state_a.get('score')}/{state_a.get('decision')} vs "
          f"B {state_b.get('score')}/{state_b.get('decision')} "
          f"(命中率 A={stats['citation_hit']['a']} B={stats['citation_hit']['b']})", file=sys.stderr)

    if _check_consensus(state_a, state_b):
        stats["consensus"] = True
        stats["consensus_round"] = 0
        print("[debate] ✅ 双方报告结论直接一致，无需驳论", file=sys.stderr)
    else:
        for round_no in range(1, MAX_DEBATE_ROUNDS + 1):
            _progress("debate", f"第 {round_no} 轮分歧点驳论")
            divs = _identify_divergences(state_a, state_b)
            if not divs:
                stats["consensus"] = True
                stats["consensus_round"] = round_no
                print(f"[debate] ✅ 第{round_no}轮无分歧，达成共识", file=sys.stderr)
                break
            stats["rounds"] = round_no
            div_text = "\n".join(f"- {d}" for d in divs)

            rb_a = call_a(REBUTTAL_PROMPT.format(
                label=cfg["model_a"]["label"], round=round_no, max_rounds=MAX_DEBATE_ROUNDS,
                own_analysis=json.dumps(state_a, ensure_ascii=False),
                other_analysis=json.dumps(state_b, ensure_ascii=False),
                divergence_list=div_text), data_block)
            if "revised_score" in rb_a:
                state_a["score"] = rb_a["revised_score"]
            if "revised_decision" in rb_a:
                state_a["decision"] = rb_a["revised_decision"]

            rb_b = call_b(REBUTTAL_PROMPT.format(
                label=cfg["model_b"]["label"], round=round_no, max_rounds=MAX_DEBATE_ROUNDS,
                own_analysis=json.dumps(state_b, ensure_ascii=False),
                other_analysis=json.dumps(state_a, ensure_ascii=False),
                divergence_list=div_text), data_block)
            if "revised_score" in rb_b:
                state_b["score"] = rb_b["revised_score"]
            if "revised_decision" in rb_b:
                state_b["decision"] = rb_b["revised_decision"]

            stats["round_traces"].append({
                "round": round_no,
                "a": {"score": state_a.get("score"), "decision": state_a.get("decision"),
                      "responses": rb_a.get("responses", [])},
                "b": {"score": state_b.get("score"), "decision": state_b.get("decision"),
                      "responses": rb_b.get("responses", [])},
            })
            print(f"[debate] 第{round_no}轮: A {state_a.get('score')}/{state_a.get('decision')} vs "
                  f"B {state_b.get('score')}/{state_b.get('decision')}", file=sys.stderr)

            if _check_consensus(state_a, state_b):
                stats["consensus"] = True
                stats["consensus_round"] = round_no
                print(f"[debate] ✅ 第{round_no}轮达成共识", file=sys.stderr)
                break

    # ── 阶段 3：执笔者合并两份完整报告 ──
    final = _rule_merge(state_a, state_b)
    stats["final"] = {"score": final["score"], "decision": final["decision"],
                      "merged_by": "consensus" if stats["consensus"] else "rule_merge"}
    if stats["consensus"]:
        merged_by_desc = ("双方报告结论直接一致（无需辩论），合并报告取双方报告之并集"
                          if stats["consensus_round"] == 0
                          else f"第{stats['consensus_round']}轮达成共识")
    else:
        merged_by_desc = f"{MAX_DEBATE_ROUNDS}轮未达成共识，规则整合兜底（双模型存在持续分歧，结论仅供参考）"
    summary = (f"双顾问独立报告：A {stats['initial']['a_score']}/{stats['initial']['a_decision']}，"
               f"B {stats['initial']['b_score']}/{stats['initial']['b_decision']}；"
               f"驳论 {stats['rounds']} 轮，{merged_by_desc}。")

    _progress("merge", "正在合并两份报告")
    report = call_a(system_prompt, WRITER_MERGE_TEMPLATE.format(
        data=markdown_report,
        report_a=json.dumps(report_a, ensure_ascii=False),
        report_b=json.dumps(report_b, ensure_ascii=False),
        score=final["score"], decision=final["decision"],
        merged_by=merged_by_desc,
        attribution=json.dumps(final["signal_attribution"], ensure_ascii=False),
        summary=summary), max_tokens=16384)

    stats["issues"] = validate_report(report)
    stats["elapsed"] = round(time.time() - t0, 1)
    print(f"[debate] 完成: 最终 {final['score']}/{final['decision']}, 违规 {len(stats['issues'])}, "
          f"耗时 {stats['elapsed']}s, 调用 A×{usage['model_a']['calls']} B×{usage['model_b']['calls']}",
          file=sys.stderr)
    return report, usage, stats


def debate_with_fallback(markdown_report: str, stock_code: str = "", on_progress=None) -> tuple[dict, dict, dict | None]:
    """生产统一入口：优先双模型辩论，失败静默降级标准分析（不打扰用户）

    Returns:
        (report, usage, stats)
        stats = None 表示已降级为标准分析（前端"双模型深度分析"角标据此不显示）
    """
    from stock_agent.analyze import analyze

    try:
        return debate_analyze(markdown_report, stock_code=stock_code, on_progress=on_progress)
    except Exception as e:
        print(f"[debate] ⚠️ 辩论链路失败，静默降级标准分析: {e}", file=sys.stderr)
        # 降级后仍保留 E1 历史记忆（标准分析也要有历史对比）
        history_context = ""
        if stock_code:
            try:
                from database import get_recent_reports
                from stock_agent.history import build_history_context
                history_context = build_history_context(get_recent_reports(stock_code))
            except Exception:
                pass
        report, usage = analyze(markdown_report, history_context)
        return report, usage, None
