"""东方财富免费 HTTP API — 数据源

提供：
  - _get_name_eastmoney()   — 公司名称查询（iFinD 兜底）
  - _fetch_ohlcv_eastmoney() — 日K线 OHLCV 数据（前复权，与同花顺 APP 一致）

两个接口均免费、无需注册、无 QPS 限制。
"""

import requests


def _get_name_eastmoney(stock_code: str) -> str | None:
    """东方财富 HTTP 直调查询公司名称，A股+港股通用

    作为 iFinD 正则提取失败时的兜底方案。
    secid 规则：沪市 1.{code}，深市 0.{code}，港股 116.{zfill(5)}
    """
    code = stock_code.strip()
    # 港股 secid：116. + 零填充到5位
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        if not pure:  # 守卫：纯后缀输入（如 ".HK"）
            return None
        secid = f"116.{pure.zfill(5)}"
    else:
        # A股：清掉 .SH/.SZ 后缀，按首字判断市场
        pure = code.replace(".SH", "").replace(".SZ", "")
        if not pure:  # 守卫：空代码或纯后缀（如 ".SH"），避免 pure[0] IndexError
            return None
        market = "1" if pure[0] in ("6", "5") else "0"
        secid = f"{market}.{pure}"

    # 收窄异常：网络错误 / JSON 解析 / 字段缺失分别对应明确类型，不再裸吞 Exception
    try:
        r = requests.get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            params={"fltt": "2", "invt": "2", "fields": "f57,f58", "secid": secid},
            timeout=5,
        )
        data = r.json()
        name = (data.get("data") or {}).get("f58", "")  # data 字段可能为 None
        if name and len(name) >= 2:
            return name
    except (requests.RequestException, ValueError, KeyError, TypeError):
        # ValueError 覆盖 JSONDecodeError；TypeError/KeyError 覆盖响应结构异常
        pass
    return None


def _fetch_ohlcv_eastmoney(stock_code: str) -> dict | None:
    """从东方财富免费 HTTP API 获取日K线 OHLCV 数据（前复权）

    支持 A 股（.SH/.SZ）和港股（.HK），返回与 _parse_ohlcv_table() 同结构的 dict。
    数据按时间升序排列（最早日期在前），与同花顺 APP 日K 数据一致。

    Returns:
        {"dates": [...], "closes": [...], "highs": [...], "lows": [...],
         "change_pcts": [...], "turnovers": [...]}
        失败返回 None
    """
    code = stock_code.strip()

    # 构造东财 secid：港股 116.{zfill(5)}，沪市 1.{code}，深市 0.{code}
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        if not pure:
            return None
        secid = f"116.{pure.zfill(5)}"
    else:
        pure = code.replace(".SH", "").replace(".SZ", "")
        if not pure:  # 守卫：空代码或纯后缀，避免 pure[0] IndexError
            return None
        market = "1" if pure[0] in ("6", "5") else "0"
        secid = f"{market}.{pure}"

    try:
        r = requests.get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            params={
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",       # 日K
                "fqt": "1",         # 前复权
                "end": "20500101",
                "lmt": "70",        # 取70条保证覆盖60个交易日
            },
            timeout=10,
        )
        data = r.json()
        klines = (data.get("data") or {}).get("klines")  # data 字段可能为 None
        if not klines:
            return None

        # 解析 K 线字符串：日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
        dates, closes, highs, lows, change_pcts, turnovers = [], [], [], [], [], []
        for k in klines:
            parts = k.split(",")
            if len(parts) < 11:
                continue
            dates.append(parts[0].replace("-", ""))  # 2026-07-17 → 20260717
            closes.append(float(parts[2]))
            highs.append(float(parts[3]))
            lows.append(float(parts[4]))
            change_pcts.append(float(parts[8]))
            turnovers.append(float(parts[10]))

        if len(closes) < 5:
            return None

        # 东财数据已是时间升序（最早在前），无需反转
        return {
            "dates": dates,
            "closes": closes,
            "highs": highs,
            "lows": lows,
            "change_pcts": change_pcts,
            "turnovers": turnovers,
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None
