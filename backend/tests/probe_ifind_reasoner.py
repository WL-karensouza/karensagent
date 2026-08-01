"""
实验 3+4：Reasoner 分析质量验证 H3.1 + H3.2（适配 2026-07-16 9 模块 Schema）

用 iFind 真实数据组装 prompt → 调 deepseek-reasoner → 生成综合报告
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

from openai import OpenAI
from ifind_call import call

# ── 配置 ──
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
STOCK = {"code": "688981.SH", "name": "中芯国际"}

# deepseek-reasoner / deepseek-chat 均已下架，统一使用 deepseek-v4-flash
REASONER_MODEL = "deepseek-v4-flash"
CHAT_MODEL = "deepseek-v4-flash"

OUTPUT_DIR = Path(__file__).parent / "probe_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Prompt 模板（基于新版 analyze.py 9 模块） ──
SYSTEM_PROMPT = """你是一个经验丰富的 A 股投资顾问。你的读者是普通散户，他们不喜欢研报官腔，
需要的是专业准确但像朋友聊天一样直白易懂的分析。

你必须遵循 **"三步思考链"** 来撰写每一段分析：
  第一步「数据事实化」：从原始数据中提取关键事实，不添加主观判断
  第二步「逻辑推演化」：基于事实进行因果推理，形成分析判断
  第三步「散民口语化」：用散户听得懂的大白话表达，像朋友聊天一样把道理讲透

## 九个分析模块
| 模块 | 内容 |
|------|------|
| 模块1 核心结论 | 一句话评级 + 核心逻辑 + 参考价位 |
| 模块2 公司画像 | 大白话主营业务 + PE/PB 估值温度计 |
| 模块3 财务健康 | 赚钱能力 + 核心指标 + 排雷提示 |
| 模块4 股价走势 | 趋势形态 + 融资融券 + 主力资金 |
| 模块5 北向资金 | 北向资金动向及解读 |
| 模块6 股东筹码 | 增减持动向 + 筹码集中度 |
| 模块7 催化舆情 | 利好/利空事件 + 舆论风向标 |
| 模块8 风险ESG | 风险红绿灯 + ESG 通俗解读 |
| 模块9 操作指南 | 建仓策略 + 止损止盈 + 持有期建议 |

## 核心原则
1. **基于数据，不编造**：结论必须有数据支撑，数据不足时说"数据不足，无法判断"
2. **区分事实与推断**：数据直接反映的标注"数据显示"，推理判断标注"分析认为"
3. **三步思考链铁律**：每段分析必须严格经过「数据事实化 → 逻辑推演化 → 散民口语化」
4. **禁止术语堆砌**：禁止使用深奥的金融学术语（如"戴维斯双击""麦克米伦缺口"），若必须使用需括号解释
5. **不给出买卖指令**：只给出观察方向和分析建议
6. **关注风险和催化**：每只股票必须指出 ≥2 个风险点和 ≥2 个利好催化
7. **说人话**：用散户听得懂的语言写报告"""

REPORT_PROMPT_TEMPLATE = """请对 {name}（{code}）进行综合分析，输出 9 模块 JSON 格式报告。

## 行情数据
{market_data}

## 财务数据
{financials_data}

## 新闻事件
{news_data}

## 风险数据
{risk_data}

## ESG 数据
{esg_data}

## 重大事件
{events_data}

---
请输出 JSON（不要包含 markdown 代码块标记）：
{{
  "score": 0-100,
  "decision": "看多/震荡/看空",
  "module_1_核心结论": {{"rating_sentence": "...", "core_logic": [], "reference_prices": {{"support": "...", "resistance": "..."}}}},
  "module_2_公司画像": {{"business": "...", "valuation": {{"pe_level": "偏低/合理/偏高/极度偏高", "pb_level": "...", "analysis": "..."}}}},
  "module_3_财务健康": {{"profitability": "...", "key_indicators": [], "risk_alerts": []}},
  "module_4_股价走势": {{"trend": "...", "capital_flow": {{"margin_trading": "...", "main_force": "..."}}}},
  "module_5_北向资金": {{"available": false, "trend": "北向资金数据暂不可用", "interpretation": "北向资金数据暂不可用"}},
  "module_6_股东筹码": {{"major_moves": [], "chip_analysis": "..."}},
  "module_7_催化舆情": {{"positive": [], "negative": [], "sentiment": "偏乐观/偏谨慎/中性", "sentiment_reason": "..."}},
  "module_8_风险ESG": {{"risk_level": "低/中/高", "risks": [], "esg": "..."}},
  "module_9_操作指南": {{"buy_strategy": "...", "stop_loss": "...", "take_profit": "...", "holding_period": {{"type": "短线博弈/中短线波段/中长线持有", "reason": "..."}}}},
  "signal_attribution": []
}}"""


def truncate(s, max_len=3000):
    """截断过长文本"""
    if not isinstance(s, str):
        s = str(s)
    return s[:max_len] + "\n...(数据截断)" if len(s) > max_len else s


def fetch_all_data(stock):
    """采集单只股票的全部数据"""
    data = {}
    queries = {
        "market": (
            "get_stock_info",
            f"{stock['code']} 收盘价、涨跌幅、换手率、MACD、RSI、MA5、MA10、MA20、量比",
        ),
        "financials": (
            "get_stock_financials",
            f"{stock['name']} 最新财报ROE、ROA、净利润增速、营收增速、毛利率、净利率、资产负债率、EPS、经营现金流",
        ),
        "risk": (
            "get_risk_indicators",
            f"{stock['code']} 近一年贝塔、波动率、夏普比率、最大回撤",
        ),
        "esg": ("get_esg_data", f"{stock['code']} ESG评级"),
        "events": ("get_stock_events", f"{stock['code']} 近期重大事件"),
    }

    for key, (tool, query) in queries.items():
        print(f"  采集 {key}...", end=" ")
        try:
            r = call("stock", tool, {"query": query})
            if r["ok"]:
                content = r["data"].get("result", {}).get("content", [])
                for c in content:
                    text = c.get("text", "")
                    if text:
                        inner = json.loads(text)
                        answer = inner.get("data", {}).get("answer", "")
                        if answer:
                            data[key] = answer
                            print(f"✅ {len(answer)} 字符")
                            break
                else:
                    data[key] = "(无数据)"
                    print("⚠️ 无数据")
            else:
                data[key] = f"(API错误: {r.get('error')})"
                print(f"❌")
        except Exception as e:
            data[key] = f"(异常: {e})"
            print(f"❌ {e}")

    # 新闻
    print(f"  采集 news...", end=" ")
    try:
        r = call("news", "search_news", {
            "query": f"{stock['name']} {stock['code']}",
            "time_start": "2026-06-01",
            "time_end": "2026-07-10",
            "size": 5,
        })
        if r["ok"]:
            content = r["data"].get("result", {}).get("content", [])
            for c in content:
                text = c.get("text", "")
                if text:
                    inner = json.loads(text)
                    news_data = inner.get("data", {}).get("data", "")
                    if news_data:
                        data["news"] = news_data
                        print(f"✅ {len(news_data)} 字符")
                        break
            else:
                data["news"] = "(无新闻)"
                print("⚠️ 无")
        else:
            data["news"] = f"(API错误)"
            print("❌")
    except Exception as e:
        data["news"] = "(异常)"
        print(f"❌")

    return data


def call_llm(model, system_prompt, user_prompt, label):
    """调 LLM 生成报告"""
    if not DEEPSEEK_API_KEY:
        return {"error": "DEEPSEEK_API_KEY 未配置"}

    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

    print(f"\n  🤖 调用 {model} ({label})...")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=8000,
        )
        content = response.choices[0].message.content
        usage = response.usage
        print(f"    ✅ 完成，tokens: input={usage.prompt_tokens} output={usage.completion_tokens}")

        # 提取 JSON
        json_str = content.strip()
        if json_str.startswith("```"):
            lines = json_str.split("\n")
            json_str = "\n".join(lines[1:-1])
        try:
            report = json.loads(json_str)
            return {"report": report, "raw": content, "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            }}
        except json.JSONDecodeError:
            return {"report": None, "raw": content, "parse_error": True, "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            }}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("实验 3+4：DeepSeek Reasoner 分析质量验证 (v2 9模块)")
    print(f"时间: {datetime.now().isoformat()}")
    print(f"目标: {STOCK['name']} ({STOCK['code']})")
    print("=" * 60)

    # Step 1: 重新采集数据
    print("\n📡 Step 1: 采集 iFind 数据...")
    data = fetch_all_data(STOCK)

    # Step 2: 构造 prompt
    print("\n📝 Step 2: 构造 Prompt...")
    user_prompt = REPORT_PROMPT_TEMPLATE.format(
        name=STOCK["name"],
        code=STOCK["code"],
        market_data=truncate(data.get("market", ""), 2000),
        financials_data=truncate(data.get("financials", ""), 2000),
        news_data=truncate(data.get("news", ""), 2000),
        risk_data=truncate(data.get("risk", ""), 1500),
        esg_data=truncate(data.get("esg", ""), 1000),
        events_data=truncate(data.get("events", ""), 1000),
    )
    print(f"   System prompt: {len(SYSTEM_PROMPT)} 字符")
    print(f"   User prompt: {len(user_prompt)} 字符")

    # Step 3: 调用 reasoner
    print("\n🧠 Step 3: 调用 DeepSeek Reasoner...")
    reasoner_result = call_llm(REASONER_MODEL, SYSTEM_PROMPT, user_prompt, "reasoner+iFind")

    # Step 4: 调用 chat 作为对照
    print("\n📊 Step 4: 调用 DeepSeek Chat 作为对照...")
    chat_result = call_llm(CHAT_MODEL, SYSTEM_PROMPT, user_prompt, "chat+iFind")

    # Step 5: 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "stock": STOCK,
        "timestamp": timestamp,
        "prompts": {"system": SYSTEM_PROMPT, "user": user_prompt},
        "data": {k: v[:500] for k, v in data.items()},
        "reasoner_result": reasoner_result,
        "chat_result": chat_result,
    }

    output_path = OUTPUT_DIR / f"reasoner_report_{timestamp}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 完整结果已保存: {output_path}")

    # Step 6: 打印 reasoner 报告（9 模块格式）
    if reasoner_result.get("report"):
        print("\n" + "=" * 60)
        print("🎯 DeepSeek Reasoner 分析报告 (9模块)")
        print("=" * 60)
        report = reasoner_result["report"]
        print(f"评分: {report.get('score')}")
        print(f"判断: {report.get('decision')}")

        # 模块1 核心结论
        m1 = report.get("module_1_核心结论", {})
        if m1:
            print(f"\n--- 核心结论 ---")
            print(f"  评级: {m1.get('rating_sentence', '')[:200]}")
            for pt in m1.get("core_logic", []):
                print(f"  • {pt[:200]}")

        # 模块3 财务健康
        m3 = report.get("module_3_财务健康", {})
        if m3:
            print(f"\n--- 财务健康 ---")
            print(f"  盈利: {m3.get('profitability', '')[:200]}")
            alerts = m3.get("risk_alerts", [])
            if alerts:
                for a in alerts:
                    print(f"  ⚠️ {a[:200]}")

        # 模块7 催化舆情
        m7 = report.get("module_7_催化舆情", {})
        if m7:
            print(f"\n--- 催化舆情 ---")
            print(f"  舆情: {m7.get('sentiment', '')} — {m7.get('sentiment_reason', '')[:200]}")

        # 模块8 风险ESG
        m8 = report.get("module_8_风险ESG", {})
        if m8:
            print(f"\n--- 风险ESG ---")
            print(f"  风险等级: {m8.get('risk_level')}")
            for r in m8.get("risks", [])[:3]:
                print(f"  • {r.get('type')} ({r.get('level')}): {r.get('desc', '')[:200]}")

        # 模块9 操作指南
        m9 = report.get("module_9_操作指南", {})
        if m9:
            print(f"\n--- 操作指南 ---")
            print(f"  建仓: {m9.get('buy_strategy', '')[:200]}")
            print(f"  止损: {m9.get('stop_loss', '')[:200]}")

        # 信号归因
        sa = report.get("signal_attribution", [])
        if sa:
            print(f"\n--- 信号归因 ---")
            for item in sa[:6]:
                print(f"  {item.get('source')} {item.get('weight',0)*100:.0f}% {item.get('direction')} → {item.get('note', '')[:100]}")

    elif reasoner_result.get("parse_error"):
        print("\n⚠️ Reasoner 返回了非 JSON 格式，原始输出:")
        print(reasoner_result.get("raw", "")[:2000])
    elif reasoner_result.get("error"):
        print(f"\n❌ Reasoner 调用失败: {reasoner_result['error']}")

    print(f"\n⏱️ Token 消耗:")
    if reasoner_result.get("usage"):
        u = reasoner_result["usage"]
        print(f"  Reasoner: input={u['prompt_tokens']} output={u['completion_tokens']}")
    if chat_result.get("usage"):
        u = chat_result["usage"]
        print(f"  Chat:     input={u['prompt_tokens']} output={u['completion_tokens']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
