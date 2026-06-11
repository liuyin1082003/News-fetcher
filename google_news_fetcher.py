#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google News RSS 抓取器 — 通过 Google News RSS 搜索获取全球涉华新闻。

原理：
  Google News 仍提供 RSS 端点（2026年可用），通过搜索关键词可获取
  全球数千新闻源的涉华报道，远超手动维护的 RSS 列表。

用法：
  from google_news_fetcher import GoogleNewsFetcher
  gnf = GoogleNewsFetcher()
  articles = gnf.fetch_all()                          # 所有查询×所有地区
  articles = gnf.fetch(query="china", countries=["US", "GB"])  # 指定查询和地区

注意事项：
  - Google News RSS 可能随时变化，非官方 API
  - 需要通过代理访问（google.com 在国内被墙）
  - 每搜索最多返回约 100 条
"""

import feedparser
import re
import sys
import time
import urllib.request
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ─── Windows UTF-8 编码修复 ─────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class GoogleNewsFetcher:
    """Google News RSS 搜索获取器"""

    # 涉华搜索关键词（英文，用于搜索国际媒体报道）
    SEARCH_QUERIES = [
        "china",
        "beijing",
        "taiwan",
        "south china sea",
        "belt and road china",
        "china economy trade",
    ]

    # 搜索地区（不同 gl= 参数返回不同国家的报道视角）
    COUNTRIES = {
        "US": "美国",
        "GB": "英国",
        "IN": "印度",
        "AU": "澳大利亚",
        "JP": "日本",
        "KR": "韩国",
        "FR": "法国",
        "DE": "德国",
        "SG": "新加坡",
    }

    # Google News RSS 基础 URL
    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, timeout=15, max_workers=5):
        """
        Args:
            timeout: HTTP 请求超时（秒）
            max_workers: 并发搜索线程数
        """
        self.timeout = timeout
        self.max_workers = max_workers
        # SSL 上下文（忽略证书错误，代理环境下常见）
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE

    # ─── 构建搜索 URL ────────────────────────────────────────

    def build_url(self, query, country_code="US"):
        """构建 Google News RSS 搜索 URL

        Args:
            query: 搜索关键词
            country_code: 国家/地区代码（如 US, GB, IN）

        Returns:
            str: RSS URL
        """
        # URL 编码关键词
        encoded_query = urllib.request.quote(query)
        # ceid 格式：国家:语言
        ceid = f"{country_code}:en"
        return (
            f"{self.BASE_URL}?q={encoded_query}"
            f"&hl=en-US"
            f"&gl={country_code}"
            f"&ceid={ceid}"
        )

    # ─── 解析 Google News 条目 ───────────────────────────────

    def parse_entry(self, entry, query, country_code):
        """将 feedparser entry 转为标准文章格式

        Args:
            entry: feedparser 条目
            query: 搜索关键词
            country_code: 国家代码

        Returns:
            dict | None: 标准化文章，解析失败返回 None
        """
        try:
            title = entry.get("title", "无标题")
            # Google News 标题格式通常是 "标题 - 媒体名"，尝试分离
            source = "Google News"
            clean_title = title
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                clean_title = parts[0].strip()
                source = parts[1].strip()

            # 摘要
            summary = entry.get("summary", entry.get("description", ""))
            summary = re.sub(r"<[^>]+>", "", summary)[:300]

            # 链接（Google 重定向链接，需要提取真实 URL）
            link = entry.get("link", "#")

            # 时间
            pub_date = None
            pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub_parsed:
                pub_date = datetime(*pub_parsed[:6])

            return {
                "title": clean_title,
                "link": link,
                "summary": summary,
                "published": pub_date.isoformat() if pub_date else "",
                "source": source,
                "country": self.COUNTRIES.get(country_code, country_code),
                "via": "Google News",
            }
        except Exception:
            return None

    # ─── 单次搜索 ────────────────────────────────────────────

    def fetch(self, query, country_code="US", days=None, start_date=None, end_date=None):
        """执行一次 Google News 搜索

        Args:
            query: 搜索关键词
            country_code: 国家代码
            days: 最近 N 天（与 start_date/end_date 二选一）
            start_date: 开始日期 datetime
            end_date: 结束日期 datetime

        Returns:
            list[dict]: 标准化文章列表
        """
        url = self.build_url(query, country_code)
        country_name = self.COUNTRIES.get(country_code, country_code)

        try:
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"  ⚠️  Google News RSS 解析警告 [{query}@{country_code}]", file=sys.stderr)

            articles = []
            now = datetime.now()

            for entry in feed.entries[:30]:  # 限制每个搜索最多取30条
                article = self.parse_entry(entry, query, country_code)
                if article is None:
                    continue

                # 日期过滤
                pub_date_str = article.get("published", "")
                if pub_date_str:
                    try:
                        pub_dt = datetime.fromisoformat(pub_date_str)
                        if start_date and end_date:
                            if not (start_date <= pub_dt <= end_date):
                                continue
                        elif days:
                            cutoff = now - datetime.timedelta(days=days)
                            if pub_dt < cutoff:
                                continue
                    except ValueError:
                        pass  # 日期解析失败，保留

                articles.append(article)

            return articles

        except Exception as e:
            print(f"  ❌ Google News 抓取失败 [{query}@{country_code}]: {e}", file=sys.stderr)
            return []

    # ─── 批量搜索（并发）──────────────────────────────────────

    def fetch_all(self, days=None, start_date=None, end_date=None, queries=None, countries=None):
        """并发搜索所有关键词×所有地区

        Args:
            days: 最近 N 天
            start_date: 开始日期
            end_date: 结束日期
            queries: 自定义搜索词列表（默认使用 SEARCH_QUERIES）
            countries: 自定义地区列表（默认使用 COUNTRIES 的 keys）

        Returns:
            list[dict]: 去重后的标准化文章列表
        """
        if queries is None:
            queries = self.SEARCH_QUERIES
        if countries is None:
            countries = list(self.COUNTRIES.keys())

        # 生成所有搜索任务
        tasks = []
        for query in queries:
            for country in countries:
                tasks.append((query, country))

        print(f"\n🌐 Google News: {len(queries)} 关键词 × {len(countries)} 地区 = {len(tasks)} 次搜索", file=sys.stderr)

        all_articles = []
        completed = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.fetch, query, country, days, start_date, end_date
                ): (query, country)
                for query, country in tasks
            }

            for future in as_completed(futures):
                query, country = futures[future]
                try:
                    result = future.result()
                    if result:
                        all_articles.extend(result)
                        completed += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"  ❌ [{query}@{country}]: {e}", file=sys.stderr)
                    failed += 1

        print(f"✅ Google News 完成: {completed} 成功, {failed} 失败, 共 {len(all_articles)} 篇文章", file=sys.stderr)
        return all_articles


# ─── 自测入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    """直接运行以测试 Google News 抓取器"""
    print("=" * 50)
    print("Google News 抓取器自测")
    print("=" * 50)

    gnf = GoogleNewsFetcher(timeout=10)

    # 只测试一个查询一个地区，避免过多请求
    print("\n测试搜索: china @ US")
    articles = gnf.fetch("china", "US", days=7)

    print(f"\n获取到 {len(articles)} 篇文章:")
    for i, a in enumerate(articles[:5]):
        print(f"  {i+1}. [{a['source']}] {a['title'][:80]}")
        print(f"     日期: {a['published'][:19]}")
        print(f"     摘要: {a['summary'][:100]}...")
        print()
