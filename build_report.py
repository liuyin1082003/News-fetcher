#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 fetch_news.py 输出的 JSON 生成：
  1. news_YYYY-MM-DD.html - 当日新闻详情页
  2. index.html - 日期选择导航首页
  3. manifest.json - 日期元数据清单

用于 GitHub Actions 自动化流程。

用法：
  python build_report.py raw_news.json
  python build_report.py raw_news.json liuyin1082003/News-fetcher
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

# ─── 每日新闻详情页模板 ─────────────────────────────────────

DAILY_TEMPLATE = """<!DOCTYPE html>
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
.btn{{padding:8px 16px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:14px;background:var(--card-bg);color:var(--text);transition:all .2s;white-space:nowrap;text-decoration:none}}
.btn:hover{{border-color:var(--accent);color:var(--accent)}}
.btn-nav{{padding:8px 12px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:14px;background:var(--card-bg);color:var(--text);transition:all .2s;white-space:nowrap;text-decoration:none;font-weight:700}}
.btn-nav:hover{{border-color:var(--accent);color:var(--accent)}}
.btn-nav.disabled{{opacity:.3;pointer-events:none;cursor:default}}
.btn-back{{border-color:var(--accent);color:var(--accent);font-weight:500}}
.date-picker{{padding:8px 12px;border:1px solid var(--border);border-radius:6px;font-size:14px;background:var(--card-bg);color:var(--text);cursor:pointer;min-width:170px;font-weight:600;transition:border-color .2s}}
.date-picker:focus{{outline:none;border-color:var(--accent)}}
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

<!-- NEWS_META: {meta_json} -->
<div class="header">
    <h1>📰 国际涉华新闻日报</h1>
    <div class="header-actions">
        <a href="#" class="btn btn-nav" id="btnPrev" title="前一天">◀</a>
        <select class="date-picker" id="datePicker"></select>
        <a href="#" class="btn btn-nav" id="btnNext" title="后一天">▶</a>
        <a href="./" class="btn btn-back" title="返回日期列表">📋</a>
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
    <p style="margin-top:6px"><a href="./">📅 查看其他日期的报道</a></p>
</div>

<script>
var DATA = {articles_json};
var DATE = '{date}';
var REPO = '{repo}';
var ALL_DATES = {all_dates_json};

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
    initDateNav();
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

function initDateNav(){{
    if(!ALL_DATES||!ALL_DATES.length)return;
    // 找到当天在所有日期中的索引
    var curIdx=-1;
    for(var i=0;i<ALL_DATES.length;i++){{if(ALL_DATES[i].date===DATE){{curIdx=i;break;}}}}

    // 填充日期下拉框
    var sel=document.getElementById('datePicker');
    ALL_DATES.forEach(function(d){{
        var opt=document.createElement('option');
        opt.value=d.date;
        // 显示格式: "6月12日 · 16篇 · 8国"
        var parts=d.date.split('-');
        var label=parseInt(parts[1])+'月'+parseInt(parts[2])+'日 · '+d.articles+'篇 · '+d.countries+'国';
        if(d.date===DATE)label='📍 '+label;
        opt.textContent=label;
        if(d.date===DATE)opt.selected=true;
        sel.appendChild(opt);
    }});
    sel.addEventListener('change',function(){{
        var v=this.value;
        if(v!==DATE)window.location.href='news_'+v+'.html';
    }});

    // 前后天按钮
    var btnPrev=document.getElementById('btnPrev');
    var btnNext=document.getElementById('btnNext');
    if(curIdx<=0)btnPrev.classList.add('disabled');
    else btnPrev.addEventListener('click',function(e){{e.preventDefault();if(curIdx>0)window.location.href='news_'+ALL_DATES[curIdx-1].date+'.html';}});
    if(curIdx>=ALL_DATES.length-1)btnNext.classList.add('disabled');
    else btnNext.addEventListener('click',function(e){{e.preventDefault();if(curIdx<ALL_DATES.length-1)window.location.href='news_'+ALL_DATES[curIdx+1].date+'.html';}});

    // 键盘左右箭头翻页
    document.addEventListener('keydown',function(e){{
        if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;
        if(e.key==='ArrowLeft'&&curIdx>0)window.location.href='news_'+ALL_DATES[curIdx-1].date+'.html';
        if(e.key==='ArrowRight'&&curIdx<ALL_DATES.length-1)window.location.href='news_'+ALL_DATES[curIdx+1].date+'.html';
    }});
}}
</script>
</body>
</html>"""

# ─── 日期导航首页模板 ───────────────────────────────────────

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国际涉华新闻日报</title>
<style>
:root{{
    --bg:#f5f5f5;--card-bg:#fff;--text:#333;--text2:#666;--border:#e0e0e0;
    --accent:#1a73e8;--accent-lt:#e8f0fe;--accent2:#0d9488;--accent2-lt:#e6fffa;
    --shadow:0 2px 8px rgba(0,0,0,.08);--hdr-bg:#1a1a2e;--hdr-text:#fff;
    --today-bg:linear-gradient(135deg,#1a73e8,#0d9488);--today-text:#fff
}}
[data-theme="dark"]{{
    --bg:#1a1a2e;--card-bg:#16213e;--text:#e0e0e0;--text2:#a0a0a0;--border:#2a2a4a;
    --accent:#64b5f6;--accent-lt:#1e3a5f;--accent2:#4dd0b8;--accent2-lt:#1a3a35;
    --shadow:0 2px 8px rgba(0,0,0,.3);--hdr-bg:#0d0d1a;
    --today-bg:linear-gradient(135deg,#1a73e8,#0d9488);--today-text:#fff
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.7;transition:background .3s,color .3s;min-height:100vh}}
.header{{background:var(--hdr-bg);color:var(--hdr-text);padding:20px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.2)}}
.header h1{{font-size:1.5em;font-weight:700}}
.header p{{font-size:14px;opacity:.8}}
.btn{{padding:8px 16px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:14px;background:var(--card-bg);color:var(--text);transition:all .2s;white-space:nowrap;text-decoration:none;display:inline-block}}
.btn:hover{{border-color:var(--accent);color:var(--accent)}}
.container{{max-width:960px;margin:0 auto;padding:28px 20px}}
.hero{{text-align:center;padding:32px 20px 24px}}
.hero h2{{font-size:1.6em;font-weight:700;margin-bottom:8px;color:var(--text)}}
.hero p{{color:var(--text2);font-size:15px}}
.stats-bar{{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;margin-bottom:32px}}
.stat-card{{background:var(--card-bg);border:1px solid var(--border);border-radius:12px;padding:18px 28px;text-align:center;min-width:120px;box-shadow:var(--shadow);transition:transform .2s}}
.stat-card:hover{{transform:translateY(-2px)}}
.stat-card .stat-num{{font-size:2em;font-weight:700;color:var(--accent);line-height:1.2}}
.stat-card .stat-label{{font-size:13px;color:var(--text2);margin-top:4px}}
.date-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:20px}}
.date-card{{background:var(--card-bg);border:2px solid var(--border);border-radius:12px;padding:20px 24px;cursor:pointer;transition:all .25s;text-decoration:none;color:var(--text);display:block;box-shadow:var(--shadow);position:relative;overflow:hidden}}
.date-card:hover{{border-color:var(--accent);transform:translateY(-3px);box-shadow:0 6px 20px rgba(0,0,0,.14)}}
.date-card.today{{border-color:transparent;background:var(--today-bg);color:var(--today-text);box-shadow:0 4px 16px rgba(26,115,232,.3)}}
.date-card.today:hover{{transform:translateY(-3px);box-shadow:0 8px 24px rgba(26,115,232,.4)}}
.date-card .date-num{{font-size:2.2em;font-weight:800;line-height:1.1;margin-bottom:2px}}
.date-card.today .date-num{{color:#fff}}
.date-card .date-week{{font-size:13px;opacity:.7;margin-bottom:12px}}
.date-card .date-meta{{display:flex;gap:16px;font-size:13px;opacity:.85}}
.date-card.today .date-meta{{opacity:.9}}
.date-card .date-meta span{{display:flex;align-items:center;gap:4px}}
.date-card .today-badge{{position:absolute;top:12px;right:14px;background:rgba(255,255,255,.25);color:#fff;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:600}}
.footer{{text-align:center;padding:30px;color:var(--text2);font-size:13px;border-top:1px solid var(--border);margin-top:30px}}
.footer a{{color:var(--accent)}}
.empty-state{{text-align:center;padding:60px 20px;color:var(--text2)}}
.empty-state .empty-icon{{font-size:3em;margin-bottom:16px}}
.view-toggle{{display:flex;gap:4px;margin-bottom:24px;justify-content:center}}
.view-toggle .btn{{border-radius:8px}}
.view-toggle .btn.active{{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600}}
.calendar-container{{}}
.calendar{{
    background:var(--card-bg);border:1px solid var(--border);border-radius:14px;
    padding:16px 20px 20px;box-shadow:var(--shadow);max-width:700px;margin:0 auto 20px
}}
.cal-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}
.cal-month{{font-size:1.15em;font-weight:700;color:var(--text)}}
.cal-nav{{padding:4px 10px;border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:14px;background:var(--card-bg);color:var(--text)}}
.cal-nav:hover{{border-color:var(--accent);color:var(--accent)}}
.cal-weekdays{{display:grid;grid-template-columns:repeat(7,1fr);text-align:center;font-size:12px;color:var(--text2);margin-bottom:6px;font-weight:600}}
.cal-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}}
.cal-cell{{
    aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
    border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;color:var(--text);
    transition:all .15s;position:relative;text-decoration:none;min-width:0
}}
.cal-cell:hover{{background:var(--accent-lt);color:var(--accent);transform:scale(1.05)}}
.cal-cell.empty{{cursor:default;color:var(--border)}}
.cal-cell.empty:hover{{background:transparent;transform:none;color:var(--border)}}
.cal-cell.today{{background:var(--accent);color:#fff;font-weight:700;box-shadow:0 2px 8px rgba(26,115,232,.3)}}
.cal-cell.today:hover{{background:var(--accent);color:#fff}}
.cal-cell .day-num{{font-size:14px;line-height:1}}
.cal-cell .day-count{{font-size:9px;line-height:1;opacity:.7;margin-top:1px}}
@media(max-width:768px){{
    .header{{padding:14px 16px}}.header h1{{font-size:1.2em}}
    .container{{padding:14px 10px}}
    .hero{{padding:20px 10px 16px}}.hero h2{{font-size:1.3em}}
    .date-grid{{grid-template-columns:1fr;gap:12px}}
    .date-card .date-num{{font-size:1.6em}}
    .stats-bar{{gap:12px}}.stat-card{{min-width:90px;padding:14px 18px}}
    .stat-card .stat-num{{font-size:1.5em}}
}}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>📰 国际涉华新闻日报</h1>
        <p>每日自动抓取 · 北京时间 16:00 更新 · RSS + Google News</p>
    </div>
    <button class="btn" id="themeToggle" title="切换暗色模式">🌙</button>
</div>

<div class="container">
    <div class="hero">
        <h2>📅 选择日期查看报道</h2>
        <p>点击日期卡片，查看当日国际媒体涉华报道</p>
    </div>

    <div class="stats-bar">
        <div class="stat-card">
            <div class="stat-num">{total_days}</div>
            <div class="stat-label">📅 收录天数</div>
        </div>
        <div class="stat-card">
            <div class="stat-num">{total_articles}</div>
            <div class="stat-label">📰 报道总数</div>
        </div>
    </div>

    <div class="view-toggle">
        <button class="btn active" id="btnCardView">📋 列表视图</button>
        <button class="btn" id="btnCalView">📅 日历视图</button>
    </div>

    <div class="date-grid" id="dateGrid">
        <!-- JS 动态渲染 -->
    </div>

    <div class="calendar-container" id="calContainer" style="display:none">
        <div class="calendar" id="calendar">
            <!-- JS 动态渲染 -->
        </div>
    </div>

    <div class="empty-state" id="emptyState" style="display:none">
        <div class="empty-icon">📭</div>
        <h3>暂无数据</h3>
        <p>请等待首次新闻抓取完成</p>
    </div>
</div>

<div class="footer">
    <p>🤖 由 GitHub Actions 自动生成 · 每日定时更新 · <a href="https://github.com/{repo}">查看源码</a></p>
    <p style="margin-top:6px">数据来源：RSS 订阅 + Google News 搜索 · 仅展示标题摘要，深度分析请使用 Claude Code /daily_news</p>
</div>

<script>
var DATES = {manifest_json};
var TODAY = '{today_str}';

var WEEKDAYS = ['周日','周一','周二','周三','周四','周五','周六'];

function formatDate(dateStr) {{
    var parts = dateStr.split('-');
    return parts[0]+'年'+parseInt(parts[1])+'月'+parseInt(parts[2])+'日';
}}

function getWeekday(dateStr) {{
    var d = new Date(dateStr + 'T00:00:00');
    return WEEKDAYS[d.getDay()];
}}

function render() {{
    if (!DATES.length) {{
        document.getElementById('emptyState').style.display = 'block';
        return;
    }}

    var h = '';
    DATES.forEach(function(item) {{
        var isToday = item.date === TODAY;
        var cls = isToday ? 'date-card today' : 'date-card';
        var badge = isToday ? '<div class="today-badge">今天</div>' : '';

        h += '<a href="news_'+item.date+'.html" class="'+cls+'">';
        h += badge;
        h += '<div class="date-num">'+parseInt(item.date.split('-')[2])+'</div>';
        h += '<div class="date-week">'+formatDate(item.date)+' '+getWeekday(item.date)+'</div>';
        h += '<div class="date-meta">';
        h += '<span>📰 '+item.articles+' 篇</span>';
        h += '<span>🌍 '+item.countries+' 国</span>';
        h += '</div>';
        h += '</a>';
    }});
    document.getElementById('dateGrid').innerHTML = h;
}}

document.addEventListener('DOMContentLoaded', function() {{
    // 暗色模式
    try {{
        if (localStorage.getItem('nt') === 'dark') {{
            document.documentElement.setAttribute('data-theme', 'dark');
            document.getElementById('themeToggle').textContent = '☀️';
        }}
    }} catch(e) {{}}

    render();
    renderCalendar();

    // 视图切换
    var btnCard=document.getElementById('btnCardView');
    var btnCal=document.getElementById('btnCalView');
    var dateGrid=document.getElementById('dateGrid');
    var calContainer=document.getElementById('calContainer');

    function switchView(mode){{
        if(mode==='card'){{
            dateGrid.style.display='';calContainer.style.display='none';
            btnCard.classList.add('active');btnCal.classList.remove('active');
        }}else{{
            dateGrid.style.display='none';calContainer.style.display='block';
            btnCard.classList.remove('active');btnCal.classList.add('active');
            renderCalendar();
        }}
        try{{localStorage.setItem('nv',mode)}}catch(e){{}}
    }}

    btnCard.addEventListener('click',function(){{switchView('card')}});
    btnCal.addEventListener('click',function(){{switchView('cal')}});

    // 恢复上次视图选择
    try{{if(localStorage.getItem('nv')==='cal')switchView('cal')}}catch(e){{}}

    document.getElementById('themeToggle').addEventListener('click', function() {{
        var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', next);
        this.textContent = next === 'dark' ? '☀️' : '🌙';
        try {{ localStorage.setItem('nt', next); }} catch(e) {{}}
    }});

    // 快捷键
    document.addEventListener('keydown', function(e) {{
        if ((e.ctrlKey || e.metaKey) && e.key === 'd' && !e.shiftKey) {{
            e.preventDefault();
            document.getElementById('themeToggle').click();
        }}
    }});
}});

var calYear,calMonth;
function renderCalendar(){{
    if(!DATES.length)return;
    // 默认显示当前月份
    var now=new Date(TODAY+'T00:00:00');
    if(typeof calYear==='undefined'){{calYear=now.getFullYear();calMonth=now.getMonth()+1;}}

    var dateMap={{}};
    DATES.forEach(function(d){{dateMap[d.date]=d;}});

    var firstDay=new Date(calYear,calMonth-1,1);
    var lastDay=new Date(calYear,calMonth,0);
    var startDow=firstDay.getDay();
    var totalDays=lastDay.getDate();

    var WEEKDAYS=['日','一','二','三','四','五','六'];
    var MONTHS=['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];

    var h='';
    h+='<div class="cal-header">';
    h+='<button class="cal-nav" onclick="calShift(-1)">◀</button>';
    h+='<span class="cal-month">'+calYear+'年 '+MONTHS[calMonth-1]+'</span>';
    h+='<button class="cal-nav" onclick="calShift(1)">▶</button>';
    h+='</div>';
    h+='<div class="cal-weekdays">';
    WEEKDAYS.forEach(function(w){{h+='<span>'+w+'</span>';}});
    h+='</div><div class="cal-grid">';

    // 填充空白
    for(var i=0;i<startDow;i++)h+='<span class="cal-cell empty"></span>';

    for(var d=1;d<=totalDays;d++){{
        var ds=calYear+'-'+String(calMonth).padStart(2,'0')+'-'+String(d).padStart(2,'0');
        var meta=dateMap[ds];
        var isToday=ds===TODAY;
        var cls=isToday?'cal-cell today':'cal-cell';
        if(meta){{
            h+='<a href="news_'+ds+'.html" class="'+cls+'" title="'+meta.articles+'篇报道, '+meta.countries+'国">';
            h+='<span class="day-num">'+d+'</span>';
            h+='<span class="day-count">'+meta.articles+'篇</span>';
            h+='</a>';
        }}else{{
            h+='<span class="cal-cell empty">';
            h+='<span class="day-num">'+d+'</span>';
            h+='</span>';
        }}
    }}
    h+='</div>';
    document.getElementById('calendar').innerHTML=h;
}}

function calShift(delta){{
    calMonth+=delta;
    if(calMonth>12){{calMonth=1;calYear++;}}
    if(calMonth<1){{calMonth=12;calYear--;}}
    renderCalendar();
}}
</script>
</body>
</html>"""


# ─── 核心函数 ────────────────────────────────────────────────


def build_report(json_path, repo="liuyin1082003/News-fetcher"):
    """主函数：生成当日报告 + 更新日期清单 + 生成日期导航首页

    Args:
        json_path: fetch_news.py 输出的 JSON 文件路径
        repo: GitHub 仓库名（用于页面底部链接）
    """
    # 1. 读取 JSON 数据
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    today = datetime.now().strftime("%Y-%m-%d")

    # 2. 提取元数据
    countries = set()
    for a in articles:
        c = a.get("country", "未知")
        countries.add(c)

    today_meta = {
        "articles": len(articles),
        "countries": len(countries),
    }

    # 3. 确保输出目录存在
    os.makedirs("news_output", exist_ok=True)

    # 4. 扫描所有已有 HTML 文件，构建完整日期列表
    all_dates = _scan_all_dates(today, today_meta)

    # 构建日期卡片列表（按日期降序），供模板使用
    dates_sorted = sorted(all_dates.items(), key=lambda x: x[0], reverse=True)
    all_dates_list = [
        {"date": d, "articles": m["articles"], "countries": m["countries"]}
        for d, m in dates_sorted
    ]

    # 5. 生成当日新闻详情页（带日期导航）
    daily_html = DAILY_TEMPLATE.format(
        date=today,
        repo=repo,
        meta_json=json.dumps(today_meta, ensure_ascii=False),
        articles_json=json.dumps(articles, ensure_ascii=False),
        all_dates_json=json.dumps(all_dates_list, ensure_ascii=False),
    )

    daily_path = f"news_output/news_{today}.html"
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write(daily_html)

    print(f"✅ 日报: {daily_path}  ({len(articles)} 篇报道)", file=sys.stderr)

    # 6. 重新生成所有历史日期的日报（确保日期导航功能一致）
    regenerated = 0
    import re as _re
    for date_str in all_dates:
        if date_str == today:
            continue
        old_path = f"news_output/news_{date_str}.html"
        if not os.path.exists(old_path):
            continue
        old_articles = _extract_articles_from_html(old_path)
        if not old_articles:
            # 从 manifest 取元数据，至少生成空页面骨架
            meta = all_dates.get(date_str, {"articles": 0, "countries": 0})
            old_articles = []
        daily_html = DAILY_TEMPLATE.format(
            date=date_str,
            repo=repo,
            meta_json=json.dumps(all_dates.get(date_str, {"articles": len(old_articles), "countries": 0}), ensure_ascii=False),
            articles_json=json.dumps(old_articles, ensure_ascii=False),
            all_dates_json=json.dumps(all_dates_list, ensure_ascii=False),
        )
        with open(old_path, "w", encoding="utf-8") as f:
            f.write(daily_html)
        regenerated += 1
    if regenerated:
        print(f"  🔄 重新生成了 {regenerated} 个历史日期的日报，同步日期导航功能", file=sys.stderr)

    # 7. 保存 manifest + 生成日期导航首页
    manifest = {"dates": all_dates}
    _save_manifest(manifest)

    # 6. 生成日期导航首页
    index_html = _build_index_html(manifest, repo)
    index_path = "news_output/index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    print(f"✅ 首页: {index_path}  ({len(all_dates)} 天记录)", file=sys.stderr)

    return daily_path


def _scan_all_dates(today, today_meta):
    """扫描 news_output/ 下所有 news_*.html，提取元数据。

    对于当日：直接使用刚抓取的元数据。
    对于历史日期：尝试从 HTML 中的 <!-- NEWS_META: ... --> 注释提取。
    提取失败则从嵌入的 JSON 数据中统计。

    Returns:
        dict: {"2026-06-11": {"articles": 38, "countries": 10}, ...}
    """
    import re
    import glob as glob_mod

    all_dates = {}

    # 列出所有 news_*.html 文件
    pattern = os.path.join("news_output", "news_*.html")
    for filepath in sorted(glob_mod.glob(pattern)):
        filename = os.path.basename(filepath)
        # 提取日期: news_2026-06-11.html → 2026-06-11
        date_match = re.match(r"news_(\d{4}-\d{2}-\d{2})\.html", filename)
        if not date_match:
            continue
        date_str = date_match.group(1)

        # 当日数据直接用传入的元数据
        if date_str == today:
            all_dates[date_str] = today_meta
            continue

        # 历史日期：尝试从 HTML 注释提取
        meta = _extract_meta_from_html(filepath)
        if meta:
            all_dates[date_str] = meta
            print(f"  📅 {date_str}: {meta['articles']} 篇, {meta['countries']} 国 (从HTML提取)", file=sys.stderr)
        else:
            # 提取失败，用占位数据（至少日期能显示）
            all_dates[date_str] = {"articles": 0, "countries": 0}
            print(f"  ⚠️ {date_str}: 无法提取元数据，使用占位值", file=sys.stderr)

    # 确保当日始终在列表中（即使文件尚未生成，因为上面的循环只扫描已存在的文件）
    if today not in all_dates:
        all_dates[today] = today_meta

    return all_dates


def _extract_meta_from_html(filepath):
    """从 HTML 文件中提取元数据。

    优先从 <!-- NEWS_META: {...} --> 注释提取（最快）。
    失败则从 var DATA = [...] 中统计。
    """
    import re

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # 方法1: 从 NEWS_META 注释提取
    meta_match = re.search(r"<!-- NEWS_META:\s*(\{.*?\})\s*-->", content)
    if meta_match:
        try:
            meta = json.loads(meta_match.group(1))
            if "articles" in meta and "countries" in meta:
                return meta
        except json.JSONDecodeError:
            pass

    # 方法2: 从 var DATA = [...] 统计
    data_match = re.search(r"var DATA = (\[.*?\]);", content, re.DOTALL)
    if data_match:
        try:
            articles = json.loads(data_match.group(1))
            countries = set(a.get("country", "未知") for a in articles)
            return {
                "articles": len(articles),
                "countries": len(countries),
            }
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _extract_articles_from_html(filepath):
    """从历史 HTML 文件中提取完整的文章数据，用于重新生成。

    从 var DATA = [...] 中提取完整 JSON 数组。
    支持旧版模板（有 summary 字段）和新版模板。

    Returns:
        list | None: 文章列表，提取失败返回 None
    """
    import re

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # 匹配 var DATA = [...];  使用非贪婪匹配到第一个 ]; 为止
    data_match = re.search(r"var DATA = (\[.*?\]);\s*$", content, re.MULTILINE | re.DOTALL)
    if not data_match:
        # 更宽松的匹配
        data_match = re.search(r"var DATA\s*=\s*(\[[^\]]*\])\s*;", content, re.DOTALL)
    if data_match:
        try:
            articles = json.loads(data_match.group(1))
            if isinstance(articles, list) and len(articles) > 0:
                return articles
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _load_manifest():
    """读取现有的 manifest.json，不存在则返回空结构"""
    manifest_path = "news_output/manifest.json"
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("  ⚠️ manifest.json 损坏，重新创建", file=sys.stderr)
    return {"dates": {}}


def _save_manifest(manifest):
    """保存 manifest.json"""
    manifest_path = "news_output/manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def _build_index_html(manifest, repo):
    """根据 manifest 生成日期导航首页 HTML

    Args:
        manifest: {"dates": {"2026-06-11": {"articles": 38, "countries": 10}, ...}}
        repo: GitHub 仓库名
    """
    dates = manifest.get("dates", {})

    # 按日期降序排列
    dates_sorted = sorted(dates.items(), key=lambda x: x[0], reverse=True)

    # 汇总统计
    total_articles = sum(m["articles"] for _, m in dates_sorted)
    total_days = len(dates_sorted)
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 构建日期卡片数据
    date_cards = []
    for date_str, meta in dates_sorted:
        date_cards.append({
            "date": date_str,
            "articles": meta["articles"],
            "countries": meta["countries"],
        })

    return INDEX_TEMPLATE.format(
        total_days=total_days,
        total_articles=total_articles,
        today_str=today_str,
        manifest_json=json.dumps(date_cards, ensure_ascii=False),
        repo=repo,
    )


# ─── CLI 入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python build_report.py raw_news.json [github-repo]", file=sys.stderr)
        print("示例: python build_report.py raw_news.json liuyin1082003/News-fetcher", file=sys.stderr)
        sys.exit(1)

    json_path = sys.argv[1]
    repo = sys.argv[2] if len(sys.argv) > 2 else "liuyin1082003/News-fetcher"

    if not os.path.exists(json_path):
        print(f"❌ 文件不存在: {json_path}", file=sys.stderr)
        sys.exit(1)

    build_report(json_path, repo)
    print("\n🎉 全部完成！", file=sys.stderr)
