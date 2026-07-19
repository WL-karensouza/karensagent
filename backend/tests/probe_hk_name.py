"""探测脚本：东方财富获取港股公司名称 — secid 格式试错

当前已知：A股 secid 格式为 {市场}.{代码}，如 1.600519
港股 secid 可能格式：116.{代码} / 116.{零填充5位} / 128.{代码} 等
"""

import requests
import time
import sys

# 强制 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


STOCKS = [
    {"code": "2513.HK", "desc": "智谱华章"},
    {"code": "0700.HK", "desc": "腾讯控股（蓝筹验证）"},
    {"code": "9988.HK", "desc": "阿里巴巴（蓝筹验证）"},
]

# 待测试的 secid 格式组合
FORMATS = [
    ("116.{pure}", "不补零"),
    ("116.{zp5}", "补零到5位"),
    ("116.{zp4}", "补零到4位"),
]


def probe(code: str, desc: str):
    pure = code.replace(".HK", "").strip()
    zp4 = pure.zfill(4)
    zp5 = pure.zfill(5)

    print(f"\n{'='*60}")
    print(f"[{desc}] {code} -> pure={pure}")
    print(f"{'='*60}")

    for fmt_tpl, note in FORMATS:
        secid = fmt_tpl.format(pure=pure, zp4=zp4, zp5=zp5)
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "fltt": "2",
            "invt": "2",
            "fields": "f57,f58,f2,f3,f12,f14",
            "secid": secid,
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            data = r.json()
            info = data.get("data")
            if info and info.get("f58"):
                print(f"  [OK]  {secid:20s} ({note:10s}) -> {info['f57']} {info['f58']}  现价={info.get('f2','')}  涨跌={info.get('f3','')}%")
            else:
                err = data.get("message", "") if isinstance(data, dict) else str(data)[:80]
                print(f"  [NO]  {secid:20s} ({note:10s}) -> msg={err}")
        except Exception as e:
            print(f"  [ERR] {secid:20s} ({note:10s}) -> {e}")
        time.sleep(0.15)


def main():
    print("东方财富港股 secid 格式探测")
    print("=" * 60)
    t0 = time.time()

    for s in STOCKS:
        probe(s["code"], s["desc"])

    print(f"\n{'='*60}")
    print(f"总耗时: {int(time.time() - t0)}s")


if __name__ == "__main__":
    main()
