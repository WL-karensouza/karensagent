"""SKILL 数据格式化 — 股票代码归一化、SSE 事件、技术指标 Markdown"""
import json
import re

from ..datasources.eastmoney import _fetch_ohlcv_eastmoney
from .indicators import (
    _calc_ema, _calc_ma, _calc_macd, _calc_boll, _calc_rsi, _calc_kdj,
    _last_valid,
)
from .parse import _parse_ohlcv_table


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
