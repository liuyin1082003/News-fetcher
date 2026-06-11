# 🌏 国际涉华新闻日报

每天自动抓取全球主流媒体涉华新闻，生成可在线阅读的 HTML 报告。

## 📰 在线阅读

访问：**https://你的用户名.github.io/news-fetcher/**

## 🔄 自动更新

每天北京时间 16:00 自动抓取并更新。

## 📡 信息来源

覆盖 **15+ 国家**、**38 个 RSS 源** + Google News 搜索，包括：

| 地区 | 媒体 |
|------|------|
| 🇺🇸 北美 | CNN, NYT, WSJ, Washington Post, NPR, USA Today |
| 🇬🇧 欧洲 | BBC, Guardian, Economist, Reuters, Le Monde, Figaro, Spiegel, DW |
| 🇰🇷 韩国 | KBS, Yonhap, Korea Herald, Korea Times |
| 🇯🇵 日本 | 朝日新聞, 読売新聞, NHK World, Japan Times |
| 🇮🇳 印度 | Times of India, The Hindu, Indian Express |
| 🇦🇺 澳洲 | ABC News, Sydney Morning Herald |
| 🇷🇺 俄罗斯 | TASS, RT |
| 🇸🇬 东南亚 | CNA, Straits Times, Bangkok Post |
| 🇸🇦 中东 | Al Jazeera, Arab News |
| 🌍 非洲 | AllAfrica |

## 🛠 本地使用

```bash
pip install feedparser
python fetch_news.py --days 1 --source all --output raw.json
python build_report.py raw.json 你的用户名/news-fetcher
```

## 📋 说明

- GitHub Actions 服务器在美国，无需代理即可访问所有国外新闻源
- 报告自动去重、过滤体育娱乐内容
- 支持暗色模式、关键词搜索、按国家筛选
