import hashlib
import json
from pathlib import Path
import numpy as np
from engine import Encoder, ROOT, MODEL

def main():
    encoder = Encoder(local=False)
    papers_path = ROOT / 'data/papers.jsonl'
    papers = [json.loads(line) for line in papers_path.read_text(encoding='utf-8').splitlines()]
    folder = ROOT / 'index'
    folder.mkdir(exist_ok=True)
    all_vectors, ids, ends, limits = [], [], [], {v: [] for v in ['short', 'medium', 'long']}
    for i, paper in enumerate(papers):
        texts = {v: (ROOT / paper['variants'][v]['path']).read_text(encoding='utf-8').split() for v in limits}
        words = texts['long']
        chunks, chunk_ends = [], []
        # Boundaries at variant endings ensure every variant has complete text coverage.
        boundaries = sorted({0, len(texts['short']), len(texts['medium']), len(words)})
        for lo, hi in zip(boundaries, boundaries[1:]):
            for start in range(lo, hi, 100):
                end = min(start + 120, hi)
                chunks.append(paper['title'][:200] + '\n' + ' '.join(words[start:end]))
                chunk_ends.append(end)
        cache = folder / f'{paper["versioned_id"]}.npy'
        if cache.exists():
            vectors = np.load(cache)
            if len(vectors) != len(chunks):
                raise RuntimeError('Chunk cache mismatch; remove index/*.npy and rebuild')
        else:
            vectors = encoder.encode(chunks)
            np.save(cache, vectors)
        all_vectors.append(vectors)
        ids.extend([i] * len(chunks))
        ends.extend(chunk_ends)
        for v in limits:
            limits[v].extend([len(texts[v])] * len(chunks))
        print(f'Indexed {i + 1}/{len(papers)}: {len(chunks)} passages', flush=True)
    np.savez_compressed(folder / 'chunks.npz', vectors=np.concatenate(all_vectors), paper_index=np.array(ids),
                        end_word=np.array(ends), **{f'{v}_limit': np.array(x) for v, x in limits.items()})
    (folder / 'manifest.json').write_text(json.dumps({'model': MODEL, 'pooling': 'attention-masked mean, L2 normalized',
        'max_tokens': 256, 'chunk_words': 120, 'stride_words': 100, 'title_prefix': True,
        'corpus_sha256': hashlib.sha256(papers_path.read_bytes()).hexdigest(), 'papers': len(papers), 'chunks': len(ids)}, indent=2))

if __name__ == '__main__':
    main()
