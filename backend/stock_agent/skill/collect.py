"""SKILL 采集编排 — 维度配置、参数构建与单维度采集重试"""
import time
from datetime import datetime, timedelta

from ..datasources.eastmoney import (
    _get_name_eastmoney, _get_name_tencent,
)
from . import call_skill, extract_text, extract_raw
from .format import _market_suffix


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
    故先查简称：东财 → 腾讯（备份，东财对本机 IP 间歇性限速）→ 都失败
    则降级回代码格式（等同旧行为，不崩溃）。
    """
    shortname = _get_name_eastmoney(stock_code) or _get_name_tencent(stock_code)
    subject = shortname if shortname else f"股票代码{stock_code}"
    # 只写 iFinD 认识的具体指标（"估值水平"等模糊措辞会触发其"部分不识别→整体标错误"）
    return (
        f"{subject}的基本信息，包括公司全称、所属行业、上市日期、"
        f"总市值、流通市值、市盈率PE、市净率PB、市销率PS"
    )


def _strip_error_prefix(text: str) -> str:
    """剥离 SKILL 响应的错误前缀，返回正文"""
    if text.startswith("[错误]"):
        return text[4:].strip()
    if text.startswith("[无数据]"):
        return text[5:].strip()  # [无数据] 为 5 字符，[4:] 会残留 ']'
    if text.startswith("[权限不足"):
        return text.split("]", 1)[-1].strip() if "]" in text else text[5:].strip()
    return text


def _call_dim_with_retry(dim: dict, stock_code: str, max_attempts: int = 2):
    """单维度采集（含重试）：iFinD 会间歇性拒绝/限速，失败等 1 秒重试

    假错误容错：iFinD 偶发"标错误但返回数据"（query 含其不认识的指标时，
    已认识的部分照常返回、整体标 [错误]）——前缀带数据表格时剥离前缀按成功处理。

    Returns (text, raw)；最终失败抛 RuntimeError（携带最后一次错误信息）。
    """
    params = _build_params(dim, stock_code)
    last_err = None
    for attempt in range(max_attempts):
        result = call_skill(dim["server"], dim["tool"], params)
        text = extract_text(result)
        if not (text.startswith("[错误]") or text.startswith("[无数据]") or text.startswith("[权限不足")):
            return text, extract_raw(result)
        # 假错误判定：剥前缀后有实质内容（含表格且够长）→ 视为数据送达
        body = _strip_error_prefix(text)
        if "|" in body and len(body) > 100:
            return body, extract_raw(result)
        last_err = text
        if attempt < max_attempts - 1:
            time.sleep(1.0)
    raise RuntimeError(last_err)


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
