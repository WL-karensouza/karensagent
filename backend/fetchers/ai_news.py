"""AI 前沿资讯抓取器 —— Hacker News + ArXiv"""

from datetime import datetime
import httpx
import feedparser


HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# ArXiv CS.AI 分类 RSS
ARXIV_CS_AI_RSS = "https://rss.arxiv.org/rss/cs.AI"

# AI 相关关键词（过滤 HN 和 ArXiv）
AI_KEYWORDS = [
    "agent", "llm", "gpt", "claude", "language model", "rag",
    "tool use", "function call", "prompt", "fine-tun", "alignment",
    "transformer", "reinforcement learning", "multi-agent", "mcp",
    "model context protocol", "langgraph", "langchain", "crewai",
    "autogen", "skill", "chain-of-thought", "reasoning",
    "openai", "anthropic", "deepseek", "gemini", "llama",
    "vector database", "embedding", "retrieval", "generation",
    "machine learning", "deep learning", "neural network",
    "artificial intelligence", "ai ", "agi",
]


def _match_ai_topic(title: str, summary: str = "") -> bool:
    """检查标题/摘要是否与 AI 主题相关"""
    text = (title + " " + summary).lower()
    return any(kw in text for kw in AI_KEYWORDS)


def fetch_hackernews(limit: int = 30) -> list[dict]:
    """
    抓取 Hacker News 首页热帖，过滤 AI 相关

    Returns:
        [{title, url, source, score, summary}, ...]
    """
    try:
        resp = httpx.get(HN_TOP_STORIES, timeout=15)
        resp.raise_for_status()
        story_ids = resp.json()
    except Exception as e:
        print(f"[hn] 获取列表失败: {e}")
        raise

    news = []
    for sid in story_ids[:limit * 3]:  # 多取一些，过滤后可能不够
        if len(news) >= limit:
            break
        try:
            item_url = HN_ITEM.format(sid)
            item = httpx.get(item_url, timeout=10).json()
            if not item:
                continue

            title = item.get("title", "")
            url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
            score = item.get("score", 0)

            if _match_ai_topic(title):
                news.append({
                    "title": title,
                    "url": url,
                    "source": "hackernews",
                    "score": score,
                    "summary": "",
                })
        except Exception as e:
            print(f"[hn] 解析 ID={sid} 失败: {e}")
            continue

    print(f"[hn] AI 相关帖子: {len(news)} 条")
    return news


def fetch_arxiv(limit: int = 20) -> list[dict]:
    """
    抓取 ArXiv CS.AI 最新论文

    Returns:
        [{title, url, source, score, summary}, ...]
    """
    try:
        feed = feedparser.parse(ARXIV_CS_AI_RSS)
    except Exception as e:
        print(f"[arxiv] RSS 解析失败: {e}")
        raise

    papers = []
    for entry in feed.entries[:limit * 2]:  # 多取一些做过滤
        if len(papers) >= limit:
            break

        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", "").strip()

        # ArXiv ID 作为简化的引用计数
        arxiv_id = entry.get("id", "").split("/")[-1]
        score = 0

        if _match_ai_topic(title, summary):
            # 简短摘要（取前 200 字符）
            short_sum = summary[:200].replace("\n", " ") + "..." if len(summary) > 200 else summary
            papers.append({
                "title": title,
                "url": link,
                "source": "arxiv",
                "score": score,
                "summary": short_sum,
            })

    print(f"[arxiv] AI 相关论文: {len(papers)} 篇")
    return papers


def fetch_paperswithcode(limit: int = 10) -> list[dict]:
    """
    抓取 Hugging Face Daily Papers（Papers With Code 社区精选）

    HF Daily Papers API（免费，无需 key）
    返回社区投票选出的当日 AI 论文

    Returns:
        [{title, url, source, score, summary}, ...]
    """
    HF_DAILY_API = "https://huggingface.co/api/daily_papers"
    try:
        resp = httpx.get(HF_DAILY_API, timeout=20)
        resp.raise_for_status()
        papers_data = resp.json()
    except Exception as e:
        print(f"[pwc] HF Daily Papers 请求失败: {e}")
        raise

    papers = []
    for entry in papers_data:
        if len(papers) >= limit:
            break

        paper = entry.get("paper", {})
        title = paper.get("title", "").strip()

        # 构建 ArXiv 链接
        arxiv_id = paper.get("id", "")
        paper_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

        # 摘要
        summary = paper.get("summary", "").strip()
        if len(summary) > 200:
            summary = summary[:200] + "..."

        # HF 社区投票数作为热度
        upvotes = entry.get("upvotes", 0)

        if title and paper_url:
            papers.append({
                "title": title,
                "url": paper_url,
                "source": "paperswithcode",
                "score": upvotes,
                "summary": summary,
            })

    print(f"[pwc] HF Daily Papers 抓取: {len(papers)} 篇")
    return papers


def fetch_all_news(date: str = "") -> list[dict]:
    """统一入口：抓取 HN + ArXiv + Papers With Code，标记日期"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    hn = fetch_hackernews(limit=10)
    for n in hn:
        n["fetch_date"] = date

    arxiv = fetch_arxiv(limit=10)
    for n in arxiv:
        n["fetch_date"] = date

    pwc = fetch_paperswithcode(limit=10)
    for n in pwc:
        n["fetch_date"] = date

    all_news = hn + arxiv + pwc
    print(f"[ai_news] 总计抓取: {len(all_news)} 条 (HN={len(hn)} ArXiv={len(arxiv)} PwC={len(pwc)})")
    return all_news
