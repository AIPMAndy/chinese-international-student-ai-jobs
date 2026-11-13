#!/usr/bin/env python3
"""Create complete template and source archives; standard library only."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist' / 'downloads'
NAME = 'chinese-international-student-ai-jobs'
SKIP_PARTS = {'.git', '.openai', '__pycache__', 'tmp', 'node_modules', 'pdf-pages', 'pdf-contact-sheets'}


def include(path):
    rel = path.relative_to(ROOT)
    if any(part in SKIP_PARTS for part in rel.parts):
        return False
    if rel.parts[:2] == ('dist', 'downloads') or rel.parts[:2] == ('dist', 'source'):
        return False
    if path.suffix in {'.pyc', '.gz'} or path.name.startswith('.env'):
        return False
    return path.is_file()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = ROOT / 'pdf' / (NAME + '-guide.pdf')
    if not pdf.exists():
        raise SystemExit('PDF missing: run python3 scripts/build_pdf.py before release packaging')
    shutil.copy2(pdf, OUT / pdf.name)
    with zipfile.ZipFile(OUT/'templates.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted((ROOT/'templates').glob('*.md')):
            z.write(p, 'templates/'+p.name)
        z.write(ROOT/'LICENSE-CONTENT.md', 'LICENSE-CONTENT.md')
    source = OUT / (NAME + '-source.zip')
    with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(ROOT.rglob('*')):
            if include(p):
                z.write(p, NAME+'/'+p.relative_to(ROOT).as_posix())
    records = []
    for p in [OUT/pdf.name, OUT/'templates.zip', source]:
        records.append({'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    # A separate ready-to-open website bundle includes all three downloads.
    # Its own bytes are excluded to prevent recursive archives.
    website = OUT / (NAME + '-website.zip')
    with zipfile.ZipFile(website, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted((ROOT/'dist').rglob('*')):
            if p.is_file() and p not in {website, OUT/'checksums.json'}:
                z.write(p, p.relative_to(ROOT/'dist').as_posix())
        z.writestr('downloads/checksums.json', json.dumps({'version':'1.0.0','artifacts':records},ensure_ascii=False,indent=2)+'\n')
    records.append({'file':website.name,'bytes':website.stat().st_size,'sha256':hashlib.sha256(website.read_bytes()).hexdigest()})
    (OUT/'checksums.json').write_text(json.dumps({'version':'1.0.0','artifacts':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
