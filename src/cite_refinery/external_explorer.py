"""Offline Cytoscape.js explorer export for a candidate Cite-Refinery packet.

Ships an unmodified pinned Cytoscape.js build with license alongside the
generated HTML. Does NOT expose bearer credentials, a hosted API or untrusted
source HTML. Browser-only static navigation; graph structure stays unchanged.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

VENDOR = Path(__file__).resolve().parent / "vendor"


def export_cytoscape_explorer(packet: dict, output_dir: str | Path) -> dict:
    if not isinstance(packet, dict) or not isinstance(packet.get("nodes"), list) or not isinstance(packet.get("edges"), list):
        raise ValueError("expected a semantic graph packet with nodes and edges")
    if len(packet["nodes"]) > 20000 or len(packet["edges"]) > 50000:
        raise ValueError("graph exceeds the browser export safety limit")
    keys = set()
    elements = []
    for n in packet["nodes"]:
        key = n.get("key")
        if not isinstance(key, str) or not key or len(key) > 160 or key in keys:
            raise ValueError("duplicate or invalid packet node key")
        keys.add(key)
        elements.append({"group": "nodes", "data": {
            "id": key, "label": str(n.get("statement") or key)[:300],
            "kind": str(n.get("kind") or "concept")[:80],
            "layer": str(n.get("layer") or "neutral"),
            "clusters": n.get("clusters", [])[:30],
            "refs": [str(x)[:2000] for x in n.get("source_refs", [])[:40]],
            "status": str((n.get("provenance") or {}).get("review_status") or "unreviewed")[:120],
            "reviewer_verdict": str((n.get("provenance") or {}).get("second_pass_verdict") or "not_run")[:90],
            "boundary": str((n.get("provenance") or {}).get("boundary") or "")[:1500],
        }})
    for i, e in enumerate(packet["edges"]):
        if e.get("source") not in keys or e.get("target") not in keys:
            raise ValueError(f"edge {i} has missing endpoint")
        elements.append({"group": "edges", "data": {
            "id": f"edge_{i}", "source": e["source"], "target": e["target"],
            "relation": str(e.get("relation") or "RELATED_TO")[:100],
            "status": str(e.get("status") or "unreviewed")[:100],
            "reviewer_verdict": str((e.get("provenance") or {}).get("second_pass_verdict") or "not_run")[:90],
            "boundary": str((e.get("provenance") or {}).get("boundary") or "")[:1500],
            "refs": [str(x)[:2000] for x in e.get("evidence_refs", [])[:40]],
        }})
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(VENDOR / "cytoscape.min.js", directory / "cytoscape.min.js")
    shutil.copyfile(VENDOR / "CYTO_LICENSE.txt", directory / "CYTO_LICENSE.txt")
    data = json.dumps(elements, ensure_ascii=False, separators=(",", ":"))
    # Avoid script-tag breakout or entity-based HTML parsing tricks.
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page = _HTML.replace("__GRAPH_JSON__", data)
    (directory / "index.html").write_text(page, encoding="utf-8")
    return {
        "path": str(directory / "index.html"),
        "node_count": len(packet["nodes"]), "edge_count": len(packet["edges"]),
        "backend": "Cytoscape.js 3.30.4 (offline bundle)", "data_policy": "static_no_network_or_credentials",
    }


_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; connect-src 'none'; img-src 'none'; object-src 'none'">
<title>Cite-Refinery · Evidence Graph Explorer</title>
<style>
:root{color-scheme:dark;font-family:Inter,system-ui,sans-serif;background:#0c1220;color:#edf3ff}
*{box-sizing:border-box}body{margin:0}header{padding:16px 22px;border-bottom:1px solid #2b3850;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0;font-weight:700;letter-spacing:-.2px}header p{margin:4px 0 0;font-size:12px;color:#adbacd}
#search{background:#151e30;color:#edf3ff;border:1px solid #415574;border-radius:8px;padding:10px 14px;min-width:255px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;height:calc(100vh - 91px)}
#cy{min-width:0;height:100%;background:radial-gradient(circle at center,#15243a,#0c1220 70%)}
aside{padding:20px;border-left:1px solid #2b3850;overflow:auto;min-width:0}
.controls{display:flex;gap:12px;flex-wrap:wrap;padding-top:8px;font-size:12px}
.controls label{cursor:pointer;display:flex;align-items:center;gap:5px}
h2{font-size:17px;line-height:1.35;overflow-wrap:anywhere}dl{font-size:13px;line-height:1.55}
dt{color:#92a5c4;margin-top:14px}dd{margin:4px 0 0;overflow-wrap:anywhere}
a{color:#7db8ff;overflow-wrap:anywhere}li{margin-bottom:7px;line-height:1.4}
.muted{color:#adbacd;font-size:13px}button{background:#243a57;border:1px solid #4b7298;color:#e8f0fc;padding:7px 10px;cursor:pointer;border-radius:6px}
.legend{font-size:12px;color:#adbacd}b.practical{color:#42c2b3}b.academic{color:#a68bfa}b.program{color:#f9ad65}b.neutral{color:#a0aec0}
@media(max-width:860px){.layout{grid-template-columns:1fr;grid-template-rows:60vh auto;height:auto}aside{border-left:0;border-top:1px solid #2b3850}}
</style></head><body>
<header><div><h1>Cite-Refinery · Semantic Evidence Explorer</h1>
<p>Candidate provenance-aware graph · node count <span id="ncount">0</span> · edge count <span id="ecount">0</span></p></div>
<div><input id="search" type="search" aria-label="Search problem modules" placeholder="Search nodes, evidence, source IDs...">
<div class="controls"><label><input class="filter" type="checkbox" value="neutral" checked>Neutral</label>
<label><input class="filter" type="checkbox" value="practical" checked>Practical</label>
<label><input class="filter" type="checkbox" value="academic" checked>Academic</label>
<label><input class="filter" type="checkbox" value="program" checked>Program</label></div></div>
<button id="reset">Fit all</button>
</header><div class="layout"><div id="cy" role="application" aria-label="Interactive evidence graph"></div>
<aside><div class="legend">Node layers: <b class="neutral">neutral</b> · <b class="practical">practical</b> · <b class="academic">academic</b> · <b class="program">program</b></div>
<h2 id="title">Select a node or relationship</h2><p class="muted" id="intro">Click to inspect source references, boundary conditions and candidate relation status. An absent link does not prove real-world absence.</p>
<dl id="detail"></dl><ul id="links"></ul></aside></div>
<script id="graph-data" type="application/json">__GRAPH_JSON__</script>
<script src="cytoscape.min.js"></script>
<script>
"use strict";
const elements = JSON.parse(document.getElementById('graph-data').textContent);
document.getElementById('ncount').textContent = elements.filter(e=>e.group==='nodes').length;
document.getElementById('ecount').textContent = elements.filter(e=>e.group==='edges').length;
const cy=cytoscape({container:document.getElementById('cy'),elements,
 style:[
 {selector:'node',style:{'background-color':'#8994a7','label':'data(label)','font-size':8,'color':'#d9e2f1','text-opacity':0.84,'text-max-width':110,'text-wrap':'ellipsis','text-valign':'bottom','text-margin-y':5,'width':15,'height':15}},
 {selector:'node[layer="practical"]',style:{'background-color':'#42c2b3'}},
 {selector:'node[layer="academic"]',style:{'background-color':'#a68bfa'}},
 {selector:'node[layer="program"]',style:{'background-color':'#f9ad65'}},
 {selector:'edge',style:{'line-color':'#53637d','target-arrow-color':'#53637d','target-arrow-shape':'triangle','curve-style':'bezier','width':1,'opacity':0.65}},
 {selector:'edge[status="candidate"]',style:{'line-style':'dashed','opacity':0.40}},
 {selector:'edge[status="unresolved"]',style:{'line-style':'dotted','line-color':'#edb061','target-arrow-color':'#edb061','width':2,'opacity':0.85}},
 {selector:':selected',style:{'border-width':3,'border-color':'#fff','opacity':1}},
 {selector:'.faded',style:{'opacity':0.04,'text-opacity':0}},
 {selector:'.hidden_layer',style:{'display':'none'}}
 ],layout:{name:'cose',animate:false,randomize:false,nodeRepulsion:120000,idealEdgeLength:110,numIter:500,fit:true,padding:42}
});
document.documentElement.dataset.graphReady='true';
const title=document.getElementById('title'), detail=document.getElementById('detail'), links=document.getElementById('links');
function row(k,v){const dt=document.createElement('dt');dt.textContent=k;const dd=document.createElement('dd');dd.textContent=String(v);detail.append(dt,dd)}
function select(ele){const d=ele.data();title.textContent=d.label||d.relation||d.id;
 detail.replaceChildren();links.replaceChildren();document.getElementById('intro').textContent='Source attribution is not evidence that the relationship is effective or causal.';
 for(const k of ['id','layer','kind','relation','status','reviewer_verdict','clusters','boundary'])if(d[k]!==undefined)row(k,Array.isArray(d[k])?d[k].join(', '):d[k]);
 for(const url of d.refs||[]){const li=document.createElement('li');if(/^https:\/\//i.test(url)){const a=document.createElement('a');a.href=url;a.rel='noopener noreferrer';a.target='_blank';a.textContent=url;li.append(a)}else li.textContent=url;links.append(li)}
}
cy.on('tap','node,edge',evt=>select(evt.target));
const search=document.getElementById('search');
function apply(){const q=search.value.toLowerCase().trim(), show=new Set([...document.querySelectorAll('.filter:checked')].map(el=>el.value));
cy.batch(()=>{cy.nodes().forEach(n=>{n.toggleClass('hidden_layer',!show.has(n.data('layer')));const matches=!q||[n.data('label'),n.data('kind'),...(n.data('refs')||[])].join(' ').toLowerCase().includes(q);n.toggleClass('faded',!matches)});
cy.edges().forEach(e=>{e.toggleClass('hidden_layer',e.source().hasClass('hidden_layer')||e.target().hasClass('hidden_layer'));e.toggleClass('faded',!!q&&(e.source().hasClass('faded')&&e.target().hasClass('faded')))});})}
search.addEventListener('input',apply);document.querySelectorAll('.filter').forEach(el=>el.addEventListener('change',apply));
document.getElementById('reset').addEventListener('click',()=>{search.value='';document.querySelectorAll('.filter').forEach(el=>el.checked=true);apply();cy.fit(undefined,28)});
</script></body></html>
"""
