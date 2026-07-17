"""
实验 9：iFind EDB 宏观经济数据完整性探查 (H1.3)

EDB server 仅一个工具：get_edb_data
覆盖: 全球宏观、中国宏观、行业经济指标
测试半导体相关经济指标是否可获取。
"""
import json
import os
import sys
import re
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

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_answer(result):
    """从 EDB 返回中提取数据"""
    try:
        content = result.get("data", {}).get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if text:
                inner = json.loads(text)
                data_obj = inner.get("data", {})
                # EDB 可能用 data.answer 格式
                for key in ["answer", "data", "result"]:
                    val = data_obj.get(key, "")
                    if val and isinstance(val, str) and len(val) > 10:
                        return val
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return ""


def count_meaningful_content(answer_text):
    """统计有意义的非空内容"""
    if not answer_text:
        return 0, "空响应"

    lines = [l.strip() for l in answer_text.split("\n") if l.strip()]

    # 检查 markdown 表格行
    table_rows = sum(1 for l in lines if l.startswith("|") and l.endswith("|"))
    # 检查 JSON 内容
    json_content = ""
    json_matches = re.findall(r"```json\s*\n(.*?)\n```", answer_text, re.DOTALL)
    if json_matches:
        json_content = json_matches[0]

    if table_rows > 0:
        return table_rows, f"markdown表格({table_rows}行)"
    elif json_content:
        try:
            items = json.loads(json_content)
            if isinstance(items, list):
                return len(items), f"JSON数组({len(items)}项)"
            elif isinstance(items, dict):
                return len(items), f"JSON对象({len(items)}键)"
        except:
            pass
        return len(json_content), f"JSON文本({len(json_content)}字符)"
    elif len(lines) > 0:
        return len(lines), f"纯文本({len(lines)}行)"
    return 0, "无法解析"


# ── 测试查询 ──
# EDB 覆盖 3 类指标，每类选 2-3 个典型查询
QUERIES = [
    # 全球宏观指标
    {"label": "美国GDP增长率", "query": "美国GDP年增长率 最新数据"},
    {"label": "全球半导体市场规模", "query": "全球半导体市场规模 销售额"},

    # 中国宏观指标
    {"label": "中国工业增加值", "query": "中国工业增加值 同比增速"},
    {"label": "中国PMI", "query": "中国制造业PMI 最新数据"},
    {"label": "中国M2货币供应", "query": "中国M2货币供应量 同比增速"},

    # 行业经济指标（半导体相关）
    {"label": "中国集成电路产量", "query": "中国集成电路产量 当月值"},
    {"label": "半导体设备出货", "query": "半导体设备出货额 月度数据"},
    {"label": "芯片进口金额", "query": "中国芯片进口金额 集成电路"},
]


def main():
    print("=" * 60)
    print("实验 9：iFind EDB 宏观经济数据完整性探查")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"用例: {len(QUERIES)} 个查询")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0
    total_records = 0

    for i, q in enumerate(QUERIES):
        print(f"\n  [{i+1}/{len(QUERIES)}] {q['label']}: {q['query'][:60]}...")

        try:
            result = call("edb", "get_edb_data", {"query": q["query"]})
        except Exception as e:
            print(f"    ❌ 异常: {e}")
            failed += 1
            results.append({**q, "ok": False, "error": str(e)})
            continue

        if not result["ok"]:
            err = result.get("error", "unknown")
            print(f"    ❌ API 错误: {err}")
            failed += 1
            results.append({**q, "ok": False, "error": str(err)})
            continue

        answer = extract_answer(result)
        count, desc = count_meaningful_content(answer)

        if count > 0:
            print(f"    ✅ {desc}")
            preview = answer[:200].replace("\n", "\\n")
            print(f"    预览: {preview}...")
            passed += 1
            total_records += count
            results.append({**q, "ok": True, "count": count, "format": desc, "preview": answer[:500]})
        else:
            print(f"    ⚠️ 有响应但无有效数据 (desc={desc})")
            if answer:
                print(f"    原始: {answer[:200]}")
            failed += 1
            results.append({**q, "ok": False, "count": 0, "format": desc, "error": "无有效数据"})

    # ── 按类别汇总 ──
    print("\n" + "=" * 60)
    print("📋 分类汇总")
    print("=" * 60)

    categories = {
        "全球宏观": QUERIES[:2],
        "中国宏观": QUERIES[2:5],
        "行业经济": QUERIES[5:],
    }

    cat_results = {}
    for cat, cat_queries in categories.items():
        cat_labels = {q["label"] for q in cat_queries}
        cat_ok = sum(1 for r in results if r["label"] in cat_labels and r["ok"])
        cat_total = len(cat_queries)
        cat_results[cat] = {"ok": cat_ok, "total": cat_total}
        print(f"  {cat}: {cat_ok}/{cat_total} 成功")

    # ── 保存 ──
    output_path = OUTPUT_DIR / f"edb_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 结果已保存: {output_path}")

    # ── 判定 ──
    total = passed + failed
    success_rate = passed / total * 100 if total > 0 else 0

    print(f"\n  总成功: {passed}/{total} ({success_rate:.0f}%)")
    print(f"  总记录数: {total_records}")

    if success_rate >= 50:
        print(f"\n✅ 实验 9 通过！EDB 数据源可用 (成功率 {success_rate:.0f}% ≥ 50%)")
        print(f"   注意: EDB 查询质量取决于同花顺指标覆盖范围，部分特定指标可能无数据")
        return 0
    else:
        print(f"\n❌ 实验 9 失败：成功率 {success_rate:.0f}% < 50%")
        print(f"   EDB 可能不适合作为主要宏观经济数据源，建议保留 akshare 做 fallback")
        return 1


if __name__ == "__main__":
    sys.exit(main())
