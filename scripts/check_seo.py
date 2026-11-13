#!/usr/bin/env python3
"""Verify all generated AI-career Pages SEO/GEO facts and absolute sitemap URLs."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'dist'
BASE = 'https://aipmandy.github.io/chinese-international-student-ai-jobs/'


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.title = ''
        self.inside_title = False
        self.description = ''
        self.canonical = []
        self.og = {}
        self.scripts = []
        self.inside_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'h1': self.h1 += 1
        if tag == 'title': self.inside_title = True
        if tag == 'link' and 'canonical' in a.get('rel','').split():
            self.canonical.append(a.get('href',''))
        if tag == 'meta':
            if a.get('name') == 'description': self.description = a.get('content','')
            if a.get('property','').startswith('og:'):
                self.og[a['property']] = a.get('content','')
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.scripts.append('')
            self.inside_script = True

    def handle_data(self, value):
        if self.inside_title: self.title += value
        if self.inside_script: self.scripts[-1] += value

    def handle_endtag(self, tag):
        if tag == 'title': self.inside_title = False
        if tag == 'script': self.inside_script = False


def main():
    errors = []
    html_files = sorted(SITE.rglob('*.html'))
    expected = set()
    for file in html_files:
        path = file.relative_to(SITE).as_posix()
        url = BASE if path == 'index.html' else BASE + path
        expected.add(url)
        meta = Page()
        meta.feed(file.read_text('utf-8'))
        if meta.h1 != 1: errors.append(f'{path}: expected one H1; found {meta.h1}')
        if not meta.title or not meta.description: errors.append(f'{path}: missing title/description')
        if meta.canonical != [url]: errors.append(f'{path}: wrong canonical {meta.canonical!r}')
        if meta.og.get('og:title') != meta.title or meta.og.get('og:url') != url:
            errors.append(f'{path}: OG title/URL mismatch')
        for key in ['og:site_name','og:description','og:locale']:
            if not meta.og.get(key): errors.append(f'{path}: missing {key}')
        if len(meta.scripts) != 1:
            errors.append(f'{path}: JSON-LD count {len(meta.scripts)}')
            continue
        try:
            doc = json.loads(meta.scripts[0])
        except json.JSONDecodeError as exc:
            errors.append(f'{path}: invalid JSON-LD: {exc}')
            continue
        if doc.get('@context') != 'https://schema.org' or doc.get('@type') != 'WebPage':
            errors.append(f'{path}: invalid WebPage context/type')
        if doc.get('url') != url or doc.get('inLanguage') != 'zh-CN':
            errors.append(f'{path}: schema URL/language mismatch')
        if doc.get('author',{}).get('name') != 'AI 酋长 Andy' or doc.get('author',{}).get('url') != 'https://metaver.vip/':
            errors.append(f'{path}: author mismatch')
        if doc.get('publisher',{}).get('url') != 'https://www.a6no1.cn/':
            errors.append(f'{path}: publisher mismatch')
    try:
        robot = (SITE/'robots.txt').read_text('utf-8')
        if 'Sitemap: '+BASE+'sitemap.xml' not in robot:
            errors.append('robots: missing absolute sitemap')
        document = ET.parse(SITE/'sitemap.xml')
        locs = [n.text for n in document.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        if len(locs) != len(set(locs)): errors.append('sitemap: duplicate URLs')
        if set(locs) != expected:
            errors.append(f'sitemap: {len(set(locs))} URLs != {len(expected)} pages')
    except (OSError, ET.ParseError) as exc:
        errors.append(f'robots/sitemap invalid: {exc}')
    homepage = (SITE/'index.html').read_text('utf-8')
    for value in ('AIPMAndy', 'data-copy', 'https://metaver.vip/', 'https://metaver.vip/services', 'https://www.a6no1.cn/'):
        if value not in homepage: errors.append('homepage missing '+value)
    summary = {'html_pages':len(html_files),'sitemap_urls':len(expected),'errors':errors[:40],'omitted_errors':max(0,len(errors)-40)}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return int(bool(errors))


if __name__ == '__main__': sys.exit(main())
