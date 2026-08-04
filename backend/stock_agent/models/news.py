"""iFind 数据模型 — 新闻、公告与重大事件"""
from __future__ import annotations


class NewsEventsData:
    """新闻 + 公告 + 重大事件"""

    # iFind MCP 新闻类返回字段名映射（兼容多来源字段名差异）
    _NEWS_TITLE_KEYS = ("资讯标题", "title", "新闻标题")
    _NEWS_CONTENT_KEYS = ("资讯内容", "资讯摘要", "content", "description", "摘要")
    _NEWS_TIME_KEYS = ("日期", "time", "date", "发布时间")
    _NOTICE_TITLE_KEYS = ("公告标题", "title", "标题")
    _NOTICE_CONTENT_KEYS = ("公告片段内容", "content", "摘要", "description")
    _NOTICE_DATE_KEYS = ("日期", "date", "time", "发布时间")

    @staticmethod
    def _first_of(record: dict, *keys: str) -> str:
        """从 record 中取第一个非空字段值（兼容非字符串类型，统一转 str）"""
        for k in keys:
            val = record.get(k, "")
            s = "" if val is None else str(val).strip()
            if s:
                return s
        return ""

    def __init__(self, stock_code: str, news: list[dict], notices: list[dict],
                 events: str = ""):
        self.stock_code = stock_code
        self.news = news
        self.notices = notices
        self.events = events  # LLM 总结后的中文描述文本

    @property
    def news_count(self) -> int:
        return len(self.news)

    @property
    def notice_count(self) -> int:
        return len(self.notices)

    @property
    def has_events(self) -> bool:
        return bool(self.events and self.events.strip())

    def to_prompt_context(self) -> str:
        lines = [f"### 近期新闻与公告（{self.stock_code}）"]
        if self.news:
            lines.append("\n**新闻**：")
            for n in self.news:
                title = self._first_of(n, *self._NEWS_TITLE_KEYS)
                content = self._first_of(n, *self._NEWS_CONTENT_KEYS)
                time = self._first_of(n, *self._NEWS_TIME_KEYS)
                lines.append(f"- [{time}] {title}（{content[:80]}...）" if len(content) > 80
                             else f"- [{time}] {title}（{content}）")
        if self.notices:
            lines.append("\n**公告**：")
            for n in self.notices:
                title = self._first_of(n, *self._NOTICE_TITLE_KEYS)
                content = self._first_of(n, *self._NOTICE_CONTENT_KEYS)
                date = self._first_of(n, *self._NOTICE_DATE_KEYS)
                lines.append(f"- [{date}] {title}（{content[:80]}...）" if len(content) > 80
                             else f"- [{date}] {title}（{content}）")
        if self.events:
            lines.append(f"\n**重大事件总结**：\n{self.events}")
        return "\n".join(lines)

    def to_frontend(self) -> dict:
        """导出新闻事件为前端可渲染的结构"""
        return {
            "news": [{
                "title": self._first_of(n, *self._NEWS_TITLE_KEYS),
                "source": self._first_of(n, *self._NEWS_CONTENT_KEYS),
                "time": self._first_of(n, *self._NEWS_TIME_KEYS),
            } for n in self.news],
            "notices": [{
                "title": self._first_of(n, *self._NOTICE_TITLE_KEYS),
                "type": self._first_of(n, *self._NOTICE_CONTENT_KEYS),
                "date": self._first_of(n, *self._NOTICE_DATE_KEYS),
            } for n in self.notices],
            "events_summary": self.events or "",
        }
