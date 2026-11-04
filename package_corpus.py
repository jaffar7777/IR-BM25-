"""Package all referenced text and metadata into two browser-uploadable archives."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).parent

def main():
    papers = [json.loads(s) for s in (ROOT / 'data/papers.jsonl').read_text(encoding='utf-8').splitlines()]
    texts = sorted({ROOT / v['path'] for p in papers for v in p['variants'].values()})
    metadata = sorted(p for p in (ROOT / 'data').rglob('*') if p.is_file() and 'texts' not in p.parts and 'pdfs' not in p.parts and not p.name.startswith('.') and not p.name.endswith('.tmp'))
    groups = [metadata + texts[::2], texts[1::2]]
    for number, group in enumerate(groups, 1):
        out = ROOT / f'corpus-data-{number}.zip'
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for p in group:
                archive.write(p, p.relative_to(ROOT))
        if out.stat().st_size > 24_000_000:
            raise RuntimeError(f'{out.name} exceeds the intended browser-upload budget')
        print(out.name, out.stat().st_size, 'bytes', flush=True)
    # The local extraction is already current. Avoid overwriting an audit on next import.
    archives = [ROOT / f'corpus-data-{n}.zip' for n in (1, 2)]
    digest = hashlib.sha256(b''.join(hashlib.sha256(p.read_bytes()).digest() for p in archives)).hexdigest()
    (ROOT / 'data/.corpus-unpacked.sha256').write_text(digest)

if __name__ == '__main__':
    main()
