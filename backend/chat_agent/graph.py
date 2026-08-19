"""投研 AI 问答 —— LangGraph 工作流

节点：
  understand → LLM 意图理解（输出 JSON：is_off_topic / stock_code / needs_tools）
  tool_loop  → Function Calling 循环（最多 MAX_TOOL_ROUNDS 轮）
  answer     → 基于工具结果 + 报告 + 历史生成最终回答
"""
import json
import os
from datetime import datetime
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import StreamWriter
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID
from .tools import get_tool_descriptions, execute_tool_call, TOOL_FRIENDLY_NAMES

MAX_TOOL_ROUNDS = 4


class QaState(TypedDict):
    """LangGraph 工作流状态"""
    # 输入（build_initial_state 一次注入）
    question: str
    stock_code: str          # 会话绑定股票（报告锚点，始终保持）
    stock_name: str
    report_context: str
    history: list[dict]      # 最近 8 轮 [{role, content}]
    tool_hints: list[str]    # understand 失败兜底方向
    # understand 产出
    is_off_topic: bool
    needs_tools: bool
    target_code: str         # 跨股票提问时 ≠ stock_code
    # tool 循环维护
    messages: list[dict]     # OpenAI 格式对话（首条为纯问题，含工具结果回填）
    tool_results: str        # 拼接的工具文本（喂 answer）
    tool_calls: list[dict]   # records [{name, label, ok, duration_ms, arguments}]
    rounds: int              # 已执行工具轮数（替换 for 循环计数器）
    # answer 产出
    answer_text: str


def build_initial_state(question, stock_code, stock_name, report_context,
                        tool_hints, history=None) -> dict:
    """构建初始 state（messages 仅含纯问题；目标股票上下文由 llm_round 首轮注入）"""
    return {
        "question": question,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "report_context": report_context,
        "history": history or [],
        "tool_hints": tool_hints,
        "is_off_topic": False,
        "needs_tools": False,
        "target_code": stock_code,
        "messages": [{"role": "user", "content": question}],
        "tool_results": "",
        "tool_calls": [],
        "rounds": 0,
        "answer_text": "",
    }


_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        # OpenAI SDK 需要 OpenAI 兼容端点；若配置指向 anthropic 端点则归一化为 /v1
        base_url = LLM_BASE_URL.replace("/anthropic", "/v1")
        _client = OpenAI(api_key=LLM_API_KEY, base_url=base_url)
    return _client


def _format_history(history: list[dict] | None) -> str:
    """把历史消息列表转成 prompt 文本（越早的在前）"""
    if not history:
        return "（无历史对话）"
    lines = []
    for msg in history:
        role = msg.get("role", "")
        content = (msg.get("content") or "").strip()
        label = "用户" if role == "user" else "助手"
        lines.append(f"{label}：{content}")
    return "\n".join(lines)


def understand_node(state: QaState, writer: StreamWriter) -> dict:
    """意图理解节点：发 phase understand 事件，产出意图分析结果"""
    from .prompts import UNDERSTAND_PROMPT

    writer({"type": "phase", "phase": "understand"})
    now = datetime.now()
    prompt = UNDERSTAND_PROMPT.format(
        question=state["question"], stock_code=state["stock_code"],
        stock_name=state["stock_name"], today_str=now.strftime("%Y-%m-%d"),
    )
    try:
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL_ID, max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"thinking": {"type": "disabled"}},  # 意图分析求快
        )
        text = resp.choices[0].message.content or ""
        # 剥离 ```json 包裹（先处理 ```json 再处理 ```，避免 json 前缀残留）
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(text.strip())
        return {
            "is_off_topic": bool(data.get("is_off_topic", False)),
            "needs_tools": bool(data.get("needs_tools", False)),
            "target_code": data.get("stock_code") or state["stock_code"],
            "tool_hints": data.get("tool_hints", []),
        }
    except Exception as e:
        print(f"[chat_agent] [警告] 意图理解失败，默认按股票相关处理: {e}")
        return {
            "is_off_topic": False,
            "needs_tools": False,
            "target_code": state["stock_code"],
            "tool_hints": [],
        }


def llm_round_node(state: QaState) -> dict:
    """单轮 Function Calling：调用 LLM，产出本轮 tool_calls 或收尾消息

    首轮（rounds == 0）把 messages[0] 替换为目标股票上下文（含证券实体名，
    2026-08-19 根因修复）；target_code 由 understand 产出，跨股票提问时 ≠ stock_code。
    """
    tools = _build_tools_for(state["tool_hints"])
    messages = list(state["messages"])
    if state["rounds"] == 0:
        messages = [{
            "role": "user",
            "content": (f"当前对话股票目标：{state['target_code']}"
                        f"（{state['stock_name']}）。问题：{state['question']}"),
        }] + messages[1:]
    try:
        resp = _get_client().chat.completions.create(
            model=LLM_MODEL_ID, messages=messages, tools=tools,
            max_tokens=2048,
            extra_body={"thinking": {"type": "enabled"}},
            temperature=1.0,
        )
        msg = resp.choices[0].message
        tool_calls = msg.tool_calls or []
        if not tool_calls:
            # 收尾：无工具调用
            return {"messages": messages + [{"role": "assistant", "content": msg.content or ""}]}
        # 干净 assistant 消息：只保留 OpenAI 兼容字段，剔除 reasoning_content
        return {"messages": messages + [{
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id, "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        }]}
    except Exception as e:
        # LLM 调用失败：本轮无工具，避免死循环，走 answer
        print(f"[chat_agent] [警告] 工具循环 LLM 调用失败: {e}")
        return {"messages": messages + [{"role": "assistant", "content": ""}]}


def execute_tools_node(state: QaState, writer: StreamWriter) -> dict:
    """执行本轮全部工具调用：发 tool_start/tool_done，累积 records 与 tool_results"""
    import time as _t

    last = state["messages"][-1]
    calls = last.get("tool_calls") or []
    messages = list(state["messages"])
    records = list(state["tool_calls"])
    results_parts = []

    for tc in calls:
        name = tc["function"]["name"]
        label = TOOL_FRIENDLY_NAMES.get(name, name)
        writer({"type": "tool_start", "name": name, "label": label})
        try:
            args = json.loads(tc["function"]["arguments"])
        except Exception:
            args = {}
        # 边界守卫：LLM 返回的 arguments 可能是不可信的非 dict，统一包成 {"query": ...}
        if not isinstance(args, dict):
            args = {"query": str(args)}
        t0 = _t.time()
        out = execute_tool_call(name, args)
        dt = int((_t.time() - t0) * 1000)
        writer({"type": "tool_done", "name": name, "label": label, "ok": out["ok"]})
        records.append({
            "name": name, "label": label, "ok": out["ok"],
            "duration_ms": dt, "arguments": args,
        })
        results_parts.append(out["text"])
        messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out["text"]})

    return {
        "messages": messages,
        "tool_results": (state["tool_results"] + "\n\n".join(results_parts)
                         if results_parts else state["tool_results"]),
        "tool_calls": records,
        "rounds": state["rounds"] + 1,
    }


def answer_node(state: QaState, writer: StreamWriter) -> dict:
    """生成最终回答：off_topic 拒绝（不发 phase）；否则发 phase answer 事件 + 正文"""
    from .prompts import ANSWER_PROMPT, REPORT_ONLY_PROMPT, DISCLAIMER

    if state["is_off_topic"]:
        return {"answer_text": "karens暂时无法回答您这个问题哦？"}

    writer({"type": "phase", "phase": "answer"})

    history_text = _format_history(state["history"])
    # 跨股票提问时标注目标股票，让 LLM 把工具数据归属到目标股票；同股则留空
    target_line = (f"目标股票：{state['target_code']}"
                   if state["target_code"] != state["stock_code"] else "")
    tool_results = state["tool_results"].strip()

    if tool_results:
        prompt = ANSWER_PROMPT.format(
            question=state["question"], stock_code=state["stock_code"],
            stock_name=state["stock_name"], target_line=target_line,
            report_context=state["report_context"], tool_results=tool_results,
            history=history_text,
        )
    else:
        prompt = REPORT_ONLY_PROMPT.format(
            question=state["question"], stock_code=state["stock_code"],
            stock_name=state["stock_name"], target_line=target_line,
            report_context=state["report_context"], history=history_text,
        )

    resp = _get_client().chat.completions.create(
        model=LLM_MODEL_ID, messages=[{"role": "user", "content": prompt}],
        # max_tokens 放大（2026-08-19）：工具结果可达 1.3 万字符，4096 偶发耗尽
        max_tokens=16000,
        extra_body={"thinking": {"type": "enabled"}},
        temperature=1.0,
    )
    answer = resp.choices[0].message.content or ""
    # 兜底（2026-08-19）：思考完成但正文为空时给友好提示而非只拼免责声明
    if not answer.strip():
        answer = "抱歉，我未能获取到足够的实时数据来完成这次分析，请换个问法或稍后再试。"
    return {"answer_text": answer + DISCLAIMER}


def decide_after_understand(state: QaState) -> str:
    """understand 后：off_topic 或不需要工具 → answer；否则 → llm_round"""
    if state["is_off_topic"] or not state["needs_tools"]:
        return "answer"
    return "llm_round"


def decide_after_llm(state: QaState) -> str:
    """llm_round 后：本轮有工具调用 且 未达轮次上限 → execute_tools；否则 → answer"""
    last = state["messages"][-1]
    has_calls = bool(last.get("tool_calls")) and state["rounds"] < MAX_TOOL_ROUNDS
    return "execute_tools" if has_calls else "answer"


def create_qa_workflow():
    """构建并编译 QA 工作流（4 节点 + 2 条件边）"""
    wf = StateGraph(QaState)
    wf.add_node("understand", understand_node)
    wf.add_node("llm_round", llm_round_node)
    wf.add_node("execute_tools", execute_tools_node)
    wf.add_node("answer", answer_node)
    wf.add_edge(START, "understand")
    wf.add_conditional_edges("understand", decide_after_understand)
    wf.add_conditional_edges("llm_round", decide_after_llm)
    wf.add_edge("execute_tools", "llm_round")
    wf.add_edge("answer", END)
    return wf.compile()


_compiled_workflow = None


def qa_workflow():
    """获取编译后的工作流（单例缓存，避免每次调用重建）"""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = create_qa_workflow()
    return _compiled_workflow


def run_qa_agent(question: str, stock_code: str, stock_name: str,
                 report_context: str, tool_hints: list[str],
                 history: list[dict] | None = None) -> dict:
    """同步执行完整问答（LangGraph 薄封装）

    流式路径由 routers/chat.py 直接调用 qa_workflow().astream()；
    本函数供同步调用/测试/诊断，返回结构保持兼容。

    Returns:
        {
            "answer": str,
            "is_off_topic": bool,
            "tool_calls": list[dict],   # [{name, label, ok, duration_ms, arguments}]
            "success": bool,
            "error": str,
        }
    """
    try:
        initial = build_initial_state(question, stock_code, stock_name,
                                      report_context, tool_hints, history)
        result = qa_workflow().invoke(initial)
        return {
            "answer": result["answer_text"],
            "is_off_topic": result["is_off_topic"],
            "tool_calls": result["tool_calls"],
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

    默认拉 stock + news 两个服务的全部工具描述；
    港股相关 hint 追加 global_stock；指数/板块 hint 追加 index；基金 hint 追加 fund。
    """
    servers = ["stock", "news"]
    if any("港股" in h or "global" in str(h) for h in tool_hints):
        servers.append("global_stock")
    if any(("指数" in h or "板块" in h or "index" in str(h)) for h in tool_hints):
        servers.append("index")
    if any(("基金" in h or "fund" in str(h)) for h in tool_hints):
        servers.append("fund")
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
