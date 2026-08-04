"""E1 实验：历史对比记忆 A/B 盲评材料生成

单变量控制：两版都走裸 analyze（不经过校验/修正层），唯一差异是是否注入历史上下文。
股票：600519 / 000858 / 688221（DB 历史均 ≥7 份，满足奇数位采样 [1,3,5,7]）

产出：
  docs/e1-blind-review/report-01..06.md —— 打乱匿名的盲评报告
  docs/e1-blind-review/prompt-length-stats.csv —— A5 假设统计（prompt 长度增量 / token）
  仓库根 .e1-mapping.txt —— 盲名↔A/B 归属映射（盲评结束后揭示，评完即删）
"""
import random
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.analyze import analyze, build_user_prompt
from stock_agent.core.history import build_history_context, sample_history_indices
from stock_agent.core.render import render_markdown
from stock_agent.skill.report import generate_report_sync
from database import get_recent_reports, SessionLocal
from models import StockReport

STOCKS = ["600519", "000858", "688221"]
OUT_DIR = BACKEND.parent / "docs" / "e1-blind-review"
MAPPING_FILE = BACKEND.parent / ".e1-mapping.txt"


def count_history(stock_code: str) -> int:
    db = SessionLocal()
    try:
        return db.query(StockReport).filter(StockReport.stock_code == stock_code).count()
    finally:
        db.close()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []  # (code, version_label, md, user_prompt_len, total_token)

    for code in STOCKS:
        n = count_history(code)
        print(f"\n{'='*60}\n📊 {code}: DB 历史 {n} 份, 采样位置 {sample_history_indices(n)}\n{'='*60}")

        print(f"  📡 SKILL 采集...")
        t0 = time.time()
        data = generate_report_sync(code)
        if data.get("has_critical_failure"):
            print(f"  ❌ 关键维度失败，跳过该股票")
            continue
        data_md = data["markdown"]
        stock_name = data.get("stock_name", code)
        print(f"  ✅ 采集完成 {time.time()-t0:.0f}s, 数据报告 {len(data_md)} 字符")

        # 版本 A：无历史（基线）
        t0 = time.time()
        report_a, usage_a = analyze(data_md, "")
        len_a = len(build_user_prompt(data_md, ""))
        print(f"  🅰 无历史版: {time.time()-t0:.0f}s, token={usage_a['total']}, user_prompt={len_a} 字符")

        # 版本 B：注入历史骨架
        history_ctx = build_history_context(get_recent_reports(code))
        t0 = time.time()
        report_b, usage_b = analyze(data_md, history_ctx)
        len_b = len(build_user_prompt(data_md, history_ctx))
        delta = (len_b - len_a) / max(len_a, 1) * 100
        print(f"  🅱 有历史版: {time.time()-t0:.0f}s, token={usage_b['total']}, user_prompt={len_b} 字符 (vs A {delta:+.1f}%)")

        entries.append((code, "A-无历史", render_markdown(code, report_a, usage_a, stock_name), len_a, usage_a["total"]))
        entries.append((code, "B-有历史", render_markdown(code, report_b, usage_b, stock_name), len_b, usage_b["total"]))

    if not entries:
        print("❌ 无任何有效条目")
        return

    # 打乱匿名输出
    random.shuffle(entries)
    mapping_lines = []
    stats_lines = ["stock,version,blind_name,user_prompt_len,total_token"]
    for i, (code, ver, md, plen, tok) in enumerate(entries, 1):
        blind_name = f"report-{i:02d}.md"
        (OUT_DIR / blind_name).write_text(md, encoding="utf-8")
        mapping_lines.append(f"{blind_name} <- {code} {ver}")
        stats_lines.append(f"{code},{ver},{blind_name},{plen},{tok}")

    MAPPING_FILE.write_text("\n".join(mapping_lines), encoding="utf-8")
    (OUT_DIR / "prompt-length-stats.csv").write_text("\n".join(stats_lines), encoding="utf-8")

    print(f"\n✅ 盲评材料 → {OUT_DIR}")
    print(f"✅ 归属映射 → {MAPPING_FILE}（盲评结束后揭示，评完即删）")
    print("\n--- prompt 长度 / token 统计 ---")
    print("\n".join(stats_lines))


if __name__ == "__main__":
    main()
