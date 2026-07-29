"""技术指标计算（纯数学，零网络依赖）

基于 OHLCV 原始数据（来源不限：东方财富 / iFinD 均可），
自行推算 MA/MACD/BOLL/RSI/KDJ，绕开外部数据源不拆分子指标的局限。

仅依赖 Python 标准库 math，无需额外安装。
"""

import math


def _calc_ema(data: list, period: int) -> list:
    """计算指数移动平均（EMA），返回与输入等长的列表，首段不足时为 None

    输入契约：data 不允许含 None（当前东财/iFinD 两个数据源均满足）。
    """
    if len(data) < period:
        return [None] * len(data)
    k = 2.0 / (period + 1)
    result = [None] * len(data)
    result[period - 1] = sum(data[:period]) / period
    for i in range(period, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def _calc_ma(data: list, period: int) -> list:
    """计算简单移动平均（MA），返回与输入等长的列表

    窗口内 None 值被跳过，按有效值取平均；窗口全 None 则该点为 None。
    """
    if len(data) < period:
        return [None] * len(data)
    result = [None] * len(data)
    for i in range(period - 1, len(data)):
        window = [x for x in data[i - period + 1:i + 1] if x is not None]
        if window:
            result[i] = sum(window) / len(window)
    return result


def _calc_macd(closes: list) -> dict:
    """计算 MACD 指标（标准参数 12/26/9）

    输入契约：closes 不允许含 None，经由 _calc_ema 继承该契约。

    Returns:
        {'dif': [...], 'dea': [...], 'bar': [...]}  # bar = 2*(DIF-DEA)
    """
    ema12 = _calc_ema(closes, 12)
    ema26 = _calc_ema(closes, 26)

    # DIF = EMA12 - EMA26
    dif = [None] * len(closes)
    dif_start = None
    for i in range(len(closes)):
        if ema12[i] is not None and ema26[i] is not None:
            dif[i] = ema12[i] - ema26[i]
            if dif_start is None:
                dif_start = i

    if dif_start is None:
        return {'dif': dif, 'dea': [None] * len(closes), 'bar': [None] * len(closes)}

    # DEA = 9-period EMA of DIF
    dif_valid = dif[dif_start:]
    dea_valid = _calc_ema(dif_valid, 9)
    dea = [None] * len(closes)
    for j, di in enumerate(range(dif_start, len(closes))):
        dea[di] = dea_valid[j]

    # BAR = 2 * (DIF - DEA)
    bar = [None] * len(closes)
    for i in range(len(closes)):
        if dif[i] is not None and dea[i] is not None:
            bar[i] = 2.0 * (dif[i] - dea[i])

    return {'dif': dif, 'dea': dea, 'bar': bar}


def _calc_boll(closes: list, period: int = 20, multiplier: float = 2.0) -> dict:
    """计算 BOLL 布林线

    Returns:
        {'upper': [...], 'middle': [...], 'lower': [...]}
    窗口内 None 值跳过；有效值不足 2 个时该点三轨为 None。
    """
    middle = _calc_ma(closes, period)
    upper = [None] * len(closes)
    lower = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        mean = middle[i]
        if mean is None:
            continue
        window = [x for x in closes[i - period + 1:i + 1] if x is not None]
        if len(window) < 2:
            continue
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = math.sqrt(variance)
        upper[i] = mean + multiplier * std
        lower[i] = mean - multiplier * std

    return {'upper': upper, 'middle': middle, 'lower': lower}


def _calc_rsi(closes: list, period: int = 14) -> list:
    """计算 RSI（Wilder's smoothing），返回与输入等长的列表

    输入契约：closes 不允许含 None（当前东财/iFinD 两个数据源均满足）。
    """
    if len(closes) < period + 1:
        return [None] * len(closes)

    result = [None] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(delta if delta > 0 else 0.0)
        losses.append(-delta if delta < 0 else 0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = 100.0 if avg_loss == 0 else (100.0 - 100.0 / (1.0 + avg_gain / avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            result[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return result


def _calc_kdj(highs: list, lows: list, closes: list, n: int = 9) -> dict:
    """计算 KDJ 指标

    需要 highs/lows 不含 None；如果有 None 则回退到用 close 近似。
    Returns:
        {'k': [...], 'd': [...], 'j': [...]}
    """
    length = len(closes)
    k_vals = [None] * length
    d_vals = [None] * length
    j_vals = [None] * length

    if length < n:
        return {'k': k_vals, 'd': d_vals, 'j': j_vals}

    # 初始 K/D = 50
    k_prev, d_prev = 50.0, 50.0
    for i in range(n - 1, length):
        # 窗口内的最高/最低（highs/lows 含 None 时回退用 close 近似）
        win_high = max((highs[j] if highs[j] is not None else closes[j]) for j in range(i - n + 1, i + 1))
        win_low = min((lows[j] if lows[j] is not None else closes[j]) for j in range(i - n + 1, i + 1))
        if win_high == win_low:
            rsv = 50.0
        else:
            rsv = (closes[i] - win_low) / (win_high - win_low) * 100.0

        if i == n - 1:
            k_vals[i] = 50.0
            d_vals[i] = 50.0
        else:
            k_vals[i] = 2.0 / 3.0 * k_prev + 1.0 / 3.0 * rsv
            d_vals[i] = 2.0 / 3.0 * d_prev + 1.0 / 3.0 * k_vals[i]
        j_vals[i] = 3.0 * k_vals[i] - 2.0 * d_vals[i]
        k_prev, d_prev = k_vals[i], d_vals[i]

    return {'k': k_vals, 'd': d_vals, 'j': j_vals}


def _last_valid(seq: list) -> float | None:
    """返回序列最后一个非 None 值"""
    for v in reversed(seq):
        if v is not None:
            return v
    return None
