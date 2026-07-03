"""
多数据源采集层
=============
核心网络库: curl_cffi（独立 TLS 栈，不读取 Windows 注册表代理）

K线数据优先级: 腾讯K线 API → akshare
实时行情优先级: 腾讯实时行情
资金流优先级: akshare（缺失时标注数据不足）
新闻优先级: akshare

返回统一的 dict 结构，下游 analyze() 无需关心数据来源。
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import random
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

# curl_cffi 核心优势: 不读 Windows 代理注册表，自带 TLS 指纹伪装
from curl_cffi import requests as http

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# 东方财富反爬补丁（Token获取用 requests，补丁为 akshare 准备）
# ═══════════════════════════════════════════════════════════

_UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

_nid_cache: dict = {"data": None, "expire_at": 0, "lock": threading.Lock(), "ttl": 20}
_patch_applied = False


def _random_ua() -> str:
    return random.choice(_UA_LIST)


def _get_nid() -> Optional[str]:
    """获取东方财富 NID 授权令牌（20s 缓存）"""
    now = time.time()
    if _nid_cache["data"] and now < _nid_cache["expire_at"]:
        return _nid_cache["data"]
    with _nid_cache["lock"]:
        if _nid_cache["data"] and now < _nid_cache["expire_at"]:
            return _nid_cache["data"]
        try:
            import requests as _r
            ua = _random_ua()
            payload = {
                "osPlatform": "Windows", "sourceType": "WEB",
                "osversion": "Windows 10.0", "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "webDeviceInfo": {
                    "screenResolution": random.choice(["1920X1080", "2560X1440"]),
                    "userAgent": ua,
                    "canvasKey": hashlib.md5(str(uuid.uuid4()).encode()).hexdigest(),
                    "webglKey": hashlib.md5(str(uuid.uuid4()).encode()).hexdigest(),
                    "fontKey": hashlib.md5(str(uuid.uuid4()).encode()).hexdigest(),
                    "audioKey": hashlib.md5(str(uuid.uuid4()).encode()).hexdigest(),
                },
            }
            _st = "".join(secrets.choice(
                "useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict"
            ) for _ in range(21))
            headers = {
                "Cookie": f"st_nvi={_st}{hashlib.sha256(_st.encode()).hexdigest()[:4]}",
                "Content-Type": "application/json",
            }
            resp = _r.post(
                "https://anonflow2.eastmoney.com/backend/api/webreport",
                headers=headers, json=payload, timeout=30,
            )
            resp.raise_for_status()
            nid = resp.json()["data"]["nid"]
            _nid_cache["data"] = nid
            _nid_cache["expire_at"] = now + _nid_cache["ttl"]
            return nid
        except Exception:
            _nid_cache["data"] = None
            _nid_cache["expire_at"] = now + 300
            return None


def apply_eastmoney_patch():
    """给 requests.Session.request 打补丁（为 akshare 防反爬）"""
    global _patch_applied
    if _patch_applied:
        return
    try:
        import requests as _r
        _original = _r.Session.request

        def _patched(self, method, url, **kwargs):
            url_s = str(url) if url else ""
            if any(d in url_s for d in ["eastmoney.com"]):
                h = kwargs.get("headers", {}) or {}
                h["User-Agent"] = _random_ua()
                nid = _get_nid()
                if nid:
                    h["Cookie"] = f"nid18={nid}"
                kwargs["headers"] = h
                time.sleep(random.uniform(0.3, 1.5))
            return _original(self, method, url, **kwargs)

        _r.Session.request = _patched
        _patch_applied = True
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 股票名称映射 + 工具函数
# ═══════════════════════════════════════════════════════════

_NAME_MAP: dict[str, str] = {
    "600398": "海澜之家", "600519": "贵州茅台", "000858": "五粮液",
    "300750": "宁德时代", "000001": "平安银行", "600036": "招商银行",
    "601318": "中国平安", "000333": "美的集团", "002415": "海康威视",
    "600276": "恒瑞医药", "000725": "京东方A", "002594": "比亚迪",
    "601012": "隆基绿能", "600030": "中信证券", "000002": "万科A",
    "600887": "伊利股份", "000651": "格力电器", "600900": "长江电力",
}


def _lookup_name(code: str) -> str:
    return _NAME_MAP.get(code, code)


def _sh_sz(code: str) -> str:
    if code.startswith(("6", "5", "9")):
        return f"sh{code}"
    return f"sz{code}"


# ═══════════════════════════════════════════════════════════
# K 线采集（腾讯优先 → akshare fallback）
# ═══════════════════════════════════════════════════════════

def _fetch_kline_tencent(stock_code: str) -> dict:
    """腾讯 K 线 API（curl_cffi，不走系统代理）"""
    symbol = _sh_sz(stock_code)
    resp = http.get(
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": f"{symbol},day,,,90,qfq"},
        headers={"User-Agent": _random_ua(), "Accept": "application/json"},
        impersonate="chrome131",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"腾讯K线API错误: {data.get('msg')}")

    stock_data = data["data"].get(symbol, {})
    klines = stock_data.get("qfqday", stock_data.get("day", []))
    if not klines:
        raise ValueError("腾讯K线数据为空")

    import pandas as pd
    rows = [{
        "日期": k[0], "开盘": float(k[1]), "收盘": float(k[2]),
        "最高": float(k[3]), "最低": float(k[4]), "成交量": float(k[5]),
    } for k in klines[-60:]]
    return {"df": pd.DataFrame(rows), "source": "tencent"}


def _fetch_kline_akshare(stock_code: str) -> dict:
    """akshare K 线（东方财富，带超时）"""
    import akshare as ak
    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
    df = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                            start_date=start, end_date=end, adjust="qfq")
    if df.empty:
        raise ValueError("K线数据为空")
    return {"df": df.tail(60), "source": "akshare"}


def _fetch_kline(stock_code: str) -> dict:
    """采集K线，腾讯优先，akshare fallback"""
    for name, fn in [("tencent", _fetch_kline_tencent), ("akshare", _fetch_kline_akshare)]:
        try:
            if name == "akshare":
                result = _run_with_timeout(lambda: fn(stock_code), timeout=12.0)
            else:
                result = fn(stock_code)
            logger.info(f"K线来源: {result['source']}")
            return result
        except Exception as e:
            logger.warning(f"{name} K线失败: {e}")
    raise RuntimeError(f"所有K线数据源均失败: {stock_code}")


def _run_with_timeout(fn, timeout: float = 10.0):
    """线程池超时包装，防止 akshare/网络调用卡死

    使用 ThreadPoolExecutor 替代 multiprocessing：
    - Windows 兼容（无 pickle 问题）
    - I/O 密集型任务，GIL 不影响超时控制
    - shutdown(wait=False)：超时后不等待卡死线程，立即返回
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f"操作超时 ({timeout}s)")
    finally:
        executor.shutdown(wait=False)


# ═══════════════════════════════════════════════════════════
# 实时行情（腾讯）
# ═══════════════════════════════════════════════════════════

def _fetch_spot_tencent(stock_code: str) -> dict:
    """腾讯实时行情"""
    symbol = _sh_sz(stock_code)
    resp = http.get(
        f"https://qt.gtimg.cn/q={symbol}",
        headers={"User-Agent": _random_ua()},
        impersonate="chrome131",
        timeout=8,
    )
    resp.encoding = "gbk"
    parts = resp.text.split("~")
    if len(parts) < 45:
        raise ValueError("实时行情解析失败")
    return {
        "name": parts[1],
        "最新价": parts[3], "昨收": parts[4], "今开": parts[5],
        "最高": parts[33], "最低": parts[34],
        "成交量": parts[6], "成交额": parts[37],
        "换手率": parts[38], "市盈率": parts[39],
        "总市值": parts[45], "流通市值": parts[44],
    }


# ═══════════════════════════════════════════════════════════
# 基本面数据采集（新浪源 → akshare fallback）
# ═══════════════════════════════════════════════════════════

def _fetch_fundamental(stock_code: str) -> dict:
    """采集基本面数据：PE/PB/ROE/营收增速/净利润增速

    数据来源：akshare 财务指标（东方财富源）
    失败时返回空 dict，不阻塞下游分析。
    """
    result: dict[str, Any] = {}

    # ── akshare 财务指标（含 PE/PB/ROE/营收增速等）──
    try:
        import akshare as ak
        fin = _run_with_timeout(lambda: ak.stock_financial_analysis_indicator(symbol=stock_code), timeout=15.0)
        if fin is not None and not fin.empty:
            latest = fin.iloc[-1]
            # PE / PB
            pe = latest.get("市盈率", None)
            if pe is not None:
                try:
                    result["pe"] = round(float(pe), 2)
                except (ValueError, TypeError):
                    pass
            pb = latest.get("市净率", None)
            if pb is not None:
                try:
                    result["pb"] = round(float(pb), 2)
                except (ValueError, TypeError):
                    pass
            # ROE
            roe = latest.get("净资产收益率", None)
            if roe is not None:
                try:
                    result["roe"] = round(float(roe), 2)
                except (ValueError, TypeError):
                    pass
            # 营收增速
            rev_growth = latest.get("营业收入同比增长", None)
            if rev_growth is not None:
                try:
                    result["revenue_yoy"] = round(float(rev_growth), 2)
                except (ValueError, TypeError):
                    pass
            # 净利润增速
            profit_growth = latest.get("净利润同比增长", None)
            if profit_growth is not None:
                try:
                    result["profit_yoy"] = round(float(profit_growth), 2)
                except (ValueError, TypeError):
                    pass
            # 资产负债率
            debt_ratio = latest.get("资产负债率", None)
            if debt_ratio is not None:
                try:
                    result["debt_ratio"] = round(float(debt_ratio), 2)
                except (ValueError, TypeError):
                    pass
            # EPS
            eps = latest.get("基本每股收益", None)
            if eps is not None:
                try:
                    result["eps"] = round(float(eps), 2)
                except (ValueError, TypeError):
                    pass
            result["fin_source"] = "akshare_eastmoney"
            logger.info("基本面财务指标来源: akshare 东方财富")
    except Exception as e:
        logger.warning(f"akshare 财务指标失败: {e}")

    # ── fallback: 东方财富实时行情（PE/PB 补充）──
    if "pe" not in result or "pb" not in result:
        try:
            import akshare as ak
            spot = _run_with_timeout(lambda: ak.stock_zh_a_spot_em(), timeout=25.0)
            if spot is not None and not spot.empty:
                row = spot[spot["代码"] == stock_code]
                if not row.empty:
                    r = row.iloc[0]
                    if "pe" not in result:
                        pe_val = r.get("市盈率-动态", None)
                        if pe_val is not None:
                            try:
                                result["pe"] = round(float(pe_val), 2)
                            except (ValueError, TypeError):
                                pass
                    if "pb" not in result:
                        pb_val = r.get("市净率", None)
                        if pb_val is not None:
                            try:
                                result["pb"] = round(float(pb_val), 2)
                            except (ValueError, TypeError):
                                pass
                    result.setdefault("pe_pb_source", "akshare_spot_em")
                    logger.info("基本面 PE/PB 补充来源: akshare 东方财富实时行情")
        except Exception as e:
            logger.warning(f"akshare 实时行情 PE/PB 补充失败: {e}")

    return result


# ═══════════════════════════════════════════════════════════
# 新闻 & 资金流（akshare）
# ═══════════════════════════════════════════════════════════

def _fetch_news_akshare(stock_code: str) -> list[dict]:
    """akshare 个股新闻"""
    import akshare as ak
    news = _run_with_timeout(lambda: ak.stock_news_em(symbol=stock_code), timeout=10.0)
    if news.empty:
        return []
    return [
        {"title": str(n["新闻标题"]), "time": str(n["发布时间"])}
        for n in news.head(8).to_dict(orient="records")
    ]


def _fetch_fund_flow_akshare(stock_code: str) -> list[dict]:
    """akshare 资金流向"""
    import akshare as ak
    market = "sh" if stock_code.startswith(("6", "5", "9")) else "sz"
    fund = _run_with_timeout(lambda: ak.stock_individual_fund_flow(stock=stock_code, market=market), timeout=10.0)
    if fund.empty:
        return []
    return fund.tail(5).to_dict(orient="records")


# ═══════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════

def fetch_stock_data(stock_code: str) -> dict:
    """采集单只A股全量数据"""
    apply_eastmoney_patch()
    data: dict[str, Any] = {
        "stock_code": stock_code,
        "fetch_time": datetime.now().isoformat(),
    }
    _total_start = time.time()

    # ── K 线（必须）──
    t0 = time.time()
    try:
        result = _fetch_kline(stock_code)
        df = result["df"]
        closes = [float(v) for v in df["收盘"].tolist()]
        volumes = [float(v) for v in df["成交量"].tolist()]

        for p in [5, 10, 20, 60]:
            if len(closes) >= p:
                data[f"ma{p}"] = round(sum(closes[-p:]) / p, 2)

        if len(closes) >= 15:
            gains = [max(0, closes[i] - closes[i - 1]) for i in range(-14, 0)]
            losses = [max(0, closes[i - 1] - closes[i]) for i in range(-14, 0)]
            avg_g = sum(gains) / 14
            avg_l = sum(losses) / 14
            data["rsi"] = round(100 - 100 / (1 + avg_g / avg_l), 2) if avg_l > 0 else 100

        def _ema(s, n):
            k = 2 / (n + 1)
            r = [s[0]]
            for v in s[1:]:
                r.append(v * k + r[-1] * (1 - k))
            return r

        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        dif = ema12[-1] - ema26[-1]
        dea = _ema([ema12[i] - ema26[i] for i in range(len(closes))], 9)[-1]
        data["macd_dif"] = round(dif, 3)
        data["macd_dea"] = round(dea, 3)
        data["macd_bar"] = round(2 * (dif - dea), 3)

        if len(volumes) >= 6:
            avg5 = sum(volumes[-6:-1]) / 5
            data["volume_ratio"] = round(volumes[-1] / avg5, 2) if avg5 > 0 else 1.0

        for n, key in [(6, "pct_5d"), (11, "pct_10d"), (21, "pct_20d")]:
            if len(closes) >= n:
                data[key] = round((closes[-1] / closes[-n] - 1) * 100, 2)

        bars = []
        for _, r in df.tail(5).iterrows():
            bars.append({
                "date": str(r["日期"])[:10],
                "open": r["开盘"], "high": r["最高"], "low": r["最低"],
                "close": r["收盘"], "volume": int(r["成交量"]),
                "pct_chg": round(float(r.get("涨跌幅", 0)), 2),
            })
        data["recent_bars"] = bars
        data["latest_close"] = round(closes[-1], 2)
        data["data_source"] = result["source"]
        print(f"  ✅ K线: {len(df)}条, 来源={result['source']}, 收盘={closes[-1]:.2f}, 耗时{time.time()-t0:.1f}s")
    except Exception as e:
        data["kline_error"] = str(e)
        print(f"  ❌ K线失败: {e}")

    # ── 实时行情 ──
    t0 = time.time()
    try:
        spot = _fetch_spot_tencent(stock_code)
        data["spot"] = spot
        name = spot.get("name", "")
        if name and name != stock_code:
            data["stock_name"] = name
            _NAME_MAP[stock_code] = name
        print(f"  ✅ 实时行情: {data.get('stock_name', '?')}, 耗时{time.time()-t0:.1f}s")
    except Exception as e:
        print(f"  ⚠️ 实时行情跳过: {e}")

    # ── 资金流（akshare，可选；eastmoney 不可用时跳过）──
    akshare_ok = data.get("data_source") == "akshare"
    if akshare_ok:
        t0 = time.time()
        try:
            fund = _fetch_fund_flow_akshare(stock_code)
            if fund:
                data["fund_flow_recent_5d"] = fund
                print(f"  ✅ 资金流: {len(fund)}条, 耗时{time.time()-t0:.1f}s")
        except TimeoutError:
            data["fund_error"] = "资金流采集超时"
            print(f"  ⚠️ 资金流超时 ({time.time()-t0:.1f}s)")
        except Exception as e:
            data["fund_error"] = str(e)
            print(f"  ⚠️ 资金流: {e}")
    else:
        data["fund_error"] = "eastmoney不可用，跳过资金流采集"
        print(f"  ⚠️ 资金流跳过（eastmoney不可用）")

    # ── 新闻（akshare，可选；eastmoney 不可用时跳过）──
    if akshare_ok:
        t0 = time.time()
        try:
            news = _fetch_news_akshare(stock_code)
            if news:
                data["news"] = news
                print(f"  ✅ 新闻: {len(news)}条, 耗时{time.time()-t0:.1f}s")
        except TimeoutError:
            data["news_error"] = "新闻采集超时"
            print(f"  ⚠️ 新闻超时 ({time.time()-t0:.1f}s)")
        except Exception as e:
            data["news_error"] = str(e)
            print(f"  ⚠️ 新闻跳过: {e}")
    else:
        data["news_error"] = "eastmoney不可用，跳过新闻采集"
        print(f"  ⚠️ 新闻跳过（eastmoney不可用）")

    # ── 基本面（akshare 新浪/东方财富，可选）──
    t0 = time.time()
    try:
        fundamental = _fetch_fundamental(stock_code)
        if fundamental:
            data["fundamental"] = fundamental
            fields_found = [k for k in ["pe", "pb", "roe", "revenue_yoy", "profit_yoy"]
                          if k in fundamental]
            print(f"  ✅ 基本面: {'、'.join(fields_found) if fields_found else '无可用字段'}, 耗时{time.time()-t0:.1f}s")
    except Exception as e:
        data["fundamental_error"] = str(e)
        print(f"  ⚠️ 基本面跳过: {e}")

    print(f"  ⏱ 采集总耗时: {time.time()-_total_start:.1f}s")
    return data


# ═══════════════════════════════════════════════════════════
# 数据守卫
# ═══════════════════════════════════════════════════════════

class DataIncompleteError(RuntimeError):
    """关键数据缺失，禁止调用LLM"""
    pass


REQUIRED_FIELDS = ["latest_close", "recent_bars"]


def validate_data(data: dict) -> None:
    """调用LLM前必须通过此校验"""
    missing = [k for k in REQUIRED_FIELDS if k not in data]
    if missing:
        raise DataIncompleteError(
            f"缺少关键行情数据: {', '.join(missing)}，无法生成分析报告"
        )
