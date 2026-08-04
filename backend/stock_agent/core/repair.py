"""报告违规定点修正 — 校验失败后回传 LLM 修复"""
import json
import os

from openai import OpenAI

from .parser import _parse_json


def _add_usage(a: dict, b: dict) -> dict:
    """两份 usage 成本字典逐项累加（保持 prompt/completion/total 可观测）"""
    return {k: a.get(k, 0) + b.get(k, 0) for k in ("prompt", "completion", "total")}


def _repair_report(report: dict, issues: list[str], history_context: str = "") -> tuple[dict, dict]:
    """将违规清单回传 LLM，要求其输出修正后的完整 JSON，返回 (report, usage)

    修正 prompt 只要求修复违规处、禁止改动合规字段；解析失败时向上抛异常，
    由 analyze_with_validation 兜底保留原报告。

    Args:
        history_context: 历史报告骨架上下文（E1），非空时注入修正 prompt，
                         防止修正 LLM 无真实历史日期可查时编造 YYYY-MM-DD
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    issues_text = "\n".join(f"- {issue}" for issue in issues)

    resp = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": (
                "你是 JSON 修正助手。用户会给你一份股票投研报告 JSON 和它违反的规则清单。"
                "请输出修正后的完整 JSON：只修复违反规则的部分，不要改动合规字段，"
                "不要输出任何解释文字或 markdown 包裹，只输出纯 JSON。"
            )},
            {"role": "user", "content": (
                f"违反的规则清单：\n{issues_text}\n\n"
                f"原始报告 JSON：\n{json.dumps(report, ensure_ascii=False)}"
                + (f"\n\n【历史对比上下文】\n{history_context}\n\n"
                   f"修正涉及 module_9 的 history_anchor / history_changes / changed_aspects / history_compared 字段时，"
                   f"必须严格依据上方历史上下文中已有的日期与变化信息填写，不得编造任何 YYYY-MM-DD 日期或虚构变化内容。"
                   if history_context else "")
            )},
        ],
        extra_body={"thinking": {"type": "enabled"}},
        reasoning_effort="high",
        max_tokens=16384,
    )

    content = resp.choices[0].message.content
    reasoning_content = getattr(resp.choices[0].message, 'reasoning_content', None)
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }

    # 与主调用相同的剥离逻辑：```json 包裹 / content 为空时兜底 reasoning_content
    raw_text = content or ""
    if not raw_text.strip() and reasoning_content:
        raw_text = reasoning_content
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1].split("```", 1)[0]
    raw_text = raw_text.strip()
    if not raw_text:
        raise RuntimeError("修正调用返回空内容")

    return _parse_json(raw_text), usage
