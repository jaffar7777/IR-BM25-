"""BM25, pretrained dense embeddings, and genuine rank/score fusion."""
import hashlib
import json
import math
import re
from collections import Counter
from difflib import get_close_matches
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
ABBREVIATIONS = {'nlp': 'natural language processing', 'mt': 'machine translation', 'nmt': 'neural machine translation',
                 'qa': 'question answering', 'rag': 'retrieval augmented generation', 'llm': 'large language model',
                 'llms': 'large language models', 'nlu': 'natural language understanding', 'nlg': 'natural language generation'}
STOP = set('a an the of and or is are to for in on with by at from this that it as be using'.split())
MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

def ensure_corpus(root=ROOT):
    """Unpack the byte-preserving GitHub corpus distribution on first use."""
    import zipfile
    archive = root / 'corpus-data.zip'
    if not archive.exists():
        return
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    marker = root / 'data/.corpus-unpacked.sha256'
    if marker.exists() and marker.read_text().strip() == digest:
        return
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            target = (root / entry.filename).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('Unsafe path in corpus archive')
        source.extractall(root)
    marker.write_text(digest)

ensure_corpus()

def tokens(text):
    return re.findall(r'[a-z0-9]+', text.casefold())

def canonical(text):
    return ' '.join(tokens(text))

def prepare_query(query, vocab, correct=True):
    phrases = [canonical(p) for p in re.findall(r'"([^"\n]+)"', query) if canonical(p)]
    protected = {t for p in phrases for t in tokens(p)}
    changes = []
    output = []
    for token in tokens(query):
        if token in ABBREVIATIONS:
            output.extend(tokens(ABBREVIATIONS[token]))
            changes.append(f'{token} -> {ABBREVIATIONS[token]}')
            continue
        replacement = token
        if correct and len(token) >= 4 and token not in vocab and token not in protected and not token.isdigit():
            matches = get_close_matches(token, vocab, n=1, cutoff=.84)
            if matches:
                replacement = matches[0]
                changes.append(f'{token} -> {replacement}')
        output.append(replacement)
    return ' '.join(output), phrases, changes

def rrf(sparse, dense, k=60):
    result = np.zeros(len(sparse), dtype=np.float64)
    # Only actual lexical matches contribute to the sparse ranking.
    for scores, eligible in [(sparse, np.flatnonzero(sparse > 0)), (dense, np.arange(len(dense)))]:
        order = eligible[np.argsort(-scores[eligible], kind='stable')]
        result[order] += 1 / (k + np.arange(1, len(order) + 1))
    return result

def weighted(sparse, dense, alpha=.5):
    def scale(values):
        spread = values.max() - values.min()
        return (values - values.min()) / spread if spread > 1e-12 else np.zeros_like(values)
    return alpha * scale(sparse) + (1 - alpha) * scale(dense)

class Encoder:
    def __init__(self, local=True):
        import torch
        from transformers import AutoTokenizer, AutoModel
        self.torch = torch
        path = ROOT / 'models' / 'minilm'
        source = str(path) if path.exists() else MODEL
        cache = str(ROOT / 'models' / 'download-cache')
        self.tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=local, cache_dir=cache)
        self.model = AutoModel.from_pretrained(source, local_files_only=local, cache_dir=cache)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device).eval()
        if not local:
            path.mkdir(parents=True, exist_ok=True)
            self.tokenizer.save_pretrained(path)
            self.model.save_pretrained(path)

    def encode(self, texts, batch_size=32):
        vectors = []
        for offset in range(0, len(texts), batch_size):
            batch = self.tokenizer(texts[offset:offset + batch_size], return_tensors='pt', padding=True, truncation=True, max_length=256).to(self.device)
            with self.torch.inference_mode():
                hidden = self.model(**batch).last_hidden_state
                mask = batch['attention_mask'].unsqueeze(-1)
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1)
                pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
            vectors.append(pooled.cpu().numpy())
        return np.concatenate(vectors).astype('float32')

class Engine:
    def __init__(self):
        self.papers = [json.loads(line) for line in (ROOT / 'data/papers.jsonl').read_text(encoding='utf-8').splitlines()]
        self.texts = {}
        self.counters = {}
        self.idfs = {}
        self.lengths = {}
        self.vocab = set()
        for variant in ['short', 'medium', 'long']:
            texts = [p['title'] + '\n' + (ROOT / p['variants'][variant]['path']).read_text(encoding='utf-8') for p in self.papers]
            self.texts[variant] = texts
            counters = [Counter(tokens(t)) for t in texts]
            self.counters[variant] = counters
            df = Counter(t for c in counters for t in c)
            self.idfs[variant] = {t: math.log(1 + (len(texts) - n + .5) / (n + .5)) for t, n in df.items()}
            self.lengths[variant] = np.array([sum(c.values()) for c in counters])
            self.vocab.update(t for t, n in df.items() if n >= 2)
        self.encoder = Encoder()
        self.dense = np.load(ROOT / 'index/chunks.npz')
        metadata = json.loads((ROOT / 'index/manifest.json').read_text())
        if metadata['corpus_sha256'] != hashlib.sha256((ROOT / 'data/papers.jsonl').read_bytes()).hexdigest():
            raise RuntimeError('Corpus changed; run python build_index.py again.')

    def search(self, query, mode='rrf', variant='long', alpha=.5, correct=True, rerank=False, topic='all'):
        query = query.strip()
        if not query:
            return {'query': '', 'changes': [], 'results': []}
        normalized, phrases, changes = prepare_query(query, self.vocab, correct)
        q = Counter(t for t in tokens(normalized) if t not in STOP)
        if not q and phrases:
            q = Counter(tokens(normalized))
        if not q:
            return {'query': normalized, 'changes': changes, 'results': []}
        counters, lengths = self.counters[variant], self.lengths[variant]
        sparse = np.zeros(len(self.papers))
        for term, freq in q.items():
            tf = np.array([c.get(term, 0) for c in counters])
            sparse += self.idfs[variant].get(term, 0) * tf * 2.5 / (tf + 1.5 * (.25 + .75 * lengths / lengths.mean())) * freq
        dense = np.full(len(self.papers), -1., dtype='float32')
        query_vector = self.encoder.encode([normalized])[0]
        eligible_chunks = self.dense['end_word'] <= self.dense[f'{variant}_limit']
        similarities = self.dense['vectors'][eligible_chunks] @ query_vector
        np.maximum.at(dense, self.dense['paper_index'][eligible_chunks], similarities)
        if mode == 'rrf':
            scores = rrf(sparse, dense)
        elif mode == 'weighted':
            scores = weighted(sparse, dense, alpha)
        elif mode == 'bm25':
            scores = sparse.copy()
        elif mode == 'dense':
            scores = dense.copy()
        else:
            raise ValueError('Unknown retrieval mode')
        allowed = np.array([(topic == 'all' or p['subtopic'] == topic) and all((' ' + phrase + ' ') in (' ' + canonical(self.texts[variant][i]) + ' ') for phrase in phrases) for i, p in enumerate(self.papers)])
        if mode == 'bm25':
            allowed &= sparse > 0
        order = [int(i) for i in np.argsort(-scores, kind='stable') if allowed[i]][:50]
        # Optional, transparent lexical reranking of the fused top-50. No learned reranker.
        bonus = {}
        if rerank:
            for i in order:
                title_terms = set(tokens(self.papers[i]['title']))
                bonus[i] = len(set(q) & title_terms) / max(1, len(q))
            order.sort(key=lambda i: -(scores[i] + (.005 if mode == 'rrf' else .05) * bonus[i]))
        results = []
        for i in order[:10]:
            p = self.papers[i]
            # Abstract-based snippets avoid PDF title/author/header extraction noise.
            # Ranking still uses the selected full-text variant.
            text = ' '.join(p.get('abstract', self.texts[variant][i]).split())
            match = re.search('|'.join(re.escape(t) for t in q), text, flags=re.I) if q else None
            start = max(0, (match.start() if match else 0) - 60)
            results.append({'title': p['title'], 'url': p['arxiv_url'], 'arxiv_id': p['arxiv_id'],
                            'subtopic': p['subtopic'], 'snippet': text[start:start + 200],
                            'score': float(scores[i] + ((.005 if mode == 'rrf' else .05) * bonus.get(i, 0))),
                            'bm25': float(sparse[i]), 'dense': float(dense[i])})
        return {'query': normalized, 'phrases': phrases, 'changes': changes, 'results': results}
