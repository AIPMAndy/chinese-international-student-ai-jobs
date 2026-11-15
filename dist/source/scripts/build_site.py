#!/usr/bin/env python3
"""Build the offline-friendly website using Python's standard library only.

Run from the repository: python3 scripts/build_site.py
After GitHub is actually published, supply --repo-url with the verified URL.
PDF/ZIP download files in dist/downloads are preserved between builds.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
DATE = '2026-11-13'
TITLE = '中国留学生 AI 岗位求职保姆级攻略'
DESCRIPTION = '按真实职责判断 AI 岗位，补足能力证据，完成有针对性的申请与技术面试准备。免费中文攻略、可运行项目、模板与 PDF。'
ROUTES = {'R1':'算法与机器学习','R2':'AI 工程','R3':'AI 应用工程','X':'交叉岗位'}
SECTIONS = {'docs':'完整攻略','research':'岗位与来源','templates':'可编辑模板','examples':'技术项目','README.md':'项目说明'}
PAGES: dict[str, dict] = {}
REPO_URL = ''
SITE_URL = 'https://aipmandy.github.io/chinese-international-student-ai-jobs/'


def h(value):
    return html.escape(str(value), quote=True)


def read_json(path, fallback=None):
    p = ROOT / path
    if not p.exists():
        return fallback if fallback is not None else {}
    return json.loads(p.read_text(encoding='utf-8'))


def slug(value):
    value = re.sub(r'<[^>]+>', '', value).strip().lower()
    value = re.sub(r'[^\w\u4e00-\u9fff\- ]+', '', value)
    return re.sub(r'\s+', '-', value) or 'section'


def prefix_for(url):
    return '../' * (len(Path(url).parts)-1)


def text_title(text, fallback):
    first = re.search(r'^#\s+(.+)$', text, re.M)
    return re.sub(r'[*`]', '', first.group(1)) if first else fallback


def replace_markdown_links(text, replace):
    """Replace inline links/images while retaining balanced URL parentheses."""
    pieces = []
    cursor = 0
    for match in re.finditer(r'(!?)\[([^\]\n]*)\]\(', text):
        if match.start() < cursor:
            continue
        pos = match.end()
        start = pos
        depth = 0
        while pos < len(text):
            char = text[pos]
            if char == '\\' and pos + 1 < len(text):
                pos += 2
                continue
            if char == '(':
                depth += 1
            elif char == ')':
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace():
                break
            pos += 1
        if depth or pos == start:
            continue
        target = text[start:pos]
        while pos < len(text) and text[pos].isspace():
            pos += 1
        # Preserve support for optional quoted link titles.
        if pos < len(text) and text[pos] in ('"', "'"):
            quote = text[pos]
            pos += 1
            while pos < len(text) and text[pos] != quote:
                pos += 2 if text[pos] == '\\' and pos + 1 < len(text) else 1
            if pos == len(text):
                continue
            pos += 1
            while pos < len(text) and text[pos].isspace():
                pos += 1
        if pos >= len(text) or text[pos] != ')':
            continue
        target = re.sub(r'\\([\\()])', r'\1', target)
        pieces.append(text[cursor:match.start()])
        pieces.append(replace(match.group(2), target, bool(match.group(1))))
        cursor = pos + 1
    pieces.append(text[cursor:])
    return ''.join(pieces)


def markdown_to_plain(text):
    """Readable text for cards and search, without Markdown link destinations."""
    text = re.sub(r'^\s{0,3}\[[^\]]+\]:\s+.*$', '', text, flags=re.M)
    text = replace_markdown_links(text, lambda label, target, is_image: label)
    text = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', text)
    text = re.sub(r'^\s*(?:```|~~~)[^\n]*$', '', text, flags=re.M)
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.M)
    text = re.sub(r'^\s*>\s?', '', text, flags=re.M)
    text = re.sub(r'[`*~\[\]|]', ' ', text)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def complete_preview(text, limit=140):
    """Prefer complete prose; only shorten an oversized first sentence as a fallback."""
    prose = re.sub(r'(?ms)^\s*(```|~~~).*?^\s*\1\s*$', '', text)
    paragraphs = []
    for block in re.split(r'\n\s*\n', prose):
        block = block.strip()
        if not block or re.match(r'^(?:#|\||>|[-+*]\s|\d+[.)]\s|作者[：:]|版本[：与]|核验[：日])', block):
            continue
        plain = markdown_to_plain(block)
        if plain:
            paragraphs.append(plain)
    if not paragraphs:
        return '打开完整内容，按步骤完成当前任务。'
    paragraph = paragraphs[0]
    if len(paragraph) <= limit:
        return paragraph
    # Chinese stops and English sentence endings, while preserving decimal points.
    sentences = re.findall(r'.+?(?:[。！？]|[.!?](?=\s|$)|$)', paragraph)
    selected = ''
    for sentence in sentences:
        candidate = (selected + sentence).strip()
        if len(candidate) > limit:
            break
        selected = candidate
    if selected:
        return selected
    # A paragraph without a short complete sentence may end at a clause boundary.
    clause = paragraph[:limit]
    boundaries = list(re.finditer(r'[，；,;]\s*', clause))
    if boundaries and boundaries[-1].start() >= limit // 2:
        return clause[:boundaries[-1].start()].rstrip() + '…'
    # Never split an English word, technical identifier, or file path in half.
    word = re.compile(r'[A-Za-z0-9_./:+#%=-]')
    end = limit
    if word.fullmatch(paragraph[end-1]) and word.fullmatch(paragraph[end]):
        while end > 0 and word.fullmatch(paragraph[end-1]):
            end -= 1
        if end == 0:
            end = limit
            while end < len(paragraph) and word.fullmatch(paragraph[end]):
                end += 1
    return paragraph[:end].rstrip() + '…'


def section_of(source):
    return SECTIONS.get(source.split('/')[0], '项目资料')


def local_target(source, target):
    """Resolve a relative markdown link without escaping the repository."""
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith('#'):
        return None
    path = unquote(parsed.path)
    joined = os.path.normpath(str(Path(source).parent / path)).replace('\\', '/')
    if joined.startswith('../') or joined.startswith('/'):
        return None
    return joined


def href(source, target, page_url):
    parsed = urlsplit(target)
    if parsed.scheme in ('https', 'http', 'mailto'):
        return target, True
    if target.startswith('#'):
        return '#' + slug(unquote(target[1:])), False
    if parsed.scheme:
        return '#', False
    resolved = local_target(source, target)
    if resolved is None:
        return target, False
    if resolved in PAGES:
        final = PAGES[resolved]['url']
    elif resolved in ('', '.'):
        final = 'index.html'
    elif resolved == 'pdf/chinese-international-student-ai-jobs-guide.pdf':
        final = 'downloads/chinese-international-student-ai-jobs-guide.pdf'
    elif resolved == 'dist':
        final = 'index.html'
    elif resolved.startswith('dist/'):
        final = resolved[5:]
    elif (ROOT/resolved).is_dir():
        readme = resolved.rstrip('/')+'/README.md'
        final = PAGES.get(readme, {}).get('url', 'guide.html')
    else:
        final = 'source/'+resolved
    if parsed.fragment:
        final += '#' + slug(unquote(parsed.fragment))
    if parsed.query:
        final += '?' + parsed.query
    return prefix_for(page_url)+final, False


def inline(text, source, page_url):
    tokens=[]
    def save(value):
        tokens.append(value)
        return '\x00'+str(len(tokens)-1)+'\x00'
    text = re.sub(r'`([^`\n]+)`', lambda m: save('<code>'+h(m.group(1))+'</code>'), text)
    def link_or_image(label, target, is_image):
        path,external = href(source,target,page_url)
        if is_image:
            return save('<img src="'+h(path)+'" alt="'+h(label)+'" loading="lazy">')
        extra = ' target="_blank" rel="noopener noreferrer"' if external else ''
        label = re.sub(r'[*`]', '', label)
        return save('<a href="'+h(path)+'"'+extra+'>'+h(label)+'</a>')
    text = replace_markdown_links(text, link_or_image)
    text = re.sub(r'<(https?://[^>]+)>', lambda m: save('<a href="'+h(m.group(1))+'" target="_blank" rel="noopener noreferrer">'+h(m.group(1))+'</a>'), text)
    text = re.sub(r'(?<![\w"=])(https?://[^\s<>\x00]+)', lambda m: save('<a href="'+h(m.group(1).rstrip('。；，'))+'" target="_blank" rel="noopener noreferrer">'+h(m.group(1).rstrip('。；，'))+'</a>'+h(m.group(1)[len(m.group(1).rstrip('。；，')):])), text)
    text = h(text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', text)
    for _ in range(len(tokens)+1):
        if '\x00' not in text: break
        text = re.sub('\x00(\\d+)\x00', lambda m:tokens[int(m.group(1))], text)
    return text


def render_md(text, source, page_url):
    lines = text.splitlines(); result=[]; headings=[]; used={}; i=0
    list_pattern=re.compile(r'^(\s*)([-+*]|\d+[.)])\s+(.+)$')
    def table_cells(line):
        return [v.strip().replace('\\|','|') for v in re.split(r'(?<!\\)\|',line.strip().strip('|'))]
    def blockstart(line):
        return bool(re.match(r'^\s*(?:#{1,6}\s|```|~~~|>|[-+*]\s|\d+[.)]\s|---+$|\*\*\*+$)',line))
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        fence=re.match(r'^\s*(```|~~~)([^\s]*)',line)
        if fence:
            marker,lang=fence.group(1),fence.group(2);code=[];i+=1
            while i<len(lines) and not lines[i].lstrip().startswith(marker):code.append(lines[i]);i+=1
            i+=1
            result.append('<pre><span class="code-label">'+h(lang or 'command / text')+'</span><code>'+h('\n'.join(code))+'</code></pre>');continue
        header=re.match(r'^(#{1,6})\s+(.+)$',line)
        if header:
            level=len(header.group(1));label=header.group(2).strip();ident=slug(label);used[ident]=used.get(ident,0)+1
            if used[ident]>1:ident+='-'+str(used[ident])
            result.append(f'<h{level} id="{h(ident)}">{inline(label,source,page_url)}</h{level}>')
            if level in (2,3):headings.append((level,label,ident))
            i+=1;continue
        if re.fullmatch(r'\s*(?:---+|\*\*\*+|___+)\s*',line):result.append('<hr>');i+=1;continue
        if i+1<len(lines) and '|' in line and re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*',lines[i+1]):
            headers=table_cells(line);i+=2;body=[]
            while i<len(lines) and '|' in lines[i] and lines[i].strip():
                cells=table_cells(lines[i]);cells+=['']*max(0,len(headers)-len(cells));body.append('<tr>'+''.join('<td>'+inline(v,source,page_url)+'</td>' for v in cells[:len(headers)])+'</tr>');i+=1
            result.append('<div class="table-wrap" tabindex="0" role="region" aria-label="可横向滚动的表格"><table><thead><tr>'+''.join('<th scope="col">'+inline(v,source,page_url)+'</th>' for v in headers)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>');continue
        if line.lstrip().startswith('>'):
            quote=[]
            while i<len(lines) and lines[i].lstrip().startswith('>'):quote.append(re.sub(r'^\s*>\s?','',lines[i]));i+=1
            inner,_=render_md('\n'.join(quote),source,page_url);result.append('<blockquote>'+inner+'</blockquote>');continue
        if list_pattern.match(line):
            stack=[];chunk=[]
            while i<len(lines):
                m=list_pattern.match(lines[i])
                if not m:break
                indent=len(m.group(1).replace('\t','    '));typ='ol' if m.group(2)[0].isdigit() else 'ul';content=m.group(3)
                while stack and indent<stack[-1][0]:chunk.append('</li></'+stack.pop()[1]+'>')
                if not stack:chunk.append('<'+typ+'>');stack.append((indent,typ));chunk.append('<li>')
                elif indent>stack[-1][0]:chunk.append('<'+typ+'>');stack.append((indent,typ));chunk.append('<li>')
                elif typ!=stack[-1][1]:chunk.append('</li></'+stack.pop()[1]+'><'+typ+'>');stack.append((indent,typ));chunk.append('<li>')
                else:chunk.append('</li><li>')
                task=re.match(r'^\[([ xX])\]\s*(.*)$',content)
                if task:chunk.append('<input type="checkbox" disabled'+(' checked' if task.group(1).lower()=='x' else '')+' aria-label="检查项"> '+inline(task.group(2),source,page_url))
                else:chunk.append(inline(content,source,page_url))
                i+=1
            while stack:chunk.append('</li></'+stack.pop()[1]+'>')
            result.append(''.join(chunk));continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not blockstart(lines[i]):
            if i+1<len(lines) and '|' in lines[i] and re.match(r'^\s*\|?\s*:?-{3,}',lines[i+1]):break
            paragraph.append(lines[i]);i+=1
        result.append('<p>'+inline(' '.join(x.strip() for x in paragraph),source,page_url)+'</p>')
    return '\n'.join(result),headings


def layout(page_url, title, body, active='', search=False):
    p=prefix_for(page_url)
    links=[('guide.html','阅读攻略','guide'),('jobs.html','岗位库','jobs'),('regions.html','地区资格','regions'),('projects.html','项目实测','projects'),('downloads.html','资料下载','downloads')]
    nav=''.join('<a'+(' class="active" aria-current="page"' if active==k else '')+' href="'+p+u+'">'+t+'</a>' for u,t,k in links)
    repo='<a href="'+h(REPO_URL)+'" target="_blank" rel="noopener noreferrer">GitHub 开源仓库</a>' if REPO_URL else '<span class="publication">GitHub 仓库：待发布</span>'
    script='<script src="'+p+'data/search-index.js" defer></script>' if search else ''
    # Declare only facts visible on the generated page; avoid unsupported outcome claims.
    page_location = SITE_URL if page_url == 'index.html' else SITE_URL + page_url
    page_title = title + ' · AI酋长Andy'
    schema = {
        '@context': 'https://schema.org', '@type': 'WebPage',
        'name': title, 'description': DESCRIPTION, 'url': page_location,
        'inLanguage': 'zh-CN', 'dateModified': DATE,
        'isPartOf': {'@type': 'WebSite', 'name': TITLE, 'url': SITE_URL},
        'author': {
            '@type': 'Person',
            'name': 'AI酋长Andy',
            'affiliation': {'@type': 'Organization', 'name': '星觉科技'},
            'address': {'@type': 'PostalAddress', 'addressLocality': '北京'},
        },
        'publisher': {'@type': 'Organization', 'name': '星觉科技', 'url': 'https://www.a6no1.cn/'}
    }
    jsonld = json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c')
    image = 'https://aipmandy.github.io/chinese-international-student-ai-jobs/assets/social-preview.png'
    metadata = (
        f'<link rel="canonical" href="{h(page_location)}">'
        f'<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{h(TITLE)}">'
        f'<meta property="og:locale" content="zh_CN">'
        f'<meta property="og:title" content="{h(page_title)}">'
        f'<meta property="og:description" content="{h(DESCRIPTION)}">'
        f'<meta property="og:url" content="{h(page_location)}">'
        f'<meta property="og:image" content="{image}">'
        f'<meta property="og:image:width" content="1280">'
        f'<meta property="og:image:height" content="640">'
        f'<meta name="twitter:card" content="summary_large_image">'
        f'<script type="application/ld+json">{jsonld}</script>'
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{h(DESCRIPTION)}"><meta name="theme-color" content="#152725"><title>{h(title)} · AI酋长Andy</title>{metadata}<link rel="icon" href="{p}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{p}assets/style.css">{script}<script src="{p}assets/app.js" defer></script></head>
<body data-base="{p}"><a class="skip-link" href="#main">跳到正文</a><header class="topbar"><div class="wrap nav-inner"><a class="brand" href="{p}index.html" aria-label="AI 岗位求职攻略首页"><span class="brand-mark" aria-hidden="true">A</span><span class="brand-title">AI 岗位求职指南<small>AI酋长Andy · OPEN GUIDE</small></span></a><button id="menu-toggle" class="menu-toggle" aria-controls="nav-links" aria-expanded="false">目录</button><nav class="nav-links" id="nav-links" aria-label="主导航">{nav}<a class="nav-start" href="{p}self-check.html">岗位自查</a></nav></div></header>
<main id="main">{body}</main>
<footer class="footer"><div class="wrap footer-grid"><div><strong>把岗位要求，变成可以验证的证据。</strong><p>作者：AI酋长Andy · 星觉科技 · 北京 · 微信号：AIPMAndy</p><div class="footer-links"><a href="https://metaver.vip/" target="_blank" rel="noopener noreferrer">个人官网 metaver.vip</a><a href="https://www.a6no1.cn/" target="_blank" rel="noopener noreferrer">公司官网 a6no1.cn</a><a href="https://metaver.vip/services" target="_blank" rel="noopener noreferrer">咨询与陪跑</a><a href="https://aipmandy.github.io/chinese-international-student-career-guide/">留学生求职总攻略</a><a href="https://aipmandy.github.io/chinese-international-student-product-jobs/">产品岗位攻略</a><a href="https://aipmandy.github.io/chinese-international-student-business-jobs/">商科岗位攻略</a>{repo}</div></div><div class="footer-right"><p>版本 1.0.0 · 资料核验 {DATE}<br>免费内容完整开放 · 教学模拟明确标注<br>独立阅读，无账号、无数据上传、无访问统计。</p><div class="footer-links" style="justify-content:inherit"><a href="{p}search.html">搜索全文</a><a href="{p}read/research-coverage-gaps.html">待补信息与核验边界</a></div></div></div></footer></body></html>'''


def save(url, title, body, active='', search=False):
    dest=OUT/url;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(layout(url,title,body,active,search),encoding='utf-8')


def page_head(kicker,title,description):
    return '<div class="page-head"><p class="eyebrow">'+h(kicker)+'</p><h1>'+h(title)+'</h1><p>'+h(description)+'</p></div>'


def consult():
    return '<section class="section"><div class="consult"><div><p class="eyebrow">可选的一对一支持</p><h2>卡在岗位判断、项目诊断或面试准备？</h2><p>先使用完整免费的攻略、代码和模板。需要进一步诊断，可说明目标地区、毕业时间、技术基础与具体卡点。咨询和求职陪跑不承诺录用。</p></div><div class="contact-box"><span>微信 · 备注“留学生 AI 岗位”</span><b>AIPMAndy</b><button class="copy-button" data-copy="AIPMAndy">复制微信号</button></div></div></section>'


def doc_url(source, fallback='guide.html'):
    return PAGES.get(source,{}).get('url',fallback)


def build_home(jd, policy, summary):
    jobs=jd.get('jobs',[]);regions=policy.get('regions',[]);full=sum(j.get('source_status')=='official_detail_readable' for j in jobs);partial=len(jobs)-full
    projects=sum(bool(read_json(p)) for p in ['examples/01_ml_experiment/reports/evaluation.json','examples/02_model_service/reports/verification.json','examples/03_grounded_retrieval/reports/evaluation.json'])
    hero=f'''<div class="wrap"><section class="hero"><div class="hero-grid"><div><p class="eyebrow">CHINESE INTERNATIONAL STUDENTS · AI CAREER GUIDE</p><h1>中国留学生<br><em>AI 岗位求职</em><br>保姆级攻略</h1><p class="hero-deck">从真实岗位出发，找到适合你的技术路线。<br>补足能力证据，做出可验证的项目，准备经得起追问的面试回答。</p><div class="actions"><a class="button" href="{doc_url('docs/00-start.md')}">从 90 分钟行动开始 <span aria-hidden="true">↗</span></a><a class="button secondary" href="downloads.html">下载完整资料</a></div><p class="hero-foot">作者 AI酋长Andy · 星觉科技 · 北京 · 版本 1.0.0 · 核验 {DATE}<br>申请 AI 技术岗位的完整路径；本册可独立使用。</p></div><aside class="route-sheet" aria-label="从岗位到证据的四步路径"><p class="sheet-label">YOUR EVIDENCE PATH</p><h2>每一步，都有交付物。</h2><div class="sheet-step"><span>01</span><div><strong>判断岗位与资格</strong><p>职责、毕业窗口、地点、工作权</p></div></div><div class="sheet-step"><span>02</span><div><strong>定位能力差距</strong><p>编程、数学、研究与工程证据</p></div></div><div class="sheet-step"><span>03</span><div><strong>完成可复现项目</strong><p>数据、基线、评测、失败与限制</p></div></div><div class="sheet-step"><span>04</span><div><strong>定向申请与面试</strong><p>简历、项目追问、投递复盘</p></div></div><div class="sheet-note">免费内容完整开放 · 不需要先加微信</div></aside></div></section><section class="stats" aria-label="本版资料覆盖"><div class="stat"><div class="stat-value">3</div><div class="stat-label">技术主路线</div><div class="stat-detail">研究/建模 · 工程 · 应用</div></div><div class="stat"><div class="stat-value">{len(jobs)}</div><div class="stat-label">真实雇主 JD 研究记录</div><div class="stat-detail">{full} 条详情可读 · {partial} 条待复核</div></div><div class="stat"><div class="stat-value">{len(regions)}</div><div class="stat-label">代表性地区资格记录</div><div class="stat-detail">保留访问限制与官方冲突</div></div><div class="stat"><div class="stat-value">{projects}</div><div class="stat-label">本地可运行技术样例</div><div class="stat-detail">{'已有实测报告' if summary else '运行状态以报告为准'} · 明确教学边界</div></div></section>'''
    routes=[('R1','算法与机器学习','RESEARCH / APPLIED ML','从数据和实验回答问题。研究岗位还要证明新的问题、方法与个人贡献。','数据划分、基线、消融、误差分析','ml'),('R2','AI 工程','ML SYSTEMS / ENGINEERING','把模型交给其他系统使用。接口、资源、可靠性和观测都需要证据。','输入校验、模型版本、延迟、回滚','service'),('R3','AI 应用工程','APPLIED AI SOFTWARE','把检索或模型能力接入具体任务。评测、引用、拒答和权限一起验收。','任务评测、证据引用、失败与回退','retrieval')]
    route_html=''.join(f'<article class="route-card"><div class="route-no">{code} / 技术路线</div><h3>{name}</h3><p class="subtitle">{en}</p><p>{desc}</p><div class="evidence"><strong>你要拿出的证据</strong><br>{ev}</div><a href="projects.html#{anchor}">查看对应教学项目 →</a></article>' for code,name,en,desc,ev,anchor in routes)
    body=hero+f'''<section class="section"><div class="section-heading"><div><h2>先选一条主线，再补关键证据。</h2><p>按实际职责分流。岗位标题不能代替对 JD 的逐条判断。</p></div><a href="{doc_url('docs/01-role-map.md')}">阅读完整岗位路线图 →</a></div><div class="grid-3">{route_html}</div></section><section class="section split-section"><div><p class="eyebrow">FIRST 90 MINUTES</p><h2>今天就能开始。<br>先交出第一份判断。</h2><p>不同学历、专业和技术基础，都从约束与证据开始。先把“可投”“先确认”和“先补能力”分开。</p><a class="button secondary" href="self-check.html">做一次岗位自查</a></div><ol class="step-list"><li><div><strong>写下你的真实约束</strong><p>毕业日期、入职时间、目标地点、当前工作资格。</p></div></li><li><div><strong>对照两条具体 JD</strong><p>分清必需条件与加分项，保留原始链接和核验日期。</p></div></li><li><div><strong>把要求对应到证据</strong><p>课程、研究、实习、开源贡献和项目，分别写清个人职责。</p></div></li><li><div><strong>运行一个样例，解释一个失败</strong><p>从输入到输出走一遍。成功运行只是开始，解释与改进才形成你的证据。</p></div></li></ol></section><section class="section"><div class="notice"><strong>地区覆盖与来源边界</strong><p>本版有 {len(regions)} 个代表性地区资格记录，覆盖北美、欧洲、亚洲、大洋洲和回国求职。非洲、南美洲不纳入。并未穷尽其余全部国家。岗位网页可读不等于仍在招，也不等于接受你的工作资格。</p><a href="regions.html">查看访问限制、日期冲突与待确认事项 →</a></div></section>{consult()}</div>'''
    save('index.html',TITLE,body)


def build_guide():
    docs=[(s,p) for s,p in PAGES.items() if s.startswith('docs/')]
    cards=''.join('<a class="index-item" href="'+p['url']+'"><span class="read-status" data-read-status="'+h(s)+'"></span><h2>'+h(p['title'])+'</h2><p>'+h(p['preview'])+'</p></a>' for s,p in docs)
    body='<div class="wrap">'+page_head('THE COMPLETE GUIDE','完整中文攻略','从岗位判断到项目证据，再到技术面试与申请复盘。按章节读，也可以直接进入当前卡点。')+'<div class="actions" style="margin-bottom:28px"><a class="button secondary" href="search.html">搜索全部内容</a><a class="text-link" href="downloads.html">离线阅读与模板下载 →</a></div><section class="section content-index">'+cards+'</section>'+consult()+'</div>'
    save('guide.html','完整攻略',body,'guide')


def build_read_pages():
    sources=list(PAGES)
    chapters=[s for s in sources if s.startswith('docs/')]
    for source,page in PAGES.items():
        p=prefix_for(page['url']);side='<a class="nav-search" href="'+p+'search.html">搜索全部攻略与模板</a>';mobile=''
        for group,label in [('docs','攻略章节'),('examples','技术项目'),('templates','模板'),('research','原始研究与来源')]:
            entries=[(s,pg) for s,pg in PAGES.items() if s.startswith(group+'/')]
            if not entries:continue
            side+='<h2>'+label+'</h2>'
            mobile+='<strong>'+label+'</strong>'
            for s,pg in entries:
                a='<a href="'+p+pg['url']+'"'+(' class="current" aria-current="page"' if s==source else '')+'>'+h(pg['title'])+'</a>'
                side+=a;mobile+=a
        prose,headings=render_md(page['text'],source,page['url'])
        toc='<details class="toc-panel"><summary>本页目录 · '+str(len(headings))+' 节</summary><ul>'+''.join('<li'+(' style="margin-left:12px"' if level==3 else '')+'><a href="#'+h(ident)+'">'+h(label)+'</a></li>' for level,label,ident in headings)+'</ul></details>' if headings else ''
        nextprev=''
        if source in chapters:
            at=chapters.index(source);prev=PAGES[chapters[at-1]] if at else None;nex=PAGES[chapters[at+1]] if at+1<len(chapters) else None
            nextprev='<nav class="chapter-nav" aria-label="章节翻页">'+('<a href="'+p+prev['url']+'">← '+h(prev['title'])+'</a>' if prev else '<a href="'+p+'guide.html">← 章节目录</a>')+('<a href="'+p+nex['url']+'">'+h(nex['title'])+' →</a>' if nex else '<a href="'+p+'downloads.html">下载全部资料 →</a>')+'</nav>'
        body='<div class="wrap read-layout"><aside class="sidebar" aria-label="阅读目录">'+side+'</aside><div class="read-main"><details class="mobile-chapters"><summary>打开章节导航</summary>'+mobile+'</details><div class="read-topline"><span>'+h(page['section'])+' · 资料核验 '+DATE+'</span><button id="mark-read" data-chapter="'+h(source)+'" aria-pressed="false">标记已读</button></div>'+toc+'<article class="prose">'+prose+'</article><p class="source-path">原始文档：<a href="'+p+'source/'+h(source)+'">'+h(source)+'</a></p>'+nextprev+'</div></div>'
        save(page['url'],page['title'],body,'guide')


def build_jobs(data):
    jobs=data.get('jobs',[]);countries=sorted(set(j.get('country_region','') for j in jobs));full=sum(j.get('source_status')=='official_detail_readable' for j in jobs)
    controls='<div class="toolbar"><div class="field grow"><label for="filter-query">岗位、公司或技能</label><input id="filter-query" type="search" placeholder="如 Python、research、毕业"></div><div class="field"><label for="filter-region">国家 / 地区</label><select id="filter-region"><option value="">全部地区</option>'+''.join('<option>'+h(c)+'</option>' for c in countries)+'</select></div><div class="field"><label for="filter-route">技术路线</label><select id="filter-route"><option value="">全部路线</option>'+''.join('<option value="'+k+'">'+v+'</option>' for k,v in ROUTES.items())+'</select></div><label class="checkbox-field"><input id="filter-verified" type="checkbox">仅官方详情可读</label></div><p id="filter-count" class="result-count" aria-live="polite"></p>'
    cards=[]
    for j in jobs:
        verified=j.get('source_status')=='official_detail_readable';route=j.get('route','X');country=j.get('country_region','');search=' '.join(str(j.get(k,'')) for k in ['title','employer','skills','tasks','work_authorization','degree','location'])
        card=f'<article class="job-card" data-region="{h(country)}" data-route="{h(route)}" data-verified="{"yes" if verified else "no"}" data-search="{h(search)}"><div class="card-meta"><span>{h(j.get("id"))} · {h(country)}</span><span class="tag {"" if verified else "warn"}">{"官方详情可读" if verified else "官方索引 · 待复核"}</span></div><h2>{h(j.get("title"))}</h2><p class="job-company">{h(j.get("employer"))} · {h(j.get("seniority"))}</p><span class="tag dark">{h(ROUTES.get(route,route))}</span><dl><dt>主要工作</dt><dd>'+h('；'.join(j.get('tasks',[])))+'</dd><dt>必需 / 重点能力</dt><dd>'+h('；'.join(j.get('skills',[])))+'</dd><dt>学历与毕业窗口</dt><dd>'+h(j.get('degree','未说明'))+'<br>'+h(j.get('graduation_window','未说明'))+'</dd><dt>地点</dt><dd>'+h(j.get('location','未说明'))+'</dd></dl><div class="eligibility"><strong>工作资格与支持：必须独立判断</strong>'+h(j.get('work_authorization','未说明'))+'<br>'+h(j.get('sponsorship','未说明'))+'</div><details class="details"><summary>路线判断、项目证据与未决事项</summary><p><strong>为何分到这条路线：</strong>'+h(j.get('route_reason',''))+'</p><p><strong>可以准备的证据：</strong>'+h(j.get('evidence_to_build',''))+'</p><p><strong>申请截止：</strong>'+h(j.get('application_deadline','未说明'))+'</p><p><strong>页面状态：</strong>'+h(j.get('availability','未确认'))+'</p><p>'+h('；'.join(j.get('uncertainties',[])))+'</p></details><div class="job-links"><a href="'+h(j.get('source_url',''))+'" target="_blank" rel="noopener noreferrer">打开雇主原文 ↗</a><span>核验 '+h(j.get('checked_at',DATE))+'</span></div></article>'
        cards.append(card)
    body='<div class="wrap">'+page_head('EMPLOYER REQUIREMENTS','从真实 JD，看清岗位要求。',f'{len(jobs)} 条教学用岗位研究记录；{full} 条官方详情可读、{len(jobs)-full} 条仅索引可读。按职责分路线，保留学历、毕业时间、地点与身份限制。')+'<div class="notice" style="margin-bottom:25px"><strong>这是一份岗位研究表。</strong><p>网页可读不等于仍在招。没有写明的条件保持“未说明”；资格支持按每条职位确认。研究分类是本项目的教学分析，不是雇主承诺。</p></div>'+controls+'<section class="section job-grid">'+''.join(cards)+'</section><div id="filter-empty" class="empty-state" hidden>没有匹配的记录。可放宽地区或路线筛选，再回到原始 JD 核查。</div><p class="small-muted">完整数据：<a href="source/research/employer-jds.json">JSON 原表</a> · <a href="'+doc_url('research/jd-source-notes.md')+'">核验方法与缺口</a></p>'+consult()+'</div>'
    save('jobs.html','真实雇主岗位库',body,'jobs')


def build_regions(data):
    rows=data.get('regions',[]);groups=sorted(set(r['continent'] for r in rows));controls='<div class="toolbar"><div class="field grow"><label for="filter-query">地区、路径或条件</label><input type="search" id="filter-query" placeholder="如英国、毕业、申请日期"></div><div class="field"><label for="filter-region">区域</label><select id="filter-region"><option value="">全部区域</option>'+''.join('<option>'+h(x)+'</option>' for x in groups)+'</select></div><label class="checkbox-field"><input id="filter-verified" type="checkbox">仅需重点复核的记录</label></div><p id="filter-count" class="result-count" aria-live="polite"></p>'
    cards=[]
    for r in rows:
        status=r['verification_status'];attention=status!='官方正文可读';sources=''.join('<li><a href="'+h(s['url'])+'" target="_blank" rel="noopener noreferrer">'+h(s['title'])+' ↗</a><small>'+h(s['access'])+'</small></li>' for s in r['sources'])
        cards.append('<article class="region-card" data-region="'+h(r['continent'])+'" data-verified="'+('yes' if attention else 'no')+'" data-search="'+h(' '.join([r['region'],r['graduate_route'],r['verified_summary'],r['uncertainty']]))+'"><div class="card-meta"><span>'+h(r['continent'])+' · '+h(r['checked_at'])+'</span><span class="tag '+('warn' if attention else '')+'">'+('重点复核' if attention else '官方正文可读')+'</span></div><h2>'+h(r['region'])+'</h2><p class="region-route">'+h(r['graduate_route'])+'</p><p>'+h(r['verified_summary'])+'</p><p><strong>申请时钟：</strong>'+h(r['application_clock'])+'</p><details class="details"><summary>逐岗位确认事项与官方来源</summary><ul>'+''.join('<li>'+h(v)+'</li>' for v in r['employer_checks'])+'</ul><ul class="source-links">'+sources+'</ul></details><p class="uncertainty"><strong>'+h(status)+'。</strong><br>'+h(r['uncertainty'])+'</p></article>')
    body='<div class="wrap">'+page_head('REGIONAL ELIGIBILITY','工作资格、毕业时间、岗位地点，分别查。',f'{len(rows)} 个代表性地区的调查记录。以现行官方来源为起点，保留访问受限、未来调整和原文冲突；不替代对个人条件的核定。')+'<div class="notice" style="margin-bottom:25px"><strong>两处官方口径冲突仍待确认。</strong><p>新西兰新增 PSWV 路径生效日出现 11 月 16 日 / 23 日；韩国 D-10 新旧页面期限不同。详见对应记录。日本、澳大利亚及美国部分具体页面访问受限。</p><a href="'+doc_url('research/coverage-gaps.md')+'">完整覆盖边界与更新清单 →</a></div>'+controls+'<section class="section region-grid">'+''.join(cards)+'</section><div id="filter-empty" class="empty-state" hidden>没有匹配记录。其他目标地请先完成官方规则与具体 JD 的双重核验。</div><p class="small-muted">原始记录：<a href="source/research/regional-rules.json">地区 JSON</a> · <a href="'+doc_url('research/regional-rules.md')+'">阅读核查步骤与英文询问信</a></p>'+consult()+'</div>'
    save('regions.html','地区资格核验',body,'regions')


def pct(value):
    return f'{float(value)*100:.1f}%'


def metric(value,label,warning=False):
    return '<div class="metric-box'+(' warning' if warning else '')+'"><span class="number">'+h(value)+'</span><span class="label">'+h(label)+'</span></div>'


def bar(label,value,alt=False):
    v=max(0,min(1,float(value)))
    return '<div class="bar-row"><span>'+h(label)+'</span><div class="bar-track"><div class="bar-fill'+(' alt' if alt else '')+'" style="width:'+f'{v*100:.4f}'+'%"></div></div><span class="bar-number">'+pct(v)+'</span></div>'


def report_links(folder, files):
    read=doc_url(folder+'/README.md','guide.html')
    return '<div class="raw-links"><a href="'+read+'">完整运行说明 →</a>'+''.join('<a href="source/'+folder+'/reports/'+f+'">'+h(label)+'</a>' for f,label in files)+'</div>'


def build_projects(summary):
    ml=read_json('examples/01_ml_experiment/reports/evaluation.json');service=read_json('examples/02_model_service/reports/verification.json');retrieval=read_json('examples/03_grounded_retrieval/reports/evaluation.json');body='<div class="wrap">'+page_head('RUNNABLE EVIDENCE','让结果可复现，也让失败可解释。','以下图表直接读取仓库中实际运行生成的报告。样例使用合成教学数据，不包含客户记录，不宣称真实业务收益。')+'<div class="notice" style="margin-bottom:28px"><strong>先看测量范围。</strong><p>模型质量、接口行为和检索结果分别验证。本机小样本结果不代表生产能力、线上效果或录用竞争力。检索样例是无大模型的基线，不能称为完整 RAG 系统。</p></div>'
    if summary:body+='<div class="pill-row"><span class="tag">'+h(summary.get('unit_tests','未记录'))+' 项单元检查</span><span class="tag">'+h(summary.get('real_http_checks','未记录'))+' 项真实 HTTP 检查</span><span class="tag">确定性验收 '+h(summary.get('deterministic_acceptance','未记录'))+'</span><span class="tag">Python '+h(summary.get('python','未记录'))+'</span></div>'
    if ml:
        test=ml['test'];matrix=test['confusion_gold_rows_predicted_columns'];labels=list(matrix);table='<table class="matrix"><thead><tr><th>真实 ↓ / 预测 →</th>'+''.join('<th>'+h(x)+'</th>' for x in labels)+'</tr></thead><tbody>'
        for real in labels:
            table+='<tr><th scope="row">'+h(real)+'</th>'
            for pred in labels:
                val=matrix[real][pred];alpha=.04+.45*(val/max(1,max(matrix[real].values())));table+='<td style="background:rgba(30,101,87,'+str(round(alpha,2))+');color:'+('#fff' if alpha>.38 else '#152725')+'">'+str(val)+'</td>'
            table+='</tr>'
        table+='</tbody></table>'
        failed=''.join('<p><code>'+h(f['id'])+'</code> · '+h(f['text'])+'<br>真实 '+h(f['gold'])+' / 预测 '+h(f['label'])+'</p>' for f in ml.get('failures',[]))
        body+='<section id="ml" class="project-section"><p class="eyebrow">01 / ALGORITHMS & MACHINE LEARNING</p><h2>工单分类：从基线到失败分析</h2><p>多项式朴素贝叶斯。训练、验证、测试固定分开；参数用验证集选择，测试集保留为最后评估。</p><div class="project-meta"><span class="tag">合成教学数据</span><span>训练 '+str(ml['split_sizes']['train'])+' · 验证 '+str(ml['split_sizes']['dev'])+' · 测试 '+str(test['n'])+'</span><span>实测 '+h(ml.get('run_at_utc',ml.get('checked_at','未记录')))+'</span></div><div class="metric-grid">'+metric(pct(test['macro_f1']),'测试 Macro F1 · '+str(test['n'])+' 条')+metric(pct(test['accuracy']),'测试准确率')+metric(str(len(ml.get('failures',[]))),'保留的测试失败案例',True)+'</div><div class="report-grid"><div><h3>同一测试集：模型与对照</h3>'+bar('选定模型',test['macro_f1'])+bar('多数类基线',ml['majority_baseline']['macro_f1'],True)+bar('移除全部特征',ml['ablation_remove_all_features']['macro_f1'],True)+'<p class="chart-note">指标为 Macro F1。数据规模很小；不能从这张图推断对真实工单的泛化效果。</p></div><div><h3>混淆矩阵 · 计数</h3>'+table+'<p class="chart-note">每行是真实类别，每列是预测类别。非对角项对应需要解释的错误。</p></div></div><div class="failure-box"><h3>失败没有被藏起来</h3>'+failed+'<p>“退款收据无法访问”与“发票页面卡住”暴露词面关联和真实意图的差异。模型输出没有做置信度校准。</p></div>'+report_links('examples/01_ml_experiment',[('evaluation.json','完整评测 JSON'),('failures.json','失败记录')])+'</section>'
    if service:
        checks=service['checks'];passed=sum(bool(x['passed']) for x in checks);bench=service['benchmark'];check_html=''.join('<li'+(' class="failed"' if not c['passed'] else '')+'>'+h(c['name'])+'<span>'+str(c['status'])+' · '+('PASS' if c['passed'] else 'FAIL')+'</span></li>' for c in checks)
        body+='<section id="service" class="project-section"><p class="eyebrow">02 / AI ENGINEERING</p><h2>模型服务：把正常和错误输入都说清楚</h2><p>本地 HTTP 服务加载版本化模型，检查请求格式与边界。每项状态码来自实际 HTTP 验证。</p><div class="project-meta"><span class="tag">本地 loopback</span><span>模型 '+h(service['model_id'])+'</span><span>'+h(service['system'])+' / '+h(service['machine'])+' · Python '+h(service['python'])+'</span></div><div class="metric-grid">'+metric(str(passed)+' / '+str(len(checks)),'真实 HTTP 检查通过')+metric(str(bench['p50_ms'])+' ms','p50 · '+str(bench['n'])+' 次顺序本机请求')+metric(str(bench['p95_ms'])+' ms','p95 · 包含本地客户端耗时')+'</div><ul class="check-grid">'+check_html+'</ul><div class="failure-box"><h3>不要把本机延迟写成生产性能</h3><p>测量包含预热 '+str(bench['warmup'])+' 次、单进程、loopback、短合成输入。此处不是容量测试或公网延迟测试。教学服务没有 TLS、认证、限流和有界线程池。</p></div>'+report_links('examples/02_model_service',[('verification.json','接口验证与延迟原始值')])+'</section>'
    if retrieval:
        t=retrieval['test'];fail=[r for r in t.get('records',[]) if not r.get('correct')];failed=''.join('<p><code>'+h(r['id'])+'</code> · '+h(r['question'])+'<br>结果：'+h(r['result']['status'])+' · '+h(r['result']['reason'])+'</p>' for r in fail)
        body+='<section id="retrieval" class="project-section"><p class="eyebrow">03 / AI APPLICATION ENGINEERING</p><h2>有出处的检索：命中、回答与拒答分开测</h2><p>BM25 检索与原文抽取。没有调用大模型；用固定模式阻断作为演示，不能证明可抵御未知提示注入。</p><div class="project-meta"><span class="tag">无 LLM 的离线基线</span><span>语料 '+str(retrieval['corpus_size'])+' 篇 · 验证 '+str(retrieval['dev_size'])+' 条 · 测试 '+str(t['n'])+' 条</span><span>阈值 '+str(retrieval['selected_threshold'])+' 由验证集选择</span></div><div class="metric-grid">'+metric(pct(t['task_accuracy']),'任务正确率 · '+str(t['n'])+' 条')+metric(pct(t['retrieval_recall_at_3']),'Recall@3 · '+str(t['answerable_n'])+' 条可回答问题')+metric(pct(t['unanswerable_refusal_rate']),'不可回答问题拒答率 · '+str(t['unanswerable_n'])+' 条',True)+'</div><div class="report-grid"><div><h3>不同阶段，分别验收</h3>'+bar('检索 Recall@3',t['retrieval_recall_at_3'])+bar('可答问题正确率',t['answerable_correct_rate'])+bar('不可答拒答率',t['unanswerable_refusal_rate'],True)+'<p class="chart-note">可回答问题 '+str(t['answerable_n'])+' 条，不可回答问题 '+str(t['unanswerable_n'])+' 条。检索命中不保证最后回答正确。</p></div><div><h3>边界样本的实测结果</h3><p class="small-muted">'+str(t['injection_n'])+' 条固定攻击样本的拒答率：<strong>'+pct(t['injection_refusal_rate'])+'</strong>。这个小集合不能证明对未知攻击安全。</p><p class="small-muted">已回答内容的原文完整性：<strong>'+pct(t['answered_quote_integrity'])+'</strong>。引用准确仍可能答非所问，不能用它替代任务正确率。</p><p class="small-muted">本轮保留 '+str(len(fail))+' 条失败，涵盖漏答和对无依据问题错误作答。</p></div></div><details class="failure-box"><summary>展开 '+str(len(fail))+' 条真实运行失败</summary>'+failed+'</details>'+report_links('examples/03_grounded_retrieval',[('evaluation.json','逐题评测 JSON'),('failures.json','失败记录')])+'</section>'
    if not any([ml,service,retrieval]):body+='<div class="empty-state">尚未发现实测报告。先运行 python3 examples/run_all.py，再重新构建网站。</div>'
    body+='<section class="section"><p class="small-muted">验收记录：<a href="source/examples/verification-summary.json">运行汇总 JSON</a> · <a href="'+doc_url('examples/README.md')+'">从环境准备到复现的完整步骤</a></p></section>'+consult()+'</div>'
    save('projects.html','技术项目实测报告',body,'projects')


def build_downloads():
    files=[('PDF','完整成品攻略','chinese-international-student-ai-jobs-guide.pdf','封面、路线图、技术案例、操作截图、检查表、页码与来源。'),('SOURCE ZIP','源码与完整正文','chinese-international-student-ai-jobs-source.zip','中文攻略、运行样例、网站源码、研究来源与验收材料，可在本地继续编辑。'),('TEMPLATES ZIP','可编辑求职模板','templates.zip','岗位研究、能力差距、学习行动、项目说明、评测记录、简历与面试自查。')]
    cards=[]
    for kind,title,name,desc in files:
        f=OUT/'downloads'/name
        ready = f.is_file() and f.stat().st_size > 0
        if ready and f.suffix == '.pdf':
            with f.open('rb') as stream: ready = stream.read(5) == b'%PDF-'
        elif ready and f.suffix == '.zip':
            ready = zipfile.is_zipfile(f)
        if ready:
            action='<a class="button" download href="downloads/'+name+'">下载 '+kind+' ↓</a>'
            # The source archive contains this page. Embedding its size/hash here
            # would make every repack invalidate the metadata shown to readers.
            meta='<a href="downloads/checksums.json">查看文件大小与完整 SHA-256 校验清单</a>'
        else:action='<span class="button disabled" aria-disabled="true">正在生成，暂不可下载</span>';meta='构建时未发现成品文件；正文与源码阅读不受影响。'
        cards.append('<article class="download-card"><span class="file-type">'+kind+'</span><h2>'+title+'</h2><p>'+desc+'</p>'+action+'<p class="file-meta">'+meta+'</p></article>')
    template_links=[]
    for f in sorted((ROOT/'templates').glob('*')) if (ROOT/'templates').exists() else []:
        if not f.is_file() or f.name.startswith('.') or f.name == 'README.md':continue
        source=str(f.relative_to(ROOT));title=PAGES[source]['title'] if source in PAGES else f.stem;url=PAGES[source]['url'] if source in PAGES else 'source/'+source
        template_links.append('<a class="template-link" href="'+url+'"><span>'+h(title)+'</span><small>'+h(f.suffix.upper().lstrip('.'))+' →</small></a>')
    body='<div class="wrap">'+page_head('TAKE THE TOOLKIT','完整资料，带走继续做。','全部免费开放，无需注册或添加微信。先选一条路线，再按模板填写自己的事实和证据。')+'<section class="section download-grid">'+''.join(cards)+'</section><section class="section"><div class="section-heading"><div><h2>单独阅读与编辑模板</h2><p>填写你的真实经历。教学模拟不能当作个人商业项目或工作业绩。</p></div></div><div class="template-grid">'+''.join(template_links)+'</div></section><section class="section"><div class="notice"><strong>使用与署名</strong><p>代码、内容及教学数据的许可分别见源码中的许可说明。复用开源材料时保留许可、来源和贡献边界，记录 AI 辅助部分。</p><a href="source/LICENSE-CODE">查看代码许可</a></div></section>'+consult()+'</div>'
    save('downloads.html','资料下载与模板',body,'downloads')


def build_selfcheck():
    def select(name,label,options,note=''):
        return '<div class="field"><label for="'+name+'">'+label+'</label><select id="'+name+'" name="'+name+'" required><option value="">请选择</option>'+''.join('<option value="'+v+'">'+t+'</option>' for v,t in options)+'</select>'+('<small>'+note+'</small>' if note else '')+'</div>'
    fields=select('eligibility','01 / 这条岗位的工作资格，核清了吗？',[('unknown','未确认，或毕业/地点/支持条件有未知项'),('confirmed','已对照具体 JD 与当前身份确认'),('blocked','已有明确不符合的硬条件')],'先选一条具体 JD。没有写明的条件不自动视为允许。')
    fields+=select('programming','02 / 你目前能独立完成多少编程工作？',[('none','还不能独立写完并调试一个程序'),('basic','能完成课程/教程，但独立项目仍需要帮助'),('independent','能独立编码、调试、测试并解释取舍')])
    fields+=select('math','03 / 概率、线性代数与模型评估基础如何？',[('low','需要从基础补起'),('basic','学过，能解释常见概念'),('strong','能用于建模与实验，并解释假设和限制')])
    fields+=select('research','04 / 你有怎样的研究证据？',[('none','暂时没有'),('course','课程实验或复现，个人贡献可说明'),('independent','有可归属的研究问题、对照和实验贡献')])
    fields+=select('preference','05 / 你更想交付哪一种工作？',[('models','可验证的预测、排序或推荐模型'),('research','新问题、新方法与研究结论'),('systems','可部署、可观测的模型系统'),('applications','完成具体任务的 AI 应用')])
    body='<div class="wrap">'+page_head('ROLE READINESS CHECK','先判断下一步，不猜录用概率。','用你的真实能力与一条具体岗位来回答。结果只用于选择补证据的方向，不替代雇主要求或工作资格审查。')+'<section class="section wizard-grid"><div><form id="route-wizard" class="wizard-form">'+fields+'<button class="button" type="submit">生成下一步行动</button><p class="small-muted">无需姓名、学校或个人证件。回答不上传。</p></form><section id="wizard-result" class="wizard-result" aria-live="polite" hidden></section></div><aside class="wizard-aside"><p class="eyebrow">判断顺序</p><h2>资格 → 职责 → 证据</h2><p>学历和学校只提供背景信息。判断依据是具体岗位要交付的工作，以及你能提供的证据。</p><ul><li>岗位资格未知：先确认。</li><li>必需能力没有证据：先补一项可验收作品。</li><li>研究岗位：另查学位、专业、论文与个人研究贡献。</li><li>能运行教程：不等于能独立交付。</li></ul><a class="text-link" href="jobs.html">先找到一条真实 JD →</a><hr style="border:0;border-top:1px solid var(--line);margin:22px 0"><p>AI 产品经理归产品求职专题。交叉的数据科学、解决方案岗位，要继续按主要职责分流。</p></aside></section></div>'
    save('self-check.html','岗位自查与下一步行动',body)


def build_search():
    body='<div class="wrap">'+page_head('SEARCH THE GUIDE','快速找到当前的卡点。','搜索全部章节、地区说明、岗位研究与可编辑模板。全文索引随网站打包；下载源码并在本地启动静态服务器后，可断网搜索。')+'<form id="site-search" class="search-form"><label class="sr-only" for="search-query">搜索关键词</label><input id="search-query" type="search" placeholder="试试：面试、工作资格、macro F1、英国" autocomplete="off"><button class="button" type="submit">搜索</button></form><p id="search-count" class="result-count" aria-live="polite"></p><section id="search-results" class="section search-results"></section></div>'
    save('search.html','全文搜索',body,search=True)


def collect_pages():
    paths=[]
    for group in ['docs','research','templates']:
        paths.extend(sorted((ROOT/group).glob('*.md')) if (ROOT/group).exists() else [])
    paths.extend(sorted((ROOT/'examples').glob('**/README.md')))
    if (ROOT/'examples/DATA-LICENSE.md').exists():paths.append(ROOT/'examples/DATA-LICENSE.md')
    for filename in ['README.md','VALIDATION.md','PUBLISH.md','DEPLOYMENT.md','AUTHORSHIP.md','LICENSE-CONTENT.md','CONTRIBUTING.md','CHANGELOG.md']:
        if (ROOT/filename).exists(): paths.append(ROOT/filename)
    for file in paths:
        source=str(file.relative_to(ROOT))
        text=file.read_text(encoding='utf-8')
        url='read/'+source[:-3].replace('/','-')+'.html'
        plain=markdown_to_plain(text)
        title=text_title(text,file.stem)
        preview=complete_preview(text)
        PAGES[source]=dict(source=source,url=url,title=title,text=text,plain=plain,preview=preview,section=section_of(source))


def copy_sources():
    permitted={'.py','.json','.jsonl','.csv','.tsv','.md','.txt','.sh','.toml','.yaml','.yml','.svg','.png','.jpg','.jpeg','.webp'}
    for folder in ['docs','research','templates','examples','scripts','pdf','assets']:
        path=ROOT/folder
        if not path.exists():continue
        for f in path.rglob('*'):
            if not f.is_file() or f.suffix.lower() not in permitted or any(part.startswith('.') or part=='__pycache__' for part in f.relative_to(ROOT).parts):continue
            dest=OUT/'source'/f.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    # Publish only small, top-level validation evidence; never render intermediates.
    validation_path = ROOT/'validation'
    if validation_path.exists():
        for f in validation_path.glob('*'):
            if not f.is_file() or f.suffix.lower() not in {'.log','.json','.md'} or f.name.startswith('.'):
                continue
            dest=OUT/'source'/'validation'/f.name
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(f,dest)
    for filename in ['README.md','LICENSE','LICENSE-CODE','LICENSE-CONTENT','LICENSE-CONTENT.md','NOTICE','CONTRIBUTING.md','CHANGELOG.md','VALIDATION.md','PUBLISH.md','DEPLOYMENT.md','AUTHORSHIP.md']:
        f=ROOT/filename
        if f.exists():dest=OUT/'source'/filename;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)


def main():
    global REPO_URL
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-url',default='',help='Only set after this exact public GitHub repository has been verified.')
    args=parser.parse_args()
    if args.repo_url and not re.fullmatch(r'https://github\.com/AIPMAndy/chinese-international-student-ai-jobs/?',args.repo_url):
        raise SystemExit('Unexpected repository URL. This build must only advertise this task repository.')
    REPO_URL=args.repo_url.rstrip('/')
    OUT.mkdir(exist_ok=True);(OUT/'assets').mkdir(exist_ok=True);(OUT/'data').mkdir(exist_ok=True);(OUT/'downloads').mkdir(exist_ok=True)
    for f in (ROOT/'site-assets').iterdir():
        if f.is_file():shutil.copy2(f,OUT/'assets'/f.name)
    (OUT/'assets/favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="16" fill="#152725"/><path d="M18 47 29 17h7l11 30h-8l-2-7H28l-2 7zm12-14h5l-2-9z" fill="#e5eddb"/></svg>',encoding='utf-8')
    preview = ROOT/'assets'/'social-preview.png'
    if not preview.is_file():
        raise SystemExit('assets/social-preview.png is required for the published social card')
    shutil.copy2(preview, OUT/'assets'/'social-preview.png')
    collect_pages();copy_sources()
    jd=read_json('research/employer-jds.json',{});policy=read_json('research/regional-rules.json',{});summary=read_json('examples/verification-summary.json',{})
    search_data=[dict(title=p['title'],url=p['url'],text=p['plain'],section=p['section']) for p in PAGES.values()]
    (OUT/'data/search-index.js').write_text('window.AI_JOBS_SEARCH='+json.dumps(search_data,ensure_ascii=False).replace('</','<\\/')+';\n',encoding='utf-8')
    build_home(jd,policy,summary);build_guide();build_read_pages();build_jobs(jd);build_regions(policy);build_projects(summary);build_downloads();build_selfcheck();build_search()
    manifest=dict(title=TITLE,version='1.0.0',checked_at=DATE,github_url=REPO_URL or None,content_pages=len(PAGES),top_pages=['index.html','guide.html','jobs.html','regions.html','projects.html','downloads.html','self-check.html','search.html'],jd_records=len(jd.get('jobs',[])),region_records=len(policy.get('regions',[])),downloads=[p.name for p in sorted((OUT/'downloads').glob('*')) if p.is_file()],data_sources=['research/employer-jds.json','research/regional-rules.json','examples/verification-summary.json'],generated_with='Python standard library; local static assets; no external requests')
    (OUT/'site-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    # Every HTML route is included (including deep reader pages); no fictitious paths.
    from xml.sax.saxutils import escape as xml_escape
    html_pages = sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob('*.html'))
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>' \
        + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' \
        + ''.join('<url><loc>' + xml_escape(SITE_URL if page == 'index.html' else SITE_URL + page) + '</loc><lastmod>' + DATE + '</lastmod></url>' for page in html_pages) \
        + '</urlset>'
    (OUT/'sitemap.xml').write_text(sitemap, encoding='utf-8')
    (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + SITE_URL + 'sitemap.xml\n', encoding='utf-8')

    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
