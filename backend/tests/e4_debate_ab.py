"""E4 实验：双角色跨模型辩论原型执行（须在 E3 跑完后执行，避免 SKILL 限速撞车）

股票集：6 只（含港股），每只：基线单次分析 vs 双模型辩论
指标：共识达成率/轮数 / 初始模型分歧 / score 调整幅度 / validator 违规 / 双模型 token / 耗时
产出：docs/e4-blind-review/
  e4-stats.csv           客观指标汇总
  {code}-baseline.md     基线报告
  {code}-debate.md       辩论版报告
  {code}-debate.json     辩论过程 stats（轮数/共识/初始分歧，供抽查）
"""
import csv
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from stock_agent.analyze import analyze
from stock_agent.debate import debate_analyze
from stock_agent.render import render_markdown
from stock_agent.skill.report import generate_report_sync
from stock_agent.validator import validate_report

STOCKS = ["688825"]  # 用户指定：测多轮辩论质量（高争议股票，逼出真实分歧驳论）
OUT_DIR = BACKEND.parent / "docs" / "e4-blind-review"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats_rows = [["stock", "version", "score", "decision", "validator_issues",
                   "deepseek_token", "qwen_token", "total_token",
                   "rounds", "consensus", "elapsed_s"]]

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

        # 版本 A：基线单次分析
        t0 = time.time()
        try:
            report_a, usage_a = analyze(data_md)
        except Exception as e:
            print(f"  ❌ 基线版失败，跳过该股票: {e}")
            continue
        elapsed_a = round(time.time() - t0, 1)
        issues_a = len(validate_report(report_a))
        print(f"  🅰 基线版: {elapsed_a}s, score={report_a.get('score')}/{report_a.get('decision')}, "
              f"token={usage_a['total']}, 违规={issues_a}")

        # 基线版产物独立先落盘（辩论版失败也不丢基线数据）
        stats_rows.append([code, "A-基线", report_a.get("score"), report_a.get("decision"),
                           issues_a, usage_a["total"], "", usage_a["total"], "", "", elapsed_a])
        (OUT_DIR / f"{code}-baseline.md").write_text(
            render_markdown(code, report_a, usage_a, stock_name), encoding="utf-8")

        # 版本 B：双模型辩论
        try:
            report_b, usage_b, stats_b = debate_analyze(data_md)
        except Exception as e:
            print(f"  ❌ 辩论版失败，跳过该股票: {e}")
            continue
        issues_b = len(stats_b["issues"])
        ini, fin = stats_b["initial"], stats_b["final"]
        print(f"  🅱 辩论版: {stats_b['elapsed']}s, score={fin['score']}/{fin['decision']} "
              f"(初始: A {ini['a_score']}/{ini['a_decision']} vs B {ini['b_score']}/{ini['b_decision']}), "
              f"轮数={stats_b['rounds']}, 共识={stats_b['consensus']}（第{stats_b.get('consensus_round')}轮）, "
              f"证据命中率={stats_b.get('citation_hit')}, "
              f"token: A={usage_b['model_a']['total']} B={usage_b['model_b']['total']}, 违规={issues_b}")

        total_b = usage_b["model_a"]["total"] + usage_b["model_b"]["total"]
        stats_rows.append([code, "B-辩论", fin["score"], fin["decision"], issues_b,
                           usage_b["model_a"]["total"], usage_b["model_b"]["total"], total_b,
                           stats_b["rounds"], stats_b["consensus"], stats_b["elapsed"]])

        # 辩论版产物落盘：报告 + 辩论过程
        (OUT_DIR / f"{code}-debate.md").write_text(
            render_markdown(code, report_b, {"total": total_b}, stock_name), encoding="utf-8")
        (OUT_DIR / f"{code}-debate.json").write_text(
            json.dumps(stats_b, ensure_ascii=False, indent=2), encoding="utf-8")

    with open(OUT_DIR / "e4-stats.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(stats_rows)
    print(f"\n✅ 材料 → {OUT_DIR}")


if __name__ == "__main__":
    main()
