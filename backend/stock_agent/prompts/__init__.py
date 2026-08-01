"""股票投研分析提示词包

三层 system prompt + user prompt 组装：
  Layer 1 (role_definition) → 角色定义 + 三步思考链 + 9 模块概述
  Layer 2 (core_rules)      → 核心分析原则
  Layer 3 (output_schema)   → 输出 JSON Schema

对外暴露 build_system_prompt / build_user_prompt，三层拆分属包内部细节。
"""
from .role_definition import ROLE_DEFINITION
from .core_rules import CORE_RULES
from .output_schema import OUTPUT_SCHEMA

__all__ = [
    "ROLE_DEFINITION",
    "CORE_RULES",
    "OUTPUT_SCHEMA",
    "build_system_prompt",
    "build_user_prompt",
]


def build_system_prompt() -> str:
    """分层组装 system prompt

    Layer 1 → 角色定义 + 模块表
    Layer 2 → 核心分析原则
    Layer 3 → 输出 JSON Schema
    """
    layers = [ROLE_DEFINITION, CORE_RULES, OUTPUT_SCHEMA]
    return "\n\n".join(layers)


def build_user_prompt(markdown_report: str, history_context: str = "") -> str:
    """构建 user prompt——数据报告 + 可选历史对比上下文

    Args:
        markdown_report: SKILL 返回的 Markdown 综合数据报告
        history_context: stock_agent.history 构建的历史报告骨架上下文（空串 = 不注入历史）
    """
    parts = [
        "以下是同花顺 iFinD SKILL 为该股票采集的综合数据报告，请基于此数据进行分析：",
        "",
        markdown_report,
    ]
    if history_context:
        parts += [
            "",
            history_context,
            "",
            "若本次结论与历史结论存在差异，请在 module_1 核心逻辑中明确指出变化方向及原因。",
        ]
    return "\n".join(parts)
