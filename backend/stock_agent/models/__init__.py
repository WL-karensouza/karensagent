"""iFind 数据模型包

原 models.py（470 行）拆为按领域归类的子模块，对外 re-export 保持
`from stock_agent.models import X` 路径不变（test_models.py 等消费者零改动）。
"""
from .base import DataIncompleteError, IfindRecord, ParsedData
from .market import MarketData, FinancialsData
from .shareholders import ShareholderData
from .news import NewsEventsData
from .risk import RiskData
from .env import MarketEnvData
from ._util import _iter_fields, _TABLE_META_KEYS

__all__ = [
    "DataIncompleteError",
    "IfindRecord",
    "ParsedData",
    "MarketData",
    "FinancialsData",
    "ShareholderData",
    "NewsEventsData",
    "RiskData",
    "MarketEnvData",
    "_iter_fields",
    "_TABLE_META_KEYS",
]
