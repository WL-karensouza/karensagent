"""失败语料回放 — 用真实故障样本验证 _parse_json 容错的实际效果（tech-tracker #2）

遍历 stock_agent/reports/failures/*.txt，逐份原文过 _parse_json：
  救回（不抛 + 含核心字段）→ 该样本已被当前策略覆盖，可人工归档
  仍失败 → 列出错误形态，作为下一轮容错加固的输入
用法：python tests/replay_failures.py
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.analyze import _parse_json

FAIL_DIR = BACKEND / "stock_agent" / "reports" / "failures"


def main():
    if not FAIL_DIR.exists():
        print(f"语料目录不存在（尚未触发过失败）: {FAIL_DIR}")
        return
    files = sorted(FAIL_DIR.glob("*.txt"))
    if not files:
        print("语料目录为空 — 尚未触发过解析失败，好事")
        return

    rescued, still_failed = 0, []
    for f in files:
        raw = f.read_text(encoding="utf-8")
        try:
            result = _parse_json(raw)
            if isinstance(result, dict) and ("score" in result or "decision" in result):
                rescued += 1
                continue
            still_failed.append((f.name, "解析成功但核心字段缺失"))
        except Exception as e:
            still_failed.append((f.name, f"{type(e).__name__}: {str(e)[:80]}"))

    print(f"语料 {len(files)} 份：救回 {rescued}，仍失败 {len(still_failed)}")
    for name, err in still_failed:
        print(f"  ❌ {name}: {err}")
    if rescued:
        print(f"\n💡 已救回的 {rescued} 份语料可人工归档（当前策略已覆盖其故障形态）")


if __name__ == "__main__":
    main()
