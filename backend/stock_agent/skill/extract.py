"""iFinD SKILL 响应解析 — 文本提取与结构化提取

统一从 MCP JSON-RPC 包装中解出业务数据，供上层维度处理。
"""
import json


def _is_out_of_scope_answer(answer) -> bool:
    """数据范围外应答判定（如查港股走了 A 股服务），厂商以自然语言拒答"""
    return isinstance(answer, str) and "不属于" in answer and "数据范围" in answer


def _answer_of(data) -> str | None:
    """iFinD 应答文本提取：dict 含 answer 键即视为应答（dict/字符串包裹两种形态共用）"""
    if isinstance(data, dict) and "answer" in data:
        return data["answer"]
    return None


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

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return str(first)

    raw_text = first.get("text", "")
    if not raw_text:
        return "[空响应]"

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return raw_text

    if not isinstance(inner, dict):
        return str(inner)

    # 检查内层 code 字段
    # 约定（Task 2 于 2026-07-29 实证确认）：iFinD 内层 code=0 表示失败/权限不足，
    # 成功响应 code 为 1（msg='success'）。系统正常运行即依赖此约定，勿按"0=成功"的通用惯例改。
    if inner.get("code") == 0:
        return f"[权限不足或无数据] {inner.get('msg', '')}"

    inner_data = inner.get("data")
    if inner_data is None:
        return raw_text

    # 新闻/公告类：data 是 dict，含 "data" 字段（JSON 数组字符串）
    if isinstance(inner_data, dict):
        answer = _answer_of(inner_data)
        if answer is not None:
            # 数据范围外应答（如查港股走了 A 股服务）→ 标记为无数据
            if _is_out_of_scope_answer(answer):
                return f"[无数据] {answer}"
            return answer
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
            # 与 dict 分支对齐：global_stock 应答的 data 为 JSON 字符串包裹 answer，
            # 不识别会误分类成 json，截断港股名称提取链路（2026-08-07 实证根因）
            answer = _answer_of(table_data)
            if answer is not None:
                if _is_out_of_scope_answer(answer):
                    return f"[无数据] {answer}"
                return answer
            if isinstance(table_data, dict) and "tables" in table_data:
                return _format_table(table_data)
            return json.dumps(table_data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            # 厂商软错误：外层 code=1 但 data 是非 JSON 错误文本（实证用例见
            # test_extract_text_vendor_soft_error）。本分支契约是行情表格 JSON
            # 字符串，非 JSON 即异常，统一转 [无数据] 供上层判定维度失败。
            # 注：新闻 data 分支的纯文本属合法数据，不适用此规则
            return f"[无数据] {inner_data}"

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
      {"type": "json",   "data": {...}}               — 非表格的结构化 JSON
      {"type": "text",   "text": "..."}               — 纯文本/兜底
      None                                              — 错误或无数据
    """
    if not result.get("ok"):
        return None

    data = result.get("data", {})
    content = data.get("result", {}).get("content", [])
    if not content:
        return None

    # 守卫：MCP 异常响应下 content[0] 可能不是 dict
    first = content[0]
    if not isinstance(first, dict):
        return {"type": "text", "text": str(first)}

    raw_text = first.get("text", "")
    if not raw_text:
        return None

    try:
        inner = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {"type": "text", "text": raw_text}

    if not isinstance(inner, dict):
        return {"type": "text", "text": str(inner)}

    # 检查内层 code 字段
    # 约定（Task 2 于 2026-07-29 实证确认）：iFinD 内层 code=0 表示失败/权限不足，
    # 成功响应 code 为 1（msg='success'）。系统正常运行即依赖此约定，勿按"0=成功"的通用惯例改。
    if inner.get("code") == 0:
        return None

    inner_data = inner.get("data")
    if inner_data is None:
        return {"type": "text", "text": raw_text}

    # 新闻/公告类：data 是 dict
    if isinstance(inner_data, dict):
        answer = _answer_of(inner_data)
        if answer is not None:
            return {"type": "answer", "text": answer}
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
            # 与 dict 分支对齐：JSON 字符串包裹 answer（global_stock 应答形态）
            answer = _answer_of(table_data)
            if answer is not None:
                return {"type": "answer", "text": answer}
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
