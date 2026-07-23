"""GitHub Trending 页面解析器 —— 抓取 daily/weekly 热榜"""

from datetime import datetime
from bs4 import BeautifulSoup
import httpx
from config import GITHUB_HEADERS


GITHUB_TRENDING_URL = "https://github.com/trending"


def fetch_trending(since: str = "daily", language: str = "") -> list[dict]:
    """
    抓取 GitHub Trending 页面

    Args:
        since: "daily" 或 "weekly"
        language: 语言过滤（空=全部），如 "python"

    Returns:
        [{repo_name, repo_url, description, language, stars_today, total_stars, rank}, ...]
    """
    url = GITHUB_TRENDING_URL
    params = {"since": since}
    if language:
        url = f"{GITHUB_TRENDING_URL}/{language}"
        params = {"since": since}

    try:
        resp = httpx.get(url, headers=GITHUB_HEADERS, params=params,
                         timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[github] 请求失败: {e}")
        raise

    soup = BeautifulSoup(resp.text, "lxml")
    articles = soup.find_all("article", class_="Box-row")

    repos = []
    for idx, article in enumerate(articles, 1):
        try:
            # 仓库名和链接
            h2 = article.find("h2", class_="h3")
            if not h2:
                continue
            link = h2.find("a")
            if not link:
                continue

            # href 格式: "/owner/repo"
            href = link.get("href", "").strip()
            repo_name = href.strip("/")
            repo_url = f"https://github.com{repo_name}"

            # 描述
            desc_p = article.find("p", class_="col-9")
            description = desc_p.text.strip() if desc_p else ""

            # 语言
            lang_span = article.find("span", itemprop="programmingLanguage")
            language_name = lang_span.text.strip() if lang_span else ""

            # 解析 stars（兼容 daily/weekly/monthly 三种文案）
            # daily → "123 stars today"
            # weekly → "1,234 stars this week"
            # monthly → "5,678 stars this month"
            stars_today = 0
            total_stars = 0

            all_spans = article.find_all("span")
            for s in all_spans:
                text = s.text.strip()
                # 匹配各种 stars 文案
                if "stars today" in text or "stars this week" in text or "stars this month" in text:
                    # 提取数字部分（去掉文案，去逗号）
                    import re
                    num_match = re.search(r'[\d,]+', text)
                    if num_match:
                        try:
                            stars_today = int(num_match.group().replace(",", ""))
                        except ValueError:
                            pass

            # 总星标：在 stars_today 后的纯数字 span（格式如 "45,678"）
            for s in all_spans:
                text = s.text.strip()
                # 跳过已识别为 stars_today 的文本
                if "stars" in text:
                    continue
                cleaned = text.replace(",", "").strip()
                if cleaned.isdigit():
                    try:
                        val = int(cleaned)
                        if 0 < val < 100_000_000:
                            total_stars = val
                            break  # 取第一个符合条件的纯数字
                    except ValueError:
                        pass

            # 备用解析：从 star 徽章区域获取总星标
            if total_stars == 0:
                star_badge = article.select_one("span[aria-label*='star']")
                if star_badge:
                    label = star_badge.get("aria-label", "")
                    digits = "".join(filter(str.isdigit, label))
                    if digits:
                        total_stars = int(digits)

            repos.append({
                "repo_name": repo_name,
                "repo_url": repo_url,
                "description": description,
                "language": language_name,
                "stars_today": stars_today,
                "total_stars": total_stars,
                "rank": idx,
            })
        except Exception as e:
            print(f"[github] 解析单条失败 (排名 {idx}): {e}")
            continue

    print(f"[github] {since} 趋势抓取完成，共 {len(repos)} 条")
    return repos


def fetch_all_trends(date: str = "") -> list[dict]:
    """抓取 daily + weekly + monthly，各自保留原始 source 和排名"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    all_repos = []

    # weekly 趋势（本周 GitHub 官方排名）
    weekly = fetch_trending(since="weekly")
    for r in weekly:
        r["source"] = "weekly"
        r["fetch_date"] = date
    all_repos.extend(weekly)

    # monthly 趋势（本月 GitHub 官方排名）
    monthly = fetch_trending(since="monthly")
    for r in monthly:
        r["source"] = "monthly"
        r["fetch_date"] = date
    all_repos.extend(monthly)

    # 按 repo_name + source 去重（同 source 同仓库只保留第一条）
    seen = {}
    for r in all_repos:
        key = (r["repo_name"], r["source"])
        if key not in seen:
            seen[key] = r

    result = list(seen.values())
    print(f"[github] 去重后共 {len(result)} 个仓库 (weekly+monthly)")
    return result
