"""Exercise real embeddings and actual corpus; no relevance-quality claims."""
import json
import time
import numpy as np
from engine import Engine, ROOT, canonical

def main():
    start = time.perf_counter()
    engine = Engine()
    checks = []
    for variant in ['short', 'medium', 'long']:
        for mode in ['bm25', 'dense', 'rrf', 'weighted']:
            t = time.perf_counter()
            result = engine.search('machine translation', mode=mode, variant=variant)
            assert len(result['results']) == 10, (variant, mode, len(result['results']))
            assert len({r['arxiv_id'] for r in result['results']}) == 10
            assert all(np.isfinite(r['score']) and len(r['snippet']) <= 200 for r in result['results'])
            checks.append({'variant': variant, 'mode': mode, 'results': 10, 'seconds': round(time.perf_counter()-t, 3)})
    plain = engine.search('machine translation')['results']
    case = engine.search('MACHINE TRANSLATION')['results']
    assert [r['arxiv_id'] for r in plain] == [r['arxiv_id'] for r in case]
    abbreviation = engine.search('NLP')
    assert abbreviation['query'] == 'natural language processing'
    typo = engine.search('translatoin')
    assert 'translation' in typo['query']
    quoted = engine.search('"machine translation"')
    assert quoted['results']
    by_id = {p['arxiv_id']: i for i, p in enumerate(engine.papers)}
    assert all(' machine translation ' in ' '+canonical(engine.texts['long'][by_id[r['arxiv_id']]])+' ' for r in quoted['results'])
    assert engine.search('"this phrase cannot possibly occur qzxjv993"')['results'] == []
    assert engine.search('')['results'] == []
    topic = engine.search('summarization', topic='summarization', rerank=True)
    assert topic['results'] and all(r['subtopic'] == 'summarization' for r in topic['results'])
    report = {'passed': True, 'papers': len(engine.papers), 'checks': checks,
              'query_checks': ['case invariance', 'abbreviation expansion', 'spelling correction', 'mandatory phrase matching', 'empty query', 'topic filter with reranking'],
              'total_seconds': round(time.perf_counter()-start, 3),
              'limitation': 'Functional checks only. No relevance judgments, precision/recall or ranking-quality evaluation.'}
    (ROOT / 'validation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
