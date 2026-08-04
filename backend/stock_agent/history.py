"""历史对比 — 兼容门面（真实现见 stock_agent.core.history）"""
from stock_agent.core.history import (  # noqa: F401
    build_history_context,
    sample_history_indices,
    extract_skeleton,
    MAX_HISTORY,
)
