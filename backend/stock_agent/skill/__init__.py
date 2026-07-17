"""iFinD SKILL 调用封装

通过 sys.path 导入 ~/.claude/skills/ifind-finance-data/call.py
不复制文件，密钥配置由 call.py 自行读取同目录下的 mcp_config.json
"""
import json
import sys
import warnings
from pathlib import Path

# 禁用 SSL 警告（call.py 使用 verify=False）
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

SKILL_DIR = str(Path("~/.claude/skills/ifind-finance-data").expanduser())
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

from call import call as _call, list_tools as _list_tools  # noqa: E402


def call_skill(server_type: str, tool_name: str, params: dict) -> dict:
    """调用 iFinD SKILL 的 call 函数

    Args:
        server_type: stock | fund | edb | news | bond | global_stock | index
        tool_name: SKILL 工具名称，详见 references/ 下子服务文档
        params: 请求参数，自然语言工具用 {"query": "..."}，
                高频行情用 {"symbols": "...", "indicators": "...", "data_mode": "..."}

    Returns:
        {"ok": True/False, "status_code": int, "data": dict}
    """
    return _call(server_type, tool_name, params)


def list_skill_tools(server_type: str) -> dict:
    """获取某个服务当前可用的工具清单"""
    return _list_tools(server_type)


def extract_text(result: dict) -> str:
    """从 SKILL 返回结果中提取文本内容

    SKILL 返回格式为 MCP JSON-RPC 包装：
    data.result.content[0].text → JSON 字符串 → 内层 data 字段

    不同工具的内层格式略有差异，此函数做统一提取。
    """
    if not result.get("ok"):
        err = result.get("error", "未知错误")
        if isinstance(err, dict):
            err = err.get("message", str(err))
        return f"[错误] {err}"

    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return "[无数据]"

    raw_text = content[0].get("text", "")
    if not raw_text:
        return "[空响应]"

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return raw_text

    if not isinstance(inner, dict):
        return str(inner)

    # 检查内层 code 字段
    if inner.get("code") == 0:
        return f"[权限不足或无数据] {inner.get('msg', '')}"

    inner_data = inner.get("data")
    if inner_data is None:
        return raw_text

    # 新闻/公告类：data 是 dict，含 "data" 字段（JSON 数组字符串）
    if isinstance(inner_data, dict):
        if "answer" in inner_data:
            return inner_data["answer"]
        if "data" in inner_data:
            news_data = inner_data["data"]
            if isinstance(news_data, str):
                try:
                    articles = json.loads(news_data)
                    return _format_news(articles)
                except (json.JSONDecodeError, TypeError):
                    return news_data
            if isinstance(news_data, list):
                return _format_news(news_data)
        # 兜底：返回整个 inner_data 的 JSON
        return json.dumps(inner_data, ensure_ascii=False, indent=2)

    # 实时行情类：data 是 JSON 字符串，内含表格
    if isinstance(inner_data, str):
        try:
            table_data = json.loads(inner_data)
            if isinstance(table_data, dict) and "tables" in table_data:
                return _format_table(table_data)
            return json.dumps(table_data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            return inner_data

    return str(inner_data)


def _format_table(data: dict) -> str:
    """格式化 SKILL 返回的表格数据为 Markdown 表格"""
    tables = data.get("tables", [])
    if not tables:
        return json.dumps(data, ensure_ascii=False, indent=2)

    lines = []
    # tables[0] 是表头，tables[1:] 是数据行
    if len(tables) >= 2:
        headers = tables[0]
        rows = tables[1:]
        # Markdown 表格
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def extract_raw(result: dict):
    """从 SKILL 返回结果中提取原始结构化数据（不做 Markdown 格式化）

    返回 typed dict，方便 prose formatter 按维度处理：
      {"type": "table",  "tables": [[...], ...]}     — 表格数据
      {"type": "news",   "articles": [{...}, ...]}    — 新闻/公告列表
      {"type": "answer", "text": "..."}               — 自然语言回答（可能内含表格）
      {"type": "text",   "text": "..."}               — 纯文本/兜底
      None                                              — 错误或无数据
    """
    if not result.get("ok"):
        return None

    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return None

    raw_text = content[0].get("text", "")
    if not raw_text:
        return None

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {"type": "text", "text": raw_text}

    if not isinstance(inner, dict):
        return {"type": "text", "text": str(inner)}

    # 检查错误码
    if inner.get("code") == 0:
        return None

    inner_data = inner.get("data")
    if inner_data is None:
        return {"type": "text", "text": raw_text}

    # 新闻/公告类：data 是 dict
    if isinstance(inner_data, dict):
        if "answer" in inner_data:
            return {"type": "answer", "text": inner_data["answer"]}
        if "data" in inner_data:
            news_data = inner_data["data"]
            if isinstance(news_data, str):
                try:
                    articles = json.loads(news_data)
                    return {"type": "news", "articles": articles}
                except (json.JSONDecodeError, TypeError):
                    return {"type": "text", "text": news_data}
            if isinstance(news_data, list):
                return {"type": "news", "articles": news_data}
        return {"type": "json", "data": inner_data}

    # 表格类：data 是 JSON 字符串
    if isinstance(inner_data, str):
        try:
            table_data = json.loads(inner_data)
            if isinstance(table_data, dict) and "tables" in table_data:
                return {"type": "table", "tables": table_data["tables"]}
            return {"type": "json", "data": table_data}
        except (json.JSONDecodeError, TypeError):
            return {"type": "text", "text": inner_data}

    return {"type": "text", "text": str(inner_data)}


def _format_news(articles: list) -> str:
    """格式化新闻/公告列表为 Markdown"""
    if not articles:
        return "[无相关新闻或公告]"

    lines = []
    for i, article in enumerate(articles, 1):
        if isinstance(article, dict):
            title = article.get("资讯标题") or article.get("公告标题") or article.get("title", "无标题")
            date = article.get("日期") or article.get("date", "")
            content = article.get("资讯内容") or article.get("公告片段内容") or article.get("content", "")
            # 截取前 300 字
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"**{i}. {title}**")
            if date:
                lines.append(f"  📅 {date}")
            lines.append(f"  {content}")
            lines.append("")
        else:
            lines.append(f"- {article}")
    return "\n".join(lines)
