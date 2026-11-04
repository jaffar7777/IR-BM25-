"""Local browser GUI. No web-framework dependency; listens on loopback only."""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from engine import Engine, ROOT

PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>arXiv Hybrid Search</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f5f6fa;color:#182238;font:16px system-ui,sans-serif}main{max-width:1000px;margin:48px auto;padding:0 24px}small,.muted{color:#637087}h1{font-size:40px;letter-spacing:-1.5px;margin:8px 0}header{margin-bottom:28px}.badge{background:#e1e8ff;color:#344b9b;padding:5px 10px;border-radius:18px;font-size:12px}.panel,article{background:white;border:1px solid #dce2eb;border-radius:14px;padding:22px;margin:14px 0;box-shadow:0 3px 10px #15213a05}form{display:flex;gap:10px}input[type=search]{flex:1;min-width:0;padding:14px;border:1px solid #a9b5c9;border-radius:8px;font-size:17px}button{background:#314fbc;color:white;border:0;border-radius:8px;padding:12px 24px;font-size:16px;cursor:pointer}button:disabled{opacity:.6}.options{display:flex;gap:16px;flex-wrap:wrap;margin-top:16px}label{font-size:13px;color:#526078}select{display:block;margin-top:5px;padding:8px;border:1px solid #cbd3df;border-radius:6px;background:white}a{color:#294bb2;text-decoration:none}a:hover{text-decoration:underline}h2{font-size:19px;margin:0 0 10px}.score{float:right;font-size:13px;color:#344b9b;background:#eef2ff;border-radius:6px;padding:5px;margin-left:14px}.snippet{line-height:1.65;font-size:15px}.meta{font-size:12px;color:#667289}#status{white-space:pre-wrap;line-height:1.6}footer{font-size:12px;color:#68758a;margin:32px 0}summary{cursor:pointer}details{margin-top:12px;font-size:13px}@media(max-width:600px){main{margin:24px auto}h1{font-size:30px}form{flex-direction:column}}
</style><main><header><span class="badge">PHASE 1 · COMPUTATIONAL LINGUISTICS</span><h1>arXiv Hybrid Search</h1><div class="muted">Find research through lexical and semantic retrieval.</div></header>
<section class="panel"><form id="search"><input id="query" type="search" required maxlength="500" placeholder='Try: NLP summarization or "machine translation"' aria-label="Search query"><button id="button">Search</button></form>
<div class="options"><label>Ranking<select id="mode"><option value="rrf">Hybrid · Reciprocal Rank Fusion</option><option value="weighted">Hybrid · Weighted scores</option><option value="bm25">BM25 only</option><option value="dense">Dense only</option></select></label>
<label>Document variant<select id="variant"><option value="long">Long · full paper</option><option value="medium">Medium · first 8 pages</option><option value="short">Short · first 5 pages</option></select></label>
<label>Subtopic<select id="topic"><option value="all">All subtopics</option><option value="machine_translation">Machine translation</option><option value="question_answering">Question answering</option><option value="summarization">Summarization</option><option value="dialogue_systems">Dialogue systems</option></select></label>
<label>BM25 weight<select id="alpha"><option value="0.5">50% (weighted fusion)</option><option value="0.25">25%</option><option value="0.75">75%</option></select></label></div>
<div class="options"><label><input id="correct" type="checkbox" checked> Correct spelling</label><label><input id="rerank" type="checkbox"> Rerank top 50 by title coverage</label></div>
<details><summary>How search works</summary><p>Queries ignore case. Known abbreviations expand automatically. Put exact phrases in double quotes; those phrases must occur in the selected text variant. RRF adds 1/(60 + rank) from both rankings. Weighted fusion combines min-max normalized scores. Optional reranking adds a small title-term coverage bonus; it is a heuristic, not a trained model. Scores are ranking values, not probabilities.</p></details></section>
<p id="status" role="status">Ready. Search across locally stored papers.</p><section id="results" aria-label="Search results"></section><footer>Original papers remain linked to arXiv. Short and medium variants are source-page excerpts, not rewritten papers.</footer></main>
<script>
const $=id=>document.getElementById(id);function element(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
$('search').addEventListener('submit',async event=>{event.preventDefault();$('button').disabled=true;$('status').textContent='Searching…';$('results').replaceChildren();const start=performance.now();try{const response=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:$('query').value,mode:$('mode').value,variant:$('variant').value,topic:$('topic').value,alpha:Number($('alpha').value),correct:$('correct').checked,rerank:$('rerank').checked})});const data=await response.json();if(!response.ok)throw Error(data.error);$('status').textContent=`${data.results.length} results · ${((performance.now()-start)/1000).toFixed(2)} seconds\nProcessed query: ${data.query}`+(data.changes.length?'\nChanges: '+data.changes.join('; '):'')+(data.phrases?.length?'\nRequired phrases: '+data.phrases.join('; '):'');if(!data.results.length)$('status').textContent+='\nNo matching papers. Try fewer terms or remove phrase constraints.';data.results.forEach((r,i)=>{const card=element('article');card.append(element('span','score',r.score.toFixed(5)));const heading=element('h2');const link=element('a','',`${i+1}. ${r.title}`);link.href=r.url;link.target='_blank';link.rel='noopener noreferrer';heading.append(link);card.append(heading,element('div','meta',`${r.arxiv_id} · ${r.subtopic.replaceAll('_',' ')}`),element('p','snippet',r.snippet),element('div','meta',`BM25 ${r.bm25.toFixed(3)} · dense cosine ${r.dense.toFixed(3)}`));$('results').append(card);});}catch(error){$('status').textContent='Search failed: '+error.message;}finally{$('button').disabled=false;}});
</script></html>'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8501)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    print('Loading local corpus and embedding model...', flush=True)
    engine = Engine()
    lock = threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path == '/':
                self.reply(200, PAGE.encode(), 'text/html; charset=utf-8')
            elif self.path == '/api/health':
                self.reply(200, json.dumps({'papers': len(engine.papers), 'status': 'ready'}).encode(), 'application/json')
            else:
                self.reply(404, b'Not found', 'text/plain')
        def do_POST(self):
            if self.path != '/api/search':
                self.reply(404, b'Not found', 'text/plain')
                return
            try:
                length = int(self.headers.get('Content-Length', 0))
                if length < 1 or length > 5000:
                    raise ValueError('Invalid request length')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data.get('query'), str) or len(data['query']) > 500:
                    raise ValueError('Query must be at most 500 characters')
                if data.get('variant', 'long') not in ['short', 'medium', 'long']:
                    raise ValueError('Invalid variant')
                if not 0 <= float(data.get('alpha', .5)) <= 1:
                    raise ValueError('Weight must be between 0 and 1')
                with lock:
                    result = engine.search(**data)
                self.reply(200, json.dumps(result).encode(), 'application/json')
            except Exception as exc:
                self.reply(400, json.dumps({'error': str(exc)}).encode(), 'application/json')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{args.port}'
    print(f'Ready: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()
