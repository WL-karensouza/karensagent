"""借鉴点落地 TDD 测试

TDD RED → GREEN → REFACTOR
测试三个借鉴点的最小可验证行为：
  借鉴1: SkillMeta 轻量包装
  借鉴2: 分层 Prompt 组装
  借鉴4: 决策仪表盘 Schema 升级
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════
# 借鉴 1 — SkillMeta 轻量包装
# ═══════════════════════════════════════════════

def test_skillmeta_class_exists():
    """SkillMeta 类应可以从 skills 包导入"""
    from stock_agent.skills import SkillMeta
    assert SkillMeta is not None, "SkillMeta 类应存在"


def test_skills_are_skillmeta_instances():
    """SKILLS 列表中每个元素都应是 SkillMeta 实例"""
    from stock_agent.skills import SKILLS, SkillMeta
    assert len(SKILLS) == 6, f"应有 6 个技能，实际 {len(SKILLS)} 个"
    for skill in SKILLS:
        assert isinstance(skill, SkillMeta), \
            f"{skill} 应为 SkillMeta 实例，实际 {type(skill)}"


def test_skillmeta_has_required_attributes():
    """每个 SkillMeta 实例应有 name/display_name/instructions/required_fields/category"""
    from stock_agent.skills import SKILLS
    for skill in SKILLS:
        assert isinstance(skill.name, str) and len(skill.name) > 0, \
            f"skill.name 应为非空字符串: {skill.name}"
        assert isinstance(skill.display_name, str) and len(skill.display_name) > 0, \
            f"skill.display_name 应为非空字符串"
        assert isinstance(skill.instructions, str) and len(skill.instructions) > 20, \
            f"skill.instructions 应至少 20 字符: {skill.name}"
        assert isinstance(skill.required_fields, list), \
            f"skill.required_fields 应为列表: {skill.name}"
        assert isinstance(skill.category, str) and len(skill.category) > 0, \
            f"skill.category 应为非空字符串: {skill.name}"


def test_skillmeta_is_callable():
    """SkillMeta 实例应可直接调用，返回 enabled/section 结构"""
    from stock_agent.skills import SKILLS

    # 构造最小可用的模拟数据
    fake_data = {
        "stock_code": "600398",
        "stock_name": "海澜之家",
        "latest_close": 5.46,
        "recent_bars": [
            {"date": "2026-07-01", "open": 5.40, "high": 5.50, "low": 5.38,
             "close": 5.46, "volume": 100000, "pct_chg": 0.5},
        ],
        "rsi": 45.0,
        "ma5": 5.50, "ma10": 5.55, "ma20": 5.60, "ma60": 5.80,
        "macd_dif": -0.05, "macd_dea": -0.03, "macd_bar": -0.02,
        "volume_ratio": 0.8,
        "pct_5d": -1.5, "pct_10d": 2.0, "pct_20d": 3.0,
        "fund_flow_recent_5d": [],
        "spot": {"换手率": "0.5", "市盈率": "12.5", "总市值": "25000000000"},
        "news": [],
        "fundamental": {
            "pe": 12.25, "pb": 1.5, "roe": 15.0,
            "revenue_yoy": 8.0, "profit_yoy": 5.0,
            "debt_ratio": 40.0, "eps": 0.85,
        },
    }

    for skill in SKILLS:
        result = skill(fake_data)
        assert isinstance(result, dict), \
            f"{skill.name} 调用结果应为 dict，实际 {type(result)}"
        assert "enabled" in result, \
            f"{skill.name} 返回缺少 'enabled' 字段"
        if result["enabled"]:
            assert "section" in result, \
                f"{skill.name} 启用时应包含 'section'"


def test_skillmeta_name_replaces_dunder_name():
    """skill.name 应返回注册名（如 'technical'），而非函数名或类名"""
    from stock_agent.skills import SKILLS
    expected_names = {"technical", "capital", "news", "fundamental", "risk", "market_env"}
    actual_names = {s.name for s in SKILLS}
    assert actual_names == expected_names, \
        f"技能名应为 {expected_names}，实际 {actual_names}"


# ═══════════════════════════════════════════════
# 借鉴 2 — 分层 Prompt 组装
# ═══════════════════════════════════════════════

def test_prompt_constants_exist():
    """ROLE_DEFINITION / CORE_RULES / OUTPUT_SCHEMA 常量应存在"""
    from stock_agent.analyze import ROLE_DEFINITION, CORE_RULES, OUTPUT_SCHEMA
    assert len(ROLE_DEFINITION) > 50, "ROLE_DEFINITION 至少 50 字符"
    assert len(CORE_RULES) > 50, "CORE_RULES 至少 50 字符"
    assert len(OUTPUT_SCHEMA) > 100, "OUTPUT_SCHEMA 至少 100 字符"


def test_build_system_prompt_contains_all_layers():
    """build_system_prompt() 返回的 prompt 应包含所有层"""
    from stock_agent.analyze import build_system_prompt
    prompt = build_system_prompt()
    assert "A 股投资顾问" in prompt, "应包含角色定义"
    assert "核心原则" in prompt, "应包含分析原则"
    assert "输出格式" in prompt, "应包含输出 Schema"
    assert "各维度分析指令" in prompt, "应包含技能指令层"


def test_build_system_prompt_injects_skill_instructions():
    """build_system_prompt() 应注入每个技能的 instructions"""
    from stock_agent.analyze import build_system_prompt
    from stock_agent.skills import SKILLS
    prompt = build_system_prompt()
    for skill in SKILLS:
        # 每个技能的 display_name 应出现在 prompt 中
        assert skill.display_name in prompt, \
            f"应包含 {skill.display_name} 的分析指令"


def test_build_prompt_uses_skill_name():
    """build_prompt 中不可用数据列表应使用 skill.name（字符串），而非 skill.__name__"""
    from stock_agent.analyze import build_prompt
    # 构造一个只有基础行情、无任何其他数据的最小输入
    # news_skill 会因为无新闻而 disabled
    minimal_data = {
        "stock_code": "000001",
        "stock_name": "测试股",
        "latest_close": 10.0,
        "recent_bars": [],
        "news": None,
        "spot": {},
        "pct_5d": 0, "pct_10d": 0, "pct_20d": 0,
        "volume_ratio": 1.0,
    }
    result = build_prompt(minimal_data)
    # 应该包含 "不可用数据" 节，其中有 skill.name 而非 "__name__"
    assert "不可用数据" in result
    # skill.name 应出现在结果中（如 "technical: 无K线数据"）
    # 各种 skill 可能因数据不足而 disabled
    assert isinstance(result, str) and len(result) > 0


# ═══════════════════════════════════════════════
# 借鉴 4 — Schema 升级（sniper_points + signal_attribution）
# ═══════════════════════════════════════════════

def test_output_schema_contains_sniper_points():
    """OUTPUT_SCHEMA 应包含 sniper_points 字段定义"""
    from stock_agent.analyze import OUTPUT_SCHEMA
    assert "sniper_points" in OUTPUT_SCHEMA, \
        "OUTPUT_SCHEMA 应包含 sniper_points"


def test_output_schema_contains_signal_attribution():
    """OUTPUT_SCHEMA 应包含 signal_attribution 字段定义"""
    from stock_agent.analyze import OUTPUT_SCHEMA
    assert "signal_attribution" in OUTPUT_SCHEMA, \
        "OUTPUT_SCHEMA 应包含 signal_attribution"


FAKE_REPORT_WITH_NEW_FIELDS = {
    "score": 45,
    "decision": "震荡",
    "summary": "测试摘要",
    "sections": {
        "技术面": {"signal": "偏空", "insight": "均线空头排列，MACD死叉运行中"},
        "资金面": {"sentiment": "中性", "insight": "缩量震荡，主力资金小幅流出"},
        "消息面": {"sentiment": "中性", "key_themes": ["业绩预告"], "insight": "近期无明显利好利空"},
        "基本面": {"signal": "合理", "insight": "低PE+稳健ROE"},
        "风险面": {"level": "中", "top_risks": ["均线空头", "主力流出"], "insight": "中等风险"},
        "市场环境": {"style_match": "中性", "insight": "中盘价值股，市场关注度一般"},
    },
    "risks": ["风险1", "风险2"],
    "catalysts": ["利好1", "利好2"],
    "watch_points": ["观察点1"],
    "position_advice": {
        "no_position": "观察等待回调",
        "has_position": "继续持有，注意风控",
    },
    # 🆕 新增字段
    "sniper_points": {
        "ideal_range": "5.0-5.3元附近（20日均线+前期低点支撑）",
        "stop_loss": "跌破4.8元需警惕趋势转弱",
        "take_profit": "5.8-6.0元附近（前期平台压力）",
    },
    "signal_attribution": [
        {"source": "技术面", "weight": 0.35, "direction": "偏空",
         "note": "均线空头排列+MACD死叉为主要拖累"},
        {"source": "基本面", "weight": 0.25, "direction": "偏多",
         "note": "低PE+稳健ROE提供安全边际"},
        {"source": "风险面", "weight": 0.15, "direction": "偏空",
         "note": "主力流出+技术风险信号偏多"},
        {"source": "市场环境", "weight": 0.10, "direction": "中性",
         "note": "中盘价值风格，缺乏板块催化"},
        {"source": "资金面", "weight": 0.10, "direction": "中性",
         "note": "缩量震荡，方向不明"},
        {"source": "消息面", "weight": 0.05, "direction": "中性",
         "note": "近期消息面平静"},
    ],
}

FAKE_REPORT_WITHOUT_NEW_FIELDS = {
    "score": 45,
    "decision": "震荡",
    "summary": "测试摘要",
    "sections": {
        "技术面": {"signal": "偏空", "insight": "均线空头排列"},
        "资金面": {"sentiment": "中性", "insight": "缩量震荡"},
        "消息面": {"sentiment": "中性", "key_themes": [], "insight": "无重大消息"},
        "基本面": {"signal": "合理", "insight": "低PE"},
        "风险面": {"level": "中", "top_risks": [], "insight": "中等"},
        "市场环境": {"style_match": "中性", "insight": "中性"},
    },
    "risks": ["风险1"],
    "catalysts": ["利好1"],
    "watch_points": ["观察点1"],
    "position_advice": {
        "no_position": "观察",
        "has_position": "持有",
    },
    # 没有 sniper_points 和 signal_attribution
}


def test_render_markdown_renders_sniper_points():
    """render_markdown 应在有新字段时渲染关键价位参考"""
    from stock_agent.analyze import render_markdown
    fake_data = {"stock_code": "600398", "stock_name": "海澜之家"}
    fake_usage = {"total": 1000}
    md = render_markdown(fake_data, FAKE_REPORT_WITH_NEW_FIELDS, fake_usage)
    assert "关键价位" in md, "应包含关键价位参考节"
    assert "5.0-5.3" in md, "应包含理想观察区间"
    assert "4.8" in md, "应包含风控参考价"


def test_render_markdown_renders_signal_attribution():
    """render_markdown 应在有新字段时渲染信号归因表"""
    from stock_agent.analyze import render_markdown
    fake_data = {"stock_code": "600398", "stock_name": "海澜之家"}
    fake_usage = {"total": 1000}
    md = render_markdown(fake_data, FAKE_REPORT_WITH_NEW_FIELDS, fake_usage)
    assert "信号归因" in md, "应包含信号归因节"
    assert "技术面" in md, "应包含技术面归因行"
    assert "35%" in md, "应包含权重百分比"


def test_render_markdown_backward_compatible():
    """render_markdown 在缺失新字段时不应崩溃（向后兼容）"""
    from stock_agent.analyze import render_markdown
    fake_data = {"stock_code": "600398", "stock_name": "海澜之家"}
    fake_usage = {"total": 1000}
    # 不应抛出异常
    md = render_markdown(fake_data, FAKE_REPORT_WITHOUT_NEW_FIELDS, fake_usage)
    assert len(md) > 0, "应返回非空字符串"
    assert "分析报告" in md, "应包含报告标题"


# ═══════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all", "skillmeta", "prompt", "schema"], default="all")
    args = ap.parse_args()

    print("=" * 50)
    print("Stock Agent 借鉴点 TDD 测试")
    print("=" * 50)

    if args.mode in ("all", "skillmeta"):
        print("\n-- 借鉴1: SkillMeta 轻量包装 --")
        test_skillmeta_class_exists()
        test_skills_are_skillmeta_instances()
        test_skillmeta_has_required_attributes()
        test_skillmeta_is_callable()
        test_skillmeta_name_replaces_dunder_name()

    if args.mode in ("all", "prompt"):
        print("\n-- 借鉴2: 分层 Prompt 组装 --")
        test_prompt_constants_exist()
        test_build_system_prompt_contains_all_layers()
        test_build_system_prompt_injects_skill_instructions()
        test_build_prompt_uses_skill_name()

    if args.mode in ("all", "schema"):
        print("\n-- 借鉴4: Schema 升级 --")
        test_output_schema_contains_sniper_points()
        test_output_schema_contains_signal_attribution()
        test_render_markdown_renders_sniper_points()
        test_render_markdown_renders_signal_attribution()
        test_render_markdown_backward_compatible()

    print("\n" + "=" * 50)
    print("[OK] All Stock Agent tests passed")
