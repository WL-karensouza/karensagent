"""
实验 2：iFind News 数据完整性探查 (H1.2)

验证 news server 3 个工具能否返回半导体行业相关数据。
测试标的：688981.SH 中芯国际 + 002371.SZ 北方华创
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 加载 .env
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

STOCKS = [
    {"code": "688981.SH", "name": "中芯国际"},
    {"code": "002371.SZ", "name": "北方华创"},
]

NEWS_TOOLS = [
    {
        "name": "search_news",
        "desc": "财经新闻",
        "params_tpl": lambda s: {
            "query": f"{s['name']} {s['code']} 半导体芯片",
            "time_start": "2026-06-10",
            "time_end": "2026-07-10",
            "size": 10,
        },
    },
    {
        "name": "search_notice",
        "desc": "公司公告",
        "params_tpl": lambda s: {
            "query": f"{s['name']} {s['code']} 公告",
            "time_start": "2026-04-10",
            "time_end": "2026-07-10",
            "size": 10,
        },
    },
]

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_answer(result):
    """从 iFind 返回中提取数据文本"""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                data_obj = inner.get("data", {})
                # news server 返回格式：data.data（JSON 数组字符串）
                answer = data_obj.get("data", "")
                if answer:
                    return answer
                # stock server 返回格式：data.answer（markdown 表格）
                answer = data_obj.get("answer", "")
                if answer:
                    return answer
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return ""


def count_entries(answer_text):
    """统计返回的数据条目数"""
    if not answer_text:
        return 0
    # news 数据是 JSON 数组字符串，尝试解析
    try:
        items = json.loads(answer_text)
        if isinstance(items, list):
            return len(items)
    except (json.JSONDecodeError, TypeError):
        pass
    # fallback：按行统计
    lines = [l for l in answer_text.strip().split("\n") if l.strip()]
    data_lines = [l for l in lines if l.startswith("|") and not all(
        c in "-:| " for c in l.replace("|", "").strip()
    )]
    if data_lines:
        return len(data_lines)
    return len(lines)


def probe_news(stock, tool):
    """探查单只股票 + 单个 news 工具"""
    params = tool["params_tpl"](stock)
    print(f"  [{tool['desc']}] params: {json.dumps(params, ensure_ascii=False)[:100]}...")

    try:
        result = call("news", tool["name"], params)
    except Exception as e:
        print(f"    ❌ 异常: {e}")
        return {"ok": False, "error": str(e), "params": params}

    if not result["ok"]:
        print(f"    ❌ API 错误: {result.get('error', 'unknown')}")
        return {"ok": False, "error": result.get("error"), "params": params}

    answer = extract_answer(result)
    entries = count_entries(answer)

    if entries > 0:
        print(f"    ✅ 返回 {entries} 条数据")
        preview = answer[:200].replace("\n", "\\n")
        print(f"    预览: {preview}...")
    else:
        print(f"    ⚠️ 无有效数据条目，原始 answer 长度: {len(answer)}")
        if answer:
            print(f"    原始内容: {answer[:300]}")

    return {"ok": True, "entries": entries, "answer": answer, "params": params}


def main():
    print("=" * 60)
    print("实验 2：iFind News 数据完整性探查")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {len(STOCKS)} 只股票 x {len(NEWS_TOOLS)} 个工具")
    print("=" * 60)

    all_results = {}
    all_passed = True

    for stock in STOCKS:
        print(f"\n📰 {stock['name']} ({stock['code']})")
        stock_results = {}

        for tool in NEWS_TOOLS:
            r = probe_news(stock, tool)
            stock_results[tool["name"]] = r

            if not r["ok"]:
                all_passed = False

        all_results[stock["code"]] = stock_results

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print("📋 汇总")
    print("=" * 60)

    for code, stock_results in all_results.items():
        name = next((s["name"] for s in STOCKS if s["code"] == code), code)
        print(f"\n  {name} ({code}):")
        for tool_name, r in stock_results.items():
            if not r:
                continue
            tool_desc = next(
                (t["desc"] for t in NEWS_TOOLS if t["name"] == tool_name), tool_name
            )
            if r.get("ok"):
                entries = r.get("entries", 0)
                if entries > 0:
                    print(f"    ✅ {tool_desc}: {entries} 条")
                else:
                    print(f"    ⚠️ {tool_desc}: 0 条（工具正常，当前无数据）")
            else:
                print(f"    ❌ {tool_desc}: {r.get('error', 'unknown')}")
                all_passed = False

    # ── 保存完整结果 ──
    output_path = OUTPUT_DIR / f"news_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 完整结果已保存: {output_path}")

    # ── 判定：所有工具调用必须成功（不强制每个都有数据） ──
    if all_passed:
        print("\n✅ 实验 2 通过！所有 news 工具调用成功")
        return 0
    else:
        print("\n❌ 实验 2 失败：部分工具调用报错")
        return 1


if __name__ == "__main__":
    sys.exit(main())
