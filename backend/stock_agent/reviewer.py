"""E2 实验原型：Reflection 质量评审员（不接入生产管线，仅供 e2 实验调用）

借鉴 Reflection 范式的 生成 → 批判 → 重写 闭环：
  1. analyze() 生成初始报告
  2. 评审员批判：输入 = 数据报告 + 报告 JSON + 评审清单，输出 = JSON 裁决
  3. 有问题 → 携带问题清单重写（最多 MAX_REVIEW_ROUNDS 轮，"pass" 即早停）

与 validator（E0）的分工：validator 抓结构性硬错误（零 LLM 成本），
reviewer 抓语义质量问题（分析浅 / 术语堆砌 / 事实推断不分）——两者互补。
"""
import json
import os
import sys

from openai import OpenAI

MAX_REVIEW_ROUNDS = 2  # 批判-重写最多循环轮数

# 评审员 system prompt：只关心"格式对但质量差"的语义问题（硬规则由 validator 负责）
REVIEW_SYSTEM_PROMPT = """你是一个严苛的投研报告评审员。用户会给你原始数据报告和分析师产出的 JSON。
请对照以下清单批判，只关心"格式正确但质量差"的问题：

1. 罗列数据不给解读（只堆数字，不讲逻辑联系和深层解读）
2. 术语堆砌（使用"戴维斯双击"等深奥术语却没有括号白话解释）
3. 事实与推断不分（"数据显示"与"分析认为"的语气混用）
4. 财务分析单薄（module_3 未覆盖盈利能力/成长趋势/偿债安全/现金流质量四个维度）
5. 结论缺少数据支撑（凭空判断，或结论方向与数据明显矛盾）
6. 官腔空话（不说散户听得懂的大白话，缺少生活化判断）

输出严格 JSON（不要输出任何其他文字、不要 markdown 包裹）：
{"verdict": "pass", "problems": []}  或  {"verdict": "issues", "problems": ["问题1（指明模块与症状）", ...]}

评审纪律：报告质量过得去就判 pass，不要吹毛求疵；problems 最多 5 条，按严重度排序。"""

# 重写员 system prompt
REWRITE_SYSTEM_PROMPT = """你是投研报告重写专家。用户会给你原始数据报告、待重写报告 JSON 和评审员的问题清单。
请输出重写后的完整 JSON：逐条修正问题，保持原 schema 结构不变，未出问题的部分不要改动，
继续遵循「数据事实化 → 逻辑推演化 → 散民口语化」三步思考链，只输出纯 JSON。"""


def _call_llm(system: str, user: str, max_tokens: int = 16384) -> tuple[str, dict]:
    """共用 LLM 调用（与 analyze 主调用同参数），返回 (content_text, usage)"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        extra_body={"thinking": {"type": "enabled"}},
        reasoning_effort="high",
        max_tokens=max_tokens,
    )
    content = resp.choices[0].message.content or ""
    reasoning = getattr(resp.choices[0].message, "reasoning_content", None)
    # reasoner 可能把输出全放进 reasoning_content
    if not content.strip() and reasoning:
        content = reasoning
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }
    return content, usage


def _strip_and_parse(text: str) -> dict:
    """剥离 ```json 包裹后解析 JSON（复用 analyze 的容错解析）"""
    from stock_agent.analyze import _parse_json

    raw = text.strip()
    if "```json" in raw:
        raw = raw.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw:
        raw = raw.split("```", 1)[1].split("```", 1)[0]
    return _parse_json(raw.strip())


def review_report(markdown_report: str, report: dict) -> tuple[list | None, dict]:
    """评审报告，返回 (问题清单, usage)；问题清单为 None 表示评审通过"""
    content, usage = _call_llm(
        REVIEW_SYSTEM_PROMPT,
        f"## 原始数据报告\n{markdown_report}\n\n## 分析师产出 JSON\n{json.dumps(report, ensure_ascii=False)}",
        max_tokens=4096,  # 评审输出较短
    )
    try:
        verdict = _strip_and_parse(content)
    except Exception as e:
        print(f"[reviewer] ⚠️ 评审结果解析失败，按通过处理: {e}", file=sys.stderr)
        return None, usage
    if verdict.get("verdict") == "issues":
        problems = verdict.get("problems") or []
        return (problems if problems else None), usage
    return None, usage


def reflect_analyze(markdown_report: str) -> tuple[dict, dict, dict]:
    """E2 实验入口：analyze + 评审-重写闭环

    Returns:
        (report, usage, stats)
        stats = {rounds: 批判轮数, early_stopped: 是否早停, rewrites: 重写次数,
                 all_problems: [[每轮问题清单]...]}
    """
    from stock_agent.analyze import analyze

    report, usage = analyze(markdown_report)
    stats = {"rounds": 0, "early_stopped": False, "rewrites": 0, "all_problems": []}

    for round_no in range(1, MAX_REVIEW_ROUNDS + 1):
        stats["rounds"] = round_no
        problems, review_usage = review_report(markdown_report, report)
        usage = {k: usage.get(k, 0) + review_usage.get(k, 0) for k in ("prompt", "completion", "total")}

        if problems is None:
            stats["early_stopped"] = True
            print(f"[reviewer] 第 {round_no} 轮评审: 通过（早停）", file=sys.stderr)
            break

        stats["all_problems"].append(problems)
        print(f"[reviewer] 第 {round_no} 轮评审: {len(problems)} 个问题 → 重写", file=sys.stderr)
        try:
            content, rewrite_usage = _call_llm(
                REWRITE_SYSTEM_PROMPT,
                f"## 原始数据报告\n{markdown_report}\n\n"
                f"## 待重写报告 JSON\n{json.dumps(report, ensure_ascii=False)}\n\n"
                f"## 评审员问题清单\n" + "\n".join(f"- {p}" for p in problems),
            )
            usage = {k: usage.get(k, 0) + rewrite_usage.get(k, 0) for k in ("prompt", "completion", "total")}
            report = _strip_and_parse(content)
            stats["rewrites"] += 1
        except Exception as e:
            print(f"[reviewer] ⚠️ 重写失败，保留当前版本: {e}", file=sys.stderr)
            break

    return report, usage, stats
