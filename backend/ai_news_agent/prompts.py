"""AI 前沿咨询 Agent —— 固定的搜索 Query 和 LLM 摘要 Prompt"""

# ═══════════════════════════════════════════
# Tavily 搜索 Query（中英文双语，提高覆盖面）
# ═══════════════════════════════════════════

DAILY_SEARCH_QUERY = (
    "AI artificial intelligence breaking news today "
    "large language model LLM agent multi-agent RAG "
    "open source model release AI safety regulation "
    "OpenAI Anthropic Google DeepMind latest"
)

WEEKLY_SEARCH_QUERY = (
    "AI artificial intelligence important news this week 2026 "
    "breakthrough technology trend open source framework "
    "large language model LLM agent research paper "
    "AI policy regulation industry competition"
)

# ═══════════════════════════════════════════
# LLM 摘要 Prompt
# ═══════════════════════════════════════════

DAILY_SUMMARIZE_PROMPT = """当前日期：{today_str}

基于以下搜索结果为用户提供过去 24 小时内 AI/人工智能领域的重大新闻摘要：

搜索结果：
{search_results}

请严格遵循以下要求：
1. 筛选出真正属于过去 24 小时内的新闻（对比发布时间与当前日期 {today_str}）
2. 用中文简洁总结，每条 1-2 句话，突出核心信息
3. 每条新闻必须标注：📅发布时间 和 🔗来源URL
4. 如果搜索结果中的发布时间早于 {today_str}，诚实告知"搜索到的最新新闻是 X 月 X 日的"
5. 按发布时间从新到旧排列
6. 最多 5 条
7. 不要包含与 AI/人工智能无关的内容"""

WEEKLY_SUMMARIZE_PROMPT = """当前日期：{today_str}

基于以下搜索结果为用户提供过去 7 天内 AI/人工智能领域最重要的新闻摘要：

搜索结果：
{search_results}

请严格遵循以下要求：
1. 筛选出过去 7 天内最重要的 AI 新闻
2. 用中文简洁总结，每条 1-2 句话，突出核心信息和为什么重要
3. 每条新闻必须标注：📅发布时间 和 🔗来源URL
4. 按重要性排序（非时间顺序），最重要的排前面
5. 最多 10 条
6. 不要包含与 AI/人工智能无关的内容"""
