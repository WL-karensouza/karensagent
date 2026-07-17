"""SKILL 报告编排器

10 维度串行调度、SSE 进度推送、Markdown 汇总。
"""
import asyncio
import json
import re
import time
from datetime import datetime
from . import call_skill, extract_text, extract_raw


# ═══════════════════════════════════════════
# 10 个报告维度定义（完全参照 SKILL 工具能力）
# ═══════════════════════════════════════════

DIMENSIONS = [
    {"key": "quotes",      "label": "实时行情",       "server": "stock", "tool": "stock_highfreq_quotes",  "critical": True},
    {"key": "summary",     "label": "基本信息与估值",  "server": "stock", "tool": "get_stock_summary",       "critical": True},
    {"key": "performance", "label": "近期行情走势",    "server": "stock", "tool": "get_stock_performance",    "critical": False},
    {"key": "financials",  "label": "财务数据",       "server": "stock", "tool": "get_stock_financials",     "critical": False},
    {"key": "shareholders","label": "股东结构",       "server": "stock", "tool": "get_stock_shareholders",   "critical": False},
    {"key": "risk",        "label": "风险评估",       "server": "stock", "tool": "get_risk_indicators",      "critical": False},
    {"key": "esg",         "label": "ESG 评级",       "server": "stock", "tool": "get_esg_data",             "critical": False},
    {"key": "events",      "label": "重大事件",       "server": "stock", "tool": "get_stock_events",         "critical": False},
    {"key": "news",        "label": "近期新闻",       "server": "news",  "tool": "search_news",              "critical": False},
    {"key": "notices",     "label": "公司公告",       "server": "news",  "tool": "search_notice",            "critical": False},
]

# 限速间隔（秒）：免费版 2 QPS，串行 10 维度约 20-30 秒
RATE_LIMIT_INTERVAL = 0.6


def _build_params(dim: dict, stock_code: str) -> dict:
    """根据维度配置和股票代码构建 SKILL 调用参数"""
    key = dim["key"]
    tool = dim["tool"]

    # 实时行情使用结构化参数
    if tool == "stock_highfreq_quotes":
        suffix = _market_suffix(stock_code)
        return {
            "symbols": f"{stock_code}{suffix}",
            "indicators": "latest,open,high,low,close,volume,amount,change,changePct,amplitude,avgPrice",
            "data_mode": "latest",
        }

    # 自然语言类工具 — 构造中文 query
    queries = {
        "summary": (
            f"股票代码{stock_code}的基本信息，包括公司全称、所属行业、上市日期、"
            f"总市值、流通市值、市盈率PE、市净率PB、估值水平"
        ),
        "performance": (
            f"股票代码{stock_code}的近期行情走势，包括近1月/近3月/近6月/近1年"
            f"的涨跌幅、区间收益、相对大盘表现"
        ),
        "financials": (
            f"股票代码{stock_code}的最新财务数据，包括营业收入、净利润、扣非净利润、"
            f"ROE净资产收益率、毛利率、净利率、资产负债率、经营现金流、每股收益"
        ),
        "shareholders": (
            f"股票代码{stock_code}的股东结构，包括前十大股东、十大流通股东、"
            f"股东户数、机构持股比例、户均持股"
        ),
        "risk": (
            f"股票代码{stock_code}的风险指标，包括波动率、贝塔系数、"
            f"最大回撤、夏普比率、VaR风险价值"
        ),
        "esg": (
            f"股票代码{stock_code}的ESG评级数据，包括环境E、社会责任S、"
            f"公司治理G三个维度的评分和评级"
        ),
        "events": (
            f"股票代码{stock_code}的重大事件，包括分红送转、增发配股、"
            f"高管增减持、业绩预告、资本运作"
        ),
        "news": f"{stock_code} 近期新闻",
        "notices": f"{stock_code} 近期公告",
    }

    return {"query": queries.get(key, f"{stock_code}")}


def _market_suffix(stock_code: str) -> str:
    """根据股票代码判断交易所后缀"""
    if stock_code.startswith(("60", "68")):
        return ".SH"
    elif stock_code.startswith(("00", "30", "002", "003")):
        return ".SZ"
    elif stock_code.startswith(("8", "4")):
        return ".BJ"
    return ".SH"


def _format_sse(event_type: str, data: dict) -> str:
    """格式化为 SSE 消息"""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ═══════════════════════════════════════════
# 表格 → 客观陈述文章转换器
# ═══════════════════════════════════════════

def _clean_header(h: str) -> str:
    """清洗表头：去除单位括号"""
    import re as _re
    h = str(h).strip()
    h = _re.sub(r'[（(]单位[：:][^)）]*[)）]', '', h)
    return h


def _parse_tsv_sections(text: str) -> list[dict]:
    """从 answer 文本中解析 TSV 表格区域

    返回: [{"title": "区域标题", "headers": [...], "rows": [[...], ...]}, ...]
    没有表格时返回空列表
    """
    lines = text.strip().split('\n')
    sections = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if '\t' not in line:
            # 标题行——后续跟 TSV 表
            title = line
            i += 1
            header_line = None
            data_lines = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    break
                if '\t' in cur:
                    if header_line is None:
                        header_line = cur
                    else:
                        data_lines.append(cur)
                else:
                    break  # 下一个标题
                i += 1
            if header_line:
                sections.append({
                    'title': title,
                    'headers': [_clean_header(h) for h in header_line.split('\t')],
                    'rows': [[c.strip() for c in r.split('\t')] for r in data_lines],
                })
        else:
            # 无标题表格
            header_line = line
            i += 1
            data_lines = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    break
                if '\t' in cur:
                    data_lines.append(cur)
                else:
                    break
                i += 1
            sections.append({
                'title': '',
                'headers': [_clean_header(h) for h in header_line.split('\t')],
                'rows': [[c.strip() for c in r.split('\t')] for r in data_lines],
            })
    return sections


def _table_rows_to_prose(headers: list, rows: list, title: str = '') -> str:
    """将单个表格（表头+行数据）转为客观陈述段落。

    - 单行表 → 一段逗号连接的陈述句
    - 多行表（如财务多季度）→ 每行一段，首列作前缀
    """
    if not rows:
        return "暂无数据。"

    # 过滤全空列
    valid_cols = []
    for ci, h in enumerate(headers):
        has_val = any(
            str(rows[ri][ci]).strip() not in ('', '--', '-', 'None')
            for ri in range(len(rows))
            if ci < len(rows[ri])
        )
        if has_val:
            valid_cols.append(ci)

    if not valid_cols:
        return "暂无有效数据。"

    if len(rows) == 1:
        # 单行 → 一句综述
        parts = []
        for ci in valid_cols:
            h = headers[ci]
            v = str(rows[0][ci]).strip() if ci < len(rows[0]) else ''
            if v and v != '--':
                parts.append(f"{h}{v}")
        result = "，".join(parts) + "。"
        if title:
            result = f"{title}：{result}"
        return result

    # 多行 → 每行一段
    paragraphs = []
    for row in rows:
        key_val = str(row[0]).strip() if row else ''
        parts = []
        # 跳过首列（用作前缀），如果 valid_cols 不包含首列则保留
        start = 1 if 0 in valid_cols else 0
        for ci in valid_cols:
            if ci == 0 and start == 1:
                continue
            h = headers[ci]
            v = str(row[ci]).strip() if ci < len(row) else ''
            if v and v != '--':
                parts.append(f"{h}{v}")
        line = "，".join(parts) + "。"
        if key_val:
            line = f"{key_val}：{line}"
        paragraphs.append(line)
    result = "\n".join(paragraphs)
    if title:
        result = f"【{title}】\n{result}"
    return result


def _format_news_prose(articles: list) -> str:
    """将新闻/公告列表格式化为散文段落"""
    if not articles:
        return "暂无相关信息。"

    lines = []
    for i, a in enumerate(articles, 1):
        if isinstance(a, dict):
            title = a.get("资讯标题") or a.get("公告标题") or a.get("title", "无标题")
            date = a.get("日期") or a.get("date", "")
            content = a.get("资讯内容") or a.get("公告片段内容") or a.get("content", "")
            # 截取前 200 字
            if len(content) > 200:
                content = content[:200] + "……"
            date_str = f"（{date}）" if date else ""
            lines.append(f"{i}. {title}{date_str}：{content}")
        else:
            lines.append(f"{i}. {a}")
    return "\n\n".join(lines)


def _raw_to_prose(raw, dim_key: str = '') -> str:
    """主入口：将 extract_raw() 返回的结构化数据转为客观陈述文章

    Args:
        raw: extract_raw() 的返回值
        dim_key: 维度 key，用于微调输出格式

    Returns:
        中文散文段落字符串
    """
    if raw is None:
        return "⚠️ 数据获取失败。"

    typ = raw.get("type", "text")

    if typ == "table":
        tables = raw.get("tables", [])
        if not tables or len(tables) < 2:
            return "暂无数据。"
        headers = [str(h).strip() for h in tables[0]]
        rows = tables[1:]
        return _table_rows_to_prose(headers, rows)

    if typ == "news":
        return _format_news_prose(raw.get("articles", []))

    if typ == "answer":
        answer_text = raw.get("text", "")
        # 尝试解析内嵌 TSV 表格
        sections = _parse_tsv_sections(answer_text)
        if sections:
            parts = []
            for sec in sections:
                title = sec['title']
                headers = sec['headers']
                rows = sec['rows']
                parts.append(_table_rows_to_prose(headers, rows, title))
            return "\n\n".join(parts)
        # 无表格 → 直接返回文本
        return answer_text.strip()

    # 兜底：text / json → 直接返回
    if typ == "json":
        data = raw.get("data", {})
        return json.dumps(data, ensure_ascii=False, indent=2)
    return raw.get("text", "暂无数据。")


# ═══════════════════════════════════════════
# 辅助函数：从 summary 维度提取公司全称
# ═══════════════════════════════════════════

def _extract_stock_name(raw, stock_code: str) -> str:
    """从 summary 维度（基本信息与估值）的 raw 数据中提取公司全称

    iFinD 的 get_stock_summary 返回自然语言文本，其中包含"公司全称：XXX"。
    此函数用正则提取公司全称，提取失败则 fallback 到 stock_code。
    """
    if raw is None:
        return stock_code
    if raw.get("type") != "answer":
        return stock_code
    text = raw.get("text", "")
    if not text:
        return stock_code

    # 按优先级尝试多种模式（非贪婪，遇到分隔符即停）
    patterns = [
        r'公司全称[：:]\s*(.+?)[，,。\n]',
        r'公司名称[：:]\s*(.+?)[，,。\n]',
        r'全\s*称[：:]\s*(.+?)[，,。\n]',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            name = m.group(1).strip()
            if name and len(name) >= 2 and name != stock_code:
                return name

    return stock_code


# ═══════════════════════════════════════════
# 异步版：SSE 流式生成器（FastAPI StreamingResponse 用）
# ═══════════════════════════════════════════

async def generate_report_stream(stock_code: str, dimensions: list[str] | None = None):
    """异步生成综合数据报告，yield SSE 事件

    Args:
        stock_code: 股票代码
        dimensions: 可选，指定要采集的维度 key 列表；传 None 则采集全部 10 个维度

    complete 事件包含：
      - report: 完整 Markdown（保留供投研报告使用）
      - sections: {dim_key: prose_text, ...}  各维度客观陈述文章
    """
    report_parts = []
    raws = {}          # dim_key → extract_raw() 结果
    has_critical_failure = False
    loop = asyncio.get_running_loop()

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in DIMENSIONS if dimensions is None or d["key"] in dimensions]
    total = len(active_dims)

    yield _format_sse("start", {"stock_code": stock_code, "total": total})

    for i, dim in enumerate(active_dims):
        yield _format_sse("progress", {
            "stage": dim["key"],
            "label": dim["label"],
            "status": "running",
            "current": i + 1,
            "total": total,
        })

        try:
            params = _build_params(dim, stock_code)
            result = await loop.run_in_executor(
                None, call_skill, dim["server"], dim["tool"], params,
            )
            text = extract_text(result)
            raw = extract_raw(result)

            if text.startswith("[错误]") or text.startswith("[无数据]") or text.startswith("[权限不足"):
                raise RuntimeError(text)

            report_parts.append(f"## {dim['label']}\n\n{text}")
            raws[dim["key"]] = raw

            yield _format_sse("progress", {
                "stage": dim["key"],
                "label": dim["label"],
                "status": "done",
                "current": i + 1,
                "total": total,
            })

        except Exception as e:
            error_msg = str(e)
            if dim["critical"]:
                has_critical_failure = True

            report_parts.append(
                f"## {dim['label']}\n\n> ⚠️ 数据获取失败：{error_msg}"
            )
            raws[dim["key"]] = None

            yield _format_sse("progress", {
                "stage": dim["key"],
                "label": dim["label"],
                "status": "error",
                "error": error_msg,
                "current": i + 1,
                "total": total,
            })

        # 维度间限速（最后一项不延迟）
        if i < total - 1:
            await asyncio.sleep(RATE_LIMIT_INTERVAL)

    # 组装完整 Markdown 报告（保留，供投研报告使用）
    stock_name = _extract_stock_name(raws.get("summary"), stock_code)
    header = f"# {stock_name}（{stock_code}）综合数据报告\n\n"
    header += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    if has_critical_failure:
        header += "> ⚠️ **注意**：关键数据维度获取失败，报告可能不完整。\n\n"
    header += "---\n\n"
    full_markdown = header + "\n\n".join(report_parts)

    # 构建 sections：每维度独立客观陈述文章
    sections = {}
    for dim in active_dims:
        raw = raws.get(dim["key"])
        sections[dim["key"]] = _raw_to_prose(raw, dim["key"])

    yield _format_sse("complete", {
        "report": full_markdown,
        "sections": sections,
        "stock_name": stock_name,
        "has_critical_failure": has_critical_failure,
    })


# ═══════════════════════════════════════════
# 同步版：后台线程直接调用（analyze / trigger 内部用）
# ═══════════════════════════════════════════

def generate_report_sync(stock_code: str, dimensions: list[str] | None = None) -> dict:
    """同步生成综合数据报告

    用于后台线程（_run_analysis / _run_watchlist_analyze）。

    Args:
        stock_code: 股票代码
        dimensions: 可选，指定要采集的维度 key 列表；传 None 则采集全部 10 个维度

    Returns:
        {"markdown": str, "stock_name": str, "sections": {dim_key: prose, ...}}
    """
    parts = []
    raws = {}
    has_critical_failure = False

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in DIMENSIONS if dimensions is None or d["key"] in dimensions]

    for i, dim in enumerate(active_dims):
        try:
            params = _build_params(dim, stock_code)
            result = call_skill(dim["server"], dim["tool"], params)
            text = extract_text(result)
            raw = extract_raw(result)

            if text.startswith("[错误]") or text.startswith("[无数据]") or text.startswith("[权限不足"):
                raise RuntimeError(text)

            parts.append(f"## {dim['label']}\n\n{text}")
            raws[dim["key"]] = raw

        except Exception as e:
            if dim["critical"]:
                has_critical_failure = True
            parts.append(f"## {dim['label']}\n\n> ⚠️ 数据获取失败：{e}")
            raws[dim["key"]] = None

        # 限速
        if i < len(active_dims) - 1:
            time.sleep(RATE_LIMIT_INTERVAL)

    # 从 summary 维度中提取公司全称
    stock_name = _extract_stock_name(raws.get("summary"), stock_code)

    header = f"# {stock_name}（{stock_code}）综合数据报告\n\n"
    header += f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    if has_critical_failure:
        header += "> ⚠️ **注意**：关键数据维度获取失败，报告可能不完整。\n\n"
    header += "---\n\n"

    # 构建 sections
    sections = {}
    for dim in active_dims:
        raw = raws.get(dim["key"])
        sections[dim["key"]] = _raw_to_prose(raw, dim["key"])

    return {
        "markdown": header + "\n\n".join(parts),
        "stock_name": stock_name,
        "sections": sections,
    }
