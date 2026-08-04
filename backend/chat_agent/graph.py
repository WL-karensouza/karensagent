"""投研 AI 问答 —— LangGraph 工作流

节点：
  understand → LLM 意图理解（输出 JSON：is_off_topic / stock_code / needs_tools）
  tool_loop  → Function Calling 循环（最多 MAX_TOOL_ROUNDS 轮）
  answer     → 基于工具结果 + 报告 + 历史生成最终回答
"""
import json
import os
from datetime import datetime
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
from .tools import get_tool_descriptions, execute_tool_call, TOOL_FRIENDLY_NAMES

MAX_TOOL_ROUNDS = 4

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # OpenAI SDK 需要 OpenAI 兼容端点；若配置指向 anthropic 端点则归一化为 /v1
        base_url = LLM_BASE_URL.replace("/anthropic", "/v1")
        _client = OpenAI(api_key=LLM_API_KEY, base_url=base_url)
    return _client


def _understand(question: str, stock_code: str, stock_name: str) -> dict:
    """意图理解：返回 {is_off_topic, stock_code, needs_tools, tool_hints}"""
    from .prompts import UNDERSTAND_PROMPT

    now = datetime.now()
    prompt = UNDERSTAND_PROMPT.format(
        question=question, stock_code=stock_code, stock_name=stock_name,
        today_str=now.strftime("%Y-%m-%d"),
    )
    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_ID,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"thinking": {"type": "disabled"}},  # 意图分析求快
        )
        text = resp.choices[0].message.content or ""
        # 剥离 ```json 包裹（先处理 ```json 再处理 ```，避免 json 前缀残留导致 loads 失败）
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(text.strip())
        return {
            "is_off_topic": bool(data.get("is_off_topic", False)),
            "stock_code": data.get("stock_code") or stock_code,
            "needs_tools": bool(data.get("needs_tools", False)),
            "tool_hints": data.get("tool_hints", []),
        }
    except Exception as e:
        print(f"[chat_agent] [警告] 意图理解失败，默认按股票相关处理: {e}")
        return {
            "is_off_topic": False,
            "stock_code": stock_code,
            "needs_tools": False,
            "tool_hints": [],
        }


def _tool_loop(question: str, tool_hints: list[str]) -> tuple[list, list]:
    """Function Calling 循环，返回 (tool_results_text, tool_calls_records)

    tool_calls_records: [{name, label, ok, duration_ms}] —— 供前端步骤卡片
    """
    tools = _build_tools_for(tool_hints)
    messages = [{"role": "user", "content": question}]
    results = []
    records = []

    for _ in range(MAX_TOOL_ROUNDS):
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL_ID,
            messages=messages,
            tools=tools,
            max_tokens=2048,
            extra_body={"thinking": {"type": "enabled"}},
            temperature=1.0,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []
        if not tool_calls:
            break
        # 不直接回填原始 msg 对象：思考模式下其 reasoning_content 会一并回传浪费 token（个别版本可能 400），
        # 构造干净 dict 只保留 OpenAI 兼容的 role/content/tool_calls 字段
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
            # 边界守卫：LLM 返回的 arguments 可能是不可信的非 dict（如数组/字符串），
            # 统一包成 {"query": ...} 再交给 execute_tool_call，避免 dict(arguments) 抛异常破坏工具循环
            if not isinstance(args, dict):
                args = {"query": str(args)}
            import time as _t
            t0 = _t.time()
            out = execute_tool_call(tc.function.name, args)
            dt = int((_t.time() - t0) * 1000)
            records.append({
                "name": tc.function.name,
                "label": TOOL_FRIENDLY_NAMES.get(tc.function.name, tc.function.name),
                "ok": out["ok"],
                "duration_ms": dt,
            })
            results.append(out["text"])
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": out["text"],
            })
        # 工具失败或已收集足够数据，LLM 会自行停止请求工具
    return "\n\n".join(results), records


def _answer(question: str, stock_code: str, stock_name: str,
            report_context: str, tool_results: str, is_off_topic: bool) -> str:
    """生成最终回答（工具结果 / 报告 / 历史）"""
    from .prompts import ANSWER_PROMPT, REPORT_ONLY_PROMPT, DISCLAIMER

    if is_off_topic:
        return "karens暂时无法回答您这个问题哦？"

    if tool_results.strip():
        prompt = ANSWER_PROMPT.format(
            question=question, stock_code=stock_code, stock_name=stock_name,
            report_context=report_context, tool_results=tool_results,
        )
    else:
        prompt = REPORT_ONLY_PROMPT.format(
            question=question, stock_code=stock_code, stock_name=stock_name,
            report_context=report_context,
        )

    resp = _get_client().chat.completions.create(
        model=LLM_MODEL_ID,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        extra_body={"thinking": {"type": "enabled"}},
        temperature=1.0,
    )
    answer = resp.choices[0].message.content or ""
    return answer + DISCLAIMER


def run_qa_agent(question: str, stock_code: str, stock_name: str,
                 report_context: str, tool_hints: list[str]) -> dict:
    """总入口：understand → tool_loop → answer

    Returns:
        {
            "answer": str,
            "is_off_topic": bool,
            "tool_calls": list[dict],   # [{name, label, ok, duration_ms}]
            "success": bool,
            "error": str,
        }
    """
    try:
        und = _understand(question, stock_code, stock_name)
        is_off_topic = und["is_off_topic"]
        needs_tools = und["needs_tools"] and not is_off_topic

        tool_results, records = "", []
        if needs_tools:
            hints = und["tool_hints"] or tool_hints
            tool_results, records = _tool_loop(question, hints)

        answer = _answer(question, stock_code, stock_name,
                         report_context, tool_results, is_off_topic)
        return {
            "answer": answer,
            "is_off_topic": is_off_topic,
            "tool_calls": records,
            "success": True,
            "error": "",
        }
    except Exception as e:
        print(f"[chat_agent] [错误] run_qa_agent 失败: {e}")
        return {
            "answer": f"karens 暂时遇到问题，请稍后重试。（{type(e).__name__}）",
            "is_off_topic": False,
            "tool_calls": [],
            "success": False,
            "error": str(e),
        }


def _build_tools_for(tool_hints: list[str]) -> list[dict]:
    """按 tool_hints 选择工具服务，构建 Function Calling tools 参数

    简化：默认拉 stock + news 两个服务的全部工具描述；
    港股相关 hint 追加 global_stock。
    """
    servers = ["stock", "news"]
    if any("港股" in h or "global" in str(h) for h in tool_hints):
        servers.append("global_stock")
    tools = []
    for server in servers:
        for t in get_tool_descriptions(server):
            schema = t.get("inputSchema") or {}
            tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": schema,
                },
            })
    return [t for t in tools if t["function"]["name"]]
