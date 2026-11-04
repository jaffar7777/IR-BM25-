"""Add exact 7- and 9-page excerpts to the existing corpus without downloads."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from variants import VARIANT_PAGES, VARIANTS

ROOT = Path(__file__).parent

def main():
    path = ROOT / 'data/papers.jsonl'
    papers = [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]
    for i, paper in enumerate(papers):
        if 'medium' in paper['variants']:
            paper['variants']['medium8'] = paper['variants'].pop('medium')
        long_text = (ROOT / paper['variants']['long']['path']).read_text(encoding='utf-8')
        with pymupdf.open(ROOT / paper['pdf_path']) as pdf:
            pages = [pdf[n].get_text(sort=True) for n in range(9)]
        for name, count in [('medium7', 7), ('medium9', 9)]:
            text = '\n\n'.join(pages[:count])
            if not long_text.startswith(text):
                raise RuntimeError(f'{paper["arxiv_id"]}: extraction differs from stored source; refusing inconsistent excerpt')
            out = ROOT / 'data/texts' / f'{paper["versioned_id"]}_{name}.txt'
            out.write_text(text, encoding='utf-8')
            paper['variants'][name] = {'path': out.relative_to(ROOT).as_posix(), 'pages': count,
                'words': len(text.split()), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}
        paper['variants'] = {v: paper['variants'][v] for v in VARIANTS}
        print(f'Prepared {i+1}/{len(papers)}: medium 7, 8, 9 pages', flush=True)
    temporary = path.with_suffix('.jsonl.tmp')
    temporary.write_text(''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in papers), encoding='utf-8')
    temporary.replace(path)
    manifest_path = ROOT / 'data/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['variants'] = {v: f'first {n} source PDF pages' if n else 'all source PDF pages (at least 10)' for v,n in VARIANT_PAGES.items()}
    manifest['medium_variants_updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Metadata updated. Rebuild the index and corpus distribution archives.',flush=True)

if __name__ == '__main__':
    main()
