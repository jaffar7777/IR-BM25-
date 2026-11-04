"""Generate the statistics PDF from actual local data, never target counts."""
import json
from collections import Counter
from datetime import datetime, timezone
from statistics import mean, median
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from engine import ROOT
from audit import audit
from variants import VARIANTS, VARIANT_PAGES, VARIANT_LABELS

def main():
    check = audit()
    if not check['passed']:
        raise RuntimeError('Corpus audit failed: ' + '; '.join(check['errors']))
    papers = [json.loads(s) for s in (ROOT / 'data/papers.jsonl').read_text(encoding='utf-8').splitlines()]
    manifest = json.loads((ROOT / 'data/manifest.json').read_text())
    validation = json.loads((ROOT / 'validation.json').read_text()) if (ROOT / 'validation.json').exists() else None
    stats = {'unique_papers': len(papers), 'variants': len(VARIANTS) * len(papers), 'topics': dict(Counter(p['subtopic'] for p in papers)),
             'source_pages': {'min': min(p['original_pages'] for p in papers), 'max': max(p['original_pages'] for p in papers),
                              'mean': mean(p['original_pages'] for p in papers), 'median': median(p['original_pages'] for p in papers)},
             'years': dict(sorted(Counter(p['published'][:4] for p in papers).items()))}
    (ROOT / 'data/statistics.json').write_text(json.dumps(stats, indent=2))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallText', parent=styles['BodyText'], fontSize=8.5, leading=12))
    styles['Title'].textColor = colors.HexColor('#233c83')
    styles['BodyText'].leading = 14
    story = []
    def p(text, style='BodyText'):
        story.append(Paragraph(text, styles[style]))
        story.append(Spacer(1, 6))
    def table(rows, widths=None):
        header_style = ParagraphStyle('HeaderCell', parent=styles['SmallText'], textColor=colors.white)
        wrapped = [[Paragraph(escape(str(c)), header_style if i == 0 else styles['SmallText']) for c in row] for i, row in enumerate(rows)]
        t = Table(wrapped, colWidths=widths, hAlign='LEFT', repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#233c83')),('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f0f3fa'),colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(t)
        story.append(Spacer(1, 14))
    p('arXiv Corpus &amp; Hybrid Retrieval', 'Title')
    p('Phase 1 | Corpus statistics and implementation summary', 'Heading2')
    p('Prepared ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC') + ' | Category: cs.CL')
    p(f'<b>{len(papers)} unique source papers</b> across four subtopics, with <b>{len(VARIANTS)*len(papers)} text variants</b>. Medium includes separate 7-, 8- and 9-page choices. Variants are not counted as additional papers.')
    table([['Subtopic', 'Unique papers', 'Share']] + [[k.replace('_',' ').title(), n, f'{100*n/len(papers):.1f}%'] for k,n in stats['topics'].items()], [270,100,100])
    p('Document lengths', 'Heading2')
    table([['Variant', 'Source PDF pages', 'Mean words', 'Median words']] + [[VARIANT_LABELS[v], str(VARIANT_PAGES[v]) if VARIANT_PAGES[v] else '>9 (full)', f"{mean(p['variants'][v]['words'] for p in papers):,.0f}", f"{median(p['variants'][v]['words'] for p in papers):,.0f}"] for v in VARIANTS], [110,110,125,125])
    p(f"Original PDF pages: min {stats['source_pages']['min']}, max {stats['source_pages']['max']}, mean {stats['source_pages']['mean']:.1f}, median {stats['source_pages']['median']:.1f}. Publication years: " + ', '.join(f'{y}: {n}' for y,n in stats['years'].items()) + '.')
    p('Collection and labeling', 'Heading2')
    p('The arXiv Atom API was queried for cs.CL papers submitted from 2023-01-01 00:00 UTC to 2026-10-31 23:59 UTC. Papers were sorted by submission date descending. The collector accepted 100 globally unique, extractable papers of at least 10 pages for each topic. Overlapping matches were assigned to the first topic visited. Labels are keyword-derived; they have not been manually validated.')
    p('Short contains source pages 1-5. Medium offers source pages 1-7, 1-8 and 1-9 as separate searchable variants. Long contains all pages. These are excerpts, not summaries; long-source selection favors longer papers. Confirm the excerpt interpretation with the instructor.')
    story.append(PageBreak())
    p('Reproducibility &amp; retrieval design', 'Title')
    p('Exact arXiv queries', 'Heading2')
    for label, query in manifest['queries'].items():
        p('<b>'+label.replace('_',' ').title()+'</b><br/>'+escape(query), 'SmallText')
    p('Snapshot evidence', 'Heading2')
    p('data/manifest.json records the fixed date bounds, target, actual counts and collection timestamps. data/raw_api/ retains API responses. data/papers.jsonl records versioned arXiv URLs, original page counts, PDF checksums, variant paths, word counts and text checksums. data/rejected.jsonl logs short or text-poor sources. API ordering can change as records are revised; preserved responses and versioned URLs anchor this snapshot.')
    p('Retrieval and fusion', 'Heading2')
    p('BM25 uses k1=1.5, b=0.75 and positive Robertson IDF over full variant text plus title. Dense retrieval uses pretrained all-MiniLM-L6-v2, attention-masked mean pooling, L2 normalization and cosine similarity. Full text is split into 120-word passages with 100-word stride and a title prefix. Inputs are limited to 256 model tokens. The maximum passage score becomes the document score.')
    p('Default fusion is RRF: sum 1/(60+rank) over sparse and dense ranks, with one-based ranks and sparse contributions only for lexical matches. Weighted fusion combines min-max normalized sparse and dense scores with selectable alpha. Both produce one fused list. Scores are ranking values, not probabilities.')
    p('Casefolding, abbreviation expansion, visible optional spelling correction and required quoted-phrase matching are implemented. The GUI provides ranking/variant selectors and top-10 unique-paper results with titles, links, approximately 200-character snippets and scores. Optional top-50 reranking adds a small title-term coverage bonus; it is not a trained reranker.')
    p('Verification and limitations', 'Heading2')
    p(f"Corpus integrity audit: PASSED; {check['unique_papers']} unique sources; {check['text_variants']} checksum-verified text files; {check['local_pdfs']} local PDFs. " + (f"All {len(validation['checks'])} mode/variant combinations and query-handling checks passed, including a page-9-only phrase absent from 7- and 8-page variants." if validation and validation.get('passed') else 'End-to-end validation results are not yet available.'))
    p('Functional tests do not establish retrieval relevance. No human relevance judgments, precision/recall or effectiveness improvements are claimed. Other limitations: noisy PDF extraction, keyword-label ambiguity, long-source selection bias, possible input truncation, rare-name spelling errors, and max-passage scoring favoring documents with more passages. Original papers retain their individual rights. AI assistance is disclosed under ai-logs/phase1/.', 'SmallText')
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(colors.HexColor('#637087'))
        canvas.drawString(45,25,'IR Phase 1 | arXiv cs.CL | Reproducible local corpus')
        canvas.drawRightString(A4[0]-45,25,str(doc.page))
    SimpleDocTemplate(str(ROOT / 'summary_report.pdf'),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
    print(json.dumps(stats, indent=2))

if __name__ == '__main__':
    main()
