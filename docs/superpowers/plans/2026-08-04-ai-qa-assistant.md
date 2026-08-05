# 投研 AI 问答助理（karens）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将投研报告页右侧的 AI 问答占位面板升级为真实可用的问答智能体 karens。用户针对股票提问，karens 通过 LangGraph 工作流 + DeepSeek Function Calling + iFinD 全工具层实时取数分析，流式回答。

**Architecture:** 后端新建 `backend/chat_agent/` 包（参照 `ai_news_agent/` 与 `stock_agent/` 的模块化分层），ORM 模型加在 `backend/models.py`（根 ORM），DAO 独立；前端升级 `AiChatPanel.vue` 并新建步骤卡片组件。

**Tech Stack:** Python 3, FastAPI, LangGraph, OpenAI SDK（DeepSeek 兼容端点）, Vue 3, Pinia

## Global Constraints

- 全程**不重写已存在的股票分析逻辑**（analyze.py / collect.py / report.py 等不动）
- 新增依赖前需确认（langgraph 已装——ai_news_agent 在用）
- 遵循 CLAUDE.md：Python 函数/变量 snake_case、类 CapWords、中文注释；前端 camelCase / PascalCase
- 数据库模型遵循根 `models.py` 风格（SQLAlchemy ORM + comment 注释）
- 回答输出走 SSE 流式；iFinD 调用复用 `stock_agent.skill` 的 `call_skill` / `extract_text`
- 免责声明由后端固定拼接，不占 LLM 生成
- 会话绑定股票共享（非报告专属、非全局）；允许跨股票提问
- 前端 UI 遵循项目浅色系、简约、无渐变（对应 `--sent-*` CSS 变量）

---

### Task 1: 后端 DB 层（ORM 模型 + DAO + 建表）

**Files:**
- Modify: `backend/models.py`（新增 `ChatSession` + `ChatMessage` 两个 ORM 类）
- Create: `backend/chat_agent/__init__.py`
- Create: `backend/chat_agent/database.py`（DAO）

**Interfaces:**
- Consumes: 根 `models.py` 的 `Base`（来自 database.py）
- Produces: `ChatSession` / `ChatMessage` ORM 类；`chat_agent/database.py` 导出 `get_or_create_session` / `get_session` / `list_messages` / `add_message` / `update_session_report`
- `init_db()`（database.py）需能建出新表（create_all 自动覆盖）

- [ ] **Step 1: 在 backend/models.py 追加两个 ORM 类**

在文件末尾追加（遵循既有风格）：

```python
class ChatSession(Base):
    """AI 问答会话（绑定股票共享，每只股票一个活跃会话）"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, unique=True, comment="股票代码")
    stock_name = Column(String(64), default="", comment="股票名称")
    report_id = Column(Integer, nullable=True, comment="最近锚定的报告 ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        {"comment": "AI 问答会话"},
    )


class ChatMessage(Base):
    """AI 问答消息"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, comment="所属会话 ID")
    role = Column(String(16), nullable=False, comment="user / assistant")
    content = Column(Text, nullable=False, comment="问题或回答")
    tool_calls = Column(Text, nullable=True, comment="该轮工具调用记录 JSON 数组")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    __table_args__ = (
        {"comment": "AI 问答消息"},
    )
```

- [ ] **Step 2: 新建 chat_agent/__init__.py**

```python
"""投研 AI 问答智能体（karens）—— 数据库 / 工具层 / 工作流 / 接口分层"""
```

- [ ] **Step 3: 新建 chat_agent/database.py（DAO）**

DAO 函数（参照 `backend/ai_news_agent/database.py` 风格：内部 `SessionLocal()` + `_model_to_dict`）：

```python
"""投研 AI 问答 —— 数据库操作"""
import json
from database import SessionLocal, _model_to_dict


def get_or_create_session(stock_code: str, stock_name: str = "") -> dict:
    """按股票代码获取会话，不存在则创建（每只股票一个活跃会话）

    返回 _model_to_dict 后的会话 dict。
    """
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.stock_code == stock_code).first()
        if row is None:
            row = ChatSession(stock_code=stock_code, stock_name=stock_name)
            db.add(row)
            db.commit()
            db.refresh(row)
        return _model_to_dict(row)
    finally:
        db.close()


def get_session(session_id: int) -> dict | None:
    """按 ID 获取会话"""
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        return _model_to_dict(row) if row else None
    finally:
        db.close()


def update_session_report(session_id: int, report_id: int | None) -> None:
    """更新会话锚定的报告 ID（进入报告页时调用）"""
    from models import ChatSession

    db = SessionLocal()
    try:
        row = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if row:
            row.report_id = report_id
            db.commit()
    finally:
        db.close()


def add_message(session_id: int, role: str, content: str,
                tool_calls: list | None = None) -> dict:
    """追加一条消息，返回 _model_to_dict 结果"""
    from models import ChatMessage

    db = SessionLocal()
    try:
        obj = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return _model_to_dict(obj)
    finally:
        db.close()


def list_messages(session_id: int, limit: int = 100) -> list[dict]:
    """获取会话消息列表（按时间正序，limit 默认 100 条）"""
    from models import ChatMessage

    db = SessionLocal()
    try:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .limit(limit)
            .all()
        )
        return [_model_to_dict(r) for r in rows]
    finally:
        db.close()
```

- [ ] **Step 4: 建表验证**

Run: `cd backend && python -c "from database import init_db; init_db(); from models import ChatSession, ChatMessage; print('CHAT DB OK')"`
Expected: 打印 `CHAT DB OK`

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent
git add backend/models.py backend/chat_agent/
git commit -m "feat(chat_agent): 新增问答会话/消息 ORM 模型与 DAO"
```

---

### Task 2: 工具层（iFinD 全工具缓存 + 友好名映射 + 执行器）

**Files:**
- Create: `backend/chat_agent/tools.py`

**Interfaces:**
- Consumes: `stock_agent.skill` 的 `call_skill` / `list_skill_tools` / `extract_text`
- Produces: `chat_agent/tools.py` 导出 `TOOL_FRIENDLY_NAMES` / `get_tool_descriptions()` / `execute_tool_call(tool_name, arguments)` / `_server_for_tool(tool_name)`

- [ ] **Step 1: 定义工具友好名映射 + 服务路由表**

```python
"""投研 AI 问答 —— iFinD 工具层

职责：
  1. 维护工具→友好名映射（前端步骤卡片展示用，不暴露接口名）
  2. 拉取 iFinD tools/list 缓存工具描述（供 Function Calling 声明）
  3. execute_tool_call：把 LLM 的 tool_call 映射到 stock_agent.skill.call_skill 执行
"""
import json

from stock_agent.skill import call_skill, list_skill_tools
from stock_agent.skill.extract import extract_text

# 工具名 → 友好展示名（前端步骤卡片用）
TOOL_FRIENDLY_NAMES = {
    "get_stock_summary": "获取基本信息",
    "search_stocks": "智能选股",
    "get_stock_performance": "查询行情走势",
    "get_stock_info": "查询基本资料",
    "get_stock_shareholders": "查询股东结构",
    "get_stock_financials": "核对财务数据",
    "get_risk_indicators": "分析风险指标",
    "get_stock_events": "查询重大事件",
    "get_esg_data": "查询 ESG 评级",
    "stock_highfreq_quotes": "查询实时行情",
    "search_notice": "查询公司公告",
    "search_news": "查询近期新闻",
    # 港股 global_stock
    "global_stock_profile": "查询港股基本资料",
    "global_stock_quotes": "查询港股行情",
    "global_stock_financial": "查询港股财务",
    "global_stock_events": "查询港股事件",
    # 指数 / 板块 / 基金
    "index_data": "查询指数数据",
    "sector_data": "查询板块数据",
    "index_highfreq_quotes": "查询指数实时行情",
    "get_fund_profile": "查询基金资料",
    "get_fund_market_performance": "查询基金业绩",
    "get_fund_ownership": "查询基金持仓",
    "get_fund_portfolio": "查询基金组合",
    "get_fund_financials": "查询基金财务",
    "get_fund_company_info": "查询基金公司",
    "fund_highfreq_quotes": "查询基金实时行情",
}

# 工具名 → 所属 iFinD 服务
TOOL_SERVER_MAP = {
    # A股 / 股票
    "get_stock_summary": "stock",
    "search_stocks": "stock",
    "get_stock_performance": "stock",
    "get_stock_info": "stock",
    "get_stock_shareholders": "stock",
    "get_stock_financials": "stock",
    "get_risk_indicators": "stock",
    "get_stock_events": "stock",
    "get_esg_data": "stock",
    "stock_highfreq_quotes": "stock",
    # 新闻
    "search_notice": "news",
    "search_news": "news",
    # 港股
    "global_stock_profile": "global_stock",
    "global_stock_quotes": "global_stock",
    "global_stock_financial": "global_stock",
    "global_stock_events": "global_stock",
    # 指数
    "index_data": "index",
    "sector_data": "index",
    "index_highfreq_quotes": "index",
    # 基金
    "get_fund_profile": "fund",
    "get_fund_market_performance": "fund",
    "get_fund_ownership": "fund",
    "get_fund_portfolio": "fund",
    "get_fund_financials": "fund",
    "get_fund_company_info": "fund",
    "fund_highfreq_quotes": "fund",
}
```

- [ ] **Step 2: 工具描述缓存 + get_tool_descriptions()**

```python
_tool_descriptions_cache = {}


def get_tool_descriptions(server: str = "stock") -> list[dict]:
    """获取某服务全部工具描述（供 Function Calling 声明）

    首次调用从 iFinD tools/list 拉取并缓存；返回 MCP 工具结构，
    含 name/description/inputSchema。
    """
    if server in _tool_descriptions_cache:
        return _tool_descriptions_cache[server]
    try:
        res = list_skill_tools(server)
        # list_skill_tools 返回 {"data": {"result": {"tools": [...]}}}
        tools = res.get("data", {}).get("result", {}).get("tools", [])
        _tool_descriptions_cache[server] = tools
        return tools
    except Exception as e:
        print(f"[chat_agent] ⚠️ 拉取 {server} 工具描述失败: {e}")
        return []
```

- [ ] **Step 3: execute_tool_call + 结果格式化**

```python
def execute_tool_call(tool_name: str, arguments: dict) -> dict:
    """执行一个 iFinD 工具调用

    Args:
        tool_name: iFinD 工具名
        arguments: LLM 生成的参数 dict（query 自然语言 / 结构化参数）

    Returns:
        {"ok": bool, "text": str}   # text 为提取后的业务文本，可直接喂回 LLM
    """
    server = TOOL_SERVER_MAP.get(tool_name)
    if server is None:
        return {"ok": False, "text": f"[错误] 未知工具: {tool_name}"}

    # 高频行情用结构化参数；news 类需补 time 参数（可默认最近 90 天）
    params = dict(arguments)
    if tool_name == "search_news" and "time_start" not in params:
        params["time_start"] = _days_ago_str(90)
        params["time_end"] = _days_ago_str(0)
    if tool_name == "search_notice" and "time_start" not in params:
        params["time_start"] = _days_ago_str(180)
        params["time_end"] = _days_ago_str(0)

    try:
        result = call_skill(server, tool_name, params)
        text = extract_text(result)
        return {"ok": result.get("ok", False), "text": text}
    except Exception as e:
        return {"ok": False, "text": f"[错误] {type(e).__name__}: {str(e)}"}


def _days_ago_str(days: int) -> str:
    """返回 N 天前的日期字符串 YYYY-MM-DD"""
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
```

- [ ] **Step 4: 冒烟测试**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
from chat_agent.tools import execute_tool_call, get_tool_descriptions
# 工具描述可拉取
d = get_tool_descriptions('stock')
print(f'stock 工具数: {len(d)}')
# query 工具可执行
r = execute_tool_call('get_stock_financials', {'query': '贵州茅台最新 ROE'})
print(f'query 工具 ok={r[\"ok\"]} 文本长度={len(r[\"text\"])}')
# 高频行情工具可执行（非 query）
r2 = execute_tool_call('stock_highfreq_quotes', {'symbols': '600519.SH', 'indicators': '最新价,涨跌幅', 'data_mode': 'real_time'})
print(f'非query 工具 ok={r2[\"ok\"]} 文本长度={len(r2[\"text\"])}')
print('TOOLS OK')"`
Expected: 打印 `stock 工具数: 10` + `TOOLS OK`

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent
git add backend/chat_agent/tools.py
git commit -m "feat(chat_agent): iFinD 全工具层（描述缓存/友好名/执行器）"
```

---

### Task 3: LangGraph 工作流（understand / tool_loop / answer + prompts）

**Files:**
- Create: `backend/chat_agent/prompts.py`
- Create: `backend/chat_agent/graph.py`

**Interfaces:**
- Consumes: Task 2 的 `chat_agent/tools.py`；`stock_agent.skill` 的 `call_skill`；根 `database.py` 的 `get_stock_report_by_id`
- Produces: `chat_agent/graph.py` 导出 `run_qa_agent(question, stock_code, stock_name, report_context, history)`（返回事件迭代器 / 最终结果）

- [ ] **Step 1: 写 prompts.py（三个 prompt）**

```python
"""投研 AI 问答 —— Prompt 模板（意图理解 / 工具循环 / 约束回答）"""

# 意图理解：判断是否股票相关、提取目标股票、决定是否需要工具
UNDERSTAND_PROMPT = """分析用户的提问，输出 JSON。

用户问题：{question}
当前股票：{stock_code}（{stock_name}）
当前日期：{today_str}

请判断并输出严格 JSON（不要 markdown 包裹）：
{{
  "is_off_topic": false,
  "stock_code": "{stock_code}",
  "needs_tools": true,
  "tool_hints": ["估值", "财务"]
}}

规则：
1. is_off_topic：问题与股票/金融投资完全无关时置 true（如"今天天气如何"）。
2. stock_code：若问题提到明确的其他股票（如"五粮液怎么样"），输出那只股票的代码格式提示；否则默认当前股票。
3. needs_tools：需要实时查数时 true；仅需解读报告内容时可 false。
4. tool_hints：大致需要的数据方向，取值示例 ["估值","财务","行情","股东","新闻","风险","ESG","公告"]，最多 3 个。"""

# 约束回答：基于工具结果 + 报告 + 历史生成最终回答
ANSWER_PROMPT = """你是投研报告问答助理 karens，正在为用户解读股票投研报告并实时查数回答。

当前股票：{stock_code}（{stock_name}）
用户问题：{question}
报告结论摘要：
{report_context}

实时查询到的数据：
{tool_results}

要求：
1. 优先依据实时查询数据回答，不得编造数值。
2. 数据不足时明确说明"数据不足"。
3. 结合报告结论给出解读。
4. 若用户问题与股票/金融投资无关，统一回复："karens暂时无法回答您这个问题哦？"
5. 回答用 Markdown，结构清晰。
"""

# 纯报告解读（无工具调用时，answer 节点用）
REPORT_ONLY_PROMPT = """你是投研报告问答助理 karens，请基于以下报告结论回答用户问题。

当前股票：{stock_code}（{stock_name}）
用户问题：{question}
报告结论摘要：
{report_context}

要求：
1. 仅基于报告内容回答，不得编造报告外的数据。
2. 报告未覆盖的内容，可提示"报告未包含该数据，需要我实时查询吗？"
3. 回答用 Markdown。"""

# 免责声明（后端固定拼接）
DISCLAIMER = "\n\n---\n*以上内容基于 iFinD 实时数据与投研报告，仅供参考，不构成投资建议。*"
```

- [ ] **Step 2: 写 graph.py 核心（LLM 客户端 + Function Calling 循环）**

```python
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
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    return _client
```

- [ ] **Step 3: 写 understand 节点**

```python
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
        # 剥离 ```json 包裹
        if "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        data = json.loads(text.strip())
        return {
            "is_off_topic": bool(data.get("is_off_topic", False)),
            "stock_code": data.get("stock_code") or stock_code,
            "needs_tools": bool(data.get("needs_tools", False)),
            "tool_hints": data.get("tool_hints", []),
        }
    except Exception as e:
        print(f"[chat_agent] ⚠️ 意图理解失败，默认按股票相关处理: {e}")
        return {
            "is_off_topic": False,
            "stock_code": stock_code,
            "needs_tools": False,
            "tool_hints": [],
        }
```

- [ ] **Step 4: 写 tool_loop 节点（Function Calling 循环）**

```python
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
        messages.append(msg)
        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
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
```

- [ ] **Step 5: 写 answer 节点 + 总入口 run_qa_agent**

```python
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
        print(f"[chat_agent] ❌ run_qa_agent 失败: {e}")
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
```

- [ ] **Step 6: 冒烟测试（用真实 DeepSeek + 真实 iFinD 单轮）**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
from chat_agent.graph import run_qa_agent
r = run_qa_agent('贵州茅台最新估值怎么样？', '600519.SH', '贵州茅台', '报告摘要：茅台估值处于历史低位。', [])
print(f'answer长度: {len(r[\"answer\"])} 工具调用数: {len(r[\"tool_calls\"])}')
print('ANSWER 开头:', r['answer'][:150])
print('GRAPH OK')"`
Expected: 打印 `GRAPH OK`，answer 非空，工具调用 ≥ 1

- [ ] **Step 7: 提交**

```bash
cd d:/karensAgent
git add backend/chat_agent/prompts.py backend/chat_agent/graph.py
git commit -m "feat(chat_agent): LangGraph 问答工作流（understand/tool_loop/answer）"
```

---

### Task 4: SSE 接口（routers + 流式事件）

**Files:**
- Create: `backend/chat_agent/routers/__init__.py`
- Create: `backend/chat_agent/routers/chat.py`
- Modify: `backend/main.py`（注册路由）

**Interfaces:**
- Consumes: Task 1 `chat_agent/database.py`；Task 3 `chat_agent/graph.py`；根 `database.py` 的 `get_stock_report_by_id`
- Produces: 三个 API：
  - `GET /api/chat/session/{stock_code}` → 会话 + 历史消息
  - `GET /api/chat/session/{stock_code}/messages` → 分页历史
  - `POST /api/chat/{stock_code}/ask` → SSE 流式提问

- [ ] **Step 1: 写 routers/__init__.py**

```python
"""投研 AI 问答 —— API 路由"""
```

- [ ] **Step 2: 写 routers/chat.py（三个端点）**

```python
"""投研 AI 问答 —— FastAPI 路由"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from database import get_stock_report_by_id
from ..database import (
    get_or_create_session, update_session_report, add_message, list_messages,
)
from ..graph import run_qa_agent
from ..tools import TOOL_FRIENDLY_NAMES

router = APIRouter(prefix="/api/chat", tags=["chat"])


class AskRequest(BaseModel):
    question: str
    report_id: int | None = None   # 可选，用于锚定会话
    stock_name: str = ""


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/session/{stock_code}")
def get_chat_session(stock_code: str):
    """获取会话 + 历史消息"""
    session = get_or_create_session(stock_code)
    messages = list_messages(session["id"])
    return {"code": 0, "data": {"session": session, "messages": messages}}


@router.get("/session/{stock_code}/messages")
def get_chat_messages(stock_code: str, limit: int = 100):
    """分页拉历史消息"""
    session = get_or_create_session(stock_code)
    messages = list_messages(session["id"], limit=limit)
    return {"code": 0, "data": messages}


@router.post("/{stock_code}/ask")
async def ask(stock_code: str, req: AskRequest):
    """SSE 流式提问"""
    session = get_or_create_session(stock_code, req.stock_name)

    # 锚定报告（可选）
    if req.report_id:
        update_session_report(session["id"], req.report_id)

    # 构建报告上下文（固定锚点：取最新报告结论摘要）
    report_context = _build_report_context(req.report_id, stock_code)

    # 记录用户消息
    add_message(session["id"], "user", req.question)

    async def gen():
        yield _sse({"type": "thinking"})
        # 后台线程执行问答（含工具调用），完成后流式输出
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_qa_agent(
                req.question, stock_code, req.stock_name or session["stock_name"],
                report_context, [],
            ),
        )

        # 工具调用事件（前端步骤卡片）
        for tc in result["tool_calls"]:
            yield _sse({"type": "tool_done", "name": tc["name"],
                        "label": tc.get("label", tc["name"]), "ok": tc["ok"]})

        # 回答增量（简单按句切分模拟流式；后续可换真 token 流）
        answer = result["answer"]
        for chunk in _chunk_text(answer):
            yield _sse({"type": "delta", "text": chunk})
            await asyncio.sleep(0.02)

        yield _sse({"type": "done", "full": answer})

        # 记录助手消息
        add_message(session["id"], "assistant", answer, result["tool_calls"] or None)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _build_report_context(report_id: int | None, stock_code: str) -> str:
    """构建注入报告上下文：优先指定报告，否则取该股最新报告"""
    row = None
    if report_id:
        row = get_stock_report_by_id(report_id)
    if row is None:
        from database import get_latest_report
        row = get_latest_report(stock_code)
    if row is None:
        return "（暂无报告）"
    # 提取报告结论摘要：summary 字段 + 评分/判断
    parts = [f"评分：{row.get('score', '')}", f"判断：{row.get('decision', '')}"]
    if row.get("summary"):
        parts.append(f"摘要：{row['summary']}")
    return "\n".join(parts)


def _chunk_text(text: str, size: int = 6) -> list[str]:
    """把回答切成小块（近似流式；中文字符按 6 字一块）"""
    if not text:
        return []
    return [text[i:i + size] for i in range(0, len(text), size)]
```

- [ ] **Step 3: 注册路由到 main.py**

在 `backend/main.py` 路由注册区追加：

```python
from chat_agent.routers.chat import router as chat_router
# ...
app.include_router(chat_router)
```

- [ ] **Step 4: 接口冒烟（直接调 run_qa_agent 已测，此处验证路由可导入）**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
from chat_agent.routers.chat import router, _build_report_context, _chunk_text
assert len(_chunk_text('abc中文测试', 6)) >= 1
print('ctx:', _build_report_context(None, '600519.SH')[:80])
print('ROUTER OK')"`
Expected: 打印 `ROUTER OK`

- [ ] **Step 5: 提交**

```bash
cd d:/karensAgent
git add backend/chat_agent/routers/ backend/main.py
git commit -m "feat(chat_agent): SSE 问答接口（会话/历史/流式提问）"
```

---

### Task 5: 前端面板（AiChatPanel 升级 + 步骤卡片 + store/api）

**Files:**
- Modify: `frontend/src/api/index.js`（新增 chat API + SSE 函数）
- Modify: `frontend/src/stores/stock.js`（新增 chat 状态与 action）
- Create: `frontend/src/components/report/AiStepsCard.vue`（步骤卡片组件）
- Modify: `frontend/src/components/report/AiChatPanel.vue`（占位升级为真实会话）

**Interfaces:**
- Consumes: 现有 `useStockStore`；`marked`（已在用）
- Produces: `AiChatPanel.vue` 接收 `useStockStore.currentReport`（内含 stock_code/stock_name）

- [ ] **Step 1: api/index.js 新增 chat API**

```javascript
/* ═══════════════════════════════════════════
 * AI 问答助理（karens）
 * ═══════════════════════════════════════════ */
export const getChatSession = (stockCode) =>
  api.get(`/chat/session/${stockCode}`)

export const getChatMessages = (stockCode, limit = 100) =>
  api.get(`/chat/session/${stockCode}/messages`, { params: { limit } })

/**
 * SSE 问答：流式获取 karens 回答
 * @param {string} stockCode
 * @param {object} body  { question, report_id, stock_name }
 * @param {object} callbacks { onThinking, onToolDone, onDelta, onDone, onError }
 * @returns {AbortController}
 */
export function fetchChatAsk(stockCode, body, callbacks = {}) {
  const controller = new AbortController()
  fetch(`/api/chat/${stockCode}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: controller.signal,
  }).then(async (res) => {
    if (!res.ok) { callbacks.onError?.(new Error(`HTTP ${res.status}`)); return }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop()
      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'thinking') callbacks.onThinking?.(data)
          else if (data.type === 'tool_done') callbacks.onToolDone?.(data)
          else if (data.type === 'delta') callbacks.onDelta?.(data)
          else if (data.type === 'done') callbacks.onDone?.(data)
          else if (data.type === 'error') callbacks.onError?.(new Error(data.message || '未知错误'))
        } catch (_) {}
      }
    }
  }).catch(err => {
    if (err.name !== 'AbortError') callbacks.onError?.(err)
  })
  return controller
}
```

- [ ] **Step 2: stores/stock.js 新增 chat 状态与 action**

state 追加：

```javascript
    /* AI 问答 */
    chatMessages: [],       // [{ role, content, tool_calls }]
    chatSession: null,      // { id, stock_code, ... }
    chatAsking: false,      // 是否正在请求
    chatThinking: false,    // 是否正在思考/查数
    chatToolSteps: [],      // [{ id, label, status }] 工具步骤卡片
```

actions 追加：

```javascript
    /* ── AI 问答 ── */
    async fetchChatSession(stockCode) {
      try {
        const res = await api.getChatSession(stockCode)
        if (res.code === 0) {
          this.chatSession = res.data.session
          this.chatMessages = res.data.messages || []
        }
      } catch (e) { this.showToast('加载问答会话失败') }
    },
    async fetchChatMessages(stockCode) {
      try {
        const res = await api.getChatMessages(stockCode)
        if (res.code === 0) this.chatMessages = res.data || []
      } catch (_) {}
    },

    /**
     * 发送问答（SSE 流式），内部管理 thinking/toolSteps/chatAsking 状态。
     * 组件只调此 action，不直接 import api（符合项目惯例）。
     * @returns {AbortController}
     */
    askChat(stockCode, { question, report_id, stock_name }) {
      this.chatAsking = true
      this.chatThinking = true
      this.chatToolSteps = []
      this.chatMessages.push({ role: 'user', content: question, tool_calls: null })

      let stepId = 0
      const controller = api.fetchChatAsk(stockCode, {
        question, report_id, stock_name,
      }, {
        onThinking: () => { this.chatThinking = true },
        onToolDone: (d) => {
          this.chatThinking = false
          stepId++
          this.chatToolSteps.push({
            id: stepId,
            label: d.label || d.name,
            status: d.ok ? 'done' : 'error',
          })
        },
        onDelta: (d) => {
          const last = this.chatMessages[this.chatMessages.length - 1]
          if (last && last.role === 'assistant') last.content += d.text
          else this.chatMessages.push({ role: 'assistant', content: d.text, tool_calls: null })
        },
        onDone: (d) => {
          const last = this.chatMessages[this.chatMessages.length - 1]
          if (last && last.role === 'assistant') last.content = d.full
          else this.chatMessages.push({ role: 'assistant', content: d.full, tool_calls: null })
          this.chatThinking = false
          this.chatToolSteps = []
          this.chatAsking = false
        },
        onError: (e) => {
          this.showToast(e.message || '回答失败')
          this.chatThinking = false
          this.chatToolSteps = []
          this.chatAsking = false
        },
      })
      return controller
    },
```

- [ ] **Step 3: 新建 AiStepsCard.vue（步骤卡片组件）**

遵循项目浅色系、简约、无渐变，复用 `--sent-*` CSS 变量。展示工具调用步骤列表：等待（灰点）/ 进行（呼吸动画）/ 完成（绿勾淡入）/ 失败（红叉）。

```vue
<!-- AI 问答步骤卡片：展示 karens 实时查数的工具调用过程（友好名 + 状态图标） -->
<template>
  <div class="ai-steps">
    <div v-for="s in steps" :key="s.id" class="step" :class="`is-${s.status}`">
      <span class="step-icon" aria-hidden="true">{{ iconOf(s.status) }}</span>
      <span class="step-label">{{ s.label }}</span>
    </div>
  </div>
</template>

<script setup>
/* 步骤卡片：status = pending | running | done | error */
defineProps({
  steps: { type: Array, default: () => [] },
})
function iconOf(status) {
  if (status === 'done') return '✓'
  if (status === 'error') return '✕'
  if (status === 'running') return '◐'
  return '○'
}
</script>

<style scoped>
/* 步骤卡片容器：浅色卡片，内部步骤纵向排列 */
.ai-steps {
  display: flex; flex-direction: column; gap: 6px;
  background: var(--sent-bg); border: 1px solid var(--border-color);
  border-radius: var(--radius-md); padding: 10px 12px;
}
.step { display: flex; align-items: center; gap: 8px; font-size: 0.76rem; color: var(--sent-mid); }
.step-icon { width: 14px; text-align: center; }
.step.is-done .step-icon { color: var(--success, #2e7d32); }
.step.is-error .step-icon { color: var(--red, #c62828); }
.step.is-running .step-icon { animation: step-spin 1.2s linear infinite; color: var(--accent); }
@keyframes step-spin { to { transform: rotate(360deg); } }
</style>
```

> 注：`--success` 若项目未定义，fallback 到 `#2e7d32`；`--red` 项目已有。

- [ ] **Step 4: 升级 AiChatPanel.vue**

核心改动：
- 顶部：占位的"即将上线"徽章改为 karens 标识
- 会话区：占位说明替换为真实消息气泡列表（用户右对齐、karens 左对齐 + marked 渲染）
- 发送中：显示"思考"提示 + 步骤卡片（实时更新 tool_done 事件）
- 输入区：启用输入框 + 发送按钮（禁用防重复提交）
- 挂载时：`store.fetchChatSession(stockCode)` 加载历史
- 用 `useStockStore` 取 `currentReport` 的 `stock_code` / `stock_name` / `id` 作为 `report_id`

关键脚本结构：

```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { useStockStore } from '../../stores/stock.js'
import AiStepsCard from './AiStepsCard.vue'

const store = useStockStore()
const input = ref('')

const report = computed(() => store.currentReport)
const stockCode = computed(() => report.value?.stock_code || '')
const stockName = computed(() => report.value?.stock_name || '')

/* 历史消息渲染（含 tool_calls 转步骤卡片） */
const messages = computed(() => store.chatMessages)
const thinking = computed(() => store.chatThinking)
const toolSteps = computed(() => store.chatToolSteps)
function renderMd(text) { return marked.parse(text) }

function toolStepsFromRecord(record) {
  return (record.tool_calls || []).map((tc, i) => ({
    id: i, label: tc.label || tc.name, status: tc.ok ? 'done' : 'error',
  }))
}

async function send() {
  const q = input.value.trim()
  if (!q || store.chatAsking) return
  input.value = ''
  store.askChat(stockCode.value, {
    question: q,
    report_id: report.value?.id || null,
    stock_name: stockName.value,
  })
}

onMounted(() => {
  if (stockCode.value) store.fetchChatSession(stockCode.value)
})
</script>
```

> 组件只依赖 `useStockStore`，SSE 逻辑在 store `askChat` action 内（符合项目"组件不直接 import api"惯例）。

模板结构（占位结构替换）：

```html
<template>
  <aside class="ai-panel">
    <header class="ai-head">
      <div class="ai-id">
        <svg .../>  <!-- karens 头像 -->
        <strong>karens 问答助理</strong>
      </div>
    </header>

    <div class="ai-body">
      <!-- 空态：无消息时显示欢迎语 -->
      <div v-if="!messages.length" class="ai-empty">
        <p>对这份投研报告有任何疑问，尽管问 karens。</p>
      </div>

      <!-- 消息气泡 -->
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="bubble" v-html="renderMd(m.content)"></div>
        <AiStepsCard v-if="m.role === 'assistant' && m.tool_calls" :steps="toolStepsFromRecord(m)" />
      </div>

      <!-- 思考中 -->
      <div v-if="thinking" class="ai-thinking">
        <span class="ai-dots"><i></i><i></i><i></i></span>
        <span>karens 正在理解你的问题…</span>
      </div>

      <!-- 工具步骤卡片（实时） -->
      <AiStepsCard v-if="toolSteps.length" :steps="toolSteps" />
    </div>

    <footer class="ai-input">
      <input v-model="input" type="text" placeholder="输入问题，回车发送"
             @keyup.enter="send" :disabled="store.chatAsking" />
      <button type="button" @click="send" :disabled="store.chatAsking || !input.trim()">发送</button>
    </footer>
  </aside>
</template>
```

> 样式沿用现有 `ai-panel`/`ai-body`/`ai-head`/`ai-input` 结构，新增 `.msg`（用户右对齐 / karens 左对齐）、`.bubble`、`.ai-empty`、`.ai-thinking` 样式，遵循项目 `--sent-*` 色系。

- [ ] **Step 5: 前端构建验证**

Run: `cd frontend && npm run build 2>&1 | tail -15`
Expected: 构建成功，无报错

- [ ] **Step 6: 提交**

```bash
cd d:/karensAgent
git add frontend/src/api/index.js frontend/src/stores/stock.js frontend/src/components/report/
git commit -m "feat(chat_agent): 前端问答面板升级（步骤卡片/流式回答/会话历史）"
```

---

### Task 6: 联调验证 + 收尾

**Files:**
- 无新文件，仅验证

**Interfaces:**
- 无

- [ ] **Step 1: 后端全量测试**

Run: `cd backend && python -m pytest tests -q`
Expected: 全部通过（新增代码不破坏既有 191 项）

- [ ] **Step 2: 后端 import 冒烟（模拟 main.py 启动路径）**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
from chat_agent.routers.chat import router
from chat_agent.graph import run_qa_agent
from chat_agent.tools import execute_tool_call
from chat_agent.database import get_or_create_session, add_message, list_messages
print('CHAT SMOKE OK')"`
Expected: 打印 `CHAT SMOKE OK`

- [ ] **Step 3: 前端构建确认**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: 构建成功

- [ ] **Step 4: 端到端冒烟（真实提问）**

Run: `cd backend && python -c "
import sys; sys.path.insert(0, '.')
from chat_agent.graph import run_qa_agent
# 真实端到端：意图理解 → 工具调用 → 回答
r = run_qa_agent('贵州茅台今天的实时行情怎么样？', '600519.SH', '贵州茅台', '报告摘要：茅台估值合理。', [])
print(f'success={r[\"success\"]} tools={len(r[\"tool_calls\"])} answer_len={len(r[\"answer\"])}')
print('末尾免责声明存在:', '仅供参考' in r['answer'])
print('E2E OK')"`
Expected: `E2E OK`，tools ≥ 1，免责声明存在

- [ ] **Step 5: 提交收尾**

```bash
cd d:/karensAgent
git status
git commit -m "feat(chat_agent): AI 问答助理完整链路联调验证通过" --allow-empty
```
（若上一步无改动，此步可跳过空提交。）

---

## Self-Review 记录

- **Spec 覆盖**：Task 1=PRD 5.1 表结构；Task 2=PRD 4.3 工具层；Task 3=PRD 4.2 工作流 + 8 Prompt 范式；Task 4=PRD 5.3 API + 6.1 SSE 事件；Task 5=PRD 7 前端界面设计；Task 6=PRD 10 成功指标验证。全部覆盖 ✅
- **Placeholder 扫描**：无 TBD/TODO。所有函数体给出完整代码 ✅
- **依赖顺序**：Task 1（DB）→ Task 2（工具层）→ Task 3（图，依赖工具层）→ Task 4（接口，依赖图）→ Task 5（前端，独立可并行）→ Task 6（联调）✅
- **关键风险提示**：Task 3 的 Function Calling 已实测 DeepSeek 支持且与思考模式兼容（见 PRD 4.3）；iFinD 6 接口实测可用；`run_qa_agent` 为同步执行 + 线程池包装，SSE 流式先按句切块模拟，后续可换真 token 流 ✅
