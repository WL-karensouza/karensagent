"""E3 实验：Plan&Solve 模块化 A/B 材料生成

单变量控制：两版都不注入历史，唯一差异是单次生成 vs plan+逐模块生成。
门槛（用户调整版）：效果优先——截断→0、validator 违规不劣化、token ≤3× → 引入
指标：validator 违规数 / token / 耗时 / 截断次数 / 9 模块完整度
材料按 {code}-A/B.md 命名（以客观指标判定，材料仅供抽查，不做盲评）
"""
import csv
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.analyze import analyze
from stock_agent.modular import modular_analyze, MODULE_KEYS
from stock_agent.render import render_markdown
from stock_agent.skill.report import generate_report_sync
from stock_agent.validator import validate_report

STOCKS = ["600398", "600519", "000858", "688221", "300369",
          "601127", "600905", "300033", "000938", "HK2513"]
OUT_DIR = BACKEND.parent / "docs" / "e3-blind-review"


def completeness(report: dict) -> int:
    """9 模块中非空模块数"""
    return sum(1 for k in MODULE_KEYS if isinstance(report.get(k), dict) and report[k])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats_rows = [["stock", "version", "token", "validator_issues", "completeness",
                   "truncations", "module_fails", "elapsed_s"]]

    for code in STOCKS:
        print(f"\n{'='*60}\n📊 {code}\n{'='*60}")
        print("  📡 SKILL 采集...")
        t0 = time.time()
        data = generate_report_sync(code)
        if data.get("has_critical_failure"):
            print("  ❌ 关键维度失败，跳过")
            continue
        data_md = data["markdown"]
        stock_name = data.get("stock_name", code)
        print(f"  ✅ 采集完成 {time.time()-t0:.0f}s")

        # 版本 A：单次生成基线
        t0 = time.time()
        try:
            report_a, usage_a = analyze(data_md)
        except Exception as e:
            print(f"  ❌ 基线版失败，跳过该股票: {e}")
            continue
        elapsed_a = round(time.time() - t0, 1)
        issues_a = len(validate_report(report_a))
        comp_a = completeness(report_a)
        print(f"  🅰 基线版: {elapsed_a}s, token={usage_a['total']}, 违规={issues_a}, 完整度={comp_a}/9")

        # 版本 B：模块化（plan + 逐模块）
        try:
            report_b, usage_b, stats_b = modular_analyze(data_md)
        except Exception as e:
            print(f"  ❌ 模块化版失败，跳过该股票: {e}")
            continue
        issues_b = len(stats_b["issues"])
        comp_b = completeness(report_b)
        ratio = usage_b["total"] / max(usage_a["total"], 1)
        print(f"  🅱 模块化版: {stats_b['elapsed']}s, token={usage_b['total']} ({ratio:.1f}× vs A), "
              f"违规={issues_b}, 完整度={comp_b}/9, 截断={stats_b['truncations']}, 调用={stats_b['calls']}次")

        stats_rows.append([code, "A-单次", usage_a["total"], issues_a, comp_a, "", "", elapsed_a])
        stats_rows.append([code, "B-模块化", usage_b["total"], issues_b, comp_b,
                           stats_b["truncations"], ";".join(stats_b["module_fails"]), stats_b["elapsed"]])

        # 双版报告落盘（供抽查）
        (OUT_DIR / f"{code}-A.md").write_text(render_markdown(code, report_a, usage_a, stock_name), encoding="utf-8")
        (OUT_DIR / f"{code}-B.md").write_text(render_markdown(code, report_b, usage_b, stock_name), encoding="utf-8")

    with open(OUT_DIR / "e3-stats.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(stats_rows)
    print(f"\n✅ 材料 → {OUT_DIR}")


if __name__ == "__main__":
    main()
