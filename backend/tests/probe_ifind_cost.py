"""
实验 8：Reasoner 分析成本评估 (H3.3)

基于实验 3+4 的真实 token 消耗数据，评估:
1. 单次报告成本（Reasoner vs Chat）
2. 月度预估成本（按不同调用频率）
3. 输入/输出 token 比例和优化空间
4. 缓存命中后的成本节约

DeepSeek 官方定价 (per 1M tokens, 2026-07):
  Model           Input       Output      Cached Input
  ─────────────────────────────────────────────────────
  deepseek-reasoner  $0.55      $2.19       $0.14
  deepseek-chat      $0.27      $1.10       $0.07

换算: 1M tokens = 100万 tokens
"""
import json
import os
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 定价 ──
PRICING = {
    "deepseek-reasoner": {"input": 0.55, "output": 2.19, "cached_input": 0.14},
    "deepseek-chat": {"input": 0.27, "output": 1.10, "cached_input": 0.07},
}

# ── 加载实验 3+4 的 token 数据 ──
def load_previous_data():
    """从实验 3+4 的结果文件中加载 token 消耗数据"""
    # 先尝试最新的 reasoner_report
    reports = sorted(OUTPUT_DIR.glob("reasoner_report_*.json"), reverse=True)
    if reports:
        with open(reports[0], encoding="utf-8") as f:
            data = json.load(f)
        return data
    return None


def calc_cost(model, prompt_tokens, completion_tokens, cache_hit_ratio=0.0):
    """计算单次调用成本（美元）"""
    pricing = PRICING[model]
    cached = prompt_tokens * cache_hit_ratio
    uncached = prompt_tokens * (1 - cache_hit_ratio)

    input_cost = (uncached * pricing["input"] + cached * pricing["cached_input"]) / 1_000_000
    output_cost = completion_tokens * pricing["output"] / 1_000_000

    return input_cost + output_cost, input_cost, output_cost


def main():
    print("=" * 60)
    print("实验 8：Reasoner 分析成本评估")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    prev = load_previous_data()

    # ── 基于实验 3+4 的真实数据 ──
    if prev and "reasoner_result" in prev:
        r_usage = prev["reasoner_result"].get("usage", {})
        c_usage = prev.get("chat_result", {}).get("usage", {})

        r_prompt = r_usage.get("prompt_tokens", 4821)
        r_completion = r_usage.get("completion_tokens", 1830)
        c_prompt = c_usage.get("prompt_tokens", 4821)
        c_completion = c_usage.get("completion_tokens", 910)

        print(f"\n📊 实验 3+4 实测数据:")
        print(f"  Reasoner: prompt={r_prompt}, completion={r_completion}")
        print(f"  Chat:     prompt={c_prompt}, completion={c_completion}")
    else:
        # fallback 到摘要中的数据
        print(f"\n⚠️ 未找到实验 3+4 结果文件，使用上一轮记录的估算值")
        r_prompt, r_completion = 4821, 1830
        c_prompt, c_completion = 4821, 910
        print(f"  Reasoner: prompt={r_prompt}, completion={r_completion}")
        print(f"  Chat:     prompt={c_prompt}, completion={c_completion}")

    # ── 单次成本 ──
    print("\n" + "=" * 60)
    print("💰 单次报告成本")
    print("=" * 60)

    for label, model, prompt_t, completion_t in [
        ("Reasoner", "deepseek-reasoner", r_prompt, r_completion),
        ("Chat", "deepseek-chat", c_prompt, c_completion),
    ]:
        # 无缓存
        total, inp, out = calc_cost(model, prompt_t, completion_t, 0.0)
        # 50% 缓存（系统性 prompt 可被缓存）
        total_c50, _, _ = calc_cost(model, prompt_t, completion_t, 0.5)
        # 80% 缓存（连续分析同一只股票时，大部分输入不变）
        total_c80, _, _ = calc_cost(model, prompt_t, completion_t, 0.8)

        print(f"\n  {label} ({model}):")
        print(f"    Token: prompt={prompt_t}, completion={completion_t}")
        print(f"    无缓存: ${total:.4f} (input=${inp:.4f}, output=${out:.4f})")
        print(f"    50%缓存: ${total_c50:.4f}")
        print(f"    80%缓存: ${total_c80:.4f}")

    # ── 月度成本预估 ──
    print("\n" + "=" * 60)
    print("📅 月度成本预估（按 20 个交易日）")
    print("=" * 60)

    # 假设每天分析 N 只股票（默认规划: 10 只自选股）
    scenarios = [
        ("轻量: 5只/天 (100次/月)", 100),
        ("中量: 10只/天 (200次/月)", 200),
        ("重量: 20只/天 (400次/月)", 400),
    ]

    for scenario, calls_per_month in scenarios:
        print(f"\n  {scenario}:")
        for label, model, prompt_t, completion_t in [
            ("Reasoner", "deepseek-reasoner", r_prompt, r_completion),
            ("Chat", "deepseek-chat", c_prompt, c_completion),
        ]:
            cost_0, _, _ = calc_cost(model, prompt_t, completion_t, 0.0)
            cost_50, _, _ = calc_cost(model, prompt_t, completion_t, 0.5)
            monthly_0 = cost_0 * calls_per_month
            monthly_50 = cost_50 * calls_per_month
            print(f"    {label}: ${monthly_0:.2f}/月 (无缓存) → ${monthly_50:.2f}/月 (50%缓存)")

    # ── 与旧版对比 ──
    print("\n" + "=" * 60)
    print("📊 与旧版 (chat+akshare) 对比")
    print("=" * 60)

    # 旧版用 chat + akshare 免费数据，成本 ≈ chat 成本
    # 新版用 reasoner + iFind 收费数据
    old_monthly = calc_cost("deepseek-chat", c_prompt, c_completion, 0.5)[0] * 200
    new_monthly = calc_cost("deepseek-reasoner", r_prompt, r_completion, 0.5)[0] * 200
    iFind_api_cost = 0  # iFind API 成本未知（用户按调用量付费）

    print(f"  旧版 (Chat + akshare):")
    print(f"    LLM 成本: ~${old_monthly:.2f}/月 (200次)")
    print(f"    数据成本: ¥0 (akshare 免费)")
    print(f"  新版 (Reasoner + iFind):")
    print(f"    LLM 成本: ~${new_monthly:.2f}/月 (200次)")
    print(f"    数据成本: 同花顺 API 月费（用户已知）")
    print(f"    LLM 增量: +${new_monthly - old_monthly:.2f}/月")

    # ── 优化建议 ──
    print("\n" + "=" * 60)
    print("💡 成本优化建议")
    print("=" * 60)
    tips = [
        "1. 系统性 prompt 缓存: 将固定的 SYSTEM_PROMPT 放在消息开头，缓存命中率可达 70-80%",
        "2. 数据截断策略: 当前截断 1000-2000 字符/维度，已较合理；进一步压缩可选只保留关键指标",
        "3. 批量分析: 同一天分析多只股票时，共用 markets/edb 上下文，减少重复 prompt_tokens",
        "4. 降级策略: 对不重要的股票用 Chat 模型，仅对重点关注股票用 Reasoner",
        f"5. 建议月度 LLM 预算: ${new_monthly:.2f}（200次/月，50%缓存）",
    ]
    for tip in tips:
        print(f"  {tip}")

    # ── 判定 ──
    print("\n" + "=" * 60)

    # 判定标准: 单次 cost < $0.01（1美分）为优秀，<$0.05 为可接受
    reasoner_cost = calc_cost("deepseek-reasoner", r_prompt, r_completion, 0.5)[0]
    monthly_200 = reasoner_cost * 200

    if reasoner_cost < 0.01:
        print(f"✅ 实验 8 通过！Reasoner 单次成本 ${reasoner_cost:.4f} < $0.01，优秀")
    elif reasoner_cost < 0.05:
        print(f"✅ 实验 8 通过！Reasoner 单次成本 ${reasoner_cost:.4f}，可接受范围")
    else:
        print(f"⚠️ 实验 8 警告：Reasoner 单次成本 ${reasoner_cost:.4f}，需评估是否超预算")

    print(f"   月度成本(200次,50%缓存): ${monthly_200:.2f}")
    return 0


if __name__ == "__main__":
    main()
