#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 fetch_news.py 输出的 JSON 生成自包含 HTML 报告。
用于 GitHub Actions 自动化流程，不需要 Claude 参与。

用法：
  python build_report.py raw_news.json
"""

import json
import os
import sys
from datetime import datetime

# ─── Windows UTF-8 ───────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── HTML 模板 ───────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国际涉华新闻日报 - {date}</title>
<style>
:root{{
    --bg:#f5f5f5;--card-bg:#fff;--text:#333;--text2:#666;--border:#e0e0e0;
    --accent:#1a73e8;--accent-lt:#e8f0fe;--tag-bg:#e8f0fe;--tag-text:#1a73e8;
    --highlight:#ffeb3b;--shadow:0 2px 8px rgba(0,0,0,.08);--hdr-bg:#1a1a2e;--hdr-text:#fff
}}
[data-theme="dark"]{{
    --bg:#1a1a2e;--card-bg:#16213e;--text:#e0e0e0;--text2:#a0a0a0;--border:#2a2a4a;
    --accent:#64b5f6;--accent-lt:#1e3a5f;--tag-bg:#1e3a5f;--tag-text:#64b5f6;
    --highlight:#5c5200;--shadow:0 2px 8px rgba(0,0,0,.3);--hdr-bg:#0d0d1a
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.7;transition:background .3s,color .3s;min-height:100vh}}
.header{{background:var(--hdr-bg);color:var(--hdr-text);padding:16px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.2)}}
.header h1{{font-size:1.4em;font-weight:700}}
.header-actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.btn{{padding:8px 16px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:14px;background:var(--card-bg);color:var(--text);transition:all .2s;white-space:nowrap}}
.btn:hover{{border-color:var(--accent);color:var(--accent)}}
.search-box{{padding:8px 14px;border:1px solid var(--border);border-radius:6px;font-size:14px;background:var(--card-bg);color:var(--text);width:180px;transition:border-color .2s}}
.search-box:focus{{outline:none;border-color:var(--accent)}}
.filter-select{{padding:8px 12px;border:1px solid var(--border);border-radius:6px;font-size:14px;background:var(--card-bg);color:var(--text);cursor:pointer}}
.container{{max-width:1000px;margin:0 auto;padding:24px 20px}}
.summary-bar{{background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:14px 24px;margin-bottom:20px;display:flex;gap:24px;flex-wrap:wrap;font-size:14px;color:var(--text2);box-shadow:var(--shadow)}}
.summary-bar strong{{color:var(--accent);font-size:1.1em}}
.no-results{{text-align:center;padding:40px;color:var(--text2);font-size:16px;display:none}}
.country-group{{margin-bottom:28px}}
.country-header{{font-size:1.2em;font-weight:700;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid var(--accent);color:var(--accent);display:flex;align-items:center;gap:8px}}
.country-header .count{{font-size:.8em;font-weight:400;color:var(--text2);margin-left:auto}}
.card{{background:var(--card-bg);border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin-bottom:14px;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}}
.card:hover{{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.12)}}
.card-title{{font-size:1.05em;font-weight:600;margin-bottom:8px}}
.card-title a{{color:var(--text);text-decoration:none}}
.card-title a:hover{{color:var(--accent)}}
.card-meta{{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px}}
.tag{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:500;white-space:nowrap}}
.tag-source{{background:var(--accent-lt);color:var(--tag-text)}}
.tag-via{{background:#fff3e0;color:#e65100}}
[data-theme="dark"] .tag-via{{background:#3d2600;color:#ffb74d}}
.card-summary{{font-size:14px;color:var(--text2);line-height:1.6;margin-bottom:4px}}
.card-link{{font-size:13px}}
.card-link a{{color:var(--accent);text-decoration:none}}
.card-link a:hover{{text-decoration:underline}}
mark{{background:var(--highlight);color:inherit;padding:1px 3px;border-radius:2px}}
.footer{{text-align:center;padding:30px;color:var(--text2);font-size:13px;border-top:1px solid var(--border);margin-top:30px}}
.footer a{{color:var(--accent)}}
@media print{{
    .header{{position:static;background:#fff!important;color:#000!important;box-shadow:none}}
    .card{{break-inside:avoid;box-shadow:none}}
    .btn,.search-box,.filter-select,.footer{{display:none!important}}
}}
@media(max-width:768px){{
    .header{{padding:12px 16px}}.header h1{{font-size:1.1em}}
    .container{{padding:14px 10px}}.card{{padding:14px 16px}}
}}
</style>
</head>
<body>

<div class="header">
    <h1>📰 国际涉华新闻日报</h1>
    <div class="header-actions">
        <input type="text" class="search-box" id="searchBox" placeholder="🔍 搜索..." />
        <select class="filter-select" id="countryFilter">
            <option value="all">🌍 全部</option>
        </select>
        <button class="btn" id="themeToggle">🌙</button>
    </div>
</div>

<div class="container">
    <div class="summary-bar" id="summaryBar"></div>
    <div class="no-results" id="noResults">😕 没有匹配的结果，试试换一个搜索词。</div>
    <div id="articlesContainer"></div>
</div>

<div class="footer">
    <p>🤖 由 GitHub Actions 自动生成 · 每日更新 · <a href="https://github.com/{repo}">查看源码</a></p>
    <p style="margin-top:6px">注意：本页面仅展示新闻标题和摘要，不含深度分析。需要分析版请使用 Claude Code /daily_news。</p>
</div>

<script>
var DATA = {articles_json};
var DATE = '{date}';
var REPO = '{repo}';

function escapeHtml(text) {{
    if(!text)return'';
    var d=document.createElement('div');d.textContent=text;return d.innerHTML;
}}

function render() {{
    if(!DATA.length){{
        document.getElementById('summaryBar').innerHTML='<span>⚠️ 今日未抓到涉华新闻，请稍后再试</span>';
        return;
    }}

    var countries=[...new Set(DATA.map(function(a){{return a.country||'未知'}}))];
    document.getElementById('summaryBar').innerHTML=
        '<span>📅 <strong>'+DATE+'</strong></span>'+
        '<span>📰 <strong>'+DATA.length+'</strong> 篇</span>'+
        '<span>🌍 <strong>'+countries.length+'</strong> 个国家/地区</span>'+
        '<span>🔗 来源: RSS + Google News</span>';

    var sel=document.getElementById('countryFilter');
    sel.innerHTML='<option value="all">🌍 全部 ('+DATA.length+')</option>';
    countries.forEach(function(c){{
        var n=DATA.filter(function(a){{return a.country===c}}).length;
        sel.innerHTML+='<option value="'+escapeHtml(c)+'">'+escapeHtml(c)+' ('+n+')</option>';
    }});

    var grouped={{}};
    DATA.forEach(function(a){{
        var k=a.country||'未知';
        if(!grouped[k])grouped[k]=[];
        grouped[k].push(a);
    }});

    var h='';
    for(var c in grouped){{
        var arts=grouped[c];
        h+='<div class="country-group"><div class="country-header">'+escapeHtml(c)+'<span class="count">'+arts.length+' 篇</span></div>';
        arts.forEach(function(a){{
            var txt=(a.title+' '+a.summary).toLowerCase();
            h+='<div class="card" data-country="'+escapeHtml(c)+'" data-search="'+escapeHtml(txt)+'">';
            h+='<div class="card-title"><a href="'+escapeHtml(a.link||'#')+'" target="_blank" rel="noopener">'+escapeHtml(a.title)+'</a></div>';
            h+='<div class="card-meta">';
            h+='<span class="tag tag-source">'+escapeHtml(a.source||c)+'</span>';
            if(a.via)h+='<span class="tag tag-via">'+escapeHtml(a.via)+'</span>';
            h+='</div>';
            if(a.summary)h+='<div class="card-summary">'+escapeHtml(a.summary)+'</div>';
            h+='<div class="card-link"><a href="'+escapeHtml(a.link||'#')+'" target="_blank" rel="noopener">阅读原文 →</a></div>';
            h+='</div>';
        }});
        h+='</div>';
    }}
    document.getElementById('articlesContainer').innerHTML=h;
}}

function filter() {{
    var t=(document.getElementById('searchBox').value||'').toLowerCase().trim();
    var c=document.getElementById('countryFilter').value;
    var vis=false;
    document.querySelectorAll('.card').forEach(function(card){{
        var ok=true;
        if(c!=='all'&&card.dataset.country!==c)ok=false;
        if(t&&ok&&(card.dataset.search||'').indexOf(t)===-1)ok=false;
        card.style.display=ok?'':'none';
        if(ok)vis=true;
    }});
    document.querySelectorAll('.country-group').forEach(function(g){{
        var v=g.querySelectorAll('.card:not([style*="display: none"])').length;
        g.style.display=v>0?'':'none';
    }});
    document.getElementById('noResults').style.display=vis?'none':'block';
}}

document.addEventListener('DOMContentLoaded',function(){{
    try{{if(localStorage.getItem('nt')==='dark'){{document.documentElement.setAttribute('data-theme','dark');document.getElementById('themeToggle').textContent='☀️'}}}}catch(e){{}}
    render();
    document.getElementById('themeToggle').addEventListener('click',function(){{
        var n=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
        document.documentElement.setAttribute('data-theme',n);
        this.textContent=n==='dark'?'☀️':'🌙';
        try{{localStorage.setItem('nt',n)}}catch(e){{}}
    }});
    var t;document.getElementById('searchBox').addEventListener('input',function(){{clearTimeout(t);t=setTimeout(filter,250)}});
    document.getElementById('countryFilter').addEventListener('change',filter);
    document.addEventListener('keydown',function(e){{
        if((e.ctrlKey||e.metaKey)&&e.key==='k'){{e.preventDefault();document.getElementById('searchBox').focus()}}
        if((e.ctrlKey||e.metaKey)&&e.key==='d'&&!e.shiftKey){{e.preventDefault();document.getElementById('themeToggle').click()}}
    }});
    console.log('📰 '+DATA.length+' 篇新闻');
}});
</script>
</body>
</html>"""


def build_report(json_path, repo="username/news-fetcher"):
    """从原始 JSON 生成 HTML 报告

    Args:
        json_path: fetch_news.py 输出的 JSON 文件路径
        repo: GitHub 仓库名（用于页面底部链接）
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])

    if not articles:
        print("⚠️  无新闻数据，生成空报告", file=sys.stderr)

    today = datetime.now().strftime("%Y-%m-%d")

    # 确保输出目录存在
    os.makedirs("news_output", exist_ok=True)

    # 生成日期命名的 HTML
    html = HTML_TEMPLATE.format(
        date=today,
        repo=repo,
        articles_json=json.dumps(articles, ensure_ascii=False),
    )

    output_path = f"news_output/news_{today}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # 同时生成 index.html（GitHub Pages 默认首页）
    index_path = "news_output/index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 报告已生成: {output_path}", file=sys.stderr)
    print(f"✅ 首页已生成: {index_path}", file=sys.stderr)
    print(f"   📰 {len(articles)} 篇报道", file=sys.stderr)

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python build_report.py raw_news.json [github-repo]", file=sys.stderr)
        sys.exit(1)

    repo = sys.argv[2] if len(sys.argv) > 2 else "username/news-fetcher"
    build_report(sys.argv[1], repo)
