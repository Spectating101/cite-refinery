from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
:root {
  --bg:#f2f0e9; --paper:#fbfaf6; --ink:#191a17; --muted:#6f7169;
  --line:#d7d4c9; --accent:#6f7754; --accent-2:#9b6b42; --dark:#23251f;
  --soft:#e8e5da; --good:#526443; --warn:#8d653d; --bad:#824c43;
}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button,input,select{font:inherit} a{color:inherit}.shell{display:grid;grid-template-columns:270px 1fr;min-height:100vh}
.sidebar{background:var(--dark);color:#efeee8;padding:22px 18px;position:sticky;top:0;height:100vh;overflow:auto}.brand{font-size:20px;font-weight:750;letter-spacing:-.02em}.brand small{display:block;color:#adaf9f;font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;margin-top:3px}.side-label{color:#929586;font-size:10px;text-transform:uppercase;letter-spacing:.12em;margin:28px 8px 8px}.project-button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#dad9d2;padding:10px;border-radius:8px;cursor:pointer;margin-bottom:3px}.project-button:hover,.project-button.active{background:#34362e;color:white}.project-button strong{display:block;font-size:13px}.project-button span{display:block;color:#9ea091;font-size:11px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.main{min-width:0}.header{padding:28px 34px 0}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--accent)}h1{font-size:32px;line-height:1.08;letter-spacing:-.035em;margin:7px 0 8px}.problem{max-width:900px;color:var(--muted);font-size:14px}.tabs{display:flex;gap:2px;overflow:auto;padding:24px 34px 0;border-bottom:1px solid var(--line)}.tab{border:0;background:transparent;padding:12px 14px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;text-transform:capitalize}.tab.active{color:var(--ink);border-bottom-color:var(--accent);font-weight:650}.content{padding:28px 34px 60px;max-width:1450px}.grid{display:grid;gap:14px}.metrics{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.metric,.card{background:var(--paper);border:1px solid var(--line);border-radius:10px}.metric{padding:16px}.metric .value{font-size:26px;font-weight:730;letter-spacing:-.03em}.metric .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-top:4px}.card{padding:18px}.card h3{margin:0 0 12px;font-size:15px}.section-title{display:flex;align-items:end;justify-content:space-between;gap:16px;margin:0 0 14px}.section-title h2{margin:0;font-size:20px;letter-spacing:-.02em}.section-title p{margin:0;color:var(--muted);font-size:12px}.two{grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr)}.three{grid-template-columns:repeat(3,minmax(0,1fr))}.list{display:grid;gap:8px}.row{padding:12px 0;border-top:1px solid var(--line)}.row:first-child{border-top:0;padding-top:0}.row:last-child{padding-bottom:0}.row-title{font-weight:650}.meta{color:var(--muted);font-size:11px;margin-top:4px}.pill{display:inline-block;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:3px 7px;font-size:10px;margin:2px 3px 2px 0}.pill.practical{background:#eee7db}.pill.academic{background:#e5e8dc}.pill.program{background:#ebe2d9}.pill.neutral{background:#ecebe6}.muted{color:var(--muted)}.empty{padding:28px;border:1px dashed var(--line);border-radius:10px;color:var(--muted);text-align:center}.table-wrap{overflow:auto}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}.table th{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:650}.engine{font-size:11px;color:var(--accent-2);font-weight:650;text-transform:uppercase;letter-spacing:.08em}.graph-toolbar{display:flex;gap:8px;margin-bottom:12px}.graph-toolbar input{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:white}.node{display:block;width:100%;text-align:left;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:11px;cursor:pointer}.node:hover{border-color:#aaa796}.node .statement{font-weight:600}.node .node-meta{margin-top:5px;color:var(--muted);font-size:10px}.inspector{position:sticky;top:18px}.relation{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;background:var(--soft);padding:3px 5px;border-radius:4px}.boundary{font-size:11px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px;margin-top:12px}.source-link{word-break:break-all;font-size:11px;color:var(--muted)}.layer-strip{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}.layer-box{border:1px solid var(--line);border-radius:8px;padding:10px}.layer-box strong{display:block;text-transform:capitalize}.layer-box span{font-size:11px;color:var(--muted)}.good{color:var(--good)}.warn{color:var(--warn)}.bad{color:var(--bad)}
@media(max-width:900px){.shell{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.two,.three{grid-template-columns:1fr}.header,.content{padding-left:18px;padding-right:18px}.tabs{padding-left:18px;padding-right:18px}}
</style>
</head>
<body>
<div class="shell">
  <aside class="sidebar">
    <div class="brand">Cite-Refinery<small>problem intelligence workspace</small></div>
    <div class="side-label">Projects</div>
    <div id="projects"></div>
  </aside>
  <main class="main">
    <header class="header">
      <div class="eyebrow" id="status">Unified workspace</div>
      <h1 id="title">Loading…</h1>
      <div class="problem" id="problem"></div>
    </header>
    <nav class="tabs" id="tabs"></nav>
    <section class="content" id="content"><div class="empty">Loading project workspace…</div></section>
  </main>
</div>
<script>
const state={projects:[],project:null,tab:'overview',node:null};
const $=s=>document.querySelector(s); const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString();
async function api(path){const r=await fetch(path); if(!r.ok)throw new Error(await r.text()); return r.json()}
function projectButton(p){return `<button class="project-button ${state.project?.project?.id===p.id?'active':''}" data-project="${esc(p.id)}"><strong>${esc(p.title)}</strong><span>${esc(p.problem||'')}</span></button>`}
function renderProjects(){$('#projects').innerHTML=state.projects.length?state.projects.map(projectButton).join(''):'<div class="muted">No projects yet.</div>';document.querySelectorAll('[data-project]').forEach(b=>b.onclick=()=>loadProject(b.dataset.project))}
function renderTabs(){const nav=state.project?.navigation||[];$('#tabs').innerHTML=nav.map(t=>`<button class="tab ${state.tab===t?'active':''}" data-tab="${t}">${esc(t)}</button>`).join('');document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{state.tab=b.dataset.tab;state.node=null;renderTabs();renderContent()})}
function metric(label,value){return `<div class="metric"><div class="value">${fmt(value)}</div><div class="label">${esc(label)}</div></div>`}
function pills(values,cls=''){return (values||[]).filter(Boolean).map(v=>`<span class="pill ${cls}">${esc(v)}</span>`).join('')}
function empty(msg){return `<div class="empty">${esc(msg)}</div>`}
function renderOverview(s){const o=s.overview,g=s.graph.summary;return `<div class="section-title"><div><div class="engine">One project · three engines · one semantic graph</div><h2>Project state</h2></div><p>No composite score. Counts expose the represented lifecycle.</p></div><div class="grid metrics">${metric('Reality observations',o.reality_observations)}${metric('Research briefs',o.research_briefs)}${metric('Semantic nodes',o.semantic_nodes)}${metric('Graph edges',o.semantic_edges)}${metric('Open requirements',o.open_requirements)}${metric('Solution candidates',o.solution_candidates)}${metric('Experiments',o.experiments)}${metric('Feedback results',o.feedback_results)}</div><div class="grid three" style="margin-top:14px"><div class="card"><div class="engine">Nocturnal</div><h3>Reality</h3><p class="muted">${fmt(s.reality.observations.length)} observations across ${fmt(s.reality.matter_count)} matters, backed by ${fmt(s.reality.source_link_count)} source links.</p></div><div class="card"><div class="engine">Cite</div><h3>Research</h3><p class="muted">${fmt(s.research.research_question_count)} research questions and ${fmt(s.research.paper_receipts)} paper receipts across ${fmt(s.research.briefs.length)} briefs.</p></div><div class="card"><div class="engine">Refinery</div><h3>Solutions</h3><p class="muted">${fmt(s.solutions.candidate_count)} candidate supply objects mapped against ${fmt(s.solutions.requirements.length)} requirements; ${fmt(s.solutions.capabilities.length)} capabilities adopted locally.</p></div></div><div class="grid two" style="margin-top:14px"><div class="card"><h3>Semantic topology</h3><div class="layer-strip">${['practical','academic','program'].map(l=>`<div class="layer-box"><strong>${l}</strong><span>${fmt(g.layer_counts[l]||0)} nodes</span></div>`).join('')}</div><div class="meta">${fmt(g.unresolved_or_candidate_edges)} unresolved/candidate edges · ${fmt(g.contradiction_edges)} contradiction edges · ${fmt(s.graph.clusters.length)} semantic clusters</div></div><div class="card"><h3>Authority boundary</h3>${Object.entries(state.project.product_boundary||{}).map(([k,v])=>`<div class="row"><div class="row-title">${esc(k)}</div><div class="meta">${esc(v)}</div></div>`).join('')}</div></div>`}
function renderReality(r){return `<div class="section-title"><div><div class="engine">${esc(r.engine)}</div><h2>Reality</h2></div><p>Empirical observations stay empirical; they are not automatically academic claims.</p></div><div class="grid two"><div class="card"><h3>Observations</h3><div class="list">${r.observations.length?r.observations.slice(0,200).map(o=>`<div class="row"><div class="row-title">${esc(o.text)}</div><div class="meta">${pills([o.status_stage,o.frame,o.matter_id])}</div>${(o.sources||[]).slice(0,3).map(src=>`<div class="source-link">${esc(src)}</div>`).join('')}</div>`).join(''):empty('No empirical observations yet.')}</div></div><div><div class="card"><h3>Source systems</h3>${Object.entries(r.source_system_counts||{}).map(([k,v])=>`<div class="row"><span>${esc(k)}</span><strong style="float:right">${fmt(v)}</strong></div>`).join('')||empty('No source systems.')}</div><div class="card" style="margin-top:14px"><h3>Status stages</h3>${Object.entries(r.status_stage_counts||{}).map(([k,v])=>`<div class="row"><span>${esc(k)}</span><strong style="float:right">${fmt(v)}</strong></div>`).join('')||empty('No stages.')}</div></div></div>`}
function renderResearch(r){return `<div class="section-title"><div><div class="engine">${esc(r.engine)}</div><h2>Research</h2></div><p>Cite discovery and grounding are projected without silently upgrading authority.</p></div><div class="grid metrics">${metric('Briefs',r.briefs.length)}${metric('Research questions',r.research_question_count)}${metric('Paper receipts',r.paper_receipts)}${metric('Grounding audits',r.grounding_audits.length)}</div><div class="card" style="margin-top:14px"><h3>Research briefs</h3>${r.briefs.length?`<div class="table-wrap"><table class="table"><thead><tr><th>Brief</th><th>Status</th><th>Questions</th><th>Observations</th></tr></thead><tbody>${r.briefs.map(b=>`<tr><td><strong>${esc(b.title)}</strong><div class="meta">${esc(b.id)}</div></td><td>${pills([b.status])}</td><td>${fmt((b.questions||[]).length)}</td><td>${fmt((b.observation_ids||[]).length)}</td></tr>`).join('')}</tbody></table></div>`:empty('No research briefs yet.')}</div>`}
function graphNodeButton(n){return `<button class="node" data-node="${esc(n.id)}"><div class="statement">${esc(n.statement)}</div><div class="node-meta">${pills([n.layer,n.kind],n.layer)} ${esc(n.id)}</div></button>`}
async function inspectNode(id){state.node=id;const p=state.project.project.id;const data=await api(`/api/projects/${encodeURIComponent(p)}/nodes/${encodeURIComponent(id)}/coverage?depth=1`);renderGraph(state.project.sections.graph,data.coverage)}
function renderGraph(g,coverage=null){const exp=state.project.graph_export||{};let nodes=Object.values(exp.nodes||{});const q=($('#graph-search')?.value||'').toLowerCase();if(q)nodes=nodes.filter(n=>(n.statement+' '+n.kind+' '+n.layer).toLowerCase().includes(q));const inspector=coverage?`<div class="card inspector"><div class="engine">Trace this node</div><h3>${esc(coverage.node.statement)}</h3><div>${pills([coverage.node.layer,coverage.node.kind],coverage.node.layer)}</div><div class="layer-strip">${['practical','academic','program'].map(l=>`<div class="layer-box"><strong class="${coverage.layer_presence[l]?'good':'muted'}">${l}</strong><span>${coverage.layer_presence[l]?'represented':'not represented'}</span></div>`).join('')}</div><div class="row"><div class="row-title">Intersection</div><div class="meta">${esc(coverage.intersection)}</div></div><div class="row"><div class="row-title">Relations</div><div class="meta">${Object.entries(coverage.relations||{}).map(([r,v])=>`<span class="relation">${esc(r)} × ${fmt(v.length)}</span>`).join(' ')||'None'}</div></div><div class="row"><div class="row-title">Unresolved / missing</div><div class="meta">${fmt((coverage.unresolved_or_missing||[]).length)}</div></div><div class="row"><div class="row-title">Contradictions</div><div class="meta">${fmt((coverage.contradictions||[]).length)}</div></div><div class="boundary">${esc(coverage.boundary)}</div></div>`:`<div class="card inspector"><h3>Node inspector</h3><p class="muted">Select a semantic node to inspect its practical, academic and program neighborhood.</p></div>`;return `<div class="section-title"><div><div class="engine">${esc(g.engine)}</div><h2>Semantic map</h2></div><p>Specific modules, typed edges, provenance and represented gaps.</p></div><div class="grid metrics">${metric('Nodes',g.summary.node_count)}${metric('Edges',g.summary.edge_count)}${metric('Clusters',g.clusters.length)}${metric('Unresolved / candidate',g.summary.unresolved_or_candidate_edges)}</div><div class="grid two" style="margin-top:14px"><div><div class="graph-toolbar"><input id="graph-search" placeholder="Search semantic nodes…" value="${esc(q)}"></div><div class="list" id="node-list">${nodes.length?nodes.slice(0,250).map(graphNodeButton).join(''):empty('No semantic nodes match.')}</div></div>${inspector}</div>`}
function bindGraph(){const input=$('#graph-search');if(input)input.oninput=()=>{const v=input.value;renderContent(v)};document.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>inspectNode(b.dataset.node))}
function renderSolutions(s){return `<div class="section-title"><div><div class="engine">${esc(s.engine)}</div><h2>Solutions</h2></div><p>Candidate supply stays distinct from adoption and validation.</p></div><div class="grid metrics">${metric('Requirements',s.requirements.length)}${metric('Candidates',s.candidate_count)}${metric('Capabilities',s.capabilities.length)}${metric('Implementations',s.implementations.length)}</div><div class="grid two" style="margin-top:14px"><div class="card"><h3>Requirements</h3>${s.requirements.length?s.requirements.map(r=>`<div class="row"><div class="row-title">${esc(r.text)}</div><div class="meta">${pills([r.status,r.kind,...(r.tags||[])])}</div></div>`).join(''):empty('No requirements yet.')}</div><div class="card"><h3>Supply authority</h3>${Object.entries(s.candidate_authority_counts||{}).map(([k,v])=>`<div class="row"><span>${esc(k)}</span><strong style="float:right">${fmt(v)}</strong></div>`).join('')||empty('No mapped candidates.')}</div></div>`}
function renderBuild(b){return `<div class="section-title"><div><h2>Build / Execute</h2></div><p>Adopted capabilities become implementations, runs and artifacts.</p></div><div class="grid metrics">${metric('Implementations',b.implementations.length)}${metric('Runs',b.runs.length)}${metric('Succeeded runs',b.succeeded_runs)}${metric('Artifacts',b.artifacts.length)}</div><div class="card" style="margin-top:14px"><h3>Runs</h3>${b.runs.length?`<div class="table-wrap"><table class="table"><thead><tr><th>Provider</th><th>Status</th><th>Duration</th><th>Run</th></tr></thead><tbody>${b.runs.map(r=>`<tr><td>${esc(r.provider)}</td><td>${pills([r.status])}</td><td>${fmt(r.duration_ms)} ms</td><td class="meta">${esc(r.id)}</td></tr>`).join('')}</tbody></table></div>`:empty('No implementation runs yet.')}</div>`}
function renderValidate(v){return `<div class="section-title"><div><h2>Validate / Feedback</h2></div><p>Experiments and post-intervention observation close the loop without automatic causal claims.</p></div><div class="grid metrics">${metric('Experiments',v.experiments.length)}${metric('Passed / supported',v.passed_or_supported_experiments)}${metric('Feedback requests',v.feedback_requests.length)}${metric('Feedback results',v.feedback_results.length)}</div><div class="card" style="margin-top:14px"><h3>Experiments</h3>${v.experiments.length?v.experiments.map(e=>`<div class="row"><div class="row-title">${esc(e.name)}</div><div class="meta">${pills([e.verdict])} ${esc(e.method||'')}</div><div class="meta">${esc(e.result||'')}</div></div>`).join(''):empty('No experiments yet.')}</div>`}
function renderContent(preserveSearch=null){if(!state.project)return;const s=state.project.sections;let html='';if(state.tab==='overview')html=renderOverview(s);else if(state.tab==='reality')html=renderReality(s.reality);else if(state.tab==='research')html=renderResearch(s.research);else if(state.tab==='graph')html=renderGraph(s.graph);else if(state.tab==='solutions')html=renderSolutions(s.solutions);else if(state.tab==='build')html=renderBuild(s.build);else if(state.tab==='validate')html=renderValidate(s.validate);$('#content').innerHTML=html;if(state.tab==='graph'){if(preserveSearch!==null)$('#graph-search').value=preserveSearch;bindGraph()}}
async function loadProject(id){state.project=await api(`/api/projects/${encodeURIComponent(id)}?graph=1`);state.node=null;$('#title').textContent=state.project.project.title||'Untitled project';$('#problem').textContent=state.project.project.problem||'';$('#status').textContent=`${state.project.project.status||'active'} · unified workspace`;renderProjects();renderTabs();renderContent();history.replaceState(null,'',`?project=${encodeURIComponent(id)}`)}
async function init(){try{state.projects=await api('/api/projects');renderProjects();const q=new URLSearchParams(location.search);const id=q.get('project')||state.projects[0]?.id;if(id)await loadProject(id);else{$('#title').textContent='Cite-Refinery';$('#problem').textContent='Create a project to begin.';$('#content').innerHTML=empty('No projects in this workspace.')}}catch(e){$('#content').innerHTML=`<div class="empty bad">${esc(e.message)}</div>`}}
init();
</script>
</body>
</html>'''


class _Handler(BaseHTTPRequestHandler):
    workspace: ProductWorkspace

    def _json(self, value: Any, status: int = 200) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _html(self, value: str, status: int = 200) -> None:
        payload = value.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message, "status": status}, status=status)

    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - intentionally quiet
        return

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        try:
            if path in {"/", "/index.html"}:
                self._html(APP_HTML)
                return
            if path == "/api/health":
                self._json({"status": "ok", "product": "cite-refinery"})
                return
            if path == "/api/projects":
                self._json(self.workspace.list_projects())
                return

            parts = [part for part in path.split("/") if part]
            if len(parts) >= 3 and parts[:2] == ["api", "projects"]:
                project_id = parts[2]
                if len(parts) == 3:
                    include_graph = query.get("graph", ["0"])[0] in {"1", "true", "yes"}
                    self._json(self.workspace.project_view(project_id, include_graph=include_graph))
                    return
                if len(parts) == 4 and parts[3] == "graph":
                    self._json(self.workspace.graph.export(project_id))
                    return
                if len(parts) == 6 and parts[3] == "nodes" and parts[5] == "coverage":
                    depth = int(query.get("depth", ["1"])[0])
                    self._json(self.workspace.node_view(project_id, parts[4], depth=depth))
                    return

            self._error(HTTPStatus.NOT_FOUND, "not found")
        except KeyError as exc:
            self._error(HTTPStatus.NOT_FOUND, str(exc))
        except (ValueError, TypeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:  # pragma: no cover - defensive server boundary
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"internal error: {exc}")


def make_server(
    workspace: str | Path = ".cite-refinery",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    if not 1 <= int(port) <= 65535:
        raise ValueError("port must be between 1 and 65535")
    product = ProductWorkspace(JsonStore(workspace))

    class Handler(_Handler):
        pass

    Handler.workspace = product
    return ThreadingHTTPServer((host, int(port)), Handler)


def serve(
    workspace: str | Path = ".cite-refinery",
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    server = make_server(workspace, host=host, port=port)
    print(f"Cite-Refinery web: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive behavior
        pass
    finally:
        server.server_close()
