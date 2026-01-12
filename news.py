"""news.py

Query SerpApi (Google News) for a company name, rank articles by a simple
relevance heuristic (term frequency + recency), and write top N articles to
`news.txt`.

Requirements:
  pip install requests python-dotenv

Usage:
  - Set SERPAPI_KEY in environment or in a local `.env` file:
      SERPAPI_KEY=your_key_here
  - Run: python news.py
"""

import os
import sys
import time
from datetime import datetime, timezone
import math

try:
    import requests
except ImportError:
    print("Missing dependency: requests. Install with: pip install requests")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional
    pass

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

API_URL = "https://serpapi.com/search.json"


def prompt_for_api_key():
    key = input("Enter your SerpApi key (won't be saved): ").strip()
    return key or None


def fetch_news(company, api_key, page=1, page_size=10):
    """Fetch news search results from SerpApi (Google News via tbm=nws).
    Returns list of news result dicts (as returned under 'news_results').
    """
    params = {
        "engine": "google",
        "q": company,
        "tbm": "nws",
        "api_key": api_key,
        "num": page_size,
        "start": (page - 1) * page_size,
    }
    resp = requests.get(API_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # SerpApi returns 'news_results' for the news engine
    return data.get("news_results", [])


def fetch_news_paginated(company, api_key, limit=10, page_size=20, max_pages=5, sleep_between=0.1, progress_callback=None):
    """Fetch up to `limit` news articles by paging through SerpApi results.

    - Deduplicates by link/url
    - Stops early if SerpApi returns fewer than page_size results
    - If `progress_callback` is provided, it will be called as
      progress_callback(page_number, total_results_collected)
    """
    results = []
    seen_links = set()
    page = 1
    # adapt max_pages so we fetch enough when limit > page_size
    max_pages = max_pages or (math.ceil(limit / page_size) + 2)
    while len(results) < limit and page <= max_pages:
        try:
            batch = fetch_news(company, api_key, page=page, page_size=page_size)
        except Exception:
            break
        if not batch:
            # still call progress callback to indicate completion of this page
            if progress_callback:
                progress_callback(page, len(results))
            break
        for a in batch:
            link = a.get("link") or a.get("url")
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            results.append(a)
            if len(results) >= limit:
                break
        # report progress after processing each page
        if progress_callback:
            try:
                progress_callback(page, len(results))
            except Exception:
                pass
        # If we got less than a full page, no more results likely
        if len(batch) < page_size:
            break
        page += 1
        if sleep_between:
            time.sleep(sleep_between)
    return results


def article_relevance_score(article, company):
    """Compute a simple relevance score for sorting:
    - frequency of company tokens in title + snippet (weighted)
    - recency bonus (newer = higher)
    """
    text = f"{article.get('title','')} {article.get('snippet','')}".lower()
    name = company.lower()
    # simple token match frequency
    freq = text.count(name)
    # word-level partial matches (split company into tokens)
    for t in name.split():
        freq += text.count(t) * 0.5

    # recency: use 'date' or 'published' if available
    date_str = article.get("date") or article.get("published") or article.get("datetime")
    recency_score = 0.0
    if date_str:
        try:
            # SerpApi 'date' values can be like '2 hours ago', '2025-12-23T10:34:00Z', etc.
            # Try parsing ISO first
            dt = None
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except Exception:
                # fallback: if it contains 'ago' or 'hour', approximate as very recent
                if "ago" in date_str:
                    recency_score = 1.0
                else:
                    # unknown format
                    dt = None
            if dt:
                age_seconds = (datetime.now(timezone.utc) - dtastimezone(dt)).total_seconds()
                # bucket recency: 48h or less gets bonus up to 2.0
                hours = age_seconds / 3600
                recency_score = max(0.0, (48 - min(hours, 48)) / 48 * 2.0)
        except Exception:
            recency_score = 0.0

    # combine scores
    score = freq * 10.0 + recency_score
    return score


def dtastimezone(dt):
    """Return a timezone-aware datetime in UTC for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def rank_and_format(articles, company):
    scored = []
    for a in articles:
        score = article_relevance_score(a, company)
        scored.append((score, a))
    scored.sort(key=lambda s: s[0], reverse=True)
    return scored


def write_results(scored_articles, out_path="news.txt", limit=10):
    lines = []
    now = datetime.now().isoformat()
    lines.append(f"News summary generated: {now}\n")
    if not scored_articles:
        lines.append("No articles found.\n")
    else:
        for i, (score, art) in enumerate(scored_articles[:limit], 1):
            title = art.get("title") or art.get("title_no_date") or "(No title)"
            source = art.get("source") or art.get("provider") or "(Unknown source)"
            date = art.get("date") or art.get("published") or "(Unknown date)"
            link = art.get("link") or art.get("url") or "(No link)"
            snippet = art.get("snippet") or art.get("snippet_highlighted") or ""
            lines.append(f"{i}. {title}")
            lines.append(f"   Source: {source}")
            lines.append(f"   Date: {date}")
            lines.append(f"   Link: {link}")
            lines.append(f"   Snippet: {snippet}")
            lines.append(f"   Relevance score: {score:.2f}\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote top {min(limit, len(scored_articles))} results to {out_path}")


def main():
    global SERPAPI_KEY
    # Support command-line mode for automation/tests: python news.py "Microsoft" 5
    if len(sys.argv) > 1:
        company = sys.argv[1]
        try:
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        except ValueError:
            limit = 10
    else:
        company = input("Enter company name to search news for: ").strip()
        if not company:
            print("No company provided. Exiting.")
            return
        try:
            count_in = input("How many articles to return [default 10]: ").strip()
            limit = int(count_in) if count_in else 10
        except ValueError:
            limit = 10

    if not SERPAPI_KEY:
        print("SERPAPI_KEY not found in environment.")
        print("Tip: set it persistently using PowerShell: `setx SERPAPI_KEY \"your_key\"`\n")
        print("Or run the helper: .\\1. NEWS SEARCH\\set_serpapi_key.ps1\n")
        print("Alternative: create a local .env file (see .env.example) or provide the key now.")
        SERPAPI_KEY = prompt_for_api_key()
        if not SERPAPI_KEY:
            print("SerpApi key is required to run searches. Get one at https://serpapi.com/")
            return

    try:
        # use paginated fetch to attempt to gather the requested number of articles
        articles = fetch_news_paginated(company, SERPAPI_KEY, limit=limit, page_size=min(50, max(10, limit)), max_pages=6)
    except requests.HTTPError as e:
        print(f"HTTP error fetching news: {e}")
        return
    except Exception as e:
        print(f"Error fetching news: {e}")
        return

    scored = rank_and_format(articles, company)
    write_results(scored, out_path="news.txt", limit=limit)


if __name__ == "__main__":
    main()
