# Phase 1: arXiv Corpus and Hybrid Retrieval

Category: **cs.CL**. Four keyword-derived subtopics: machine translation, question answering, summarization, dialogue systems. Target: **400 unique source papers, 100 per topic**, and three length variants per paper. Actual completion is recorded in `data/manifest.json` and checked by `audit.py`; target counts are not evidence of completion.

## Run locally

Requires Python 3.10+ (tested on Python 3.12), about 4 GB free RAM, and internet for initial package/model setup. Runtime search is local and offline after setup.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python build_index.py
python app.py
```

Open http://127.0.0.1:8501 if the browser does not open automatically. Stop with Ctrl+C. On later runs, use `python app.py` without rebuilding. The embedding model and passage index are generated locally rather than committed as large Git files. The complete collected text dataset is committed as `corpus-data.zip` (about 23 MB) to fit GitHub website upload limits. Importing the engine unpacks it automatically on first use, preserving exact bytes and checksums. Original PDFs remain in the local delivery folder; their versioned URLs and SHA-256 checksums are in the dataset.

On Windows you can alternatively double-click `setup.bat` once, then `run.bat` for subsequent launches. The supplied local delivery has model weights and an index already prepared; `run.bat` can use the existing Python installation when no virtual environment is present.

## Reproduce collection

```powershell
python collect.py
python audit.py
python build_index.py
python -m unittest test_engine.py -v
python integration_check.py
python report.py
```

The collector checkpoints each accepted paper. Rerun after interruption. It uses one connection and at least 3.1 seconds between request starts. Raw Atom responses, versioned paper IDs, dates, exact queries, accepted/rejected records, and checksums are preserved. The fixed submission-date interval is **2023-01-01 00:00 UTC through 2026-10-31 23:59 UTC**. Newly updated versions can affect a fresh collection; use recorded versioned URLs and cached API responses for the closest reproduction of this snapshot.

## Corpus design and length variants

Only source papers with at least 10 PDF pages and sufficient extractable text are accepted. The first 100 globally unique accepted papers for each topic are selected in descending submission-date order. Topic order resolves overlaps; a paper receives one label. Labels come from the arXiv keyword queries and are not expert-reviewed ground truth. Cross-listed cs.CL papers are permitted.

Each paper has a **short first-5-page excerpt**, a **medium first-8-page excerpt**, and a **long full-paper variant** with at least 10 pages. Page counts refer to original PDF page boundaries, including references and appendices. Excerpts are not summaries or separately authored papers. This design permits controlled comparisons of retrieval on different lengths, but it biases the source corpus toward longer papers. The ambiguous 6-page gap in the assignment is avoided. Confirm with the instructor if they intended naturally short/medium/long source papers rather than derived variants.

Text extraction uses PyMuPDF; equations, tables, columns, headers, references and scanned pages can reduce text quality. Full text is retained as extracted rather than claiming perfect reading order. Original source PDFs and versioned links allow inspection.

## Ranking implementation

* **BM25:** token-frequency scoring, `k1=1.5`, `b=0.75`, positive Robertson IDF. Each variant has its own document lengths and document frequencies. Title text is prepended once.
* **Dense:** pretrained `sentence-transformers/all-MiniLM-L6-v2` through Transformers. Attention-masked mean pooling and L2 normalization produce 384-dimensional vectors. Full texts are split into 120-word passages with 100-word stride, respecting variant boundaries, with a title prefix. Encoder input is limited to 256 model tokens; unusually token-dense passages may be truncated. A document score is the maximum cosine similarity among its eligible passages. Longer papers have more opportunities to match; this is an explicit limitation.
* **Default hybrid (RRF):** for each paper, sum `1/(60 + rank)` from both rankings. Ranks start at one. The sparse list includes positive BM25 matches only. Dense ranks include every paper. This combines rankings into a single result list.
* **Weighted hybrid:** `alpha * minmax(BM25) + (1-alpha) * minmax(cosine)`. Alpha is selectable. Constant score arrays normalize to zero. Scores are not calibrated probabilities and cannot be compared across modes or queries.
* **Optional reranking:** take the top 50 candidates, then add title query-term coverage times 0.005 for RRF, or 0.05 for other modes. This is a deterministic heuristic, not a learned cross-encoder. It is disabled by default. No claim of improved relevance is made without human relevance judgments.

## Query behavior and GUI

Casefolded alphanumeric tokens provide case insensitivity. Explicit abbreviations expand (NLP, MT, NMT, QA, RAG, LLM, LLMs, NLU, NLG). Unknown words of at least four characters are conservatively corrected against corpus terms appearing in at least two papers using similarity cutoff 0.84; corrections are visible and can be disabled. This heuristic can miss errors or alter rare names.

Double-quoted phrases are mandatory contiguous token matches after case/punctuation/whitespace normalization. Quoted terms are protected from spelling correction, and phrases are matched literally rather than abbreviation-expanded. Thus `"NLP"` requires the literal token NLP, while unquoted NLP expands. Phrase and topic constraints filter the fused ranking. An optional title reranker then reorders the top 50 eligible results.

GUI: query field, four ranking modes including two real hybrid modes, length selector, topic filter, weighted-fusion control, correction/reranking toggles, top 10 unique source papers, title/link, up-to-200-character abstract-based snippet, final score and component scores. Snippets use abstracts for readability; retrieval uses the selected full-text variant. HTML is created using textContent to avoid treating paper text as executable markup. The server binds only to localhost.

## Files and submission

After automatic extraction of `corpus-data.zip`, `data/papers.jsonl` has title, abstract, subtopic, arXiv URLs/version, source page count, original PDF checksum and paths/checksums/word counts for all variants. `data/texts/` contains the full local text dataset. `data/raw_api/` stores the exact API responses. `summary_report.pdf` is generated from actual corpus statistics. `data/audit.json` and `validation.json` record verification results. The archive contains all metadata, all 1,200 text variants, raw API responses, the original build audit and corpus statistics; it excludes large original PDFs.

`ai-logs/phase1/` discloses AI assistance. Review that folder against your course's full AI policy and add the complete exported Codex conversation if required; the programmatic work log is not represented as a complete platform transcript.

The source code is provided for this course project. Original papers retain their authors' rights and individual licenses; an arXiv link is not a blanket redistribution license. No new license is asserted over source papers.

## Live discussion

See `DISCUSSION.md` for the architecture and demonstration checklist. The program contains no hosted inference/API dependency at search time. Do not claim measured retrieval quality: automated checks establish functional behavior, not relevance effectiveness.

## Technical references

- [arXiv API manual](https://info.arxiv.org/help/api/user-manual.html)
- [arXiv API terms and access limits](https://info.arxiv.org/help/api/tou.html)
- [MiniLM model card and mean-pooling example](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
