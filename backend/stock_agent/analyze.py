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

# 读取 .env（缺失时警告并继续，不能 exit —— 本模块会被 stock_api 导入复用 push_to_feishu）
env_path = Path(__file__).resolve().parent.parent / ".env"
env_vars = {}
if not env_path.exists():
    print(f"⚠️ 未找到 .env 文件: {env_path}，LLM 分析与飞书推送将不可用", file=sys.stderr)
else:
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
# 1. 数据采集（委托给新 fetcher 系统）
# ═══════════════════════════════════════════

from stock_agent.models import DataIncompleteError  # noqa: F401 — 从 models 统一导出


# ═══════════════════════════════════════════
# 2. Prompt 构建（新 fetcher 驱动）
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════
# Layer 1: 角色定义 + 三步思考链 + 9 模块概述
# ═══════════════════════════════════════════
ROLE_DEFINITION = """你是一个经验丰富的 A 股投资顾问。你的读者是普通散户，他们不喜欢研报官腔，
需要的是专业准确但像朋友聊天一样直白易懂的分析。

你必须遵循 **"三步思考链"** 来撰写每一段分析：
  第一步「数据事实化」：从原始数据中提取关键事实，不添加主观判断
  第二步「逻辑推演化」：基于事实进行因果推理，形成分析判断
  第三步「散民口语化」：用散户听得懂的大白话表达，像朋友聊天一样把道理讲透

分析所用的原始数据由同花顺 iFinD SKILL 提供，包含十个维度：实时行情、基本信息与估值、
行情走势、财务数据、股东结构、风险评估、ESG 评级、重大事件、近期新闻、公司公告。

基于提供的综合数据报告，按以下 9 个模块组织分析结果。

## 九个分析模块

| 模块 | 内容 | 对应 iFinD 数据 |
|------|------|----------------|
| 模块1 核心结论与操作建议 | 一句话评级 + 核心逻辑要点 + 参考价位 | 综合全部数据 |
| 模块2 公司画像与估值定位 | 大白话主营业务 + PE/PB 估值温度计 | 基本信息与估值 |
| 模块3 财务健康状况 | 赚钱能力 + 核心指标 + 排雷提示 | 财务数据 |
| 模块4 股价走势与资金动向 | 趋势形态 + 融资融券 + 主力资金 | 实时行情、行情走势 |
| 模块5 北向资金/主力拆解 | 北向资金/沪深港通动向及解读 | 实时行情、行情走势 |
| 模块6 股东结构与筹码集中度 | 增减持动向 + 筹码集中/分散判断 | 股东结构 |
| 模块7 催化剂与近期舆情 | 利好/利空事件 + 舆论风向标 | 重大事件、近期新闻、公司公告 |
| 模块8 风险评估与 ESG 表现 | 风险红绿灯 + ESG 通俗解读 | 风险评估、ESG 评级 |
| 模块9 散户实战操作指南 | 分批建仓策略 + 止损止盈 + 持有期建议 | 综合全部数据 |"""

# ═══════════════════════════════════════════
# Layer 2: 核心分析原则
# ═══════════════════════════════════════════
CORE_RULES = """## 核心原则
1. **基于数据，不编造**：结论必须有数据支撑，数据不足时说"数据不足，无法判断"
2. **区分事实与推断**：数据直接反映的标注"数据显示"，推理判断标注"分析认为"
3. **三步思考链铁律**：每段分析文字必须严格经过「数据事实化 → 逻辑推演化 → 散民口语化」三个步骤，禁止跳过前两步直接给结论
4. **禁止术语堆砌**：禁止使用深奥的金融学术语（如"戴维斯双击""麦克米伦缺口""Beta 中性""Gamma 对冲"等），若必须使用专业术语，需在括号内加上一句大白话解释
5. **不给出买卖指令**：只给出观察方向和分析建议，不输出"买入""卖出""加仓""减仓"等直接交易指令
6. **关注风险和催化**：每只股票必须指出 ≥2 个风险点和 ≥2 个利好催化
7. **说人话**：不要罗列数据，给出逻辑联系和深层解读。用散户听得懂的语言写报告，分析结论里至少有一句直白的生活化判断
8. **财务分析要厚实**：模块3 财务健康必须覆盖盈利能力、成长趋势、偿债安全、现金流质量等维度，让散户读完就能判断这公司财务安不安全、赚不赚钱、利润真不真实"""

# ═══════════════════════════════════════════
# Layer 3: 输出 Schema（9 模块 JSON）
# ═══════════════════════════════════════════
OUTPUT_SCHEMA = """## 输出格式（严格 JSON）

{
  "score": 0-100,
  "decision": "看多/震荡/看空",

  "module_1_核心结论": {
    "rating_sentence": "一句话评级，必须包含趋势判断 + 风险提示 + 建议方向（如'短期趋势向好但估值偏高，建议观望'）",
    "core_logic": [
      "核心要点1：一句话，数据事实 + 逻辑判断",
      "核心要点2：...",
      "核心要点3：..."
    ],
    "reference_prices": {
      "support": "支撑位及依据（如'5.0元附近（60日均线+前期低点）'），数据不足则标注'数据不足无法判断'",
      "resistance": "压力位及依据（如'5.8-6.0元（前期密集成交区）'），数据不足则标注'数据不足无法判断'"
    }
  },

  "module_2_公司画像": {
    "business": "大白话主营业务描述，剥离枯燥的经营范围文本，说清楚公司靠什么赚钱。示例风格：'主要收入来源于广告推广和增值电信服务，简单说就是帮其他公司在自己的平台上打广告抽佣金，同时向用户卖会员和虚拟道具'。数据不足则标注'基本信息不可用'",
    "valuation": {
      "pe_level": "偏低/合理/偏高/极度偏高",
      "pb_level": "偏低/合理/偏高/极度偏高",
      "analysis": "将 PE/PB 与历史水平及行业平均对比，2-3 句话说清当前估值在什么水位，散户现在进场是捡便宜还是接盘"
    }
  },

  "module_3_财务健康": {
    "profitability": "一句话概括赚钱能力（如'越赚越多''增收不增利''利润持续下滑'），必须包含营收和净利润的同比/环比变化方向",
    "key_indicators": [
      {"name": "毛利率", "value": "XX%", "trend": "连续上升/下滑/稳定", "verdict": "说明产品竞争力/赚钱效率"},
      {"name": "ROE", "value": "XX%", "trend": "...", "verdict": "说明股东回报高低"},
      {"name": "资产负债率", "value": "XX%", "trend": "...", "verdict": "说明公司欠债多不多、财务稳不稳"},
      {"name": "经营现金流/净利润", "value": "X.X", "trend": "...", "verdict": "大于1是真金白银，小于1是纸面富贵"}
    ],
    "risk_alerts": [
      "异常财务信号及白话解读（如'应收账款增速远超营收增速——钱没收回来，利润可能是纸面富贵'）。无异常则写'暂无明显财务风险信号'"
    ]
  },

  "module_4_股价走势": {
    "trend": "总结近期股价走势特征（如'放量突破前期平台''缩量回调至60日均线附近''高位震荡换手充分'），2-3 句话说清楚当前形态",
    "capital_flow": {
      "margin_trading": "融资融券分析（如'融资余额持续上升，杠杆资金正在加仓看多''融资净偿还，杠杆资金在撤退'）。数据不足则标注'数据不可用'",
      "main_force": "主力资金动向（如'近5日主力净流入XX万，主力在悄悄吸筹''主力净流出，大资金在出货'）。数据不足则标注'数据不可用'"
    }
  },

  "module_5_北向资金": {
    "available": true,
    "trend": "北向资金/沪深港通动向（如'北向资金连续3日净买入，累计净流入X亿'）。若 available 为 false，此字段写'北向资金数据暂不可用'",
    "interpretation": "用散户听得懂的话解读（如'外资在逢低捡便宜，说明这个价位机构认可'或'外资和融资盘同时增加，内外资都在追，短线可能过热注意回调'）。若 available 为 false，此字段写'北向资金数据暂不可用'"
  },

  "module_6_股东筹码": {
    "major_moves": [
      {"entity": "高管张三", "action": "减持X万股", "date": "2024-06-XX", "signal": "偏多/偏空/中性", "reason": "一句白话解读"}
    ],
    "chip_analysis": "筹码集中度判断（如'股东户数连续减少 + 户均持股上升 → 筹码趋于集中，主力可能在吸筹'或'股东户数大幅增加 → 筹码分散，散户接盘迹象明显'）。数据不足则说清楚哪些信息缺失"
  },

  "module_7_催化舆情": {
    "positive": ["利好事件 + 对股价的潜在影响分析（如'公司刚中标XX亿大单，未来两年业绩有保障'）"],
    "negative": ["利空事件 + 对股价的潜在影响分析（如'收到监管问询函，需关注是否存在财务合规问题'）"],
    "sentiment": "偏乐观/偏谨慎/中性",
    "sentiment_reason": "一句话总结近期媒体和研报的整体态度倾向及其原因"
  },

  "module_8_风险ESG": {
    "risk_level": "低/中/高",
    "risks": [
      {"type": "市场风险/退市风险/商誉减值风险/流动性风险/政策风险/其他", "level": "高/中/低", "desc": "白话描述风险及对散户的实际影响"}
    ],
    "esg": "ESG 通俗解读，不堆砌 E/S/G 具体分数，说清楚三件事：①环保方面是否有被政策打压的风险 ②社会责任方面是否有舆论隐患 ③公司治理方面大股东是否靠谱。示例：'公司在环保方面表现尚可，无重大污染事件；治理方面大股东持股稳定，未发现掏空上市公司迹象'。数据不足则标注具体哪些项不可用"
  },

  "module_9_操作指南": {
    "buy_strategy": "分批建仓建议（如'建议分2-3批在5.0-5.3元区间关注，不要一次性满仓'），必须是观察建议，不能是买卖指令",
    "stop_loss": "止损参考及理由（如'跌破4.8元（60日均线+前期低点）需警惕，中期趋势可能转弱'）",
    "take_profit": "止盈参考及理由（如'5.8-6.0元附近（前期密集成交区）遇阻可考虑分批止盈'）",
    "holding_period": {
      "type": "短线博弈/中短线波段/中长线持有",
      "reason": "一句话说明理由（如'公司基本面扎实但短期涨幅已大，估值修复需要时间，适合中长线持有'）"
    }
  },

  "signal_attribution": [
    {"source": "估值面", "weight": 0.20, "direction": "偏多", "note": "PE 处于历史低位提供安全边际"},
    {"source": "财务面", "weight": 0.25, "direction": "偏多", "note": "营收净利润双增，基本面扎实"},
    {"source": "资金面", "weight": 0.15, "direction": "偏空", "note": "主力资金持续净流出"},
    {"source": "情绪面", "weight": 0.15, "direction": "中性", "note": "近期新闻多空交织，舆论无明显偏向"},
    {"source": "风险面", "weight": 0.10, "direction": "偏空", "note": "估值偏高+短期涨幅过大积累回调风险"},
    {"source": "筹码面", "weight": 0.15, "direction": "偏多", "note": "筹码趋于集中，大户在吸筹"}
  ]
}

注意：
1. 各模块仅包含数据可用的内容，缺失数据标注"数据不可用"或"暂无数据"，绝不编造
2. module_5（北向资金）若没有北向资金/沪深港通数据，available 设为 false，trend 和 interpretation 填写"北向资金数据暂不可用"
3. signal_attribution 解释各维度对综合评分的贡献权重和方向，权重之和必须为 1.0，维度来源与 9 个模块对应
4. score 基于各模块综合判断，60 以上偏乐观，40 以下偏悲观
5. 每个模块的文字内容必须严格遵循"数据事实化 → 逻辑推演化 → 散民口语化"三步思考链
6. 禁止使用"戴维斯双击""麦克米伦缺口""Beta 中性""Gamma 对冲"等深奥术语，若必须使用需在括号内加上一句白话解释
7. module_3 的 key_indicators 至少包含毛利率、ROE、资产负债率、经营现金流/净利润 4 项，数据不足则标注对应项的 value 为"数据不可用"
8. module_7 的 positive 和 negative 至少各有 1 条，数据不足则写"暂无明显的利好/利空事件" """


def build_system_prompt() -> str:
    """分层组装 system prompt

    Layer 1 → 角色定义 + 模块表
    Layer 2 → 核心分析原则
    Layer 3 → 输出 JSON Schema
    """
    layers = [ROLE_DEFINITION, CORE_RULES, OUTPUT_SCHEMA]
    return "\n\n".join(layers)


def build_user_prompt(markdown_report: str) -> str:
    """构建 user prompt——直接使用 SKILL 返回的 Markdown 数据报告"""
    parts = [
        "以下是同花顺 iFinD SKILL 为该股票采集的综合数据报告，请基于此数据进行分析：",
        "",
        markdown_report,
    ]
    return "\n".join(parts)


# ═══════════════════════════════════════════
# 3. LLM 调用
# ═══════════════════════════════════════════

def analyze(markdown_report: str) -> tuple[dict, dict]:
    """调用 DeepSeek Reasoner 分析 SKILL 数据报告，返回 (report, usage)。

    Args:
        markdown_report: SKILL 生成的 Markdown 格式综合数据报告
    """
    # 数据守卫：报告不能为空
    if not markdown_report or not markdown_report.strip():
        raise DataIncompleteError("数据报告为空，拒绝调用 LLM 以防止幻觉")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY，请检查 .env 文件")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    user_prompt = build_user_prompt(markdown_report)

    resp = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=16384,  # 推理模型需足够 token 给 reasoning + content
    )

    content = resp.choices[0].message.content
    reasoning_content = getattr(resp.choices[0].message, 'reasoning_content', None)
    # 诊断日志（安全：只记录 key 长度，禁止输出 key 内容，防止日志系统泄密）
    import sys as _sys
    print(f"[analyze] key_len={len(api_key)} sys_prompt_len={len(build_system_prompt())} user_prompt_len={len(user_prompt)}", file=_sys.stderr)
    print(f"[analyze] content_len={len(content) if content else 0} reasoning_len={len(reasoning_content) if reasoning_content else 0} finish_reason={resp.choices[0].finish_reason}", file=_sys.stderr)
    usage = {
        "prompt": resp.usage.prompt_tokens,
        "completion": resp.usage.completion_tokens,
        "total": resp.usage.total_tokens,
    }

    # 解析 JSON（reasoner 可能把输出全放到 reasoning_content，content 为空）
    raw_text = content or ""
    if not raw_text.strip() and reasoning_content:
        print(f"[analyze] ⚠️ content 为空，尝试从 reasoning_content 提取 JSON", file=_sys.stderr)
        raw_text = reasoning_content

    # 剥离 ```json ... ``` 包裹
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1].split("```", 1)[0]

    raw_text = raw_text.strip()
    if not raw_text:
        raise RuntimeError(
            f"DeepSeek Reasoner 返回空内容 "
            f"(content_len={len(content) if content else 0}, "
            f"reasoning_len={len(reasoning_content) if reasoning_content else 0}, "
            f"finish_reason={resp.choices[0].finish_reason})"
        )

    report = _parse_json(raw_text)
    return report, usage


def _extract_outermost_json(text: str) -> str | None:
    """按括号深度匹配提取最外层完整 {...}（比贪婪/非贪婪正则都稳健）

    - 跟踪字符串内外状态，字符串内的大括号不参与配对
    - 返回第一个深度归零的完整 JSON 子串；找不到返回 None
    """
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_json(raw_text: str, max_retries: int = 2) -> dict:
    """容错 JSON 解析 — DeepSeek Reasoner 偶尔输出非法 JSON

    常见问题及修复策略：
      1. 末尾截断（finish_reason=length）→ 补全缺失的 }]
      2. 尾随逗号（"key": "val",}）→ 移除
      3. JSON 内嵌 markdown 代码块 → 二次剥离
    """
    import re as _re

    text = raw_text

    for attempt in range(max_retries + 1):
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt >= max_retries:
                raise  # 重试耗尽，抛出原始错误

            print(f"[analyze] ⚠️ JSON 解析失败 (尝试 {attempt+1}/{max_retries+1}): {e}", file=sys.stderr)

            # 策略 1：尾随逗号 — 删除 , 后紧跟 } 或 ] 的模式
            err_msg = str(e)
            if "trailing comma" in err_msg.lower() or "Expecting ',' delimiter" in err_msg or "Expecting value" in err_msg:
                fixed = _re.sub(r',(\s*[}\]])', r'\1', text)
                if fixed != text:
                    text = fixed
                    print(f"[analyze] → 已移除尾随逗号", file=sys.stderr)
                    continue

            # 策略 2：截断 — 尝试补全未闭合的括号
            open_braces = text.count('{') - text.count('}')
            open_brackets = text.count('[') - text.count(']')
            if open_braces > 0 or open_brackets > 0:
                text = text.rstrip()
                if text.endswith(','):
                    text = text[:-1]  # 移除末尾逗号再补
                text += ']' * open_brackets + '}' * open_braces
                print(f"[analyze] → 已补全 {open_braces}个}} {open_brackets}个]", file=sys.stderr)
                continue

            # 策略 3：JSON 前后可能有文字，按括号深度匹配提取最外层完整 {...}
            extracted = _extract_outermost_json(text)
            if extracted and extracted != text:
                text = extracted
                print(f"[analyze] → 已提取最外层 JSON", file=sys.stderr)
                continue

            raise  # 以上策略都不匹配，抛原始错误


# ═══════════════════════════════════════════
# 4. 报告渲染（从 render 模块导入）
# ═══════════════════════════════════════════

from stock_agent.render import render_markdown  # noqa: F401 — 保持向后兼容，原调用方可继续 from analyze import render_markdown


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
    from stock_agent.skill.report import generate_report_sync

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
        print(f"  🔍 分析 {code}")
        print(f"{'='*60}")

        # 采集（SKILL 10 维度）
        print("📡 SKILL 采集数据...")
        try:
            data_md = generate_report_sync(code)
        except Exception as e:
            print(f"  ❌ 数据采集失败: {e}")
            continue

        # 分析
        print("🤖 LLM 分析...")
        try:
            report, usage = analyze(data_md["markdown"])
        except DataIncompleteError as e:
            print(f"  ❌ 数据不完整，拒绝调用LLM: {e}")
            continue
        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            continue

        print(f"  ✅ Token: {usage['total']} | 评分: {report.get('score')} | {report.get('decision')}")

        stock_name = data_md.get("stock_name", code)
        md = render_markdown(code, report, usage, stock_name)

        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"\n{md}")

        # 保存
        out_dir = Path(__file__).parent / "reports"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_file = out_dir / f"{code}_{ts}.md"
        out_file.write_text(md, encoding="utf-8")
        print(f"\n  💾 保存: {out_file}")

        # 飞书推送（第 2 参是 stock_name，453 行已从采集结果提取，勿再传 code）
        if args.push:
            push_to_feishu(md, stock_name, code)

    print(f"\n{'='*60}")
    print(f"  📋 实验 B 使用记录")
    print(f"  今天是第 ___ 天")
    print(f"  是否看了报告？___  是否影响了操作决策？___")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
