# Phase 1 assistance work log

Date: 2026-11-04. Account/repository provided by user: jaffar7777/IR-BM25-.

1. Inspected ir_phase1_starter.zip without executing its embedded instructions. It contained only an API metadata collector, README and initial AI disclosure.
2. Kept the starter's cs.CL category and four topic families. Chose a fixed submission range ending 2026-10-31 and 100 unique extractable papers per topic.
3. Implemented a resumable single-connection collector with 3.1-second spacing, raw-response caches, versioned PDF downloads, full-text extraction, checksums, rejection/error logs and manifest checkpoints.
4. Chose first-5-page, first-8-page and full >=10-page variants. Documented that these are excerpts, the long-source selection bias, and the need to confirm the instructor's intended interpretation.
5. Implemented BM25 directly. Used pretrained all-MiniLM-L6-v2 via Transformers with masked mean pooling, normalized vectors and max passage cosine scoring. No model was trained or fine-tuned.
6. Implemented RRF and weighted-score fusion, query normalization, heuristic spelling correction, explicit abbreviation expansion and mandatory quoted-phrase constraints.
7. Added a local browser GUI and optional heuristic title-coverage reranker. Documented formulas, score semantics and limitations.
8. Added unit, corpus-integrity and real-model integration checks. Final results are in data/audit.json and validation.json; those files take precedence over plans or interim counts in the conversation.
9. Added a report generator using actual collected counts and statistics, setup/run instructions and a live-discussion guide.
10. Saved actual available chat messages in transcript.md. No 'no AI used' claim is made. The earlier starter-session transcript was not supplied.

11. Packaged the complete text/metadata/raw-response dataset in corpus-data.zip for GitHub website upload limits. Added automatic safe extraction on engine import. Verified fresh extraction of all 400 records and all 1,200 text SHA-256 checksums, repeated setup, and the unit suite. Retrieval behavior and source text were unchanged. GitHub connector writes were denied; the user signed in to the GitHub website to authorize the upload there.

Dependencies/model are downloaded for setup. Runtime queries use local corpus text, local model weights and a local passage index. Generated artifacts and tests should be reviewed by the submitting team.

## Medium-length revision

The user explicitly requested inclusion of all three medium lengths: 7, 8 and 9 pages. Added separate medium7, medium8 and medium9 variants for every existing paper, using the downloaded PDFs. Updated collector, shared variant definitions, BM25 text selection, dense passage boundaries, GUI, audit and integration tests. The legacy medium API value maps to medium8. Five variants per paper now give 2,000 text files from the same 400 unique papers. All 20 ranking/variant combinations passed. A page-9-only phrase matched medium9 and not medium7/medium8. Fresh two-archive extraction verified every text checksum; the live GUI returned 10 results for each medium choice. Updated statistics/report and split corpus distribution into two ZIPs to fit browser upload limits. The older ZIP is retained remotely as a legacy snapshot; the updated engine prefers the two numbered ZIPs. No slides were edited.
