"""
Probe: get_stock_events 公平 A/B 对比 — 自然语言 vs 管道分隔
"""
import json, os, sys
from pathlib import Path

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
EVENT_TYPES = "分红送转 回购 增发 股权激励 股东减持 股东增持 限售解禁 股权质押 违规处罚 重大诉讼 关联交易 业绩快报 大宗交易"

TESTS = {
    # A. 纯自然语言（不加管道符）
    "nl_a": f"请返回{STOCK}的重大事件综合数据，包括分红送转、回购、增发、股权激励、股东减持、股东增持、限售解禁、股权质押、违规处罚、重大诉讼、关联交易、业绩快报、大宗交易",
    # B. 纯管道分隔（不加自然语言）
    "pipe_b": f"{STOCK} 分红送转|回购|增发|股权激励|股东减持|股东增持|限售解禁|股权质押|违规处罚|重大诉讼|关联交易|业绩快报|大宗交易",
    # C. 空格分隔（对照组）
    "space_c": f"{STOCK} {EVENT_TYPES}",
    # D. 自然语言 + 管道（instruct 原版）
    "nl_pipe_d": f"请整合{STOCK}的以下所有事件类型并一次性返回：分红送转|回购|增发|股权激励|股东减持|股东增持|限售解禁|股权质押|违规处罚|重大诉讼|关联交易|业绩快报|大宗交易",
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
                raw_text = inner.get("data", {}).get("answer", "")
                break
    except Exception:
        pass

    if not raw_text:
        return {"ok": True, "record_count": 0, "table_count": 0,
                "total_fields": 0, "headers": [], "note": "empty"}

    # 解析所有表
    lines = raw_text.strip().split("\n")
    tables = []
    current_headers = []
    current_rows = []

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if all(p.replace("-", "").replace(":", "").strip() == "" for p in parts):
            continue
        if not current_headers:
            current_headers = list(parts)
        else:
            # 检测是否遇到新表头（行内容很像表头而非数据行）
            # 简单策略：如果列数变了，就是新表
            if len(parts) != len(current_headers):
                # 保存当前表
                if current_rows:
                    tables.append({"headers": current_headers, "rows": len(current_rows)})
                current_headers = list(parts)
                current_rows = []
            else:
                rec = {}
                for i, v in enumerate(parts):
                    if i < len(current_headers):
                        rec[current_headers[i]] = v
                if rec:
                    current_rows.append(rec)

    if current_headers:
        tables.append({"headers": current_headers, "rows": len(current_rows)})

    all_fields = set()
    for t in tables:
        all_fields.update(t["headers"])

    return {
        "ok": True,
        "record_count": sum(t["rows"] for t in tables),
        "table_count": len(tables),
        "total_fields": len(all_fields),
        "tables": tables,
    }


def main():
    print("A/B 对比: 自然语言 vs 管道分隔 vs 空格分隔")
    print("=" * 70)

    for label, query in TESTS.items():
        r = probe(label, query)
        print(f"\n[{label}]")
        print(f"  query: {query[:120]}...")
        if not r["ok"]:
            print(f"  FAIL: {r.get('error')}")
        elif r["record_count"] == 0:
            print(f"  EMPTY")
        else:
            print(f"  表数={r['table_count']} 总行数={r['record_count']} 总字段数={r['total_fields']}")
            for i, t in enumerate(r["tables"]):
                # 计算非空值行数
                print(f"  表{i+1}: {t['rows']}行 x {len(t['headers'])}字段")
                print(f"    headers: {t['headers'][:12]}...")


if __name__ == "__main__":
    main()
