"""
实验 A：LLM 分析质量 PoC
——用海澜之家(600398)真实数据，测试 DeepSeek 能否生成有信息增量的分析报告
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 将 backend 目录加入 path，以便读取 .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 读取 .env 中的 DEEPSEEK_API_KEY
env_path = Path(__file__).resolve().parent.parent / ".env"
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            os.environ["DEEPSEEK_API_KEY"] = line.split("=", 1)[1].strip()
            break

from openai import OpenAI

STOCK_CODE = "600398"
STOCK_NAME = "海澜之家"


def fetch_stock_data(stock_code: str) -> dict:
    """用 akshare 采集个股全量数据"""
    import akshare as ak

    data = {"stock_code": stock_code, "fetch_time": datetime.now().isoformat()}

    # ── 1. 实时行情 ──
    try:
        spot = ak.stock_individual_info_em(symbol=stock_code)
        info = {}
        for _, row in spot.iterrows():
            info[row["item"]] = row["value"]
        data["spot"] = info
        print(f"  ✅ 实时行情获取成功")
    except Exception as e:
        data["spot"] = {"error": str(e)}
        print(f"  ❌ 实时行情失败: {e}")

    # ── 2. 近 60 日 K 线 ──
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
        kline = ak.stock_zh_a_hist(
            symbol=stock_code, period="daily",
            start_date=start_date, end_date=end_date, adjust="qfq"
        )
        if not kline.empty:
            # 只取最近 60 条
            kline = kline.tail(60)
            records = kline.to_dict(orient="records")
            # 计算技术指标
            closes = kline["收盘"].tolist()
            volumes = kline["成交量"].tolist()

            # 均线
            for period in [5, 10, 20, 60]:
                if len(closes) >= period:
                    ma = sum(closes[-period:]) / period
                    data[f"ma{period}"] = round(ma, 2)

            # RSI (14日)
            if len(closes) >= 15:
                gains, losses = [], []
                for i in range(-14, 0):
                    diff = closes[i] - closes[i-1]
                    gains.append(diff if diff > 0 else 0)
                    losses.append(-diff if diff < 0 else 0)
                avg_gain = sum(gains) / 14
                avg_loss = sum(losses) / 14
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                data["rsi"] = round(rsi, 2)

            # MACD
            if len(closes) >= 26:
                def ema(data_list, period):
                    k = 2 / (period + 1)
                    result = [data_list[0]]
                    for price in data_list[1:]:
                        result.append(price * k + result[-1] * (1 - k))
                    return result
                ema12 = ema(closes, 12)
                ema26 = ema(closes, 26)
                dif = ema12[-1] - ema26[-1]
                dea_list = ema([ema12[i] - ema26[i] for i in range(len(closes))], 9)
                dea = dea_list[-1]
                macd_bar = 2 * (dif - dea)
                data["macd_dif"] = round(dif, 3)
                data["macd_dea"] = round(dea, 3)
                data["macd_bar"] = round(macd_bar, 3)

            # 最近 5 日量比
            if len(volumes) >= 6:
                avg_vol_5 = sum(volumes[-6:-1]) / 5
                data["volume_ratio"] = round(volumes[-1] / avg_vol_5, 2) if avg_vol_5 > 0 else 1.0

            # 最近 5 日涨跌幅
            if len(closes) >= 6:
                data["pct_chg_5d"] = round((closes[-1] / closes[-6] - 1) * 100, 2)
            if len(closes) >= 11:
                data["pct_chg_10d"] = round((closes[-1] / closes[-11] - 1) * 100, 2)

            price_col = "收盘"
            open_col = "开盘" if "开盘" in kline.columns else "开盘价"
            high_col = "最高" if "最高" in kline.columns else "最高价"
            low_col = "最低" if "最低" in kline.columns else "最低价"

            # K 线摘要：最近 5 根日 K
            recent_bars = []
            for r in records[-5:]:
                bar = {
                    "date": str(r.get("日期", "")),
                    "open": r.get(open_col, 0),
                    "close": r.get(price_col, 0),
                    "high": r.get(high_col, 0),
                    "low": r.get(low_col, 0),
                    "volume": r.get("成交量", 0),
                    "pct_chg": r.get("涨跌幅", 0),
                }
                recent_bars.append(bar)
            data["recent_bars"] = recent_bars
            data["latest_close"] = round(closes[-1], 2)

            print(f"  ✅ K线数据获取成功 ({len(records)} 条, 最新收盘价: {closes[-1]:.2f})")
        else:
            print(f"  ⚠️  K线数据为空")
    except Exception as e:
        print(f"  ❌ K线获取失败: {e}")

    # ── 3. 资金流向 ──
    try:
        fund_flow = ak.stock_individual_fund_flow(stock=stock_code, market="sh")
        if not fund_flow.empty:
            latest = fund_flow.tail(5).to_dict(orient="records")
            data["fund_flow_recent_5d"] = latest
            print(f"  ✅ 资金流向获取成功 ({len(latest)} 条)")
        else:
            print(f"  ⚠️  资金流向数据为空")
    except Exception as e:
        print(f"  ❌ 资金流向失败: {e}")

    # ── 4. 个股新闻 ──
    try:
        # 尝试东方财富新闻
        news = ak.stock_news_em(symbol=stock_code)
        if not news.empty:
            recent_news = news.head(10)[["新闻标题", "发布时间"]].to_dict(orient="records")
            data["recent_news"] = [{
                "title": n["新闻标题"],
                "time": str(n["发布时间"])
            } for n in recent_news]
            print(f"  ✅ 新闻获取成功 ({len(recent_news)} 条)")
        else:
            print(f"  ⚠️  新闻数据为空")
    except Exception as e:
        print(f"  ❌ 新闻获取失败: {e}")

    return data


def build_analysis_prompt(data: dict) -> str:
    """基于采集数据构建分析 Prompt"""

    # 构建数据摘要（限制长度，避免 token 浪费）
    sections = []

    # 基础信息
    spot = data.get("spot", {})
    if spot and "error" not in spot:
        sections.append(f"""## 实时行情
- 最新价：{spot.get('最新', 'N/A')} 元
- 今开：{spot.get('今开', 'N/A')}
- 最高：{spot.get('最高', 'N/A')}
- 最低：{spot.get('最低', 'N/A')}
- 成交量：{spot.get('成交量', 'N/A')}
- 换手率：{spot.get('换手率', 'N/A')}%
- 市盈率-动态：{spot.get('市盈率-动态', 'N/A')}
- 总市值：{spot.get('总市值', 'N/A')}
- 流通市值：{spot.get('流通市值', 'N/A')}
- 60日涨跌幅：{spot.get('60日涨跌幅', 'N/A')}%
- 年初至今涨跌幅：{spot.get('年初至今涨跌幅', 'N/A')}%""")

    # 技术指标
    tech_items = []
    for key, label in [
        ("ma5", "MA5"), ("ma10", "MA10"), ("ma20", "MA20"), ("ma60", "MA60"),
        ("rsi", "RSI(14)"), ("macd_dif", "MACD DIF"), ("macd_dea", "MACD DEA"),
        ("macd_bar", "MACD 柱"), ("volume_ratio", "量比"), ("pct_chg_5d", "5日涨跌"),
        ("pct_chg_10d", "10日涨跌"), ("latest_close", "最新收盘价")
    ]:
        if key in data:
            tech_items.append(f"- {label}：{data[key]}")
    if tech_items:
        sections.append("## 技术指标\n" + "\n".join(tech_items))

    # 最近 5 日 K 线
    bars = data.get("recent_bars", [])
    if bars:
        bar_lines = ["## 近 5 日 K 线"]
        for b in bars:
            bar_lines.append(
                f"- {b['date']}：开 {b['open']} 高 {b['high']} 低 {b['low']} "
                f"收 {b['close']} 量 {b['volume']:.0f} 涨幅 {b['pct_chg']:.2f}%"
            )
        sections.append("\n".join(bar_lines))

    # 资金流向
    fund = data.get("fund_flow_recent_5d", [])
    if fund:
        fund_lines = ["## 近 5 日资金流向"]
        for f_item in fund:
            fund_lines.append(
                f"- {f_item.get('日期', 'N/A')}："
                f"主力净流入 {f_item.get('主力净流入-净额', 'N/A')} 万 ｜ "
                f"超大单 {f_item.get('超大单净流入-净额', 'N/A')} 万 ｜ "
                f"大单 {f_item.get('大单净流入-净额', 'N/A')} 万"
            )
        sections.append("\n".join(fund_lines))

    # 近期新闻
    news = data.get("recent_news", [])
    if news:
        news_lines = ["## 近期新闻标题"]
        for n_item in news[:8]:
            news_lines.append(f"- [{n_item['time']}] {n_item['title']}")
        sections.append("\n".join(news_lines))

    data_text = "\n\n".join(sections)

    # ── 完整 Prompt ──
    system_prompt = """你是一个专业的 A 股分析师，擅长结合技术面、资金面和消息面对个股进行综合分析。

## 你的分析原则
1. **基于数据，不编造**：所有分析结论必须基于我提供的行情数据。如果数据不足以支撑某个判断，请明确说"数据不足，无法判断"。
2. **区分事实与推断**：对于数据直接反映的情况，标注为"数据显示"；对于你的推理判断，标注为"分析认为"。
3. **关注风险和催化**：每只股票都要指出潜在风险因素和利好催化因素。
4. **不给出买卖建议**：不要给出"买入""卖出"操作建议，而是给出"关注点"和"观察方向"。
5. **简洁有洞察**：不要罗列数据（数据我已经有了），要给出数据背后的逻辑联系和分析洞察。

## 输出格式
请严格按照以下 JSON 格式输出，不要添加任何 JSON 之外的内容：

{
  "score": 0-100的整数,  // 综合评分
  "decision": "看多/看空/震荡",  // 综合判断
  "summary": "一句话总结当前状态（50字以内）",
  "technical": {
    "trend": "当前趋势描述",
    "key_levels": {"support": [支撑位价格], "resistance": [压力位价格]},
    "indicators_signal": "技术指标综合信号（偏多/偏空/中性）",
    "insight": "技术面的独立洞察（不是复述指标数据，而是解读指标组合的含义）"
  },
  "capital": {
    "main_force": "主力资金方向判断",
    "sentiment": "资金情绪（积极/中性/谨慎/悲观）",
    "insight": "资金面的独立洞察"
  },
  "news": {
    "sentiment": "消息面情绪（偏多/中性/偏空）",
    "key_themes": ["关键词1", "关键词2"],
    "insight": "消息面的独立洞察"
  },
  "risks": ["风险点1", "风险点2"],
  "catalysts": ["利好催化1", "利好催化2"],
  "watch_points": ["值得关注的信号1", "值得关注的信号2"]
}"""

    user_prompt = f"""请分析以下 A 股数据：

股票：{STOCK_NAME}（{STOCK_CODE}）

{data_text}

请基于以上数据，输出你的分析报告（严格按照 JSON 格式）。"""

    return system_prompt, user_prompt


async def main():
    print(f"\n{'='*60}")
    print(f"  实验 A：LLM 分析质量 PoC")
    print(f"  标的：{STOCK_NAME}（{STOCK_CODE}）")
    print(f"  LLM：DeepSeek API")
    print(f"{'='*60}\n")

    # Step 1：采集数据
    print("📡 Step 1/3：采集行情数据...")
    data = fetch_stock_data(STOCK_CODE)

    # 保存原始数据
    raw_path = Path(__file__).parent / "experiment_a_raw_data.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  💾 原始数据保存到: {raw_path}\n")

    # Step 2：构建 Prompt
    print("📝 Step 2/3：构建分析 Prompt...")
    system_prompt, user_prompt = build_analysis_prompt(data)
    print(f"  System Prompt: {len(system_prompt)} 字符")
    print(f"  User Prompt:   {len(user_prompt)} 字符")

    # 打印 user prompt 预览
    print(f"\n{'─'*40}  PROMPT 预览 {'─'*40}")
    print(user_prompt[:1500])
    if len(user_prompt) > 1500:
        print(f"\n... (省略 {len(user_prompt) - 1500} 字符)")
    print(f"{'─'*92}\n")

    # Step 3：调用 LLM
    print("🤖 Step 3/3：调用 DeepSeek API...")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("  ❌ 未找到 DEEPSEEK_API_KEY，跳过 LLM 调用")
        return

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # 低温度，减少幻觉
            max_tokens=2048,
            response_format={"type": "json_object"},  # JSON 模式
        )

        content = response.choices[0].message.content
        usage = response.usage

        print(f"  ✅ API 调用成功")
        print(f"  Token 消耗: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}")
        print(f"\n{'='*60}")
        print(f"  📊 LLM 分析报告")
        print(f"{'='*60}\n")

        # 解析 JSON
        try:
            report = json.loads(content)
            # 美化打印
            print(json.dumps(report, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print("  ⚠️  JSON 解析失败，原始输出：")
            print(content)

        # 保存分析报告
        report_path = Path(__file__).parent / "experiment_a_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n  💾 分析报告保存到: {report_path}")

        # 输出评估维度
        print(f"\n{'='*60}")
        print(f"  📋 质量评估清单")
        print(f"{'='*60}")
        print(f"  [ ] ① 是否有 ≥2 条有独立逻辑的洞察（不是复述数据）？")
        print(f"  [ ] ② 是否有 0 处事实性错误（如把涨说成跌）？")
        print(f'  [ ] ③ 是否有「数据不足，无法判断」等自知表达？')
        print(f"  [ ] ④ JSON 结构是否完整可解析？")
        print(f"  [ ] ⑤ 风险和催化因素是否具体（非泛泛而谈）？")

    except Exception as e:
        print(f"  ❌ API 调用失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())
