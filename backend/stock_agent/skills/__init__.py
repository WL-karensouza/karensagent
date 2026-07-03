"""
技能插件注册表
============
协议: 每个技能是签名为 (data: dict) -> dict 的函数
返回: {"enabled": True, "section": {...}} 或 {"enabled": False, "reason": "..."}

新增技能只需: ① 写技能文件 ② 在此注册（1行） ③ 不改调度器
"""
from .technical import technical_skill
from .capital import capital_skill
from .news import news_skill

# 注册表：新增技能在此加一行即可
SKILLS: list = [
    technical_skill,
    capital_skill,
    news_skill,
]

SKILL_ORDER = [s.__name__ for s in SKILLS]
