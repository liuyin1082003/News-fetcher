#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际涉华新闻抓取工具 v2.0
========================

功能：
  从 RSS 源 + Google News 抓取涉华新闻，支持代理、去重、内容安全化。

用法：
  python fetch_news.py --days 7                          # 最近7天
  python fetch_news.py --start 2025-01-01 --end 2025-01-10  # 指定日期范围
  python fetch_news.py --days 3 --source rss              # 仅RSS源
  python fetch_news.py --days 3 --source google           # 仅Google News
  python fetch_news.py --days 3 --source all              # 全部来源（默认）

依赖：
  pip install feedparser

输出：
  标准 JSON，包含 status 和 articles 数组。
"""

import feedparser
import argparse
import json
import sys
import re
import os
import ssl
import urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Windows UTF-8 编码修复 ─────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── 导入自定义模块 ─────────────────────────────────────────
# 添加当前目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from proxy_manager import ProxyManager
    HAS_PROXY = True
except ImportError:
    HAS_PROXY = False

try:
    from google_news_fetcher import GoogleNewsFetcher
    HAS_GOOGLE_NEWS = True
except ImportError:
    HAS_GOOGLE_NEWS = False


# ============================================================
#  配置
# ============================================================

# ─── 涉华关键词（分级过滤）─────────────────────────────────

CHINA_KEYWORDS = {
    # 一级：必定涉华
    "primary": [
        "china", "chinese", "beijing", "shanghai",
    ],
    # 二级：高度涉华
    "secondary": [
        "taiwan", "taiwanese",
        "hong kong", "hongkong",
        "xinjiang", "uyghur", "uighur",
        "tibet", "tibetan",
        "south china sea",
        "belt and road", "bri",
        "huawei", "tiktok", "wechat",
        "communist party", "ccp",
        "people's liberation army", "pla",
        "renminbi", "yuan",
        "macau", "macao",
    ],
    # 三级：可能涉华（需配合一级/二级使用）
    "tertiary": [
        "trade war", "tariff", "sanctions",
        "indo-pacific", "quad", "aukus",
        "semiconductor", "rare earth",
        "supply chain", "reshoring",
    ],
}

# ─── 黑名单关键词（即使涉华也排除）─────────────────────────

BLACKLIST_KEYWORDS = [
    # 体育
    "sports", "football", "basketball", "soccer", "olympic",
    "tennis", "baseball", "golf", "cricket", "rugby",
    "formula 1", "f1 racing", "grand prix",
    "nba", "nfl", "mlb", "nhl", "premier league",
    # 娱乐
    "entertainment", "movie", "celebrity", "music", "concert",
    "album", "cinema", "hollywood", "bollywood", "k-pop",
    "boy band", "girl group", "reality show", "box office",
    "tv show", "netflix series", "film review",
    # 无关联
    "horoscope", "recipe", "weather forecast",
    "lottery", "crossword",
]

# ─── 内容安全化映射 ─────────────────────────────────────────

SANITIZE_MAP = [
    # 长匹配优先（按长度降序）
    ("President Xi Jinping", "席"),
    ("Xi Jinping", "席"),
    ("President Xi", "席"),
    ("Chairman Xi", "席"),
    ("Xi's", "席的"),
    ("xi jinping", "席"),
    ("president xi", "席"),
]

# ─── 默认配置路径 ───────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROXY_CONFIG = os.path.join(SCRIPT_DIR, "proxy_config.json")
DEFAULT_RSS_CONFIG = os.path.join(SCRIPT_DIR, "rss_sources.json")


# ============================================================
#  工具函数
# ============================================================

def load_rss_sources(config_path):
    """从 JSON 配置文件加载 RSS 源列表

    Args:
        config_path: rss_sources.json 路径

    Returns:
        dict: {name: {url, country, region, ...}, ...}
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        feeds = {}
        for item in data.get("feeds", []):
            if item.get("enabled", True):
                name = item.pop("name")
                feeds[name] = item
        return feeds
    except FileNotFoundError:
        print(f"⚠️  RSS 配置文件不存在: {config_path}，使用内置默认源", file=sys.stderr)
        return get_builtin_feeds()
    except Exception as e:
        print(f"⚠️  RSS 配置文件加载失败: {e}，使用内置默认源", file=sys.stderr)
        return get_builtin_feeds()


def get_builtin_feeds():
    """返回内置的最小 RSS 源集合（作为 JSON 配置不可用时的回退）"""
    return {
        "CNN": {"url": "http://rss.cnn.com/rss/edition.rss", "country": "美国", "region": "北美", "language": "en"},
        "BBC": {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "country": "英国", "region": "欧洲", "language": "en"},
        "Le Monde": {"url": "https://www.lemonde.fr/rss/une.xml", "country": "法国", "region": "欧洲", "language": "fr"},
        "Der Spiegel": {"url": "https://www.spiegel.de/schlagzeilen/index.rss", "country": "德国", "region": "欧洲", "language": "de"},
        "朝日新聞": {"url": "https://www.asahi.com/rss/index.rdf", "country": "日本", "region": "东亚", "language": "ja"},
        "KBS": {"url": "https://world.kbs.co.kr/service/news_english.xml", "country": "韩国", "region": "东亚", "language": "en"},
    }


def _match_keyword(text, keyword):
    """智能关键词匹配：长词用子串匹配，短缩写用词边界匹配

    避免短缩写误伤：bri 不应匹配 "British"，pla 不应匹配 "plans"
    """
    if len(keyword) <= 3:
        # 短缩写用词边界正则匹配
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    else:
        # 长词用普通子串匹配
        return keyword in text


def is_china_related(text):
    """判断文本是否涉华（分级关键词匹配）

    Args:
        text: 标题+摘要（小写）

    Returns:
        bool: 是否涉华
    """
    text_lower = text.lower()

    # 检查一级关键词（强信号）
    has_primary = any(_match_keyword(text_lower, kw) for kw in CHINA_KEYWORDS["primary"])

    # 检查二级关键词（中信号）
    has_secondary = any(_match_keyword(text_lower, kw) for kw in CHINA_KEYWORDS["secondary"])

    # 命中一级或二级 → 直接通过
    if has_primary or has_secondary:
        return True

    # 检查三级关键词（弱信号，需配合一级/二级）
    has_tertiary = any(_match_keyword(text_lower, kw) for kw in CHINA_KEYWORDS["tertiary"])

    # 仅命中三级 → 需要额外判断（标题中出现亚洲/太平洋相关）
    if has_tertiary:
        # 三级关键词 + 提及 asia/pacific/beijing → 通过
        extra = ["asia", "pacific", "beijing", "chinese", "china"]
        if any(_match_keyword(text_lower, kw) for kw in extra):
            return True

    return False


def is_blacklisted(text):
    """判断是否属于应排除的内容（体育、娱乐等）

    Args:
        text: 标题+摘要（小写）

    Returns:
        bool: 是否应排除
    """
    text_lower = text.lower()
    return any(_match_keyword(text_lower, kw) for kw in BLACKLIST_KEYWORDS)


def sanitize_text(text):
    """对文本执行内容安全化处理（敏感词替换）

    Args:
        text: 原始文本

    Returns:
        str: 处理后的文本
    """
    if not text:
        return text

    # 1. 长字符串替换（按长度优先）
    for old, new in SANITIZE_MAP:
        text = text.replace(old, new)

    # 2. 用词边界正则替换剩余的独立 "Xi"（避免误伤 Mexico 等）
    text = re.sub(r'\bXi\b', '席', text)

    return text


def sanitize_article(article):
    """对整篇文章执行内容安全化处理

    Args:
        article: 文章字典

    Returns:
        dict: 处理后的文章
    """
    article["title"] = sanitize_text(article.get("title", ""))
    article["summary"] = sanitize_text(article.get("summary", ""))
    return article


def deduplicate(articles):
    """基于标题去重

    Args:
        articles: 文章列表

    Returns:
        list: 去重后的文章列表
    """
    seen = set()
    unique = []
    for a in articles:
        # 取标题前60字符，小写，去空白作为去重键
        key = a.get("title", "")[:60].lower().strip()
        key = re.sub(r'\s+', ' ', key)  # 合并空白
        if key and key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


# ============================================================
#  RSS 抓取
# ============================================================

def parse_date(entry):
    """从 feedparser entry 解析发布日期

    Args:
        entry: feedparser entry

    Returns:
        datetime | None
    """
    pub = entry.get("published_parsed") or entry.get("updated_parsed")
    if pub:
        try:
            return datetime(*pub[:6])
        except (ValueError, TypeError):
            pass
    return None


def fetch_rss_feed(name, config, days=None, start_date=None, end_date=None):
    """抓取单个 RSS 源

    Args:
        name: 媒体名称
        config: {url, country, region, ...}
        days: 最近 N 天
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        list[dict]: 符合条件的文章列表
    """
    url = config.get("url", "")
    country = config.get("country", "未知")
    region = config.get("region", "")

    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            print(f"  ⚠️  RSS 解析警告 [{name}]", file=sys.stderr)

        articles = []
        now = datetime.now()
        max_entries = 30  # 每个源最多取30条

        for entry in feed.entries[:max_entries]:
            # ── 日期过滤 ──
            pub_date = parse_date(entry)
            if pub_date:
                if start_date and end_date:
                    if not (start_date <= pub_date <= end_date):
                        continue
                elif days:
                    cutoff = now - timedelta(days=days)
                    if pub_date < cutoff:
                        continue

            # ── 相关性过滤 ──
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            full_text = (title + " " + summary).lower()

            if not is_china_related(full_text):
                continue
            if is_blacklisted(full_text):
                continue

            # ── 提取摘要 ──
            clean_summary = re.sub(r"<[^>]+>", "", summary)[:300]

            articles.append({
                "title": title,
                "link": entry.get("link", "#"),
                "summary": clean_summary,
                "published": pub_date.isoformat() if pub_date else "",
                "source": name,
                "country": country,
                "region": region,
                "via": "RSS",
            })

        if articles:
            print(f"  ✅ [{name}] {len(articles)} 篇", file=sys.stderr)
        return articles

    except Exception as e:
        print(f"  ❌ [{name}] 抓取失败: {e}", file=sys.stderr)
        return []


def fetch_all_rss(feeds, days=None, start_date=None, end_date=None, max_workers=5):
    """并发抓取所有 RSS 源

    Args:
        feeds: {name: config, ...}
        days: 最近 N 天
        start_date: 开始日期
        end_date: 结束日期
        max_workers: 并发数

    Returns:
        list[dict]: 所有文章
    """
    print(f"\n📡 抓取 {len(feeds)} 个 RSS 源...", file=sys.stderr)

    all_articles = []
    success = 0
    fail = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_rss_feed, name, config, days, start_date, end_date): name
            for name, config in feeds.items()
        }

        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                if result:
                    all_articles.extend(result)
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                print(f"  ❌ [{name}] 线程异常: {e}", file=sys.stderr)
                fail += 1

    print(f"📡 RSS 完成: {success} 成功, {fail} 无结果, 共 {len(all_articles)} 篇", file=sys.stderr)
    return all_articles


# ============================================================
#  主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="国际涉华新闻抓取工具 v2.0 — 从 RSS + Google News 抓取涉华新闻",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fetch_news.py --days 7
  python fetch_news.py --start 2025-06-01 --end 2025-06-10
  python fetch_news.py --days 3 --source rss
  python fetch_news.py --days 3 --source google
  python fetch_news.py --days 3 --source all --workers 3
        """,
    )

    # 日期参数
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--days", type=int, help="抓取最近 N 天的新闻")
    group.add_argument("--start", help="开始日期 YYYY-MM-DD（需配合 --end）")

    parser.add_argument("--end", help="结束日期 YYYY-MM-DD（配合 --start 使用）")

    # 数据源
    parser.add_argument(
        "--source", choices=["rss", "google", "all"], default="all",
        help="数据源：rss=仅RSS源, google=仅Google News, all=全部（默认）",
    )

    # 配置文件路径
    parser.add_argument("--rss-config", default=DEFAULT_RSS_CONFIG, help="RSS 源配置文件路径")
    parser.add_argument("--proxy-config", default=DEFAULT_PROXY_CONFIG, help="代理配置文件路径")

    # 其他选项
    parser.add_argument("--workers", type=int, default=5, help="并发线程数（默认5，走代理建议3）")
    parser.add_argument("--no-sanitize", action="store_true", help="跳过内容安全化处理")
    parser.add_argument("--no-dedup", action="store_true", help="跳过标题去重")
    parser.add_argument("--output", help="输出 JSON 文件路径（默认输出到 stdout）")

    args = parser.parse_args()

    # ── 1. 解析时间范围 ──
    start_date = None
    end_date = None
    days = None

    if args.start:
        try:
            start_date = datetime.fromisoformat(args.start)
            end_date = datetime.fromisoformat(args.end) if args.end else datetime.now()
            # 设置 end_date 为当天结束
            end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError as e:
            print(f"❌ 日期格式错误: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.days:
        days = args.days
    else:
        days = 7  # 默认最近7天

    # ── 2. 安装代理 ──
    proxy_installed = False
    if HAS_PROXY:
        pm = ProxyManager(args.proxy_config)
        if pm.config.get("enabled", False):
            proxy_installed = pm.install()
    else:
        print("ℹ️  proxy_manager.py 未找到，代理功能不可用", file=sys.stderr)

    # ── 3. 抓取新闻 ──
    all_articles = []

    # 3a. RSS 源
    if args.source in ("rss", "all"):
        feeds = load_rss_sources(args.rss_config)
        # 走代理时降低并发数
        rss_workers = min(args.workers, 3) if proxy_installed else args.workers
        rss_articles = fetch_all_rss(feeds, days=days, start_date=start_date, end_date=end_date, max_workers=rss_workers)
        all_articles.extend(rss_articles)

    # 3b. Google News
    if args.source in ("google", "all"):
        if HAS_GOOGLE_NEWS:
            gnf = GoogleNewsFetcher(timeout=15, max_workers=min(args.workers, 5))
            gn_articles = gnf.fetch_all(days=days, start_date=start_date, end_date=end_date)
            all_articles.extend(gn_articles)
        else:
            print("⚠️  google_news_fetcher.py 未找到，Google News 不可用", file=sys.stderr)

    # ── 4. 去重 ──
    if not args.no_dedup:
        before = len(all_articles)
        all_articles = deduplicate(all_articles)
        after = len(all_articles)
        if before > after:
            print(f"🔗 去重: {before} → {after} (移除 {before - after} 条重复)", file=sys.stderr)

    # ── 5. 内容安全化 ──
    if not args.no_sanitize:
        all_articles = [sanitize_article(a) for a in all_articles]
        print(f"🛡️  内容安全化完成", file=sys.stderr)

    # ── 6. 按发布时间倒序排列 ──
    all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

    # ── 7. 构建输出 ──
    output = {
        "status": "ok" if all_articles else "no_articles",
        "count": len(all_articles),
        "query": {
            "days": days,
            "start": args.start,
            "end": args.end,
            "source": args.source,
        },
        "generated": datetime.now().isoformat(),
        "articles": all_articles,
    }

    # ── 8. 输出 ──
    json_str = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"\n📄 结果已保存至: {args.output}", file=sys.stderr)
    else:
        print(json_str)

    # ── 9. 摘要 ──
    if all_articles:
        sources = set(a.get("source", "") for a in all_articles)
        countries = set(a.get("country", "") for a in all_articles)
        print(f"\n📊 摘要: {len(all_articles)} 条新闻, {len(sources)} 个来源, {len(countries)} 个国家/地区", file=sys.stderr)
    else:
        print("\n⚠️  未找到符合条件的新闻", file=sys.stderr)


if __name__ == "__main__":
    main()
