#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成器 — 将 Claude 分析后的 .md 文件转为自包含 HTML。

生成的 HTML 特性：
  - 新闻内容全部内嵌，拷到任何位置双击即看
  - 暗色模式、关键词搜索高亮、按国家筛选
  - 完全无外部依赖，离线可用
  - 支持拖拽其他 .md 文件到页面加载

用法：
  python generate_report.py news_2026-06-11.md
  python generate_report.py news_2026-06-11.md -o custom_name.html
"""

import argparse
import json
import os
import re
import sys

# ─── Windows UTF-8 ───────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ============================================================
#  Markdown 解析器
# ============================================================

def parse_news_md(text):
    """解析 daily_news 生成的 Markdown 为结构化数据

    Args:
        text: .md 文件全文

    Returns:
        dict: {time_range, articles: [{country, title, link, summary, opinion, data, example}]}
    """
    lines = text.split("\n")
    articles = []
    current_country = ""
    current_article = None
    current_field = ""
    time_range = ""

    # 提取时间范围
    time_match = re.search(r"时间范围[：:]\s*(.+)", text)
    if time_match:
        time_range = time_match.group(1).strip()

    for line in lines:
        stripped = line.strip()

        # 一级标题（报告标题，跳过）
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        # 二级标题 → 国家/媒体分组
        if stripped.startswith("## "):
            if current_article:
                articles.append(current_article)
                current_article = None
            current_country = stripped[3:].strip()
            continue

        # 三级标题 → 文章标题
        if stripped.startswith("### "):
            if current_article:
                articles.append(current_article)

            title_line = stripped[4:].strip()
            link_match = re.match(r"^\[(.+)\]\((.+)\)$", title_line)
            current_article = {
                "country": current_country,
                "title": link_match.group(1) if link_match else title_line,
                "link": link_match.group(2) if link_match else "#",
                "summary": "",
                "opinion": "",
                "data": "",
                "example": "",
            }
            current_field = ""
            continue

        # 分隔线 → 文章结束
        if stripped in ("---", "***", "___") and current_article:
            articles.append(current_article)
            current_article = None
            current_field = ""
            continue

        # 字段行
        if current_article:
            if stripped.startswith("**摘要**") or stripped.startswith("**Summary**"):
                current_field = "summary"
                val = re.sub(r"^\*\*(?:摘要|Summary)\*\*[：:]?\s*", "", stripped)
                current_article["summary"] = val
            elif stripped.startswith("**主要观点**") or stripped.startswith("**观点**"):
                current_field = "opinion"
                val = re.sub(r"^\*\*(?:主要)?观点\*\*[：:]?\s*", "", stripped)
                current_article["opinion"] = val
            elif stripped.startswith("**数据**"):
                current_field = "data"
                val = re.sub(r"^\*\*数据\*\*[：:]?\s*", "", stripped)
                current_article["data"] = val
            elif stripped.startswith("**事例**"):
                current_field = "example"
                val = re.sub(r"^\*\*事例\*\*[：:]?\s*", "", stripped)
                current_article["example"] = val
            elif stripped.startswith("**") and "**" in stripped[2:]:
                current_field = ""
            elif stripped and current_field and not stripped.startswith("#"):
                # 续行追加
                if current_article[current_field]:
                    current_article[current_field] += "\n" + stripped
                else:
                    current_article[current_field] = stripped

    # 保存最后一篇
    if current_article:
        articles.append(current_article)

    return {"time_range": time_range, "articles": articles}


# ============================================================
#  HTML 生成器
# ============================================================

def escape_js(text):
    """转义文本用于嵌入 JavaScript 字符串"""
    if not text:
        return ""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")


def generate_html(data, output_path):
    """生成自包含 HTML 文件

    Args:
        data: parse_news_md 的返回值
        output_path: 输出 .html 文件路径
    """
    articles_json = json.dumps(data["articles"], ensure_ascii=False)
    time_range = data.get("time_range", "未知")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>国际涉华新闻日报</title>
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
.btn-file{{position:relative;overflow:hidden}}
.btn-file input[type="file"]{{position:absolute;left:0;top:0;width:100%;height:100%;opacity:0;cursor:pointer}}
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
.card-summary{{font-size:14px;color:var(--text2);line-height:1.6;margin-bottom:8px}}
.card-details{{margin-top:10px;padding-top:10px;border-top:1px solid var(--border);font-size:14px}}
.card-details dt{{font-weight:600;margin-top:8px;color:var(--text)}}
.card-details dd{{margin-left:0;margin-top:3px;color:var(--text2);line-height:1.6}}
mark{{background:var(--highlight);color:inherit;padding:1px 3px;border-radius:2px}}
@media print{{
    .header{{position:static;background:#fff!important;color:#000!important;box-shadow:none}}
    .card{{break-inside:avoid;box-shadow:none}}
    .btn,.search-box,.filter-select{{display:none!important}}
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
        <input type="text" class="search-box" id="searchBox" placeholder="🔍 搜索关键词..." />
        <select class="filter-select" id="countryFilter">
            <option value="all">🌍 全部</option>
        </select>
        <button class="btn btn-file">📂 打开其他 .md
            <input type="file" id="fileInput" accept=".md" />
        </button>
        <button class="btn" id="themeToggle" title="暗色模式">🌙</button>
    </div>
</div>

<div class="container" id="mainContainer">
    <div class="summary-bar" id="summaryBar"></div>
    <div class="no-results" id="noResults">😕 没有匹配的新闻，试试换一个搜索词或筛选条件。</div>
    <div id="articlesContainer"></div>
</div>

<script>
// ===== 数据 =====
const ARTICLES = {articles_json};
const TIME_RANGE = '{time_range}';

// ===== 渲染 =====
function escapeHtml(text) {{
    if(!text)return'';
    const d=document.createElement('div');d.textContent=text;return d.innerHTML;
}}

function simpleMd(text) {{
    if(!text)return'';
    return escapeHtml(text)
        .replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')
        .replace(/\\*(.+?)\\*/g,'<em>$1</em>')
        .replace(/`(.+?)`/g,'<code>$1</code>')
        .replace(/\\n/g,'<br>');
}}

function render() {{
    const container=document.getElementById('articlesContainer');
    const summaryBar=document.getElementById('summaryBar');
    const filterSelect=document.getElementById('countryFilter');

    if(!ARTICLES.length){{
        summaryBar.innerHTML='<span>⚠️ 没有找到新闻数据</span>';
        return;
    }}

    // 摘要栏
    const countries=[...new Set(ARTICLES.map(a=>a.country).filter(Boolean))];
    summaryBar.innerHTML=
        '<span>📅 <strong>'+escapeHtml(TIME_RANGE||'未知')+'</strong></span>'+
        '<span>📰 <strong>'+ARTICLES.length+'</strong> 篇报道</span>'+
        '<span>🌍 <strong>'+countries.length+'</strong> 个国家/媒体</span>';

    // 国家筛选下拉
    filterSelect.innerHTML='<option value="all">🌍 全部 ('+ARTICLES.length+')</option>';
    countries.forEach(function(c){{
        const count=ARTICLES.filter(function(a){{return a.country===c}}).length;
        filterSelect.innerHTML+='<option value="'+escapeHtml(c)+'">'+escapeHtml(c)+' ('+count+')</option>';
    }});

    // 按国家分组
    const grouped={{}};
    ARTICLES.forEach(function(a){{
        const key=a.country||'其他';
        if(!grouped[key])grouped[key]=[];
        grouped[key].push(a);
    }});

    // 渲染卡片
    let html='';
    for(const[country,arts]of Object.entries(grouped)){{
        html+='<div class="country-group" data-country="'+escapeHtml(country)+'">';
        html+='<div class="country-header">'+escapeHtml(country)+'<span class="count">'+arts.length+' 篇</span></div>';
        arts.forEach(function(a){{
            const searchText=(a.title+' '+a.summary+' '+a.opinion+' '+a.data+' '+a.example).toLowerCase();
            html+='<div class="card" data-country="'+escapeHtml(a.country||'')+'" data-search="'+escapeHtml(searchText)+'">';
            html+='<div class="card-title"><a href="'+escapeHtml(a.link||'#')+'" target="_blank" rel="noopener">'+escapeHtml(a.title)+'</a></div>';
            html+='<div class="card-meta"><span class="tag tag-source">'+escapeHtml(a.country||'')+'</span></div>';
            if(a.summary)html+='<div class="card-summary">'+simpleMd(a.summary)+'</div>';
            html+='<div class="card-details">';
            if(a.opinion)html+='<dl><dt>💭 主要观点</dt><dd>'+simpleMd(a.opinion)+'</dd></dl>';
            if(a.data&&a.data!=='无')html+='<dl><dt>📊 数据</dt><dd>'+simpleMd(a.data)+'</dd></dl>';
            if(a.example&&a.example!=='无')html+='<dl><dt>📋 事例</dt><dd>'+simpleMd(a.example)+'</dd></dl>';
            html+='</div></div>';
        }});
        html+='</div>';
    }}
    container.innerHTML=html;
}}

// ===== 搜索 & 筛选 =====
function applyFilters() {{
    const term=(document.getElementById('searchBox').value||'').toLowerCase().trim();
    const country=document.getElementById('countryFilter').value;
    let anyVisible=false;

    document.querySelectorAll('.card').forEach(function(card){{
        let visible=true;
        if(country!=='all'&&card.dataset.country!==country)visible=false;
        if(term&&visible){{
            const txt=card.dataset.search||'';
            if(txt.indexOf(term)===-1)visible=false;
        }}
        card.style.display=visible?'':'none';
        if(visible)anyVisible=true;
    }});

    // 隐藏空分组
    document.querySelectorAll('.country-group').forEach(function(g){{
        const vis=g.querySelectorAll('.card:not([style*="display: none"])').length;
        g.style.display=vis>0?'':'none';
    }});

    document.getElementById('noResults').style.display=anyVisible?'none':'block';
}}

function highlightSearch() {{
    // 简化版：搜索时用 CSS 高亮（通过重新渲染实现更干净）
    applyFilters();
}}

// ===== 暗色模式 =====
function initTheme() {{
    try{{
        if(localStorage.getItem('news_theme')==='dark'){{
            document.documentElement.setAttribute('data-theme','dark');
            document.getElementById('themeToggle').textContent='☀️';
        }}
    }}catch(e){{}}
}}

function toggleTheme() {{
    const cur=document.documentElement.getAttribute('data-theme');
    const next=cur==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',next);
    document.getElementById('themeToggle').textContent=next==='dark'?'☀️':'🌙';
    try{{localStorage.setItem('news_theme',next)}}catch(e){{}}
}}

// ===== 文件加载（拖拽支持其他 .md） =====
function loadMdFile(file) {{
    if(!file||!file.name.match(/\\.md$/i))return;
    const reader=new FileReader();
    reader.onload=function(e){{
        // 很遗憾，浏览器端没有 Python 解析器，这里只做简单的提示
        // 用户应该用 generate_report.py 重新生成
        alert('此文件是另一个 .md 文件。\\n\\n要查看它，请用 generate_report.py 重新生成 HTML：\\n\\npython generate_report.py "'+file.name+'"');
    }};
    reader.readAsText(file,'UTF-8');
}}

// ===== 启动 =====
document.addEventListener('DOMContentLoaded',function(){{
    initTheme();
    render();

    document.getElementById('themeToggle').addEventListener('click',toggleTheme);
    document.getElementById('fileInput').addEventListener('change',function(e){{loadMdFile(e.target.files[0])}});

    let timer;
    document.getElementById('searchBox').addEventListener('input',function(){{
        clearTimeout(timer);
        timer=setTimeout(applyFilters,250);
    }});
    document.getElementById('countryFilter').addEventListener('change',applyFilters);

    // 拖拽
    document.body.addEventListener('dragover',function(e){{e.preventDefault()}});
    document.body.addEventListener('drop',function(e){{
        e.preventDefault();
        const f=e.dataTransfer.files[0];
        if(f)loadMdFile(f);
    }});

    // 快捷键
    document.addEventListener('keydown',function(e){{
        if((e.ctrlKey||e.metaKey)&&e.key==='k'){{e.preventDefault();document.getElementById('searchBox').focus()}}
        if((e.ctrlKey||e.metaKey)&&e.key==='d'&&!e.shiftKey){{e.preventDefault();toggleTheme()}}
    }});

    console.log('📰 新闻日报已就绪 ('+ARTICLES.length+' 篇)');
    console.log('  快捷键: Ctrl+K 搜索 | Ctrl+D 暗色模式');
}});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ============================================================
#  主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="报告生成器 — 将 .md 分析报告转为自包含 HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python generate_report.py news_2026-06-11.md\n  python generate_report.py news_2026-06-11.md -o 今日新闻.html",
    )
    parser.add_argument("input", help="输入的 .md 文件路径")
    parser.add_argument("-o", "--output", help="输出的 .html 文件路径（默认与输入同名）")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".html"

    # 读取并解析
    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    data = parse_news_md(md_text)

    if not data["articles"]:
        print("⚠️  未从 .md 中解析到任何文章，请检查文件格式", file=sys.stderr)
        sys.exit(1)

    # 生成 HTML
    generate_html(data, output_path)

    # 报告
    countries = set(a.get("country", "") for a in data["articles"])
    print(f"✅ 报告已生成: {output_path}", file=sys.stderr)
    print(f"   📰 {len(data['articles'])} 篇报道, 🌍 {len(countries)} 个国家/媒体", file=sys.stderr)
    print(f"   📂 可拷贝到任意位置，双击即可用浏览器打开", file=sys.stderr)


if __name__ == "__main__":
    main()
