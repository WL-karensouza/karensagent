"""SKILL 响应解析 — TSV/表格/新闻/公司名提取"""
import json
import re

from ..datasources.eastmoney import (
    _get_name_eastmoney, _get_name_tencent,
)


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
    # iFinD 表格的公司名列有多种写法（A股新表为"公司证券全称"），都要认
    name_cols = ("公司中文名称", "公司全称", "公司证券全称")
    lines = [ln.strip() for ln in text.splitlines()]
    fallback = None
    for i, ln in enumerate(lines):
        if not ln.startswith("|"):
            continue
        headers = [c.strip() for c in ln.strip("|").split("|")]
        if not any(h in (*name_cols, "证券简称") for h in headers):
            continue
        # 表头行之后跳过分隔行，取第一条数据行
        for data_ln in lines[i + 1:]:
            if not data_ln.startswith("|"):
                break
            cells = [c.strip() for c in data_ln.strip("|").split("|")]
            if all(c.replace("-", "").replace(":", "") == "" for c in cells):
                continue  # |---|---| 分隔行
            row = dict(zip(headers, cells))
            for col in name_cols:
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
    # iFinD 假错误（标[无数据]但返回数据）时 extract_raw 会降级为 type=text，
    # 必须同样尝试提取，否则中文名称丢失（2026-08-04 实证根因）
    if raw.get("type") not in ("answer", "text"):
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

    # 以上全部失败 → 名称三重保险：东财 → 腾讯 → 代码本身
    fallback = _get_name_eastmoney(stock_code)
    if fallback:
        return fallback
    fallback = _get_name_tencent(stock_code)
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
