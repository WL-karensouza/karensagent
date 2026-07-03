"""
技能插件注册表
============
协议: 每个技能是签名为 (data: dict) -> dict 的函数
返回: {"enabled": True, "section": {...}} 或 {"enabled": False, "reason": "..."}

当前分析维度（6维）：
  技术面 | 资金面 | 消息面 | 基本面 | 风险面 | 市场环境

新增技能只需: ① 写技能文件 ② 在此注册（1行） ③ 不改调度器
"""
from dataclasses import dataclass, field
from typing import Callable

from .technical import technical_skill as _technical_func
from .capital import capital_skill as _capital_func
from .news import news_skill as _news_func
from .fundamental import fundamental_skill as _fundamental_func
from .risk import risk_skill as _risk_func
from .market_env import market_env_skill as _market_env_func


@dataclass
class SkillMeta:
    """技能元数据——轻量包装，不改现有函数逻辑

    协议：实例可调用，签名同 (data: dict) -> dict
    - name: 唯一标识（如 'technical'）
    - display_name: 中文显示名（如 '技术面'）
    - instructions: 自然语言分析指令，注入 LLM system prompt
    - required_fields: 依赖的数据字段（供数据守卫参考）
    - category: 技能分类标签（trend/flow/sentiment/value/risk/context）
    - _analyze: 实际的分析函数（不对外暴露）
    """
    name: str
    display_name: str
    instructions: str
    required_fields: list
    category: str = "general"
    _analyze: Callable = field(default=None, repr=False)

    def __call__(self, data: dict) -> dict:
        if self._analyze is None:
            return {"enabled": False, "reason": f"技能 {self.name} 未绑定分析函数"}
        return self._analyze(data)


# ── 注册表：一行元数据 + 一行绑定 ──

technical_skill = SkillMeta(
    name="technical",
    display_name="技术面",
    instructions=(
        "技术面分析：观察K线形态（阳线/阴线占比、上下影线长度），"
        "判断均线排列（多头/空头/缠绕），解读MACD/RSI信号的含义，"
        "识别关键支撑位（近期低点、均线位置）和压力位（近期高点、均线位置），"
        "结合量比判断量价配合是否健康（放量上涨=积极、缩量下跌=观望、放量下跌=警惕），"
        "结合多周期涨跌幅（5日/10日/20日）判断短中期趋势方向，"
        "最终给出偏多/中性/偏空的技术综合信号。"
    ),
    required_fields=["recent_bars", "latest_close"],
    category="trend",
)
technical_skill._analyze = _technical_func

capital_skill = SkillMeta(
    name="capital",
    display_name="资金面",
    instructions=(
        "资金面分析：关注主力资金净流向的方向和规模（同花顺数据），"
        "融资融券余额变化趋势反映杠杆资金态度，"
        "换手率是否异常（>10%警惕对倒出货，<0.5%关注流动性枯竭），"
        "量价配合关系（放量上涨=积极信号，缩量下跌=观望，放量下跌=警惕出逃），"
        "综合判断市场参与者情绪为积极/中性/谨慎，"
        "注意区分'散户行为'和'主力意图'。"
    ),
    required_fields=["fund_flow_recent_5d", "latest_close"],
    category="flow",
)
capital_skill._analyze = _capital_func

news_skill = SkillMeta(
    name="news",
    display_name="消息面",
    instructions=(
        "消息面分析：提取近期新闻的关键主题（业绩/政策/行业/公司事件），"
        "判断整体情绪偏向（偏多/中性/偏空），"
        "识别潜在利好（业绩预增、政策支持、新产品发布、股东增持等）和"
        "潜在利空（减持、处罚、业绩下滑、诉讼等），"
        "区分'已被市场定价的旧信息'和'可能影响未来走势的新信息'，"
        "注意：不编造新闻，只能基于提供的新闻标题分析。"
    ),
    required_fields=["news"],
    category="sentiment",
)
news_skill._analyze = _news_func

fundamental_skill = SkillMeta(
    name="fundamental",
    display_name="基本面",
    instructions=(
        "基本面分析：基于PE/PB判断估值水位（需结合行业特征，不同行业合理PE差异大），"
        "基于ROE评价盈利能力（>20%优秀、10-20%良好、<10%一般、<0亏损），"
        "基于营收增速和净利润增速判断成长性（双增>20%=高成长、双降=警惕经营风险），"
        "资产负债率评估财务风险（>70%高负债、<40%稳健），"
        "EPS为盈利质量提供参考，"
        "结合市值规模最终给出估值信号（低估/合理/高估）。"
    ),
    required_fields=["fundamental", "spot"],
    category="value",
)
fundamental_skill._analyze = _fundamental_func

risk_skill = SkillMeta(
    name="risk",
    display_name="风险面",
    instructions=(
        "风险面分析：综合扫描四个维度的风险信号——"
        "技术面（RSI极端值>80或<20、均线死叉、MACD空头运行、放量下跌），"
        "资金面（主力持续净流出、换手率异常高>10%），"
        "基本面（亏损、PE>100极高估值、资产负债率>70%、营收利润双降），"
        "消息面（标题含减持/处罚/亏损/诉讼/退市等利空关键词），"
        "统计风险信号总数，评定综合风险等级（高>=5个/中>=2个/低<2个），"
        "输出最值得警惕的Top 3风险点，"
        "并判断这些风险是否已被市场定价（股价已反映 vs 尚未反映）。"
    ),
    required_fields=[],
    category="risk",
)
risk_skill._analyze = _risk_func

market_env_skill = SkillMeta(
    name="market_env",
    display_name="市场环境",
    instructions=(
        "市场环境分析：根据市值规模判断个股风格（大盘>1000亿/中盘100-1000亿/小盘<100亿），"
        "根据PE水平判断估值风格（价值/成长/题材），"
        "通过MA5与MA20的相对位置判断个股短期相对自身的强弱，"
        "结合个股所属板块或题材（如消费、新能源、金融、科技等），"
        "综合判断当前市场环境对该股的友好程度（有利/中性/不利），"
        "注意：如果你不知道近期大盘具体表现，请如实说明'基于LLM训练数据的判断'，不要编造今日大盘数据。"
    ),
    required_fields=["latest_close", "recent_bars"],
    category="context",
)
market_env_skill._analyze = _market_env_func

# 注册表：新增技能在此加一组 SkillMeta + 一行注册
# 顺序即分析报告中的展示顺序
SKILLS: list = [
    technical_skill,
    capital_skill,
    news_skill,
    fundamental_skill,
    risk_skill,
    market_env_skill,
]

SKILL_ORDER = [s.name for s in SKILLS]
