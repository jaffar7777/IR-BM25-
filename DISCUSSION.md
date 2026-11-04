# Live discussion guide

1. Run `python audit.py`, then `python app.py`. Explain that 400 papers are unique sources; 2,000 text variants are not 2,000 independent papers.
2. Search `NLP summarization`. Point out the displayed abbreviation expansion.
3. Search `translatoin`; inspect spelling correction, then switch it off.
4. Search `"machine translation"`. Explain the required phrase filter and case normalization.
5. Compare BM25, dense, RRF and weighted fusion. Hybrid modes produce one fused list, not side-by-side models. Explain why RRF does not require raw scores to share a scale.
6. Switch between short, medium (7 pages), medium (8 pages), medium (9 pages) and long. All three medium lengths are included. Each option searches its exact excerpt/full text, not only abstracts. A phrase occurring only on page 9 must not match the same paper's 7- or 8-page excerpts. The title is included once in lexical text and prefixed to each dense passage.
7. Enable title reranking. Explain the candidate set (top 50), bonus formula, and lack of trained relevance labels. It can change rank, and might reduce quality.
8. Explain the dense pipeline: pretrained encoder, mean pooling, vector normalization, cosine similarity, passage max to document aggregation. The model is not trained from scratch.
9. Discuss limitations: heuristic labels, topic overlap resolved by first assignment, long-source selection bias, truncated model inputs, noisy PDF extraction, title heuristic, no human relevance judgments, excerpt interpretation needing instructor confirmation.
10. Disconnect the network after setup and repeat a search. The dataset, model and index are local.

## Core formulas

BM25(t,d) = IDF(t) * tf(t,d)*(k1+1) / [tf(t,d)+k1*(1-b+b*length(d)/average_length)]. Sum over query terms. IDF(t) = ln(1+(N-df(t)+0.5)/(df(t)+0.5)).

RRF(d) = 1/(60+rank_BM25(d)) + 1/(60+rank_dense(d)), omitting a sparse contribution when there is no lexical match.

Weighted(d) = alpha*normalized_BM25(d)+(1-alpha)*normalized_dense(d).

Optional final score = retrieval score + lambda*|query terms intersect title terms|/|query terms|; lambda is 0.005 for RRF and 0.05 otherwise.
