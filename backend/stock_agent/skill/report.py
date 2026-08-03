"""SKILL 报告编排器

10 维度串行调度、SSE 进度推送、Markdown 汇总。
"""
import asyncio
import json
import re

from ..datasources.eastmoney import _get_name_eastmoney, _fetch_ohlcv_eastmoney
from .indicators import (
    _calc_ema, _calc_ma, _calc_macd, _calc_boll, _calc_rsi, _calc_kdj,
    _last_valid,
)
import time
from datetime import datetime, timedelta
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

# 港股维度定义（global_stock 服务，key 尽量与 A 股对齐以兼容前端维度选择）
# ESG 事件类数据由 global_stock_events 覆盖，故并入 events 维度
HK_DIMENSIONS = [
    {"key": "summary",     "label": "基本信息",       "server": "global_stock", "tool": "global_stock_profile",   "critical": True,
     "query_tpl": "港股{code}的公司全称、公司中文名称、所属行业、上市日期、总股本、主营业务"},
    {"key": "quotes",      "label": "行情表现",       "server": "global_stock", "tool": "global_stock_quotes",    "critical": True,
     "query_tpl": "港股{code}的最新收盘价、涨跌幅、总市值、换手率、成交额"},
    {"key": "performance", "label": "近期行情走势",    "server": "global_stock", "tool": "global_stock_quotes",    "critical": False,
     "query_tpl": "港股{code}的近1月、近3月、近6月涨跌幅和年涨跌幅"},
    {"key": "financials",  "label": "财务数据",       "server": "global_stock", "tool": "global_stock_financial", "critical": False,
     "query_tpl": "港股{code}的最新营业收入、净利润、毛利率、资产负债率、每股收益"},
    {"key": "valuation",   "label": "估值水平",       "server": "global_stock", "tool": "global_stock_financial", "critical": False,
     "query_tpl": "港股{code}的市盈率PE、市净率PB、市销率PS、盈利预测"},
    {"key": "shareholders","label": "股东结构",       "server": "global_stock", "tool": "global_stock_profile",   "critical": False,
     "query_tpl": "港股{code}的主要股东及持股比例、机构持股"},
    {"key": "risk",        "label": "风险评估",       "server": "global_stock", "tool": "global_stock_quotes",    "critical": False,
     "query_tpl": "港股{code}的贝塔系数、年化波动率、夏普比率、最大回撤"},
    {"key": "events",      "label": "重大事件与ESG",   "server": "global_stock", "tool": "global_stock_events",    "critical": False,
     "query_tpl": "港股{code}的IPO发行价、募资金额、分红、回购、ESG评级"},
    {"key": "news",        "label": "近期新闻",       "server": "news",  "tool": "search_news",   "critical": False,
     "query_tpl": "{code} 近期新闻"},
    {"key": "notices",     "label": "公司公告",       "server": "news",  "tool": "search_notice", "critical": False,
     "query_tpl": "{code} 近期公告"},
]

# 限速间隔（秒）：免费版 2 QPS，串行 10 维度约 20-30 秒
RATE_LIMIT_INTERVAL = 0.6


def _dimensions_for(stock_code: str) -> list[dict]:
    """按市场选择维度表：港股走 global_stock，其余走 A 股 stock"""
    return HK_DIMENSIONS if stock_code.endswith(".HK") else DIMENSIONS


def _news_time_params(dim_key: str) -> dict:
    """news 服务必填的时间范围参数：新闻查近 90 天，公告查近 180 天"""
    today = datetime.now()
    days = 180 if dim_key == "notices" else 90
    return {
        "time_start": (today - timedelta(days=days)).strftime("%Y-%m-%d"),
        "time_end": today.strftime("%Y-%m-%d"),
        "size": 5 if dim_key == "notices" else 8,
    }


def _resolve_summary_query(stock_code: str) -> str:
    """构建 summary 维度查询：iFinD 的 get_stock_summary 只认股票简称

    「股票代码XXXXXX」格式会被服务端拒绝（"未识别到有效的A股股票代码"），
    故先经东财查简称；查不到则降级回代码格式（等同旧行为，不崩溃）。
    """
    shortname = _get_name_eastmoney(stock_code)
    subject = shortname if shortname else f"股票代码{stock_code}"
    return (
        f"{subject}的基本信息，包括公司全称、所属行业、上市日期、"
        f"总市值、流通市值、市盈率PE、市净率PB、估值水平"
    )


def _build_params(dim: dict, stock_code: str) -> dict:
    """根据维度配置和股票代码构建 SKILL 调用参数"""
    # 带查询模板的维度（港股）直接格式化
    if "query_tpl" in dim:
        params = {"query": dim["query_tpl"].format(code=stock_code)}
        if dim["server"] == "news":
            params.update(_news_time_params(dim["key"]))
        return params

    key = dim["key"]
    tool = dim["tool"]

    # 实时行情使用结构化参数（iFinD v1.3.0: data_mode 仅支持 real_time/highfreq）
    if tool == "stock_highfreq_quotes":
        suffix = _market_suffix(stock_code)
        return {
            "symbols": f"{stock_code}{suffix}",
            "indicators": "最新价,开盘价,最高价,最低价,收盘价,涨跌幅,成交量,成交额,振幅,均价",
            "data_mode": "real_time",
        }

    # 自然语言类工具 — 构造中文 query
    queries = {
        # summary 走简称解析（iFinD 只认简称，见 _resolve_summary_query）
        "summary": _resolve_summary_query(stock_code),
        "performance": (
            f"{stock_code}{_market_suffix(stock_code)}近60个交易日的开盘价、收盘价、最高价、最低价、"
            f"涨跌幅、换手率、成交量、成交额"
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

    params = {"query": queries.get(key, f"{stock_code}")}
    if dim["server"] == "news":
        params.update(_news_time_params(key))
    return params


def normalize_stock_code(stock_code: str) -> str:
    """归一化股票代码：港股各种写法统一为 xxxx.HK，其余原样返回

    HK2513 / hk2513 / 2513.hk → 2513.HK；600519 等 A 股代码不变。
    """
    s = stock_code.strip()
    m = re.fullmatch(r"[Hh][Kk](\d{1,5})", s)
    if m:
        return f"{m.group(1)}.HK"
    if re.fullmatch(r"\d{1,5}\.[Hh][Kk]", s):
        return s.upper()
    return s


def _market_suffix(stock_code: str) -> str:
    """根据股票代码判断交易所后缀（仅 A 股；港股走 global_stock 服务不拼后缀）"""
    if stock_code.endswith(".HK"):
        # 港股维度用 query_tpl 分支，从不需要后缀；误调用时快速失败，
        # 防止静默拼出 "2513.HK.SH" 这类错误代码
        raise ValueError(f"港股代码 {stock_code} 不应走 A 股后缀逻辑（应用 global_stock 服务）")
    if stock_code.startswith(("60", "68")):
        return ".SH"
    elif stock_code.startswith(("00", "30")):  # 002/003 前缀已被 00 覆盖
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
    h = str(h).strip()
    h = re.sub(r'[（(]单位[：:][^)）]*[)）]', '', h)  # 复用模块级 re（第 7 行已导入）
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

def _name_from_pipe_table(text: str) -> str | None:
    """从 Markdown 管道表格中提取公司名（港股 global_stock_profile 返回表格应答）

    优先取"公司中文名称/公司全称"列，其次"证券简称"列。
    """
    lines = [ln.strip() for ln in text.splitlines()]
    fallback = None
    for i, ln in enumerate(lines):
        if not ln.startswith("|"):
            continue
        headers = [c.strip() for c in ln.strip("|").split("|")]
        if not any(h in ("公司中文名称", "公司全称", "证券简称") for h in headers):
            continue
        # 表头行之后跳过分隔行，取第一条数据行
        for data_ln in lines[i + 1:]:
            if not data_ln.startswith("|"):
                break
            cells = [c.strip() for c in data_ln.strip("|").split("|")]
            if all(c.replace("-", "").replace(":", "") == "" for c in cells):
                continue  # |---|---| 分隔行
            row = dict(zip(headers, cells))
            for col in ("公司中文名称", "公司全称"):
                v = row.get(col, "")
                if v and len(v) >= 2:
                    return v
            v = row.get("证券简称", "")
            if v and len(v) >= 2 and fallback is None:
                fallback = v
            break
    return fallback


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

    # 正则未命中 → 尝试从表格应答提取（港股 profile 为表格格式）
    name = _name_from_pipe_table(text)
    if name and name != stock_code:
        return name

    # 以上全部失败 → 东方财富 HTTP 兜底
    fallback = _get_name_eastmoney(stock_code)
    if fallback:
        return fallback

    return stock_code


# ═══════════════════════════════════════════
# iFinD OHLCV 表格解析（兜底方案，东方财富获取失败时使用）
# ═══════════════════════════════════════════

def _parse_ohlcv_table(answer_text: str) -> dict | None:
    """从 get_stock_performance 返回的 Markdown 管道表格中解析 OHLCV 数据

    返回按时间升序排列的 dict（最早日期在前），格式：
        {"dates": [...], "closes": [...], "highs": [...], "lows": [...],
         "change_pcts": [...], "turnovers": [...]}
    解析失败返回 None
    """
    lines = answer_text.strip().split('\n')

    # 找表头行
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith('|') and '证券代码' in line:
            header_idx = i
            break
    if header_idx is None:
        return None

    headers = [h.strip() for h in lines[header_idx].strip('|').split('|')]
    col_map = {}
    for idx, h in enumerate(headers):
        h_clean = h.replace('（', '(').replace('）', ')')
        if '日期' in h:
            col_map['date'] = idx
        elif '开盘' in h:
            col_map['open'] = idx
        elif '收盘' in h:
            col_map['close'] = idx
        elif '最高' in h:
            col_map['high'] = idx
        elif '最低' in h:
            col_map['low'] = idx
        elif '涨跌幅' in h:
            col_map['change_pct'] = idx
        elif '换手率' in h:
            col_map['turnover'] = idx

    if 'close' not in col_map:
        return None

    # 解析数据行（从底向上保证升序）
    rows = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line.startswith('|') or '---|---' in line:
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]

        def _cell(key):
            idx = col_map.get(key)
            if idx is None or idx >= len(cells):
                return ''
            return cells[idx]

        # 过滤 iFinD 末尾的统计汇总行（无日期列或日期不是日期格式）
        date_str = _cell('date')
        if not date_str or not re.fullmatch(r'\d{8}', date_str):
            continue

        try:
            close_val = float(_cell('close'))
        except (ValueError, TypeError):
            continue

        row = {'date': date_str, 'close': close_val}
        for key in ('open', 'high', 'low'):
            try:
                row[key] = float(_cell(key)) if _cell(key) else None
            except (ValueError, TypeError):
                row[key] = None
        for key in ('change_pct', 'turnover'):
            try:
                row[key] = float(_cell(key)) if _cell(key) else None
            except (ValueError, TypeError):
                row[key] = None
        rows.append(row)

    if len(rows) < 5:
        return None

    # iFinD 返回的数据是倒序（最新在前），反转为升序（最早在前）
    rows.reverse()

    return {
        'dates': [r['date'] for r in rows],
        'closes': [r['close'] for r in rows],
        'highs': [r.get('high') for r in rows],
        'lows': [r.get('low') for r in rows],
        'change_pcts': [r.get('change_pct') for r in rows],
        'turnovers': [r.get('turnover') for r in rows],
    }


def _format_indicators_markdown(ohlcv: dict, indicators: dict, source: str = "iFinD") -> str:
    """将技术指标格式化为 Markdown 表格（标题标注自算 + OHLCV 数据源）"""
    latest_close = ohlcv['closes'][-1]
    lines = [f"### 技术指标（自算，数据源：{source}，截至最近交易日）", ""]

    # ── MA 均线 ──
    lines.append("#### MA 均线")
    lines.append("| 周期 | MA值 | 收盘价 | 偏离度 |")
    lines.append("|------|------|--------|--------|")
    for period, ma_seq in indicators['ma'].items():
        ma_val = _last_valid(ma_seq)
        if ma_val is not None:
            deviation = (latest_close - ma_val) / ma_val * 100
            lines.append(f"| MA{period} | {ma_val:.2f} | {latest_close:.2f} | {deviation:+.2f}% |")
    lines.append("")

    # ── MACD ──
    lines.append("#### MACD（12/26/9）")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for label, key in [('DIF', 'dif'), ('DEA', 'dea'), ('柱值（BAR）', 'bar')]:
        val = _last_valid(indicators['macd'][key])
        if val is not None:
            lines.append(f"| {label} | {val:.4f} |")
    lines.append("")

    # ── BOLL ──
    lines.append("#### BOLL 布林线（20日, 2σ）")
    lines.append("| 轨道 | 数值 |")
    lines.append("|------|------|")
    for label, key in [('上轨', 'upper'), ('中轨', 'middle'), ('下轨', 'lower')]:
        val = _last_valid(indicators['boll'][key])
        if val is not None:
            lines.append(f"| {label} | {val:.2f} |")
    # 带宽
    upper_v = _last_valid(indicators['boll']['upper'])
    lower_v = _last_valid(indicators['boll']['lower'])
    if upper_v is not None and lower_v is not None:
        lines.append(f"| 带宽（上-下） | {upper_v - lower_v:.2f} |")
    lines.append("")

    # ── RSI ──
    lines.append("#### RSI 相对强弱")
    lines.append("| 周期 | 数值 | 区域 |")
    lines.append("|------|------|------|")
    for period, rsi_seq in indicators['rsi'].items():
        val = _last_valid(rsi_seq)
        if val is not None:
            zone = "超买 ⚠️" if val > 70 else ("超卖 ⚠️" if val < 30 else "中性")
            lines.append(f"| RSI({period}) | {val:.2f} | {zone} |")
    lines.append("")

    # ── KDJ ──
    lines.append("#### KDJ 随机指标（9日）")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    for label, key in [('K', 'k'), ('D', 'd'), ('J', 'j')]:
        val = _last_valid(indicators['kdj'][key])
        if val is not None:
            zone = "超买 ⚠️" if val > 80 else ("超卖 ⚠️" if val < 20 else "中性")
            lines.append(f"| {label} | {val:.2f} | {zone} |")
    lines.append("")

    return "\n".join(lines)


def _enrich_performance(answer_text: str, stock_code: str = "") -> str:
    """解析 OHLCV 数据并计算技术指标，返回增强后的 Markdown

    优先使用东方财富前复权日K数据（与同花顺 APP 一致），
    失败时 fallback 到 iFinD Markdown 表格解析。
    两次尝试均失败时原样返回 answer_text，不中断报告生成。
    """
    ohlcv = None
    source = "iFinD"

    # 优先：东方财富免费 API（前复权，与同花顺 APP 日K 一致）
    if stock_code:
        ohlcv = _fetch_ohlcv_eastmoney(stock_code)
        if ohlcv is not None:
            source = "东方财富"

    # 兜底：从 iFinD 返回的 Markdown 表格解析
    if ohlcv is None:
        ohlcv = _parse_ohlcv_table(answer_text)

    if ohlcv is None:
        return answer_text

    closes = ohlcv['closes']
    highs = ohlcv['highs']
    lows = ohlcv['lows']

    # 计算全部技术指标
    indicators = {
        'ma': {
            5: _calc_ma(closes, 5),
            10: _calc_ma(closes, 10),
            20: _calc_ma(closes, 20),
            30: _calc_ma(closes, 30),
            60: _calc_ma(closes, 60),
        },
        'macd': _calc_macd(closes),
        'boll': _calc_boll(closes),
        'rsi': {
            6: _calc_rsi(closes, 6),
            12: _calc_rsi(closes, 12),
            24: _calc_rsi(closes, 24),
        },
        'kdj': _calc_kdj(highs, lows, closes),
    }

    indicator_md = _format_indicators_markdown(ohlcv, indicators, source)
    return answer_text + "\n\n" + indicator_md


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

    # 归一化代码并按市场选择维度表（港股走 global_stock）
    stock_code = normalize_stock_code(stock_code)
    all_dims = _dimensions_for(stock_code)

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in all_dims if dimensions is None or d["key"] in dimensions]
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

            # performance 维度：基于 OHLCV 自行计算全部技术指标
            # _enrich_performance 内含东财同步 HTTP，必须丢线程池避免阻塞事件循环
            if dim["key"] == "performance":
                text = await loop.run_in_executor(
                    None, _enrich_performance, text, stock_code
                )

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
    # _extract_stock_name 兜底走东财同步 HTTP，同样丢线程池
    stock_name = await loop.run_in_executor(
        None, _extract_stock_name, raws.get("summary"), stock_code
    )
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
        "stock_code": stock_code,
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
        {"markdown": str, "stock_code": str, "stock_name": str,
         "sections": {dim_key: prose, ...}, "has_critical_failure": bool}

        stock_code 为归一化后的代码（如 HK2513 → 2513.HK）；
        has_critical_failure 为 True 表示关键维度（实时行情/基本信息）失败，
        上层应据此硬终止（勿拿失败数据调 LLM）。
    """
    parts = []
    raws = {}
    has_critical_failure = False

    # 归一化代码并按市场选择维度表（港股走 global_stock）
    stock_code = normalize_stock_code(stock_code)
    all_dims = _dimensions_for(stock_code)

    # 如果指定了维度，只处理选中的维度
    active_dims = [d for d in all_dims if dimensions is None or d["key"] in dimensions]

    for i, dim in enumerate(active_dims):
        try:
            params = _build_params(dim, stock_code)
            result = call_skill(dim["server"], dim["tool"], params)
            text = extract_text(result)
            raw = extract_raw(result)

            if text.startswith("[错误]") or text.startswith("[无数据]") or text.startswith("[权限不足"):
                raise RuntimeError(text)

            # performance 维度：基于 OHLCV 自行计算全部技术指标
            if dim["key"] == "performance":
                text = _enrich_performance(text, stock_code)

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
        "stock_code": stock_code,
        "stock_name": stock_name,
        "sections": sections,
        "has_critical_failure": has_critical_failure,
    }
