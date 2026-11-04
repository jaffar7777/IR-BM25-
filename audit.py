"""Validate every stored artifact; fail rather than claiming incomplete data is complete."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from engine import ROOT

def audit(require_complete=True):
    records = [json.loads(s) for s in (ROOT / 'data/papers.jsonl').read_text(encoding='utf-8').splitlines()]
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    errors = []
    ids = [p['arxiv_id'] for p in records]
    if len(set(ids)) != len(ids):
        errors.append('Duplicate paper IDs')
    counts = Counter(p['subtopic'] for p in records)
    if require_complete and (len(records) < 400 or len(counts) < 4 or min(counts.values()) < 100):
        errors.append('Expected at least 400 unique papers and 100 per subtopic')
    if require_complete and (not manifest.get('complete') or manifest.get('total_unique') != len(records)):
        errors.append('Manifest completion/count does not match stored records')
    for p in records:
        if p['variants']['long']['pages'] != p['original_pages']:
            errors.append(f'{p["arxiv_id"]}: long variant must include all original pages')
        date = p['published'].replace('-', '').replace(':', '').replace('T', '')[:12]
        if not manifest['start_date'] <= date <= manifest['end_date']:
            errors.append(f'{p["arxiv_id"]}: publication date outside query range')
        for v, bounds in [('short', (1, 5)), ('medium', (7, 9)), ('long', (10, 10000))]:
            variant = p['variants'][v]
            path = ROOT / variant['path']
            if not path.exists():
                errors.append(f'Missing {path}')
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != variant['sha256']:
                errors.append(f'Checksum mismatch: {path}')
            if len(path.read_text(encoding='utf-8').split()) != variant['words']:
                errors.append(f'Word-count mismatch: {path}')
            if not bounds[0] <= variant['pages'] <= bounds[1]:
                errors.append(f'Invalid page count: {path}')
        # PDFs are optional in a Git checkout but mandatory in the local collected corpus.
        pdf = ROOT / p['pdf_path']
        if pdf.exists() and hashlib.sha256(pdf.read_bytes()).hexdigest() != p['pdf_sha256']:
            errors.append(f'PDF checksum mismatch: {pdf}')
        if all((ROOT / p['variants'][v]['path']).exists() for v in ['short', 'medium', 'long']):
            texts = {v: (ROOT / p['variants'][v]['path']).read_text(encoding='utf-8') for v in ['short', 'medium', 'long']}
            if not texts['long'].startswith(texts['medium']) or not texts['medium'].startswith(texts['short']):
                errors.append(f'{p["arxiv_id"]}: excerpts are not nested source-text prefixes')
    result = {'passed': not errors, 'unique_papers': len(records), 'text_variants': 3 * len(records),
              'subtopics': dict(counts), 'local_pdfs': sum((ROOT / p['pdf_path']).exists() for p in records),
              'errors': errors, 'checked_at': datetime.now().isoformat()}
    (ROOT / 'data/audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result

if __name__ == '__main__':
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
