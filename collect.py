"""Resumable, single-connection arXiv collection. Run from project directory."""
import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from variants import VARIANT_PAGES, VARIANTS

DATA = Path(__file__).parent / 'data'
TOPICS = {'machine_translation': '"machine translation"', 'question_answering': '"question answering"',
          'summarization': 'summarization', 'dialogue_systems': '("dialogue system" OR "dialogue systems" OR "dialog system")'}
START, END = '202301010000', '202610312359'
NS = {'a': 'http://www.w3.org/2005/Atom', 'x': 'http://arxiv.org/schemas/atom'}
last_request = 0

def get(url):
    global last_request
    for attempt in range(4):
        time.sleep(max(0, 3.1 - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'UniversityIRPhase1/1.0 academic corpus'})
            with urllib.request.urlopen(req, timeout=75) as response:
                return response.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))

def read_records():
    path = DATA / 'papers.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--per-topic', type=int, default=100)
    args = parser.parse_args()
    for folder in ['pdfs', 'texts', 'raw_api']:
        (DATA / folder).mkdir(parents=True, exist_ok=True)
    papers = read_records()
    seen = {p['arxiv_id'] for p in papers}
    rejected_path = DATA / 'rejected.jsonl'
    rejected = {json.loads(s)['arxiv_id'] for s in rejected_path.read_text(encoding='utf-8').splitlines()} if rejected_path.exists() else set()
    manifest = {'category': 'cs.CL', 'start_date': START, 'end_date': END,
                'target_per_topic': args.per_topic, 'queries': {},
                'selection': 'First 100 globally unique papers per topic in descending submission order with >=10 PDF pages and extractable text. Topic order is insertion order in TOPICS. Labels are keyword-derived, not human annotations.',
                'variants': {v: f'first {n} source PDF pages' if n else 'all source PDF pages (at least 10)' for v, n in VARIANT_PAGES.items()},
                'started_at_utc': datetime.now(timezone.utc).isoformat()}
    old_manifest = DATA / 'manifest.json'
    if old_manifest.exists():
        manifest['started_at_utc'] = json.loads(old_manifest.read_text())['started_at_utc']
    def save():
        manifest['counts'] = dict(Counter(p['subtopic'] for p in papers))
        manifest['total_unique'] = len(papers)
        manifest['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
        manifest['complete'] = all(manifest['counts'].get(t, 0) >= args.per_topic for t in TOPICS)
        old_manifest.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for label, term in TOPICS.items():
        query = f'cat:cs.CL AND all:{term} AND submittedDate:[{START} TO {END}]'
        manifest['queries'][label] = query
        save()
        count = sum(p['subtopic'] == label for p in papers)
        offset = 0
        while count < args.per_topic and offset < 3000:
            cache = DATA / 'raw_api' / f'{label}_{offset}.xml'
            params = {'search_query': query, 'start': offset, 'max_results': 100,
                      'sortBy': 'submittedDate', 'sortOrder': 'descending'}
            if not cache.exists():
                cache.write_bytes(get('https://export.arxiv.org/api/query?' + urllib.parse.urlencode(params)))
            entries = ET.fromstring(cache.read_bytes()).findall('a:entry', NS)
            if not entries:
                break
            for entry in entries:
                version = entry.findtext('a:id', '', NS).rsplit('/', 1)[-1]
                pid = re.sub(r'v\d+$', '', version)
                if not re.fullmatch(r'\d{4}\.\d{4,5}', pid) or pid in seen or pid in rejected:
                    continue
                pdf = DATA / 'pdfs' / f'{version}.pdf'
                try:
                    if not pdf.exists():
                        payload = get(f'https://arxiv.org/pdf/{version}')
                        if not payload.startswith(b'%PDF'):
                            raise ValueError('Response is not a PDF')
                        pdf.write_bytes(payload)
                    with pymupdf.open(pdf) as doc:
                        pages = [page.get_text(sort=True) for page in doc]
                    if len(pages) < 10 or any(len(' '.join(pages[:n]).split()) < n * 80 for n in [5, 7, 8, 9, len(pages)]):
                        rejected.add(pid)
                        with rejected_path.open('a', encoding='utf-8') as f:
                            f.write(json.dumps({'arxiv_id': pid, 'pages': len(pages), 'reason': 'too short or insufficient extractable text'}) + '\n')
                        pdf.unlink()
                        continue
                    variants = {}
                    for name, limit in VARIANT_PAGES.items():
                        n = limit or len(pages)
                        path = DATA / 'texts' / f'{version}_{name}.txt'
                        text = '\n\n'.join(pages[:n])
                        path.write_text(text, encoding='utf-8')
                        variants[name] = {'path': path.relative_to(DATA.parent).as_posix(), 'pages': n, 'words': len(text.split()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                    record = {'arxiv_id': pid, 'versioned_id': version, 'arxiv_url': f'https://arxiv.org/abs/{version}',
                              'pdf_url': f'https://arxiv.org/pdf/{version}', 'pdf_path': pdf.relative_to(DATA.parent).as_posix(),
                              'pdf_sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(),
                              'title': ' '.join(entry.findtext('a:title', '', NS).split()),
                              'abstract': ' '.join(entry.findtext('a:summary', '', NS).split()),
                              'published': entry.findtext('a:published', '', NS), 'subtopic': label,
                              'license': entry.findtext('x:license', '', NS), 'original_pages': len(pages), 'variants': variants}
                    with (DATA / 'papers.jsonl').open('a', encoding='utf-8') as f:
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    papers.append(record)
                    seen.add(pid)
                    count += 1
                    save()
                    print(f'{label}: {count}/{args.per_topic}; total={len(papers)}; {version}; pages={len(pages)}', flush=True)
                except Exception as exc:
                    with (DATA / 'errors.jsonl').open('a', encoding='utf-8') as f:
                        f.write(json.dumps({'arxiv_id': pid, 'error': str(exc)}) + '\n')
                    print(f'Retry on next run: {pid}: {exc}', flush=True)
                if count >= args.per_topic:
                    break
            offset += len(entries)
        save()
    if not manifest['complete']:
        raise SystemExit('Collection incomplete. Review manifest and errors; rerun to resume.')

if __name__ == '__main__':
    main()
