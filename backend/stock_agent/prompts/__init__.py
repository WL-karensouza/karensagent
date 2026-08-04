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
        history_context: stock_agent.core.history 构建的历史报告骨架上下文（空串 = 不注入历史）
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
            "你必须将该股历史报告与本次数据逐项对比（财务面、股价面、操作建议三块），并遵守：",
            "1. module_9 中 history_compared 必须为 true，history_anchor 填最近一份历史报告日期；",
            "2. 有变化 → changed_aspects 列出变化方面，history_changes 条目化描述（每条含对比日期与对建议的影响）；",
            "3. 无变化 → changed_aspects 与 history_changes 均置空数组；",
            "4. 建仓策略/止损参考/止盈参考必须基于与历史同三要素的对比分析后给出，若较历史有调整要说明原因。",
        ]
    return "\n".join(parts)
