#!/usr/bin/env python3
"""Validate evidence records, local links, generated pages and release archives."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.lang = ''
        self.viewport = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        if tag == 'html':
            self.lang = a.get('lang','')
        if tag == 'meta' and a.get('name') == 'viewport':
            self.viewport = True
        if tag in ('a','link') and a.get('href'):
            self.links.append(a['href'])
        if tag in ('script','img') and a.get('src'):
            self.links.append(a['src'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    failures = []
    jobs = json.loads((ROOT/'research/employer-jds.json').read_text())['jobs']
    regions = json.loads((ROOT/'research/regional-rules.json').read_text())['regions']
    for name, rows in [('jobs',jobs),('regions',regions)]:
        if len({r['id'] for r in rows}) != len(rows):
            failures.append(name+': duplicate ids')
        for row in rows:
            if row['checked_at'] != '2026-11-13':
                failures.append(name+': inconsistent edition date '+row['id'])
    for row in jobs:
        if not row['source_url'].startswith('https://'):
            failures.append(row['id']+': invalid source URL')
        for field in ['degree','graduation_window','work_authorization','sponsorship','source_status','uncertainties']:
            if field not in row:
                failures.append(row['id']+': missing '+field)
    for row in regions:
        for src in row['sources']:
            if not src['url'].startswith('https://') or not src.get('access'):
                failures.append(row['id']+': invalid source metadata')
    for p in list((ROOT/'docs').glob('*.md'))+list((ROOT/'templates').glob('*.md'))+list((ROOT/'research').glob('*.md'))+[ROOT/'README.md']:
        body = re.sub(r'```.*?```','',p.read_text(encoding='utf-8'),flags=re.S)
        for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)',body):
            u = urlsplit(target)
            if u.scheme or u.netloc or not u.path:
                continue
            local = (p.parent/unquote(u.path)).resolve()
            if not local.exists() and not (args.allow_incomplete and local.suffix=='.pdf'):
                failures.append(str(p.relative_to(ROOT))+': missing '+target)
    pages = {}
    for p in (ROOT/'dist').rglob('*.html'):
        if 'source' in p.relative_to(ROOT/'dist').parts:
            continue
        page = Page()
        content = p.read_text(encoding='utf-8')
        page.feed(content)
        pages[p.resolve()] = page
        if page.lang != 'zh-CN' or not page.viewport:
            failures.append(str(p.relative_to(ROOT))+': missing language or viewport')
        if '\x00' in content or '\ufffd' in content:
            failures.append(str(p.relative_to(ROOT))+': invalid rendered character')
    for path, page in pages.items():
        for target in page.links:
            u=urlsplit(target)
            if u.scheme or u.netloc:
                continue
            dest=(path.parent/unquote(u.path)).resolve() if u.path else path
            if not dest.exists():
                if not (args.allow_incomplete and dest.suffix in ('.pdf','.zip')):
                    failures.append(str(path.relative_to(ROOT))+': broken link '+target)
            elif u.fragment and dest in pages and unquote(u.fragment) not in pages[dest].ids:
                failures.append(str(path.relative_to(ROOT))+': missing anchor '+target)
    # Check complete original URLs, including parentheses in official job paths.
    fidelity = [
        ('jobs.html', [j['source_url'] for j in jobs]),
        ('read/research-employer-jds.html', [j['source_url'] for j in jobs]),
        ('regions.html', [s['url'] for r in regions for s in r['sources']]),
        ('read/research-regional-rules.html', [s['url'] for r in regions for s in r['sources']]),
    ]
    for filename, expected_urls in fidelity:
        page = pages.get((ROOT/'dist'/filename).resolve())
        if page is None:
            failures.append('missing source-bearing page '+filename)
            continue
        for url in expected_urls:
            if url not in page.links:
                failures.append(filename+': original source URL missing or altered: '+url)
    manifest = json.loads((ROOT/'dist/site-manifest.json').read_text())
    if not manifest.get('github_url'):
        candidate = 'https://github.com/AIPMAndy/chinese-international-student-ai-jobs'
        for path, page in pages.items():
            if any(url.startswith(candidate) for url in page.links):
                failures.append(str(path.relative_to(ROOT))+': unpublished candidate repository advertised as a live link')
    downloads=ROOT/'dist/downloads'
    archives=[]
    if not args.allow_incomplete:
        expected=['chinese-international-student-ai-jobs-guide.pdf','templates.zip','chinese-international-student-ai-jobs-source.zip','chinese-international-student-ai-jobs-website.zip']
        for name in expected:
            p=downloads/name
            if not p.exists() or p.stat().st_size==0:
                failures.append('missing download '+name)
                continue
            if p.suffix=='.pdf' and not p.read_bytes().startswith(b'%PDF-'):
                failures.append('invalid PDF signature')
            if p.suffix=='.zip':
                with zipfile.ZipFile(p) as z:
                    if z.testzip():
                        failures.append('corrupt zip '+name)
                    if any(n.startswith('/') or '..' in Path(n).parts for n in z.namelist()):
                        failures.append('unsafe archive path '+name)
                    archives.append({'name':name,'members':len(z.namelist())})
        cpath=downloads/'checksums.json'
        if cpath.exists():
            for a in json.loads(cpath.read_text())['artifacts']:
                p=downloads/a['file']
                if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:
                    failures.append('checksum mismatch '+a['file'])
    result={'version':'1.0.0','checked_at':'2026-11-13','jd_records':len(jobs),'jd_detail_readable':sum(x['source_status']=='official_detail_readable' for x in jobs),'regions':len(regions),'templates':len(list((ROOT/'templates').glob('[0-9][0-9]-*.md'))),'html_pages':len(pages),'original_source_url_placements_checked':sum(len(urls) for _,urls in fidelity),'archives':archives,'failures':failures,'status':'passed' if not failures else 'failed','external_links':'Primary source access statuses recorded in research; not a blanket assertion that every external URL is currently reachable.'}
    (ROOT/'validation').mkdir(exist_ok=True)
    (ROOT/'validation/content-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(failures))


if __name__=='__main__':
    main()
