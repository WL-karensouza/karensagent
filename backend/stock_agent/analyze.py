"""
实验 B：Dogfooding 最小可行分析脚本
用法：
    python backend/stock_agent/analyze.py 600398              # 终端查看报告
    python backend/stock_agent/analyze.py 600398 --push       # 查看 + 推送到飞书
    python backend/stock_agent/analyze.py 600398 --json       # JSON 格式输出
    python backend/stock_agent/analyze.py --watchlist         # 分析自选股列表
    python backend/stock_agent/analyze.py 600398,000858,300750  # 批量分析

连续使用 3 天后评估：
- 今天（Day 1）：____ 是否看了报告？____ 是否影响了操作决策？____
- Day 2：____ 是否主动使用？____ 是否影响了操作决策？____
- Day 3：____ 是否主动使用？____ 是否影响了操作决策？____
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Windows 控制台 UTF-8 编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 将 backend 加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 读取 .env
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()

os.environ.setdefault("DEEPSEEK_API_KEY", env_vars.get("DEEPSEEK_API_KEY", ""))
FEISHU_WEBHOOK_URL = env_vars.get("FEISHU_STOCK_WEBHOOK_URL", "")

from openai import OpenAI


# ═══════════════════════════════════════════
# 1. 数据采集（委托给 fetcher 多数据源层）
# ═══════════════════════════════════════════

from stock_agent.fetcher import fetch_stock_data, validate_data, DataIncompleteError, _lookup_name
from stock_agent.skills import SKILLS


# ═══════════════════════════════════════════
# 2. Prompt 构建（技能驱动）
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════
# Layer 1: 角色定义 + 维度概述
# ═══════════════════════════════════════════
ROLE_DEFINITION = """你是一个经验丰富的 A 股投资顾问。你的读者是普通散户，他们不喜欢研报官腔，
需要的是专业准确但像朋友聊天一样直白易懂的分析。
能用大白话说就别堆术语，必须用术语时要加一句通俗解释。

基于提供的行情数据，对个股进行六维度综合分析。

## 六个分析维度

| 维度 | 关注点 | 数据驱动/LLM推理 |
|------|--------|:---:|
| 技术面 | K线形态、均线排列、MACD/RSI、支撑压力位 | 数据驱动 |
| 资金面 | 主力资金流向、量价配合、换手率活跃度 | 数据驱动 |
| 消息面 | 近期新闻主题、利好/利空分类 | 数据驱动 |
| 基本面 | PE/PB 估值水位、ROE 盈利能力、营收/利润增速 | 数据驱动 |
| 风险面 | 技术/资金/基本面/消息面各维度风险信号汇总评级 | LLM推理 |
| 市场环境 | 个股与大盘/板块的相对强弱、市值风格、估值风格 | 数据+LLM |"""

# ═══════════════════════════════════════════
# Layer 4: 核心分析原则
# ═══════════════════════════════════════════
CORE_RULES = """## 核心原则
1. **基于数据，不编造**：结论必须有数据支撑，数据不足时说"数据不足，无法判断"
2. **区分事实与推断**：数据直接反映的标注"数据显示"，推理判断标注"分析认为"
3. **关注风险和催化**：每只股票必须指出 ≥2 个风险点和 ≥2 个利好催化
4. **不给出买卖建议**：只给出观察方向，不输出"买入""卖出"
5. **简洁有洞察**：不要罗列数据，给出逻辑联系和深层解读
6. **说人话**：用散户听得懂的语言写报告，技术术语必须配通俗解释，insight 里至少有一句直白的生活化判断
7. **综合评估要讲透**：summary 是对整只股票的综合判断段落，不是一句口号。必须说清楚多空双方的博弈焦点、散户最该警惕的风险点、以及判断的主要逻辑链，让散户看完 summary 就能理解这只股票的核心矛盾。"""

# ═══════════════════════════════════════════
# Layer 5: 输出 Schema
# ═══════════════════════════════════════════
OUTPUT_SCHEMA = """## 输出格式（严格 JSON）
{
  "score": 0-100,
  "decision": "看多/震荡/看空",
  "summary": "综合评估段落（100-200字），需包含：①当前多空博弈的核心矛盾是什么 ②散户最该警惕的关键风险 ③整体倾向判断及主要逻辑链。用散户听得懂的大白话写，像朋友聊天一样把道理讲透，避免术语堆砌。",
  "sections": {
    "技术面": {"signal": "偏多/中性/偏空", "insight": "3-4句独立洞察"},
    "资金面": {"sentiment": "积极/中性/谨慎", "insight": "3-4句独立洞察"},
    "消息面": {"sentiment": "偏多/中性/偏空", "key_themes": [], "insight": "基于提供的每一条新闻标题，逐条展开分析其背后的含义和对股价的潜在影响。尽可能覆盖所有新闻，让散户看完报告就不用再去手机搜新闻了。"},
    "基本面": {"signal": "低估/合理/高估", "insight": "3-4句独立洞察"},
    "风险面": {"level": "高/中/低", "top_risks": ["识别到的风险事件（仅列事件本身，如换手率37%异常高）"], "insight": "综合风险评估"},
    "市场环境": {"style_match": "有利/中性/不利", "insight": "3-4句独立洞察"}
  },
  "risks": ["散户注意事项（与top_risks互补：top_risks说什么风险，risks说散户该怎么办。如高换手率下追高容易被套，建议等换手率回落再关注）"],
  "catalysts": ["利好1", "利好2"],
  "watch_points": ["观察点+条件分析（每条不仅是'关注什么'，更要说明'若A则意味什么、散户该怎么做'。例如：'关注明天高开高走还是低开低走——高开高走说明做多意愿强可继续观察，低开低走则短期偏弱不宜追高''关注龙虎榜是游资还是机构主导——游资主导则短线快进快出波动大，机构主导则趋势更稳可持续跟踪'）"],
  "position_advice": {
    "no_position": "空仓者建议（观察等待/可关注/不建议）",
    "has_position": "持仓者建议（继续持有/减仓观察/注意风控）"
  },
  "sniper_points": {
    "ideal_range": "理想观察区间（如'5.0-5.3元附近'，基于当前价+均线支撑+前期低点综合判断）",
    "stop_loss": "关键支撑下沿（如'跌破4.8元需警惕'，破此位中期趋势可能转弱）",
    "take_profit": "上方压力参考（如'5.8-6.0元附近'，接近此区间注意量能是否配合突破）"
  },
  "signal_attribution": [
    {"source": "技术面", "weight": 0.35, "direction": "偏空", "note": "均线空头排列+MACD死叉为主要拖累"},
    {"source": "基本面", "weight": 0.25, "direction": "偏多", "note": "低PE+稳健ROE提供安全边际"}
  ]
}

注意：
- sections 中仅包含数据可用的维度，缺失的维度不要编造
- position_advice 给出的是观察建议，不是买卖指令
- top_risks 和 risks 必须互补不能重复：top_risks 列"识别到的风险事件"，risks 写"散户面对这些风险该怎么办"
- sniper_points 是基于技术面的关键价位参考，不是买卖点位，必须结合当前价格和支撑压力位给出合理区间
- signal_attribution 解释各维度对综合评分的贡献权重和方向，权重之和应为 1.0，列出所有可用维度的归因
- score 基于各维度综合判断，60以上偏乐观，40以下偏悲观
- 每个 section 的 insight 字段必须是你独立分析后的洞察，而非数据罗列"""


def build_system_prompt() -> str:
    """分层组装 system prompt

    Layer 1 → 角色定义 + 维度表
    Layer 3 → 技能分析指令（遍历 SkillMeta 注册表注入 instructions）
    Layer 4 → 核心分析原则
    Layer 5 → 输出 JSON Schema（含 sniper_points + signal_attribution）
    """
    from stock_agent.skills import SKILLS  # 延迟导入，避免循环依赖

    layers = [ROLE_DEFINITION]

    # Layer 3: 注入每个技能的自然语言分析指令
    skill_parts = []
    for skill in SKILLS:
        skill_parts.append(f"### {skill.display_name}\n{skill.instructions}")
    layers.append("## 各维度分析指令\n\n" + "\n\n".join(skill_parts))

    layers.append(CORE_RULES)
    layers.append(OUTPUT_SCHEMA)

    return "\n\n".join(layers)


def build_prompt(data: dict) -> str:
    """构建 user prompt——遍历所有技能的产出"""
    name = data.get("stock_name", data["stock_code"])
    code = data["stock_code"]
    parts = [f"## {name}（{code}）\n"]

    # 基础行情
    basics = []
    for k, label in [("latest_close", "最新收盘价"), ("pct_5d", "5日涨跌%"),
                      ("pct_10d", "10日涨跌%"), ("pct_20d", "20日涨跌%"),
                      ("volume_ratio", "量比")]:
        if k in data:
            basics.append(f"- {label}：{data[k]}")
    if basics:
        parts.append("### 基础行情\n" + "\n".join(basics))

    # K线
    bars = data.get("recent_bars", [])
    if bars:
        lines = ["### 近 5 日 K 线"]
        for b in bars:
            lines.append(f"- {b['date']} | 开{b['open']} 高{b['high']} 低{b['low']} 收{b['close']} | 量{b['volume']} | {b['pct_chg']:+.2f}%")
        parts.append("\n".join(lines))

    # 技能产出：遍历注册表中的每个技能，收集分析数据
    for skill in SKILLS:
        result = skill(data)
        if result.get("enabled"):
            section = result["section"]
            parts.append(f"\n### {section['title']}")
            hint = section.get("hint", "")
            fields = section.get("fields", {})
            for fk, fv in fields.items():
                if isinstance(fv, list):
                    parts.append(f"- {fk}:")
                    for item in fv:
                        parts.append(f"  - {item}")
                else:
                    parts.append(f"- {fk}：{fv}")
            if hint:
                parts.append(f"\n> {hint}")

    # 注明哪些技能因数据不足而未输出
    skipped = []
    for skill in SKILLS:
        result = skill(data)
        if not result.get("enabled"):
            skipped.append(f"{skill.name}: {result.get('reason', '未知')}")
    if skipped:
        parts.append(f"\n### 不可用数据\n" + "\n".join(f"- {s}" for s in skipped))

    return "\n".join(parts)


# ═══════════════════════════════════════════
# 3. LLM 调用
# ═══════════════════════════════════════════

def analyze(data: dict) -> tuple[dict, dict]:
    """调用 DeepSeek 分析，返回 (report, usage)。调用前校验数据完整性。"""
    # 数据守卫：缺失关键字段时拒绝调用LLM，防止幻觉
    validate_data(data)

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，请检查 .env 文件")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    user_prompt = build_prompt(data)

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,  # 股票分析非创意写作，要求输出确定、可复现，降低幻觉风险
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }

    # 解析 JSON
    try:
        report = json.loads(content)
    except json.JSONDecodeError:
        # 尝试修复：去掉 markdown code block 标记
        content = content.replace("```json", "").replace("```", "").strip()
        report = json.loads(content)

    return report, usage


# ═══════════════════════════════════════════
# 4. 报告渲染（Markdown）
# ═══════════════════════════════════════════

def render_markdown(data: dict, report: dict, usage: dict) -> str:
    """渲染为 Markdown 报告"""
    name = data.get("stock_name", data["stock_code"])
    code = data["stock_code"]
    score = report.get("score", "N/A")
    decision = report.get("decision", "N/A")
    emoji_map = {"看多": "🟢", "震荡": "🟡", "看空": "🔴"}
    emoji = emoji_map.get(decision, "⚪")

    sections = report.get("sections", {})
    tech = sections.get("技术面", {})
    capital = sections.get("资金面", {})
    news_r = sections.get("消息面", {})
    fundamental = sections.get("基本面", {})
    risk = sections.get("风险面", {})
    market_env = sections.get("市场环境", {})

    # 评分条
    bar_len = 20
    if isinstance(score, int):
        filled = int(score / 100 * bar_len)
    else:
        filled = 0
    bar = "█" * filled + "░" * (bar_len - filled)

    out = []
    out.append(f"# {emoji} {name}（{code}）分析报告")
    out.append("")
    out.append("```")
    out.append(f"综合评分：{score}/100  [{bar}]")
    out.append(f"综合判断：{decision}")
    out.append("```")
    out.append("")
    out.append(f"> {report.get('summary', '')}")
    out.append("")
    out.append("---")

    n = 0  # 章节序号

    # 1. 技术面
    if tech:
        n += 1
        t_signal = tech.get("signal", "N/A")
        t_insight = tech.get("insight", "")
        out.append("")
        out.append("")
        out.append(f"**{n}. 📊 技术面（{t_signal}）**")
        out.append("")
        out.append("> " + str(t_insight))

    # 2. 资金面
    if capital:
        n += 1
        c_sentiment = capital.get("sentiment") or "N/A"
        c_insight = capital.get("insight") or "暂无资金面数据"
        out.append("")
        out.append("")
        out.append(f"**{n}. 💰 资金面（{c_sentiment}）**")
        out.append("")
        out.append("> " + str(c_insight))

    # 3. 消息面
    if news_r:
        n += 1
        n_sentiment = news_r.get("sentiment") or "N/A"
        themes = news_r.get("key_themes", [])
        n_insight = news_r.get("insight") or ""
        out.append("")
        out.append("")
        out.append(f"**{n}. 📰 消息面（{n_sentiment}）**")
        if themes:
            out.append("**关键词**：" + "、".join(themes))
        out.append("")
        out.append("> " + str(n_insight))

    # 4. 基本面
    if fundamental:
        n += 1
        f_signal = fundamental.get("signal") or "N/A"
        f_insight = fundamental.get("insight") or ""
        out.append("")
        out.append("")
        out.append(f"**{n}. 📈 基本面（{f_signal}）**")
        out.append("")
        out.append("> " + str(f_insight))

    # 5. 风险面
    if risk:
        n += 1
        r_level = risk.get("level") or "N/A"
        r_insight = risk.get("insight") or ""
        top_risks = risk.get("top_risks", [])
        out.append("")
        out.append("")
        out.append(f"**{n}. 🚨 风险面（等级：{r_level}）**")
        if top_risks:
            for tr in top_risks:
                out.append("- " + str(tr))
        out.append("")
        out.append("> " + str(r_insight))

    # 6. 市场环境
    if market_env:
        n += 1
        m_style = market_env.get("style_match") or "N/A"
        m_insight = market_env.get("insight") or ""
        out.append("")
        out.append("")
        out.append(f"**{n}. 🌐 市场环境（{m_style}）**")
        out.append("")
        out.append("> " + str(m_insight))

    # 7. 风险提示
    risks_list = report.get("risks", [])
    if risks_list:
        n += 1
        out.append("")
        out.append("---")
        out.append("")
        out.append("")
        out.append(f"**{n}. 风险提示**")
        for r in risks_list:
            out.append("- " + str(r))

    # 8. 利好催化
    catalysts_list = report.get("catalysts", [])
    if catalysts_list:
        n += 1
        out.append("")
        out.append("")
        out.append(f"**{n}. ✨ 利好催化**")
        for c in catalysts_list:
            out.append("- " + str(c))

    # 9. 观察建议
    pos = report.get("position_advice", {})
    if pos:
        n += 1
        out.append("")
        out.append("")
        out.append(f"**{n}. 📋 观察建议**")
        no_pos = pos.get("no_position", "")
        has_pos = pos.get("has_position", "")
        if no_pos:
            out.append(f"- 空仓者：{no_pos}")
        if has_pos:
            out.append(f"- 持仓者：{has_pos}")

    # 10. 关注点
    watch_list = report.get("watch_points", [])
    if watch_list:
        n += 1
        out.append("")
        out.append("")
        out.append(f"**{n}. 🔍 关注点**")
        for w in watch_list:
            out.append("- " + str(w))

    # 11. 关键价位
    sniper = report.get("sniper_points", {})
    if sniper:
        n += 1
        out.append("")
        out.append("")
        out.append(f"**{n}. 🎯 关键价位参考**")
        ideal = sniper.get("ideal_range", "")
        stop = sniper.get("stop_loss", "")
        profit = sniper.get("take_profit", "")
        if ideal:
            out.append(f"- 理想观察区间：{ideal}")
        if stop:
            out.append(f"- 风控参考：{stop}")
        if profit:
            out.append(f"- 上方压力参考：{profit}")

    # 12. 信号归因
    attributions = report.get("signal_attribution", [])
    if attributions:
        n += 1
        out.append("")
        out.append("")
        out.append(f"**{n}. 📊 信号归因**")
        out.append("")
        for a in attributions:
            src = a.get("source", "")
            w = a.get("weight", 0)
            d = a.get("direction", "")
            note_text = a.get("note", "")
            d_emoji = {"偏多": "🟢", "偏空": "🔴", "中性": "⚪"}.get(d, "")
            out.append(f"{d_emoji} {src} · {w*100:.0f}% · {d} → {note_text}")

    out.append("")
    out.append("---")
    out.append("*生成时间：" + datetime.now().strftime("%Y-%m-%d %H:%M") + "*")
    out.append("*以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。*")

    return "\n".join(out)


# ═══════════════════════════════════════════
# 5. 飞书推送
# ═══════════════════════════════════════════

def push_to_feishu(md_report: str, stock_name: str, stock_code: str):
    """推送到飞书（复用现有 notifier）"""
    import requests

    if not FEISHU_WEBHOOK_URL:
        print("  ⚠️ 未配置 FEISHU_WEBHOOK_URL，跳过飞书推送")
        return False

    # 去掉 H1 标题行（飞书卡片已有 header，避免重复）
    lines = md_report.split("\n")
    start = 2 if len(lines) > 1 and lines[1] == "" else 1
    card_body = "\n".join(lines[start:])

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{stock_name}（{stock_code}）分析报告"},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": card_body},
                {"tag": "note", "elements": [
                    {"tag": "plain_text", "content": f"Karens Agent · 股票分析 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
                ]}
            ]
        }
    }

    try:
        r = requests.post(FEISHU_WEBHOOK_URL, json=payload, timeout=10)
        if r.status_code == 200:
            print("  ✅ 飞书推送成功")
            return True
        else:
            print(f"  ❌ 飞书推送失败: {r.status_code} {r.text}")
            return False
    except Exception as e:
        print(f"  ❌ 飞书推送失败: {e}")
        return False


# ═══════════════════════════════════════════
# 6. 主入口
# ═══════════════════════════════════════════

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="A 股个股分析工具（实验 B）")
    parser.add_argument("stocks", nargs="?", default="600398",
                        help="股票代码，多个用逗号分隔，如 600519,000858")
    parser.add_argument("--push", action="store_true", help="推送到飞书")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--watchlist", action="store_true", help="使用默认自选股列表")
    args = parser.parse_args()

    # 默认自选股
    DEFAULT_WATCHLIST = ["600398", "600519", "000858"]

    if args.watchlist:
        codes = DEFAULT_WATCHLIST
    else:
        codes = [c.strip() for c in args.stocks.split(",") if c.strip()]

    for code in codes:
        print(f"\n{'='*60}")
        print(f"  🔍 分析 {_lookup_name(code)}（{code}）")
        print(f"{'='*60}")

        # 采集
        print("📡 采集数据...")
        data = fetch_stock_data(code)

        if "kline_error" in data and "latest_close" not in data:
            print(f"  ❌ K线数据采集失败（已尝试所有数据源），跳过 {code}")
            continue

        # 分析
        print("🤖 LLM 分析...")
        try:
            report, usage = analyze(data)
        except DataIncompleteError as e:
            print(f"  ❌ 数据不完整，拒绝调用LLM: {e}")
            continue
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            continue

        print(f"  ✅ Token: {usage['total']} | 评分: {report.get('score')} | {report.get('decision')}")

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            md = render_markdown(data, report, usage)
            print(f"\n{md}")

        # 保存
        out_dir = Path(__file__).parent / "reports"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_file = out_dir / f"{code}_{ts}.md"
        out_file.write_text(md, encoding="utf-8")
        print(f"\n  💾 保存: {out_file}")

        # 飞书推送
        if args.push:
            push_to_feishu(md, data.get("stock_name", code), code)

    print(f"\n{'='*60}")
    print(f"  📋 实验 B 使用记录")
    print(f"  今天是第 ___ 天")
    print(f"  是否看了报告？___  是否影响了操作决策？___")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
