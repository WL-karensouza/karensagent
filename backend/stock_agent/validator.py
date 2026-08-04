"""报告校验 — 兼容门面（真实现见 stock_agent.core.validator）"""
from stock_agent.core.validator import (  # noqa: F401
    validate_report,
    is_collapsed_report,
    StructuralCollapseError,
    REQUIRED_FIELDS,
    MODULE_SUB_FIELDS,
    VALID_DECISIONS,
    WEIGHT_SUM_TOLERANCE,
    MIN_KEY_INDICATORS,
    MIN_POSITIVE_NEGATIVE,
    MIN_RISKS,
    BULLISH_SCORE_FLOOR,
    BEARISH_SCORE_CEIL,
    MIN_PRESENT_MODULES,
    VALID_CHANGED_ASPECTS,
)
