"""探测脚本：对比 AKShare vs 东方财富直调 获取股票公司名称

用法: python tests/probe_stock_name.py
"""

import sys
import time
import requests
import json

# ═══════════════════════════════════════════
# 待探测股票
# ═══════════════════════════════════════════

STOCKS = [
    {"code": "588000", "market": "SH", "desc": "科创50ETF"},
    {"code": "2513.HK", "market": "HK", "desc": "港股"},
    {"code": "688221", "market": "SH", "desc": "科创板"},
    {"code": "601127", "market": "SH", "desc": "沪市主板"},
]


# ═══════════════════════════════════════════
# 方案 A：东方财富 HTTP 直调
# ═══════════════════════════════════════════

def _em_market_code(code: str) -> str:
    """东方财富市场代码：1=沪市, 0=深市, 116=港股"""
    code = code.strip()
    if code.endswith(".HK"):
        return "116"
    pure = code.replace(".SH", "").replace(".SZ", "")
    if pure.startswith(("6", "5")):  # 60xxxx/68xxxx 沪市主板/科创板, 5xxxxx ETF
        return "1"
    return "0"  # 00xxxx/30xxxx 深市


def _em_secid(code: str) -> str:
    """构建东方财富 secid"""
    code = code.strip()
    if code.endswith(".HK"):
        pure = code.replace(".HK", "")
        return f"116.{pure}"
    pure = code.replace(".SH", "").replace(".SZ", "")
    mk = _em_market_code(pure)
    return f"{mk}.{pure}"


def get_name_eastmoney(code: str) -> dict:
    """东方财富 HTTP 直调查询"""
    secid = _em_secid(code)
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "fltt": "2",
        "invt": "2",
        "fields": "f57,f58",  # f57=代码, f58=简称
        "secid": secid,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        info = data.get("data", {})
        if not info:
            return {"ok": False, "error": "无数据", "secid": secid}
        return {
            "ok": True,
            "code": info.get("f57", ""),
            "name": info.get("f58", ""),
            "secid": secid,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "secid": secid}


# ═══════════════════════════════════════════
# 方案 B：AKShare
# ═══════════════════════════════════════════

def get_name_akshare_a(code: str) -> dict:
    """AKShare A 股实时行情查名称（stock_zh_a_spot_em 全量过滤）"""
    import akshare as ak
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df["代码"] == code]
        if row.empty:
            return {"ok": False, "error": f"代码 {code} 未在 A 股行情中找到"}
        return {
            "ok": True,
            "code": str(row.iloc[0]["代码"]),
            "name": str(row.iloc[0]["名称"]),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_name_akshare_individual(code: str) -> dict:
    """AKShare 单只股票详细信息查名称（stock_individual_info_em）"""
    import akshare as ak
    try:
        df = ak.stock_individual_info_em(symbol=code)
        # df 有两列: item, value；找 "股票简称" 行
        if df.empty:
            return {"ok": False, "error": "返回为空"}
        row = df[df["item"] == "股票简称"]
        if row.empty:
            return {"ok": False, "error": "未找到'股票简称'字段", "raw_keys": list(df["item"])}
        return {
            "ok": True,
            "code": code,
            "name": str(row.iloc[0]["value"]),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_name_akshare_code_map(code: str) -> dict:
    """AKShare stock_info_a_code_name 全量映射表查询"""
    import akshare as ak
    try:
        df = ak.stock_info_a_code_name()
        row = df[df["code"] == code]
        if row.empty:
            return {"ok": False, "error": f"代码 {code} 未在映射表中"}
        return {
            "ok": True,
            "code": str(row.iloc[0]["code"]),
            "name": str(row.iloc[0]["name"]),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════
# 港股特殊处理
# ═══════════════════════════════════════════

def get_name_hk_akshare(code: str) -> dict:
    """AKShare 港股查名称（stock_hk_spot_em）"""
    import akshare as ak
    pure = code.replace(".HK", "").strip()
    try:
        df = ak.stock_hk_spot_em()
        row = df[df["代码"] == pure]
        if row.empty:
            return {"ok": False, "error": f"代码 {pure} 未在港股行情中找到"}
        return {
            "ok": True,
            "code": str(row.iloc[0]["代码"]),
            "name": str(row.iloc[0]["名称"]),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════

def probe_one(stock: dict):
    """探测单只股票"""
    code = stock["code"]
    print(f"\n{'='*60}")
    print(f"【{stock['desc']}】{code}")
    print(f"{'='*60}")

    is_hk = code.endswith(".HK")

    # ── 东方财富直调 ──
    t0 = time.time()
    em = get_name_eastmoney(code)
    em_ms = int((time.time() - t0) * 1000)
    print(f"\n  东方财富直调 ({em_ms}ms):")
    if em["ok"]:
        print(f"    代码: {em['code']}  名称: {em['name']}")
    else:
        print(f"    [FAIL] {em['error']} (secid={em.get('secid','')})")

    # ── AKShare ──
    if is_hk:
        t0 = time.time()
        ak = get_name_hk_akshare(code)
        ak_ms = int((time.time() - t0) * 1000)
        print(f"\n  AKShare 港股行情 ({ak_ms}ms):")
        if ak["ok"]:
            print(f"    代码: {ak['code']}  名称: {ak['name']}")
        else:
            print(f"    [FAIL] {ak['error']}")
    else:
        # 方法1：单只详细信息
        t0 = time.time()
        ak1 = get_name_akshare_individual(code)
        ak1_ms = int((time.time() - t0) * 1000)
        print(f"\n  AKShare individual_info_em ({ak1_ms}ms):")
        if ak1["ok"]:
            print(f"    代码: {ak1['code']}  名称: {ak1['name']}")
        else:
            print(f"    [FAIL] {ak1['error']}")

        # 方法2：全量行情过滤（耗时，只测一只时跳过，但演示用）
        t0 = time.time()
        ak2 = get_name_akshare_a(code)
        ak2_ms = int((time.time() - t0) * 1000)
        print(f"\n  AKShare stock_zh_a_spot_em 过滤 ({ak2_ms}ms):")
        if ak2["ok"]:
            print(f"    代码: {ak2['code']}  名称: {ak2['name']}")
        else:
            print(f"    [FAIL] {ak2['error']}")

        # 方法3：全量映射表
        t0 = time.time()
        ak3 = get_name_akshare_code_map(code)
        ak3_ms = int((time.time() - t0) * 1000)
        print(f"\n  AKShare stock_info_a_code_name ({ak3_ms}ms):")
        if ak3["ok"]:
            print(f"    代码: {ak3['code']}  名称: {ak3['name']}")
        else:
            print(f"    [FAIL] {ak3['error']}")

    # ── 汇总 ──
    print(f"\n  {'─'*50}")
    names = set()
    if em["ok"]:
        names.add(em["name"])
    if not is_hk:
        if ak1.get("ok"):
            names.add(ak1["name"])
        if ak2.get("ok"):
            names.add(ak2["name"])
        if ak3.get("ok"):
            names.add(ak3["name"])
    else:
        if ak.get("ok"):
            names.add(ak["name"])
    if len(names) == 1:
        print(f"  [OK] 结果一致: {names.pop()}")
    elif len(names) > 1:
        print(f"  [WARN] 结果不一致! {names}")
    else:
        print(f"  [FAIL] 全部失败")


def main():
    print("=" * 60)
    print("  股票代码 → 公司名称 数据源对比探测")
    print("  东方财富直调 vs AKShare 多接口")
    print("=" * 60)

    overall_t0 = time.time()
    for stock in STOCKS:
        probe_one(stock)

    total_s = int(time.time() - overall_t0)
    print(f"\n{'='*60}")
    print(f"总耗时: {total_s}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
