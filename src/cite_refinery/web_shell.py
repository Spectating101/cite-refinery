from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .store import JsonStore
from .workspace import ProductWorkspace


APP_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Cite-Refinery</title>
<style>
:root{
  --bg:#f3f1eb;--paper:#fffef9;--ink:#1c201d;--muted:#6f746f;--line:#d9d6cd;
  --dark:#20241f;--soft:#ebe8df;--accent:#6c7454;
  --p:#7b6448;--pbg:#f3ece2;--a:#4c6578;--abg:#eaf0f4;--s:#5d7057;--sbg:#eaf0e7;
}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
button,input{font:inherit}.shell{display:grid;grid-template-columns:270px 1fr;min-height:100vh}.side{background:var(--dark);color:#eee;padding:22px 16px;position:sticky;top:0;height:100vh;overflow:auto}
.brand{font-size:20px;font-weight:780;letter-spacing:-.035em}.brand small{display:block;color:#9fa596;font-size:10px;text-transform:uppercase;letter-spacing:.12em;margin-top:2px}.label{margin:26px 8px 8px;color:#8f9587;font-size:10px;text-transform:uppercase;letter-spacing:.12em}
.project{width:100%;border:0;background:transparent;color:#d9ddd4;padding:10px;border-radius:8px;text-align:left;cursor:pointer;margin:2px 0}.project:hover,.project.active{background:#343a32;color:white}.project strong,.project span{display:block}.project span{font-size:11px;color:#969d90;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.main{min-width:0}.head{padding:28px 34px 0}.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:.12em;font-weight:750;color:#7b6448}.head h1{font-size:32px;letter-spacing:-.045em;margin:6px 0}.problem{max-width:950px;color:var(--muted)}
.nav{display:flex;gap:2px;padding:20px 34px 0;border-bottom:1px solid var(--line)}.nav button{border:0;background:transparent;padding:11px 14px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;text-transform:capitalize}.nav button.active{color:var(--ink);font-weight:750;border-color:var(--accent)}
.content{padding:24px 34px 60px;max-width:1580px}.grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}.two{grid-template-columns:minmax(250px,.7fr) minmax(0,1.8fr)}.three{grid-template-columns:repeat(3,minmax(0,1fr))}
.card,.metric{background:var(--paper);border:1px solid var(--line);border-radius:11px}.card{padding:16px}.metric{padding:14px}.metric b{display:block;font-size:25px;letter-spacing:-.04em}.metric span{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
h2{font-size:21px;margin:0 0 12px}h3{font-size:14px;margin:0 0 9px}.muted,.meta{color:var(--muted)}.meta{font-size:11px;margin-top:4px}.pill{display:inline-block;background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:2px 7px;font-size:10px;margin:2px 3px 2px 0}.empty{padding:22px;border:1px dashed var(--line);border-radius:9px;text-align:center;color:var(--muted)}
.topline{display:flex;justify-content:space-between;gap:18px;align-items:flex-end;margin-bottom:14px}.topline p{margin:0;color:var(--muted);font-size:11px;max-width:520px;text-align:right}.boundary{border-left:3px solid var(--line);padding-left:10px;color:var(--muted);font-size:11px;margin-top:12px}
.cluster-search,.node-search{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:white}.cluster-list{display:grid;gap:7px;margin-top:10px;max-height:72vh;overflow:auto}.cluster-button{width:100%;text-align:left;border:1px solid var(--line);background:var(--paper);border-radius:9px;padding:10px;cursor:pointer}.cluster-button:hover,.cluster-button.active{border-color:#8d917e;box-shadow:0 0 0 1px #8d917e inset}.cluster-button strong{display:block}.cluster-presence{display:flex;gap:5px;margin-top:7px}.dot{font-size:9px;border-radius:999px;padding:2px 6px;border:1px solid var(--line);opacity:.42}.dot.on{opacity:1}.dot.p{background:var(--pbg);color:var(--p)}.dot.a{background:var(--abg);color:var(--a)}.dot.s{background:var(--sbg);color:var(--s)}
.module-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.module-head h2{margin-bottom:4px}.missing{color:#8b5c42;font-size:11px}.layer-board{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.layer-col{border:1px solid var(--line);border-radius:11px;min-width:0;overflow:hidden;background:var(--paper)}.layer-title{padding:11px 12px;border-bottom:1px solid var(--line);font-size:12px;font-weight:780;text-transform:uppercase;letter-spacing:.08em}.layer-title.p{background:var(--pbg);color:var(--p)}.layer-title.a{background:var(--abg);color:var(--a)}.layer-title.s{background:var(--sbg);color:var(--s)}.layer-body{padding:9px;display:grid;gap:8px;max-height:560px;overflow:auto}.node{width:100%;text-align:left;border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px;cursor:pointer}.node:hover,.node.active{border-color:#929785}.node strong{display:block;font-size:12px;line-height:1.35}.node .meta{word-break:break-word}.neutral{padding:11px 12px;border:1px solid var(--line);background:#f8f6f0;border-radius:9px;margin-top:12px}.neutral strong{display:block;margin-bottom:5px}
.lower{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(310px,.65fr);gap:14px;margin-top:14px}.row{padding:10px 0;border-top:1px solid var(--line)}.row:first-child{border-top:0;padding-top:0}.relation{font:10px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:3px 5px;border-radius:4px;display:inline-block;margin:2px}.edge{padding:9px 0;border-top:1px solid var(--line)}.edge:first-child{border-top:0}.edge-line{font-size:12px}.edge-line .rel{font:10px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:2px 5px;border-radius:4px;margin:0 5px}.inspector{position:sticky;top:18px}.source{font-size:10px;color:var(--muted);word-break:break-all;margin-top:3px}
.source a{color:#395f82;text-decoration:underline}.trace{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
.trace-group{border-top:1px solid var(--line);padding:9px 0}.trace-group:first-child{border-top:0}
.trace-path{background:#f8f7f3;border:1px solid var(--line);border-radius:7px;padding:8px;margin:7px 0;font-size:11px}
.trace-step{display:block;margin:4px 0;padding:4px 0;border-top:1px dashed var(--line)}
.trace-step:first-child{border-top:0}.trace-target{border:0;background:transparent;padding:0;text-align:left;text-decoration:underline;cursor:pointer;color:#33556d;font-weight:600}
.trace-warning{font-size:11px;color:#985d3a}.provenance{margin-top:8px;font-size:11px;color:var(--muted)}
.provenance pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f3ed;border-radius:7px;padding:9px;font:10px/1.5 ui-monospace,monospace;color:var(--ink)}
.module-actions{margin:9px 0}.export-button,.cluster-filter{padding:7px 11px;border:1px solid var(--line);border-radius:7px;background:var(--paper);cursor:pointer;font-size:11px}
.export-button:hover{border-color:var(--accent)}
.layer-mini{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:10px 0}.layer-mini div{border:1px solid var(--line);border-radius:7px;padding:7px}.layer-mini b{display:block;font-size:10px;text-transform:uppercase}.layer-mini span{font-size:10px;color:var(--muted)}
.record-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.record-col .record-title{font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;margin-bottom:10px}.record-title.p{color:var(--p)}.record-title.a{color:var(--a)}.record-title.s{color:var(--s)}.table{width:100%;border-collapse:collapse}.table td,.table th{text-align:left;vertical-align:top;border-bottom:1px solid var(--line);padding:7px}.table th{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}.scroll{overflow:auto}
@media(max-width:1100px){.layer-board,.record-grid{grid-template-columns:1fr}.lower,.two{grid-template-columns:1fr}.inspector{position:relative}.layer-body{max-height:none}}
@media(max-width:760px){.shell{grid-template-columns:1fr}.side{position:relative;height:auto}.head,.content,.nav{padding-left:18px;padding-right:18px}.topline{display:block}.topline p{text-align:left;margin-top:6px}.three{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand">Cite-Refinery<small>clustered research map</small></div>
    <div class="label">Projects</div><div id="projects"></div>
  </aside>
  <main class="main">
    <header class="head"><div class="eyebrow">Three-layer semantic workspace</div><h1 id="title">Loading…</h1><div class="problem" id="problem"></div></header>
    <nav class="nav" id="nav"></nav>
    <section class="content" id="content"><div class="empty">Loading…</div></section>
  </main>
</div>
<script>
const state={projects:[],project:null,view:'map',clusterId:null,clusterQuery:'',nodeId:null,coverage:null,trace:null,clusterFilter:'all'};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString();
async function api(path){const r=await fetch(path);if(!r.ok)throw new Error(await r.text());return r.json()}
function pill(v){return v?`<span class="pill">${esc(v)}</span>`:''}
function metric(label,value){return `<div class="metric"><b>${fmt(value)}</b><span>${esc(label)}</span></div>`}
function empty(text){return `<div class="empty">${esc(text)}</div>`}
function presence(c){return `<div class="cluster-presence"><span class="dot p ${c.layer_presence.practical?'on':''}">P ${fmt(c.layer_counts.practical)}</span><span class="dot a ${c.layer_presence.academic?'on':''}">A ${fmt(c.layer_counts.academic)}</span><span class="dot s ${c.layer_presence.program?'on':''}">S ${fmt(c.layer_counts.program)}</span></div>`}
function renderProjects(){
  $('#projects').innerHTML=state.projects.map(p=>`<button class="project ${state.project?.project?.id===p.id?'active':''}" data-project="${esc(p.id)}"><strong>${esc(p.title)}</strong><span>${esc(p.problem||'')}</span></button>`).join('')||'<div class="muted">No projects.</div>';
  document.querySelectorAll('[data-project]').forEach(b=>b.onclick=()=>loadProject(b.dataset.project));
}
function renderNav(){
  const nav=state.project?.navigation||['map','records','project'];
  $('#nav').innerHTML=nav.map(v=>`<button class="${state.view===v?'active':''}" data-view="${esc(v)}">${esc(v)}</button>`).join('');
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{state.view=b.dataset.view;state.nodeId=null;state.coverage=null;state.trace=null;renderNav();renderContent()});
}
function nodeButton(n){return `<button class="node ${state.nodeId===n.id?'active':''}" data-node="${esc(n.id)}"><strong>${esc(n.statement)}</strong><div class="meta">${pill(n.kind)}${(n.tags||[]).slice(0,3).map(pill).join('')}</div></button>`}
function edgeRow(e,nodes){const s=nodes[e.source_id]?.statement||e.source_id,t=nodes[e.target_id]?.statement||e.target_id;return `<div class="edge"><div class="edge-line">${esc(s)} <span class="rel">${esc(e.relation)}</span> ${esc(t)}</div><div class="meta">${pill(e.status)} ${(e.evidence_refs||[]).slice(0,2).map(x=>esc(x)).join(' · ')}</div></div>`}
function sourceLink(ref){
  const v=String(ref||'');
  let href=null;
  try{
    if(/^https?:\/\//i.test(v)){const u=new URL(v);if(['https:','http:'].includes(u.protocol))href=u.href}
    else if(/^doi:10\.[0-9]{4,9}\/[a-z0-9._;()/:-]+$/i.test(v))href='https://doi.org/'+encodeURI(v.slice(4));
  }catch(err){}
  return href?'<a href="'+esc(href)+'" target="_blank" rel="noopener noreferrer">'+esc(v)+'</a>':esc(v);
}
function sources(refs){
  return (refs||[]).map(ref=>'<div class="source">'+sourceLink(ref)+'</div>').join('');
}
function receiptDetails(receipts,label='Provenance receipts'){
  if(!receipts?.length)return '';
  return '<details class="provenance"><summary>'+esc(label)+' ('+fmt(receipts.length)+')</summary><pre>'+esc(JSON.stringify(receipts,null,2))+'</pre></details>';
}
function tracePath(path){
  const chain=path.nodes||[],steps=path.steps||[];
  const lead=chain[0];
  return '<div class="trace-path"><div><strong>'+esc(lead?.statement||'')+'</strong></div>'+
    steps.map((step,i)=>'<div class="trace-step"><div><span class="relation">'+esc(step.direction==='reverse'?'← '+step.relation:step.relation+' →')+'</span> '+
      pill(step.status)+' '+(step.status==='qualified'?'<span class="trace-warning">Qualified relation</span>':'')+'</div>'+
      '<button class="trace-target" data-trace-node="'+esc(chain[i+1].id)+'">'+esc(chain[i+1].statement)+'</button>'+
      sources(step.evidence_refs)+receiptDetails(step.provenance_receipts,'Edge provenance')+'</div>').join('')+
    (path.has_qualification?'<div class="trace-warning">This represented path includes qualifications.</div>':'')+
    '</div>';
}
function inspector(){
  const c=state.coverage;if(!c)return '<div class="card inspector"><h3>Node inspector</h3><div class="muted">Select a Practical, Academic, Program or neutral node. Typed paths and provenance are inspectable without AI. No AI call is required.</div></div>';
  const t=state.trace||{},paths=t.paths||{};
  const group=layer=>{
    const rows=paths[layer]||[];
    return '<div class="trace-group"><strong>'+esc(layer.toUpperCase())+'</strong>'+
      (rows.length?rows.map(tracePath).join(''):'<div class="muted">No asserted/qualified path represented within '+fmt(t.max_depth)+' steps.</div>')+'</div>';
  };
  const blocked=t.blocked_or_proposed_edges||[];
  return '<div class="card inspector"><div class="eyebrow">Trace this node</div><h3>'+esc(c.node.statement)+'</h3><div>'+pill(c.node.layer)+pill(c.node.kind)+'</div>'+
    '<div class="layer-mini">'+['practical','academic','program'].map(l=>'<div><b>'+esc(l)+'</b><span>'+((paths[l]||[]).length?'connected':'no path within depth')+'</span></div>').join('')+'</div>'+
    '<div class="row"><strong>Evidence sources</strong>'+sources(c.node.source_refs)+receiptDetails(c.node.provenance_receipts,'Node provenance')+'</div>'+
    '<div class="trace"><h3>Represented typed paths · maximum '+fmt(t.max_depth)+' edges</h3>'+
    ['practical','academic','program'].map(group).join('')+
    (blocked.length?'<details class="provenance"><summary>Candidate / unresolved / missing edges ('+fmt(blocked.length)+')</summary>'+
      blocked.map(e=>'<div class="edge">'+pill(e.relation)+pill(e.status)+sources(e.evidence_refs)+receiptDetails(e.provenance_receipts,'Edge provenance')+'</div>').join('')+'</details>':'')+
    '<div class="boundary">'+esc(t.boundary||c.boundary)+'</div></div></div>';
}
function exportCluster(){
  const project=state.project,atlas=project?.atlas,c=atlas?.clusters?.find(v=>v.id===state.clusterId);
  if(!c)return;
  const graph=project.graph_export||{},nodes=graph.nodes||{};
  const neighborIds=new Set((c.cross_edges||[]).flatMap(e=>[e.source_id,e.target_id]).filter(id=>!c.node_ids.includes(id)));
  const packet={
    schema:'cite_refinery.cluster_audit_export.v1',
    exported_at:new Date().toISOString(),
    project:{id:project.project.id,title:project.project.title},
    cluster:c,
    member_nodes:c.node_ids.map(id=>nodes[id]).filter(Boolean),
    cross_cluster_neighbor_nodes:[...neighborIds].sort().map(id=>nodes[id]).filter(Boolean),
    authority_layers:['practical','academic','program'],
    boundary:atlas.boundary,
  };
  const data=new Blob([JSON.stringify(packet,null,2)],{type:'application/json'});
  const url=URL.createObjectURL(data);
  const a=document.createElement('a');a.href=url;a.download='cite-refinery-cluster-'+c.id.replace(/[^a-z0-9_-]/gi,'_')+'.json';
  document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function renderMap(){
  const atlas=state.project.atlas||{clusters:[],summary:{}};let clusters=atlas.clusters||[];const q=state.clusterQuery.toLowerCase().trim();if(q)clusters=clusters.filter(c=>(`${c.title} ${(c.tags||[]).join(' ')} ${c.intersection}`).toLowerCase().includes(q));
  if(state.clusterFilter==='all-three')clusters=clusters.filter(c=>c.intersection==='practical_academic_program');
  else if(state.clusterFilter.startsWith('missing-'))clusters=clusters.filter(c=>c.missing_layers.includes(state.clusterFilter.slice(8)));
  if(!state.clusterId||!clusters.some(c=>c.id===state.clusterId))state.clusterId=clusters.find(c=>c.node_count>0)?.id||clusters[0]?.id||null;
  const c=atlas.clusters.find(x=>x.id===state.clusterId)||null;
  const exp=state.project.graph_export||{};const nodes=exp.nodes||{};
  const left=`<div><label class="meta" for="clusterFilter">Structural filter</label><select class="cluster-filter" id="clusterFilter">
    <option value="all" ${state.clusterFilter==='all'?'selected':''}>All modules</option>
    <option value="all-three" ${state.clusterFilter==='all-three'?'selected':''}>All three layers</option>
    <option value="missing-practical" ${state.clusterFilter==='missing-practical'?'selected':''}>Practical not represented</option>
    <option value="missing-academic" ${state.clusterFilter==='missing-academic'?'selected':''}>Academic not represented</option>
    <option value="missing-program" ${state.clusterFilter==='missing-program'?'selected':''}>Program not represented</option>
    </select><input class="cluster-search" id="clusterSearch" placeholder="Find a semantic module…" value="${esc(state.clusterQuery)}"><div class="cluster-list">${clusters.length?clusters.map(x=>`<button class="cluster-button ${c?.id===x.id?'active':''}" data-cluster="${esc(x.id)}"><strong>${esc(x.title)}</strong><div class="meta">${esc(x.intersection)} · ${fmt(x.node_count)} nodes</div>${presence(x)}</button>`).join(''):empty('No matching modules.')}</div></div>`;
  if(!c)return `<div class="grid two">${left}${empty('No modules match the current search and structural filter.')}</div>`;
  const anchors=c.neutral_nodes||[];const missing=c.missing_layers||[];
  const board=`<div class="layer-board">${[['practical','p','Practical'],['academic','a','Academic'],['program','s','Program']].map(([key,cls,label])=>`<section class="layer-col"><div class="layer-title ${cls}">${label} · ${fmt((c.layers[key]||[]).length)}</div><div class="layer-body">${(c.layers[key]||[]).length?(c.layers[key]||[]).map(nodeButton).join(''):empty('Nothing represented in this layer yet.')}</div></section>`).join('')}</div>`;
  const center=`<div><div class="module-head"><div><div class="eyebrow">Semantic module</div><h2>${esc(c.title)}</h2><div class="meta">${pill(c.intersection)}${(c.tags||[]).map(pill).join('')}</div><div class="module-actions"><button class="export-button" id="exportCluster">Export module evidence · JSON</button></div></div><div class="missing">${missing.length?`Current map is missing: ${missing.map(esc).join(', ')}`:'All three layers are represented.'}</div></div>${anchors.length?`<div class="neutral"><strong>Module anchors / neutral concepts</strong>${anchors.map(nodeButton).join('')}</div>`:''}${board}<div class="lower"><div><div class="card"><h3>Typed relations inside this module</h3>${c.internal_edges.length?c.internal_edges.slice(0,100).map(e=>edgeRow(e,nodes)).join(''):empty('No internal typed relations represented yet.')}<div class="meta" style="margin-top:9px">${fmt(c.cross_edge_count)} cross-module edges · ${fmt(c.unresolved_or_missing.length)} unresolved/candidate · ${fmt(c.contradictions.length)} contradictions</div></div><div class="boundary">${esc(atlas.boundary)}</div></div>${inspector()}</div></div>`;
  return `<div class="topline"><div><div class="eyebrow">Core product view</div><h2>Clustered three-layer map</h2></div><p>Modules are mapped across Practical, Academic, and Program evidence/supply. The rest of the product hangs from these nodes.</p></div><div class="grid metrics">${metric('Semantic modules',atlas.summary.cluster_count)}${metric('P + A + S modules',atlas.summary.three_layer_clusters)}${metric('Practical represented',atlas.summary.clusters_represented_by_layer?.practical)}${metric('Academic represented',atlas.summary.clusters_represented_by_layer?.academic)}${metric('Program represented',atlas.summary.clusters_represented_by_layer?.program)}${metric('Unclustered nodes',atlas.summary.unclustered_node_count)}</div><div class="grid two" style="margin-top:14px">${left}${center}</div>`;
}
function renderRecords(){
  const s=state.project.sections,p=s.practical,a=s.academic,g=s.program,x=s.execution;
  const observations=(p.observations||[]).slice(0,80),briefs=(a.briefs||[]).slice(0,80),requirements=(g.requirements||[]).slice(0,80),caps=(g.capabilities||[]).slice(0,80);
  return `<div class="topline"><div><div class="eyebrow">Supporting records</div><h2>Source-side material</h2></div><p>These records feed the map. They remain separate authorities rather than being merged into one undifferentiated evidence pool.</p></div><div class="record-grid"><div class="card record-col"><div class="record-title p">Practical · Nocturnal</div>${observations.length?observations.map(o=>`<div class="row"><strong>${esc(o.text)}</strong><div class="meta">${pill(o.status_stage)}${pill(o.matter_id)}</div>${(o.sources||[]).slice(0,2).map(v=>`<div class="source">${esc(v)}</div>`).join('')}</div>`).join(''):empty('No empirical observations.')}</div><div class="card record-col"><div class="record-title a">Academic · Cite</div>${briefs.length?briefs.map(b=>`<div class="row"><strong>${esc(b.title)}</strong><div class="meta">${pill(b.status)} · ${fmt((b.questions||[]).length)} questions</div></div>`).join(''):empty('No research briefs.')}<div class="meta" style="margin-top:10px">${fmt(a.paper_receipts)} paper receipts · ${fmt(a.grounding_audits.length)} grounding audits</div></div><div class="card record-col"><div class="record-title s">Program · Refinery</div>${requirements.map(r=>`<div class="row"><strong>${esc(r.text)}</strong><div class="meta">${pill(r.status)}${pill(r.kind)}</div></div>`).join('')}${caps.map(c=>`<div class="row"><strong>${esc(c.name)}</strong><div class="meta">capability · ${esc(c.description||'')}</div></div>`).join('')||empty('No program-side records.')}</div></div><div class="card" style="margin-top:14px"><h3>Execution / evaluation attached to mapped work</h3><div class="grid metrics">${metric('Runs',x.runs.length)}${metric('Successful runs',x.succeeded_runs)}${metric('Artifacts',x.artifacts.length)}${metric('Experiments',x.experiments.length)}${metric('Supported / passed',x.passed_or_supported_experiments)}${metric('Feedback results',x.feedback_results.length)}</div></div>`;
}
function renderProject(){
  const p=state.project.project,g=state.project.sections.graph.summary,b=state.project.product_boundary;
  return `<div class="topline"><div><div class="eyebrow">Project</div><h2>${esc(p.title)}</h2></div><p>The semantic map is directly inspectable and remains useful without a chat or agent UI.</p></div><div class="grid metrics">${metric('Nodes',g.node_count)}${metric('Edges',g.edge_count)}${metric('Unresolved / candidate',g.unresolved_or_candidate_edges)}${metric('Contradictions',g.contradiction_edges)}</div><div class="grid three" style="margin-top:14px"><div class="card"><h3>Practical boundary</h3><div class="muted">${esc(b.practical)}</div></div><div class="card"><h3>Academic boundary</h3><div class="muted">${esc(b.academic)}</div></div><div class="card"><h3>Program boundary</h3><div class="muted">${esc(b.program)}</div></div></div><div class="card" style="margin-top:14px"><h3>AI role</h3><div class="muted">${esc(b.ai)}</div></div><div class="boundary">${esc(state.project.atlas.boundary)}</div>`;
}
function renderContent(){
  if(!state.project){$('#content').innerHTML=empty('Select a project.');return}
  $('#content').innerHTML=state.view==='map'?renderMap():state.view==='records'?renderRecords():renderProject();
  const cs=$('#clusterSearch');if(cs)cs.oninput=e=>{const start=e.target.selectionStart,end=e.target.selectionEnd;state.clusterQuery=e.target.value;renderContent();const next=$('#clusterSearch');if(next){next.focus();next.setSelectionRange(start,end)}};
  const cf=$('#clusterFilter');if(cf)cf.onchange=e=>{state.clusterFilter=e.target.value;renderContent()};
  const exp=$('#exportCluster');if(exp)exp.onclick=exportCluster;
  document.querySelectorAll('[data-cluster]').forEach(b=>b.onclick=()=>{state.clusterId=b.dataset.cluster;state.nodeId=null;state.coverage=null;state.trace=null;renderContent()});
  document.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>inspectNode(b.dataset.node));
  document.querySelectorAll('[data-trace-node]').forEach(b=>b.onclick=()=>inspectNode(b.dataset.traceNode));
}
async function inspectNode(nodeId){state.nodeId=nodeId;const pid=encodeURIComponent(state.project.project.id);const nid=encodeURIComponent(nodeId);const data=await api(`/api/projects/${pid}/nodes/${nid}/coverage?depth=1`);state.coverage=data.coverage;state.trace=data.trace||null;
  const n=state.project.graph_export?.nodes?.[nodeId], current=state.project.atlas?.clusters?.find(c=>c.id===state.clusterId);
  if(n && current && !current.node_ids.includes(nodeId)){
    const next=state.project.atlas.clusters.find(c=>n.cluster_ids?.includes(c.id)&&c.node_count>0);
    if(next)state.clusterId=next.id;
  }
  renderContent()}
async function loadProject(id){
  const pid=encodeURIComponent(id);state.project=await api(`/api/projects/${pid}?graph=1`);state.view=state.project.primary_view||'map';state.clusterId=state.project.atlas?.clusters?.find(c=>c.node_count>0)?.id||state.project.atlas?.clusters?.[0]?.id||null;state.nodeId=null;state.coverage=null;state.trace=null;state.clusterQuery='';state.clusterFilter='all';
  $('#title').textContent=state.project.project.title||id;$('#problem').textContent=state.project.project.problem||'';renderProjects();renderNav();renderContent();
}
async function boot(){
  try{state.projects=await api('/api/projects');renderProjects();if(state.projects.length)await loadProject(state.projects[0].id);else{$('#title').textContent='Cite-Refinery';$('#problem').textContent='Create or ingest a project to begin mapping semantic modules across Practical, Academic, and Program.';renderNav();$('#content').innerHTML=empty('No projects yet.')}}catch(err){$('#content').innerHTML=`<div class="empty">${esc(err.message)}</div>`}
}
boot();
</script>
</body></html>'''


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, default=str) + "\n").encode("utf-8")


def _handler(workspace: str) -> type[BaseHTTPRequestHandler]:
    store = JsonStore(workspace)
    product = ProductWorkspace(store)

    class Handler(BaseHTTPRequestHandler):
        server_version = "CiteRefineryWeb/0.11"

        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _send_json(self, value: Any, status: int = HTTPStatus.OK) -> None:
            body = _json_bytes(value)
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            body = APP_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if path in {"/", "/index.html"}:
                    self._send_html()
                    return
                if path == "/api/health":
                    self._send_json({"status": "ok", "product": "cite-refinery", "primary_view": "clustered_three_layer_map"})
                    return
                if path == "/api/projects":
                    self._send_json(product.list_projects())
                    return

                parts = [unquote(value) for value in path.strip("/").split("/") if value]
                if len(parts) >= 3 and parts[:2] == ["api", "projects"]:
                    project_id = parts[2]
                    if len(parts) == 3:
                        query = parse_qs(parsed.query)
                        include_graph = query.get("graph", ["0"])[0] in {"1", "true", "yes"}
                        self._send_json(product.project_view(project_id, include_graph=include_graph))
                        return
                    if len(parts) == 4 and parts[3] == "graph":
                        self._send_json(product.graph.export(project_id))
                        return
                    if len(parts) == 4 and parts[3] == "atlas":
                        self._send_json(product.cluster_atlas(project_id))
                        return
                    if len(parts) == 5 and parts[3] == "clusters":
                        self._send_json(product.cluster_view(project_id, parts[4]))
                        return
                    if len(parts) == 6 and parts[3] == "nodes" and parts[5] == "trace":
                        query = parse_qs(parsed.query)
                        depth = int(query.get("depth", ["4"])[0])
                        self._send_json(product.trace_node(project_id, parts[4], max_depth=depth))
                        return
                    if len(parts) == 6 and parts[3] == "nodes" and parts[5] == "coverage":
                        query = parse_qs(parsed.query)
                        depth = int(query.get("depth", ["1"])[0])
                        self._send_json(product.node_view(project_id, parts[4], depth=depth))
                        return

                self._send_json({"error": "not_found", "path": path}, HTTPStatus.NOT_FOUND)
            except (KeyError, ValueError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND if isinstance(exc, KeyError) else HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # pragma: no cover - final HTTP safety boundary
                self._send_json({"error": "internal_error", "detail": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    return Handler


def make_server(workspace: str, *, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    # This is a local operator UI, not an authenticated web service. Forbid
    # network exposure until proper identity and project authorization exist.
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("unauthenticated Cite-Refinery workspace must bind to loopback only")
    return ThreadingHTTPServer((host, int(port)), _handler(workspace))


def serve(workspace: str, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = make_server(workspace, host=host, port=port)
    print(f"Cite-Refinery clustered map: http://{host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
