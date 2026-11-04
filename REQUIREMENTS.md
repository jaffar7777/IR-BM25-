# Requirement-to-evidence checklist

| Assignment item | Implementation / evidence |
|---|---|
| At least 400 arXiv papers | `data/papers.jsonl`, actual count in `data/manifest.json`; `python audit.py` fails below 400 |
| One chosen category | `cs.CL` in every recorded query |
| At least 4 distinct subtopics | 100 papers per keyword-labeled topic; manifest and report tables |
| Title, text, ID/link, label | Every paper record plus `data/texts/` |
| Short, medium, long variants | First 5 pages / separate 7-, 8-, 9-page options / all pages; long sources have >=10 pages |
| Local data | Text files, metadata, raw API responses, original PDFs in local delivery |
| Reproducible query/date range | `collect.py`, `data/manifest.json`, raw responses, versioned URLs, checksums |
| BM25 sparse retrieval | Direct implementation in `engine.py` |
| Embedding-based dense retrieval | Local pretrained MiniLM, passage vectors, cosine/document max |
| Genuine fusion | RRF and weighted-score fusion each produce one combined ranking |
| Spelling correction | Visible optional corpus-vocabulary correction |
| Abbreviation expansion | Explicit dictionary including NLP |
| Case insensitivity | Casefolded tokenization |
| Phrase matching | Double-quoted phrases required as contiguous normalized tokens |
| Search GUI and model selector | `app.py`, local browser interface |
| Top 10 titles, links, snippets, scores | Unique source-paper cards with final and component scores |
| Dataset/code in GitHub | Repository supplied by user: `https://github.com/jaffar7777/IR-BM25-` |
| Corpus-statistics PDF | `summary_report.pdf`, built by `report.py` from actual records |
| AI usage disclosure | `ai-logs/phase1/`, including actual available chat messages |
| Live discussion preparation | `DISCUSSION.md`, setup/run scripts, functional checks |

Important interpretation: derived page excerpts are used for variants. If the instructor requires naturally short, medium and long original papers, this corpus selection must be revised. The course's full AI policy was not supplied; confirm its export requirements. Automated tests verify behavior and integrity, not retrieval relevance.
