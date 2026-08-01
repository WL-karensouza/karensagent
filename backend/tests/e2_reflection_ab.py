"""E2 实验：Reflection 质量自检 A/B 盲评材料生成

单变量控制：两版都**不注入历史**，唯一差异是 B 版经过评审-重写闭环。
验证集：10 只（主板/创业板/科创板/港股覆盖）

产出：
  docs/e2-blind-review/report-01..20.md —— 打乱匿名的盲评报告
  docs/e2-blind-review/e2-stats.csv —— 客观指标：token / validator 违规数 / 评审轮数 / 早停 / 重写数
  仓库根 .e2-mapping.txt —— 盲名↔A/B 归属（评完揭示即删）

成功判据（discovery 文档 E2）：
  A2: 盲评可感知改善（10 对中 B 版赢 ≥5 对，或用户主观判定）
  A3: 早停率 ≥70% 且附加 token ≤+40%
"""
import csv
import random
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.analyze import analyze
from stock_agent.reviewer import reflect_analyze
from stock_agent.render import render_markdown
from stock_agent.skill.report import generate_report_sync
from stock_agent.validator import validate_report

# 验证集：大盘蓝筹 / 创业板 / 科创板 / 小盘 / 港股
STOCKS = ["600398", "600519", "000858", "688221", "300369",
          "601127", "600905", "300033", "000938", "HK2513"]
OUT_DIR = BACKEND.parent / "docs" / "e2-blind-review"
MAPPING_FILE = BACKEND.parent / ".e2-mapping.txt"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []  # (code, version_label, md, total_token, validator_issues)
    stats_rows = [["stock", "version", "token", "validator_issues",
                   "review_rounds", "early_stopped", "rewrites", "problems_found"]]

    for code in STOCKS:
        print(f"\n{'='*60}\n📊 {code}\n{'='*60}")

        print(f"  📡 SKILL 采集...")
        t0 = time.time()
        data = generate_report_sync(code)
        if data.get("has_critical_failure"):
            print(f"  ❌ 关键维度失败，跳过")
            continue
        data_md = data["markdown"]
        stock_name = data.get("stock_name", code)
        print(f"  ✅ 采集完成 {time.time()-t0:.0f}s, {len(data_md)} 字符")

        # 版本 A：单次生成（基线，无历史无评审）
        t0 = time.time()
        try:
            report_a, usage_a = analyze(data_md)
        except Exception as e:
            print(f"  ❌ {code} 基线版分析失败，跳过该股票: {e}")
            continue
        issues_a = len(validate_report(report_a))
        print(f"  🅰 基线版: {time.time()-t0:.0f}s, token={usage_a['total']}, validator 违规={issues_a}")

        # 版本 B：评审-重写闭环（无历史）
        t0 = time.time()
        try:
            report_b, usage_b, stats_b = reflect_analyze(data_md)
        except Exception as e:
            print(f"  ❌ {code} 评审版分析失败，跳过该股票: {e}")
            continue
        issues_b = len(validate_report(report_b))
        problems_found = sum(len(p) for p in stats_b["all_problems"])
        extra = (usage_b["total"] - usage_a["total"]) / max(usage_a["total"], 1) * 100
        print(f"  🅱 评审版: {time.time()-t0:.0f}s, token={usage_b['total']} (vs A {extra:+.0f}%), "
              f"validator 违规={issues_b}, 评审{stats_b['rounds']}轮, "
              f"早停={stats_b['early_stopped']}, 重写{stats_b['rewrites']}次, 发现问题{problems_found}个")

        stats_rows.append([code, "A-基线", usage_a["total"], issues_a, "", "", "", ""])
        stats_rows.append([code, "B-评审", usage_b["total"], issues_b,
                           stats_b["rounds"], stats_b["early_stopped"],
                           stats_b["rewrites"], problems_found])

        entries.append((code, "A-基线", render_markdown(code, report_a, usage_a, stock_name), usage_a["total"], issues_a))
        entries.append((code, "B-评审", render_markdown(code, report_b, usage_b, stock_name), usage_b["total"], issues_b))

    if not entries:
        print("❌ 无任何有效条目")
        return

    # 打乱匿名输出
    random.shuffle(entries)
    mapping_lines = []
    for i, (code, ver, md, _tok, _iss) in enumerate(entries, 1):
        blind_name = f"report-{i:02d}.md"
        (OUT_DIR / blind_name).write_text(md, encoding="utf-8")
        mapping_lines.append(f"{blind_name} <- {code} {ver}")

    MAPPING_FILE.write_text("\n".join(mapping_lines), encoding="utf-8")
    with open(OUT_DIR / "e2-stats.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(stats_rows)

    # 客观指标汇总
    b_rows = [r for r in stats_rows[1:] if r[1] == "B-评审"]
    if b_rows:
        early_rate = sum(1 for r in b_rows if r[5] is True) / len(b_rows) * 100
        print(f"\n📊 早停率: {early_rate:.0f}% ({len(b_rows)} 只)")
    print(f"\n✅ 盲评材料 → {OUT_DIR}")
    print(f"✅ 归属映射 → {MAPPING_FILE}（盲评结束后揭示，评完即删）")


if __name__ == "__main__":
    main()
