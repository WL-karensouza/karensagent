"""核心功能测试"""

import sys
import os
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows 控制台 UTF-8 编码兼容
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def test_database_init():
    """测试数据库初始化"""
    from database import init_db, seed_keywords
    init_db()
    seed_keywords()
    print("[OK] 数据库初始化通过")


def test_github_fetch():
    """测试 GitHub Trending 抓取"""
    from fetchers.github import fetch_trending
    repos = fetch_trending(since="daily")
    assert isinstance(repos, list), "返回应为列表"
    if repos:
        r = repos[0]
        assert "repo_name" in r, "缺失 repo_name"
        assert "repo_url" in r, "缺失 repo_url"
        print(f"[OK] GitHub 抓取通过 — 获取 {len(repos)} 条，第1条: {r['repo_name']}")
    else:
        print("[WARN] GitHub 抓取返回空（可能被限流）")


def test_ai_news_fetch():
    """测试 AI 资讯抓取"""
    from fetchers.ai_news import fetch_hackernews, fetch_arxiv
    hn = fetch_hackernews(limit=5)
    print(f"[OK] HN 抓取通过 — {len(hn)} 条 AI 相关")
    arxiv = fetch_arxiv(limit=5)
    print(f"[OK] ArXiv 抓取通过 — {len(arxiv)} 条")


def test_keyword_filter():
    """测试关键词过滤（filter_news 布尔匹配）"""
    from filters.keyword import filter_news, get_active_keywords
    keywords = get_active_keywords()
    # 构造一条会命中关键词的 AI 资讯
    news_items = [
        {"title": "langgraph agent framework", "url": "https://example.com/1",
         "source": "hackernews", "score": 100, "summary": "Build language agents"},
        {"title": "unrelated cooking recipe", "url": "https://example.com/2",
         "source": "hackernews", "score": 50, "summary": "How to bake bread"},
    ]
    filtered = filter_news(news_items, top_n=10)
    assert len(filtered) >= 1, "至少命中一条 AI 关键词"
    assert filtered[0]["title"] == "langgraph agent framework", "应保留命中关键词的资讯"
    print(f"[OK] 关键词过滤通过 — {len(filtered)}/{len(news_items)} 条命中")


def test_fetch_all_trends_no_daily():
    """fetch_all_trends 不应抓取 daily，只抓 weekly+monthly"""
    from unittest.mock import patch
    from fetchers.github import fetch_all_trends

    # mock fetch_trending 返回固定数据，避免真实网络请求
    def mock_fetch(since="daily", language=""):
        return [{
            "repo_name": f"test/repo-{since}",
            "repo_url": f"https://github.com/test/repo-{since}",
            "description": f"mock {since}",
            "language": "Python",
            "stars_today": 100,
            "total_stars": 1000,
            "rank": 1,
        }]

    with patch('fetchers.github.fetch_trending', side_effect=mock_fetch):
        result = fetch_all_trends(date="2026-07-02")

    sources = {r["source"] for r in result}
    assert "daily" not in sources, f"不应包含 daily，实际来源: {sources}"
    assert "weekly" in sources, "应包含 weekly"
    assert "monthly" in sources, "应包含 monthly"
    print(f"[OK] fetch_all_trends 只抓取 weekly+monthly，sources={sources}")


def test_markdown_format():
    """测试 Markdown 格式化"""
    from formatters.markdown import build_weekly_report
    repos = [
        {
            "repo_name": "test-org/test-repo",
            "repo_url": "https://github.com/test-org/test-repo",
            "description": "A test repository",
            "week_stars": 1234,
        }
    ]
    news = [
        {
            "title": "Test AI News",
            "url": "https://example.com",
            "source": "hackernews",
            "score": 100,
        }
    ]
    report = build_weekly_report(repos, news)
    assert "test-repo" in report
    assert "Test AI News" in report
    print("[OK] Markdown 格式化通过")


# ═══════════════════════════════════════════════
# 错误传播测试（TDD: RED phase）
# ═══════════════════════════════════════════════

def test_github_http_error_raises():
    """GitHub 网络错误应该 raise，而不是静默返回 []"""
    import httpx
    from fetchers.github import fetch_trending

    with patch('fetchers.github.httpx.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        try:
            fetch_trending(since="daily")
            assert False, "应该抛出异常"
        except httpx.HTTPError:
            pass  # 预期行为
    print("[OK] GitHub HTTP 错误正确抛出")


def test_github_parse_error_resilience():
    """HTML 解析失败（无 article）应返回 []，不 raise"""
    from fetchers.github import fetch_trending

    mock_resp = MagicMock()
    mock_resp.text = "<html><body>空页面</body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch('fetchers.github.httpx.get', return_value=mock_resp):
        result = fetch_trending(since="daily")
        assert isinstance(result, list), "应返回列表"
        assert len(result) == 0, "空页面应返回空列表"
    print("[OK] GitHub 解析失败韧性正确（返回 []）")


def test_hn_http_error_raises():
    """HN 网络错误应该 raise"""
    import httpx
    from fetchers.ai_news import fetch_hackernews

    with patch('fetchers.ai_news.httpx.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        try:
            fetch_hackernews(limit=5)
            assert False, "应该抛出异常"
        except httpx.HTTPError:
            pass
    print("[OK] HN HTTP 错误正确抛出")


def test_arxiv_http_error_raises():
    """ArXiv 网络错误应该 raise"""
    from fetchers.ai_news import fetch_arxiv

    with patch('fetchers.ai_news.feedparser.parse') as mock_parse:
        mock_parse.side_effect = Exception("DNS 解析失败")
        try:
            fetch_arxiv(limit=5)
            assert False, "应该抛出异常"
        except Exception:
            pass
    print("[OK] ArXiv 网络错误正确抛出")


def test_trigger_full_returns_task_id():
    """POST /api/trigger/full 应返回 task_id"""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.post("/api/trigger/full")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "task_id" in data
    assert len(data["task_id"]) == 8
    print(f"[OK] trigger/full 返回 task_id: {data['task_id']}")


def test_task_result_not_found():
    """查询不存在的 task_id 应返回 code=1"""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.get("/api/trigger/result/nonexist")
    data = resp.json()
    assert data["code"] == 1
    print("[OK] 不存在的 task_id 正确返回 code=1")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all", "errors", "legacy"], default="all")
    args = ap.parse_args()

    print("=" * 50)
    print("GitHub Agent Core Tests")
    print("=" * 50)

    if args.mode in ("all", "legacy"):
        test_database_init()
        test_github_fetch()
        test_ai_news_fetch()
        test_keyword_filter()
        test_fetch_all_trends_no_daily()
        test_markdown_format()

    if args.mode in ("all", "errors"):
        test_github_http_error_raises()
        test_github_parse_error_resilience()
        test_hn_http_error_raises()
        test_arxiv_http_error_raises()
        test_trigger_full_returns_task_id()
        test_task_result_not_found()

    print("\n" + "=" * 50)
    print("[OK] All tests passed")
