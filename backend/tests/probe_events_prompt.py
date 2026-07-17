"""
Probe: get_stock_events 测试 prompt 形式的 query — 看能否返回综合数据
"""
import json, os, sys
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            if key and value:
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

from ifind_call import call

STOCK = "600519"

PROMPTS = {
    # A. 自然语言综合请求
    "nl_full": f"请返回{STOCK}的重大事件综合数据，包括分红送转、回购增发、股权激励、股东增减持、限售解禁、股权质押、违规处罚、重大诉讼、关联交易等各类重大事件",
    # B. 简洁版自然语言
    "nl_short": f"综合查询{STOCK}所有重大事件：分红、回购、增发、股权激励、增减持、解禁、质押、处罚、诉讼、关联交易",
    # C. 指令式
    "instruct": f"请整合{STOCK}的以下所有事件类型并一次性返回：分红送转|回购|增发|股权激励|股东减持|股东增持|限售解禁|股权质押|违规处罚|重大诉讼|关联交易|业绩快报|大宗交易",
    # D. 要求展开多维度
    "multi_dim": f"{STOCK} 重大事件 分红 送转 回购 增发 股权激励 股东减持 股东增持 限售解禁 股权质押 违规处罚 重大诉讼 关联交易 业绩快报 业绩预告 大宗交易",
    # E. 精简关键词（只用最核心的5个）
    "top5": f"{STOCK} 分红 回购 增发 减持 处罚",
    # F. 所有单次调用中最成功的（baseline_6 对比）
    "baseline_6": f"{STOCK} 分红 增发 回购 股权激励 重大资产重组 业绩预告",
}


def probe(label, query):
    result = call("stock", "get_stock_events", {"query": query})
    if not result["ok"]:
        return {"ok": False, "error": str(result.get("error", ""))[:200]}

    raw_text = ""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                raw_text = inner.get("data", {}).get("answer", inner.get("data", {}).get("data", ""))
                if not raw_text:
                    raw_text = inner.get("data", {}).get("answer", "")
                break
    except Exception:
        pass

    if not raw_text:
        return {"ok": True, "record_count": 0, "headers": [], "raw": "empty"}

    lines = raw_text.strip().split("\n")
    headers, records = [], []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
            continue
        if not headers:
            headers = list(parts)
        else:
            rec = {}
            for i, v in enumerate(parts):
                if i < len(headers):
                    rec[headers[i]] = v
            if rec:
                records.append(rec)

    return {
        "ok": True, "record_count": len(records), "headers": headers,
        "records": records[:5], "raw_preview": raw_text[:500],
    }


def main():
    print("Probe: get_stock_events prompt 形式测试")
    print("=" * 70)

    for label, query in PROMPTS.items():
        r = probe(label, query)
        print(f"\n[{label}]")
        print(f"  query: {query[:100]}...")
        if not r["ok"]:
            print(f"  FAIL: {r.get('error')}")
        elif r["record_count"] == 0:
            print(f"  EMPTY")
        else:
            print(f"  rows={r['record_count']} headers={r['headers']}")
            print(f"  raw_preview: {r.get('raw_preview', '')[:300]}")


if __name__ == "__main__":
    main()
